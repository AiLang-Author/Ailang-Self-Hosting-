# M128e7dn — TA ToIndex length + filter single-pass + @@toStringTag getter

**Desert tip:** **1606 / 2931 (55.1%)**  
**vs e7dm:** 1574 → **1606** (**+32**)  
**vs e7d0:** 566 → **1606** (**+1040**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **29.1%** |
| DataView | **67.9%** |
| TypedArray | **51.5%** (was 49.4%) |
| TypedArrayConstructors | **59.2%** |

## Changes

- **TypedArray(length)**: non-Object first arg uses `JSVM_ToIndex` (NaN/string/bool/etc.)
- Buffer-arg byteOffset/length also use `JSVM_ToIndex`
- **filter**: single-pass collect into list (was double-invoking callback)
- **@@toStringTag** getter on `%TypedArray%.prototype` returns per-kind name (`Int8Array`, …)

## Ladder

```
e7dl 1572 → e7dm 1574 → e7dn 1606 (55.1%)
```
