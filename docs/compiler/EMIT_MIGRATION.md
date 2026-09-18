# Specialty emitters → CEmitX86Enc

Inventory for migrating hand-written `X86_*` / `Emit_*` helpers onto the generated encoder. Do **not** hand-edit `Library.CEmitX86Enc.ailang` (53k lines, `tools/gen_x86enc.py`). One compile/emit module at a time: change, rebuild `-next`, identity + tests, then the next file.

`Function.*` is the unit of work. Counts below are `^Function.` in each library.

---

## Layer cake (today)

```
CCompileArith / CCompileStmt / …     compile modules
        │
        ▼
Emit_*  (CEmitCoreArch, 382)         if x86 then call X86_*
        │
        ▼
X86_*   (CEmitX86*, FPUEmit*, ~633)  hand-encoded bytes
        │
        ▼
Emit_Byte / labels / fixups          CEmitCore (keep forever)
```

FPU compile modules (`FPUCompileX86SSE`, `Trans`, …) skip `Emit_*` and call `X86_*` directly.

`CEmitX86Enc` public API (leave generated):

| Function | Role |
|---|---|
| `X86Enc_Assemble` | mnemonic string → bytes |
| `X86Enc_ParseAsm` | `"ADDSD xmm0, xmm1"` → key + operand nums |
| `X86Enc_Emit` / `X86Enc_Lookup*` | table (do not touch) |

Sin/Cos already call `X86Enc_Assemble` for xmm-xmm. That is the pattern: **one less specialty opcode**, same compile module.

---

## What stays out of Enc (class C)

These are not “another opcode.” They are compiler machinery. Keep them as a **small dedicated helper library** (today: pieces of `CEmitCore` + `CEmitX86Jump` + `CEmitX86Mem` data/RIP). Do not cram them into the generated file.

| Kind | Examples | Why not Enc |
|---|---|---|
| Buffer / labels / fixups | `Emit_Byte`, `Emit_CreateLabel`, `Emit_MarkLabel`, `Emit_AddFixup`, `Emit_ResolveFixups`, `Emit_AddData`, RIP `LoadDataAddress` | relocs, ELF layout |
| Label jumps | `X86_Jmp(label)`, `X86_Je(label)`, `X86_Call(label)`, `X86_LeaRaxLabel` | 32-bit displacement patched later |
| Frame composites | `X86_Prologue`, `X86_Epilogue`, `X86_PushVolatile`, `EMIT_SAVE_STRING_REGS` | several instructions + policy |
| XMM stack composites | `X86_PushXMM0` = `SUB RSP,8` + `MOVSD [RSP], XMM0` | two ops; can become two Assemble calls **after** mem parse |
| Arch switch | `Emit_*` in CoreArch (`if Emit.target == x86`) | HDL vs x86 |
| HDL | `EmitVerilogHDL`, `EmitJsonHDL`, `EmitSdcHDL` | not x86 |

If Enc grows `[reg]` / `[reg+disp]` in **`tools/gen_x86enc.py` + ParseAsm**, class B (memory) moves to Enc. Fixups still never live in the generated table.

**LOCK** cmpxchg/xadd: Enc may already have `LOCK CMPXCHG`. Treat as class A once a probe Assemble works; otherwise keep the three `X86_Lock*` helpers.

---

## Totals

| Bucket | `Function.*` | Notes |
|---|---|---|
| Specialty `X86_*` (CEmitX86* + FPUEmit*, not Enc) | **~633** | migration candidates |
| `CEmitCoreArch` `Emit_*` | **382** | wrappers; bodies become Assemble or stay as `X86_*` calls |
| `CEmitCore` | **37** | class C, keep |
| `CEmitX86Enc` | **111** | generated lookup + Assemble; keep |
| Compile modules (x86, not HDL, not SysDispatch) | **~250** | consumers; most already use `Emit_*` |
| `CSysDispatch` | 362 | syscall names, not emit |
| HDL compile/emit | ~200 | out of scope |

Enc-ready **now** (reg-reg, reg-imm, xmm-xmm, push/pop, ret, nop, cpuid): roughly **half** of the 633. Memory and label ops wait.

---

## Specialty emit libraries (the list)

### GPR — class A first (swap body to Assemble, keep the `Function.X86_*` name)

