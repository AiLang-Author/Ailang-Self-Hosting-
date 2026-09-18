# compiler-improvement — status and punch list

**Merged to `master` (Sep 2026).** The freeze below is historical. Current
`./ailang.x` is the promoted self-host (FPU Concat/Tan/Atan2/FMA, Hardware
CPUID, Assemble wrap). Rebuild with `./ailang.x ailang_cli.ailang ailang-next.x`.

This is the briefing for what landed, what was already fixed, and what is still open.

---

## Host — frozen (branch era; no longer policy)

| File | Role |
|------|------|
| `./ailang.x` | Host compiler. Builds `-next` binaries. Do not rebuild. |
| `./analyzer.x` | Host analyzer. Do not rebuild. |
| `./cad_app.x` | Shipping CAD. Do not rebuild from this branch. |

SHA-256 at branch start:

```
ailang.x    9d7f005a88cd075312d370b0b94d58929825dd22b9b31bc84ee913b0cb3cb87f
analyzer.x  43a7b024bbe6f61a1d084f57b18942f9acaa62ccda7fd906d312df4e5ae1efe8
```

```
sha256sum ailang.x analyzer.x
```

---

## Next — this branch's products

```
./ailang.x ailang_cli.ailang ailang-next.x
./ailang.x Applications/Analyzer/ailang_analyzer.ailang analyzer-next.x

./ailang-next.x ailang_cli.ailang ailang-next2.x
./ailang-next2.x ailang_cli.ailang ailang-next3.x
```

`*.x` is gitignored except the pinned host `ailang.x`.

Gates:

```
./tools/contract_identity.sh    # tiny fixtures, negatives, pool string, ReturnValue
./tools/demo_identity.sh        # Demo Programs/programs/*.ailang host vs next cmp
```

Unchanged legal programs must be byte-identical host vs next when the codegen path has not moved (`true.ailang`, demos). `ailang_cli.ailang` / analyzer sources will differ — this branch adds code to them. `ailang-next2.x` vs `ailang-next3.x` must be identical (fixed point).

---

## Landed on `-next`

### File-scope contract

Only declarations at file scope, plus `RunTask` in the **main** module and `Debug` blocks (NOP unless `-D`). Assignments, `PrintMessage`, `IfCondition`, and library `RunTask` abort before codegen — they used to emit onto `_start` with no stack frame.

Shared allow-list: `Librarys/Library.ContractCheck.ailang`. Compiler: `Sem_Analyze`. Analyzer2: errors, CLI exit 2.

Parser still accepts statements so the analyzer can name the node. Do not reject at parse.

### Arity and Output

More than 6 `Input:` abort (SysV; 7th was dropped). Two `Output:` on one function abort.

### Duplicates

| Where | `-next` |
|---|---|
| Same file | **abort** |
| Different files after import concat | **warning**, first wins |

### Nested call-args

Analyzer warning only (`Use(Add(1, 2))`). Compiler still accepts. Flatten into a named local.

### Analyzer hygiene

Pass 1 header no longer claims `AnalyzeFile` or owning the pipeline. Report strings do not put `()` in literals. Nesting-depth warning runs from `PostAnalysis`. Builtins include `ProcessExit`, `HaltProgram`, `RunTask`, `Arena_Init`, `Float_*`. Dead `LibraryImport.DiagnosticStore` removed from Pass 1.

### Import prefixer

`Import_GetPrefixedFor` used to rewrite every conflicting symbol to the **first** module's `NS*` name, so two `Function.X86_AndRaxImm8` both became `NS000005_X86_AndRaxImm8`. It now prefers **this module's** prefix for that module's defs and calls; outsiders still get the first prefix. Compiling `ailang_cli.ailang` with `-next` no longer emits those duplicate warnings.

### Demos

`067_fork_not_switch`, `068_fork_branch_combinatorial`, `096_void_function` driver logic moved into `SubRoutine.Main`. `./tools/demo_identity.sh`: **146/146 identical**.

---

## Proven already fixed (no new warning)

These were punch-list items from April 2026 notes. Both the August host and `-next` already do the right thing. Analyzer warnings would be false positives.

### FixedPool `Initialize="string"`

`tests/contract/pool_string_init.ailang`: `Initialize="hello"` and `Initialize=""`.

- host vs next ELF identical
- run: `hello=hello`, first byte 104, empty length 0, not a null pointer

Codegen: `is_string` + `Emit_LoadDataAddress` into the R15 slot. The CoreUtils/`wc` NULL-slot bug is gone.

### `ReturnValue` in `ThenBlock`

`tests/contract/ret_in_then.ailang`: Fib with `ReturnValue(n)` in the `n < 2` ThenBlock.

- `Fib(7)` = 13, `ClampNeg(-5)` = 0
- host and `-next` both exit 0

Codegen already JMPs to the function epilogue.

---

## CAD identity

```
./ailang.x      CAD/cad_app.ailang cad_app-host.x    # August host — will diverge
./ailang-next2.x CAD/cad_app.ailang cad_app-sg.x
./ailang-next3.x CAD/cad_app.ailang cad_app-sg-b.x
```

