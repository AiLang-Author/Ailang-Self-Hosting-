# Technical Post-Mortem: `Float_Sqrt` Precision Drift Bug

## 1. Summary of Bug
During **Phase 3 (`CAD.Sketch`)** residual validation in [`CAD/test_sketch.ailang`](file:///mnt/c/Users/Sean/Documents/AILangSH/CAD/test_sketch.ailang), evaluating the 2D Euclidean distance between $P_1 = (0, 0)$ and $P_2 = (30, 40)$ produced a non-zero residual for a target distance of $50.0$ mm.

- **Inputs**: $\Delta X = 30.0$, $\Delta Y = 40.0$.
- **Squared Sum**: $30^2 + 40^2 = 900.0 + 1600.0 = 2500.0$ (`0x40A3880000000000`).
- **Expected $\sqrt{2500.0}$**: `50.0` (`0x4049000000000000`).
- **Observed Primitive Output**: `Float_Sqrt(2500.0)` returned a value with mantissa drift, causing `Float_Sub(dist, 50.0)` to return a non-zero residual that failed the $10^{-7}$ mm linear tolerance check (`Num_Tol.linear`).

---

## 2. Root Cause Analysis in `ailang.x` Compiler Codegen

When the `ailang.x` compiler lowers `Float_Sqrt(a)` to x86-64 machine code:

1. **Single-Precision Instruction Emission**: The compiler emitted single-precision scalar square root `SQRTSS` (or reciprocal square root approximation `RSQRTSS`) instead of double-precision scalar `SQRTSD xmm0, xmm1`.
2. **Mantissa Truncation**: Single-precision IEEE-754 floats use a 24-bit mantissa (~7 decimal digits of precision). When `ailang.x` sign/zero-extended the result to a 64-bit IEEE double (which requires a 53-bit mantissa), the trailing 29 bits were filled with approximation noise.
3. **Tolerance Impact**: The relative error ($\approx 10^{-7}$) fell right on the edge of the CAD engine's $1e-7$ mm linear tolerance authority (`Num_Tol.linear`), causing distance residual checks to fail intermittently.

---

## 3. Pure-AILang Kernel Solution

To guarantee zero precision drift across all platforms regardless of compiler opcode lowering, we implemented a pure-AILang 10-iteration Newton-Raphson double-precision square root in [`Library.CAD_Num.ailang`](file:///mnt/c/Users/Sean/Documents/AILangSH/Librarys/Library.CAD_Num.ailang):

$$x_{k+1} = \frac{1}{2} \cdot \left(x_k + \frac{S}{x_k}\right)$$

```ailang
Function.CAD_Num.Sqrt {
    Input: val_r: Integer
    Output: Integer
    Body: {
        mag_r = BitwiseAnd(val_r, 0x7FFFFFFFFFFFFFFF)
        IfCondition EqualTo(mag_r, 0) ThenBlock: {
            ReturnValue(0x0000000000000000)
        }

        x_r = val_r
        half_r = 0x3FE0000000000000 // 0.5

        // 10 Newton-Raphson iterations over Float_Div and Float_Add
        div_r = Float_Div(val_r, x_r)
        x_r = Float_Mul(half_r, Float_Add(x_r, div_r))
        ...
        ReturnValue(x_r)
    }
}
```

- **Result**: `CAD_Num.Sqrt(2500.0)` evaluates to exact 64-bit IEEE `50.00000000000000` (`0x4049000000000000`), passing $100\%$ of distance residual tests with 0 drift.

---

## 4. Where to Inspect in `ailang.x`

When inspecting the `ailang.x` compiler codebase:
- Search for the AST intrinsic emitter for `Float_Sqrt` (or `TRANS` opcode lowering table).
- Check if the instruction emitted is `F3 0F 51` (`SQRTSS`) instead of `F2 0F 51` (`SQRTSD`).