**`CEmitX86Reg.ailang` (118)**  
Class A: `X86_MovRegReg`, `X86_MovRaxRbx` … all `MovR*R*`, `XorR*R*`, `XorRegReg`, `MovRaxImm64` … `MovR15Imm64`, `MovRax1`, `MovRaxNeg1`, `IncR8`, `DecR8`, `TestR8R8`, `OrRaxRdx`, `ShlRdxImm8`, `DivRcx`.  
Class B: `MovRaxDerefRsp`, `MovClDerefRsi`, `MovDerefRbxRcx`, `MovRcxDerefRbx`.  
Class C: none beyond using `MovRegReg` as the primitive.

**`CEmitX86Arith.ailang` (54)**  
Class A: `Add*`/`Sub*`/`Imul*`/`MulRbx`/`Neg*`/`Inc*`/`Dec*`/`Cqo`/`Idiv*`/`DivRbx`/`ShrRaxImm8`/`AndRaxImm8`/`AddAlImm8`/`SubAlImm8`.  
Duplicates of Logic (`AndRaxImm8`, `ShrRaxImm8`) — prefixer already splits; delete the extra copy when both bodies are Assemble.

**`CEmitX86Logic.ailang` (30)**  
Class A: `And/Or/Xor/Not/Shl/Shr/Sar/Rol/Ror/Bt*`.  
Class C or probe: `LockCmpxchgDerefRdiRsi`, `LockXaddDerefRdiRsi`, `XchgDerefRdiRsi` (LOCK + mem). `AndRspAlignment` / `AndRspImm8` (stack policy). `Mfence` → Sys.

**`CEmitX86Cmp.ailang` (43)**  
Class A: `CmpRaxRbx`, `CmpRaxImm8/32`, `TestRaxRax`, `Sete`/`Setne`/…  
Class B: `CmpByteDeref*`.  
Aliases: `TestRAX_RAX`, `CmpRAX_0` — same as Test/Cmp.

**`CEmitX86Stack.ailang` (48)**  
Class A: `PushRax`…`PushR15`, `PopRax`…`PopR15`, `SubRspImm8/32`, `AddRspImm8/32`, `Leave`.  
Class B: `MovRaxRsp24`, `MovzxRaxRspR8`, `LeaRsiRspR8`.  
Class C: `Prologue`, `Epilogue`, `PushVolatile`, `PopVolatile`, `PushCalleeSaved`, `PopCalleeSaved`.

**`CEmitX86Sys.ailang` (28)**  
Class A: `Nop`, `Nop2`, `Nop3`, `Int3`, `Ud2`, `Clc/Stc/Cmc/Cld/Std`, `Lahf/Sahf`, `Pushfq/Popfq`, `CmoveRaxRbx`…, `Cpuid`, `Rdtsc`, `Rdtscp`, `Mfence/Lfence/Sfence`.  
Class C: `NopN`, `AlignCode` (loops / padding policy).

**`CEmitX86String.ailang` (22)**  
Class A: `RepMovsb`, `RepStosb`, `RepMovsq`, `RepStosq`, `RepeCmpsb`, `RepneScasb`, `CmpAlBl`, `TestAlAl`.  
Class B: `MovAlDerefRdi`, `MovDerefRdiAl`, …

**`CEmitX86Helpers.ailang` (10)**  
Thin aliases of Arith/Reg/Mem. Fold into Assemble or delete when unused.

**`CEmitX86FixedPoint` via FPUEmit (15)**  
Class A: `ImulRbx128`, `ShrdRaxRdxImm8`, `Cqo`, `IdivRcx`, `ShlRaxImm8`, `SarRdxImm8`, `Movsxd*`.

### GPR/mem — class B until ParseAsm learns `[reg]` / `[reg+disp]`

**`CEmitX86Mem.ailang` (71)** — almost all `[rbp+off]`, `[r15+off]`, `[rax]`, RIP data.  
Class C forever: `LoadDataAddress`, `MovRaxDataOffset`, `LeaRaxRipOffset` (fixup).

**`CEmitX86Jump.ailang` (32)**  
Class A: `Ret`, `RetImm16`, `JmpRax`, `CallRax`.  
Class C: `Jmp(label)`, `Jcc`, `Je`…, `Call(label)`, `LeaRaxLabel`, `Loop*` (fixup).  
`JmpShort` only if displacement known at emit time.

