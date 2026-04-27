# Kernel Module Emission — Full Plan

**Status as of 2026-04-26:**
- Step 1 (C shim): DONE 2026-04-21.
- Step 2 (ELF emitter — staged inputs, .rela.text writer, symtab population): DONE.
- Step 3 (`ExternalKernelFunction` lexer/parser/AST): DONE.
- Step 4 (codegen reloc emission at extern call sites): DONE.
- Step 5 (`-kmod` CLI flag): DONE.
- Step 6 (end-to-end load test, Linux box): PENDING — bytes-clean, awaiting hardware.
- Bonus (not originally in plan): R_X86_64_64 data-section relocs for string-literal pointers, plus `Library.KernelShim` mirroring `ail_shim.h`. DONE.

End-to-end works in WSL today: `./ailang.x -kmod my.ailang ail_payload.o` produces an ET_REL with PLT32 relocs against the C shim's symbols and R_X86_64_64 relocs against `.data` for any string literals passed to externs. `ld -shared` against a stub resolves all calls and string pointers correctly. See `TestCode/Test.KModViaLibrary.ailang` for a representative source.

Next AiLang-side polish (optional):
- Function-skip JMP stubs around each function are still emitted in kmod mode (5 wasted bytes per function). Harmless; kernel doesn't execute that path.
- Source code that needs FixedPools in a kmod payload would have to init them inside ail_main — the auto-emit prologue is suppressed.
- Multi-payload kmod builds (one .ailang per .ko) untested.

---

## WHY

AiLang compiles to x86-64 ELF. Linux kernel modules are ET_REL ELF objects loaded by `insmod`, which resolves external symbol references at load time via relocation entries. Getting AiLang to produce loadable `.ko` files unlocks:

- Writing kernel-space code in a single self-hosted language instead of requiring C for anything touching the kernel.
- A tractable path to the same trick on Haiku (user-space C++ Kits), macOS (Cocoa), Windows (Win32) — in each case a small C/C++ shim absorbs the foreign ABI.
- A legitimate avenue to replace AiLang's current `mmap`-per-allocation arena with a shared kernel-library allocator (the originally-motivating performance win).

**Strategy:** Rust-for-Linux-style split. A thin C shim (`ail_shim.c`) owns all the kernel-version-unstable glue — `module_init`/`module_exit`, `MODULE_LICENSE`, `struct module` layout, calls to `printk`/`kmalloc`/etc. AiLang emits a payload object that only references the shim's stable `ail_*` symbol surface. `kbuild` + `ld -r` merges the two into a single `.ko`.

This reduces AiLang's relocation-emission scope to exactly one reloc type (`R_X86_64_PLT32`) and one symbol kind (`UND GLOBAL FUNC`). No kallsyms plumbing, no kernel-header reproduction, no `module_init` macro magic in the compiler.

---

## WHO — components involved

| Component | File | Role |
|---|---|---|
| C shim | `kernel_module/shim/ail_shim.c` | DONE. Hosts kernel-side glue + wrappers. |
| Shim header | `kernel_module/shim/ail_shim.h` | DONE. Documents stable ABI surface. |
| Shim Makefile | `kernel_module/shim/Makefile` | DONE. kbuild dance; merges shim.o + payload.o. |
| .ko emitter | `Librarys/Compiler/Output/Library.CELFKernelModule.ailang` | EXTEND. Accept reloc + extern + export arrays; emit real `.rela.text` + UND symtab entries. |
| Parser | `Librarys/Compiler/Frontend/Parser/Library.CParserDeclarations.ailang` | EXTEND. Add `ExternalKernelFunction.<name>` declaration. |
| Lexer | `Librarys/Compiler/Frontend/Lexer/*` | EXTEND. New keyword `ExternalKernelFunction`. |
| AST | wherever AST node kinds live | EXTEND. New node `AST.EXTERN_KFUNC`. |
| Codegen | call-site emission path | EXTEND. For calls to EXTERN_KFUNC targets, emit placeholder + reloc record. |
| CLI driver | `ailang_cli.ailang` | EXTEND. New `-kmod` flag routes to `Output_BuildKernelModule`, suppresses the normal ET_EXEC / `_start` setup. |
| Test program | `TestCode/Test.KernelModule.ailang` | NEW. Minimal "hello" payload exercising one external call. |

---

## WHAT — each step's concrete output

### Step 1 — C shim   ✅ DONE 2026-04-21

