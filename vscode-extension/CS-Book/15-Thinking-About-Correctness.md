# Chapter 15: Thinking About Correctness

**What you'll learn:** What it actually means for a program to be "correct." The ideas of preconditions, postconditions, and invariants. Why "it works on my machine" is a much weaker statement than "it is correct," and why that distinction matters.

---

## "It Works" Is Not Enough

Most programmers, especially early in their careers, operate under a very weak definition of success:

> If the program does what I wanted for the inputs I tried, it is good.

This is the "type this and pray" model in action. It produces programs that pass the test cases the author happened to think of, but fall apart the moment they encounter anything outside that narrow set.

Real correctness is a much stronger property:

> A program is correct if, for every valid input, it produces the expected output and satisfies all the properties we care about.

The gap between these two definitions is where most serious bugs live.

---

## Preconditions, Postconditions, and Invariants

To talk rigorously about correctness, we need three related ideas:

### Preconditions

A **precondition** is something that must be true before a piece of code runs.

Examples from AILang's own design:
- The size passed to `Deallocate(ptr, size)` must exactly match the size passed to the corresponding `Allocate` (demo 138).
- When calling a Function that takes a `LinkagePool` with `Direction=Input` fields, the caller must have initialized those fields (enforced by the compiler).
- "The divisor must not be zero" before division.

If a precondition is violated, the code is not obligated to behave correctly. AILang encourages failing loudly via assertions or early returns (guard clauses) rather than producing garbage.

Verified example of guard clauses (demo 065):

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

Each `If` is an explicit precondition check with an early, clear exit.

### Postconditions

A **postcondition** is something that must be true after a piece of code finishes (assuming its preconditions were met).

Examples:
- After `Array.Sort(arr)`, the array is sorted and contains the same elements (demo 141).
- After a successful `Calculate(req)` where `req` had `Direction=Output` fields, those fields contain valid results.

AILang makes these easier to check with explicit assertions (see demos 090, 125, 126).

Examples:
- "The returned value is the index of the target, or -1 if not found."
- "The array is now sorted in ascending order."
- "The allocated buffer has been filled with the requested number of bytes."

Postconditions are what the caller can rely on.

### Invariants

An **invariant** is something that must remain true throughout some process or data structure.

Examples:
- "The length field always accurately reflects the number of valid elements in the array."
- "The tree remains balanced after every insertion and deletion."
- "The total number of allocated bytes never exceeds the maximum allowed."

Invariants are what let you reason about a system over time rather than just at single points.

---

## Why These Ideas Matter

When you think in terms of preconditions, postconditions, and invariants, several good things happen:

1. **You write better interfaces.** You are forced to be explicit about what a function requires and what it guarantees.
2. **You find bugs earlier.** Many bugs are violations of an invariant or a precondition that was never stated.
3. **You can reason about code without running it.** This is essential for large systems and for security-critical code.
4. **Debugging becomes systematic instead of superstitious.** Instead of "it stopped working after I changed X," you can ask "which invariant or postcondition is now violated?"

AILang's explicit nature makes these concepts more natural to express than in languages full of implicit behavior.

---

## The Weak vs. Strong Contract

Most buggy code suffers from weak or missing contracts:

- "This function sometimes returns null, sometimes returns a valid pointer, and sometimes crashes."
- "Don't pass the same buffer as both source and destination, unless the stars are aligned."
- "The caller is responsible for freeing the returned string, except in the error case."

These are not contracts. They are collections of special cases and folklore.

A strong contract is clear, checkable, and documented in the code itself whenever possible (through assertions, direction annotations like `Input`/`Output`, and clear naming).

---

## Hardware Connection

At the machine level, there is no concept of "correctness" at all. The CPU will happily execute any sequence of valid instructions, no matter how nonsensical the result is from a human perspective.

All notions of correctness are imposed by humans (and enforced, when we are lucky, by compilers and tools).

When we say a program is correct, we are saying that the behavior it produces on the hardware matches the specification we had in our heads. The hardware itself is amoral — it just does what the bits say.

---

## Key Concepts

- "It works on my test cases" is a very weak claim.
- Preconditions, postconditions, and invariants are the basic vocabulary for talking about correctness.
- Strong contracts make code easier to reason about, easier to debug, and safer to compose.
- The machine does not care about our notions of correctness; we have to impose them.

---

*Next: We look at the first practical tool for enforcing correctness at runtime — assertions.*