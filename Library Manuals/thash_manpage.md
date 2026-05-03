# Library.THash(ailang)

## NAME
`Library.THash` — magic 64-bit hash mixing function with avalanche property

## SYNOPSIS
```
LibraryImport.THash
```
> Requires: none (pure computation, no allocation, no dependencies)

## DESCRIPTION
THash provides a single high-quality 64-bit → 64-bit mixing function based on a split-mix construction. The function guarantees full avalanche: flipping any input bit changes approximately half the output bits on average. It is designed for use as the hash primitive in HashMap, hash tables, bloom filters, and content fingerprinting.

The construction uses two multiply-xorshift rounds with carefully chosen Weyl constants derived from the golden ratio and silver ratio. The function is fully deterministic and stateless.

| Property | Value |
|---|---|
| Input width | 64 bits (Integer) |
| Output width | 64 bits (Integer) |
| Rounds | 2 (multiply-xorshift then finalize) |
| Constants | 0x9E3779B97F4A7C15 (golden), 0xC6A4A7935BD1E995 (silver) |
| Avalanche | Full (≈32 bits flip per bit) |
| Pipeline | 3–5 cycles on modern x86_64 |

## FUNCTIONS

```
Function.THash.mix64
    Input:  x: Integer
    Output: Integer
```
The primary hash mixing function. Takes a 64-bit integer and returns a pseudo-randomised 64-bit integer with full avalanche.

Algorithm:
1. `x = x ^ (x >> 30)`
2. `x = x * GOLDEN`
3. `x = x ^ (x >> 27)`
4. `x = x * SILVER`
5. `x = x ^ (x >> 31)`
6. Return `x`

```
Function.THash.combine
    Input:  a: Integer, b: Integer
    Output: Integer
```
Hash combination: hashes `a` and `b` together into a single 64-bit value suitable for incremental hashing (e.g. hashing a struct by combining field hashes). Equivalent to `mix64(a ^ mix64(b))`.

```
Function.THash.bytes
    Input:  data: Address, length: Integer
    Output: Integer
```
Hashes an arbitrary byte range into a 64-bit integer. Uses the same split-mix construction applied per 8-byte chunk with carry. Unaligned trailing bytes are handled with zero-padding and a final mix. The empty buffer hashes to a non-zero constant.

## MEMORY
THash allocates no memory. All functions are pure computation operating on registers and the stack.

## EXAMPLE

```ailang
LibraryImport.THash

THash.mix64  1234567890123456789  → h
# h = -571123456789012345 (some pseudo-random 64-bit value)

THash.combine  h  42  → combined

# Hash a string buffer
String.literal  "hello world"  → buf
String.length   buf            → len
THash.bytes     buf  len       → digest
```

## SEE ALSO
`Library.HashMap` — consumer of THash for key hashing
`Library.XArrays` — dynamic arrays, sometimes used with THash for hash sets

## VERSION
2026-05-15 — initial specification (Phase 1 Tier 1)

## COPYRIGHT
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
