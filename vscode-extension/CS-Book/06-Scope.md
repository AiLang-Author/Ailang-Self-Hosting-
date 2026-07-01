# Chapter 6: Scope — Who Can See What

**What you'll learn:** What "scope" actually means in terms of memory and time. Why AILang has no top-level variables. How local variables are implemented using the stack. Why scope is a safety mechanism, not just a convenience.

---

## The Lifetime of a Name

When you write:

```ailang
x = 42
```

the name `x` only exists for a certain period of time and within a certain region of the code. Outside that region, the name is meaningless. This region is called the **scope** of the variable.

In AILang, scope is not an abstract rule. It is a direct consequence of how the machine manages memory.

---

## Local Variables Live on the Stack

Every time a function (or subroutine) is called, the machine creates a new **stack frame** for it. This is a region of memory that belongs exclusively to that activation of the function.

Local variables are allocated within this stack frame. When the function returns, the stack pointer is moved back, and the memory that held those local variables is no longer considered valid for that purpose.

This is why top-level variables outside any `SubRoutine` or `Function` are not allowed for general use in AILang. Every piece of named state must live inside a `FixedPool`, a `LinkagePool`, or inside the scope of a function or block.

The correct pattern for sharing results or state that must outlive a single call is a named `FixedPool`. Here is a real, verified teaching example (demo 095):

```ailang
// From Demo Programs/programs/095_multi_return_via_pool.ailang
FixedPool.DivResult {
    "q": Initialize=0
    "r": Initialize=0
}

Function.DivMod {
    Input: a: Integer
    Input: b: Integer
    Output: Integer
    Body: {
        DivResult.q = Divide(a, b)
        DivResult.r = Modulo(a, b)
        ReturnValue(0)
    }
}

SubRoutine.Main {
    DivMod(47, 5)
    PrintMessage("47 / 5 = ")
    PrintNumber(DivResult.q)
    PrintMessage("  remainder ")
    PrintNumber(DivResult.r)
    PrintMessage("\n")
}
RunTask(Main)
```

This produces `47 / 5 = 9  remainder 2`.

The `DivResult` pool is the explicit, named owner of the shared state. Its lifetime is clear, it is easy to search for, and the compiler knows exactly where the storage lives. This is the AILang way to solve the "multiple return values" problem without globals or magic tuples.

This is not a limitation. It is a deliberate safety feature.

---

## Why the Absence of Globals Matters

In languages that allow easy global variables, it is extremely common to see:

- One part of the program writing to a global.
- Another part reading from it, possibly much later.
- A third part accidentally overwriting it.
- No one being able to easily find all the places the variable is used.

Because the variable has no owner and no clear lifetime, bugs involving it are hard to find and hard to reason about.

The example above (demo 095) shows the AILang alternative: a small, explicitly named `FixedPool` whose purpose is documented in its name (`DivResult`). Every access is qualified, the storage has a clear owner, and the compiler can reason about its lifetime. We will explore `FixedPool` in depth in the next chapter.

---

## Block Scope

Variables declared inside an `IfCondition`, `WhileLoop`, `ThenBlock`, or other block are only visible inside that block.

```ailang
IfCondition GreaterThan(x, 0) ThenBlock: {
    temp = x          // only visible inside this block
    // ...
}
// temp is no longer a valid name here
```

This is implemented on the stack. The compiler tracks the lifetime of every name and rejects any attempt to use a name after its storage has been reclaimed.

In practice you will see this most often inside the `Body` of a `Function` or the statements of a `SubRoutine` — each activation gets its own fresh set of locals.

---

## Hardware Connection

A local variable is an offset from the base pointer inside the current stack frame.

- Function/SubRoutine prologue: adjust RSP to reserve space for locals.
- Each name gets a fixed `[RBP - offset]`.
- Epilogue: restore the old stack pointer — those addresses are now invalid.

The compiler's scope rules are exactly the enforcement of "you may only access memory while its stack frame is live." This eliminates use-after-return and stale stack reference bugs at compile time.

---

## Key Concepts

- Scope = spatial region + temporal lifetime of storage.
- No convenient top-level globals — shared state uses named `FixedPool` (see next chapter and the verified pattern in demo 095).
- Block scope and function locals are stack-allocated and automatically reclaimed.
- The compiler turns scope rules into hard guarantees about memory validity.

---

*Next: We look at `FixedPool` — the explicit, named, compile-time mechanism AILang provides for state that must outlive a single call.*