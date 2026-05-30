# Library.Array and Library.Arrays (ailang)

## NAME

`Library.Array` / `Library.Arrays` — high-performance dynamic arrays and collections (Stack, Queue, List, SHash/IHash, utilities)

## SYNOPSIS

```
LibraryImport.Array
LibraryImport.Arrays
```

> `Library.Arrays` automatically imports `Library.Array`. Most code imports `LibraryImport.Arrays` for the full collection suite.
>
> These are the current, recommended array and basic hash collection libraries. They replace the deprecated `TArrays`, `XArrays`, `THash`, and `HashMap`.

---

## DESCRIPTION

`Library.Array` provides a **flat, high-performance dynamic array** with a 32-byte header and contiguous 8-byte element storage. It features:

- Magic number type tagging for robust `IsArray` checks
- Automatic growth (2× factor) with `Push` / `Insert`
- Rich API: slice, sort (insertion), binary search, reverse, extend, swap, shift, etc.
- Direct pointer arithmetic (no per-element call overhead)
- Safe bounds-checked access (returns 0/NULL on OOB for gets)

`Library.Arrays` builds higher-level collections on top of `Array` (and Arena for some structures):

- **Stack** — thin LIFO wrapper over Array
- **Queue** — ring-buffer FIFO with separate Arena allocation
- **IHash** — integer-keyed chained hash table
- **SHash** — string-keyed chained hash table (with `Addr` variants for pointer values)
- **List** — singly-linked list with append/prepend/pop front/back
- **Util** — sorting, searching, min/max, reverse helpers

These libraries are the foundation for many modern AILang components (JSON, OOP, Trees, etc.).

| Property | Detail |
|----------|--------|
| Element width | 8 bytes (native Integer/Address) |
| Header size | 32 bytes (`[magic, capacity, size, data_ptr]`) |
| Growth | 2× on overflow (Array) |
| Magic | `7133856912` for Array (runtime type safety) |
| Max practical size | ~65536 elements (configurable in FixedPool) |
| Hash load factor (IHash/SHash) | Unbounded (chained) |
| Queue/Stack defaults | 1024 elements |

---

## CORE: Library.Array

### Lifecycle & Introspection

```
Function.Array.Create
    Input:  initial_capacity: Integer
    Output: Address
```
Allocates header + data block. Capacity is rounded up; minimum default 16. Returns header pointer.

```
Function.Array.Destroy
    Input:  arr: Address
```
Frees header and data block. Safe on null.

```
Function.Array.IsArray
    Input:  value: Address
    Output: Integer (1/0)
```
Bulletproof runtime type check using magic number + address range guard.

```
Function.Array.Size
    Input:  arr: Address
    Output: Integer
```

```
Function.Array.Capacity
    Input:  arr: Address
    Output: Integer
```

```
Function.Array.IsEmpty
    Input:  arr: Address
    Output: Integer (1/0)
```

### Element Access

```
Function.Array.Get
    Input:  arr: Address, index: Integer
    Output: Integer (value or 0 on OOB/null)
```

```
Function.Array.Set
    Input:  arr: Address, index: Integer, value: Integer
```
No-op on OOB or null array.

```
Function.Array.First
    Input:  arr: Address
    Output: Integer (or Arrays.NULL)
```

```
Function.Array.Last
    Input:  arr: Address
    Output: Integer (or Arrays.NULL)
```

### Mutation

```
Function.Array.Push
    Input:  arr: Address, value: Integer
```
Appends; grows if needed.

```
Function.Array.Pop
    Input:  arr: Address
    Output: Integer (last value or 0)
```
Does not shrink capacity.

```
Function.Array.Clear
    Input:  arr: Address
```
Sets size=0; capacity unchanged.

```
Function.Array.Insert
    Input:  arr: Address, index: Integer, value: Integer
    Output: Integer (1 on success)
```
Shifts tail right. Clamps index into [0, size].

```
Function.Array.Delete
    Input:  arr: Address, index: Integer
    Output: Integer (deleted value or 0)
```
Shifts tail left.

```
Function.Array.Shift
    Input:  arr: Address
    Output: Integer (first value)
```
Removes and returns element 0, shifts rest left.

```
Function.Array.Resize
    Input:  arr: Address, new_capacity: Integer
    Output: Integer (1)
```
Grows or shrinks backing store (never below current size).

### Search & Order

```
Function.Array.IndexOf
    Input:  arr: Address, value: Integer
    Output: Integer (index or Arrays.NULL)
```

```
Function.Array.Contains
    Input:  arr: Address, value: Integer
    Output: Integer (1/0)
```

```
Function.Array.BinarySearch
    Input:  arr: Address, value: Integer
    Output: Integer (index or Arrays.NULL)
```
Requires sorted array (ascending).

```
Function.Array.InsertSorted
    Input:  arr: Address, value: Integer
    Output: Integer (insertion index)
```
Inserts while maintaining ascending order (linear scan + Insert).

```
Function.Array.Sort
    Input:  arr: Address
```
In-place insertion sort (stable, simple).

```
Function.Array.Reverse
    Input:  arr: Address
```
In-place.

