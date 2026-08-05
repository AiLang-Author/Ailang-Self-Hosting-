# Chapter 20: Performance — Measuring, Not Guessing

**What you'll learn:** Why intuition about performance is almost always wrong. How to measure execution time accurately. The difference between guessing where the slow parts are and actually finding them. Basic profiling concepts.

---

## The 90/10 Rule (or 80/20, or 95/5...)

In almost every non-trivial program, a small fraction of the code accounts for most of the execution time.

This is sometimes called the 90/10 rule (90% of the time is spent in 10% of the code), though the exact ratios vary. The important point is that the distribution is extremely uneven.

This has a very practical consequence:

> If you guess where the program is slow, you will almost certainly be wrong.

You will waste time optimizing code that doesn't matter, while the real bottlenecks remain untouched.

---

## Measuring Instead of Guessing

The only reliable way to know where time is being spent is to measure it.

In AILang, the language provides `DebugPerf` (fully functional per the AILANG Debug System Manual) as a built-in, zero-overhead-when-disabled way to measure execution time of regions of code.

There are several levels of measurement, from simple to sophisticated:

1. **Manual timing** — Wrap a section of code with calls to get the current time before and after, then subtract.
2. **Sampling profilers** — Periodically interrupt the program and record what it was doing (what function, what line).
3. **Instrumentation profilers** — Insert code at function entry and exit (or even every line) to record timing information.
4. **Hardware performance counters** — Use special CPU registers that count cycles, cache misses, branch mispredictions, etc.

AILang's `DebugPerf` facilities and the compiler's `-P` (profile) flag provide instrumentation-style profiling that is easy to use during development.

---

## Why Intuition Fails

Human intuition about performance tends to be shaped by:

- What the code *looks* like (loops feel expensive, function calls feel cheap).
- What was slow in previous programs or languages.
- What the programmer spent the most time thinking about.

None of these correlate well with actual runtime cost on modern hardware.

A tight loop doing simple integer arithmetic can be dramatically faster than a single function call that touches memory in a cache-unfriendly way. A "simple" string operation can dominate everything else because it walks memory.

Without measurement, you are flying blind.

---

## Hardware Connection

Modern CPUs have a cycle counter (on x86 this is read with the `RDTSC` instruction) that can be used for very high-resolution timing.

A good profiler will use this (or even more precise mechanisms) to attribute cycles to specific functions or lines.

It will also often use hardware performance counters to report not just "this took a long time," but "this caused a lot of cache misses" or "this had a lot of branch mispredictions."

This moves performance work from guesswork into engineering.

---

## Key Concepts

- The distribution of execution time is extremely uneven in most programs.
- Human intuition about what is slow is unreliable.
- Measurement (profiling) is the only way to know where optimization effort should be spent.
- Modern hardware provides excellent tools for measurement (cycle counters, performance counters).

---

*Next: We move into systems programming — what the operating system actually does for you, and how your program talks to the outside world.*