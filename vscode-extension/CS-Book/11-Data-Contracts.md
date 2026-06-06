# Chapter 11: Data Contracts — Direction Enforcement via LinkagePool

**What you'll learn:** How AILang provides enforceable read/write contracts on structured data using `Direction=Input|Output|InOut` attributes on LinkagePool fields. How these contracts are checked by the compiler when a pool is passed as an `Input:` parameter to a Function. Why this is the actual mechanism (there is no top-level `InOut:` section on Functions or SubRoutines). The connection to ownership, aliasing, and FixedPool for simpler cases.

---

## The Problem with "Just Pass It"

In many languages, when you pass data to a function, the rules are fuzzy:

- Does the function promise not to modify what I gave it?
- Am I supposed to free this memory later, or does the function take ownership?
- Can I keep using this data after the call returns, or has it been invalidated?

These questions are often answered only in comments (if at all), and the compiler does not help you.

The result is a steady stream of bugs:
- Use-after-free
- Double-free
- Unexpected mutation through aliases
- Leaked resources

AILang attacks this problem at the language level with explicit direction contracts.

---

## The Actual Mechanism: LinkagePool + Direction Attributes

There is **no** `InOut:` (or `Output:` / `Input:` beyond the top-level sections) as a general parameter direction syntax on Functions.

The real, compiler-enforced direction contracts work like this:

1. You define a `LinkagePool` type whose fields declare `Direction=Input`, `Direction=Output`, or `Direction=InOut`.
2. You pass an instance of that pool as a normal `Input:` parameter to a Function.
3. Inside the function, the compiler enforces the Direction rules on every `@field` access.

Example (the correct pattern):

```ailang
LinkagePool.Calculation {
    "a": Initialize=0, Direction=Input
    "b": Initialize=0, Direction=Input
    "result": Initialize=0, Direction=Output
}

Function.Calculate {
    Input: req: LinkagePool.Calculation
    Output: Integer
    Body: {
        req@result = Add(req@a, req@b)
        ReturnValue(1)   // or whatever
    }
}
```

Attempting `req@a = 99` inside the function would be a compile error because the field was declared `Direction=Input`.

For simpler shared mutable state without the full pool machinery, use `FixedPool` (especially with SubRoutines) or pass plain `Address` values and manage access yourself.

This is the design that actually exists in the language and is enforced by the compiler. The older description of `InOut:` as a peer to `Input:` / `Output:` at the Function declaration level was incorrect and has been removed.

---

## Why This Is More Than Documentation

In languages without these contracts, programmers rely on convention and discipline. AILang's LinkagePool Direction attributes (combined with the strict `Input:` / `Output:` on Functions and FixedPool for SubRoutines) turn the important data-flow rules into machine-checked facts instead of comments. The compiler can reject misuse of an "Input" field at compile time.

---

## Connection to Ownership and Aliasing

The LinkagePool Direction system gives you explicit, enforceable ownership-like rules for structured data passed across calls:

- A field marked `Direction=Input` is read-only inside the callee (the caller retains full control).
- A field marked `Direction=Output` must be written by the callee before the function returns.
- `Direction=InOut` allows both sides to read and write during the call.

Combined with the fact that ordinary scalar parameters to Functions are always `Input` (read-only from the callee's perspective), and that SubRoutines have no parameters and must use FixedPool, AILang makes data movement intentions visible and checked rather than relying on programmer discipline or hidden reference semantics.

---

## Hardware Connection

At the machine level, these contracts do not add runtime overhead in the common case. They are primarily a compile-time discipline.

However, they do influence code generation:
- The compiler can assume that writes through an `Output` or `InOut` parameter may affect values visible to the caller.
- It can be more aggressive about register allocation and optimization when it knows a parameter is purely `Input`.

In this sense, the contracts give the compiler (and the human reader) more precise information about data flow than a language without them can provide.

---

## Key Concepts

- LinkagePool `Direction=Input|Output|InOut` as the enforceable data movement contracts (when pools are passed as Function Input parameters).
- Functions have only `Input:` / `Output:`; SubRoutines have none (use FixedPool).
- The compiler as an active participant in preventing data-flow errors on structured data.
- The connection between these contracts, FixedPool, ownership, and aliasing.
- How explicit contracts improve both human understanding and compiler optimization.

---

*Next: We enter Part III — Memory. We will look at what memory actually is, how allocation works, and why pointers are both powerful and dangerous.*