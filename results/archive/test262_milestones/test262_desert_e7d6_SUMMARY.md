# M128e7d6 — bind CallBuf fix + TA @@iterator + Reflect.ownKeys

**Desert tip:** **1040 / 2931 (35.7%)**  
**vs e7d5:** 905 → **1040** (**+135**)  
**vs e7d0:** 566 → **1040** (**+474**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 24.0% |
| DataView | 28.0% |
| TypedArray | **35.7%** |
| TypedArrayConstructors | **44.6%** |

## Root causes fixed

1. **`Function.prototype.bind` CallBuf clobber (FUNC_BOUND)**  
   Partial args were written into `JSVMCallBuf` while call-time args still aliased that buffer → `f.bind(null,1)(2,3)` became `(1,1,1)`.  
   **Impact:** every `testWithTypedArrayConstructors` `makeCtorArg = factory.bind(TA, …)` returned the constructor instead of the array → empty TAs, mass false fails across map/filter/set/copyWithin/DefineOwnProperty/Delete/etc.

2. **TypedArray ctor `@@iterator` path**  
   `makeIterable` harness factory yields `{[Symbol.iterator]}` with no `.length`. ES prefers iterator over array-like; we now `JSVM_IterableToArray` then allocate.

3. **`Reflect.ownKeys` polyfill** (+ deleteProperty / preventExtensions / isExtensible / get|setPrototypeOf)  
   Unlocks `Reflect.ownKeys` OwnPropertyKeys tests (integer-indexes + string-keys green).

4. **Object.keys / OBJ_KEYS → TA OwnPropertyKeys** (for-in enumerable indexes).

## Notable gains (sample)

| Cluster | Δ pass |
|---------|-------:|
| copyWithin / map | +14 each |
| INT Delete | +12 |
| set / some / DefineOwnProperty | +11 |
| find / every / findIndex / fill / filter | +7–10 |

Net: **+196 pass / −61 reg** (regs mostly BigInt/resizable edges + batch-order flake).

## OwnPropertyKeys

- `integer-indexes.js` **pass**
- `integer-indexes-and-string-keys.js` **pass**
- symbol-keys / not-enumerable: green alone; some batch-order flake after prototype mutation tests
- BigInt / resizable: still fail (no real BigInt TA / no resizable AB)

## Full-suite 95%

~1.89k desert fails remain. Next: species polish on map/filter/slice, set typedarray-arg edges, detach model, BigInt TAs, length/byteLength accessors on proto (hide own stamps).
