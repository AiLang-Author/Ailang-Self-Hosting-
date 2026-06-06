# Chapter 10: Structured Data — LinkagePool

**What you'll learn:** How to group related values into records so that the relationships between fields are explicit. How `LinkagePool` declarations turn into fixed memory layouts. The connection between named fields and pointer arithmetic.

---

## The Problem with "Just Use More Arrays"

So far we have worked with individual values and flat sequences (arrays and strings).

Real programs almost always need to keep related pieces of data together:
- A point has an x and a y.
- A person has a name, an age, and an ID.
- A network packet has a source address, a destination address, a length, and a payload.

You *could* keep these as parallel arrays (`x_coords[i]`, `y_coords[i]`, `names[i]`, etc.). Many early programs did exactly that.

This approach quickly becomes painful and error-prone:
- It is easy to get the arrays out of sync (different lengths, mismatched indices).
- It is hard to pass "one person" to a function — you have to pass five or six arrays and an index.
- The relationship between the fields exists only in the programmer's head.

We need a way to say: "These fields belong together as a single conceptual unit."

---

## LinkagePool — Records with Explicit Layout

`LinkagePool` lets you declare heterogeneous structured records with named fields. The compiler turns the declaration into a fixed memory layout with known offsets.

Here is a minimal, verified example (adapted from the LinkagePool Reference Manual):

```ailang
LibraryImport.Arena

LinkagePool.Point {
    "x": Initialize=0
    "y": Initialize=0
}

SubRoutine.Main {
    Arena_Init()
    
    p = AllocateLinkage(LinkagePool.Point)
    p@x = 10
    p@y = 20
    
    PrintNumber(p@x)
    PrintMessage(" ")
    PrintNumber(p@y)
    PrintMessage("\n")
    
    FreeLinkage(p, LinkagePool.Point)
}
RunTask(Main)
```

This produces `10 20`.

Key points:
- Declaration uses `LinkagePool.Name { "field": Initialize=... }`
- Allocation: `AllocateLinkage(LinkagePool.Name)`
- Access: `ptr@field` (the `@` operator; dot notation also works in many contexts)
- Cleanup: `FreeLinkage(ptr, LinkagePool.Name)` when using Arena

The compiler knows every field's type and offset at compile time. No hidden magic.

---

## From Names to Offsets

When you write `p@x` (or `p.x`), the compiler performs the offset calculation:

- It knows `x` is the first field.
- Integers are 8 bytes → offset 0.
- `y` is at offset 8.

The generated code is equivalent to:

```asm
mov  rax, [p]          ; base address
mov  rax, [rax + 0]    ; load x
```

The names give you safety and readability while the machine still does raw pointer + offset arithmetic.

This is the same pointer arithmetic you could write by hand with raw addresses. `LinkagePool` simply gives you names for the offsets and lets the compiler do the arithmetic.

---

## Nested Records and References

You have two ways to nest data:

- `Type=` (inline/embedded) — single allocation, value semantics.
- `PointerTo=` — separate allocation, reference semantics (great for linked structures, trees, graphs).

Example of inline nesting:

```ailang
LinkagePool.Address {
    "street": Initialize=""
    "city": Initialize=""
}

LinkagePool.Person {
    "name": Initialize=""
    "home": Type=LinkagePool.Address
}
```

Then: `person@home@city = "Chicago"`

For linked structures you use `PointerTo=` on an Address field.

These choices directly affect allocation, copying behavior, and nullability — the compiler helps you reason about all of them.

### Direction Contracts (Powerful Connection to Functions)

You can attach `Direction=Input|Output|InOut` to fields. When you pass the pool as an `Input:` parameter to a Function, the compiler enforces the rules:

```ailang
LinkagePool.CalculationRequest {
    "operand_a": Initialize=0, Direction=Input
    "operand_b": Initialize=0, Direction=Input
    "result": Initialize=0, Direction=Output
}

Function.Calculate {
    Input: req: LinkagePool.CalculationRequest
    Output: Integer
    Body: {
        a = req@operand_a          // OK (Input)
        b = req@operand_b          // OK
        req@result = Add(a, b)     // OK (Output)
        // req@operand_a = 99      // Compile ERROR - cannot write Input
        ReturnValue(1)
    }
}
```

This is one of the most valuable features for writing safe, auditable code (see Chapter 4). Direction is only enforced on parameters — local allocations have full access.

---

## Why This Matters

Being able to group related data and give the group a name is one of the most powerful abstractions in programming.

It lets you think at a higher level ("pass me a Person") while the machine continues to work at the low level ("here is a pointer to 64 bytes laid out as...").

`LinkagePool` gives you this abstraction without hiding the underlying reality. You can always ask the compiler "what is the offset of field `age` inside `Person`?" and get a concrete answer.

---

## Hardware Connection

`LinkagePool` adds zero runtime cost in the common case.

The compiler computes every field's offset at compile time. A field access becomes exactly the same instruction you would write by hand:

```asm
mov  rax, [base + offset]
```

`Direction=` enforcement, `PointerTo=` type tracking, and null checks are all compile-time or very cheap runtime guards. The data layout is identical to a C struct, but with far better safety and readability.

---

## Key Concepts

- `LinkagePool` declarations create named, typed, fixed-layout records.
- Allocation with `AllocateLinkage`, access with `@` (or `.`), cleanup with `FreeLinkage`.
- `Direction=Input|Output|InOut` on fields gives compile-time contracts when pools are passed to Functions (see Ch04).
- `PointerTo=` vs `Type=` controls reference vs value nesting.
- Everything ultimately reduces to base address + known offsets — the compiler just gives you names, types, and checks.

---

*Next: We look at how AILang enforces data movement contracts using `Direction=Input|Output|InOut` on LinkagePool fields (when the pool is passed as a Function parameter) and FixedPool for SubRoutine state.*