# Math primitives — live vs missing (Sep 2026)

Comb of compiler builtins vs library. Core = one opcode or a short
poly the compiler should emit. Library = assembled from core
(`Hypot`, `Asin`, matrices). Not C math.h.

Integer `Power` is **integer** exponentiation. `Float_Pow` is IEEE
`x^y`. They are not the same.

---

## Integer (always)

| Name | Status |
|------|--------|
| `Add` `Subtract` `Multiply` `Divide` `Modulo` `Negate` | live |
| `Increment` `Decrement` | live |
| `Power(base, exp)` | live, **non-negative exp only**, O(exp) IMUL loop |
| `Abs` `Min` `Max` `ISqrt` | live (SSE dispatcher) |
| aliases `SquareRoot` `IntegerSquareRoot` `AbsoluteValue` `Minimum` `Maximum` | same as ISqrt/Abs/Min/Max — **not** `Float_Sqrt` |

Missing / weak integer: negative `Power`, `Gcd`, `Popcnt`, `Clz`/`Ctz`
(library or later Keep).

---

## Float — live (SSE2 unless noted)

| Name | Notes |
|------|--------|
| `Float_Add/Sub/Mul/Div/Min/Max` | SSE2; `Add(Mul)` fuses to FMA if `Hw.level≥2` |
| `Float_Sqrt` | `SQRTSD` |
| `Float_FromInt` `Float_ToInt` `Float_Round` | Round is SSE2 cvtsd2si path in SSE module; AVX also has Round at level 1 |
| `Float_Eq/Ne/Lt/Gt/Le/Ge` | `UCOMISD`; Le/Lt honest on negatives |
| `Float_Sin` `Float_Cos` `Float_Tan` | Cody–Waite + poly |
| `Float_Atan2(y, x)` | C order, quadrants |
| `Float_FMA/FMS/FNMA` | `Hw.level≥2` |
| `Float_Floor/Ceil/Trunc` | `Hw.level≥1` (SSE4.1 ROUNDSD) |
| `Vec2_Add/Sub/Mul/Dot` | packed double |
| `FixedMul` `FixedDiv` | fixed-point, not IEEE |

---

## Float — stub / absent (compiler)

| Name | Verdict |
|------|---------|
| `Float_Exp` `Float_Log` `Float_Pow` | **live** (poly; Pow is exp(y*ln(x)); x≤0 → NaN) |
| `Float_Abs` `Float_Neg` `Float_Copysign` | **live** |
| `Float_IsNan` `Float_IsInf` `Float_SignBit` | **live** (integer 0/1) |
| `Float_Mod` | **live** (trunc toward zero; y=0 → NaN) |
| unary `Float_Atan` | library: `Atan2(x, 1)` |
| `Float_Asin` `Float_Acos` | library from Atan2 |
| `Float_Hypot` | library: CAD_Num.Hypot2 |
| `Float_Log2` `Float_Log10` `Float_Exp2` | library scale of Log/Exp |
| `Vec3_*` | header lie — dispatcher has Vec2 only |

---

## Core set we should have

Must be compiler (used everywhere, or one ISA insn / short poly):

1. Arithmetic + cmp + sqrt + convert — **done**
2. `Float_Abs` `Float_Neg` `Float_Copysign` `IsNan` `IsInf` `SignBit` `Mod` — **done**
3. `Float_Sin/Cos/Tan/Atan2` — **done**
4. `Float_Log` + `Float_Exp` + `Float_Pow` — **done**
5. `Float_Floor/Ceil/Trunc` — SSE4.1 (`Hw.level≥1`)

Not core (`LibraryImport.Math` — optional, not auto-imported):

- Hypot, Asin/Acos, Atan, Log2/Log10, Cbrt, sincos pair, wrap-to-2π
- V3Dot/Cross/Normalize, LU, Orient — already CAD_Num
- Gamma, erf, Bessel — never unless a caller exists

---

## Traps

- `SquareRoot` → **integer** ISqrt, not `Float_Sqrt`
- `Power` → integer, exp < 0 is an infinite loop / wrong
- `CAD_Num.IsNeg(-0)` is 1 (sign bit). `Float_Abs(-0)` is +0.
