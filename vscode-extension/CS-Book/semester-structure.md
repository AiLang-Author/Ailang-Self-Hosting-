# CS 101: Computer Science Disambiguated
## Semester Structure — 16 Weeks
### Sean Collins, 2 Paws Machine and Engineering

---

## Philosophy

Most intro CS courses pick one of three lanes:

**The theory lane.** Boolean algebra, finite automata, big-O notation, type systems. Students can reason about computation but can't build anything. They know what a Turing machine is but have never seen a register.

**The vocational lane.** "Type this. Run this. Now add a button. Now connect it to a database." Students can build things but don't know why anything works. When something breaks outside the tutorial path, they're stuck.

**The math lane.** Starts with number theory, set theory, or discrete math. Important material, but it front-loads abstraction before the student has any concrete experience to anchor it to. By the time they write code, the math feels disconnected.

This course takes a fourth lane: **machine-up, concept-first.**

The student meets the hardware before they write code. They write code before they study patterns. They study patterns before they build projects. Each layer has a reason to exist because they experienced the layer below it.

The key insight: hardware isn't advanced. It's foundational. A student who knows what a register is, what RAM does, and what a syscall is will learn *any* programming language faster — because every language is eventually doing those things.

---

## Course Materials

**Book 1:** *How Computers Compute: A Primer* (Weeks 1–3)
**Book 2:** *Computer Science Disambiguated* (Weeks 4–16)
**Software:** AILANG compiler (self-hosting), Linux environment, GDB
**No other textbooks required.**

---

## Assessment Structure

| Component | Weight | Description |
|---|---|---|
| Weekly labs | 30% | Hands-on exercises, done in class or lab period |
| Three projects | 30% | Calculator (Wk 10), Text Editor (Wk 13), Database (Wk 15) |
| Midterm exam | 15% | Weeks 1–8 material (hardware + core language) |
| Final exam | 15% | Comprehensive, emphasis on Weeks 9–16 |
| Participation | 10% | Lab attendance, peer code review, in-class exercises |

Labs are pass/fail graded on completion and understanding, not polish. Projects are graded on correctness, with partial credit for working subsections. Exams include both conceptual questions ("draw what the stack looks like after this function call") and short code-writing problems.

---

## Week-by-Week

### UNIT 1: THE MACHINE (Weeks 1–3)
*Book 1: How Computers Compute*

The student's only job in this unit is to understand what's inside the computer and how the parts work together. No code. No programming. Just the machine.

---

#### Week 1 — Bits, Numbers, and the Clock

**Reading:** Primer Chapters 1–3 (Bits, Counting Like a Computer, The Clock)

**Lecture 1: What's in the Box**
Open a computer (or show high-res photos). Point at the CPU, RAM sticks, SSD, bus connectors. Name each one. "By the end of this course, you'll know exactly what each of these does and how to tell them what to do."

Introduce bits. One light switch: on or off. Two switches: four combinations. Three switches: eight. Eight switches: 256. That's a byte. Build the intuition physically — actual switches or a simulator on screen.

**Lecture 2: Counting in Binary and Hex**
Binary counting on fingers (one hand = 0–31, not 0–5). Place value — same rules as decimal, different base. Convert a few numbers by hand both directions.

Introduce hex as a compression of binary. Four bits = one hex digit. One byte = two hex digits, always. Show why programmers use hex: `FF` is easier to read than `11111111`, and both mean 255.

The clock: a crystal vibrating, producing ticks. GHz = billions of ticks per second. Nothing happens between ticks. The clock is coordination, not computation.

**Lab 1: Number Systems**
Convert between binary, decimal, and hex by hand. Twenty problems, increasing difficulty. Last five problems: "what is byte `0x41`?" → look up ASCII table → it's the letter "A." First contact with the idea that the same bits mean different things in different contexts.

Bonus: binary addition by hand. Carry rules are identical to decimal, just happens more often.

---

#### Week 2 — CPU, Registers, RAM, and the Bus

**Reading:** Primer Chapters 4–7 (CPU, Registers, RAM, The Bus)

