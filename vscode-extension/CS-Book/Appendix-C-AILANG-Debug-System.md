# Appendix C: The AILANG Debug System — Complete Reference

This appendix summarizes the debug facilities available in AILang. These tools are primarily active in development builds (they are compiled out or stubbed in optimized production builds).

## Assertion System

`DebugAssert(condition, message)`

- Evaluates `condition`.
- If false, reports the message along with file and line information, then aborts the program.
- In production builds, the check and the entire call are removed.

Best used for:
- Invariants
- Preconditions that should never be violated in correct code
- Postconditions

## Tracing

`DebugTrace.Entry(name)`
`DebugTrace.Point(name)`
`DebugTrace.Exit(name)`

- Lightweight structured tracing.
- Can be enabled/disabled via compiler flags or environment.
- Useful for understanding actual execution order without the overhead or clutter of manual PrintMessage calls.
- Output can be filtered by name or module.

## Memory Inspection

`DebugMemory.Dump(address, size)`
- Hex + ASCII dump of memory.

`DebugMemory.Pattern(address, size, pattern)`
- Fills a region with a recognizable pattern (commonly used with 0xDEADBEEF or similar to detect uninitialized reads or use-after-free).

`DebugMemory.LeakCheck()`
- Reports allocations that were not freed since the last checkpoint or program start.

## Performance Measurement

`DebugPerf.Start(label)`
`DebugPerf.End(label)`

- High-resolution timing of labeled sections.
- Uses RDTSC or equivalent when available.
- The `-P` compiler flag can automatically instrument every function with entry/exit timing.

## Interactive Debugging Support

`DebugBreak()`
- Inserts a software breakpoint (`INT3` on x86-64).
- When run under a debugger (GDB, etc.), execution stops here.
- Allows inspection of registers, memory, and single-stepping through the compiled AILang code.

## Compiler Debug Flags

Commonly useful flags (exact names may vary slightly by build):

- `-d` — Dump combined/inlined source (very useful for understanding macro and import expansion).
- `-P` — Instrument for profiling / timing.
- Various trace and debug level controls (see the full Debug Programming Manual).

For the authoritative and complete reference, always consult:

**AILANG Debug Programming Manual.md** (in the Programming_Manual directory)

That manual contains the full list of primitives, their exact semantics, build configuration options, and recommended usage patterns. The summary above is only a high-level orientation.