On disk now:
- `kernel_module/shim/ail_shim.h` (39 lines) — stable ABI declarations.
- `kernel_module/shim/ail_shim.c` (72 lines) — `module_init/exit` hooks calling `ail_main`/`ail_exit`; wrappers: `ail_printk`, `ail_kmalloc`, `ail_kfree`, `ail_strlen`.
- `kernel_module/shim/Makefile` — `obj-m += ail_combined.o`, `ail_combined-objs := ail_shim.o ail_payload.o`. Guards on `ail_payload.o` existence.

### Step 2 — Extend `ELF_BuildKernelModule` API   ✅ DONE 2026-04-25

Current: `ELF_BuildKernelModule(code, code_size, data, data_size)` — emits ET_REL with empty `.rela.text` and minimal `.symtab`.

New signature:
```
ELF_BuildKernelModule(
    code, code_size,
    data, data_size,
    relocs, reloc_count,              // flat array: 4 qwords per record
                                      // {text_offset, sym_idx, reloc_type, addend}
    extern_names, extern_count,       // UND symbols (ail_printk etc.)
    export_names, export_offsets, export_count  // GLOBAL defined symbols (ail_main, ail_exit)
                                      //   — offsets are bytes into .text
)
```

Changes inside `Library.CELFKernelModule.ailang`:
- **`.rela.text` writer** (currently empty, line 511): walk `relocs[]`, emit one `Elf64_Rela` per record. Each record is 24 bytes: `{r_offset: u64, r_info: u64 = (sym_idx << 32) | reloc_type, r_addend: i64}`.
- **`.symtab` writer**: currently emits only file + section symbols. Extend to append:
  - One `Elf64_Sym` per export (`st_name` pointing into `.strtab`, `st_info = STB_GLOBAL|STT_FUNC`, `st_shndx = .text_idx`, `st_value = export_offsets[i]`).
  - One `Elf64_Sym` per extern (`st_name` into `.strtab`, `st_info = STB_GLOBAL|STT_FUNC`, `st_shndx = SHN_UNDEF = 0`, `st_value = 0`).
- **`.strtab` writer**: add all extern + export names.
- **`sh_info` of `.symtab`**: update to point to first non-local symbol (locals come before globals in ELF symtab — this is mandatory; ld rejects symtabs where this is wrong).
- **Relocation section `sh_link`**: must point at `.symtab` section index.
- **Relocation section `sh_info`**: must point at `.text` section index.

**Verifiable by:** hand-constructed call with one extern (`ail_printk`) and one reloc, then `readelf -r out.o` + `readelf -s out.o`.

### Step 3 — Source-language marker for externs   ✅ DONE 2026-04-26

New declaration form:
```
ExternalKernelFunction.ail_printk {
    Input: s: Address
    Output: Integer
}
```

Properties:
- No `Body:` block (parser rejects if present).
- Registered in a new symbol table scope: `EXTERN_KFUNC`. Distinct from `FUNCTION` so the analyzer can check that you don't call an extern as if it were a local.
- Signature is used for arg-count + type-count validation at call sites (reuses the existing arity check from the analyzer wishlist).

Parser work:
1. Lexer: add keyword `ExternalKernelFunction` to the keyword table.
2. Parse rule: mirror the `Function` declaration parser but reject `Body`.
3. AST: new node `AST.EXTERN_KFUNC` with `data1 = name`, children = parameters (no body child).
4. Semantic pass: record into the extern-symbol table; fail if redeclared with mismatched signature; fail if a body appears.

### Step 4 — Codegen reloc emission   ✅ DONE 2026-04-26

At every `call` instruction currently emitted from `Library.CCompileFunc.ailang` (or wherever call codegen lives — confirm via `relmem callers` + grep during execution):

1. Resolve callee's symbol kind. If `FUNCTION` (local): existing path, resolved as relative offset at link time within this same file.
2. If `EXTERN_KFUNC`: emit `0xE8` (call opcode, 5 bytes total including 32-bit displacement) + 4 bytes of `0x00`. Record a reloc entry: `{text_offset = current_text_offset - 4, sym_name = callee_name, type = R_X86_64_PLT32 = 4, addend = -4}`.

Reloc records accumulate in a new `RelocList` FixedPool at module scope. Flushed as the `relocs[]` parameter into `ELF_BuildKernelModule` at final emit time.

