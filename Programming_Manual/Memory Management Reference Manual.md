# Memory Management Reference Manual

## Overview

AILang provides direct memory control with no garbage collector and no
hidden allocation. Every allocation is explicit. Every deallocation is
explicit. Memory behavior is deterministic and auditable.

The allocator is slab-based (`Library.Arena`) — requests route to
fixed-size pools rather than going directly to the kernel. This
eliminates most syscall overhead for the small, frequent allocations
common in compiler and systems work. See `Library.Arena` for internals.

---

## Register Map

AILang uses a fixed register allocation strategy. Understanding it
matters when writing syscall wrappers or inline assembly.

| Register | Role |
|----------|------|
| RAX | Return values, temporary computations |
| RBX | General purpose, preserved across calls |
| RCX | Loop counters, temporaries |
| RDX | Secondary computations |
| RSI | Source pointers, string ops |
| RDI | Destination pointers, string ops |
| RBP | Stack frame base pointer |
| RSP | Stack pointer |
| R8–R9 | 7th and 8th function parameters |
| R10–R11 | Temporary values |
| R12–R13 | Preserved temporaries |
| R14 | Reserved |
| **R15** | **Pool table base — NEVER modify** |

**R15 is reserved.** The compiler uses R15 as the base pointer for all
`FixedPool` variable access. Writing to R15 in any user code, syscall
wrapper, or inline assembly will corrupt all pool variable access.

---

## Memory Layout

```
High addresses
┌─────────────────────────────────┐
│           Stack                 │  ← RSP / RBP
│   (local variables, frames)     │
├─────────────────────────────────┤
│           Heap                  │
│   (Allocate / Arena slabs)      │
├─────────────────────────────────┤
│        Pool Table               │  ← R15
│   (FixedPool variables)         │
├─────────────────────────────────┤
│        Data Section             │
│   (string literals, constants)  │
├─────────────────────────────────┤
│        Code Section             │
│   (compiled machine code)       │
└─────────────────────────────────┘
Low addresses
```

---

## Pool Types

AILang has six pool types. Each has a specific purpose. Using the right
pool type is the primary memory management decision in AILang code.

### FixedPool

Global, static, O(1) access. The most common pool type.

```ailang
FixedPool.Config {
    "buffer_size": Initialize=4096
    "max_retries": Initialize=3
    "debug_mode":  Initialize=0
}

// Read
size = Config.buffer_size

// Write
Config.debug_mode = 1
```

**Compiled to:** `MOV RAX, [R15 + offset]` (read) /
`MOV [R15 + offset], RAX` (write) — single instruction, no indirection.

**Use when:** Global state, configuration, counters, statistics, flags.
Maximum 131,072 variables (1 MB pool table limit).

Each variable occupies exactly 8 bytes, addressed as `[R15 + index*8]`.

---

### DynamicPool

Heap-allocated, growable. Two-instruction access (load pointer, then
access field).

```ailang
DynamicPool.Cache {
    "entries": Initialize=0
    "hits":    Initialize=0
    "misses":  Initialize=0
}

Cache.entries = Add(Cache.entries, 1)
hits = Cache.hits
```

**Memory layout:**
```
Stack: [pointer to heap block]
           ↓
Heap:  [capacity: 8][size: 8][field0: 8][field1: 8]...
       ←── header ──→ ←──────── data ────────→
```

**Use when:** Data that grows dynamically, lifetime spans multiple
functions, growable collections.

---

### TemporalPool

Scope-bound. Lifetime tied to the function or block that declares it.
Freed automatically on scope exit.

```ailang
Function.Process.Compress {
    Body: {
        TemporalPool.Workspace {
            "scratch": Initialize=0
            "offset":  Initialize=0
        }

        Workspace.scratch = Allocate(1024)
        // ... use scratch ...
        // Freed automatically on return
    }
}
```

**Use when:** Function-local temporaries, intermediate computation
buffers, short-lived working sets.

---

### LinkagePool

Structured, typed data blocks for passing complex data between
functions. Fields have names, types, and optional direction constraints.

```ailang
LinkagePool.Request {
    "method":   Initialize=0
    "path":     Initialize=0
    "body_len": Initialize=0
    "status":   Initialize=0
}

// Allocate an instance
req = AllocateLinkage(LinkagePool.Request)

// Access fields with dot notation
req.method   = 1
req.path     = path_ptr
req.body_len = 256

// Read fields
method = req.method
```

**Field memory layout:** Each field occupies 8 bytes, contiguous from
the allocation base. Field names are compile-time — no runtime lookup.

**Type safety:** The compiler tracks which `LinkagePool` type each
variable holds. Accessing a field that doesn't belong to the type is a
compile error:

```ailang
LinkagePool.TypeA { "field1": Initialize=0 }
LinkagePool.TypeB { "field2": Initialize=0 }

a = AllocateLinkage(LinkagePool.TypeA)
a.field1 = 10   // valid
a.field2 = 20   // COMPILE ERROR: field2 not in TypeA
```

