# Chapter 3: Repetition

**What you'll learn:** How computers do work over and over again. The `WhileLoop` construct and what it actually compiles to. How `ExitLoop` (break) and `ContinueLoop` work at the machine level. Why some loops never terminate, and how to reason about termination from the source code alone.

---

## The Need for Repetition

So far we have only written programs that do a fixed amount of work and then stop. Real programs almost always need to do something many times — processing every character in a string, every element in an array, every packet on the network, every frame in a game.

The CPU itself only knows how to do one instruction at a time. Repetition is an illusion created by jumping backward in the instruction stream.

---

## The Fundamental Looping Construct

AILang's basic repetition tool is `WhileLoop`:

```ailang
i = 0
WhileLoop LessThan(i, 10) {
    PrintNumber(i)
    i = Add(i, 1)
}
```

This prints the numbers 0 through 9.

At the machine level, a `WhileLoop` becomes a very small, very regular pattern:

1. A label at the top of the loop.
2. Evaluate the condition.
3. A conditional jump forward to after the loop if the condition is false.
4. The body of the loop.
5. An unconditional jump back to the top label.
6. A label after the loop.

That is all. There is no special "loop hardware." The CPU is just doing comparisons and jumps, the same two mechanisms it uses for `IfCondition`.

---

## Leaving a Loop Early

Sometimes you need to stop the current iteration and go around again (`ContinueLoop`), or leave the loop entirely (`ExitLoop`).

```ailang
i = 0
WhileLoop LessThan(i, 100) {
    IfCondition EqualTo(i, 42) ThenBlock: {
        ExitLoop          // like "break" in other languages
    }
    IfCondition EqualTo(Modulo(i, 2), 0) ThenBlock: {
        ContinueLoop      // like "continue"
    }
    // only odd numbers that are not 42 reach here
    PrintNumber(i)
    i = Add(i, 1)
}
```

`ExitLoop` compiles to an unconditional jump to the label after the loop. `ContinueLoop` compiles to an unconditional jump back to the condition check at the top.

Again, the source makes the intent obvious, while the generated code is just the jumps the CPU already knows how to do.

---

## Why Loops Terminate (or Don't)

A loop will only stop if there is some path through the body that makes the loop condition become false.

Consider these two loops:

```ailang
// Will terminate
i = 0
WhileLoop LessThan(i, 10) {
    PrintMessage("working\n")
    i = Add(i, 1)
}

// Will never terminate
i = 0
WhileLoop LessThan(i, 10) {
    PrintMessage("working forever\n")
    // i is never changed
}
```

In the second case, nothing inside the loop body can ever make `LessThan(i, 10)` become false. The compiler cannot (in general) prove this for you, but a human reader can see it immediately because the language forces the condition and the body to be written in the same small, explicit scope.

Infinite loops are not a special category of beginner mistake. They are a structural property: if no execution path through the body can falsify the condition, the loop cannot end.

---

## Common Looping Patterns Made Explicit

### Counting

```ailang
i = 0
WhileLoop LessThan(i, n) {
    // do something with i
    i = Add(i, 1)
}
```

### Accumulation

```ailang
sum = 0
i = 0
WhileLoop LessThan(i, 100) {
    sum = Add(sum, i)
    i = Add(i, 1)
}
```

### Searching

```ailang
found = 0
i = 0
WhileLoop And(LessThan(i, length), EqualTo(found, 0)) {
    IfCondition EqualTo(ArrayGet(arr, i), target) ThenBlock: {
        found = 1
    }
    i = Add(i, 1)
}
```

Each of these patterns has a very regular translation into comparisons and jumps. By writing them with named operations and clear block structure, you make that regularity visible instead of burying it inside language "syntax sugar."

---

## Key Concepts

- Repetition is implemented with backward jumps.
- `WhileLoop` condition + body maps directly to CMP + conditional jump + unconditional jump.
- `ExitLoop` and `ContinueLoop` are just jumps with different targets.
- Termination is a property of whether the loop body can affect the condition.
- All higher-level looping constructs (for-each, do-while, etc.) are ultimately built from this same mechanism.

---

## Hardware Connection

Every loop in every program that has ever run on a real computer has been a comparison followed by a conditional jump backward. The only differences are how many times the jump is taken and what work happens between jumps.

By making `WhileLoop`, `ExitLoop`, and `ContinueLoop` first-class named constructs, AILang makes this fundamental machine mechanism directly visible in source code.

---

*Next: We introduce functions and subroutines as explicit contracts, and see how the calling convention on real hardware implements those contracts.*