**`CEmitX86Macros.ailang` (32)**  
Class C composites (`EMIT_SAVE_STRING_REGS`, …). A few `MovzxRaxByteDeref*` are class B.

### SSE/AVX — start here (Sin/Cos already did xmm-xmm)

**`FPUEmitX86SSE.ailang` (39)**  
Class A (Assemble today): `ADDSD/SUBSD/MULSD/DIVSD/MINSD/MAXSD xmm0,xmm1`, `SQRTSD xmm0`, `ADDPD`…, `UCOMISD`, `CVTSI2SD xmm0,rax`, `CVTSD2SI rax,xmm0`, `MOVSD xmm0,xmm1`, `MOVQ xmm0,rax` / `rax,xmm0`, `PXOR xmm0,xmm0`, `SHUFPD`, `UNPCK*`, `HADDPD`.  
Class B: `MOVSD xmm0, [rsp]`, `[rax]`, `[rbp+off]`.  
Class C composite: `PushXMM0` / `PopXMM0` / `PushXMM1` / `PopXMM1` (until mem parse, or two Enc ops + `SUB RSP,8`).

**`FPUEmitX86AVX.ailang` (49)**  
Class A: `VADDSD xmm0,xmm0,xmm1`, `ROUNDSD`, `DPPD`, `VZEROUPPER`, `VFMADD231SD`, `MOVDQA xmm,xmm`, `PCMPEQD`, …  
Class B: `MOVDQU xmm0, [rax]`, `VBROADCASTSD xmm0, [rax]`.

**`FPUEmitX86MemOps.ailang` (47)**  
String/SIMD mem: mostly class B + a few GPR `IncRSI`, `BSF` (class A).

---

## Compile modules (consumers)

Most **do not** call `X86_*`. They call `Emit_*`. Changing a `X86_*` **body** to Assemble updates every consumer with no compile-module edit.

| Module | `Function.*` | Talks to emit how | Convert when |
|---|---|---|---|
| `FPUCompileX86Trans` | 18 | Assemble already (Sin/Cos) | done for Sin/Cos |
| `FPUCompileX86SSE` | 13 | `X86_*` direct | **1st** after this doc |
| `FPUCompileX86AVX` | 13 | `X86_*` | after SSE |
| `FPUCompileX86MemOps` | 5 | `X86_*` | after mem parse |
| `FPUCompileX86String` | 9 | `X86_*` | with MemOps |
| `FPUCompileX86FixedPoint` | 3 | `X86_*` | with Arith |
| `CCompileArith` | 10 | `Emit_*` | after Arith `X86_*` bodies |
| `CCompileCompare` | 8 | `Emit_*` | with Cmp |
| `CCompileLogic` | 4 | `Emit_*` | with Logic |
| `CCompileBitwise` | 7 | `Emit_*` | with Logic |
| `CCompileStmt` | 17 | `Emit_*` + InlineAsm already Assemble | jumps stay fixup |
| `CCompileFunc` | 24 | `Emit_*` | prologue class C |
| `CCompileMem` / Pool / Array / IO / String* | — | `Emit_*` | mem class B |
| HDL `*` | — | Verilog/JSON | never Enc |
| `CSysDispatch` | 362 | syscalls | not emit |

---

## Recommended mechanics (chat conclusion)

**Keep the `Function.X86_AddRaxRbx` names.** Swap the body:

```
Function.X86_AddRaxRbx {
    Body: { X86Enc_Assemble("ADD rax, rbx") }
}
```

Compile modules stay on `Emit_AddRaxRbx` → `X86_AddRaxRbx`. No 382-wrapper rewrite. Grep still finds the helper until the last call site is gone; then delete the file.

**Do not** dump fixups into Enc. If we need a place for “not a simple opcode”:

- `CEmitCore` — bytes, labels, fixups, data (already)
- `CEmitX86Jump` — label-bearing Jcc/Call (thin, keep)
- Optional later: `CEmitX86MemAsm` only if ParseAsm never grows `[reg]`

**Do not** patch the 53k file for one missing form. Add it in `tools/gen_x86enc.py` (memory operand tokens) and regenerate.

