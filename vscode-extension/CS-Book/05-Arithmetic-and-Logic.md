# Chapter 5: Arithmetic and Logic

**What you'll learn:** How computers actually perform calculations. Why AILang uses named operations (`Add`, `Multiply`, `Power`, etc.) as the primary form. The difference between cheap one-instruction operations and expensive multi-instruction ones. How comparisons and logic work at the hardware level. Why `^` means exponentiation (not XOR), and the current state of literal syntax for large or fractional numbers.

---

## The Machine Can Only Do So Much

At the end of the hardware primer, you learned that the CPU has an Arithmetic Logic Unit (ALU) that can perform a small number of operations directly in hardware:

- Add two numbers
- Subtract two numbers
- Multiply two numbers (on modern CPUs)
- Bitwise operations (AND, OR, XOR, shifts)
- Comparisons (which are really subtractions that only care about the flags)

Everything else — division in some cases, modulo, exponentiation, square roots, trigonometric functions — is built on top of these primitive operations using sequences of instructions.

Most programming languages hide this reality behind familiar symbols (`+`, `-`, `*`, `/`, `^`) and then add layers of implicit behavior (operator precedence, implicit type conversion, etc.). This creates the illusion that the computer "just does math" the way humans do.

AILang refuses to participate in that illusion.

---

## Named Operations as the Primary Form

In AILang, the fundamental way to perform arithmetic is with explicit, named operations:

```ailang
sum     = Add(a, b)
diff    = Subtract(a, b)
product = Multiply(a, b)
quotient = Divide(a, b)
remainder = Modulo(a, b)
power   = Power(base, exponent)
```

Each of these names corresponds to a real thing the CPU (or a small sequence of instructions) can do.

There are also infix forms available for readability:

```ailang
sum = (a + b)
```

However, **infix always requires explicit parentheses**. There is no operator precedence table. This is not an inconvenience — it is a deliberate design decision that forces the programmer (or the AI coding agent) to state their intent clearly.

```ailang
// Syntax error — ambiguous
result = a + b * c

// Correct and unambiguous
result = (a + (b * c))
result = ((a + b) * c)
```

---

## What the Hardware Actually Does

When you write `Add(x, y)`, the compiler will (in the common case) emit something like:

```asm
mov  rax, [x]
add  rax, [y]
```

When you write `Multiply(x, y)`, it will emit an `IMUL` instruction (or a more complex sequence for very large numbers).

When you write `Power(base, exp)`, the compiler does **not** emit a single instruction, because the CPU does not have a "power" instruction. Instead, it emits a small loop or a call to a library routine that repeatedly multiplies. The language makes no pretense that this is as cheap as a single addition.

This honesty is extremely valuable for building real mental models.

---

## Boolean Logic and Comparisons

Comparisons in AILang return ordinary integer values (1 for true, 0 for false):

```ailang
is_big     = GreaterThan(x, 100)
is_positive = GreaterThan(x, 0)
in_range   = And(GreaterThan(x, 0), LessThan(x, 100))
```

This is not an accident. At the hardware level, a comparison instruction (`CMP`) sets flags in the CPU. Later instructions test those flags. By making the result of the comparison a first-class value, AILang makes the connection obvious.

Boolean operations (`And`, `Or`, `Not`) also have clear hardware mappings:
- `And` and `Or` can short-circuit when written in certain ways.
- Bitwise versions (`BitwiseAnd`, `BitwiseOr`) operate on every bit independently and are useful for flags and masks.

---

## Cost Matters — Named Operations Make It Visible

Not all operations are equal in the hardware:

- `Add`, `Subtract`, `BitwiseAnd`, comparisons → usually **one CPU instruction**.
- `Multiply` → one instruction on modern CPUs (`IMUL`).
- `Divide`, `Modulo` → slower (often 10–40+ cycles).
- `Power(base, exp)`, `ISqrt` → multiple instructions or a small loop (no single CPU instruction exists for these).

AILang makes the cost visible by name. Writing `Power(x, 3)` looks different from `Multiply(x, x)` for a reason.

Useful math primitives that compile efficiently (branchless where possible):

```ailang
abs_val   = Abs(-42)           // branchless CMOV
smallest  = Min(a, b)
biggest   = Max(a, b)
root      = ISqrt(50)          // floor square root via Newton's method
```

## Literals and Notation (Current State)

- Hex: `0xFF` works.
- Large integers: Write them out fully (`15000000000`) or use future underscore separators. Full scientific notation like `1.5e10` for Integers is not currently parsed (see demo 028). For values larger than ~9×10^18 you need big-integer support.
- `^` is always exponentiation (Power). Use `BitwiseXor` for XOR.

## Key Concepts

- The CPU has a small set of fast primitive operations; everything else is built from them.
- Named operations (`Add`, `Power`, `Abs`) make both meaning **and cost** explicit.
- Infix is allowed but requires parentheses — no hidden precedence.
- Comparisons return ordinary integers (1/0); there is no separate Boolean magic.
- `^` means Power because that is what mathematicians expect; the language provides `BitwiseXor` for the machine operation.

## Hardware Connection

Every arithmetic expression becomes real ALU instructions:

- `Add(x, y)` → typically `ADD` or `LEA`
- `Power(x, n)` → a loop of multiplies or library routine
- `Abs(n)` → conditional move (`CMOV`) with no branch
- Comparisons → `CMP` + conditional jump or `SETcc` instruction

By writing the operation you actually mean, you can reason about performance and correctness instead of hoping the compiler "does the right thing" with cryptic symbols.

---

*Next: We move into how programs are organized — scope, shared state, and the difference between what the language allows and what it makes easy to reason about.*