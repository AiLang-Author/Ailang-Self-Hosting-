# AILang — Language Introduction

## What is AILang?

AILang is a compiled, statically-structured systems programming language that targets x86-64 Linux. It compiles directly to native machine code with no runtime, no garbage collector, and no virtual machine. Programs run as standalone ELF executables.

AILang is designed to be:
- **Readable by humans and AI** — explicit, unambiguous syntax with no operator overloading
- **Systems capable** — direct syscall access, manual memory control, pointer arithmetic
- **Safe by design** — ambiguous operators are excluded by philosophy, not accident
- **Self-hosting** — the AILang compiler is written in AILang

---

## How AILang Differs from C / C++ / Python

### No implicit anything

C lets you write `i++`, `*p++`, `a[i++]` — expressions with implicit side effects and order-of-evaluation ambiguity. AILang requires every operation to be explicit:

```ailang
// AILang — always explicit
i = Add(i, 1)
// or with compound assignment (coming)
i += 1
```

There is no `++`, no `--`, no `,` operator, no implicit type promotion, no implicit string-to-number coercion.

### Named operators are first-class

In C, `+` is an operator and `add()` is a function call. In AILang they are the same thing. `Add(a, b)` and `(a + b)` produce identical code. The function form is always available. This matters because:

- You can grep for `Multiply` and find every multiplication in a codebase
- No operator overloading confusion
- No "what does `+` mean for this type" ambiguity

### No operator precedence surprises

AILang infix requires explicit parentheses. There is no precedence table to memorize:

```ailang
// This is a syntax error in AILang:
result = a + b * c

// This is correct — intent is unambiguous:
result = (a + (b * c))
result = ((a + b) * c)
```

You always know exactly what order things evaluate in.

### `^` means Power, not XOR

In C, `^` is bitwise XOR. In AILang, `^` is exponentiation — the mathematical meaning. XOR has no infix operator; use `BitwiseXor(a, b)`. This is documented in the operators reference and is intentional.

### No pointers-as-arrays confusion

C arrays decay to pointers, `a[i]` is `*(a + i)`, pointer arithmetic is implicit. In AILang, pointer arithmetic is explicit:

```ailang
// Access element i of an 8-byte-stride array
offset = Multiply(i, 8)
element = Dereference(Add(base_ptr, offset))
```

Verbose? Yes. Ambiguous? Never.

### Functions vs SubRoutines

AILang distinguishes functions (return a value) from subroutines (no return value). This is explicit in the definition, not inferred:

```ailang
// Function — has Output and ReturnValue
Function.Math.Square {
    Input:  n: Integer
    Output: Integer
    Body: {
        ReturnValue(Multiply(n, n))
    }
}

// SubRoutine — no Output, no ReturnValue
SubRoutine.Logger.PrintStatus {
    PrintMessage("Status: OK")
}
```

Calling them is also explicit:

```ailang
result = Math.Square(5)   // Function call — value captured
RunTask(Logger.PrintStatus)  // SubRoutine call — no value
```

This makes it impossible to accidentally discard a return value or accidentally use a void function as an expression.

### No header files, no forward declarations

AILang uses `LibraryImport` for dependencies. The compiler resolves everything. There is no separation of declaration from definition:

```ailang
LibraryImport.Arena
LibraryImport.Regex_Thompson
```

### Memory is explicit, not hidden

There is no `new`/`delete`, no `malloc`/`free`, no garbage collector. Memory allocation and deallocation are explicit primitives:

```ailang
buf = Allocate(1024)
// ... use buf ...
Deallocate(buf, 1024)
```

The size passed to `Deallocate` must match `Allocate`. Passing the wrong size routes to the wrong slab and corrupts the allocator. This is intentional — it forces you to track sizes.

### Global state lives in FixedPools

AILang has no global variables in the C sense. Global state is declared in named `FixedPool` blocks:

```ailang
FixedPool.Config {
    "buffer_size": Initialize=4096
    "max_retries": Initialize=3
}
```

Accessed as `Config.buffer_size`. This makes global state explicit, namespaced, and greppable. R15 is reserved for the pool table — never modify R15 in user code.

---

## Program Structure

Every AILang program follows this structure:

```ailang
// 1. Library imports
LibraryImport.Arena

// 2. Global state pools
FixedPool.AppConfig {
    "port": Initialize=8080
}

// 3. Function and subroutine definitions
Function.Net.ParsePort {
    Input:  s: Address
    Output: Integer
    Body: {
        ReturnValue(StringToInt(s))
    }
}

// 4. Entry point
SubRoutine.Main {
    port = Net.ParsePort("9000")
    AppConfig.port = port
    PrintNumber(AppConfig.port)
}

// 5. Run the entry point
RunTask(Main)
```

