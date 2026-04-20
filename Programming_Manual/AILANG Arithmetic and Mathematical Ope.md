# AILang Arithmetic & Mathematical Operations

## Overview

AILang arithmetic uses named functions as the canonical form. Infix
symbols are syntactic sugar that compile to identical code. Both forms
are always available. See the **Operators Reference** for the complete
operator table — this document focuses on usage patterns and behavior.

---

## Dual Syntax

Every arithmetic operation has both a function form and an infix form:

```ailang
// These produce identical machine code
result = Add(a, b)
result = (a + b)

// Mixed — fully valid
result = Add((a * b), Divide(c, d))
```

**Infix requires explicit parentheses.** Bare `a + b` without parens
is a syntax error. There is no precedence table — the parentheses are
the precedence.

```ailang
// SYNTAX ERROR
result = a + b * c

// CORRECT — intent is unambiguous
result = (a + (b * c))
result = ((a + b) * c)
```

---

## Basic Arithmetic

### Addition

```ailang
result = Add(a, b)
result = (a + b)

Add(10, 5)          // → 15
Add(-10, 5)         // → -5
Add(Add(1, 2), 3)   // → 6   chained
((1 + 2) + 3)       // → 6   chained infix
```

### Subtraction

```ailang
result = Subtract(a, b)
result = (a - b)

Subtract(20, 8)     // → 12
Subtract(5, 10)     // → -5
Subtract(-5, -10)   // → 5
```

### Multiplication

```ailang
result = Multiply(a, b)
result = (a * b)

Multiply(7, 6)      // → 42
Multiply(-3, 4)     // → -12
Multiply(-3, -4)    // → 12
```

### Division

```ailang
result = Divide(a, b)
result = (a / b)
```

Integer division always **truncates toward zero**:

```ailang
Divide(20, 3)     // → 6    (not 7)
Divide(100, 4)    // → 25
Divide(-20, 4)    // → -5
Divide(20, -4)    // → -5
Divide(-20, -4)   // → 5
```

**Division by zero is undefined behavior.** Always validate the
divisor before dividing:

```ailang
IfCondition NotEqual(divisor, 0) ThenBlock: {
    result = Divide(numerator, divisor)
}
```

### Modulo (Remainder)

```ailang
result = Modulo(a, b)
```

Modulo has no infix symbol — `^` is Power in AILang. Use the function
form. With compound assignment use `/=/`:

```ailang
remainder = Modulo(17, 5)    // → 2
Modulo(20, 4)                // → 0   (exact)
Modulo(-17, 5)               // → -2  (sign follows dividend)
Modulo(17, -5)               // → 2

// Compound assignment
i /=/ 8                      // i = Modulo(i, 8)
```

### Power / Exponentiation

```ailang
result = Power(base, exponent)
result = (base ^ exponent)
```

**`^` is Power, not XOR.** This is the most common source of confusion
for developers coming from C/C++.

```ailang
Power(5, 2)    // → 25   five squared
Power(2, 8)    // → 256  2^8
Power(42, 0)   // → 1
Power(42, 1)   // → 42
(5 ^ 2)        // → 25   same as Power(5, 2)
```

For XOR, use `BitwiseXor(a, b)` — there is no infix XOR operator.

---

## Compound Assignment

```ailang
i += 1         // i = Add(i, 1)
i -= 1         // i = Subtract(i, 1)
i *= 2         // i = Multiply(i, 2)
i /= 2         // i = Divide(i, 2)
i /=/ 8        // i = Modulo(i, 8)
```

Compound assignment is a **statement only** — it cannot appear inside
an expression or condition.

---

## Math Primitives

These compile to optimal instruction sequences (branchless CMOV,
inline Newton's method). No function-call overhead.

### Absolute Value

```ailang
result = Abs(n)

Abs(42)      // → 42
Abs(-42)     // → 42
Abs(0)       // → 0
```

Compiled to branchless conditional move (no branch misprediction).

### Minimum / Maximum

```ailang
result = Min(a, b)
result = Max(a, b)

Min(10, 5)   // → 5
Max(10, 5)   // → 10

// Nested for three-way
Min(Min(a, b), c)
Max(Max(a, b), c)
```

Both compile to branchless CMOV.

### Integer Square Root

```ailang
result = ISqrt(n)

ISqrt(25)    // → 5
ISqrt(100)   // → 10
ISqrt(50)    // → 7   (floor of 7.071...)
ISqrt(0)     // → 0
```

Returns the floor of the square root. Implemented with Newton's method
compiled directly to x86-64 assembly.

### Increment / Decrement

```ailang
n = Increment(n)   // n + 1, must reassign
n = Decrement(n)   // n - 1, must reassign
```

These do not modify `n` in place — they return the new value.
Reassignment is required.

```ailang
n = 10
n = Increment(n)   // n is now 11
n = Increment(n)   // n is now 12
n = Decrement(n)   // n is now 11
```

---

## Common Mathematical Patterns

### GCD (Euclidean algorithm)

```ailang
a = 48
b = 18
WhileLoop NotEqual(b, 0) {
    temp = b
    b = Modulo(a, b)
    a = temp
}
// a now contains GCD(48, 18) = 6
```

### Integer power (fast)

```ailang
Function.Math.FastPow {
    Input:  base: Integer
    Input:  exp:  Integer
    Output: Integer
    Body: {
        result = 1
        b = base
        e = exp
        WhileLoop GreaterThan(e, 0) {
            IfCondition NotEqual(Modulo(e, 2), 0) ThenBlock: {
                result = Multiply(result, b)
            }
            b = Multiply(b, b)
            e = Divide(e, 2)
        }
        ReturnValue(result)
    }
}
```

### Clamp value to range

```ailang
Function.Math.Clamp {
    Input:  val:  Integer
    Input:  low:  Integer
    Input:  high: Integer
    Output: Integer
    Body: {
        ReturnValue(Max(low, Min(val, high)))
    }
}
```

### Check power of 2

```ailang
// n & (n-1) == 0, and n > 0
is_pow2 = And(GreaterThan(n, 0),
              EqualTo(BitwiseAnd(n, Subtract(n, 1)), 0))
```

### Discriminant (quadratic formula)

```ailang
// b² - 4ac
disc = Subtract(Power(b, 2), Multiply(Multiply(4, a), c))
disc = ((b ^ 2) - ((4 * a) * c))   // infix form
```

### Distance squared (integer geometry)

```ailang
dx = Subtract(x2, x1)
dy = Subtract(y2, y1)
dist_sq = Add(Multiply(dx, dx), Multiply(dy, dy))
dist_sq = (((x2 - x1) * (x2 - x1)) + ((y2 - y1) * (y2 - y1)))
```

---

## Edge Cases

| Operation | Input | Result |
|-----------|-------|--------|
| `Divide(n, 0)` | any | undefined behavior |
| `Modulo(n, 0)` | any | undefined behavior |
| `Power(n, 0)` | any | 1 |
| `Power(0, 0)` | — | 1 |
| `ISqrt(0)` | — | 0 |
| `Abs(INT64_MIN)` | -2⁶³ | undefined (no positive representation) |
| `Multiply(large, large)` | overflow | wraps (64-bit signed) |

---

## See Also

`AILang Operators Reference` — complete operator table, infix rules,
bitwise operations, compound assignment  
`AILang Language Introduction` — type system, numeric types  
`Library.StringUtils` — `StringToInt` for parsing

---

## Copyright

Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
