# Library.Trees(ailang)

## NAME
`Library.Trees` — B-tree with page-size multiple nodes, sorted keys, and range scans

## SYNOPSIS
```
LibraryImport.Trees
```
> Requires: `LibraryImport.TArrays`

## DESCRIPTION
Trees implements a classic **B-tree** — a balanced multi-way search tree where each node is a multiple of the page size (4096 bytes) for optimal disk and cache locality. The tree stores sorted key-value pairs and supports point queries, predecessor/successor, and range scans.

The B-tree is general-purpose: suitable as a database index, an in-memory sorted dictionary, or a backing store for ordered collections.

| Property | Detail |
|---|---|
| Node size | 4096 bytes (one page), configurable in multiples |
| Branching factor | ~200–500 keys per node (depends on key/value size) |
| Min fill | ceil(b/2) keys per node (except root) |
| Key type | Integer (64-bit signed) |
| Value type | Address (Any) |
| Duplicate keys | Not allowed (overwrite on insert) |
| Order | Ascending |
| Height | O(log n), typically 2–4 for millions of entries |

## FUNCTIONS

### Lifecycle

```
Function.Trees.new
    Input:  —
    Output: Address  (B-tree handle)
```
Creates an empty B-tree with default page size (4096 bytes).

```
Function.Trees.newPageSize
    Input:  pageSize: Integer
    Output: Address
```
Creates a B-tree with a custom node page size. `pageSize` must be ≥ 512 and a power of two. Larger pages increase branching factor at the cost of more work per split/merge.

```
Function.Trees.free
    Input:  tree: Address
    Output: —
```
Recursively frees all nodes and the tree handle. Does NOT free stored values.

### Write Operations

```
Function.Trees.insert
    Input:  tree: Address, key: Integer, value: Address
    Output: Integer  (1 = inserted, 0 = replaced)
```
Inserts a key-value pair. If the key already exists, the value is overwritten and 0 is returned. Triggers node splits as needed to maintain the B-tree invariants.

```
Function.Trees.remove
    Input:  tree: Address, key: Integer
    Output: Integer  (1 = removed, 0 = not found)
```
Removes the entry with the given key. Triggers node merges or redistributions to maintain the minimum fill invariant. Returns 1 if the key was found and removed.

### Read Operations

```
Function.Trees.find
    Input:  tree: Address, key: Integer
    Output: Address  (value, or nil)
```
Exact-match lookup. Returns the associated value or nil.

```
Function.Trees.has
    Input:  tree: Address, key: Integer
    Output: Integer  (1 = present, 0 = absent)
```
Boolean existence check — cheaper than `find` when the value is not needed.

```
Function.Trees.min
    Input:  tree: Address
    Output: Address  (value at minimum key, or nil if empty)
```

```
Function.Trees.max
    Input:  tree: Address
    Output: Address  (value at maximum key, or nil if empty)
```

```
Function.Trees.minKey
    Input:  tree: Address
    Output: Integer  (minimum key, undefined if empty)
```

```
Function.Trees.maxKey
    Input:  tree: Address
    Output: Integer  (maximum key, undefined if empty)
```

### Predecessor / Successor

```
Function.Trees.successor
    Input:  tree: Address, key: Integer
    Output: Integer  (next larger key, or key itself if none)
```
Finds the smallest key strictly greater than `key`. Returns `key` unchanged if there is no successor.

```
Function.Trees.predecessor
    Input:  tree: Address, key: Integer
    Output: Integer  (next smaller key, or key itself if none)
```
Finds the largest key strictly less than `key`.

```
Function.Trees.successorValue
    Input:  tree: Address, key: Integer
    Output: Address  (value at successor key, or nil)
```

```
Function.Trees.predecessorValue
    Input:  tree: Address, key: Integer
    Output: Address  (value at predecessor key, or nil)
```

### Range Scans

```
Function.Trees.range
    Input:  tree: Address, low: Integer, high: Integer, inclusive: Integer
    Output: Address  (TArray of values in key order)
```
Returns all values whose keys are in `[low, high]` (if `inclusive`=1) or `(low, high)` (if `inclusive`=0). The result is a TArray of Address values. Caller must free the returned array.

```
Function.Trees.rangeKeys
    Input:  tree: Address, low: Integer, high: Integer, inclusive: Integer
    Output: Address  (TArray of Integer keys in order)
```
Like `range` but returns the keys.

```
Function.Trees.rangePairs
    Input:  tree: Address, low: Integer, high: Integer, inclusive: Integer
    Output: Address  (TArray of key-value structs)
```
Returns interleaved key-value pairs: [k1, v1, k2, v2, …].

### Size

```
Function.Trees.size
    Input:  tree: Address
    Output: Integer  (number of entries)
```

```
Function.Trees.height
    Input:  tree: Address
    Output: Integer  (tree height: leaf=1, root-only=1)
```

```
Function.Trees.nodeCount
    Input:  tree: Address
    Output: Integer  (total nodes in the tree)
```

### Iteration

```
Function.Trees.forEach
    Input:  tree: Address, callback: Address, userdata: Address
    Output: —
```
In-order traversal calling `callback(key, value, userdata)` for each entry. The tree must not be modified during traversal.

## MEMORY

| Allocation | Size | Freed by |
|---|---|---|
| Tree handle | ~40 bytes | `free` |
| Internal nodes | pageSize each | `free` (recursive) |
| Leaf nodes | pageSize each | `free` (recursive) |
| Range result TArray | variable | Caller |

## EXAMPLE

```ailang
LibraryImport.Trees
LibraryImport.String

Trees.new  → tree

# Insert
Trees.insert  tree  100  (String.literal "apple")   → _
Trees.insert  tree  200  (String.literal "banana")  → _
Trees.insert  tree  150  (String.literal "cherry")  → _

# Lookup
Trees.find  tree  150  → v
String.print  v  # cherry

# Range scan
Trees.rangeKeys  tree  100  200  1  → keys
# keys = [100, 150, 200]

# Successor
Trees.successor  tree  100  → next  # 150

Trees.size   tree  → n  # 3
Trees.free   tree
```

## SEE ALSO
`Library.SortedSet` — ordered unique-key set (often backed by Trees)
`Library.TArrays` — used internally for node storage and range results
`Library.HashMap` — unordered key-value storage

## VERSION
2026-05-15 — initial specification (Phase 1 Tier 1)

## COPYRIGHT
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
