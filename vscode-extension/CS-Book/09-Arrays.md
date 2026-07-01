# Chapter 9: Arrays — Ordered Collections

**What you'll learn:** What an array actually is at the machine level (a contiguous block of memory divided into equal-sized slots). How index arithmetic works. Why most practical array and collection usage in AILang comes from the standard library (`Library.Array` / `Library.Arrays`) rather than language builtins. The deprecation of older XArray / TArray systems. The safety/performance tradeoffs.

---

## The Simplest Ordered Collection

An array is the most fundamental way to store a sequence of values in memory.

At the hardware level, an array is nothing more than:

- A starting address (the base pointer).
- A known element size (usually 1, 2, 4, or 8 bytes on modern machines).
- A length (either known at compile time or stored alongside the pointer).

If you have an array of 10 64-bit integers, the memory layout is simply 80 consecutive bytes. The address of element `i` is:

```
base + (i × 8)
```

This calculation is called **index arithmetic**. It is one of the most common operations a CPU performs.

---

## Why Arrays Are Fast

Array access is fast for a very simple reason: the CPU can compute the exact memory address it needs using a single multiplication and addition, then perform one memory read or write.

There is no searching. There is no following chains of pointers. There is only arithmetic.

This is why arrays are the foundation of almost every high-performance data structure.

---

## The Danger of Raw Arrays

The speed of arrays comes with a sharp edge.

If you have an array of 10 elements and you access index 10 (or 100, or -5), the CPU will happily compute the address and read or write whatever happens to be at that memory location.

This is called an **out-of-bounds access**. The results can range from:
- Reading garbage data
- Corrupting other variables
- Crashing the program
- Creating a security vulnerability that an attacker can exploit

In languages that do not perform bounds checking by default (such as C and C++), this class of bug has caused an enormous number of serious problems over the decades.

The modern `Library.Array` implementation performs bounds checking on `Get` (returns 0/NULL on out-of-bounds or null array). This is a deliberate safety choice implemented in the library on top of raw memory. Lower-level pointer arithmetic is still possible when you need maximum speed and are willing to take responsibility for safety.

---

## Dynamic Arrays and Collections (Library.Array)

There is **no** built-in dynamic array type in the core language (contrast with strings, which are rich compiler builtins with many SSE2-accelerated primitives).

The practical, recommended way to work with growable ordered collections is through the standard library:

```ailang
LibraryImport.Arrays   // pulls in Library.Array + Stack, Queue, List, hashes, etc.
```

`Library.Array` is the fast foundation (contiguous 8-byte elements, 32-byte header, automatic 2× growth).

Higher collections (Stack, Queue, IHash/SHash, List, sorting helpers) live in `Library.Arrays`.

Older systems (`XArrays`, `TArrays`, `THash`, `HashMap`) are deprecated and should not be used in new code.

Here is a real, verified teaching example using the current library (demo 141):

```ailang
LibraryImport.Array

arr = Array.Create(8)
Array.Push(arr, 42)
Array.Push(arr, 7)
Array.Push(arr, 19)
Array.Push(arr, 3)
Array.Push(arr, 99)

Array.Sort(arr)

i = 0
WhileLoop LessThan(i, Array.Size(arr)) {
    v = Array.Get(arr, i)
    PrintNumber(v)
    PrintMessage(" ")
    i = Add(i, 1)
}
PrintMessage("\n")

idx = Array.BinarySearch(arr, 19)
Array.Destroy(arr)
```

This pattern is used throughout modern AILang code. The library gives you safe, high-performance collections while the underlying memory model remains simple contiguous storage + index arithmetic.

---

## Hardware Connection

An array access ultimately becomes:

```asm
mov  rax, [base + index*8]
```

The CPU's addressing modes are specifically designed to make this pattern fast. Many instruction sets can perform the multiplication by a small constant (1, 2, 4, or 8) and the addition in a single instruction.

Dynamic array growth involves:
- Allocating a new block (`mmap` or similar)
- Copying memory (`memcpy` or equivalent)
- Freeing the old block

These are relatively expensive operations, which is why dynamic arrays try to minimize how often they reallocate.

---

## Key Concepts

- At the hardware level: contiguous memory + index arithmetic (base + index × element_size).
- In AILang practice: most array and collection work is done via `Library.Array` + `Library.Arrays` (the current recommended, non-deprecated libraries).
- Older XArray / TArray systems are deprecated.
- The library provides safe, high-performance dynamic arrays, stacks, queues, lists, and hashes on top of the simple memory model.
- Contrast with strings: strings have many compiler builtins with heavy SSE2 optimization; arrays/collections are excellent library code on top of raw memory.

---

*Next: We look at structured data — how to group related values together so that the relationships between them are explicit and the hardware can still access them efficiently.*