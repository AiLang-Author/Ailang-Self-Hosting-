# Chapter 16: Debug Level 1 — Assertions

**What you'll learn:** How to turn your understanding of preconditions, postconditions, and invariants into executable checks that the computer can enforce for you. The difference between assertions in debug builds versus production builds. Why "fail fast" is often the best debugging strategy.

---

## From Thinking to Checking

In the previous chapter, we talked about thinking in terms of preconditions, postconditions, and invariants.

That is valuable, but it is still entirely in your head.

The next step is to turn some of that thinking into code that the computer can check for you at runtime.

This is what assertions are for.

---

## The Basic Idea

An assertion is a statement that says "I believe this condition must be true at this point in the program."

If the condition is false when the assertion runs, the program stops immediately (in debug builds) and tells you exactly which assumption was violated.

This "fail fast" behavior is one of the most effective debugging strategies in systems programming. A crash at the exact point where an invariant was broken is far more useful than silent corruption that appears hundreds of lines later.

```ailang
DebugAssert(NotEqual(divisor, 0), "Division by zero in CalculateAverage")
DebugAssert(GreaterThan(array_length, 0), "Cannot search an empty array")
DebugAssert(LessThan(index, array_length), "Array index out of bounds")
```

Verified examples from the teaching demos (090, 125, 126) show the pattern in practice. The key is writing the condition that expresses the precondition, postcondition, or invariant you just reasoned about in the previous chapter.

The first argument is the condition that must be true. The second is a message that will be shown if it is not.

---

## Why Assertions Are Powerful

Assertions give you several things that are hard to get any other way:

1. **They document your assumptions in executable form.** A comment can lie. An assertion that fails will tell you the truth.

2. **They turn vague bugs into precise failures.** Instead of "the program crashed somewhere with a weird value," you get "at line 47, the precondition that the file handle was valid was violated."

3. **They catch mistakes early.** Many bugs become much harder to debug the further they propagate from their origin. An assertion can stop the corruption at the source.

4. **They make the mental model explicit.** Writing the assertion forces you to decide what the actual rule is.

---

## Debug vs. Production

In AILang (and most systems), assertions are typically only enabled in debug builds.

When you compile with debug information and without the "release" or "optimize" flags, the assertions are present in the generated code. If one fails, the program stops and reports the location and message.

When you compile a release build, the compiler is allowed to remove all the assertion checks. They become zero-cost in the final product.

This is a deliberate tradeoff:

- In development and testing, you want maximum checking.
- In production, you usually do not want the program to suddenly stop because of an assertion (you would rather it try to continue or fail in a more controlled way). The performance cost of the checks can also be significant in hot paths.

The important thing is that the assertions are still present in your source code. They continue to serve as documentation even when they are not being executed.

---

## What to Assert

Good things to assert:

- Preconditions at the beginning of functions ("this pointer must not be null", "this length must be positive").
- Postconditions before returning from a function ("the returned index must be in range or -1").
- Invariants at key points ("after this operation, the length field must still match the actual number of elements").
- Assumptions about external state ("the file descriptor must still be valid").

Bad things to assert:

- Things that can legitimately fail in normal operation (file not found, network timeout, etc.). Those should be handled with proper error handling, not assertions.
- Performance-sensitive checks that you would not want even in debug builds (use them sparingly on hot paths).
- Things that are already enforced by the type system or by AILang's direction contracts (`Input`/`Output`).

---

## The "Fail Fast" Philosophy

When something is wrong, it is usually better to find out as soon as possible rather than letting the program continue in a corrupted state.

This is the "fail fast" principle.

An assertion that fires on a violated precondition is the program saying: "I have reached a state that the author of this code explicitly said should never happen. Stopping now is safer than continuing and producing wrong results or corrupting more data."

Many production systems have mechanisms to turn a failed assertion into a controlled restart or a failover to another machine rather than a hard crash. The key point is that the corruption is detected early.

---

## Hardware Connection

At the machine level, an assertion is usually compiled into something like:

```asm
cmp   rax, 0
jne   .assertion_ok
; call error reporting code with file, line, and message
int3   ; or some other trap / abort
.assertion_ok:
```

In release builds, the entire sequence (except possibly the `cmp` if the value is still needed) can be removed by the optimizer.

The `int3` (or equivalent) is a debugging breakpoint instruction. It is the same mechanism used by debuggers when you set a breakpoint.

---

## Key Concepts

- Assertions turn mental assumptions into runtime checks.
- They are documentation that the computer can enforce.
- They are usually only present in debug builds (zero cost in production).
- "Fail fast" is often safer than silent corruption.
- Good assertions check preconditions, postconditions, and invariants — not expected error conditions.

---

*Next: We look at the second level of debugging — tracing execution so you can see what the program actually did versus what you thought it would do.*