```
Function.Array.Swap
    Input:  arr: Address, idx1: Integer, idx2: Integer
    Output: Integer (1 on success)
```

### Bulk & Views

```
Function.Array.Copy
    Input:  arr: Address
    Output: Address (shallow clone)
```

```
Function.Array.Extend
    Input:  arr: Address, other: Address
```
Appends all elements from `other`.

```
Function.Array.Slice
    Input:  arr: Address, start: Integer, end_idx: Integer
    Output: Address (new array)
```
Supports Python-style negative indices. Returns new independent array.

---

## HIGHER-LEVEL COLLECTIONS: Library.Arrays

### Stack (LIFO, thin Array wrapper)

```
Function.Stack.Create
    Input:  capacity: Integer
    Output: Address
```

```
Function.Stack.Push / Pop / Peek / IsEmpty
```
`Peek` returns `XERROR` on empty. All others delegate to Array.

### Queue (FIFO ring buffer)

```
Function.Queue.Create
    Input:  capacity: Integer
    Output: Address
```
Uses separate Arena allocation for control block + data ring.

```
Function.Queue.Enqueue
    Input:  queue: Address, value: Integer
    Output: Integer (1 success, 0 full)
```

```
Function.Queue.Dequeue
    Output: Integer (value or XERROR)
```

```
Function.Queue.Destroy
```

### IHash — Integer-keyed Chained Hash

```
Function.IHash.Create
    Input:  bucket_count: Integer
    Output: Address
```

```
Function.IHash.Insert
    Input:  hash_table, key: Integer, value: Integer
    Output: 1
```

```
Function.IHash.Lookup
    Input:  hash_table, key: Integer
    Output: value or XERROR
```

```
Function.IHash.Destroy
```

### SHash — String-keyed Chained Hash (and Addr variants)

```
Function.SHash.Create / Insert / Lookup / Exists / Delete / Keys / Destroy
    Keys: string → integer
```

Addr variants (`InsertAddr`, `LookupAddr`, `ExistsAddr`, `DeleteAddr`) store/return `Address` values (for pointers, nested structures, etc.). Delete returns the old value.

`SHash.Keys` returns an Array of (copied) string pointers — caller must free the strings if taking ownership.

### Linked List

```
Function.List.Create
    Output: Address
```

```
Function.List.Append / Prepend
    Input:  list, value: Integer
```

```
Function.List.PopFront / PopBack
    Output: value (0 on empty)
```

```
Function.List.Size / Destroy / DestroyDeep
```
`DestroyDeep` also frees string values stored in nodes.

### Utilities

```
Function.Util.BinarySearch / QuickSort / Partition
Function.Util.FindMax / FindMin / Reverse
```

---

## MEMORY & OWNERSHIP

| Structure | Allocation | Responsibility |
|-----------|------------|----------------|
| Array header + data | `Allocate` (slab) | `Array.Destroy` |
| Queue control block | Arena_Alloc64 | `Queue.Destroy` |
| IHash/SHash nodes & buckets | Arena_*24 / Arena_Array | `IHash.Destroy` / `SHash.Destroy` (frees copied keys) |
| List nodes | Arena_Alloc24 | `List.Destroy` (or DestroyDeep) |
| Strings returned by SHash.Keys | `Helpers.StringCopy` → `Allocate` | Caller must `Deallocate` each |

**Important:** `SHash.Keys` returns an Array whose elements are pointers to **copies** of the keys. The hash table still owns the originals. Freeing the returned strings while the table lives is safe for the copies only.

---

## EXAMPLE

```ailang
LibraryImport.Arrays

# --- Dynamic Array ---
Array.Create(8) → arr
Array.Push(arr, 10)
Array.Push(arr, 20)
Array.Insert(arr, 1, 15)          # [10,15,20]
Array.Size(arr) → n               # 3
Array.BinarySearch(arr, 15) → 1
Array.Slice(arr, 1, 3) → sub      # [15,20]
Array.Destroy(sub)
Array.Destroy(arr)

# --- Stack ---
Stack.Create(64) → stk
Stack.Push(stk, 42)
Stack.Pop(stk) → v

# --- SHash (string → int) ---
SHash.Create(32) → users
SHash.Insert(users, (String.literal "alice"), 1001)
SHash.Lookup(users, (String.literal "alice")) → id   # 1001
SHash.Exists(users, (String.literal "bob")) → 0
SHash.Destroy(users)

# --- List ---
List.Create → lst
List.Append(lst, 1)
List.Prepend(lst, 0)
List.PopFront(lst) → 0
List.Destroy(lst)
```

---

## SEE ALSO

`Library.Hash` — the newer, faster open-addressing hash table (preferred for most new key-value work)

`Library.Arena` — underlying allocator

`Library.JSON` — uses SHash + Array internally

`Library.OOP` — uses Array + Hash

`Library.Trees` — uses Arrays

`Librarys/deprecated/` — old TArrays, THash, HashMap, XArrays kept for archaeology

---

## VERSION

2026 — Current production implementation. Supersedes all prior array and basic hash collection libraries.

## COPYRIGHT

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
