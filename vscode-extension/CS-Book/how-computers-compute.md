# How Computers Compute
## A Primer
### Sean Collins, 2 Paws Machine and Engineering

*For everyone who uses a computer every day but has never been told what's actually happening inside it.*

---

## How to Read This Book

This book follows a single idea through an entire computer. We start with electricity and end with "Hello" appearing on your screen. Each chapter is short. Each one builds on the last. There are no prerequisites except curiosity.

By the end, you'll know what a CPU actually does, why your computer has RAM, what a bus is, and how all of these things work together to turn stored instructions into everything you see on screen.

Let's go meet the machine.

---

## Chapter 1: The Only Thing a Computer Can Do

A computer can tell the difference between *on* and *off*.

That's it. That's the foundation. Every photo you've seen, every song you've streamed, every message you've sent — all of it, at the very bottom, is built from a machine that can distinguish between two states.

We call these states **1** and **0**. On and off. High voltage and low voltage. The name doesn't matter. What matters is that there are exactly two, and the machine can tell them apart.

A single on-or-off value is called a **bit**. One bit isn't very useful — it can represent "yes" or "no" and nothing else. But put eight bits together and you get a **byte**, which can represent 256 different values (every combination of eight on/off switches). Put eight bytes together and you get a 64-bit **word**, which can represent roughly 18 quintillion different values.

That's enough to represent anything: numbers, letters, colors, sounds, instructions. The trick is agreeing on what the patterns mean. The number 65 and the letter "A" are the same bit pattern (01000001) — the computer doesn't know which one it is. The program decides.

**The takeaway:** A computer is a machine that stores and manipulates patterns of bits. Everything else is organization.

---

## Chapter 2: Counting Like a Computer

You count in **decimal** — base 10. You have ten digits (0 through 9), and when you run out, you carry: 9 becomes 10, 99 becomes 100. You've done this since childhood, so it feels like the only natural way to count. It isn't. It's just the system we agreed on, probably because we have ten fingers.

A computer counts in **binary** — base 2. It has two digits (0 and 1), and when it runs out, it carries. Same rules, fewer digits.

Here's what that looks like side by side:

| Decimal | Binary | What happened |
|---|---|---|
| 0 | 0 | |
| 1 | 1 | |
| 2 | 10 | Ran out of digits, carried |
| 3 | 11 | |
| 4 | 100 | Carried again |
| 5 | 101 | |
| 6 | 110 | |
| 7 | 111 | |
| 8 | 1000 | Carried again |

The number 8 takes four binary digits. The number 255 takes eight (11111111). That's one byte — eight bits, all on. One byte can represent any value from 0 (00000000) to 255 (11111111).

Binary is honest about what the hardware does. Each digit is one bit — one wire, one switch, one on-or-off. The number `1010` in binary means: first switch on, second off, third on, fourth off. Four switches, four bits, one number.

### Place Value Still Works

In decimal, each position is worth ten times the one before it. The number 347 means:

> 3 × 100 + 4 × 10 + 7 × 1

Binary works the same way, but each position is worth *two* times the one before:

> The binary number 1101 means: 1 × 8 + 1 × 4 + 0 × 2 + 1 × 1 = **13**

The positions, from right to left, are worth 1, 2, 4, 8, 16, 32, 64, 128... Each one is a power of 2. To convert any binary number to decimal, add up the positions where there's a 1.

### Hexadecimal — A Shorthand for Humans

Binary is easy for hardware but painful for people. The number 255 is `11111111` in binary — eight digits for a single byte. Reading and writing long strings of ones and zeros gets old fast.

**Hexadecimal** (hex, base 16) is the compromise. It has sixteen digits: 0–9 plus A–F, where A=10, B=11, C=12, D=13, E=14, F=15. Each hex digit represents exactly four bits:

| Hex | Binary | Decimal |
|---|---|---|
| 0 | 0000 | 0 |
| 1 | 0001 | 1 |
| 5 | 0101 | 5 |
| 9 | 1001 | 9 |
| A | 1010 | 10 |
| F | 1111 | 15 |

This means one byte (eight bits) is always exactly two hex digits. The byte `11111111` (decimal 255) is `FF` in hex. The byte `01000001` (decimal 65, the letter "A") is `41` in hex.

When you see numbers written with a `0x` prefix — like `0xFF` or `0x41` — that's hex. It's a convention that says "the following digits are base 16." Programmers use hex constantly because it maps cleanly to bytes: two digits per byte, always, no exceptions.

### Why Three Systems?

Each has its job:

**Binary** is how the hardware thinks. Every wire is a bit. You rarely write binary directly, but understanding it is understanding the machine.

**Decimal** is how you think. Prices, ages, quantities — the everyday numbers of human life. The computer converts to and from decimal at the boundaries (reading your input, displaying output) but doesn't use it internally.

**Hexadecimal** is the meeting point. It's compact enough for humans to read and regular enough to map perfectly to binary. Memory addresses, color codes (#FF0000 is red — full red, zero green, zero blue), machine instructions — anything where you're looking at raw bytes, hex is how you'll see it.

### A Quick Reference

| Decimal | Binary | Hex | What it is |
|---|---|---|---|
| 0 | 00000000 | 00 | Zero |
| 10 | 00001010 | 0A | Ten |
| 42 | 00101010 | 2A | A common test value |
| 65 | 01000001 | 41 | The letter "A" (ASCII) |
| 127 | 01111111 | 7F | Largest 7-bit value |
| 128 | 10000000 | 80 | The 8th bit, alone |
| 255 | 11111111 | FF | Largest byte value |

The pattern in the rightmost column hints at something important: the meaning of a number depends on context. 65 is just sixty-five. Or it's the letter "A." Or it's a shade of color. Same bits, different interpretation. The computer doesn't know — the program decides.

**The takeaway:** Binary, decimal, and hex are three ways to write the same numbers. Binary matches the hardware. Decimal matches your brain. Hex is the translator between them.

---

## Chapter 3: The Clock — Tick, Tick, Tick

Somewhere inside your computer, a tiny crystal vibrates. It vibrates very fast — billions of times per second. Every vibration produces a pulse, like a heartbeat. This is the **clock**.

The clock doesn't compute anything. It *coordinates*. It says "now" to every part of the machine at the same time. On this tick, read something. On the next tick, add two numbers. On the tick after that, store the result.

When you hear that a CPU runs at "3 GHz," that means the clock ticks 3 billion times per second. Each tick is a **cycle**. Some operations take one cycle. Some take several. But nothing happens between ticks. The clock is the drummer keeping time for the entire band.

Without a clock, the different parts of the computer wouldn't know when to act. Signals take time to travel through wires, and results take time to stabilize. The clock waits long enough for everything to settle, then says "okay, now take the next step."

**The takeaway:** The clock is the heartbeat. Nothing moves without it.

---

## Chapter 4: The CPU — One Instruction at a Time

The **CPU** (Central Processing Unit) is where computation happens. It's a chip about the size of a postage stamp, and it does one thing in a loop:

1. **Fetch** — Read the next instruction from memory.
2. **Decode** — Figure out what the instruction means.
3. **Execute** — Do it.
4. Go back to step 1.

That's the cycle. Fetch, decode, execute. Your CPU does this billions of times per second, one instruction at a time.

An instruction is simple. Absurdly simple. "Add these two numbers." "Copy this value over there." "Compare these two things." "If they're equal, jump to a different instruction." That's the level of complexity we're talking about. A CPU instruction is roughly as sophisticated as one step in a recipe: "crack an egg." Not "make an omelet" — just crack the egg.

A program is a long list of these tiny instructions stored in memory. The CPU keeps track of where it is in the list using a special value called the **instruction pointer**. After each instruction, the pointer moves forward to the next one — unless the instruction says "jump somewhere else," in which case the pointer moves to wherever it was told.