**Use when:** Structured data passed between functions, typed records,
inter-module communication.

---

### Other Pool Types

These pool types exist in the keyword table and parser for specialized
subsystems. They follow the same declaration syntax as `FixedPool`.

| Type | Purpose |
|------|---------|
| `NeuralPool` | Neural network layer state |
| `KernelPool` | Kernel module interface data |
| `ActorPool` | Actor-model message passing |
| `SecurityPool` | Cryptographic / security state |
| `ConstrainedPool` | Range-validated fields |
| `FilePool` | File I/O state |

---

## Heap Allocation Primitives

### `Allocate(size)` / `Deallocate(ptr, size)`

```ailang
buf = Allocate(1024)
// ... use buf ...
Deallocate(buf, 1024)
```

Routes through `Library.Arena`'s slab allocator. Sizes ≤ 4096 bytes
hit a slab pool (O(1), no syscall after warmup). Sizes > 4096 go to
the general arena (one `mmap` per overflow chunk).

**Critical:** The `size` passed to `Deallocate` must exactly match the
`size` passed to `Allocate`. The slab router uses this value to select
the correct pool. A mismatched size routes to the wrong slab and
corrupts the free list.

```ailang
// CORRECT
buf = Allocate(256)
Deallocate(buf, 256)   // same size

// WRONG — corrupts allocator
buf = Allocate(256)
Deallocate(buf, 0)     // wrong size
```

### `Arena_Reset()`

Resets all slabs to empty without releasing kernel memory. Subsequent
allocations reuse the same physical pages. Overflow chunks are released;
initial chunks are kept. Much cheaper than `FreeAll` + `Init`.

```ailang
// Between compiler passes, grep files, etc.
Arena_Reset()
```

---

## Raw Memory Operations

| Primitive | Description |
|-----------|-------------|
| `RDMEM_64(ptr)` | Read 8-byte value at `ptr` |
| `WRMEM_64(ptr, val)` | Write 8-byte value to `ptr` |
| `RDMEM_8(ptr, offset)` | Read 1 byte at `ptr + offset` |
| `WRMEM_8(ptr, offset, val)` | Write 1 byte at `ptr + offset` |

Every width has a read and a write: `RDMEM_8/16/32/64`, the sign-extending `RDMEM_S8/S16/S32`, and `WRMEM_8/16/32/64`, each taking `(addr)` or `(base, offset)`. See *Memory Access Guide (RDMEM & WRMEM)* for the full set and the `_IO_` forms for device memory.
| `MemoryCopy(dst, src, n)` | Copy `n` bytes (SSE2-vectorized) |
| `MemorySet(ptr, val, n)` | Fill `n` bytes with `val` |
| `MemChr(ptr, byte, n)` | Find byte in `n` bytes, returns offset or -1 (SSE2) |
| `MemCompare(a, b, n)` | Compare `n` bytes, returns 0 if equal (SSE2) |
| `MemMem(hay, haylen, needle, needlen)` | First offset of `needle` in `hay`, or -1 (SSE2) |
| `MemMemFold(hay, haylen, needle, needlen)` | Same search, folding ASCII A–Z to a–z on both sides (SSE2) |
| `AddressOf(var)` | Get address of a variable |

```ailang
// Array element access (8-byte elements)
offset  = Multiply(i, 8)
element = RDMEM_64(base_ptr, offset)

// Struct-style manual layout
WRMEM_64(ptr, id)              // field 0 at offset 0
WRMEM_64(ptr, 8, age)     // field 1 at offset 8
WRMEM_64(ptr, 16, score)  // field 2 at offset 16

id    = RDMEM_64(ptr)
age   = RDMEM_64(ptr, 8)
score = RDMEM_64(ptr, 16)
```

---

## Best Practices

### Choose the right pool type

| Need | Pool |
|------|------|
| Global config / counters / flags | `FixedPool` |
| Growable collections | `DynamicPool` |
| Function-local temporaries | `TemporalPool` |
| Typed structured data | `LinkagePool` |
| Raw buffers / byte arrays | `Allocate()` |

### Always pair Allocate with Deallocate

```ailang
buf = Allocate(1024)
// work
Deallocate(buf, 1024)
```

For cleanup safety, use `Arena_Reset()` at natural boundaries (between
files, between passes) rather than tracking every individual allocation.

### Null-check before dereferencing

```ailang
IfCondition NotEqual(ptr, 0) ThenBlock: {
    val = RDMEM_64(ptr)
}
```

### Bounds-check before array access

```ailang
IfCondition LessThan(index, array_size) ThenBlock: {
    offset  = Multiply(index, 8)
    element = RDMEM_64(array_ptr, offset)
}
```

### Zero pointer after free

```ailang
Deallocate(buf, size)
buf = 0
```

Prevents use-after-free bugs from being silently successful.

### Align large allocations to cache lines

