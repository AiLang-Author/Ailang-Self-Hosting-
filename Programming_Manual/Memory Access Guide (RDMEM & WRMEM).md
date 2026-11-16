# Memory Access Guide (RDMEM & WRMEM)

Every read and write of raw memory in AILang names its width. There is one
read family, `RDMEM_`, and one write family, `WRMEM_`. The suffix after the
underscore is the width in bits.

| Read | Write | Width | Read result |
|---|---|---|---|
| `RDMEM_8` | `WRMEM_8` | 1 byte | 0 to 255 |
| `RDMEM_16` | `WRMEM_16` | 2 bytes | 0 to 65535 |
| `RDMEM_32` | `WRMEM_32` | 4 bytes | 0 to 4294967295 |
| `RDMEM_64` | `WRMEM_64` | 8 bytes | full 64-bit value |
| `RDMEM_S8` | — | 1 byte | -128 to 127 |
| `RDMEM_S16` | — | 2 bytes | -32768 to 32767 |
| `RDMEM_S32` | — | 4 bytes | -2147483648 to 2147483647 |

Every value is 64 bits wide in a register. A plain read zero-extends; an
`S` read sign-extends. A write stores the low bytes of the value and
leaves the neighbouring bytes alone. There are no signed writes, because
the low bytes are the same either way.

A misspelled name, such as `RDMEM_24` or `RDMEM_s8`, is a compile error.

## Two ways to give the address

Every primitive takes the address either whole or as a base and an offset
in bytes:

```ailang
value = RDMEM_32(addr)               // read 4 bytes at addr
value = RDMEM_32(base, offset)       // read 4 bytes at base + offset

WRMEM_32(addr, value)                // write 4 bytes at addr
WRMEM_32(base, offset, value)        // write 4 bytes at base + offset
```

The two forms compile to the same code. `RDMEM_32(base, offset)` is
`RDMEM_32(Add(base, offset))` written without the `Add`. The offset is
always in bytes: element `i` of an array of 32-bit values is at
`Multiply(i, 4)`.

## Reading

```ailang
buffer = Allocate(16)
WRMEM_64(buffer, -5)
WRMEM_16(buffer, 8, 65534)

a = RDMEM_64(buffer)            // -5
b = RDMEM_16(buffer, 8)         // 65534
c = RDMEM_S16(buffer, 8)        // -2   (same bytes, read signed)
d = RDMEM_8(buffer, 8)          // 254  (low byte of 0xFFFE)
```

Strings are byte arrays, so walking a string is `RDMEM_8` with an index:

```ailang
message = "Hello"
i = 0
WhileLoop NotEqual(RDMEM_8(message, i), 0) {
    PrintNumber(RDMEM_8(message, i))
    PrintMessage(" ")
    i = Add(i, 1)
}
// 72 101 108 108 111
```

## Writing

A write never changes more bytes than its width:

```ailang
buffer = Allocate(8)
WRMEM_64(buffer, -1)            // FF FF FF FF FF FF FF FF
WRMEM_16(buffer, 2, 0)          // FF FF 00 00 FF FF FF FF
WRMEM_8(buffer, 7, 0)           // FF FF 00 00 FF FF FF 00
```

Building a string a byte at a time:

```ailang
buffer = Allocate(8)
WRMEM_8(buffer, 0, 72)          // 'H'
WRMEM_8(buffer, 1, 73)          // 'I'
WRMEM_8(buffer, 2, 0)           // terminator
PrintString(buffer)             // HI
```

## Arrays and records

Arrays of wider values use the matching width and a byte offset:

```ailang
// 100 32-bit counters
counts = Allocate(400)
MemorySet(counts, 0, 400)
i = 7
old = RDMEM_32(counts, Multiply(i, 4))
WRMEM_32(counts, Multiply(i, 4), Add(old, 1))
```

Fixed record layouts read naturally with a constant offset:

```ailang
// header: magic (4) | version (2) | flags (2) | length (8)
magic   = RDMEM_32(hdr, 0)
version = RDMEM_16(hdr, 4)
flags   = RDMEM_16(hdr, 6)
length  = RDMEM_64(hdr, 8)
```