Every program you've ever used — your web browser, your phone's keyboard, a video game — is a list of these tiny instructions executing one after another, billions per second.

**The takeaway:** The CPU fetches instructions from memory and executes them. That's all it does. Speed and complexity come from doing it very, very fast.

---

## Chapter 5: Registers — The CPU's Hands

The CPU needs somewhere to hold the values it's currently working with. It can't add two numbers if it has nowhere to put them. These holding places are called **registers**.

Think of registers as the CPU's hands. A person can hold one thing in their left hand and one thing in their right hand, and they can do something with both — stack them, compare their weight, swap them. The CPU is similar, except it has about 16 hands (on modern x86 processors), and each can hold a 64-bit number.

Registers have names: RAX, RBX, RCX, RDX, and so on. When the CPU executes "add these two numbers," it means something like "add the number in RAX to the number in RBX, and put the result in RAX."

Registers are *fast* — the fastest storage in the entire computer. Reading a register takes effectively zero extra time; the value is right there inside the CPU. But there are only a few of them. You can't store your whole program's data in registers. That's what memory is for.

**The takeaway:** Registers are tiny, fast storage inside the CPU. The CPU does its work here, then puts results back in memory.

---

## Chapter 6: RAM — The Big Notebook

**RAM** (Random Access Memory) is where your computer stores everything it's currently working with: running programs, open documents, the web page you're reading right now. It's much larger than registers (billions of bytes versus a few dozen) but much slower.

Think of RAM as a massive notebook where every line is numbered. Line 0, line 1, line 2, all the way up to a few billion. Each line holds one byte. The number of the line is its **address**.

"Random access" means the CPU can read any address in the same amount of time. It doesn't have to start at the beginning and scan forward. Need the value at address 7,403,218? Go straight there.

When the CPU needs a value that's not in a register, it sends the address to RAM and waits for the answer. This wait — maybe 100 nanoseconds — is the most common bottleneck in modern computing. The CPU is fast; RAM is (relatively) slow. Much of computer engineering over the past 30 years has been about managing this speed gap.

RAM is **volatile**: when you turn off the power, everything in it disappears. This is why you have a hard drive or SSD for permanent storage — but that's a different story. While the computer is running, RAM is the working space.

**The takeaway:** RAM is the computer's working memory — big, addressable, but slower than registers. Programs and data live here while the computer is on.

---

## Chapter 7: The Bus — Roads Between Parts

The CPU needs to talk to RAM. RAM needs to talk to the screen. The hard drive needs to talk to RAM. How do all these parts communicate?

Through **buses**. A bus is a set of wires that carries data between components. If the CPU is a brain and RAM is a notebook, the bus is the hand that carries information between them.

There are three kinds of signals on a bus:

- **Address lines** — The CPU says *where* it wants to read or write.
- **Data lines** — The actual values being transferred.
- **Control lines** — Signals that say *what kind* of operation: read, write, ready, wait.

When the CPU wants to read address 1000 from RAM, it puts 1000 on the address lines, sets the control lines to "read," and waits. RAM sees the request, finds the value at address 1000, puts it on the data lines, and signals "ready." The CPU grabs the value.

Modern computers have multiple buses at different speeds. The fastest connects the CPU to RAM. Slower ones connect to disks, USB devices, and network hardware. They all work the same way — addresses, data, control — just at different speeds and widths.

**The takeaway:** Buses are the roads that connect components. Every piece of data that moves between the CPU, RAM, and everything else travels on a bus.

---

## Chapter 8: Cache — The Cheat Sheet

RAM is slow compared to the CPU. If the CPU had to wait for RAM on every instruction, it would spend most of its time idle.

The solution is **cache** — a small, fast memory built right into the CPU chip. When the CPU reads a value from RAM, it also stores a copy in cache. The next time it needs that value, it checks cache first. If it's there (a **cache hit**), the CPU gets it immediately. If not (a **cache miss**), it goes to RAM and waits.

