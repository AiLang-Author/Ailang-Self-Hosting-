# AILang Operators Reference

## Philosophy

AILang has no ambiguous operators. Every operator has exactly one meaning.
Where C or C++ reuse a symbol for multiple purposes (`^` = XOR in C,
`^` = Power in AILang), AILang chooses the mathematically unambiguous
meaning and provides an explicit function for the other use.

Every operator has a **function form** that is always valid. Infix symbols
are syntactic sugar that compile to identical code. When in doubt, use the
function form — it is always unambiguous and always works.

---

## Dual Syntax Rule

```ailang
// These are identical — same codegen output
result = Add(a, b)
result = (a + b)

// Mixed — also valid
result = Add((a * b), Divide(c, d))
```

**Infix requires explicit parentheses.** There is no precedence table.
The parentheses are the precedence:

```ailang
// SYNTAX ERROR — bare infix, no parens
result = a + b * c

// CORRECT — intent is unambiguous
result = (a + (b * c))
result = ((a + b) * c)
```

---

## Arithmetic Operators

| Function Form | Infix | Description |
|---------------|-------|-------------|
| `Add(a, b)` | `(a + b)` | Addition |
| `Subtract(a, b)` | `(a - b)` | Subtraction |
| `Multiply(a, b)` | `(a * b)` | Multiplication |
| `Divide(a, b)` | `(a / b)` | Integer division, truncates toward zero |
| `Modulo(a, b)` | — | Remainder. **See `/=/` below** |
| `Power(a, b)` | `(a ^ b)` | Exponentiation. **`^` is Power, NOT XOR** |

### Division behavior

Integer division always truncates toward zero:

```ailang
Divide(20, 3)    // → 6   (not 7)
Divide(-20, 4)   // → -5
Divide(-20, -4)  // → 5
```

Division by zero is undefined behavior. Always validate divisors.

### The `^` operator is Power, not XOR

**This is the most common C/C++ confusion.** In C, `^` is bitwise XOR.
In AILang, `^` is exponentiation — the mathematical meaning.

```ailang
(5 ^ 2)            // → 25   (five squared)
Power(5, 2)        // → 25   (same thing)
BitwiseXor(5, 3)   // → 6    (XOR — function only, no infix)
```

---

## Compound Assignment Operators

Compound assignment is a statement — it cannot appear in an expression
or condition. Left side must be a simple variable.

| Operator | Equivalent | Description |
|----------|-----------|-------------|
| `i += n` | `i = Add(i, n)` | Add and assign |
| `i -= n` | `i = Subtract(i, n)` | Subtract and assign |
| `i *= n` | `i = Multiply(i, n)` | Multiply and assign |
| `i /= n` | `i = Divide(i, n)` | Divide and assign |
| `i /=/ n` | `i = Modulo(i, n)` | Modulo and assign |

### Why `/=/` for modulo assignment?

`%=` would be inconsistent — AILang uses `Modulo()` not `%` for the
base operation. `/=/` is visually distinct from `/=` (divide-assign),
cannot be confused with any other operator, and reads as
"divide-remainder-by":

```ailang
i /=/ 8    // i = Modulo(i, 8)
i /= 8     // i = Divide(i, 8)   — clearly different
```

**Compound assignment is never an expression:**
```ailang
// VALID
i += 1

// SYNTAX ERROR — compound assignment inside condition
IfCondition GreaterThan(i += 1, 0) ThenBlock: { ... }
```

---

## Comparison Operators

All comparisons return `1` (true) or `0` (false).

| Function Form | Infix | Description |
|---------------|-------|-------------|
| `EqualTo(a, b)` | `(a == b)` | Equal |
| `NotEqual(a, b)` | `(a != b)` | Not equal |
| `GreaterThan(a, b)` | `(a > b)` | Greater than |
| `LessThan(a, b)` | `(a < b)` | Less than |
| `GreaterEqual(a, b)` | `(a >= b)` | Greater than or equal |
| `LessEqual(a, b)` | `(a <= b)` | Less than or equal |

