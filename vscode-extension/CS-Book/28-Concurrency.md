# Chapter 28: Concurrency — Fork and Shared State

**What you'll learn:** What happens when multiple threads or processes run at the same time. The difference between processes and threads. Why shared mutable state is dangerous. Safer alternatives such as message passing and immutable data.

---

## The Illusion of a Single Processor

Modern computers have multiple CPU cores. Even on a single-core machine, the operating system constantly switches between different programs (and different parts of the same program).

From the point of view of any individual thread, it usually appears to have the CPU mostly to itself. The operating system hides the fact that the CPU is being shared.

This illusion breaks down as soon as two threads need to interact with the same data.

---

## Processes vs Threads

- A **process** is an instance of a program with its own virtual address space, file descriptors, and other resources. Different processes are strongly isolated from each other by the operating system and the MMU.

- A **thread** is a separate flow of control *inside* a process. Threads within the same process share the same address space and can therefore see each other's memory directly.

Because threads share memory, they can communicate very efficiently — but they can also destroy each other's data if they are not careful.

---

## The Danger of Shared Mutable State

When two threads can both read and write the same memory locations, a whole new class of bugs appears:

- **Race conditions** — The final result depends on the unpredictable timing of when the threads run.
- **Data corruption** — One thread is halfway through updating a data structure when another thread reads it.
- **Deadlocks** — Two threads each wait for the other to release a resource.
- **Heisenbugs** — The bug disappears when you try to debug it because adding logging or breakpoints changes the timing.

These problems are not theoretical. They are the source of some of the most difficult bugs in real systems.

---

## Locks and the Problems They Create

The traditional tool for protecting shared data is the **mutex** (mutual exclusion lock).

A thread that wants to access a protected data structure must first "acquire" the lock. Only one thread can hold the lock at a time. Other threads that want the lock must wait.

Locks solve some problems but introduce new ones:
- Forgetting to acquire a lock (or releasing it at the wrong time) still leads to corruption.
- Acquiring locks in the wrong order leads to deadlocks.
- Contention on a heavily used lock can destroy performance.
- Locks do not compose well — combining two thread-safe components does not automatically give you a thread-safe system.

---

## Message Passing as an Alternative

Instead of sharing memory and using locks to protect it, many systems use **message passing**:

- Threads (or processes) do not directly access each other's data.
- They communicate by sending and receiving messages through channels, queues, or sockets.
- Each thread owns its own data and is responsible for its own correctness.

This model is used heavily in operating systems (Unix pipes, message queues), distributed systems, and languages designed for concurrency (Erlang, Go channels, etc.).

The mental model is much cleaner: "I send you a message. You do something with it and maybe send me a reply." There is no shared mutable state to fight over.

---

## Immutability

Another powerful technique is to make data **immutable** (unchangeable after creation).

If data cannot be modified, then multiple threads can safely read it at the same time with no locks required.

When you need to "change" an immutable data structure, you typically create a new version that shares most of its structure with the old version (persistent data structures). This is the approach used in many functional languages and in some high-performance systems.

---

## Hardware Connection

At the hardware level, the problems of concurrency come from the fact that the CPU (and the memory system) can reorder operations and can have multiple cores looking at memory through different caches.

Modern CPUs provide:
- Memory barrier / fence instructions that force ordering.
- Atomic operations (compare-and-swap, atomic add, etc.) that can update memory safely from multiple cores.
- Cache coherence protocols that try to keep multiple caches consistent.

Programming with these primitives directly is extremely difficult and error-prone. This is why higher-level abstractions (locks, message passing, transactional memory, etc.) exist.

AILang's explicit style at least makes it harder to accidentally write code that has hidden data races, because so much of the memory behavior is visible in the source.

---

## Key Concepts

- Processes are isolated; threads within a process share memory.
- Shared mutable state + concurrent access = race conditions, corruption, and deadlocks.
- Locks are a common but imperfect tool.
- Message passing and immutability are safer alternatives in many situations.
- The hardware provides low-level atomic operations and memory ordering primitives; everything else is built on top of them.

---

*Next: We begin the "Building Real Things" section with a substantial project — writing a calculator that parses and evaluates mathematical expressions.*