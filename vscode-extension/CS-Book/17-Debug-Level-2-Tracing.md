# Chapter 17: Debug Level 2 — Tracing

**What you'll learn:** How to make the actual execution of a program visible. The difference between what you think the code does and what it actually does when it runs. How to use tracing to understand control flow, especially in complex or unfamiliar code.

---

## The Gap Between Source and Execution

When you read source code, you build a mental model of what will happen when it runs.

This model is often incomplete or simply wrong.

- You might miss an early return.
- You might not realize that a particular branch is almost never taken.
- You might not notice that a function is being called recursively in a way you didn't expect.
- You might assume that two pieces of code run in a certain order when the actual order is different (especially with concurrency or callbacks).

Tracing is the practice of making the program itself tell you what it is doing, step by step.

---

## What Tracing Looks Like

A basic tracing system lets you insert markers at interesting points in the code:

```ailang
DebugTrace.Entry("ProcessData")
...
DebugTrace.Point("about to sort the array")
...
DebugTrace.Exit("ProcessData")
```

From the AILANG Debug System Manual, tracing is part of a hierarchical debug system with zero-overhead production builds (debug code becomes NOPs when the level is not enabled). Higher debug levels include all lower ones.
DebugTrace.Exit("ProcessData")
```

When the program runs (with tracing enabled), it produces output like:

```
[1234] ENTER ProcessData
[1234] POINT about to sort the array
[1234] EXIT  ProcessData
```

With more sophisticated tracing, you can record:
- Function entry and exit (with parameters and return values)
- Values of important variables at key points
- Timestamps or cycle counts
- Thread or process IDs

This creates a log of the actual execution, not your assumptions about it.

---

## Why Tracing Is Powerful

Tracing is especially valuable in several situations:

1. **When you are reading unfamiliar code.** Instead of trying to simulate the entire program in your head, you can run it with tracing and see the actual path it took.

2. **When debugging intermittent or hard-to-reproduce bugs.** The trace can show you the sequence of events that led to the failure, even if you can't reproduce it on demand.

3. **When performance is the question.** A trace with timestamps can show you where time is actually being spent, which is often very different from where you assumed it would be.

4. **When teaching or explaining code.** A trace is an excellent way to walk someone through what a piece of code actually does on real inputs.

---

## The Danger of "Print Debugging"

Many programmers discover tracing on their own by adding `PrintMessage` calls everywhere when something goes wrong. This is often called "printf debugging" or "print debugging."

It works, but it has serious limitations:

- You have to edit the code and recompile every time you want to see something new.
- The print statements clutter the code and can introduce new bugs.
- You often end up with a huge volume of output that is hard to navigate.
- When you are done debugging, you have to remember to remove all the print statements (or leave them in and suffer the clutter).

A proper tracing system (like AILang's `DebugTrace`) is designed to solve these problems:
- Tracing can often be enabled or disabled without recompiling.
- The trace points can be structured and filtered.
- The output is designed to be machine-readable as well as human-readable.
- The trace points can stay in the code permanently as a form of executable documentation.

---

## Hardware Connection

At the machine level, a trace point is usually just a call to a tracing function (or, in highly optimized systems, a write to a special memory buffer or even a dedicated tracing instruction).

The cost is the cost of that call plus whatever work the tracing system does to record the event (formatting, writing to a file or socket, etc.).

Because tracing has a cost, good systems let you control the level of detail. You might run with very lightweight tracing in production (just function entry/exit with minimal data) and turn on heavy tracing with full variable values only when you are actively debugging a problem.

---

## Key Concepts

- Your mental model of the code is often wrong or incomplete.
- Tracing makes the actual execution visible instead of forcing you to simulate it mentally.
- Good tracing is structured, controllable, and cheap enough to leave in the code.
- "Print debugging" is the manual version of tracing; proper tracing systems are the automated, sustainable version.

---

*Next: We look at the third level of debugging — directly inspecting memory contents to see what is actually stored there.*