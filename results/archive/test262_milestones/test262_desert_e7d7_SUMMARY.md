# M128e7d7 — BigInt64/BigUint64 element Get/Set (real BigInt)

**Desert tip:** **1112 / 2931 (38.2%)**  
**vs e7d6:** 1040 → **1112** (**+72**)  
**vs e7d0:** 566 → **1112** (**+546**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 24.0% |
| DataView | 28.0% |
| TypedArray | **38.9%** |
| TypedArrayConstructors | **48.5%** |

## Changes

1. **`JSVM_TA_Set` BigInt kinds (9/10)** — `ToBigInt` + `asIntN/asUintN(64)` + 8-byte LE two's complement store (was `ToNumber`, which TypeErrors on `1n` and broke all BigInt TA element writes / ctors-from-array).
2. **`JSVM_TA_Get` BigInt kinds** — read 8 LE bytes → `BI__FromTwos` (signed) or unsigned limbs → real `JSType.BIGINT` (was low-31-bit number hack).
3. **SET_ELEM** — propagate `exc_prop` from `TA_Set` (ToBigInt/ToNumber throws).

Smoke: `new BigInt64Array([10n,20n,30n])`, `a[0]=1n/-2n/2^32/2^63` wrap, OwnPropertyKeys indexes, bind+makeCtorArg all green.

## Net

~+72 desert; bulk of gains on BigInt method/internals clusters (same “makeCtorArg + real element values” path as e7d6 bind fix — not mysterious regs).

## Full-suite 95%

~1.82k desert fails remain. Full engine rescore (e7d6 harness tip) running in parallel; e7d7 batch binary built as `test262_harness_batch_e7d7.x` so the full run is not disrupted.
