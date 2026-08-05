# M128e7d1 — TypedArray methods foothold (desert)

**vs e7d0:** 566 → **746** pass (+180), **19.4% → 25.6%**

| Category | e7d0 | e7d1 | Δ |
|----------|-----:|-----:|--:|
| ArrayBuffer | 23.0% | 23.0% | 0 |
| DataView | 27.5% | 27.1% | -0.4pp |
| TypedArray | 9.1% | **15.3%** | +6.2pp |
| TypedArrayConstructors | 32.3% | **45.2%** | +12.9pp |
| **TOTAL** | 19.4% | **25.6%** | **+6.2pp** |

## What landed

1. **ArrayLike Get/Has/Set/Len** — TypedArray buffer elements (was ObjGet miss)
2. **ArraySpeciesCreate** — TypedArray same-kind / ctor construct
3. **map/filter/slice** result writes via ArrayLikeSet; filter two-pass for fixed length
4. **Shared `%TypedArray%.prototype`** — methods inherited by all TA ctors
5. Methods: map, filter, forEach, every, some, find*, reduce*, indexOf*, includes, join, toString, fill, copyWithin, reverse, slice, sort, at, keys/values/entries, with, toReversed, toSorted, set, subarray
6. **CALL_METHOD** rethrow for array method TypeErrors (not-callable etc.)

## Next

- TypedArray.from/of (species-aware)
- species custom-ctor throws / detach edges
- DataView float IEEE + endian
- set() BigInt / multi-source polish
