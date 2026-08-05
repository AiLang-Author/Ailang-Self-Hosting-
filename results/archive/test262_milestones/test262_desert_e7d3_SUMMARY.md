# M128e7d3 — %TypedArray% chain, species, buffer-arg, HasProperty

**Desert tip:** **882 / 2931 (30.2%)**  
**vs e7d0:** 566 → **882** (**+316**)  
**vs e7d2:** 766 → **882** (**+116**)

| Category | Pass% | Pass/Tot |
|----------|------:|---------:|
| ArrayBuffer | 24.0% | 47/196 |
| DataView | 28.0% | 157/561 |
| TypedArray | **26.3%** | 375/1438 |
| TypedArrayConstructors | 41.3% | 303/736 |

## Changes (e7d3)

1. **%TypedArray% intrinsic** — ctor [[Prototype]] chain for `Object.getPrototypeOf(Int8Array)`
2. **Symbol.species** on each TA constructor
3. **SpeciesConstructor** for OBJECT constructor + @@species getters
4. **subarray** species Construct(buffer, offset, length)
5. **buffer-arg** ToIndex / align / bounds
6. **CONSTRUCT rethrow** of native RangeError/TypeError
7. **HasProperty** integer-index exotic for TypedArray (`0 in ta`)
8. Writable+configurable `constructor` on TA.prototype

## Full-suite 95% note

~2.0k desert fails remain (detach, BigInt fidelity, SAB, transfer/resize, float16, more species/internals). Keep grinding — essential for raw 95%.