| Pair | Result |
|---|---|
| August `ailang.x` vs current | diverges — old backend |
| Tiny programs / demos | identical |
| `next2` vs `next3` compiling CAD | **identical** (`cad_app-sg.x` / `cad_app-sg-b.x`) |
| `cad_app-sg.x` vs earlier `cad_app-next.x` (pre-prefixer) | diverges — emit helpers bind per-module |

Shipping `cad_app.x` / `CAD/cad_app.x` not written.

---

## DiagnosticStore

`Librarys/Library.DiagnosticStore.ailang` is a finished JSON bag (`DiagStore.Add` / `ToJSON` / `PrintConsole`). Header: shared contract for analyzers, console, LSP, IDE. Harness: `dev/compiler-regression/diagstore_test_harness.ailang`.

No design doc. Nothing calls it except that harness. Pass 1 used to import it and never referenced `DiagStore`. `ailang_lsp.ailang` emits its own `"diagnostics"` array. The dead import is gone. Library stays for a later consumer. The harness has file-scope driver code, so `-next` will not compile it until wrapped in `Main`.

---

## Float_Sin / Float_Cos

Implemented on `-next` in `Library.FPUCompileX86Trans.ailang`. Does **not** edit `CEmitX86Enc.ailang` (auto-generated). Emit uses `X86Enc_Assemble` for xmm-xmm ops plus existing SSE stack helpers.

Shared `Trans_ReduceFromRax` (Cody-Waite two-part π/2). Sin: k 0/2 sin poly, 1/3 cos poly, negate if k≥2. Cos: k 0/2 cos poly, 1/3 sin poly, negate if k is 1 or 2.

- Taylor Horner through x^15 / x^16
- ±0, ±Inf, NaN
- Wrong arity rejected
- `python3 tools/test_float_sin.py` and `tools/test_float_cos.py` vs libm (all pass)

Tan / Atan2 / Exp / Log / Pow still stubs.

## Migrating specialty emitters onto CEmitX86Enc

`Library.CEmitX86Enc.ailang` is auto-generated (`tools/gen_x86enc.py`). Do not hand-edit it. Call `X86Enc_Assemble("ADDSD xmm0, xmm1")` from compile modules.

Today: hand-written `CEmitX86*` / `FPUEmitX86*` plus Enc. Float_Sin/Cos are the first compile path that prefers Enc for xmm-xmm.

Do this **one compiler module at a time**:

1. Pick a module (e.g. `FPUCompileX86SSE` binops or `CCompileArith`).
2. Replace register-register helpers with `X86Enc_Assemble`.
3. Leave memory forms (`[rsp]`, `[rax]`, rip-relative) on old helpers until Enc's parser grows `[reg]` / `[reg+disp]` — `X86Enc_ParseAsm` currently stops at `[`.
4. Rebuild `-next`, `cmp` a tiny program + CAD same-gen, run that module's tests.
5. Delete a specialty helper only when `grep` shows zero call sites.
6. Last: FPUEmit, then CEmitX86Arith/Reg/Mem. Jump/fixups stay special — Enc does not emit reloc labels.

Parser gap is the blocker for "all emit through Enc." Extend `tools/gen_x86enc.py` / ParseAsm for memory operands; do not patch the 53k generated file by hand.

Full inventory (every `Function.*`, classes A/B/C, order): `docs/compiler/EMIT_MIGRATION.md`.

## Remaining punch list

1. **Wire DiagnosticStore** — four analyzer passes + CLI + LSP onto `DiagStore.Add` / `ToJSON`. Wrap the harness in `SubRoutine.Main` so it compiles under `-next`. This is the only leftover "we built it and never plugged it in."

2. **Parser-level reject of file-scope statements** — skip unless asked. Semantic abort is the gate; parser reject would skip the rest of the file and lose FileMap diagnostics.

3. **Full type-checking in `Sem_Analyze`** — skip unless asked. Contract walk is live; undefined-var / type mismatch was never live despite old docs.

4. **Libraries = pure Functions only** — skip. Would reject the self-hosting compiler (`FixedPool`, `SubRoutine` in `Librarys/`).

5. **Promote `-next` to a same-generation host** — decision, not a patch. Freeze a new `ailang.x` from this branch when you choose. Until then August host vs current CAD keeps diverging.

6. **Old libraries with file-scope code** — Motion/GCode banners, MessageQueue `x = 0`, media demuxers with `RunTask`. Host still compiles them; `-next` will not. Not on the compiler import graph.

7. **DiagStore harness Main-wrap** — same as the three demos; only needed if you want that test under `-next`. Subset of item 1.

---

## Rebuild / recheck

```
sha256sum ailang.x analyzer.x
./ailang.x ailang_cli.ailang ailang-next.x
./ailang.x Applications/Analyzer/ailang_analyzer.ailang analyzer-next.x
./ailang-next.x ailang_cli.ailang ailang-next2.x
./ailang-next2.x ailang_cli.ailang ailang-next3.x
./tools/contract_identity.sh
./tools/demo_identity.sh
```