Cache works because programs tend to use the same data repeatedly, and they tend to use data that's stored near other data they just used. Reading array elements in order? The first access pulls a whole chunk into cache, and the next several accesses are nearly instant.

Most CPUs have multiple levels of cache:
- **L1** — Smallest (usually 32–64 KB), fastest. Built right into each CPU core. A few cycles to access.
- **L2** — Larger (256 KB–1 MB), slightly slower. Usually per-core.
- **L3** — Largest (several MB), slowest cache but still much faster than RAM. Shared among all cores.

You never manage cache directly. The hardware decides what to keep and what to evict. But understanding that cache exists explains why some programs are fast and others aren't — often the difference is how well their memory access patterns play with the cache.

**The takeaway:** Cache is a small, fast copy of recently used data, sitting between the CPU and RAM. It hides RAM's slowness for most operations.

---

## Chapter 9: The Instruction — What It Looks Like

We've been saying the CPU executes "instructions," but what is an instruction actually?

It's a pattern of bits — a number — that the CPU knows how to interpret. On x86-64 (the architecture in most desktops and laptops), instructions are variable length, from 1 to 15 bytes. Each instruction encodes:

- **What to do** — the operation (add, subtract, move, compare, jump).
- **What to do it with** — the operands (which registers, what memory address, what immediate value).

For example, "add the value in RBX to RAX" is encoded as the bytes `48 01 D8` (three bytes). The `48` says "this is a 64-bit operation." The `01` says "ADD, register to register." The `D8` says "source is RBX, destination is RAX."

Those bytes, by the way, are in hex — the system from Chapter 2. `48` is binary `01001000`, `01` is `00000001`, `D8` is `11011000`. Twelve bytes of binary, or six characters of hex. This is why hex exists.

You don't need to memorize encodings. The point is: an instruction is just a few bytes. The CPU reads those bytes, recognizes the pattern, and does what they say. Your entire program — every feature, every button click, every animation — is a sequence of these tiny encoded operations.

**The takeaway:** An instruction is a small number that tells the CPU what to do. Programs are long sequences of these numbers stored in memory.

---

## Chapter 10: The Journey of an Instruction

Let's follow one instruction from start to finish. The program says `Add(x, y)` in source code, and the compiler turned it into the instruction "add RBX to RAX" — bytes `48 01 D8`, stored in memory.

**Tick 1 — Fetch.** The CPU looks at the instruction pointer, which holds an address in RAM — say, address 4096 (or `0x1000` in hex). It sends that address out on the bus. (Actually, it checks L1 cache first, and the instruction is probably there.) The bytes `48 01 D8` come back.

**Tick 2 — Decode.** The CPU's decoder examines the bytes. It recognizes `48` as a REX prefix (64-bit mode), `01` as the ADD opcode, and `D8` as the ModR/M byte specifying RAX and RBX. It sets up the internal circuitry to perform addition.

**Tick 3 — Execute.** The CPU reads the values currently in RAX and RBX, feeds them into the arithmetic logic unit (ALU), and the ALU produces the sum. The result is written back to RAX. The instruction pointer advances by 3 (the instruction was 3 bytes long), pointing to the next instruction.

Total time: roughly one billionth of a second.

Then it does it again. And again. Billions of times per second. Every second you use your computer.

**The takeaway:** Fetch, decode, execute — one instruction at a time, billions of times per second. That's the heartbeat of every computation.

---

## Chapter 11: How "Hello" Gets to Your Screen

Let's follow the whole chain — from a program to visible text.

A program wants to display "Hello" on your screen. Here's every step:

**1. The string is in memory.** The bytes `48 65 6C 6C 6F` (H-e-l-l-o in hex, or 72-101-108-108-111 in decimal) are stored at some address in RAM — say, address `0x2000`. The compiler put them there when it built the program.