**Lecture 3: Fetch, Decode, Execute**
The CPU loop. Draw it on the board. Fetch an instruction from memory. Decode what it means. Execute it. Move to the next one. That's all the CPU does, forever.

Registers: the CPU's hands. Name them (RAX, RBX, etc.). There are only about 16. They're fast because they're physically inside the CPU. Everything the CPU works on passes through registers.

**Lecture 4: RAM and the Bus**
RAM as a numbered notebook. Every byte has an address. The CPU asks for an address, RAM returns the value. "Random access" means any address, same speed.

The bus: address lines (where), data lines (what), control lines (read or write). Draw the CPU-RAM conversation as a sequence diagram. CPU puts address on bus → RAM reads address → RAM puts value on data lines → CPU grabs it.

Cache: the cheat sheet. L1/L2/L3. Why cache exists (RAM is 100x slower than registers). Cache hits vs misses. You never manage cache directly — the hardware handles it — but knowing it exists explains why some code is faster than other code.

**Lab 2: Tracing by Hand**
Give students a simple program as a list of instructions (in pseudocode, not AILANG yet):

```
LOAD R1, 5
LOAD R2, 3
ADD R1, R2
STORE R1, [address 100]
```

Students trace through it by hand: draw registers, draw RAM locations, show the value at each step. Do five of these, increasing complexity. Last one includes a conditional jump ("if R1 > 10, jump to instruction 7").

This is the most important lab in the course. If they can trace instructions by hand, they understand what computing is.

---

#### Week 3 — Instructions, the OS, and the Full Picture

**Reading:** Primer Chapters 8–14 (Instructions, Journey of an Instruction, Hello to Screen, Storage, OS, Putting It All Together)

**Lecture 5: What an Instruction Looks Like**
Show actual x86 bytes. `48 01 D8` = ADD RAX, RBX. Break down the encoding: REX prefix, opcode, ModR/M. Students don't memorize this — the point is that instructions are just bytes, and the CPU recognizes patterns.

Follow one instruction through the full journey: fetch (cache/RAM), decode (recognize the pattern), execute (ALU does the math), writeback (result goes to a register).

**Lecture 6: The Operating System and the Full Stack**
The OS as traffic cop. Multitasking: each program gets a time slice. Memory protection: virtual address spaces. System calls: programs ask the OS to do privileged things (write to screen, read a file).

Follow "Hello" from bytes in memory → syscall → kernel → terminal → pixels → screen. This is the Schoolhouse Rock moment. Draw the whole path on the board.

The storage hierarchy: registers → cache → RAM → SSD → HDD. Each level bigger and slower. Show the table from the primer. Let the numbers sink in — RAM is 100x slower than L1, an SSD is 1000x slower than RAM.

**Lab 3: The Full Trace**
Students get a complete (tiny) program as machine instructions in hex. They trace the fetch-decode-execute cycle for each instruction, tracking: instruction pointer, registers, RAM contents. The program writes "Hi" to stdout via a syscall.

Last exercise: "You just did what the CPU does. You were the computer. The CPU does this 3 billion times per second."

**This ends Unit 1.** The student has never written code, but they know what a CPU does, how RAM works, what a bus is, what cache is for, and how an instruction becomes a result. Everything from here forward is "now let's tell this machine what to do."

---

### UNIT 2: CORE LANGUAGE (Weeks 4–8)
*Book 2: Chapters 1–11*

The student writes their first code and builds up to structured data and contracts. Every concept connects back to the hardware they learned in Unit 1.

---

#### Week 4 — First Programs, Values, and Decisions

**Reading:** Book 2 Chapters 1–2 (Your First Program, Values and Decisions)

**Lecture 7: Hello, World — For Real This Time**
Students write, compile, and run their first AILANG program. `SubRoutine.Main`, `PrintMessage`, `RunTask`. It works.

Then: look at the binary. It's about 4KB. "Remember from Week 3 — the CPU reads instructions from memory. This file IS those instructions. The compiler turned your English-like code into the bytes the CPU reads." Show the ELF header in a hex dump. Point at the string "Hello" sitting in the data section.