**Identity gate** after each helper or each file: `tools/contract_identity.sh`, `tools/test_float_sin.py`, `tools/test_float_cos.py`, and when touching GPR: `true.ailang` host vs next (path must still be identical if codegen bytes match). If Assemble encoding differs by a prefix byte, `cmp` will fail — then fix the Assemble string, don’t dual-maintain.

---

## Suggested order (one at a time)

1. **`FPUEmitX86SSE` class A** — ADDSD/MULSD/… already used by Sin/Cos via Assemble; point the old `X86_ADDSD_XMM0_XMM1` bodies at Assemble, grep, identity.
2. **`FPUCompileX86SSE` binops** — already call those helpers; should be a no-op if step 1 is done.
3. **`CEmitX86Arith` + `CEmitX86Reg` MovRegReg / Xor / Imm64**
4. **`CEmitX86Logic` / `Cmp` / `Stack` push-pop**
5. **`CEmitX86Sys` nops/fence/cpuid**
6. **ParseAsm `[reg]` / `[reg+disp8]` in the generator**
7. **`CEmitX86Mem` + SSE deref + PushXMM as two Enc ops**
8. Leave Jump-to-label, RIP data, Prologue, Core, Enc itself.

Stop after each numbered step. Rebuild `-next`. Run the gates. Then the next number.

---

## Live call-site ledger

Itemized: `docs/compiler/X86_CALLSITES.txt`

**340 sites / 143 names** in compile+debug (excludes helper *definitions*, generated CoreArch, `.hand` input, HDL).

| File | Sites | Notes |
|---|---|---|
| `FPUCompileX86String` | 86 | string/SIMD mem + BSF |
| `FPUCompileX86AVX` | 57 → xmm-xmm Assemble, deref/PushXMM kept | SSE4.1/FMA exist but **baseline ISA is SSE2**; no CPU dispatch yet |
| `FPUCompileX86MemOps` | 56 | mostly mem |
| `FPUCompileX86SSE` | 55 → **Push/Pop XMM only** after first sweep | class A → `Trans_Asm` |
| `FPUCompileX86Trans` | 35 | Sin/Cos already Assemble; leftover GPR/mem |
| `FPUCompileX86FixedPoint` | 23 | imul/idiv/shift |
| `CCompileDebug` | 17 | nop/int3 |
| `CEmitDebugX86` | 11 | nopN |

CoreArch keep wrappers (~145 `X86_*` in the generated dispatcher) are **not** this ledger; they are the Emit_* → keep-helper layer.

---

## Keep partition (then delete the cornucopia)

Yes. **Partition what cannot fold into Enc, then delete every old `CEmitX86*` / `FPUEmit*` file.** Do not leave 12 half-dead libraries. The keepers are classified by *why* they are not Assemble, not by historical filename.

After the generated CoreArch wrap, grep still finds **~300 `X86_*` call sites** (CoreArch keeps + FPU compile calling SSE helpers directly). Those bodies still live in the old emit files. Until they move, the files are not dead.

### Four keep modules (hand)

| Module | Why Enc cannot own it | What goes in |
|---|---|---|
| **`CEmitFixups.ailang`** | needs `Emit_AddFixup` / label ids | `Jmp/Je/…(label)`, `Call(label)`, `LeaRaxLabel`, RIP `Lea*RipOffset`, `LoadDataAddress*` |
| **`CEmitMem.ailang`** | ParseAsm stops at `[` | `[rsp]`, `[rax]`, `[rbp+off]`, `[r15+off]`, byte deref, lock cmpxchg. **Dies** when `gen_x86enc.py` grows `[reg]` / `[reg+disp8]` |
| **`CEmitFrame.ailang`** | composites / policy | `Prologue`, `Epilogue`, push/pop volatile, callee-saved, `AndRspAlignment` |
| **`CEmitEncGaps.ailang`** | Enc table quirks | `RET`, `SYSCALL` (keys are `RET_`/`SYSCALL_`), `REP MOVSB` (no Enc form). **Dies** when generator emits those keys |

**Runtime-reg** (`AddRegReg(dst,src)`, `MovRegReg`): not Enc’s problem. Small helper in CoreArch (or Frame) that maps reg id → `"rax"` and `Assemble("ADD " + dst + ", " + src)`. Then **no** `X86_AddRegReg` file.