## Binary formats

File formats are little-endian on x86, so a 16- or 32-bit field is one read,
not a sum of bytes:

```ailang
// WAV: channels at offset 22, sample rate at 24
channels = RDMEM_16(wav, 22)
rate     = RDMEM_32(wav, 24)

// a signed 16-bit PCM sample
sample = RDMEM_S16(pcm, Multiply(i, 2))
```

Big-endian fields (MIDI, PNG, network order) still need their bytes put back
in order:

```ailang
// MIDI chunk length, big-endian 32-bit
len = BitwiseOr(BitwiseOr(LeftShift(RDMEM_8(buf, 0), 24), LeftShift(RDMEM_8(buf, 1), 16)),
                BitwiseOr(LeftShift(RDMEM_8(buf, 2), 8), RDMEM_8(buf, 3)))
```

## Device memory: the `_IO_` forms

Memory-mapped hardware registers use `RDMEM_IO_<w>` and `WRMEM_IO_<w>`, with
the same widths and the same two address forms:

```ailang
status = RDMEM_IO_32(mmio, REG_STATUS)
WRMEM_IO_32(mmio, REG_CONTROL, 1)
```

The optimizer may cache, merge, move, or drop ordinary memory reads when it
can prove the result is the same. A device register is different: reading
it can clear a flag, and the value can change by itself. Every `_IO_`
access is exactly one access of that width, in program order. It is never
cached, hoisted out of a loop, merged with another access, split, or
removed. A polling loop therefore reads the register on every pass:

```ailang
WhileLoop EqualTo(BitwiseAnd(RDMEM_IO_32(mmio, REG_STATUS), READY), 0) {
    // waits until the device sets READY
}
```

Use `_IO_` only for device memory. On ordinary memory it gives up
optimizations for nothing.

## Common mistakes

### Reading with the wrong width

```ailang
WRMEM_32(buf, 0, 1000)
x = RDMEM_64(buf)       // WRONG: also reads the 4 bytes after the value
x = RDMEM_32(buf)       // RIGHT: 1000
```

### Reading a signed field unsigned

```ailang
WRMEM_16(buf, 0, -2)
x = RDMEM_16(buf)       // 65534: the bytes read as unsigned
x = RDMEM_S16(buf)      // -2
```

### Offsets in elements instead of bytes

```ailang
v = RDMEM_32(table, i)                  // WRONG: byte offset i
v = RDMEM_32(table, Multiply(i, 4))     // RIGHT: element i
```

### Forgetting the terminator

`PrintString` and the string functions read until a 0 byte. A buffer
built byte by byte needs `WRMEM_8(buf, n, 0)` at the end.

### Reading or writing past the allocation

Nothing checks bounds. `Allocate(5)` followed by `RDMEM_8(buf, 100)` reads
whatever is there, or crashes.

## Bulk operations

For whole blocks, use the bulk builtins rather than a loop of single
accesses:

- `MemoryCopy(dest, src, count)` copies `count` bytes.
- `MemorySet(dest, byte, count)` fills `count` bytes.
- `MemoryCompare(a, b, count)` compares `count` bytes.

## Older code

Before November 2026 these operations were spelled `GetByte`, `SetByte`,
`Dereference`, and `StoreValue`, with widths given as the strings `"byte"`,
`"word"`, `"dword"`, and `"qword"`. Those names no longer exist. Old source
converts mechanically:

```
python3 -I tools/memprim_migrate.py --write --split-add PATH...
```

| Old | New |
|---|---|
| `GetByte(b, o)` | `RDMEM_8(b, o)` |
| `SetByte(b, o, v)` | `WRMEM_8(b, o, v)` |
| `Dereference(a)` | `RDMEM_64(a)` |
| `Dereference(a, "dword")` | `RDMEM_32(a)` |
| `StoreValue(a, v)` | `WRMEM_64(a, v)` |
| `StoreValue(a, v, "word")` | `WRMEM_16(a, v)` |
