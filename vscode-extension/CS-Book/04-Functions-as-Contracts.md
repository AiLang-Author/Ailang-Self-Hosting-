# Chapter 4: Functions — Contracts for Computation

**What you'll learn:** The difference between subroutines (do something) and functions (compute something and return a value). How AILang makes these contracts explicit with `Input:` and `Output:` on Functions. How SubRoutines communicate via FixedPool instead of parameters. What a calling convention actually is at the hardware level. Why explicit contracts (plus LinkagePool Direction attributes for structured data) eliminate an entire class of subtle bugs.

---

## Two Kinds of Reusable Code

So far we have written linear sequences of instructions and simple loops. Real programs need a way to package up useful pieces of work so they can be reused without copying the same code over and over.

AILang draws a very sharp line between two different kinds of reusable code:

- **SubRoutine** — "Go do this thing." It performs an action. It does not return a value.
- **Function** — "Take these inputs and compute this output." It transforms data and returns a result.

This distinction is not just documentation. The compiler enforces it.

---

## SubRoutines — Actions, Not Values

A `SubRoutine` is a named block of code that performs an action. It does **not** return a value.

```ailang
SubRoutine.Greet {
    PrintMessage("Hello!\n")
}

SubRoutine.Main {
    Greet()
    Greet()
}

RunTask(Main)
```

You call a SubRoutine with `RunTask(Name)`. It cannot appear in an expression because it produces nothing.

SubRoutines have **no formal parameters**. They communicate with the rest of the program through `FixedPool` (the recommended way) or global variables.

Example using FixedPool for state:

```ailang
FixedPool.Stats {
    "total": Initialize=0
    "count": Initialize=0
}

SubRoutine.AddToStats {
    Stats.total = Add(Stats.total, value)
    Stats.count = Add(Stats.count, 1)
}

SubRoutine.PrintAverage {
    IfCondition GreaterThan(Stats.count, 0) ThenBlock: {
        avg = Divide(Stats.total, Stats.count)
        PrintMessage("Average: ")
        PrintNumber(avg)
        PrintMessage("\n")
    }
}
```

At the hardware level, `RunTask` compiles to a plain `CALL` / `RET` pair with very little setup — intentionally lightweight for side-effect code.

---

## Functions — Contracts That Produce Values

A `Function` declares exactly what it takes and exactly what it returns.

```ailang
Function.Square {
    Input: n: Integer
    Output: Integer
    Body: {
        ReturnValue(Multiply(n, n))
    }
}
```

Call it like any expression:

```ailang
result = Square(7)     // 49
area   = Square(5)     // 25
```

The compiler enforces the contract:
- Every declared `Input` must be supplied by the caller.
- Every path through the `Body` must reach a `ReturnValue(...)` of the declared `Output` type.

If either rule is broken, compilation fails. There is no "maybe it returns" or "maybe this parameter is optional."

---

## The Hardware Reality of a Function Call

Functions use the standard System V AMD64 calling convention on Linux x86-64:

- First six integer/pointer parameters → RDI, RSI, RDX, RCX, R8, R9
- Additional parameters → stack
- Return value → RAX

When you write `result = Square(7)`, the compiler emits:
- Move 7 into RDI
- `CALL` (pushes return address)
- Inside the function: prologue sets up a stack frame
- Compute the result, place it in RAX
- Epilogue tears down the frame and `RET`
- Caller reads RAX

This is exactly the same mechanism used by C and many other languages. AILang simply makes the contract (`Input` → registers, `Output` → RAX) visible in source instead of hiding it.

---

## Input and Output Contracts on Functions

The only two sections Functions understand are:

- `Input:` — typed parameters supplied by the caller (read-only inside the function)
- `Output:` — the single value that must be returned

Here is a real, verified example (from the teaching demos):

```ailang
Function.Classify {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessThan(n, 0) ThenBlock: { ReturnValue(-1) }
        IfCondition EqualTo(n, 0) ThenBlock: { ReturnValue(0) }
        IfCondition GreaterThan(n, 100) ThenBlock: { ReturnValue(2) }
        ReturnValue(1)
    }
}
```

This compiles and runs correctly. The compiler guarantees that every input is supplied and every execution path returns the declared output type.

SubRoutines have no `Input` or `Output` sections at all. For data that must survive across SubRoutine calls, use `FixedPool`.

When you need structured data with fine-grained read/write rules, use a `LinkagePool` with `Direction=` attributes on its fields and pass the pool as a normal `Input:` parameter (see Chapter 10). The compiler then enforces the directions on field accesses.

---

## When to Use Each

| Situation                                      | Use            | Why |
|------------------------------------------------|----------------|-----|
| You need to compute a value and return it      | Function       | Explicit `Input:` / `Output:`, type-safe, can be used in expressions |
| You are doing I/O, printing, or state changes  | SubRoutine     | Designed for actions; no parameter overhead |
| You need data that lives across multiple calls | FixedPool      | The standard way for SubRoutines to share state |
| You need multiple results or per-field rules on structured data | LinkagePool + `Direction=` on fields | Pass the pool as a normal `Input:`; compiler enforces the directions |

## Key Concepts

- Functions declare `Input:` (parameters) and `Output:` (what `ReturnValue` must produce). The compiler enforces both.
- SubRoutines have neither. Use `FixedPool` for anything that must survive the call.
- LinkagePool fields can carry `Direction=Input|Output|InOut`. When the pool is passed as a Function `Input:`, the compiler checks every field access against the declared direction.
- The hardware mechanism is the standard System V AMD64 calling convention (arguments in RDI/RSI/etc., return in RAX, `CALL`/`RET`).

## Hardware Connection

A Function call on real x86-64 Linux hardware does this:

1. Arguments placed in RDI, RSI, RDX, RCX, R8, R9 (first six) or pushed on the stack.
2. `CALL` instruction pushes the return address and jumps.
3. Function builds a stack frame (save RBP, allocate locals).
4. Work is performed.
5. Result is placed in RAX.
6. Frame is torn down and `RET` jumps back to the caller.

SubRoutine calls are lighter — mostly just the `CALL`/`RET` because there are no declared parameters to marshal.

AILang does not invent new hardware rules. It makes the real ones (the same ones C uses) visible and checkable in source code.

---

*Next: We look at arithmetic and logic — how the machine actually performs the calculations that almost every program depends on.*