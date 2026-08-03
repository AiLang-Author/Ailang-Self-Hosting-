# M128e7d2 — TypedArray.from/of + set polish

**vs e7d1c:** 746 → **766** pass (+20), 25.6% → **26.2%**  
**vs e7d0:** 566 → **766** (+200)

| Category | e7d1c | e7d2 | Δ |
|----------|-----:|-----:|--:|
| ArrayBuffer | 23.0% | 23.0% | 0 |
| DataView | 27.1% | 27.1% | 0 |
| TypedArray | 15.3% | **16.1%** | +0.8pp |
| TypedArrayConstructors | 45.2% | **46.2%** | +1.0pp |
| **TOTAL** | 25.6% | **26.2%** | **+0.6pp** |

## Changes

- **Array.from/of species path** for non-Array constructors (TypedArray)
- **TA_FROM / TA_OF** native IDs (require `IsConstructor(this)`)
- **CallBuf clobber fix** for `of()` — Construct was overwriting args buffer
- **set()**: negative offset RangeError, ArrayLike source, ToNumber(offset)
- ArrayLikeSet for custom `of` results

## Smoke green

`Uint8Array.from/of`, mapfn, Int16 negative, set + RangeError, Array.from still array, `of.call(null)` TypeError