**2. The program makes a system call.** The CPU loads a few values into registers: "I want to write" (system call number 1), "to the screen" (file descriptor 1), "the data at address `0x2000`" (pointer to the string), "5 bytes" (the length). Then it executes the `syscall` instruction.

**3. The operating system takes over.** The `syscall` instruction switches from your program to the operating system kernel. The kernel sees "write 5 bytes from address `0x2000` to file descriptor 1." File descriptor 1 is standard output — typically your terminal.

**4. The kernel copies the data.** It reads the 5 bytes from your program's memory and copies them into a buffer for the terminal.

**5. The terminal draws the characters.** The terminal application receives the bytes, looks up each one in a font (`48` hex is "H," which looks like two vertical lines connected by a horizontal bar), and draws the pixels.

**6. The display shows the pixels.** The pixel data is sent to your monitor over a cable (HDMI, DisplayPort), and the monitor's panel lights up the appropriate dots.

From `PrintMessage("Hello")` to photons hitting your eyes: stored bytes → CPU instructions → system call → kernel → terminal → pixel data → screen → light.

**The takeaway:** Displaying text involves the CPU, RAM, the operating system, and the display hardware, all coordinated through instructions and buses. It seems instant because every step happens in nanoseconds or microseconds.

---

## Chapter 12: Storage — Remembering When the Power's Off

RAM forgets everything the moment you flip the switch. So where do your files, your photos, your programs live permanently?

On **storage** — a hard drive (HDD) or solid-state drive (SSD).

A hard drive is a spinning metal platter coated in magnetic material. A tiny arm moves across the surface, reading and writing by flipping the magnetic orientation of microscopic regions. It's mechanical, which makes it slow compared to anything electronic — milliseconds instead of nanoseconds.

An SSD has no moving parts. It stores bits in tiny cells that trap electrical charge. No spinning, no arm movement — just electrical signals. This makes SSDs much faster than hard drives, though still far slower than RAM.

When you save a file, the operating system writes bytes from RAM to storage. When you open a file, bytes travel from storage to RAM so the CPU can work with them. When you start a program, the entire binary is loaded from storage into RAM before a single instruction executes.

This creates a hierarchy of storage, ordered by speed and size:

| Level | Speed | Size | Volatile? |
|---|---|---|---|
| Registers | ~0.3 ns | ~128 bytes | Yes |
| L1 Cache | ~1 ns | ~64 KB | Yes |
| L2 Cache | ~4 ns | ~256 KB | Yes |
| L3 Cache | ~10 ns | ~8 MB | Yes |
| RAM | ~100 ns | ~16 GB | Yes |
| SSD | ~100,000 ns | ~500 GB | No |
| HDD | ~10,000,000 ns | ~2 TB | No |

Each level is bigger and slower. Programs work best when they mostly access data that's in the faster levels.

**The takeaway:** Storage keeps your data safe when the power's off. RAM is the workspace. The CPU works from registers and cache. Everything moves between these levels as needed.

---

## Chapter 13: The Operating System — The Traffic Cop

Your computer runs many programs at once — a browser, a music player, a text editor. But you might have only 4 or 8 CPU cores. How does one CPU run dozens of programs?

It doesn't — not simultaneously. The **operating system** gives each program a small slice of time (a few milliseconds), then switches to the next one. This happens so fast that it looks simultaneous. This is called **multitasking**, and the switching is called a **context switch**.

The OS does a few essential jobs:

**Scheduling** — Deciding which program gets CPU time next. It balances fairness (everyone gets a turn) with priority (some things are more urgent).

**Memory protection** — Each program gets its own *virtual address space*. Program A sees addresses 0 through 4 billion. Program B also sees addresses 0 through 4 billion. But they're *different* physical RAM locations. If Program A crashes, it can't corrupt Program B's memory. The CPU's hardware (the **MMU** — Memory Management Unit) enforces this.

