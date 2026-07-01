# Chapter 19: Debug Level 4 — Breaking and Stepping

**What you'll learn:** How to stop a running program at a specific point and examine its state. The mechanics of breakpoints and single-stepping. What a debugger actually does under the hood. Basic GDB usage as a concrete example.

---

## The Most Powerful Debugging Tool

So far we have seen:
- Assertions (stop when something is obviously wrong)
- Tracing (watch what the program does as it runs)
- Memory inspection (look at raw bytes)

The fourth and most interactive level is to **stop the program** at a point you choose and look around while it is paused.

This is what debuggers do.

---

## Breakpoints

A breakpoint is an instruction to the debugger: "When execution reaches this address, stop the program and give me control."

In AILang, the language-level primitive is `DebugBreak`. Per the AILANG Debug System Manual, `DebugBreak` is one of the core fully functional features (along with `DebugAssert`, `DebugPerf`, and `DebugMemory.Dump`). It compiles to a no-op in production builds.

There are two common ways breakpoints are implemented at the machine level:

1. **Software breakpoints** — The debugger replaces the instruction at the breakpoint address with a special trapping instruction (on x86 this is `INT3`, a single-byte `0xCC`). When the CPU executes that byte, it raises an exception, the kernel delivers a signal to the debugger, and the debugger takes over.

2. **Hardware breakpoints** — Modern CPUs have a small number of special debug registers. You can tell the CPU "stop if the instruction pointer equals this address" or "stop if this memory location is read or written." These do not require modifying the code.

When a breakpoint is hit, the debugger can:
- Show you the source line (if it has debug information).
- Let you examine variables, memory, registers.
- Let you continue, step over the next line, step into a function, etc.

---

## Single-Stepping

Once the program is stopped, you can execute one instruction (or one source line) at a time.

- **Step over** — Execute the next line. If it is a function call, run the whole function without stopping inside it.
- **Step into** — If the next line is a function call, stop at the first instruction inside that function.
- **Step out** — Run until the current function returns, then stop in the caller.

This is an incredibly powerful way to understand control flow. Instead of trying to simulate the entire program in your head, you can watch it execute one step at a time and see exactly where your mental model diverged from reality.

---

## What the Debugger Actually Does

A debugger is just another program. On Unix-like systems it uses the `ptrace` system call (or equivalent) to:

- Attach to the target process.
- Read and write its memory.
- Read and write its registers.
- Set breakpoints (by writing `INT3` or using hardware debug registers).
- Receive notifications when the target stops (breakpoint, signal, exit, etc.).

When you type `print x` in GDB, the debugger looks up the address of `x` from the debug information, reads the memory at that address from the target process, and displays the value.

When you type `next`, the debugger sets a temporary breakpoint on the next line (or uses single-step mode) and lets the target run until it hits that breakpoint.

There is no magic. The debugger is using the same mechanisms the operating system provides for process inspection and control.

---

## A Minimal GDB Session

Here is a typical interaction:

```
(gdb) break main
(gdb) run
Breakpoint 1, main () at hello.ailang:5
5         PrintMessage("Hello\n")
(gdb) print some_variable
$1 = 42
(gdb) next
6         x = Add(some_variable, 10)
(gdb) step
... steps into Add ...
(gdb) info registers
... shows CPU registers ...
(gdb) x/10xb some_pointer
... examines raw memory ...
```

You do not need to become a GDB expert to benefit from this level of debugging. You only need to understand the basic ideas: breakpoints, examining state, and stepping.

---

## Hardware Connection

At the very bottom, all of this rests on the CPU's ability to:
- Raise an exception on a particular instruction (`INT3` or hardware breakpoint).
- Single-step one instruction at a time (the Trap Flag on x86, for example).
- Allow another process (the debugger) to read and write its registers and memory via the operating system.

These are the same mechanisms used by the operating system itself for process control, security, and virtualization.

---

## Key Concepts

- A breakpoint replaces an instruction with a trap (or uses hardware debug registers).
- Single-stepping lets you execute the program one instruction or line at a time.
- The debugger is just another program using the OS's process inspection facilities.
- Being able to stop and look around is often the fastest way to resolve "I have no idea what this code is doing."

---

*Next: We look at the final level of debugging in this progression — measuring performance so you can optimize based on data rather than guesswork.*