**Lecture 8: Variables, Numbers, and Decisions**
Variables as named stack offsets. "In Week 2, you traced `STORE R1, [address 100]`. A variable is the compiler picking that address for you and letting you use a name instead of a number."

`IfCondition`/`ThenBlock`/`ElseBlock`. "In Week 2, you traced a conditional jump. This is the same thing — the compiler writes the CMP and JMP for you."

**Lab 4: Basics**
Write 8–10 small programs: print a message, store values in variables, make decisions with IfCondition, combine conditions with And/Or. Each program: write it, compile it, run it, predict what it does before running.

Last exercise: Write a program that takes different paths depending on a variable's value. Predict which path executes. Run it. Were you right?

---

#### Week 5 — Loops and Functions

**Reading:** Book 2 Chapters 3–4 (Repetition, Functions)

**Lecture 9: Loops**
`WhileLoop` as CMP + conditional JMP backward. Draw the assembly-level pattern on the board, then show the AILANG version. "Same structure. The compiler writes the jumps."

Counting patterns, accumulation patterns. `ExitLoop` and `ContinueLoop` as forward and backward jumps with different targets.

Infinite loops: if nothing in the body changes the condition, the loop can't stop. This isn't a mystery — it's a structural property you can check by reading the code.

**Lecture 10: Functions as Contracts**
SubRoutine vs Function. Input/Output/Body. The calling convention: CALL pushes return address, prologue sets up stack frame, RET pops and returns.

"In Week 2, you had registers and RAM. A function call means: save your current registers, set up new space on the stack, do the work, put the answer in RAX, restore everything, jump back. The compiler writes all of this. You write `Input: n: Integer`."

ReturnValue. The contract: if you declare Output, you must return something. The compiler checks this.

