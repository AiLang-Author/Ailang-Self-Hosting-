# Library.Arena(ailang)

## NAME

`Library.Arena` — slab-based memory allocator for AILang

## SYNOPSIS

```
LibraryImport.Arena
```

> Auto-imported by most standard libraries. Safe to import multiple
> times — the compiler deduplicates.

---

## DESCRIPTION

`Library.Arena` is AILang's unified memory allocator. It replaces direct
`mmap`/`munmap` syscalls with a slab allocator that routes allocations
to fixed-size pools, dramatically reducing syscall overhead for the
small, frequent allocations common in compiler and systems code.

The user-facing interface is two primitives exposed by the compiler:

```
ptr = Allocate(size)        // allocate `size` bytes, returns Address
Deallocate(ptr, size)       // return `size` bytes at `ptr` to the pool
```

These compile directly to `Arena_Alloc` and `Arena_Free`. You do not
call `Arena_Alloc` / `Arena_Free` directly in normal code.

### Architecture

The Arena uses nine fixed-size slab pools plus one general pool for
large allocations. Each slab maintains a free list and a bump pointer
into mmap'd chunks. Freed slots return to the free list and are reused
before new bump space is consumed.

| Slab | Max allocation size |
|------|-------------------|
| Slab24 | 24 bytes |
| Slab32 | 32 bytes |
| Slab64 | 64 bytes |
| Slab128 | 128 bytes |
| Slab256 | 256 bytes |
| Slab512 | 512 bytes |
| Slab1024 | 1 024 bytes |
| Slab2048 | 2 048 bytes |
| Slab4096 | 4 096 bytes |
| ArenaGeneral | > 4 096 bytes |

`Allocate(n)` routes to the smallest slab that fits `n`. Allocations
larger than 4096 bytes go to `ArenaGeneral` which uses a linear bump
allocator backed by direct `mmap`. Large allocations cannot be
individually freed — use `Arena_Reset` or `Arena_FreeAll` to reclaim.

---

## FUNCTIONS

The following are internal functions available when building libraries
or tools that need fine-grained control. Normal application code uses
`Allocate` / `Deallocate` only.

---

### `Arena_Init`

```
Function.Arena_Init
    Output: Integer    // 1 on success
```

Initializes all nine slab pools and the general arena by `mmap`ing one
chunk per pool. Called automatically at program startup — user code
does not need to call this.

---

### `Arena_Alloc`

```
Function.Arena_Alloc
    Input:  size: Integer
    Output: Address
```

Unified allocator. Routes to the appropriate slab based on `size`.
Returns a valid `Address` on success, `0` on failure. This is the
function `Allocate(n)` compiles to.

---

### `Arena_Free`

```
Function.Arena_Free
    Input: ptr:  Address
    Input: size: Integer
```

Returns `ptr` to the appropriate slab free list based on `size`.
Passing `size = 0` for large allocations is a no-op — use
`Arena_Reset` to reclaim general arena memory. This is the function
`Deallocate(ptr, size)` compiles to.

**Note:** Passing a `size` that does not match the original allocation
routes to the wrong slab and corrupts the free list. Always pass the
same size used in `Allocate`.

---

### `Arena_Reset`

```
Function.Arena_Reset
    (no arguments, no return value)
```

Resets all slabs to empty without releasing the underlying `mmap`
chunks back to the kernel. Subsequent allocations reuse the same
physical memory. Extra overflow chunks (grown beyond the initial chunk)
are released via `munmap`; only the first chunk per slab is kept.

**Use case:** Called between passes in the compiler, between files in
grep, or any time a large working set can be discarded atomically.
Much cheaper than `Arena_FreeAll` followed by `Arena_Init` because
the initial chunks stay mapped.

---

### `Arena_FreeAll`

```
Function.Arena_FreeAll
    (no arguments, no return value)
```

Releases all `mmap`'d memory for all slabs and the general arena back
to the kernel. After this call the Arena is unusable until `Arena_Init`
is called again. Normally only called at process exit.

---

### `Arena_MmapDirect`

```
Function.Arena_MmapDirect
    Input:  size: Integer
    Output: Address
```

Allocates `size` bytes directly from the kernel via `mmap`, rounded up
to the nearest page (4096 bytes). Bypasses all slab logic. Used
internally by the slab initializers and by callers that need page-
aligned memory (e.g. DFA state buffers in the regex engine).

---

### `Arena_ArrayDestroy`

```
Function.Arena_ArrayDestroy
    Input: arr: Address
```

Frees an Arena-backed array created by the internal array primitives.
The allocation size is stored in the 8 bytes immediately before `arr`;
`Arena_ArrayDestroy` reads it and routes to the correct slab free.
Do not call this on arbitrary pointers — only on arrays created by
`Arena_ArrayCreate`.

---

## MEMORY LAYOUT

Each slab chunk is a contiguous `mmap`'d region. The first 8 bytes of
each chunk store a pointer to the next chunk (linked list for overflow).
Allocation bumps `next` forward by the slab's slot size. When `next`
reaches `end` a new chunk is `mmap`'d and linked.

```
Chunk layout:
  [0-7]    → next chunk pointer (0 if last)
  [8 ...]  → slot 0, slot 1, slot 2, ...
              ↑ Slab.next starts here on init
```

Free list slots reuse the first 8 bytes of a freed slot to store the
next free pointer (intrusive linked list, zero extra overhead).

---

## PERFORMANCE NOTES

- **Small allocations (≤ 4096 bytes):** O(1) — free list pop or bump
  pointer increment. No syscall after initial chunk setup.
- **Large allocations (> 4096 bytes):** One `mmap` syscall per
  allocation that overflows `ArenaGeneral`'s current chunk.
- **`Arena_Reset` vs `Arena_FreeAll`:** Prefer `Arena_Reset` in hot
  paths. It costs one pass over slab metadata (constant) with no
  syscalls for the kept chunks.
- **The mmap boundary:** Each `mmap` call costs ~0.005 µs (C) /
  ~0.010 µs (AILang) in isolation. Repeated calls in tight loops
  are the primary memory performance bottleneck — the slab design
  exists specifically to minimize call frequency, not per-call cost.

---

## CONSTANTS

```
ArenaConst.CHUNK_SIZE    // size of each mmap'd chunk (default: 65536)
```

---

## EXAMPLE

```
// Normal use — just use Allocate / Deallocate
buf = Allocate(256)
SetByte(buf, 0, 72)   // 'H'
// ... use buf ...
Deallocate(buf, 256)

// Reset between compiler passes
Arena_Reset()

// Large temporary buffer (general arena, no individual free)
big = Allocate(1048576)   // 1 MiB — goes to ArenaGeneral
// ... use big ...
// Arena_Reset() or Arena_FreeAll() reclaims it
```

---

## SEE ALSO

`Allocate` (compiler primitive),
`Deallocate` (compiler primitive),
`Library.StringUtils`,
`Library.Regex_Thompson`

---

## VERSION

Current allocator. Replaced earlier direct-mmap design that caused
RSS growth exceeding 11 GB on large grep workloads due to per-call
allocation churn. Slab design reduces Arena calls from millions to
thousands on typical workloads.

## COPYRIGHT

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
