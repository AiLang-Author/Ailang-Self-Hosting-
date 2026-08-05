# M128e7dh — Generator.prototype[@@iterator]

**Desert tip:** **1343 / 2931 (46.2%)**  
**vs e7dg:** 1339 → **1343** (**+4**)  
**vs e7d0:** 566 → **1343** (**+777**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 28.6% |
| DataView | 29.1% |
| TypedArray | **48.7%** |
| TypedArrayConstructors | **59.0%** |

## Changes

1. **Generator.prototype[Symbol.iterator]** — native (bc `-9994`) returns `this` (ES identity iterator).
2. **CALL / CallFunc** — handle `-9994` / handler 9993 as return-this.
3. **IterableToArray** — accept non-OBJECT iterators that still have `.next` (belt-and-suspenders for generators).

Unblocks object-arg paths that require GetMethod(@@iterator) on generator instances (`iterating-throws`, `as-generator-iterable-returns`, …).  
Array.from(generator) still incomplete (separate collector path).

## Ladder

```
e7df 1338 → e7dg 1339 → e7dh 1343 (46.2%)
```
