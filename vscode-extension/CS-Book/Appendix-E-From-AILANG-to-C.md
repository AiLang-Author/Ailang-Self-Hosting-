# Appendix E: From AILANG to C

This appendix provides a conceptual mapping between AILang constructs and their closest equivalents in C. It is intended for readers who already know C and are learning AILang (or vice versa).

## Core Philosophy Difference

C hides a lot of what the machine is doing behind convenient (and sometimes dangerous) syntax. AILang makes almost everything explicit.

| Concept                  | C (common style)                  | AILang (explicit)                          | Notes |
|--------------------------|-----------------------------------|--------------------------------------------|-------|
| Addition                 | `a + b`                           | `Add(a, b)` or `(a + b)` (with parens)    | Infix requires explicit parentheses in AILang |
| Function call            | `foo(x, y)`                       | `Foo(x, y)`                               | AILang uses capitalized names for user functions by convention in many codebases |
| Local variable           | `int x = 5;`                      | `x = 5` (type inferred or declared)       | AILang has very strong inference |
| Pointer                  | `int *p`                          | `p: Address`                              | No type attached to the pointer itself in AILang |
| Dereference              | `*p`                              | `Dereference(p)`                          | Explicit |
| Store through pointer    | `*p = 42`                         | `StoreValue(p, 42)`                       | Explicit |
| Struct / Record          | `struct Point { int x, y; }`      | `LinkagePool.Point { "x": ..., "y": ... }` | AILang records are always allocated separately |
| Function that returns value | `int square(int n) { return n*n; }` | `Function.Square { Input: n: Integer; Output: Integer; Body: { ReturnValue(Multiply(n,n)) } }` | Explicit Input/Output contracts |
| "Global" state           | `static int counter;`             | `FixedPool.Counters { "counter": Initialize=0 }` | Always named and explicit |
| Memory allocation        | `malloc(100)`                     | `Allocate(100)`                           | Size must be passed to `Deallocate` too |
| Free                     | `free(p)`                         | `Deallocate(p, size)`                     | Size is required in AILang |

## Control Flow

| C                          | AILang                                      |
|----------------------------|---------------------------------------------|
| `if (x > 0) { ... } else { ... }` | `IfCondition GreaterThan(x, 0) ThenBlock: { ... } ElseBlock: { ... }` |
| `while (i < 10) { ... }`   | `WhileLoop LessThan(i, 10) { ... }`        |
| `for (int i=0; i<10; i++)` | Usually expressed with `WhileLoop` + manual increment |
| `switch` / `case`          | `Branch value { Case 1: { ... } Default: { ... } }` |

AILang deliberately does **not** have C-style `for` loops or `switch` with fallthrough, because those constructs hide important details about control flow and state.

## Memory Model Differences

- In C, stack vs heap is implicit (local variables vs `malloc`).
- In AILang, the stack is used for locals inside functions, but long-lived or shared state must live in `FixedPool` or be explicitly heap-allocated.
- AILang has no implicit "global variables" — all shared state must be declared in a named pool.

## When Moving from C to AILang

- Expect to write more characters, but far less ambiguity.
- You will stop writing certain classes of bugs because the language makes the dangerous thing explicit.
- Performance mental model is usually better because you can see the cost of operations.

## When Moving from AILang to C

- You will gain syntactic brevity.
- You will lose a lot of safety and explicitness.
- You will need to be much more careful about lifetimes, aliasing, and undefined behavior.
- Many things that were compile-time enforced in AILang become runtime bugs or nasal demons in C.

This mapping is intentionally high-level. For a production port, study the actual generated assembly from the AILang compiler alongside equivalent C code. The compiler output is deliberately readable for exactly this reason.