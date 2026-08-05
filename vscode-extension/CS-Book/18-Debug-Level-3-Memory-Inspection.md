# Chapter 18: Debug Level 3 — Memory Inspection

**What you'll learn:** How to look directly at the raw contents of memory. Tools for dumping memory, filling it with recognizable patterns, and detecting leaks. Why seeing the actual bytes is often the fastest way to understand what has gone wrong.

---

## When Higher-Level Tools Are Not Enough

Sometimes tracing and assertions are not sufficient.

You may have a value that is clearly wrong, but you do not know where it came from. You may suspect that memory is being overwritten unexpectedly. You may have a data structure that looks corrupted when you print it through normal means.

In these situations, the most direct tool is to look at the raw bytes in memory.

---

## Dumping Memory

The primary tool is `DebugMemory.Dump` (fully functional per the AILANG Debug System Manual).

```ailang
DebugMemory.Dump(ptr, 256)   // dump 256 bytes starting at ptr
```

Output is typically hex + ASCII, making it easy to spot corruption, wrong encoding, or uninitialized data.

From the official debug manual, `DebugMemory.*` belongs to the higher debug levels and is compiled to NOPs in production builds (zero overhead when disabled).

This is often the fastest way to answer questions like:
- "Is my string actually null-terminated?"
- "Did the integer I wrote actually get written, or did something overwrite it?"
- "Is this Arena slab header intact?"
- "What does this structure actually contain right now?"

---

## Pattern Filling (The "DEADBEEF" Trick)

One of the most useful debugging techniques is to fill memory with a recognizable pattern when it is allocated or freed.

Common patterns:
- `0xDEADBEEF` or `0xDEADC0DE` when memory is allocated but not yet initialized.
- `0xFEEBDAED` or similar when memory is freed.

Then, later, if you see one of these values where you expected real data, you immediately know:
- You read from uninitialized memory, or
- You read from memory after it was freed.

This turns mysterious "garbage" values into clear evidence of a lifetime error.

---

## Leak Detection

A leak detector compares the set of allocations against the set of deallocations.

At the end of the program (or at explicit checkpoints), it can report:
- "You allocated 47 blocks and freed 46. Here is the one you leaked, with its allocation site."

More advanced detectors can also detect:
- Double-frees
- Use-after-free (if the memory has been filled with a pattern)
- Buffer overruns that corrupted allocator metadata

---

## Why Raw Memory Inspection Is Powerful

Higher-level printing (showing a "Person" object with name and age) can hide problems:
- The name pointer might be dangling.
- The age might be in the wrong union variant.
- The object might have been freed and the memory reused for something else.

When you look at the raw bytes, none of that is hidden. You see exactly what is in memory at that moment.

This is often the difference between "I don't understand why this is broken" and "Oh. The pointer is 0xDEADBEEF. It was never initialized."

---

## Hardware Connection

All of these tools ultimately boil down to reading (and sometimes writing) raw memory through the same load and store instructions the CPU uses for everything else.

`DebugMemory.Dump` is a loop that reads bytes and formats them.

Pattern filling is a loop that writes the pattern bytes.

The only thing special is that these tools are designed for debugging rather than for the program's normal operation.

---

## Key Concepts

- Raw memory dumps reveal what is actually stored, not what your data structures claim should be there.
- Pattern filling turns "garbage" into evidence of specific kinds of bugs (uninitialized reads, use-after-free).
- Leak detectors automate the comparison of allocations vs. deallocations.
- These tools are the lowest-level view you can get without a full hardware debugger.

---

*Next: We look at the fourth and most interactive level of debugging — using breakpoints and single-stepping to watch the program execute one instruction at a time.*