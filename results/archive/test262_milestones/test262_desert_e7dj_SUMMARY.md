# M128e7dj — DataView get/set BigInt64/BigUint64/Float16

**Desert tip:** **1481 / 2931 (50.8%)**  
**vs e7di:** 1369 → **1481** (**+112**)  
**vs e7d0:** 566 → **1481** (**+915**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **29.1%** |
| DataView | **51.3%** (was 31.9%) |
| TypedArray | **49.4%** |
| TypedArrayConstructors | **59.0%** |

## Changes

**DataView.prototype** methods installed + native handlers:

- `getBigInt64` / `setBigInt64` / `getBigUint64` / `setBigUint64`
- `getFloat16` / `setFloat16`
- Native IDs 343–348; NDVGetN/SetN kinds 8/9/10
- Endian-aware for BigInt/Float16 (littleEndian arg; default big-endian)
- Brand check TypeError on NDVGetN/SetN (non-DataView `this`)
- Float16: f16↔f32 soft convert via existing F32 helpers

## Ladder

```
e7dh 1343 → e7di 1369 → e7dj 1481 (50.8%)
```