**SSE**: FPU compile still calls `X86_ADDSD_XMM0_XMM1` etc. Point those 39/49 functions at Assemble (same as Sin/Cos) **or** change FPU compile to `X86Enc_Assemble` / `Emit_*`. Then `FPUEmitX86SSE/AVX` die. Deref SSE waits on Mem.

**CEmitCore** (bytes, labels, fixup list, data section) stays forever. Not an ISA encoder.

### Delete list (after partition + grep zero)

`CEmitX86Reg`, `Arith`, `Logic`, `Cmp`, `Sys`, `Helpers`, `Macros`, `String`, `Stack` (if frame absorbed), `Jump` (if fixups absorbed), `Mem` (when ParseAsm has `[reg]`), `FPUEmitX86SSE`, `AVX`, `MemOps`, `FixedPoint`.

`CEmitX86Enc` stays (generated). `CEmitCoreArch` stays (generated). `.hand.ailang` is generator input only.

### Order

1. EncGaps: wrap RET/SYSCALL/REP as the 5 leftover opcodes (or fix `gen_x86enc.py` zero-operand `_` suffix).
2. Runtime-reg Assemble helper; delete those `X86_*`.
3. SSE xmm-xmm → Assemble; FPU compile keeps working.
4. Copy remaining Jump/Mem/Frame bodies into the three keep files; retarget CoreArch imports; **grep `X86_` in old files = only definitions**; delete old files.
5. Later: ParseAsm `[reg]` → drain Mem into Enc → delete `CEmitMem`.

Identity after each step (`true`, hello, sin/cos). CAD `cmp` when a keep file moves.

---

## Deprecated emit files (2026-09-17)

Moved off the import graph to `Librarys/Compiler/Deprecated/`:

- `CodeEmit/X86/` — 11 files (`CEmitX86Reg/Arith/Logic/Cmp/Jump/Stack/Mem/Sys/String/Helpers/Macros`)
- `Compile/FPU/X86/` — 4 `FPUEmit*` files
- `Debug/X86/CEmitDebugX86.ailang`

Live emit is now:

| File | Role |
|---|---|
| `CEmitX86Enc.ailang` | generated assembler |
| `CEmitCoreArch.ailang` | generated `Emit_*` (Assemble or Keep) |
| `CEmitKeep.ailang` | ~200 remaining hand helpers (mem, fixups, frame, Enc gaps) |
| `CEmitCore.ailang` | bytes/labels/fixup list |

Compiler import count 97 → 82. `ailang-next.x` ~3.28MB → ~3.22MB (compiler itself, not user programs).

Trap: `Emit_AndRspImm8(240)` must stay sign-extended imm8 (`AND rsp, -16`). Assemble(`AND rsp, 240`) zero-extends and destroys RSP — Functions SIGSEGV. Generator keeps all `AndRsp*`.

---

## Status (generated wrap)

`tools/gen_corearch.py` reads `Library.CEmitCoreArch.hand.ailang` and writes `Library.CEmitCoreArch.ailang`.

- **237** `Emit_*` → `X86Enc_Assemble` (class A)
- **~145** keep `X86_*` (jumps/labels, mem/deref, runtime-reg, prologue, REP string, RET/SYSCALL because Enc zero-operand keys are `RET_` / `SYSCALL_` and Assemble looks up `RET` / `SYSCALL`)
- Enc file not modified
- Rollback of this wrap: `git checkout 81cdf0ed -- Librarys/Compiler/CodeEmit/Library.CEmitCoreArch.ailang`
- Gated: `true.ailang` runs, hello prints, `test_float_sin.py` / `test_float_cos.py` pass

Re-run: `python3 tools/gen_corearch.py` then rebuild `-next`.

---

## Generating CoreArch (and ARM later)

Yes: **class A (and later B) CoreArch wrappers can be generated.** Class C cannot. That is how you delete the cornucopia without a 633-file hand rewrite.

### What is already mechanical

`CEmitCoreArch` is already a dispatcher:

```
Function.Emit_MovRbpRsp {
    Body: {
        IfCondition EqualTo(Emit.target, 1) ThenBlock: {
            X86_MovRbpRsp()
        }
    }
}
```

`Arch.ARM64` is defined (`Initialize=2`) but **no `ARM_*` bodies exist**. Every wrapper is `if target == 1` only.

