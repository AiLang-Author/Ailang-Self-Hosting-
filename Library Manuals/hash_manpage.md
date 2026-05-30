# Library.Hash(ailang)

## NAME

`Library.Hash` — high-performance open-addressing string hash table with hardware CRC32, linear probing, tombstones, and nested (hash-of-hashes) operations

## SYNOPSIS

```
LibraryImport.Hash
```

> Requires: `LibraryImport.Array` (for Keys/Values/Items/M* bulk returns)
>
> This is the current recommended general-purpose hash table. It supersedes `Library.HashMap` (deprecated) and the `IHash`/`SHash` tables inside `Library.Arrays`.

---

## DESCRIPTION

`Library.Hash` is a **cache-friendly, high-performance hash table** designed for systems and compiler workloads.

### Key architectural features

- **Open addressing + linear probing** — all entries live in one flat contiguous array of 32-byte slots. No pointer chasing, excellent locality.
- **Hardware CRC32** (SSE4.2 `CRC32` instruction via `InlineAsm`) for fast, high-quality string hashing.
- **Power-of-two capacity** with bitwise masking instead of modulo.
- **70% load factor** triggers automatic doubling + rehash.
- **Tombstones** (`-1`) for deletions — enables O(1) delete without breaking probe chains; reused on subsequent inserts.
- **Magic number** (`8244561397`) for `IsHash` runtime type safety.
- **Bulk operations** return `Array` objects (from `Library.Array`).
- **Full nested hash support** — `HSet`/`HGet`/etc. implement Redis-style hash-of-hashes on top of the same table (outer values are inner `Hash` handles).

| Property | Detail |
|----------|--------|
| Slot size | 32 bytes (`[hash:8, key_ptr:8, value:8, pad:8]`) |
| Hash | CRC32 (hardware), guaranteed non-zero |
| Collision resolution | Linear probing with tombstone reuse |
| Resize threshold | 70% (`size > cap*0.7`) |
| Capacity | Always power of two, min 8 |
| Key storage | Owned copy (malloc + byte copy on Set) |
| Value type | Integer (64-bit) — use for ints, bools, pointers, or nested Hash* |
| Bulk return type | `Array` of strings / ints / 2-element Arrays |

---

## FUNCTIONS

### Creation & Introspection

```
Function.Hash.Create
    Input:  capacity: Integer
    Output: Address
```
Allocates header + entry table. Capacity is rounded up to next power of two (≥8).

```
Function.Hash.New
    Output: Address
```
Convenience: `Hash.Create(16)`.

```
Function.Hash.IsHash
    Input:  addr: Address
    Output: Integer (1/0)
```
Magic-number + range check. Safe on null or garbage.

```
Function.Hash.Size
    Input:  table: Address
    Output: Integer
```

### Core Map Operations

```
Function.Hash.Set
    Input:  table: Address, key: Address (string), value: Integer
    Output: Integer (1 = new insert, 0 = updated existing)
```
Copies the key string. Auto-resizes at 70% load. Returns 1 for fresh key.

```
Function.Hash.Get
    Input:  table: Address, key: Address
    Output: Integer (value or 0 if missing)
```

```
Function.Hash.Contains
    Input:  table: Address, key: Address
    Output: Integer (1/0)
```

```
Function.Hash.Delete
    Input:  table: Address, key: Address
    Output: Integer (1 = deleted, 0 = not found)
```
Marks slot as tombstone. Frees the key copy. Does **not** shrink table.

```
Function.Hash.Clear
    Input:  table: Address
```
Removes all entries (frees keys) but keeps the table allocated at current capacity.

```
Function.Hash.Destroy
    Input:  table: Address
```
Frees all remaining keys + entry table + header. Safe on non-hash (no-op).

### Bulk / Iteration

```
Function.Hash.Keys
    Input:  table
    Output: Address (Array of string pointers — live keys, do not free)
```

```
Function.Hash.Values
    Input:  table
    Output: Address (Array of Integer values)
```

```
Function.Hash.Items
    Input:  table
    Output: Address (Array of 2-element Arrays: [[key, value], ...])
```
Each inner array is a fresh 2-slot Array. Caller owns the outer Array and the pair arrays.

### Numeric & Multi Helpers

```
Function.Hash.IncrBy
    Input:  table, key: Address, amount: Integer
    Output: Integer (new value)
```
Creates key with 0 if absent. Useful for counters.

```
Function.Hash.MSet
    Input:  table, keys: Array, values: Array
```
Parallel bulk set. Lengths must match.

