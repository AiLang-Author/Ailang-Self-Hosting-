# FPU compile modules — ISA audit and plan

Pushed with Hardware + `-march=native`. Default compile on a capable CPU (this FX-8320: level 2) emits SSE4.1/FMA only for names that already have bodies. SSE2 remains the portable floor (`-march=sse2`).

FPU is the only compile layer that **gains** from new instructions. GPR Keep (jumps, `AND rsp, imm8`, `CQO`) does not.

---

## Modules

| File | Role | ISA |
|---|---|---|
| `FPUCompileX86SSE` | scalar float arith/cmp/convert, Vec2, integer Abs/Min/Max/ISqrt | SSE2 |
| `FPUCompileX86Trans` | Sin/Cos live; Tan/Atan2/Exp/Log/Pow stubs | SSE2 poly |
| `FPUCompileX86AVX` | Floor/Ceil/Trunc/FMA/Packed_* | gated: need 1 = SSE4.1, need 2 = FMA |
| `FPUCompileX86String` | StringLength/Concat/Compare/Equals/Copy/IndexOf/Contains | SSE2 |
| `FPUCompileX86MemOps` | MemorySet/Copy/Compare/MemChr | SSE2 |
| `FPUCompileX86FixedPoint` | FixedMul/FixedDiv | GPR (`CQO` Keep) |

Dispatch order in `CCompileMain`: SSE → MemOps → String → FixedPoint → AVX.

---

## Live vs stub

### SSE2 — done (generic: `FloatBinOp` / `FloatCmp` + `Trans_Asm`)

`Float_Add/Sub/Mul/Div/Min/Max`, `Float_Sqrt`, `FromInt/ToInt`, `Float_Round` (SSE2 cvtsd2si path), `Eq/Ne/Lt/Gt/Le/Ge`, `Vec2_*`, `Abs/Min/Max/ISqrt` integer aliases.

CAD already uses Add/Sub/Mul/Div/Le heavily. **CAD_Num.Sqrt → Float_Sqrt (`SQRTSD`)** with CAD domain 0 / negative → 0. Old Newton poly retired; compiler SQRTSD is IEEE binary64 (the SQRTSS bug is gone).

### Trans — Sin/Cos done; rest stubs

| Name | Status | Need for CAD |
|---|---|---|
| `Float_Sin` / `Float_Cos` | polynomial + Cody-Waite | CAD_Num still has its own poly |
| `Float_Tan` | sin/cos quotient after reduce | low |
| `Float_Atan2` | poly + quadrants | sketch/tess — CAD_Geom.Atan2 wraps it |
| `Float_Exp` / `Log` / `Pow` | poly + ldexp | core; Pow = exp(y*ln(x)) |

Tan = Sin/Cos ratio after the same reduce. Atan2 is live. Exp/Log/Pow are live (poly; not correctly rounded).

### AVX file — implemented, Hw.level gated

| Names | Need | Instr |
|---|---|---|
| `Float_Floor/Ceil/Trunc` | 1 | ROUNDSD |
| `Float_FMA/FMS/FNMA` | 2 | VFMADD231SD |
| `Packed_MulI32/Min/Max/Abs`, `Packed_Test`, `PMOVSX` | 1 | SSE4.1 |
| `Packed_AddI32/SubI32/Eq/Gt` | 0 | SSE2 PADDD etc. |
| `Float_DotPD` | 1 | DPPD |

`Float_Add(Float_Mul(a,b), c)` **fuses to FMA** when `Hw.level ≥ 2` (this box). SSE2 (`-march=sse2`) keeps MULSD+ADDSD. CAD source unchanged — portable prebuilt still compiles. Explicit `Float_FMA(a,b,c)` remains for opt-in.

`Float_Round` is registered in **both** SSE and AVX. SSE runs first → always SSE2 cvt path. Harmless; AVX Round is dead code unless SSE stops claiming it.

### String / Mem — SSE2, Concat done

FPU String: Length, Concat, Compare, Equals, Copy, IndexOf, Contains. Not Substring.

`StringConcat` is SSE2 strlen + 16-byte copy. **Arena_Alloc** when the program imported Arena (compiler, CAD); **mmap** fallback for tiny programs. mmap-per-concat was the real cost (syscall + 4K leak). Scalar StringCore Concat remains fallback off x86_64.

### FixedPoint — done

FixedMul/Div. Leave it.

---

## Generic compile function

New SIMD names should **not** grow a new emit file.

Pattern already in SSE:

```
FPUCompileX86_FloatBinOp(node, FloatOp.ADD)  →  Trans_Asm("ADDSD xmm0, xmm1")
```

Pattern for gated ops:

```
need = 1 or 2
If GreaterThan(need, Hw.level) → return 0
Trans_Asm("ROUNDSD xmm0, xmm1, 1")
```

One helper: `FPU_EmitBinSD(mnemonic)` / `FPU_EmitUnarySD`. Older GPR encodings stay in **Keep**. Do not “generic-ize” `Je(label)` or `AND rsp, -16`.

---

## Order (by need, this machine)

1. **StringConcat** — done. Arena when present, mmap fallback, SSE2 copy. Not a dispatch miss anymore.
2. **`CAD_Num.Sqrt` → `Float_Sqrt`** — done. SQRTSD, CAD keeps 0 / neg → 0.
3. **`Float_Tan`** — done. Same reduce as Sin/Cos; even quadrant sin/cos, odd −cos/sin.
4. **`Float_Atan2`** — done. Quadrants + reduce + odd Horner. `CAD_Geom.Atan2` wraps it.
5. **CAD hot FMA** — done as compiler fuse of `Float_Add(Float_Mul)` at `Hw.level ≥ 2`. No CAD source rewrite; sse2 portable unchanged.
6. **Exp/Log/Pow** — skip until a caller exists.
7. **AVX-256** — skip on FX-8320 (split 128-bit uops). Never AVX-512 here.

Portable GitHub CAD remains `-march=sse2` when you ship a prebuilt. Local `./ailang.x cad_app.ailang` is native.

---

## What not to do

- Runtime jump tables in `cad_app.x` (bloat).
- Implementing Enc’s 10k forms.
- Rewriting Keep GPR “to be generic.”
- Enabling AVX2/512 on this CPU (unsupported).
