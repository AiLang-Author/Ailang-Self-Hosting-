# Computer Science Disambiguated

## Using AILang to Teach Computer Science from the Ground Up

**Author:** Sean Collins  
**Status:** In Progress

---

## The Core Philosophy

This book rejects the dominant model of introductory computer science education — the "type this and pray" approach that dominates the first year (and often the first two years) at most institutions.

Instead, it follows a deliberately ground-up, machine-first path:

1. **First, understand the machine.** Students spend the initial weeks learning how computers actually work at the hardware level — bits, binary, the clock, CPU, registers, RAM, bus, cache, instructions, system calls, and the operating system — before writing a single line of code.
2. **Then, and only then, learn to program it.** Programming concepts are introduced using AILang, a language designed for radical explicitness. Every major concept is immediately connected back to what is actually happening in the hardware.
3. **Remove the magic.** No hidden control flow, no mysterious precedence rules, no "it just works." Students build a durable mental model they can reason with for the rest of their careers.

The result is a genuine computer science education rather than a collection of surface-level incantations.

---

## Book Structure

This work is organized as two closely related volumes that can be used together or independently.

### Volume 1: How Computers Compute — A Primer

A hardware-first introduction with **no programming**. This book teaches what is actually inside a computer and how the parts work together.

**Purpose:** Build the essential mental model before any code is written.

**Chapters (from the primer):**
- Chapter 1: The Only Thing a Computer Can Do (bits and states)
- Chapter 2: Counting Like a Computer (binary and hex)
- Chapter 3: The Clock
- Chapter 4: The CPU — One Instruction at a Time
- Chapter 5: Registers — The CPU's Hands
- Chapter 6: RAM — The Big Notebook
- Chapter 7: The Bus — Roads Between Parts
- Chapter 8: Cache — The Cheat Sheet
- Chapter 9: The Instruction — What It Looks Like
- Chapter 10: The Journey of an Instruction
- Chapter 11: How "Hello" Gets to Your Screen
- Chapter 12: Storage — Remembering When the Power's Off
- Chapter 13: The Operating System — The Traffic Cop
- Chapter 14: Putting It All Together

**Recommended use:** Weeks 1–3 of a 16-week CS 101 course. No code is written during this phase.

---

### Volume 2: Computer Science Disambiguated

The main programming and computer science book. It teaches how to program and how to think about computation — always with the hardware model from Volume 1 as the foundation.

**Core Thesis:** By using a radically explicit language (AILang), we can eliminate the magic that usually obscures the connection between high-level ideas and what the machine is actually doing.

**Part I: No Magic Foundations**
- Chapter 1: Your First Program
- Chapter 2: Values and Decisions
- Chapter 3: Repetition
- Chapter 4: Functions — Contracts for Computation
- Chapter 5: Arithmetic and Logic

**Part II: Organization**
- Chapter 6: Scope — Who Can See What
- Chapter 7: FixedPool — Named Shared State
- Chapter 8: Strings
- Chapter 9: Arrays — Ordered Collections
- Chapter 10: Structured Data — LinkagePool
- Chapter 11: Data Contracts — Direction Enforcement

**Part III: Memory**
- Chapter 12: What Memory Actually Is
- Chapter 13: Allocation — Asking for Memory
- Chapter 14: Pointers — Addresses as Values

**Part IV: Debugging and Correctness**
- Chapter 15: Thinking About Correctness
- Chapter 16: Debug Level 1 — Assertions
- Chapter 17: Debug Level 2 — Tracing
- Chapter 18: Debug Level 3 — Memory Inspection
- Chapter 19: Debug Level 4 — Breaking and Stepping
- Chapter 20: Performance — Measuring, Not Guessing

**Part V: Systems**
- Chapter 21: What the Operating System Does For You
- Chapter 22: The Compiler — How Your Code Becomes a Binary
- Chapter 23: The Optimizer — Doing Less Work
- Chapter 24: Self-Hosting — The Compiler Compiles Itself
- Chapter 25: Modular Design — Functions as Boundaries
- Chapter 26: Error Handling
- Chapter 27: Data Structures From First Principles
- Chapter 28: Concurrency — Fork and Shared State

**Part VI: Building Real Things**
- Chapter 29: A Calculator — Parsing Expressions
- Chapter 30: A Text Editor — Surfaces and Input
- Chapter 31: A Simple Database — Files and Indexing
- Chapter 32: Contributing — The AILang Ecosystem

**Appendices**
- Appendix A: AILang Complete Reference
- Appendix B: x86-64 Essentials
- Appendix C: The AILang Debug System — Complete Reference
- Appendix D: LinkagePool — Complete Reference
- Appendix E: From AILang to C
- Appendix F: From AILang to Rust

---

## How to Use This Material

### For Self-Study
Read Volume 1 completely before touching any code. Then proceed through Volume 2. Do the exercises. Trace programs by hand when asked.

### For a 16-Week University Course
See the companion document `semester-structure.md` for the full week-by-week plan:
- Weeks 1–3: Volume 1 (hardware only)
- Weeks 4–16: Volume 2 (programming + CS concepts)

### For AI Coding Research / Training
The extreme explicitness of AILang combined with the hardware-first approach makes this material unusually suitable for training and evaluating AI coding agents. Every decision is named. There is very little hidden state or magic.

---

## A Note on AILang Syntax in This Book

AILang uses **named operations** as the primary form (`Add(a, b)`, `Multiply(x, y)`, `GreaterThan(a, b)`, etc.). Some infix operators exist with scientific/engineering notation support, but **infix always requires explicit parentheses**. There is no hidden operator precedence.

This is not an inconvenience — it is a deliberate design decision that makes the connection to the machine short and obvious. The book will always show both the named form and the infix form where appropriate, but will never pretend that AILang is "basically C with different keywords."

---

*This book exists because the current dominant model of teaching programming does long-term damage to students. We can do better.*