# Chapter 21: What the Operating System Does For You

**What you'll learn:** The boundary between your program and the rest of the world. What a system call actually is. File descriptors, processes, memory protection, and why you cannot just talk directly to hardware.

---

## Your Program Does Not Own the Machine

When your program is running, it feels like it is in charge. It can read files, write to the screen, allocate memory, and so on.

This is an illusion, carefully maintained by the operating system.

Your program runs in **user space**. It has very limited direct access to hardware. It cannot:
- Directly read or write arbitrary physical memory (only its own virtual address space).
- Directly talk to disk controllers, network cards, or the display.
- Decide which other programs get to run and for how long.
- Access files belonging to other users without permission.

All of these things are mediated by the operating system kernel, which runs in **kernel space** with full hardware privileges.

---

## System Calls — The Narrow Gate

The only way a normal program can ask the kernel to do something on its behalf is through a **system call**.

In AILang this is very visible. For example, when the Arena needs more memory, it ultimately makes `mmap` or `brk` syscalls (as described in the Memory Management Reference Manual). The compiler emits the actual syscall instruction sequence (often using specific registers per the platform ABI).

This explicitness is one of the reasons AILang is a good teaching language for systems programming.

A system call is a controlled transfer from user mode to kernel mode. On x86-64 Linux, this is typically done with the `syscall` instruction.

Examples of common system calls:
- `write` — write bytes to a file descriptor (screen, file, socket, etc.)
- `read` — read bytes from a file descriptor
- `open` / `close` — open and close files
- `mmap` — map files or anonymous memory into the process's address space
- `fork` / `execve` — create new processes
- `exit` — terminate the current process

When you call `PrintMessage` in AILang, it eventually results in one or more `write` system calls. The compiler and runtime do not have the privilege to write directly to the terminal hardware — they must ask the kernel.

---

## File Descriptors

One of the most elegant abstractions in Unix is the **file descriptor**.

A file descriptor is a small integer that represents an open resource — a file, a terminal, a socket, a pipe, etc.

By convention:
- 0 = standard input
- 1 = standard output
- 2 = standard error

When you do `PrintMessage("Hello\n")`, the runtime is effectively doing something like:

"Write the bytes of 'Hello\n' to file descriptor 1."

The kernel looks up what file descriptor 1 means for your process (probably your terminal) and performs the actual write.

This uniform interface is incredibly powerful. The same code can write to a terminal, a file on disk, a network socket, or a pipe to another program, without knowing or caring which one it is.

---

## Memory Protection and Virtual Address Spaces

One of the most important jobs of the operating system (with help from the CPU's MMU) is to give each process the illusion that it has its own large, contiguous, private memory space.

In reality, physical RAM is shared among many processes (and the kernel itself). The MMU translates every memory access from a **virtual address** (what your program sees) to a **physical address** (actual RAM).

This provides:
- **Isolation** — One buggy or malicious program cannot corrupt another program's memory (except through explicit shared memory mechanisms).
- **Security** — The kernel can prevent user programs from accessing kernel memory or memory belonging to other users.
- **Flexibility** — The kernel can move physical pages around, swap them to disk, share them between processes (for shared libraries, copy-on-write, etc.) without the programs noticing.

When you do `Allocate(1024)`, the kernel eventually updates page tables so that a range of your virtual addresses maps to some physical pages. Your program never deals with physical addresses directly.

---

## Processes and Scheduling

The operating system creates the illusion that many programs are running at the same time, even on a machine with only a few CPU cores.

It does this through **preemptive multitasking**:
- Each program (process) gets a small slice of CPU time.
- When the time slice expires (or the process blocks waiting for I/O), the kernel saves the process's state (registers, instruction pointer, etc.) and switches to another process.
- This switching is called a **context switch**.

From the perspective of each individual program, it appears to have the CPU mostly to itself. The operating system hides the fact that it is constantly being paused and resumed.

---

## Why All of This Matters

Understanding the operating system boundary is essential for systems programming:

- You cannot "just write to the screen" — you must go through the kernel.
- You cannot "just access any memory" — only what the kernel has mapped into your address space.
- Performance often depends on understanding what is a cheap local operation versus what requires a system call (context switch, privilege change, etc.).
- Security and correctness often depend on understanding what the kernel guarantees and what it does not.

AILang's explicit nature makes these boundaries more visible than in languages that try to hide the OS behind high-level abstractions.

---

## Key Concepts

- User space vs. kernel space.
- System calls as the controlled interface between them.
- File descriptors as a uniform abstraction for I/O resources.
- Virtual memory and the MMU providing isolation and flexibility.
- Processes and preemptive multitasking.

---

*Next: We look at the compiler itself — how your AILang source code is turned into the machine instructions and data that the operating system eventually loads and runs.*