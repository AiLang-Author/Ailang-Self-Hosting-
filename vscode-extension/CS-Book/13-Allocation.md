# Chapter 13: Allocation — Asking for Memory

**What you'll learn:** How a program actually obtains memory from the operating system. What `Allocate` and `Deallocate` really do under the hood. The difference between asking the OS for memory and managing it yourself. Why memory leaks and use-after-free bugs happen.

---

## You Don't Own All the Memory

When your program starts, it does not have unlimited access to all the RAM in the machine. The operating system is in charge of physical memory. Your program runs in a virtual address space that the OS and the CPU's Memory Management Unit (MMU) conspire to make look like a private, contiguous chunk of memory.

When you need memory that will outlive the current stack frame (or that is too large for the stack), you have to ask the operating system for it.

---

## Allocate — "Please Give Me Some Memory"

In AILang, the fundamental way to request memory is:

```ailang
buffer = Allocate(1024)
```

This tells the runtime (and ultimately the operating system): "I need 1024 bytes of memory that I can use however I want, and I want an address I can use to refer to the start of that region."

What actually happens:

1. The runtime checks whether it already has a suitable free block in its own data structures (slabs, free lists, etc.).
2. If not, it makes a system call (usually `mmap` on Linux) to ask the kernel for more memory.
3. The kernel updates its page tables, finds some physical pages, maps them into your virtual address space, and returns an address.
4. The runtime gives you a pointer to a portion of that region.

From your program's perspective, you now have 1024 bytes you can read and write using `Dereference` and `StoreValue`.

---

## Deallocate — "I'm Done With This, You Can Have It Back"

When you are finished with memory you allocated, you are supposed to give it back:

```ailang
Deallocate(buffer, 1024)
```

This tells the runtime: "I am no longer using the 1024 bytes starting at `buffer`. You may reuse this memory for future allocations."

What actually happens:

1. The runtime marks that region as free in its internal data structures.
2. It may eventually make a system call to tell the kernel it no longer needs those pages (though many allocators are lazy about this for performance reasons).
3. The memory becomes available for reuse by your program or (eventually) by the system.

---

## What Goes Wrong

Two of the most common and damaging classes of bugs in systems programming come directly from mismanaging allocation:

### Memory Leaks

You allocate memory and never deallocate it. The runtime (or the OS) thinks the memory is still in use, so it cannot be reused. Over time, your program (or the whole system) runs out of memory even though it isn't actually using most of it.

### Use-After-Free

You deallocate memory and then continue to use pointers that point into it. The memory may have been reused for something else. You are now reading or writing data that belongs to a completely different part of the program (or even a different program, in some cases). This is a major source of security vulnerabilities.

A real, verified example that demonstrates the size rule (demo 138):

```ailang
LibraryImport.Arena

ptr = Allocate(128)
// ... use ptr ...
Deallocate(ptr, 128)   // Must pass the exact same size used in Allocate
```

Passing the wrong size to `Deallocate` can corrupt the Arena's internal slab structures.

Both leaks and use-after-free are symptoms of the same root cause: mismatched mental models about ownership and lifetime between the programmer and the memory manager.

---

## Why Allocation Is "Expensive" (and How AILang Mitigates It)

Compared to declaring a local variable on the stack, calling `Allocate` is relatively slow because it can involve:
- Searching internal data structures
- System calls (`mmap`/`brk`)
- Page table updates
- Potential zeroing

AILang dramatically reduces this cost for the common case by using `Library.Arena` — a slab allocator. Most small allocations come from pre-sized internal pools rather than hitting the kernel every time. The result is fast, predictable allocation while still keeping the model fully explicit (you still call `Allocate`/`Deallocate` and must track sizes).

This is why AILang programs can feel both low-level and high-performance at the same time.

---

## Hardware and OS Connection

At the bottom:

- `Allocate` (when the Arena needs more memory) becomes `mmap` or `brk` syscalls.
- The kernel manages physical pages and page tables.
- The MMU translates every virtual address your program uses into a physical one.
- `Deallocate` can eventually lead to `munmap`.

`Library.Arena` sits on top of this and hides most of the kernel traffic for small allocations, while still giving you full explicit control when you need it.

R15 continues to be reserved for the FixedPool table regardless of how much heap memory you allocate.

---

## Key Concepts

- `Allocate(size)` + `Deallocate(ptr, size)` — explicit, size must match exactly.
- `Library.Arena` makes most allocations fast via slabs (far fewer kernel calls).
- Leaks = never deallocating; use-after-free = using after deallocating.
- The programmer owns the lifetime model; the compiler and Arena help but do not hide responsibility.
- Ties directly to previous chapters: FixedPools and LinkagePools ultimately use Arena under the hood for their dynamic parts.

---

*Next: We look at pointers — addresses that have been turned into first-class values.*