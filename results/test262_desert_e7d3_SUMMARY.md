# M128e7d3 — %TypedArray% chain, species, buffer-arg, CONSTRUCT rethrow

**vs e7d2:** 766 → **880** (+114), **26.2% → 30.1%**  
**vs e7d0:** 566 → **880** (+314)

| Category | e7d2 | e7d3 | Δ |
|----------|-----:|-----:|--:|
| ArrayBuffer | 23.0% | **24.0%** | +1.0pp |
| DataView | 27.1% | **28.0%** | +0.9pp |
| TypedArray | 16.1% | **26.4%** | **+10.3pp** |
| TypedArrayConstructors | 46.2% | 40.7% | -5.5pp (stricter new/buffer) |
| **TOTAL** | 26.2% | **30.1%** | **+3.9pp** |

## Changes

1. **%TypedArray% intrinsic** — `Object.getPrototypeOf(Int8Array)` is shared base; shared methods on `.prototype`
2. **Symbol.species** data prop on each TA ctor
3. **SpeciesConstructor** for OBJECT `constructor` + getter `@@species` (map/filter/slice)
4. **subarray** species with `(buffer, byteOffset, length)` args
5. **buffer-arg** ToIndex, alignment, length bounds
6. **CONSTRUCT rethrow** of native RangeError/TypeError (was swallowed)
7. TypedArray ctor requires `new`

## Full-suite path

Desert still ~2.0k fails. At +314 from e7d0, keep grinding species/detach/set/internals toward full 95%.
