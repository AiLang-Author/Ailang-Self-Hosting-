# Chapter 14: Pointers — Addresses as Values

**What you'll learn:** A pointer is just a number that happens to be interpreted as a memory address. How pointer arithmetic works. The meaning of null. The difference between copying a pointer and copying the data it points to. Why pointers are both incredibly powerful and incredibly dangerous.

---

## The Simplest Definition

A pointer is a value whose meaning is "the address of something in memory."

That is the entire concept. There is no magic. A pointer is just an integer that the hardware and your program have agreed to treat as an address rather than as a number you might do arithmetic on for its own sake.

If the number `0x7FFF_1234_5678_9ABC` is stored in a variable and you treat that variable as a pointer, then the hardware will interpret it as "go look at whatever is stored at address `0x7FFF_1234_5678_9ABC`."

---

## Pointers Are Just Addresses

In AILang (and on real hardware), there is no fundamental difference between an integer and a pointer except in how you choose to use it.

You can take an address, store it in an integer variable, do math on it, and later use the result as an address again. The CPU does not know or care about the distinction. Only your program (and the compiler's type system) does.

This is why pointer bugs are so easy to create and so hard to find: the machine will happily follow any address you give it, no matter how nonsensical.

---

## Pointer Arithmetic

Because a pointer is just a number, you can do arithmetic on it.

If `p` points to the start of an array of 8-byte values, then:

```ailang
element_5 = Dereference(Add(p, Multiply(5, 8)))
```

is a way of saying "take the address in `p`, add 40 to it, and read the value at the resulting address."

This is exactly how `ArrayGet` and similar operations are implemented under the hood. The compiler turns clean array indexing into raw pointer arithmetic.

Understanding this is crucial. Array access is not a special high-level operation. It is pointer arithmetic with some syntactic sugar and (in AILang's case) bounds checking.

---

## Null — The Address That Means "Nothing"

By convention, the address 0 is special. It is called **null**.

Dereferencing null is almost always a crash or immediate fault. The OS arranges for address 0 to be invalid so mistakes fail loudly.

A verified teaching example (demo 023):

```ailang
p = 0   // null
IfCondition EqualTo(p, 0) ThenBlock: {
    PrintMessage("p is null\n")
}

p = Allocate(16)   // now a real pointer
IfCondition NotEqual(p, 0) ThenBlock: {
    PrintMessage("p is now a real pointer\n")
}
Deallocate(p, 16)
```

This shows the explicit "pointer is just an integer that we treat as an address" model in action. 0 has special meaning only by convention and OS protection.

In AILang the type `Address` is the language's pointer type. The constant `0` (or any variable holding 0) used where an `Address` is expected is the idiomatic representation of "no valid pointer" (null).

The null demo (023) above shows the explicit check pattern that AILang encourages.

---

## Copying the Pointer vs. Copying the Data

This is one of the most important distinctions in systems programming:

- If you have two pointer variables that contain the same address, they point to the **same** data.
- Changing the data through one pointer is visible through the other.
- Copying the pointer is cheap (just copying a number).
- Copying the data the pointer refers to requires walking the memory and making a new copy (as `StringCopy` and similar functions do).

Many subtle bugs come from confusing these two operations.

```ailang
p1 = some_pointer
p2 = p1           // cheap — now both point to the same memory

StoreValue(p2, 99)   // this also changes what you see through p1
```

If you actually wanted an independent copy of the data, you need to allocate new memory and copy the contents (which is what functions like `StringCopy` exist for).

---

## Why Pointers Are Dangerous

The power of pointers is that they let you build arbitrary data structures and share data efficiently between different parts of a program.

The danger is exactly the same power:

- You can create pointers to memory that no longer exists (dangling pointers).
- You can create multiple pointers to the same data and lose track of who is responsible for freeing it.
- You can perform arithmetic that produces an invalid address.
- You can cast between different interpretations of the same memory.

Languages with more restricted pointer models (or no raw pointers at all) give up some of this power in exchange for safety. AILang gives you the full power, but expects you to understand what you are doing.

---

## Hardware Connection

At the hardware level, a pointer is just a 64-bit value in a register or memory location.

`Dereference(p)` is a load instruction using the value in `p` as the address.

`StoreValue(p, v)` is a store instruction using the value in `p` as the address.

Pointer arithmetic is ordinary integer arithmetic on the address value.

The CPU has no idea whether a particular 64-bit number "is a pointer" or "is just a number." That distinction exists only in the programmer's (and compiler's) mind.

---

## Key Concepts

- A pointer is an address being used as a value.
- Pointer arithmetic is just integer arithmetic on addresses.
- Null is the conventional "no valid address" sentinel.
- Copying a pointer is not the same as copying the data it points to.
- The power and danger of pointers come from the same source: the ability to name and share arbitrary memory locations.

---

*Next: We look at thinking about correctness when memory, pointers, allocation lifetimes, and explicit contracts are all first-class and visible.*