```ailang
is_adult = GreaterEqual(age, 18)   // → 1 or 0
valid = And(GreaterThan(x, 0), LessThan(x, 100))
```

---

## Logical Operators

| Function Form | Infix | Description |
|---------------|-------|-------------|
| `And(a, b)` | `(a && b)` | Logical AND |
| `Or(a, b)` | `(a \|\| b)` | Logical OR |
| `Not(a)` | `(!a)` | Logical NOT |

Logical values: `0` is false, any non-zero is true. There are no
`true` / `false` keywords.

```ailang
IfCondition And(EqualTo(x, 5), GreaterThan(y, 0)) ThenBlock: {
    // ...
}
```

---

## Bitwise Operators

| Function Form | Infix | Description |
|---------------|-------|-------------|
| `BitwiseAnd(a, b)` | `(a & b)` | Bitwise AND |
| `BitwiseOr(a, b)` | `(a \| b)` | Bitwise OR |
| `BitwiseXor(a, b)` | — | Bitwise XOR. **No infix — `^` is Power** |
| `BitwiseNot(a)` | `(~a)` | Bitwise NOT (complement) |
| `LeftShift(a, n)` | `(a << n)` | Left shift by n bits |
| `RightShift(a, n)` | `(a >> n)` | Logical right shift (fills with zeros) |

### XOR has no infix operator

`BitwiseXor` is function-only. There is no symbol for it because `^` is
already Power. This is intentional and permanent.

```ailang
// CORRECT
toggled = BitwiseXor(value, mask)

// WRONG — this is POWER not XOR
toggled = (value ^ mask)   // computes value^mask = value to the power of mask
```

### Common bit manipulation patterns

```ailang
// Set bit n
set_bit = BitwiseOr(value, LeftShift(1, n))
set_bit = (value | (1 << n))

// Clear bit n
clear_bit = BitwiseAnd(value, BitwiseNot(LeftShift(1, n)))
clear_bit = (value & (~(1 << n)))

// Toggle bit n  — MUST use function, no infix XOR
toggled = BitwiseXor(value, LeftShift(1, n))

// Test bit n
is_set = NotEqual(BitwiseAnd(value, LeftShift(1, n)), 0)
is_set = ((value & (1 << n)) != 0)

// Check power of 2
is_pow2 = EqualTo(BitwiseAnd(n, Subtract(n, 1)), 0)
is_pow2 = ((n & (n - 1)) == 0)
```

---

## Advanced Math Primitives

These are compiler-level primitives — implemented directly in codegen,
not as library functions. They compile to optimal instruction sequences.

| Primitive | Description | Notes |
|-----------|-------------|-------|
| `Abs(n)` | Absolute value | Branchless CMOV |
| `Min(a, b)` | Minimum of two values | Branchless CMOV |
| `Max(a, b)` | Maximum of two values | Branchless CMOV |
| `ISqrt(n)` | Integer square root (floor) | Newton's method, inline assembly |
| `Increment(n)` | Returns n + 1 | Does not modify n |
| `Decrement(n)` | Returns n - 1 | Does not modify n |

```ailang
pos   = Abs(-42)       // → 42
small = Min(10, 5)     // → 5
big   = Max(10, 5)     // → 10
root  = ISqrt(25)      // → 5
root  = ISqrt(50)      // → 7  (floor of 7.071)

// Increment/Decrement: must reassign
n = 10
n = Increment(n)       // n is now 11
n = Decrement(n)       // n is now 10
```

---

## Memory Operators

These are compiler primitives for direct memory access.

