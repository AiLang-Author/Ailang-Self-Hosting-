# M128e7d0 desert foothold — ArrayBuffer / TypedArray / DataView

**Date:** 2026-08-03  
**Harness:** test262_harness_batch.x (post TypedArray wire)

## Slice scores (paths: built-ins/ArrayBuffer, TypedArray, TypedArrayConstructors, DataView)

| Category | Total | Pass | Fail | T/O | Pass% |
|----------|------:|-----:|-----:|----:|------:|
| ArrayBuffer | 196 | 45 | 151 | 0 | 23.0% |
| DataView | 561 | 154 | 407 | 0 | 27.5% |
| TypedArray | 1438 | 130 | 1300 | 5 | 9.1% |
| TypedArrayConstructors | 736 | 237 | 497 | 2 | 32.3% |
| **TOTAL** | **2931** | **566** | **2355** | **7** | **19.4%** |

## What landed (e7d0)

- `Library.JSVMTypedArray.ailang`: AB create/slice/isView; TA create/get/set/set/subarray; DV get/set ints+floats (LE)
- Native IDs 300–332; Builtins install all TA ctors + AB + DV
- GET_ELEM/SET_ELEM integer-index intercept for TypedArray
- CONSTRUCT allowlist + `__new_target__` for native ctors
- Smoke: construct, index R/W, slice, subarray, set, isView, DataView u8, clamp — green

## Next desert grind

- Species / @@species on ArrayBuffer & TA
- from/of/%TypedArray% prototype methods (map, filter, …)
- Float IEEE fidelity; BigInt64 full
- byteLength RangeError edge cases; detach (if any)
- Temporal still deferred

Was ~0% on these paths before install (ReferenceError on every global).
