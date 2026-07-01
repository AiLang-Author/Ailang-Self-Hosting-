# Appendix D: LinkagePool — Complete Reference

This appendix summarizes the `LinkagePool` system, which is AILang’s primary mechanism for structured, record-like data with explicit memory layout.

## Declaration

```ailang
LinkagePool.Person {
    "id":   Initialize=0, CanChange=True
    "name": Initialize=0, CanChange=True   // usually an Address (string)
    "age":  Initialize=0, CanChange=True
}
```

- Every field must have an `Initialize` value.
- `CanChange=True/False` controls mutability after allocation.
- The compiler knows the exact size and field offsets at compile time.

## Allocation and Access

```ailang
p = Pool.Person.Allocate()

p.id   = 42
p.name = StringCopy("Alice")
p.age  = 31
```

Or using the explicit form:

```ailang
LinkageStore(p, Person, id, 42)
```

Reading is symmetric:

```ailang
id = LinkageField(p, Person, id)
```

## Memory Model

- A `LinkagePool` instance is a contiguous block of memory.
- Fields are laid out in declaration order with natural alignment (the compiler inserts padding as needed).
- The base address of the pool plus the known offset gives the address of any field.
- No hidden vtables, no hidden reference counts, no hidden pointers — the layout is exactly what you declared.

## Common Patterns

- Embedding one LinkagePool inside another (nested records).
- Using a LinkagePool as a node in a linked structure (the classic "next" pointer pattern).
- Treating LinkagePools as lightweight objects for systems code where you want full control over memory.

## Relationship to Other Mechanisms

- `FixedPool` — for global / module-level named state (compile-time singleton).
- `LinkagePool` — for dynamically allocated structured records.
- Raw `Allocate` + manual `StoreValue`/`Dereference` — when you need completely custom layouts.

For the definitive and detailed reference, see:

**LinkagePool_Pointers Reference Manual.md** (in the Programming_Manual directory)

That manual covers alignment rules, padding behavior, embedding rules, interaction with the Arena allocator, and many practical examples. The summary here is only a high-level orientation for readers of this book.