**Lab 5: Loops and Functions**
Write a loop that sums 1 to 100. Write a function that computes factorial. Write a function that searches an array for a value (even though arrays aren't formally introduced yet — give them a pre-built array and ArrayGet).

Key exercise: Write a function with a bug (infinite loop, off-by-one, missing return). Trade with a partner. Find and fix each other's bug.

---

#### Week 6 — Arithmetic, Logic, and Scope

**Reading:** Book 2 Chapters 5–6 (Arithmetic and Logic, Scope)

**Lecture 11: Named Operations**
`Add`, `Subtract`, `Multiply`, `Divide`, `Modulo` — each maps to a CPU instruction. Show the mapping: `Add(a, b)` → `ADD RAX, RBX`. "The language names what the CPU does."

Boolean logic: `And`, `Or`, `Not`. Comparisons return integers (1 or 0), which means they compose: `And(GreaterThan(x, 0), LessThan(x, 100))`.

Bitwise operations: `BitwiseAnd`, `BitwiseOr`, `LeftShift`, `RightShift`. Flags and masks — encoding multiple booleans in a single integer. Brief intro, revisited when we build data structures.

**Lecture 12: Scope and Lifetime**
Local variables live on the stack. When the function returns, the stack pointer moves and the space is reclaimed. Scope isn't a rule — it's physics.

Block scope: variables inside an `IfCondition` or `WhileLoop` body are local to that block. Why this prevents bugs: if you can't name it, you can't accidentally modify it.

**Lab 6: Computation and Scope**
Build a simple calculator: read two numbers from variables, perform an operation based on a flag. Use all arithmetic operations.

Scope exercises: predict whether code compiles (accessing a variable outside its scope = error). Deliberately write scope violations, see the compiler catch them.

Bitwise exercises: use `BitwiseAnd` to check if a number is even. Use `LeftShift` to multiply by powers of 2.

---

#### Week 7 — Shared State, Strings, and Arrays

**Reading:** Book 2 Chapters 7–9 (FixedPool, Strings, Arrays)

**Lecture 13: FixedPool and Strings**
FixedPool: named shared state, declared with types and mutability. Contrast with "just make a global variable." Every access is qualified (`Config.debug`), every field is typed and annotated.

Strings as pointers to null-terminated byte sequences. "The variable doesn't hold the text — it holds the address where the text starts. Remember RAM from Week 2? The string is bytes in RAM. The variable is an address."

StringLength walks memory until it hits a zero byte. StringCompare compares byte by byte. StringCopy allocates new memory and copies bytes.

**Lecture 14: Arrays**
Contiguous memory. Index arithmetic: `base + index × 8`. ArrayGet, ArraySet, ArrayLength, ArrayDestroy. "Remember from Week 2 when you computed addresses by hand? That's what ArrayGet does."

Bounds: accessing index 10 of a 10-element array reads whatever is next in memory. Undefined behavior. Catastrophic. Bounds checking prevents this.

Library.Array + Library.Arrays: the current recommended dynamic arrays and collections (Stack, Queue, List, IHash/SHash). Replaces deprecated XArrays / TArrays. Growth, sorting, binary search, etc. via the library on top of raw contiguous memory + index arithmetic.

**Lab 7: Strings and Arrays**
String exercises: compute the length of a string manually (WhileLoop, check each byte). Compare two strings character by character. Reverse a string into a new buffer.

Array exercises: create an array, fill it with squares (0, 1, 4, 9, 16...), search for a value, find the maximum.

---

#### Week 8 — Structured Data and Contracts

**Reading:** Book 2 Chapters 10–11 (LinkagePool, Data Contracts)

**Lecture 15: LinkagePool**
Records: grouping related fields. LinkagePool declaration, AllocateLinkage, field access via @ or dot. Direction= attributes for contracts. "p@x is the compiler computing base + offset."

Nested pools: records containing records. Build a small example — a Point with x/y, a Line with two Points.

**Lecture 16: Contracts and Review**
Input:/Output: contracts on Functions + LinkagePool Direction=Input/Output/InOut attributes (enforced when pools are passed as parameters). FixedPool for SubRoutine cross-call state. The compiler catches violations at compile time.

Review session for midterm. Walk through the full stack one more time: bits → numbers → clock → CPU → registers → RAM → bus → cache → instructions → OS → source code → compilation → execution.

**Lab 8: Structured Data + Midterm Prep**
Build a student record (LinkagePool with name, grade, ID). Write functions to create, display, and compare records. Use Input/Output contracts.

Practice midterm problems: hand-trace instruction execution, predict program output, identify scope errors, convert between binary/hex/decimal, explain what a syscall does.

**MIDTERM EXAM — end of Week 8**

---

### UNIT 3: DEBUGGING AND SYSTEMS (Weeks 9–11)
*Book 2: Chapters 12–21*

The student goes deeper into memory, learns the debug system, and understands the OS interface.

---

#### Week 9 — Memory: Addresses, Allocation, and Pointers

**Reading:** Book 2 Chapters 12–14 (Memory, Allocation, Pointers)

**Lecture 17: What Memory Actually Is**
Addresses. Every byte has one. The stack grows automatically; the heap you manage yourself. StoreValue and Dereference as the fundamental operations.

"Everything you've used so far — variables, strings, arrays, pools — is built on two operations: write a value to an address, read a value from an address."

**Lecture 18: Allocation and Pointers**
Allocate/Deallocate. Memory leaks: allocate without deallocating, the memory is gone until the program exits. Arena allocator: slab allocation, free lists, O(1) allocation.

Pointers: a variable that holds an address. Pointer arithmetic. Null. Aliasing: two pointers to the same data. "Copy the pointer" vs "copy the data."

**Lab 9: Memory**
Allocate a buffer, write values into it with StoreValue, read them back with Dereference. Build a tiny linked list by hand: allocate nodes, set next pointers.

Memory leak exercise: deliberately leak memory in a loop. Use DebugMemory.LeakCheck to see the accumulation. Fix it.

---

#### Week 10 — Debugging (All Four Levels)

**Reading:** Book 2 Chapters 15–20 (Correctness, Assertions, Tracing, Memory Inspection, Breaking, Performance)

**Lecture 19: Correctness and Assertions**
Preconditions, postconditions, invariants. DebugAssert as executable documentation. "State what must be true. The computer checks it for you."

Tracing: DebugTrace.Entry/Exit/Point. "What you think your program does vs what it actually does."

**Lecture 20: Memory Inspection, Breakpoints, and Profiling**
DebugMemory.Dump — see raw bytes. Pattern fill with 0xDEADBEEF — detecting uninitialized reads. LeakCheck.

DebugBreak → INT3 → GDB. Live demo: set a breakpoint, inspect registers, step through instructions. "You're watching the fetch-decode-execute cycle from Week 2, for real."

DebugPerf: measuring, not guessing. RDTSC. Profile first, optimize second.

**Lab 10: Debug Lab**
Students receive a program with five deliberate bugs (off-by-one, null pointer, memory leak, infinite loop, uninitialized read). Using all four debug levels, find and fix each bug. Document which debug tool found each bug and why.

This is one of the most important labs. It teaches debugging as a systematic practice, not frantic guessing.

---

#### Week 11 — The Operating System Interface

**Reading:** Book 2 Chapter 21 (What the Operating System Does For You)

**Lecture 21: System Calls**
The syscall interface. write, read, open, close, mmap. File descriptors. "Your program runs in user space. It asks the kernel for anything that touches the outside world."

Trace PrintMessage from AILANG source → compiled syscall → kernel → terminal. Live demo: strace a running program, see the system calls scroll by.

**Lecture 22: Files**
OpenFile, ReadFile, WriteFile, CloseFile. Files as streams of bytes. Reading and writing as system calls that transfer bytes between RAM and storage.

Build toward Project 3 (database) by showing that files are just organized byte storage.

**Lab 11: System Calls and Files**
Write a program that opens a file, writes data, closes it, reopens it, reads the data back, and verifies it matches. Use DebugAssert to check correctness.

Exercise: write a simple `cat` clone — read a file and print its contents to stdout.

---

### UNIT 4: THE COMPILER AND ARCHITECTURE (Weeks 12–13)
*Book 2: Chapters 22–26*

---

#### Week 12 — How the Compiler Works

**Reading:** Book 2 Chapters 22–24 (The Compiler, The Optimizer, Self-Hosting)

**Lecture 23: Lexing, Parsing, Code Generation**
The three phases. Lex: characters → tokens. Parse: tokens → AST. Codegen: AST → machine code.

Show the AILANG compiler's actual code for each phase. The students have been using the compiler all semester — now they see how it works. The TryCompile dispatch chain. The Emit layer. The X86 byte emission.

"This compiler is written in AILANG. It compiles itself. Every feature you've learned — strings, arrays, pools, functions, loops — this compiler uses all of them."

**Lecture 24: The Optimizer and Self-Hosting**
Peephole optimization: recognize simple cases, emit fewer instructions. The push/pop elimination pattern.

Self-hosting: the bootstrap problem. Python compiler → AILANG compiler → AILANG compiler compiles itself. What this proves about language completeness.

**Lab 12: Compiler Exploration**
Students run the compiler with debug output enabled. Trace a simple program through lexing (see the tokens), parsing (see the AST), and code generation (see the emitted bytes).

Exercise: add a new simple operation to the compiler. Give students a template module. They write a TryCompile handler for a new operation (e.g., `DoubleIt(x)` that compiles to `ADD RAX, RAX`). They follow the existing module pattern exactly. The first time a student modifies a compiler and it works is a landmark moment.

---

#### Week 13 — Architecture and Error Handling

**Reading:** Book 2 Chapters 25–26 (Modular Design, Error Handling)

**Lecture 25: Modular Design**
The TryCompile pattern as a general design principle. Additive architecture: new features are new modules, existing modules don't change. How the compiler organizes 80 files without inheritance, base classes, or frameworks.

**Lecture 26: Error Handling**
Expected vs unexpected errors. TryBlock/CatchError/FinallyBlock. Error propagation. Writing error messages that help: what happened, where, what to do about it.

**Lab 13: Text Editor Project (Project 2)**
Build a minimal text editor. Raw terminal input, line buffer, cursor movement, insert/delete. This project exercises: strings, arrays, memory management, system calls, loops, and error handling. Students work on this across Week 13, with a submission deadline at end of week.

---

### UNIT 5: DATA STRUCTURES AND PROJECTS (Weeks 14–16)
*Book 2: Chapters 27–32*

---

#### Week 14 — Data Structures

**Reading:** Book 2 Chapters 27–28 (Data Structures, Concurrency)

**Lecture 27: Data Structures from First Principles**
Linked list, stack, queue, ring buffer, tree, hash map — each built from Allocate, StoreValue, Dereference, and pool fields. No standard library — students build them.

"You now have all the tools. A linked list is: allocate a node, store a value, set a next pointer. A hash map is: an array of linked lists plus a hash function. There's no magic. It's memory and pointers organized with intent."

**Lecture 28: Concurrency**
Fork, process isolation, shared state, message passing, ring buffers as channels. AILANG's pool model and why explicit shared state is easier to reason about.

This is an overview, not a deep dive. The goal is awareness: what concurrency is, why shared mutable state is dangerous, what the alternatives are.

**Lab 14: Data Structures**
Implement a linked list and a hash map from scratch. Insert, search, delete. Use DebugAssert to verify correctness. Use DebugPerf to measure search time as the structure grows.

---

#### Week 15 — Database Project and Review

**Reading:** Book 2 Chapters 29–31 (Calculator, Text Editor, Database)

**Lecture 29: Building a Database**
Fixed-length records in a file. Sequential scan. Building an index. Query by field. "A database is organized file I/O with indexing. Real databases are this, scaled up."

**Lecture 30: Course Review**
Walk the full path one final time: bits → numbers → clock → CPU → registers → RAM → cache → bus → OS → source code → lexer → parser → AST → codegen → optimizer → ELF → execution → syscalls → results.

Every concept from Week 1 connects to every concept from Week 15. The student can trace the entire pipeline.

**Lab 15: Database Project (Project 3)**
Build a simple database: store records in a file, read them back, sequential scan, index-based lookup. Submission end of week.

---

#### Week 16 — Final Exam and Reflection

**Lecture 31: What You Know Now**
Day one: you didn't know what a CPU does. Now you can trace an instruction through fetch-decode-execute, write programs that manage memory and files, debug them at every level, and you've seen how the compiler that compiles your code works — written in the same language you've been writing all semester.

Where to go next: C (Appendix E), Rust (Appendix F), operating systems, networking, graphics, compilers. Every one of these fields builds on what you now understand.

**FINAL EXAM — end of Week 16**

Conceptual and practical. Example questions:
- Trace this program's stack frames through two nested function calls.
- This code has a memory leak. Find it and fix it.
- Convert `0xDEAD` to binary.
- What system call does PrintMessage use? What are its arguments?
- Write a function that reverses a linked list.
- Explain why cache makes sequential array access faster than random access.
- What does the TryCompile pattern buy you when adding a new compiler feature?

---

## Instructor Notes

**The Unit 1 bet is the whole course.** Three weeks without writing code feels risky. It isn't. Students who understand the hardware learn the language faster, debug more effectively, and retain more. Every concept in Weeks 4–16 lands harder because it connects to something physical they already understand. If you're tempted to cut Unit 1 short, don't.

**Labs are where learning happens.** Lectures introduce concepts. Labs build understanding. The hand-tracing exercises in Weeks 1–3 are particularly important — they build the mental model that everything else rests on.

**The debug lab (Week 10) is the second most important lab after the hand-tracing labs.** Students who learn to debug systematically spend less time stuck on projects. Teach debugging before the projects, not during.

**The compiler lab (Week 12) is the "wow" moment.** When students modify the compiler that compiles their code — and it works — the entire course clicks. They realize the compiler is just a program, written in the language they know, that does the transformations they've been watching all semester.

**Grading philosophy:** Reward understanding over polish. A project that's 70% complete but the student can explain exactly how it works and what's missing is worth more than a 100% complete project the student copied. Oral check-ins during lab time are valuable for assessing real understanding.

**This course replaces:** Introduction to Programming, Introduction to Computer Architecture (partially), and the first third of a Data Structures course. Students leaving this course are prepared for intermediate systems programming, data structures and algorithms, operating systems, or compiler construction.
