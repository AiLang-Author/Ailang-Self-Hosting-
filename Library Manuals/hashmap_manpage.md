# Library.HashMap(ailang)

## NAME
`Library.HashMap` — external open-addressing hash map with Int:Any mapping, backed by THash

## SYNOPSIS
```
LibraryImport.HashMap
```
> Requires: `LibraryImport.THash`, `LibraryImport.XArrays`

## DESCRIPTION
HashMap provides a general-purpose key-value store mapping `Integer` keys to `Address` values (type-erased `Any`). It uses open addressing with linear probing and a power-of-two capacity, built on top of the THash mixing function for key hashing and XArrays for dynamic storage.

Keys and values are stored in parallel arrays (parallel-array open addressing). Deleted slots use a sentinel tombstone distinct from the nil sentinel.

| Concept | Detail |
|---|---|
| Key type | Integer |
| Value type | Address (Any) |
| Collision strategy | Linear probing, power-of-two capacity |
| Load factor | 0.70 max before grow |
| Grow factor | 2× (double capacity) |
| Hash function | THash.mix64 |
| Tombstone | Reserved -1 sentinel for deleted slots |

## FUNCTIONS

```
Function.HashMap.new
    Input:  —
    Output: Address  (HashMap instance)
```
Allocates a new empty HashMap with default initial capacity (16 slots). All fields are zeroed. The returned address is an opaque handle.

```
Function.HashMap.newCapacity
    Input:  initialCapacity: Integer
    Output: Address
```
Allocates a new HashMap with the given initial capacity rounded up to the next power of two. Minimum capacity is 4. Returns nil if `initialCapacity` is ≤ 0.

```
Function.HashMap.put
    Input:  map: Address, key: Integer, value: Address
    Output: Integer  (1 = inserted, 0 = replaced)
```
Inserts a key-value pair into the map. If the key already exists, the old value is overwritten and 0 is returned. If the key is new, 1 is returned. Triggers a grow+rehash if the load factor would exceed 0.70 after insertion.

```
Function.HashMap.get
    Input:  map: Address, key: Integer
    Output: Address  (value, or nil)
```
Looks up a key. Returns the associated value address or nil if the key is absent.

```
Function.HashMap.has
    Input:  map: Address, key: Integer
    Output: Integer  (1 = present, 0 = absent)
```
Boolean existence check — cheaper than `get` when the value is not needed.

```
Function.HashMap.remove
    Input:  map: Address, key: Integer
    Output: Integer  (1 = removed, 0 = not found)
```
Removes a key-value pair. Writes the tombstone sentinel into the slot. Returns 1 if the key was present and removed, 0 otherwise.

```
Function.HashMap.size
    Input:  map: Address
    Output: Integer
```
Returns the number of live (non-tombstone) entries in the map.

```
Function.HashMap.capacity
    Input:  map: Address
    Output: Integer
```
Returns the total number of slots (including empty and tombstone) in the underlying arrays.

```
Function.HashMap.keys
    Input:  map: Address
    Output: Address  (XArray of Integer)
```
Returns an XArray containing all live keys in arbitrary (probe) order. Caller must free the returned array.

```
Function.HashMap.values
    Input:  map: Address
    Output: Address  (XArray of Address)
```
Returns an XArray containing all live values in the same order as `keys`. Caller must free the returned array.

```
Function.HashMap.clear
    Input:  map: Address
    Output: —
```
Removes all entries. Does not shrink the underlying storage; capacity remains unchanged.

```
Function.HashMap.free
    Input:  map: Address
    Output: —
```
Releases all memory associated with the HashMap, including the keys array, values array, and the instance itself. Does NOT free the stored values (the caller is responsible for value lifetimes).

## MEMORY

| Allocation | Size | Freed by |
|---|---|---|
| HashMap instance | ~32 bytes | `free` |
| Keys array | capacity × 8 | `free` |
| Values array | capacity × 8 | `free` |
| Grow temporary arrays | 2×old_capacity × 8 each | internal (during grow) |

## EXAMPLE

```ailang
LibraryImport.HashMap

HashMap.new  → map
HashMap.put  map  42  (String.literal "hello")  → _
HashMap.put  map  99  (String.literal "world")  → _
HashMap.get  map  42  → val
String.print  val  # prints hello
HashMap.has  map  99  → exists  # 1
HashMap.remove  map  42  → _
HashMap.size  map  → n  # 1
HashMap.free  map
```

## SEE ALSO
`Library.THash` — hash function used internally
`Library.XArrays` — dynamic arrays backing the slot tables
`Library.SortedSet` — ordered unique-key container

## VERSION
2026-05-15 — initial specification (Phase 1 Tier 1)

## COPYRIGHT
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
