# Chapter 2: Values and Decisions

**What you'll learn:** How the machine represents and manipulates the most basic kinds of data (integers, booleans, text). How variables work as named locations in memory. How the computer makes a choice between two paths. The direct mapping between high-level decision constructs and the conditional jumps the CPU actually executes.

---

## The Only Things Computers Know How to Do

At the lowest level, a computer can only do a handful of things with data:

- Store a value at an address in memory.
- Read a value from an address in memory.
- Compare two values and remember the result (equal, greater, less, etc.).
- Use the result of a comparison to decide whether to take one path or another through the code.

Everything else — text, images, sound, networks, games, AI — is built by doing these four operations in clever combinations, billions of times per second.

This chapter introduces the first three in the context of AILang, then shows how the fourth (making decisions) is expressed in a way that makes the hardware behavior obvious.

---

## Values Live in Memory

When you write this in AILang:

```ailang
x = 42
```

You are telling the compiler: "I need a place to remember the number 42, and I want to refer to that place by the name `x`."

The compiler chooses a location in memory (on the stack, at some offset from the base pointer) and emits the machine instruction that stores 42 at that address. The name `x` exists only in your source code and in the compiler's symbol table. In the final executable, there is only an address offset.

Later, when you write:

```ailang
y = Add(x, 10)
```

The compiler emits instructions that:
1. Read the value at `x`'s address into a register.
2. Add 10 to it.
3. Store the result at `y`'s address.

The names are for humans (and the compiler). The hardware only ever sees addresses and values.

---

## The Fundamental Data Types

AILang gives you a small set of primitive types that map directly onto what the CPU and memory can represent:

- `Integer` — A 64-bit signed whole number.
- `Boolean` — The result of a comparison (internally represented as 1 for true, 0 for false).
- `Address` (pointer) — A memory address.
- Text / strings — Sequences of bytes in memory, conventionally null-terminated.

There are no "magic" high-level types at the lowest level. A string is not a special object with methods attached in the language definition — it is a pointer to a sequence of bytes that certain library operations know how to walk.

---

## Making Decisions

The most fundamental thing a program can do after storing and retrieving values is to look at a value and choose different behavior based on what it sees.

In AILang this is written with maximum clarity:

```ailang
IfCondition GreaterThan(x, 10) ThenBlock: {
    PrintMessage("Big number\n")
} ElseBlock: {
    PrintMessage("Small number\n")
}
```

This is not "if" in the vague sense of many languages. It is three distinct, named pieces:

- `IfCondition` — evaluates a question that returns true or false.
- `ThenBlock` — what to do if the answer was true.
- `ElseBlock` — what to do if the answer was false (optional).

At the hardware level this becomes:

1. A comparison instruction (`CMP`) that sets internal flags in the CPU.
2. A conditional jump (`JLE`, `JG`, etc.) that either takes the jump or falls through to the next instruction.
3. The code for one block or the other.
4. An unconditional jump (if needed) to skip the block that wasn't chosen.

The `IfCondition`/`ThenBlock`/`ElseBlock` syntax is the compiler's way of writing "compare, conditional jump, code, jump over the other code" in a form that is easy for humans to read and reason about.

There is no hidden control flow. The machine instructions are doing exactly what the source says: ask a question, then take one of two paths.

---

## Comparisons Return Values

In AILang, comparisons are not special statements. They are expressions that produce a result (1 or 0):

```ailang
is_big = GreaterThan(x, 100)
is_positive = GreaterThan(x, 0)
```

Because they produce ordinary integer values, they compose naturally:

```ailang
in_range = And(GreaterThan(x, 0), LessThan(x, 100))
```

This is the same pattern the CPU uses internally — comparisons set flags, and later instructions test those flags. AILang simply makes the intermediate result visible and nameable.

---

## Why Explicit Decisions Matter

Many languages allow you to write conditions in ways that hide complexity:

- Implicit conversion of numbers to booleans
- Operator precedence surprises
- Short-circuit evaluation that is easy to get wrong when side effects are involved

AILang removes these hiding places. Every decision is written with `IfCondition`, `GreaterThan`, `EqualTo`, etc., or the corresponding infix form with mandatory parentheses:

```ailang
IfCondition (x > 0) ThenBlock: { ... }
```

You can see at a glance exactly what question is being asked. The compiler cannot surprise you with hidden conversions or precedence rules, because there are no hidden conversions and precedence is always written with parentheses.

This explicitness is not just a style preference. It is what makes AILang unusually good for teaching — and for training AI coding agents that must reason reliably about control flow.

---

## Key Concepts

- Variables as named memory locations (stack offsets)
- The mapping from high-level names to addresses
- Comparisons as operations that produce values
- `IfCondition`/`ThenBlock`/`ElseBlock` as direct names for conditional branching
- The absence of hidden control flow and implicit conversions

---

## Hardware Connection

A decision in AILang is one comparison instruction followed by one or two jump instructions. That is the entire mechanism by which computers choose different behavior based on data. Every `if`, `switch`, `match`, or conditional in any language ultimately reduces to this pattern on real hardware.

By writing decisions explicitly, you are writing something that has a one-to-one correspondence with what the CPU will actually execute.

---

*Next: We look at repetition — how the machine does work over and over, and why some loops never stop.*