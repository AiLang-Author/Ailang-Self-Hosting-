# M128e7da — ValidateTypedArray brand on %TypedArray%.prototype methods

**Desert tip:** **1282 / 2931 (44.0%)**  
**vs e7d9:** 1220 → **1282** (**+62**)  
**vs e7d0:** 566 → **1282** (**+716**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 27.0% |
| DataView | 31.2% |
| TypedArray | **47.8%** |
| TypedArrayConstructors | 50.8% |

## Changes

1. **`JSVM__ValidateTypedArray`** — TypeError if `this` is not a TypedArray instance.
2. **Mark TA proto methods** with own `__ta_meth__` at install (separate function objects from `Array.prototype.*`).
3. **Brand check** before `DispatchStringMethod` on:
   - CALL path  
   - CALL_METHOD path  
   - `JSVM__CallFunc` (.call/.apply) path  

Array.prototype methods remain unmarked → no brand check.

## Why this order

Shared ARR_* handler IDs meant `TypedArray.prototype.map.call({})` behaved like Array map (no throw). ES requires ValidateTypedArray first — unblocks this-is-not-typedarray / invoked-as-func across map/filter/slice/forEach/etc.

## Next

- buffer-arg / object-arg ctor edges (~72 fails)  
- set / detach  
- residual species custom-ctor  
- DV get/set this-is-not-object  

## Full-suite 95%

Desert tip **44%**; built-ins full last at **43.1%** (e7d6, pre-e7d7..da). Next full rescore should clear 45%+.