A table row is enough for class A:

| emit_name | args | x86_asm | arm_asm |
|---|---|---|---|
| `Emit_AddRaxRbx` | — | `ADD rax, rbx` | `ADD x0, x0, x1` |
| `Emit_SubRaxImm8` | `val` | `SUB rax, {val}` | `SUB x0, x0, {val}` |
| `Emit_AddSD` | — | `ADDSD xmm0, xmm1` | `FADD d0, d0, d1` |

`tools/gen_corearch.py` (new, like `gen_x86enc.py`) emits `CEmitCoreArch.ailang`:

```
Function.Emit_AddRaxRbx {
    Body: {
        IfCondition EqualTo(Emit.target, 1) ThenBlock: {
            X86Enc_Assemble("ADD rax, rbx")
        }
        IfCondition EqualTo(Emit.target, 2) ThenBlock: {
            ArmEnc_Assemble("ADD x0, x0, x1")
        }
    }
}
```

Immediates must be **flattened** Ailang (no nested `Assemble(StringConcat(...))`):

```
asm = "SUB rax, "
n = NumberToString(val)
asm = StringConcat(asm, n)
X86Enc_Assemble(asm)
```

Then **`X86_AddRaxRbx` is unused** and the specialty file can die once grep is empty. Compile modules keep calling `Emit_*`. That is the whole point of CoreArch.

Do **not** generate Enc itself from this table. Enc stays the x86 opcode table (Maratyszcza XML). ARM needs its own `ArmEnc` from an AArch64 table (separate generator). CoreArch is the **only** file that should know both mnemonics.

### What you must not generate from Enc

Same class C as above: `Emit_Jmp(label_id)`, `Emit_Je`, `Emit_Call`, `Emit_LeaRaxRip`, `Emit_Prologue`, `Emit_Byte`, fixups. Keep those in a **hand** file, e.g. `CEmitCoreArchFixups.ailang`, not in the generator output. Mix: generated CoreArch + small fixup module.

Memory forms wait on ParseAsm `[reg]` in **`gen_x86enc.py`**, then add rows to the CoreArch table (`MOV rax, [rsp]`).

### ARM is not “the same table with different bytes”

The `Emit_*` **names are x86 registers** (`Emit_MovRbpRsp`, `Emit_AddRaxRbx`). ARM has `x29`/`sp`, not RBP/RSP.

Three ways, increasing honesty:

1. **Fixed map** (generator only): RAX→X0, RBX→X1, … RBP→X29, RSP→SP, XMM0→D0. SysV vs AAPCS will fight (RDI is arg0 on x86, X0 on ARM). Compile modules that mean “first argument” already used RDI because they were written for x86. A map papers over that until something uses a register for its x86 ABI role.
2. **Virtual regs** in compile modules: `Emit_Mov(Reg.RET, Reg.ARG0)` and CoreArch maps RET/ARG0 per ISA. That’s a compile-module rename, not just a generator. Right long-term.
3. **Don’t pretend CoreArch is ARM-ready** until (2). Generate x86 Assemble wrappers **now** (delete specialty modules). Add ARM rows when you have `ArmEnc` and a real reg map.

(1) is enough to **prove** the generator. (2) is what ARM actually needs. Do not block x86 debt-pay on ARM.

### Suggested generator pipeline

```
emit_ops.csv          # class A/B rows only
        │
        ▼
gen_corearch.py  →  Library.CEmitCoreArch.ailang   (DO NOT EDIT)
gen_x86enc.py    →  Library.CEmitX86Enc.ailang     (already)
gen_armenc.py    →  Library.CEmitArmEnc.ailang     (later)
        │
        ▼
CEmitCoreArchFixups.ailang   # hand: jumps, RIP, prologue
CEmitCore.ailang             # hand: bytes, labels, fixup list
```

Identity: generated CoreArch must `cmp` the same ELFs as the hand wrappers for class A ops. If Assemble emits an extra REX, fix the mnemonic string in the CSV, regenerate, don’t patch Enc.

---

## Already using Enc

- InlineAsm mnemonic path (`CCompileStmt` → `X86Enc_Assemble`)
- `Trans_Asm` in `FPUCompileX86Trans` (Float_Sin / Float_Cos)
