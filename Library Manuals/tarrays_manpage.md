# Library.TArrays(ailang)

## NAME
`Library.TArrays` — tiered dynamic vector with memcpy-friendly layout and 64-bit length

## SYNOPSIS
```
LibraryImport.TArrays
```
> Requires: none (self-contained, uses raw memory allocation)

## DESCRIPTION
TArrays provides a **tiered vector** — a growable sequence of homogeneous elements stored in contiguous chunks (tiers) rather than a single contiguous allocation. This design avoids the cost of reallocating and copying the entire array on every growth event. Each tier is a fixed-size page (default 4096 bytes), and the vector chains tiers together in a flat pointer table.

The tiered layout is memcpy-friendly: each tier is independently contiguous, suitable for scatter-gather I/O and zero-copy slices.

| Property | Detail |
|---|---|
| Element type | Opaque bytes (caller specifies element size) |
| Tier size | 4096 bytes (configurable) |
| Max elements | 2⁶⁴ − 1 |
| Growth | Appends new tiers as needed; no reallocation of existing tiers |
| Access | O(1) random access via tier+offset calculation |
| Cache | Excellent for sequential access; 1 pointer-chase per tier boundary |

## FUNCTIONS

### Lifecycle

```
Function.TArrays.new
    Input:  elementSize: Integer
    Output: Address  (TArray handle)
```
Creates an empty tiered array with the given element size (must be > 0). Returns nil if `elementSize` ≤ 0.

```
Function.TArrays.newTierSize
    Input:  elementSize: Integer, tierBytes: Integer
    Output: Address
```
Creates an empty tiered array with a custom tier size. `tierBytes` is rounded down to a multiple of `elementSize`.

```
Function.TArrays.free
    Input:  arr: Address
    Output: —
```
Frees all tiers and the array handle. Does NOT free element contents if they contain pointers — the caller must iterate and free individually if needed.

### Element Access

```
Function.TArrays.get
    Input:  arr: Address, index: Integer
    Output: Address  (pointer to element, or nil)
```
Returns a direct pointer to the element at `index` (0-based). The pointer is valid until the array is freed. Returns nil if `index` is out of bounds.

```
Function.TArrays.set
    Input:  arr: Address, index: Integer, src: Address
    Output: Integer  (1 = success, 0 = out of bounds)
```
Copies `elementSize` bytes from `src` into the slot at `index`. Returns 0 if index out of bounds.

### Size and Capacity

```
Function.TArrays.len
    Input:  arr: Address
    Output: Integer  (number of elements)
```

```
Function.TArrays.capacity
    Input:  arr: Address
    Output: Integer  (total slots across all allocated tiers)
```

```
Function.TArrays.elementSize
    Input:  arr: Address
    Output: Integer
```

```
Function.TArrays.tierCount
    Input:  arr: Address
    Output: Integer  (number of allocated tiers)
```

### Push / Pop

```
Function.TArrays.push
    Input:  arr: Address, src: Address
    Output: Integer  (new length)
```
Appends one element. Copies `elementSize` bytes from `src`. If all tiers are full, allocates a new tier. Returns the new length.

```
Function.TArrays.pushZero
    Input:  arr: Address
    Output: Integer  (new length)
```
Appends one zero-initialised element. Useful for building arrays of primitives.

```
Function.TArrays.pop
    Input:  arr: Address
    Output: Integer  (new length, or -1 if empty)
```
Removes the last element (logical removal; the bytes remain in the tier). Returns the new length or -1 if the array was empty.

```
Function.TArrays.popInto
    Input:  arr: Address, dst: Address
    Output: Integer  (1 = popped, 0 = empty)
```
Pops the last element and copies its bytes into `dst`. Returns 1 on success, 0 if empty.

### Bulk Operations

```
Function.TArrays.pushMany
    Input:  arr: Address, src: Address, count: Integer
    Output: Integer  (new length)
```
Appends `count` elements from `src`. More efficient than calling `push` in a loop.

```
Function.TArrays.clear
    Input:  arr: Address
    Output: —
```
Resets logical length to 0. Does NOT free tiers; capacity remains.

```
Function.TArrays.compact
    Input:  arr: Address
    Output: Integer  (bytes freed)
```
Frees any trailing empty tiers and returns the number of bytes reclaimed.

### Iteration

```
Function.TArrays.forEach
    Input:  arr: Address, callback: Address, userdata: Address
    Output: —
```
Calls `callback(elementPtr, index, userdata)` for each element in order. The callback receives a direct pointer valid only during the callback.

## MEMORY

| Allocation | Size | Freed by |
|---|---|---|
| TArray handle | ~48 bytes | `free` |
| Tier page | tierBytes bytes each | `free` |
| Tier pointer table | tierCount × 8 | `free` |

## EXAMPLE

```ailang
LibraryImport.TArrays

# Array of 64-bit integers
TArrays.new  8  → arr  # elementSize = 8

# Push values
Integer.literal  42  → val
TArrays.push  arr  val  → len  # 1
TArrays.push  arr  (Integer.literal 99)  → len  # 2

# Access
TArrays.get  arr  0  → ptr
Integer.load  ptr  → v  # 42

TArrays.len   arr  → n  # 2
TArrays.free  arr
```

## SEE ALSO
`Library.XArrays` — generic-typed macro wrapper around TArrays
`Library.HashMap` — uses parallel arrays for key-value storage

## VERSION
2026-05-15 — initial specification (Phase 1 Tier 1)

## COPYRIGHT
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