```
Function.Hash.MGet
    Input:  table, keys: Array
    Output: Array (values, 0 for missing keys)
```

### Simple Aliases (thin wrappers)

`Hash.NewSimple`, `SetSimple`, `GetSimple`, `DeleteSimple`, `ContainsSimple`, `SizeSimple`, `KeysSimple`, `DestroySimple` — identical semantics, provided for code that prefers a `FooSimple` naming style.

### Nested Hash Operations (Hash-of-Hashes)

These treat values in the outer table as handles to inner `Hash` tables. Ideal for Redis `HSET` / document-style storage.

```
Function.Hash.CreateNested
    Output: Address
```
Just `Hash.Create(16)` — an outer table ready for `H*` ops.

```
Function.Hash.HSet
    Input:  outer, key: Address, field: Address, value: Integer
    Output: Integer (from inner Set)
```
Creates inner hash on first use for that key.

```
Function.Hash.HGet / HDel / HExists / HLen / HKeys / HVals / HGetAll
```

```
Function.Hash.HIncrBy
```

```
Function.Hash.HMSet / HMGet
```

```
Function.Hash.DestroyNested
    Input:  outer: Address
```
Recursively destroys every inner hash found in the outer table, then the outer itself.
Uses `IsHash` checks for safety.

---

## MEMORY & LIFETIME RULES

- Keys stored in the table are **owned copies** allocated via `Allocate`. `Delete` and `Destroy` free them.
- `Keys` / `Items` return pointers into the live table — the strings remain valid only while the table lives and the key is not deleted.
- `Values` / `Items` that are themselves `Hash` handles (from nested use) must be destroyed separately or via `DestroyNested`.
- `MGet` / `Items` etc. return fresh `Array` objects — caller must `Array.Destroy` them (and any nested arrays from `Items`).
- No automatic shrinking on delete. Use `Clear` + manual recreate or just live with the capacity.

---

## PERFORMANCE CHARACTERISTICS

- **Get/Set/Delete**: amortized O(1), excellent constant factors thanks to hardware hash + contiguous storage.
- **No allocation on lookup** (except the very first `Set` of a key).
- **Resize** copies only live entries (skips tombstones).
- **CRC32** is a single instruction per byte on modern x86_64 — vastly faster than software hash functions.
- **Cache behavior**: linear probing within a power-of-two block is extremely friendly to L1/L2.

---

## EXAMPLE

```ailang
LibraryImport.Hash
LibraryImport.Array

Hash.New → users

# Basic
Hash.Set(users, (String.literal "alice"), 1001)
Hash.Get(users, (String.literal "alice")) → id     # 1001
Hash.IncrBy(users, (String.literal "visits"), 1) → 1

# Bulk
Array.Create(2) → ks
Array.Push(ks, (String.literal "bob"))
Array.Push(ks, (String.literal "carol"))
Array.Create(2) → vs
Array.Push(vs, 2002)
Array.Push(vs, 3003)
Hash.MSet(users, ks, vs)
Array.Destroy(ks)
Array.Destroy(vs)

# Iteration
Hash.Keys(users) → key_arr
# ... use ...
Array.Destroy(key_arr)

# Nested (document style)
Hash.CreateNested → config
Hash.HSet(config, (String.literal "db"), (String.literal "host"), (String.literal "localhost"))
Hash.HGet(config, (String.literal "db"), (String.literal "host")) → h
Hash.DestroyNested(config)

Hash.Destroy(users)
```

---

## MIGRATION FROM DEPRECATED LIBRARIES

| Old | New | Notes |
|-----|-----|-------|
| `HashMap.Create` / `put` / `get` | `Hash.Create` / `Set` / `Get` | Different capacity rules; Hash uses string keys |
| `HashMap.HSet` etc. | `Hash.HSet` etc. | Drop-in for nested use; uses real Hash tables inside |
| `Arrays.SHash` | `Hash.*` (preferred) or keep SHash | SHash still works and is used by JSON; Hash is faster & stronger |
| `IHash` | `Hash` with integer-to-string keys if needed | Hash is string-only |

---

## SEE ALSO

`Library.Array` / `Library.Arrays` — dynamic arrays and the older chained SHash/IHash

`Library.JSON` — still uses SHash internally (as of this writing)

`Library.OOP` — uses both Array and Hash

`Librarys/deprecated/Library.HashMap.ailang` — the old chained implementation for reference

---

## VERSION

2026 — v2 open-addressing design with hardware CRC32. Replaced earlier `HashMap` (chained) and `THash` (mixer-only) libraries.

## COPYRIGHT

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
