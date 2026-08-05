# M128e7de — TA_Set ToNumber abrupt + object-arg GetProperty

**Desert tip:** **1336 / 2931 (45.9%)**  
**vs e7dd:** 1324 → **1336** (**+12**)  
**vs e7d0:** 566 → **1336** (**+770**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 28.6% |
| DataView | 29.1% |
| TypedArray | **48.7%** |
| TypedArrayConstructors | **58.1%** |

## Changes

1. **JSVM_TA_Set** — after `ToNumber` (non-BigInt), propagate `exc_prop` (valueOf/toString throws).
2. **object-arg ctor** — length via `GetProperty` + ToNumber; element get via `GetProperty`; check exceptions after Get and Set.
3. **TypedArray.prototype.set** — check `exc_prop` after each `TA_Set`.

## Next

- remaining object-arg (iterator, BigInt ToBigInt)  
- set / filter species  
- full-suite rescore  

## Ladder

```
e7dc 1307 → e7dd 1324 → e7de 1336 (45.9%)
```
