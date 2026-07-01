# Chapter 12: What Memory Actually Is

**What you'll learn:** Addresses, bytes, and words as the fundamental units. The stack, the heap (via Arena), and the pool table as the three main regions with different rules and lifetimes. How `Allocate`/`Deallocate` and the two primitive operations (`StoreValue`/`Dereference`) actually work. The explicit nature of memory in AILang.

---

## Memory Is Just Numbered Boxes

At the lowest level, a computer's memory is a giant array of bytes. Each byte has a number that identifies its location. That number is called its **address**.

If you have 16 gigabytes of RAM, there are roughly 16 billion of these numbered boxes. The CPU can ask for the contents of any box by its address, or it can put a new value into any box.

This is the entire abstraction. Everything else — variables, arrays, objects, stacks, heaps — is built on top of "give me the byte at address X" and "put this value into the byte at address Y."

---

## Addresses, Bytes, and Words

- A **byte** is 8 bits. It can hold a value from 0 to 255 (or -128 to 127 if interpreted as a signed number).
- A **word** on a modern 64-bit machine is 8 bytes (64 bits). This is the natural size the CPU prefers to work with for addresses and many operations.
- An **address** is a number that tells the hardware which byte (or word) you want. On 64-bit systems, addresses are themselves 64-bit values.

When you write `x = 42` in AILang, the compiler decides which address `x` will live at (usually some offset from the base of the current stack frame). From that point on, every read or write of `x` becomes a load or store to that address.

---

## The Stack and the Heap

The machine manages memory in two very different regions with completely different rules.

### The Stack

- Grows and shrinks automatically as functions are called and return.
- Extremely fast to allocate from (just move the stack pointer).
- Every piece of data on the stack has a known, short lifetime: it dies when its function returns.
- Perfect for local variables, parameters, and return addresses.

When a function is called, the CPU (with help from the compiler) carves out a new region on the stack for that function's local variables. When the function returns, that region is instantly reclaimed by moving the stack pointer back. No bookkeeping, no searching for free space — just arithmetic on a single pointer.

This is why stack allocation feels "free" compared to heap allocation.

### The Heap

- A large region of memory that you manage explicitly.
- You ask for a chunk (`Allocate`), you get an address, you use it, and later you give it back (`Deallocate`).
- The lifetime of heap memory is completely independent of function calls. A heap allocation can live for milliseconds or for the entire run of the program.
- Much more flexible, but also much more dangerous and slower.

The heap exists because the stack's "die when my function returns" rule is too restrictive for many real programs. If you want a data structure that outlives the function that created it, you need the heap (managed in AILang primarily via `Library.Arena` slab allocator for speed and determinism).

### Actual Memory Layout in AILang (x86-64)

From the Memory Management Reference Manual, a running AILang program typically sees this layout (high addresses at top):

- **Stack** — RSP / RBP (local variables, frames, grows downward)
- **Heap / Arena slabs** — most `Allocate` calls
- **Pool Table** — base in reserved register **R15** (FixedPool variables; never modify R15 in user code)
- **Data Section** — string literals, constants
- **Code Section**

R15 is special: the compiler uses it as the base for all `FixedPool` access. Writing to it will corrupt pool state across the entire program.

`Library.Arena` is a slab allocator — it routes small/frequent allocations to fixed-size pools rather than making kernel syscalls every time. This is why allocation is fast and predictable in AILang.

Here is a verified teaching example (demo 138) showing explicit allocation and the importance of tracking sizes:

```ailang
LibraryImport.Arena

ptr = Allocate(128)
PrintMessage("Allocated 128 bytes.\n")

// Write some data using byte operations
SetByte(ptr, 0, 72)   // 'H'
SetByte(ptr, 1, 105)  // 'i'

PrintMessage("Wrote data. First two bytes: ")
b0 = GetByte(ptr, 0)
b1 = GetByte(ptr, 1)
PrintNumber(b0)
PrintMessage(" ")
PrintNumber(b1)
PrintMessage("\n")

Deallocate(ptr, 128)   // Size must match Allocate exactly!
PrintMessage("Deallocated successfully.\n")
```

This demonstrates the raw, explicit nature of heap memory in AILang. The compiler does not hide allocation or lifetime from you.

---

## The Two Fundamental Operations

Everything you ever do with memory ultimately comes down to two operations the CPU understands:

- `StoreValue(address, value)` — Write a value into memory at a given address.
- `Dereference(address)` — Read the value that lives at a given address.

These are the only two things the CPU can do with memory. Every variable access, every array read, every pointer dereference, every object field access — all of them are compiled down to some combination of these two primitives.

AILang makes `StoreValue` and `Dereference` (and their byte/word variants like `SetByte`/`GetByte`) explicit so there is no hidden magic about how data moves in and out of memory.

---

## Why This Matters

Most serious systems bugs are memory bugs in disguise:

- Use-after-return (stack address lives longer than its frame)
- Leaks (forgot to `Deallocate` or `FreeLinkage`)
- Use-after-free
- Buffer overflows / slab corruption (wrong size to `Deallocate`)
- Corrupting FixedPools by touching R15

AILang makes all of this explicit (Arena, Allocate/Deallocate with sizes, reserved R15, Direction contracts on LinkagePools) so the mental model stays accurate instead of becoming a source of superstition.

---

## Hardware Connection

At the lowest level the CPU only does loads and stores:

- `StoreValue(addr, val)` → `MOV [addr], val` (or equivalent)
- `Dereference(addr)` → `MOV val, [addr]`

The compiler maintains the fiction of variables, lifetimes, and safety on top of this. AILang simply refuses to hide the underlying reality.

Key hardware details (from the Memory Management manual):
- R15 is reserved as the base for the entire FixedPool table — user code must never touch it.
- Most allocations go through `Library.Arena` slabs (very fast, minimal kernel involvement).
- `Allocate` / `Deallocate` ultimately talk to the Arena or kernel, but the programmer is responsible for matching sizes exactly.

---

## Key Concepts

- Memory = flat address space of bytes.
- Three main regions with different rules: Stack (automatic, short lifetime), Arena/Heap (explicit, flexible lifetime), Pool Table (R15-based, compile-time structured).
- `StoreValue` / `Dereference` (and byte variants) are the atoms.
- Arena + explicit `Allocate`/`Deallocate` with size tracking removes most of the magic (and most of the classic memory bugs) while remaining deterministic.

---

*Next: We look at allocation in detail — `Allocate`, `Deallocate`, Arena slabs, and why size must always match.*