### Step 5 — CLI flag `-kmod`   ✅ DONE 2026-04-25

In `ailang_cli.ailang`:
- Parse `-kmod` from argv.
- If set:
  - Skip emission of the usual `_start` stub (kernel modules have no entry point — `insmod` calls `init_module` which the shim provides).
  - Skip implicit wrapping of `Main` into `RunTask`.
  - Require that the source declares at least `ail_main` and `ail_exit` as regular `Function` definitions. Add them to the `exports[]` array passed to `ELF_BuildKernelModule`.
  - Drive output via `Output_BuildKernelModule` instead of the ET_EXEC path.
- Final artifact: ET_REL `.o` at the user-specified path.

### Step 6 — End-to-end test (WSL, bytes-only)

Create `TestCode/Test.KernelModule.ailang`:
```
LibraryImport.KernelShim  // provides ExternalKernelFunction.ail_printk etc.

Function.ail_main {
    Output: Integer
    Body: {
        ail_printk("hello from ailang kernel payload")
        ReturnValue(0)
    }
}

Function.ail_exit {
    Body: {
        ail_printk("goodbye from ailang")
    }
}
```

Build + verify:
```
./ailang.x -kmod TestCode/Test.KernelModule.ailang ail_payload.o
readelf -h ail_payload.o  # expect: Type: REL, Machine: Advanced Micro Devices X86-64
readelf -s ail_payload.o  # expect: ail_main GLOBAL FUNC, ail_exit GLOBAL FUNC, ail_printk UND
readelf -r ail_payload.o  # expect: one R_X86_64_PLT32 at offset of the call
objdump -d ail_payload.o  # expect: `call <addr>` with reloc annotation pointing at ail_printk
```

Linker sanity without a live kernel: in WSL,
```
cat > stub.c <<'EOF'
int ail_printk(const char *s) { (void)s; return 0; }
EOF
gcc -c stub.c -o stub.o
ld -r stub.o ail_payload.o -o combined.o
readelf -r combined.o  # expect: no unresolved relocs
```

If `ld -r` resolves the reloc without complaining, the bytes are correct. Load-testing requires the dedicated Linux box (see next step).

### Step 7 — Load test (Linux box, user-driven)

Not doable in WSL. Hand-off:
1. Copy `kernel_module/shim/` + `ail_payload.o` to Linux box with `linux-headers-$(uname -r)` installed.
2. `cd kernel_module/shim && make`
3. `sudo insmod ail_combined.ko`
4. `dmesg | tail` — expect:
   ```
   ail_shim: loaded, invoking ail_main()
   hello from ailang kernel payload
   ```
5. `sudo rmmod ail_combined`
6. `dmesg | tail` — expect:
   ```
   goodbye from ailang
   ail_shim: unloaded
   ```

---

## WHEN — sequencing

Hard dependencies:

```
Step 1 (DONE) ─┐
               ├─> Step 7 (user load-test, last)
Step 2 ────────┤
  ↑            │
Step 4 ────────┤
  ↑            │
Step 3 ────────┤
  ↑            │
Step 5 ────────┤
  ↑            │
Step 6 ────────┘
```

- Step 2 depends on nothing; can be done first and tested in isolation with a hand-crafted call (no compiler integration).
- Step 3 is parser/lexer/AST only; independently testable via `analyzer.x` on a source with an `ExternalKernelFunction` declaration.
- Step 4 depends on Step 3 (needs EXTERN_KFUNC symbol kind to exist in the symbol table).
- Step 5 depends on Steps 2, 3, 4 — wires them together.
- Step 6 depends on Step 5 — end-to-end test.
- Step 7 depends on Step 6 producing readelf-clean bytes.

**Recommended execution order:** 2 → 3 → 4 → 5 → 6 → (hand off) 7. Each step has a local verification gate before moving on.

---

## WHERE — file inventory

Files that will be created:
- `TestCode/Test.KernelModule.ailang` — test program.
- (possibly) `Librarys/Library.KernelShim.ailang` — library of all `ExternalKernelFunction` declarations that mirror `ail_shim.h`. Consumers `LibraryImport.KernelShim`. This keeps the shim surface in one place instead of scattered through test files.

