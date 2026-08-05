# M128e7dg — TypedArray.prototype.set: snapshot TypedArray sources

**Desert tip:** **1339 / 2931 (46.0%)**  
**vs e7df:** 1338 → **1339** (**+1**)  
**vs e7d0:** 566 → **1339** (**+773**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 28.6% |
| DataView | 29.1% |
| TypedArray | **48.7%** |
| TypedArrayConstructors | **58.6%** |

## Changes

**TypedArray.prototype.set(typedArray)** — always clone the source element range into a fresh ArrayBuffer before the copy loop (spec CloneArrayBuffer when same buffer; always-clone is correct and fixes overlapping views).

Green: `typedarray-arg-set-values-same-buffer-same-type.js`  
Still open: other-type / SAB / resizable same-buffer; BigInt variants under makeCtorArg.

## Next

- same-buffer other-type / BigInt harness paths  
- object-arg generator iteration  
- buffer-arg SAB  

## Ladder

```
e7de 1336 → e7df 1338 → e7dg 1339 (46.0%)
```
