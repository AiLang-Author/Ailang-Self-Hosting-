# M128e7d9 — DataView accessors + species GetProperty

**Desert tip:** **1220 / 2931 (41.9%)**  
**vs e7d8:** 1219 → **1220** (**+1 net**; +54/−53 churn)  
**vs e7d0:** 566 → **1220** (**+654**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 27.0% |
| DataView | **31.2%** (was 28.0%) |
| TypedArray | 43.5% |
| TypedArrayConstructors | 50.8% |

## Changes

1. **DataView.prototype** `byteLength` / `byteOffset` / `buffer` accessors (same pattern as e7d8 TA/AB). Drop own data stamps on instances.
2. **TypedArraySpeciesCreate** + **subarray species**: `JSRT_ObjGet` → `JSVM__GetProperty` so `constructor` / `@@species` **accessors fire** (speciesctor-get-species* was at 0 calls).

## Targeted signal (cleaner than full desert)

| Surface | Note |
|---------|------|
| DV buffer/byteLength/byteOffset dirs | **28/38 (73.7%)** |
| species-related | **44 → 57** (+13) |
| map / filter | +4 each |

Full-desert net is flat because of batch churn (set/slice BigInt edges flip); isolated `speciesctor-get-species` green.

## Next

- ValidateTypedArray brand check on TA methods (this-is-not-typedarray*)  
- buffer-arg / object-arg ctors  
- set / detach edges  
- species residual (custom-ctor length throws, resizable)