Files that will be modified (minor, local changes only):
- `Librarys/Compiler/Output/Library.CELFKernelModule.ailang` — extended signature + reloc/symtab writers.
- `Librarys/Compiler/Frontend/Lexer/*` — new keyword.
- `Librarys/Compiler/Frontend/Parser/Library.CParserDeclarations.ailang` — new parse rule.
- `Librarys/Compiler/Compile/Modules/Library.CCompileFunc.ailang` (or wherever `call` is emitted) — reloc record on extern calls.
- `ailang_cli.ailang` — `-kmod` flag, routing.

Files that stay untouched:
- The analyzer (`ailang_analyzer.ailang` + Library.Analyzer*) — the new `ExternalKernelFunction` kind is additive; existing checks still apply. One new check eventually ("calls to externs must match declared arity") but that's a stretch goal, not required for first cut.
- Everything outside the Compiler/ tree.

---

## Correctness gates — "what does 'done' look like for each step"

| Step | Gate |
|---|---|
| 1 | ✅ Files exist; `ail_shim.c` syntactically parseable (can be checked with `gcc -fsyntax-only -I<kernel-headers>` on Linux box only; accepted on trust for now). |
| 2 | Unit test in WSL: hand-craft a `relocs` array with one entry, call `ELF_BuildKernelModule`, verify `readelf -r` shows exactly that reloc. |
| 3 | `analyzer.x` on a file with `ExternalKernelFunction.foo {...}` reports it as a declared symbol, no false errors. Adding a `Body:` to the extern produces a specific error ("ExternalKernelFunction declarations have no body"). |
| 4 | Compile a source with one `ail_printk("x")` call, dump `objdump -d` on the text section, verify the `call` instruction has `E8 00 00 00 00` bytes and a corresponding reloc record in the accumulated list. |
| 5 | `./ailang.x -kmod src.ailang out.o` produces an ET_REL file; same source without `-kmod` still produces ET_EXEC. No cross-contamination. |
| 6 | All four `readelf` / `objdump` / `ld -r` checks pass. |
| 7 | `insmod` succeeds, `dmesg` shows the expected four lines, `rmmod` succeeds cleanly. |

---

## Risks + unknowns

1. **Symtab ordering is strict.** ELF requires all `STB_LOCAL` symbols before any `STB_GLOBAL`/`STB_WEAK`, and `sh_info` of the symtab section must equal the index of the first non-local. Getting this wrong means `ld` rejects the object. **Mitigation:** Step 2 writes locals first, then exports (GLOBAL DEFINED), then externs (GLOBAL UND). Set `sh_info = (locals_count)`.

2. **Addend semantics for PLT32.** The right addend for a `call` via E8 is `-4` because the displacement is measured from the end of the 4-byte operand, not from the start of the instruction. Getting this wrong silently produces a 4-byte-off call target at load time. **Mitigation:** hard-code `-4` and verify with `objdump -d` that the computed target matches the symbol address after `ld -r`.

3. **`e_ident[EI_OSABI]`.** Current value is ELFOSABI_NONE (line 427). Linux kernel loaders accept this; Haiku may want ELFOSABI_STANDALONE or a custom value. **Mitigation:** ignore for kernel module path. Revisit during Haiku port.

4. **`ail_main` signature must be `int (void)`.** The shim declares `extern int ail_main(void)`. If AiLang-emitted `ail_main` takes arguments or returns non-integer, the call from `ail_shim_init` is UB. **Mitigation:** CLI validates `ail_main` has zero params and `Output: Integer`; fail at compile time otherwise.

5. **Recursive self-calls through PLT.** If AiLang-emitted code does `Function.foo` calling `foo()` recursively, that should NOT go through PLT (it's an internal call, not external). **Mitigation:** Step 4 only emits reloc records when the callee is `EXTERN_KFUNC` kind. Internal calls stay direct-relative as today.

6. **WSL verification ceiling.** Can't actually load the module to confirm runtime correctness. A bytes-clean object that passes all `readelf` / `ld -r` checks is the strongest WSL-side guarantee. Real verdict comes from the Linux-box load test.

---

## Stretch goals (after main path lands)

- `ail_register_chrdev` / `ail_unregister_chrdev` in the shim, to actually do something non-trivial from a payload.
- A simple Haiku port: reuse everything from Step 2 onward, swap shim for a C++ file wrapping BWindow/BApplication. First target: "hello world window from AiLang."
- Two-module variant (Option B): shim as its own `.ko` with `EXPORT_SYMBOL`, payload as a separate `.ko` that depends on it. Useful for keeping the shim loaded across multiple payload modules. Not needed for first cut.
