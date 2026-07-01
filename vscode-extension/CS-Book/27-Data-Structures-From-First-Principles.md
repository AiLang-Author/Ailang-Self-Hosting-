# Chapter 27: Data Structures From First Principles

**What you'll learn:** How to build the fundamental data structures (linked lists, stacks, queues, trees, hash maps) using only the memory primitives (`Allocate`, `StoreValue`, `Dereference`) and the explicit control flow we have already covered. No magic libraries — just pointers and discipline.

---

## Why Build Them Yourself?

In most programming courses, students are introduced to data structures by using library types: `List`, `Map`, `Set`, etc.

This is convenient for getting work done, but it has a serious pedagogical cost:

> Students learn the *interface* of data structures without ever understanding their *implementation*.

They finish the course knowing that "a hash map is fast for lookup" without any idea *why*. They have no mental model of what is actually happening in memory when they do `map[key] = value`.

This book takes the opposite approach.

We will build each major data structure from the ground up, using only the tools we already have:
- `Allocate` and `Deallocate`
- `StoreValue` and `Dereference`
- `LinkagePool` for structured records
- Explicit control flow

The goal is not to produce production-quality reusable libraries (though the resulting code can be surprisingly usable). The goal is understanding.

---

## Linked List

The simplest dynamic data structure is a singly-linked list.

A node contains:
- A value
- A pointer to the next node (or null if this is the last node)

In AILang (using modern LinkagePool syntax from Chapter 10):

```ailang
LinkagePool.ListNode {
    "value": Initialize=0
    "next":  Initialize=0   // Address of next node, or 0 for null
}
```

To build a list, you allocate nodes with `AllocateLinkage` and link them with `@` access:

```ailang
current = head
WhileLoop NotEqual(current, 0) {
    v = current@value
    PrintNumber(v)
    current = current@next
}
```

Inserting at the head is trivial: allocate a new node, set its `next` to the old head, and update the head pointer.

This structure makes the following things obvious:
- There is no "magic array" behind the list.
- Each element lives in its own separately allocated piece of memory.
- Following the `next` pointers is literally pointer chasing.
- The cost of finding the nth element is O(n) because you have to follow n pointers.

---

## Stack (LIFO)

A stack can be built on top of a linked list (push and pop at the head) or on top of a dynamic array.

The array-based version is often more practical:

- Keep an array and a "top" index.
- Push: store the value at `array[top]`, then increment `top`.
- Pop: decrement `top`, return the value that was at `array[top]`.

The implementation makes the LIFO (last-in, first-out) behavior completely obvious: the most recently pushed value is the one at the highest index, and popping just moves the "top" pointer back.

---

## Queue (FIFO)

A queue can also be built on a dynamic array, but now you need both a head and a tail index.

- Enqueue at the tail.
- Dequeue from the head.
- When the tail reaches the end of the array, you can either resize or wrap around (circular buffer / ring buffer).

The ring buffer version is particularly elegant once you see it:
- The array is treated as a circle.
- Two indices chase each other around the circle.
- The data between head and tail is the current contents of the queue.

This is exactly the kind of structure used in operating systems for task queues, network buffers, and audio processing.

---

## Binary Tree

A binary tree node contains:
- A value (or key + value)
- Left child pointer
- Right child pointer

```ailang
LinkagePool.TreeNode {
    "key":   Initialize=0
    "value": Initialize=0
    "left":  Initialize=0
    "right": Initialize=0
}
```

The recursive structure is now completely visible in the pointer fields.

Searching, insertion, and the various traversals (in-order, pre-order, post-order) all become simple recursive functions that follow the left and right pointers according to clear rules.

The student sees directly why:
- Search in a balanced binary tree is O(log n) in the average case.
- The shape of the tree determines performance.
- In-order traversal visits nodes in sorted order.

---

## Hash Map (Hash Table)

A hash map is one of the most useful data structures, and also one of the most revealing when implemented from scratch.

Basic structure:
- An array of "buckets" (each bucket is the head of a linked list of entries).
- A hash function that turns a key into an array index.
- Each entry in a bucket contains the key, the value, and a pointer to the next entry in that bucket.

Insertion:
1. Hash the key to get a bucket index.
2. Walk the linked list in that bucket looking for a matching key (to handle updates).
3. If not found, allocate a new entry and insert it at the head of the list.

Lookup is the same walk.

This implementation makes several things concrete:
- The "constant time" lookup is actually "constant time plus the length of the chain in that bucket."
- A bad hash function turns the structure into a slow linked list.
- Load factor (number of entries vs number of buckets) directly affects performance.
- Deletion requires care (especially with open addressing, which is an alternative to chaining).

Implementing a hash map from scratch is one of the best ways to truly understand why they are fast *when they are well implemented*, and why they can be surprisingly slow when they are not.

---

## The Recurring Pattern

After building several of these structures, a pattern becomes obvious:

> Almost every interesting data structure is some combination of:
> - Contiguous arrays (for speed and cache locality)
> - Linked structures using pointers (for flexibility and dynamic growth)
> - Hashing (for fast unordered lookup)

There is no magic library that creates fundamentally new capabilities. The libraries are just well-tested, convenient implementations of these same basic building blocks.

Once a student has built a few of them by hand, they read library documentation with a completely different level of understanding.

---

## Hardware Connection

Every pointer field is a memory address.

Every array access is index arithmetic.

Every allocation is a request to the operating system's virtual memory system.

The performance characteristics of these data structures are not arbitrary — they are direct consequences of how the memory hierarchy (registers, L1/L2/L3 cache, RAM) actually works.

A student who has built these structures can look at a performance problem and ask intelligent questions:
- "Are we getting cache misses because the linked list nodes are scattered all over memory?"
- "Would a flat array be better here even if it means copying on insertion?"
- "Is our hash function causing terrible bucket distribution?"

These are the kinds of questions that separate programmers who treat data structures as black boxes from those who can make informed engineering decisions.

---

## Key Concepts

- Data structures are built from arrays + pointers + allocation.
- Linked structures give flexibility at the cost of pointer chasing and poor cache behavior.
- Arrays give speed and locality at the cost of resizing and copying.
- Hashing gives fast unordered access when the hash function and load factor are good.
- Understanding the implementation is what allows you to choose the right structure and diagnose performance problems.

---

*Next: We look at concurrency — what happens when multiple threads or processes are running and need to share or communicate data.*