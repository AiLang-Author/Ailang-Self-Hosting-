# M128e7dk — DataView littleEndian + signed set + brand TE

**Desert tip:** **1533 / 2931 (52.6%)**  
**vs e7dj:** 1481 → **1533** (**+52**)  
**vs e7d0:** 566 → **1533** (**+967**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **29.1%** |
| DataView | **60.6%** (was 51.3%) |
| TypedArray | **49.4%** |
| TypedArrayConstructors | **58.9%** |

## Changes

- **littleEndian** for all multi-byte DataView get/set (default big-endian)
- **Signed int writes**: map negatives to two’s-complement via +2^8/+2^16/+2^32 before byte extract
- **f32 get**: IEEE bits via `JSVM_F32BitsToNumber` (not raw CreateFloat)
- **f32 set**: `JSVM_NumberToF32Bits` + endian
- **Value before range**: ToNumber/ToBigInt before range check
- **Missing value arg**: treat as `undefined` (no early return)
- **get/setUint8** routed through generic NDV (brand TypeError)
- f32 subnormal soft path (not yet bit-exact for all return-values cases)

## Ladder

```
e7di 1369 → e7dj 1481 → e7dk 1533 (52.6%)
```
