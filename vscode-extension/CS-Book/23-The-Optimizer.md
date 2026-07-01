# Chapter 23: The Optimizer — Doing Less Work

**What you'll learn:** Why even a simple optimizer can make a dramatic difference. The idea of peephole optimization. The 90th percentile principle. Why the optimizer is conservative by design.

---

## The Unoptimized Path

When the code generator first walks the AST, it tends to generate very general, straightforward code.

For an expression like `Add(x, y)` the naive code generator might do:

- Compile `x`, leaving the result in RAX.
- Push RAX onto the stack (to save it).
- Compile `y`, leaving the result in RAX.
- Pop the saved value into RBX.
- Emit `ADD RAX, RBX`.

This works correctly for any operands. But for the very common case where both `x` and `y` are simple, it generates unnecessary instructions.

The AILang compiler (in `Librarys/Compiler/`) contains peephole and other optimizations that catch many of these patterns and emit much tighter code (you can see some of the optimization logic in the various Emit* modules).

```asm
mov  rax, [x]
mov  rbx, [y]
add  rax, rbx
```

The difference is not just theoretical. In hot inner loops, this kind of unnecessary memory traffic and extra instructions can easily make the difference between "fast enough" and "painfully slow."

---

## Peephole Optimization

A **peephole optimizer** looks at small, local patterns in the generated code and replaces them with better equivalents.

The classic example is the one above: recognize when both operands of an arithmetic operation are simple loads or constants, and emit the short form directly instead of going through the general push/pop path.

Other common peephole patterns:
- Eliminate redundant moves (`mov rax, rax`)
- Combine a comparison immediately followed by a conditional jump into a single instruction when possible
- Recognize simple cases of strength reduction (e.g., multiplying by a power of two can become a shift)

The "peephole" name comes from the idea that the optimizer only looks at a small window ("peephole") of instructions at a time.

---

## The 90th Percentile Principle

The AILang optimizer is deliberately conservative.

It focuses on making the common, simple cases fast, and falls back to the safe, general path for anything complicated.

This is an example of the **90th percentile principle**:

> Make the 90% case really good. The remaining 10% can be merely acceptable.

Trying to optimize every possible case perfectly usually leads to:
- Enormous complexity in the optimizer
- Risk of generating incorrect code in obscure corner cases
- Diminishing returns (the complicated cases are, by definition, rare)

A simple, reliable optimizer that makes the common cases excellent is often more valuable in practice than a heroic optimizer that sometimes produces magic and sometimes produces disasters.

---

## Hardware Connection

Modern CPUs are extremely sensitive to memory traffic, instruction count, and certain patterns (such as predictable branches or cache-friendly access).

Even small improvements in the generated code — fewer loads and stores, fewer instructions, better instruction scheduling — can produce large improvements in real performance because they interact well with the CPU's internal machinery (pipelines, caches, branch predictors, etc.).

The optimizer is one of the places where the compiler directly helps the hardware do its job more efficiently.

---

## Key Concepts

- Unoptimized code generation tends to be general but inefficient for simple cases.
- Peephole optimization recognizes small local patterns and replaces them with better code.
- A conservative optimizer that makes the common cases excellent is often better than an aggressive one that tries to be perfect everywhere.
- The optimizer's job is to help the hardware, not to perform miracles.

---

*Next: We look at one of the most impressive demonstrations of a language's completeness — a self-hosting compiler.*