For buffers accessed in hot loops, align to 64 bytes:

```ailang
// Round up to 64-byte cache line boundary
aligned = Multiply(Divide(Add(size, 63), 64), 64)
buf = Allocate(aligned)
```

---

## Performance Notes

### FixedPool is the fastest access in AILang

Single instruction: `MOV RAX, [R15 + offset]`. No pointer chasing, no
cache miss after warmup. Use FixedPool for anything in a hot path.

### DynamicPool costs one extra indirection

Two instructions: load heap pointer from stack, then access field.
One potential cache miss if the heap block is cold.

### Allocate cost scales with size

- **≤ 4096 bytes:** O(1) slab — free list pop or bump pointer. No
  syscall after initial chunk setup.
- **> 4096 bytes:** One `mmap` syscall per overflow chunk (~0.005 µs
  in C, ~0.010 µs in AILang). Frequent large allocations in tight
  loops are the primary memory performance bottleneck — use
  `Arena_Reset()` to amortize.

### MemoryCopy / MemChr / MemCompare / MemMem are SSE2-vectorized

These operate in 16-byte strides. Prefer them over byte-by-byte loops
for any buffer operation on more than a few bytes.

`MemMem` returns the first byte offset of `needle`, or `-1`. A needle
length of 0 returns 0. A haystack shorter than the needle returns `-1`.
`MemMemFold` is the same search with ASCII A–Z folded to a–z in both
buffers. Other bytes, including bytes at or above `0x80`, are compared
unchanged.

---

## Common Patterns

### Ping-pong buffers (grep pattern)

```ailang
FixedPool.Buffers {
    "read_buf":  Initialize=0
    "write_buf": Initialize=0
    "buf_size":  Initialize=1048576   // 1 MiB
}

SubRoutine.InitBuffers {
    Buffers.read_buf  = Allocate(Buffers.buf_size)
    Buffers.write_buf = Allocate(Buffers.buf_size)
}

// Swap without copying
SubRoutine.SwapBuffers {
    tmp = Buffers.read_buf
    Buffers.read_buf  = Buffers.write_buf
    Buffers.write_buf = tmp
}
```

### Manual ring buffer

```ailang
FixedPool.Ring {
    "buf":   Initialize=0
    "head":  Initialize=0
    "tail":  Initialize=0
    "size":  Initialize=256
    "count": Initialize=0
}

SubRoutine.RingPush {
    // assumes: value is set by caller
    IfCondition LessThan(Ring.count, Ring.size) ThenBlock: {
        offset = Multiply(Ring.tail, 8)
        WRMEM_64(Ring.buf, offset, value)
        Ring.tail  = Modulo(Add(Ring.tail, 1), Ring.size)
        Ring.count = Add(Ring.count, 1)
    }
}

SubRoutine.RingPop {
    // sets: value for caller
    IfCondition GreaterThan(Ring.count, 0) ThenBlock: {
        offset = Multiply(Ring.head, 8)
        value = RDMEM_64(Ring.buf, offset)
        Ring.head  = Modulo(Add(Ring.head, 1), Ring.size)
        Ring.count = Subtract(Ring.count, 1)
    }
}
```

### Bump allocator (arena within arena)

```ailang
FixedPool.Bump {
    "base":  Initialize=0
    "next":  Initialize=0
    "limit": Initialize=0
}

SubRoutine.BumpInit {
    Bump.base  = Allocate(65536)
    Bump.next  = Bump.base
    Bump.limit = Add(Bump.base, 65536)
}

Function.BumpAlloc {
    Input:  size: Integer
    Output: Address
    Body: {
        aligned = Multiply(Divide(Add(size, 7), 8), 8)
        IfCondition GreaterThan(Add(Bump.next, aligned), Bump.limit) ThenBlock: {
            ReturnValue(0)
        }
        ptr = Bump.next
        Bump.next = Add(Bump.next, aligned)
        ReturnValue(ptr)
    }
}
```

---

## Troubleshooting

### Segmentation fault (SIGSEGV)

- Dereferencing `0` — check for null before `RDMEM_64`
- Out-of-bounds array access — check index against size
- Use-after-free — zero the pointer after `Deallocate`
- Wrong `Deallocate` size routed to wrong slab — verify sizes match

### Memory leak / RSS growth

- Missing `Deallocate` — pair every `Allocate`
- Or: use `Arena_Reset()` at natural boundaries instead of tracking
  individual allocations

### Pool table overflow (compiler error)

More than 131,072 `FixedPool` variables. Move large collections to
`DynamicPool` or `Allocate`.

### Corrupted allocator (crash on Deallocate)

Almost always a size mismatch: `Allocate(256)` paired with
`Deallocate(ptr, 512)`. The slab router uses the size to find the free
list. Wrong size → wrong slab → corrupted free list pointer.

---

## See Also

`Library.Arena`,
`AILang Language Introduction`,
`AILang Operators Reference`

---

## Copyright

Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
