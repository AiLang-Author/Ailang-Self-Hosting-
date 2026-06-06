# Chapter 25: Modular Design — Functions as Boundaries

**What you'll learn:** The `TryCompile` pattern as a general design principle. How to build systems that are easy to extend without modifying existing code. The value of clear boundaries and "try the next option" composition.

---

## The Compiler as a Design Example

By this point in the book, you have seen the AILang compiler's source code (or at least large parts of it) in earlier chapters.

One of its most interesting architectural features is how it is organized for extension.

The compiler does not have one giant function that knows how to compile every possible AST node. Instead, it has a chain of `TryCompile` modules (you can see this pattern clearly in `Librarys/Compiler/Compile/Modules/` — for example the various `CCompileString*` and similar files).

Each module is responsible for one category of operations:
- One module handles arithmetic and logic.
- Another handles memory allocation and pointer operations.
- Another handles control flow (`IfCondition`, `WhileLoop`, etc.).
- Another handles function and subroutine calls.
- And so on.

The main dispatcher walks the AST. For each node, it asks each module in turn: "Can you compile this?"

The first module that returns success handles it. If no module can handle it, the compiler reports an error.

This is the `TryCompile` pattern.

---

## Why This Pattern Is Powerful

This organization has several excellent properties:

1. **Additive, not intrusive.** To add support for a new operation, you write a new small module that knows how to compile that operation, and you add one line to the dispatch list. You do not have to modify any existing modules.

2. **Clear ownership.** Each category of operations has a clear owner. If something goes wrong with arithmetic, you know exactly which file to look in.

3. **Easy to understand in isolation.** You can read the arithmetic module and understand how all arithmetic is compiled without having to hold the entire compiler in your head.

4. **Graceful failure.** If a node reaches the end of the chain without being handled, you get a clear "unsupported operation" error instead of some module accidentally trying to compile something it doesn't understand and producing garbage.

This is a concrete example of a more general design principle:

> Organize systems around boundaries where new features can be added by adding new code rather than by modifying existing code.

---

## The Same Pattern in User Programs

The same idea applies far beyond compilers.

You can use `TryCompile`-style dispatch (or simple chains of functions that each try to handle a request and return success/failure) for:

- Command dispatch in a text adventure or REPL
- Handling different message types in a network protocol
- Choosing which rendering strategy to use for different kinds of UI elements
- Plugin systems
- Error recovery strategies

The key insight is the same: instead of one giant `switch` or `if-else` chain that has to know about every case, you have a list of handlers that can be extended without touching the central dispatcher.

---

## Connection to Earlier Ideas

This pattern is a natural fit for AILang's explicit style:

- Each handler module has a clear contract (it receives an AST node and either emits code or returns failure).
- The direction of data flow is explicit.
- There is no hidden global state that different handlers fight over (or if there is shared state, it lives in well-named `FixedPool`s).

It is also a good example of the "functions as boundaries" idea from earlier in the book. Each module exposes a single entry point (`TryCompile`), and the composition happens through a simple, visible chain.

---

## Hardware Connection

At the machine level, this kind of dispatch often ends up as a chain of comparisons and conditional jumps (or a jump table if the cases are dense).

The software organization does not change the fact that the CPU will eventually have to decide which piece of code to run. What the `TryCompile` pattern buys you is that the decision is made in a way that is easy for humans to extend and reason about, rather than a giant tangled mess of special cases.

---

## Key Concepts

- The `TryCompile` pattern as an example of additive architecture.
- Clear module boundaries and single entry points.
- Composing behavior by trying handlers in sequence rather than by having one central place that knows everything.
- Why this style of organization scales better than giant `switch` statements as a system grows.

---

*Next: We look at error handling — how to distinguish between expected problems and unexpected bugs, and how to give the caller useful information when something goes wrong.*