**Device access** — Programs don't talk to hardware directly. They ask the OS, and the OS talks to hardware on their behalf. This is what system calls are: your program saying "hey OS, please write these bytes to the screen for me."

**File systems** — The OS organizes bytes on storage into files and directories, handles reading and writing, and makes sure two programs don't corrupt a file by writing to it at the same time.

**The takeaway:** The operating system manages hardware so programs don't have to. It creates the illusion that each program has its own CPU, its own memory, and safe access to devices.

---

## Chapter 14: Putting It All Together

Let's zoom out and see the whole picture.

You double-click a program. Here's what happens:

**Loading:** The operating system reads the program file from storage (SSD/HDD) into RAM. The file contains machine instructions and data — those bit patterns we talked about in Chapter 1, encoded in the bytes from Chapter 2.

**Starting:** The OS creates a new process, sets up a virtual address space, and points the CPU's instruction pointer at the program's first instruction.

**Running:** The CPU starts the fetch-decode-execute cycle. It reads instructions from RAM (through cache), operates on values in registers, and stores results back to memory. Billions of times per second.

**Interacting:** When the program needs something — keyboard input, screen output, a file on disk — it makes a system call. The OS handles the request and returns control to the program.

**Multitasking:** Every few milliseconds, the OS pauses the program, saves its state (register values, instruction pointer), and lets another program run. When it's this program's turn again, the OS restores its state and it continues as if nothing happened.

**Ending:** The program calls "exit." The OS reclaims its memory and process entry. Done.

That's it. That's what your computer does, all day, every day. Billions of tiny instructions, shuffled between storage, RAM, cache, and registers, coordinated by a clock, managed by an operating system.

It's built from on/off switches.

---

## Glossary

**Address** — A number that identifies a byte's location in memory. Often written in hex (e.g., `0x7FFF1000`).

**ALU (Arithmetic Logic Unit)** — The part of the CPU that performs math and logic operations.

**Binary** — Base-2 numbering. Two digits: 0 and 1. How the hardware represents everything.

**Bit** — A single binary digit: 0 or 1.

**Bus** — A set of wires that carries data between computer components.

**Byte** — Eight bits. Can represent values from 0 to 255 (or `00` to `FF` in hex).

**Cache** — Small, fast memory inside the CPU that stores recently accessed data.

**Clock** — A crystal oscillator that generates regular timing pulses to coordinate the CPU.

**Context switch** — The OS saving one program's state and loading another's.

**CPU (Central Processing Unit)** — The chip that fetches and executes instructions.

**Cycle** — One tick of the clock.

**Decimal** — Base-10 numbering. The system humans use daily.

**File descriptor** — A small number the OS uses to represent an open file or device.

**Hexadecimal (Hex)** — Base-16 numbering. Digits 0–9 and A–F. Two hex digits = one byte.

**Instruction** — A small encoded command the CPU can execute (add, move, compare, jump).

**Instruction pointer** — A register that holds the address of the next instruction to execute.

**Kernel** — The core of the operating system that runs with full hardware access.

**MMU (Memory Management Unit)** — Hardware that translates virtual addresses to physical addresses.

**Opcode** — The part of an instruction that specifies what operation to perform.

**Operating system** — Software that manages hardware resources and provides services to programs.

**RAM (Random Access Memory)** — Volatile working memory. Fast, addressable, loses contents without power.

**Register** — A small, fast storage location inside the CPU.

**SSD (Solid-State Drive)** — Non-volatile storage using electronic cells instead of moving parts.

**System call** — A program's request to the operating system to perform a privileged operation.

**Virtual address space** — The illusion that each program has its own private memory.

**Volatile** — Loses its contents when power is removed.

**Word** — A natural unit of data for a CPU. 64 bits (8 bytes) on modern x86 processors.

---

*Now you know what's in the box. If you want to learn to tell it what to do, "Computer Science Disambiguated" picks up right where this book leaves off.*
