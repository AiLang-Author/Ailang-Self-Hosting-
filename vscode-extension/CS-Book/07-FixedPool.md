# Chapter 7: FixedPool — Named Shared State

**What you'll learn:** How AILang handles data that must outlive a single function call. Why "just use a global variable" is rejected in favor of explicit, named, typed, and auditable shared state. The difference between `FixedPool` (compile-time known structure) and dynamic allocation.

---

## The Problem of Long-Lived Data

So far, every piece of data we've created has had a very short lifetime:
- Local variables exist only while their function or block is active.
- Parameters exist only for the duration of the call.

This is safe and easy to reason about, but it is not sufficient for real programs. Many things need to persist across multiple function calls:

- Configuration values
- Counters and statistics
- Caches
- The state of a game, a database, a network connection
- The compiler's own internal data structures while it is running

In most languages, the default way to create such long-lived data is to declare a global variable. This is easy to write and extremely difficult to reason about at scale.

AILang takes a different approach.

---

## FixedPool: Explicit, Named, Typed Shared State

Instead of invisible globals, AILang requires you to declare long-lived shared state inside a named `FixedPool`:

```ailang
FixedPool.AppConfig {
    "version": Initialize="1.0"
    "debug": Initialize=0
    "max_retries": Initialize=3
}
```

This declaration does several important things at once:

- It gives the shared state a clear, searchable name (`AppConfig`).
- Every field is explicitly typed and given an initial value.
- Access is always qualified: `AppConfig.debug`, `AppConfig.max_retries`.

There is no way to create anonymous or "just this once" global state. Every piece of shared data must be declared in a pool with a name.

A real, verified teaching example of using a `FixedPool` for multiple results (demo 095):

```ailang
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

This pattern is used throughout the AILang compiler and libraries for clean, auditable cross-call state.

---

## Why This Design?

The compiler itself is one of the best examples of why this matters. The AILang compiler uses dozens of `FixedPool`s:

- `Compile` pool — current compilation state
- `Emit` pool — code and data buffers being generated
- `Lex` pool — lexer position and token stream
- Many others

Because every piece of shared state has a clear owner and a clear name, it is possible for a human (or an AI coding agent) to understand the architecture by reading the pool declarations and then searching for their qualified uses.

Contrast this with a typical large C or C++ codebase, where global variables, static variables in different translation units, and singleton classes create a tangled web that is very hard to audit.

---

## FixedPool vs Dynamic Allocation

`FixedPool` is for data whose structure is known at compile time and whose lifetime is essentially the entire run of the program.

It is **not** a replacement for dynamic memory. When you need to allocate objects whose number and size are not known until runtime, you still use `Allocate` and `Deallocate` (or higher-level structures built on top of them).

The two mechanisms serve different purposes and have different trade-offs:

- `FixedPool` — fast, predictable, auditable, limited to compile-time structure.
- Dynamic allocation — flexible, but requires manual lifetime management and is a common source of bugs.

---

## Hardware Connection

A `FixedPool` is ultimately just a region of memory whose address is known at compile time (or loaded into a fixed register such as `R15` in some AILang implementations).

Each field is at a known offset from the base of the pool. Accessing `AppConfig.debug` becomes something like:

```asm
mov  rax, [r15 + offset_of_debug]
```

Because the layout is fixed at compile time, the CPU can use simple addressing modes with no pointer chasing through multiple levels of indirection (unless the pool itself contains pointers to dynamically allocated data).

This is one of the reasons `FixedPool` access is both fast and easy to reason about.

---

## Key Concepts

- `FixedPool` as the explicit, named mechanism for long-lived, compile-time-structured shared state.
- Qualified access (`PoolName.field`) makes every use searchable and auditable.
- `Initialize=` for startup values.
- The distinction between `FixedPool` (fast, fixed layout) and dynamic allocation (flexible but manual lifetime).
- How pools make large systems (the compiler itself uses many) understandable by both humans and AI agents.

---

*Next: We look at strings — one of the most common sources of bugs in systems programming, and how AILang makes their true nature visible instead of hiding it behind convenient abstractions.*