| Primitive | Description |
|-----------|-------------|
| `Allocate(size)` | Allocate `size` bytes, returns `Address` |
| `Deallocate(ptr, size)` | Return `size` bytes at `ptr` to allocator |
| `Dereference(ptr)` | Read 8-byte value at address `ptr` |
| `StoreValue(ptr, val)` | Write 8-byte value `val` to address `ptr` |
| `GetByte(ptr, offset)` | Read 1 byte at `ptr + offset` |
| `SetByte(ptr, offset, val)` | Write 1 byte `val` at `ptr + offset` |
| `MemoryCopy(dst, src, n)` | Copy `n` bytes from `src` to `dst` (SSE2) |
| `MemorySet(ptr, val, n)` | Fill `n` bytes at `ptr` with `val` |
| `MemChr(ptr, byte, n)` | Find first occurrence of `byte` in `n` bytes. Returns offset or -1 (SSE2) |
| `MemCompare(a, b, n)` | Compare `n` bytes. Returns 0 if equal (SSE2) |
| `AddressOf(var)` | Get address of a variable |

```ailang
buf = Allocate(64)
StoreValue(buf, 42)
val = Dereference(buf)          // → 42

SetByte(buf, 0, 72)             // 'H'
SetByte(buf, 1, 105)            // 'i'
SetByte(buf, 2, 0)              // NUL

off = MemChr(buf, 105, 64)      // → 1  (offset of 'i')
```

---

## String Primitives

Built-in string operations — these are compiler primitives, not library functions.

| Primitive | Description |
|-----------|-------------|
| `StringLength(s)` | Length of NUL-terminated string |
| `StringConcat(a, b)` | Concatenate two strings, returns new `Address` |
| `StringCompare(a, b)` | Compare strings. Returns 0 if equal |
| `StringEquals(a, b)` | Returns 1 if equal, 0 otherwise |

For higher-level string operations (trim, pad, contains, etc.)
see `Library.StringUtils`.

---

## Intentionally Excluded Operators

These operators exist in C / C++ / Python but are **permanently excluded**
from AILang. This is philosophy, not oversight.

| Operator | Language | Reason excluded |
|----------|----------|----------------|
| `++` / `--` | C/C++ | Pre/post ambiguity, UB in expressions |
| `?:` ternary | C/C++ | Readability — use `IfCondition` |
| `,` comma | C/C++ | Implicit sequencing, confusing in args |
| `->` | C/C++ | Use `Dereference(Add(ptr, offset))` |
| `[]` subscript | C/C++ | Use `Dereference(Add(ptr, Multiply(i, 8)))` |
| `&` address-of (unary) | C/C++ | Use `AddressOf(var)` |
| `*` dereference (unary) | C/C++ | Use `Dereference(ptr)` |
| `sizeof` | C/C++ | Sizes are explicit in AILang |
| `~=` / `**=` | Python | Not needed |
| `^` XOR | C/C++ | `^` is Power in AILang — use `BitwiseXor()` |

---

## Quick Reference Card

```
ARITHMETIC          COMPARISON          LOGICAL
Add(a,b)  (a+b)    EqualTo(a,b)  ==    And(a,b)  &&
Subtract  (a-b)    NotEqual      !=    Or(a,b)   ||
Multiply  (a*b)    GreaterThan   >     Not(a)    !
Divide    (a/b)    LessThan      <
Modulo    /=/      GreaterEqual  >=
Power     (a^b)    LessEqual     <=

BITWISE                         COMPOUND ASSIGN
BitwiseAnd(a,b)  (a&b)         i += n    i -= n
BitwiseOr(a,b)   (a|b)         i *= n    i /= n
BitwiseXor(a,b)  NO INFIX      i /=/ n
BitwiseNot(a)    (~a)
LeftShift(a,n)   (a<<n)
RightShift(a,n)  (a>>n)

MEMORY                          MATH PRIMITIVES
Allocate(n)                     Abs(n)
Deallocate(ptr,n)               Min(a,b)  Max(a,b)
Dereference(ptr)                ISqrt(n)
StoreValue(ptr,val)             Increment(n)
GetByte(ptr,off)                Decrement(n)
SetByte(ptr,off,val)
MemChr(ptr,byte,n)
MemCompare(a,b,n)
MemoryCopy(dst,src,n)
```

---

## See Also

`AILang Language Introduction`,
`Library.StringUtils`,
`Library.Arena`,
`Memory Management Reference Manual`

---

## Copyright

Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
