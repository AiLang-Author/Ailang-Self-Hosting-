# Chapter 1: Your First Program

**What you'll learn:** What a program actually is. What happens when you compile it. What the resulting file contains and how the operating system turns it into a running process. The relationship between source code, machine instructions, and the hardware that executes them.

---

## The Simplest Possible Program

Here is a complete, working AILang program:

```ailang
SubRoutine.Main {
    PrintMessage("Hello, World!\n")
}

RunTask(Main)
```

When you compile and run it, the words "Hello, World!" appear on your screen.

This is not magic. It is the result of a long, precise chain of transformations. This chapter walks through that chain so you understand exactly what just happened.

---

## Step 1: Writing the Source

You wrote text in a file. That text follows strict rules (the AILang grammar):

- `SubRoutine.Main` declares a subroutine named `Main`.
- `PrintMessage("Hello, World!\n")` calls a built-in operation that sends characters to standard output.
- `RunTask(Main)` tells the runtime to execute the `Main` subroutine.

Nothing in this file is "executed" directly by the CPU. It is a human-readable description of what you want the computer to do.

---

## Step 2: Compilation — Source to Machine Code

You run the AILang compiler on the source file:

```bash
./ailang.x hello.ailang hello.x
```

The compiler performs three major transformations:

1. **Lexing** — Breaks the character stream into tokens (`KEYWORD:SubRoutine`, `DOT`, `IDENTIFIER:Main`, `LBRACE`, `IDENTIFIER:PrintMessage`, `LPAREN`, `STRING:"Hello, World!\n"`, ...).

2. **Parsing** — Builds an Abstract Syntax Tree (AST) that represents the logical structure of the program. The tree knows that `Main` contains a call to `PrintMessage` with a string argument.

3. **Code Generation** — Walks the AST and emits actual x86-64 machine instructions. The call to `PrintMessage` eventually becomes a `write` system call (the only way user programs can produce output on Linux).

The result is a small ELF executable (typically a few kilobytes for this program).

---

## Step 3: What the Binary Actually Contains

The output file `hello.x` is not "your code" anymore. It is a carefully structured container with several sections:

- **ELF Header** — Tells the operating system "this is an executable for x86-64 Linux."
- **Program Headers** — Describe where the code and data should be loaded into memory.
- **Code Section** (`.text`) — The actual machine instructions the CPU will execute.
- **Data Section** (`.data` / `.rodata`) — Your string literal `"Hello, World!\n"` stored as raw bytes, plus any constants.
- **Symbol Table** (optional in stripped builds) — Names for debugging (not needed at runtime).

When you run `./hello.x`, the operating system:
1. Reads the ELF headers.
2. Maps the code and data sections into memory at the addresses the headers specify.
3. Sets the CPU's instruction pointer to the program's entry point.
4. Starts executing.

---

## Step 4: Execution — From Instructions to Photons

The CPU now performs its fundamental loop billions of times per second:

1. **Fetch** an instruction from memory.
2. **Decode** what the instruction means.
3. **Execute** it (this may involve the arithmetic unit, memory access, or a system call).
4. Advance to the next instruction (or jump if the instruction says so).

Your `PrintMessage("Hello, World!\n")` eventually expands (through library and compiler transformations) into a sequence that ends with a `syscall` instruction with the `write` system call number.

The kernel receives the request, copies the bytes from your program's memory to the terminal device, and returns. The terminal (or terminal emulator) renders the characters as pixels. Those pixels are sent to your monitor as electrical signals. The monitor lights up the appropriate dots.

From your source code to light hitting your eyes: a chain of precise, mechanical steps with no hidden magic.

---

## Why This Matters

Most introductory programming material hides this chain behind layers of convenience. You are told "just print the string" without ever being shown what that actually means to the machine.

AILang's design philosophy is the opposite: **name the action**. `PrintMessage` is not pretending to be a C `printf`. It is a clear verb that ultimately means "ask the operating system to write these bytes."

By starting here — with a working program and a complete accounting of what it does — every later concept (variables, loops, memory allocation, data structures, compilation itself) can be connected to something physical you have already seen.

---

## Key Concepts Introduced

- Source code vs. compiled binary
- ELF executable format
- The CPU's fetch-decode-execute cycle
- System calls as the bridge between user programs and the kernel
- The value of explicit naming over syntactic magic

---

## Hardware Connection

Every high-level statement you write eventually becomes a small number of machine instructions and (when necessary) system calls. There is no other path from your ideas to results on the screen. Understanding this path is the foundation of the entire course.

---

*Next: We look at how the machine represents and manipulates values (numbers, truth, text) and how it makes simple decisions.*