`RunTask(Main)` at the bottom is the program entry. There is no implicit `main()`.

---

## Type System

AILang has two primitive types:

| Type | Size | Description |
|------|------|-------------|
| `Integer` | 64-bit signed | All integers. -2⁶³ to 2⁶³-1 |
| `Address` | 64-bit unsigned | Pointer / memory address |

Strings are `Address` values pointing to NUL-terminated byte sequences. There is no separate string type. Booleans are `Integer` — `1` is true, `0` is false. There is no `bool`, no `true`, no `false` keyword.

---

## Control Flow

### Conditional

```ailang
IfCondition GreaterThan(x, 0) ThenBlock: {
    PrintMessage("positive")
} ElseBlock: {
    PrintMessage("non-positive")
}
```

`ElseBlock` is optional. There is no `else if` — nest another `IfCondition` inside the `ElseBlock`.

### Loop

```ailang
i = 0
WhileLoop LessThan(i, 10) {
    PrintNumber(i)
    i = Add(i, 1)
}
```

`BreakLoop` exits the loop. `ContinueLoop` skips to the next iteration.

### Branch (switch/case)

```ailang
Branch strategy {
    Case 0: { PrintMessage("empty") }
    Case 1: { PrintMessage("whole line") }
    Case 7: { hit = Match_LiteralBM(line, line_len, pi) }
}
```

`Branch` dispatches on an integer value. Cases must be integer literals. No fallthrough — each case is a block. The compiler emits a two-instruction dispatch (CMP + JE) per case.

---

## Memory Model

```
High addresses
┌─────────────────┐
│     Stack       │  ← Local variables, function frames (RBP/RSP)
├─────────────────┤
│     Heap        │  ← Allocate() / Arena slabs
├─────────────────┤
│   Pool Table    │  ← R15 — FixedPool variables
├─────────────────┤
│  Data Section   │  ← String literals, constants
├─────────────────┤
│  Code Section   │  ← Compiled machine code
└─────────────────┘
Low addresses
```

**R15 is reserved.** The compiler uses R15 as the pool table base pointer. Never write to R15 in inline assembly or syscall wrappers.

---

## Compilation

```bash
# Compile to executable
ailang program.ailang

# Output: program_exec (ELF64, no extension)
./program_exec
```

Programs produce a single ELF64 executable with no shared library dependencies beyond the Linux kernel syscall interface.

---

## What AILang Does Not Have

These are intentional omissions, not missing features:

| Missing | Why |
|---------|-----|
| `++` / `--` | Pre/post ambiguity, UB in expressions |
| Implicit type coercion | Every conversion is explicit |
| Operator overloading | `+` always means integer addition |
| Exceptions / try-catch | Errors are return values |
| Garbage collector | Memory ownership is explicit |
| Header files | `LibraryImport` handles dependencies |
| Preprocessor macros | No text substitution |
| Undefined behavior | Every operation has defined semantics |
| `goto` | Use `BreakLoop` / `ContinueLoop` / `ReturnValue` |

---

## Conventions

- **Naming:** `Function.Module.Name`, `SubRoutine.Module.Name`, `FixedPool.Name`
- **Pools:** `Pool.field` access — always namespaced
- **Addresses:** Treated as unsigned 64-bit integers in arithmetic
- **NUL strings:** All string `Address` values point to NUL-terminated byte arrays
- **Error returns:** Functions return `-1` or `0` on failure by convention
- **File extensions:** `.ailang`

---

## Demo Programs & Teaching Examples

The `Demo Programs/programs/` directory contains 130+ progressive, numbered teaching examples — from `001_hello_world.ailang` through advanced recursion, error handling with `Result`/`Option`, classic algorithms (Tower of Hanoi, fast exponentiation), and AILang-specific control-flow idioms (`Fork` + `Branch` combinatorial decision trees).

**Master index + recommended clean teaching curriculum:**

`Demo Programs/DEMO_PROGRAMS_TEACHING_INDEX.md`

These are the best way to learn the language by reading real, small, focused programs in order.

## See Also

`AILang Operators Reference`,
`Library.Arena`,
`Library.StringUtils`,
`Library.Regex_Thompson`,
`Memory Management Reference Manual`,
`Demo Programs/DEMO_PROGRAMS_TEACHING_INDEX.md` (the full progressive curriculum)

---

## Copyright

Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
