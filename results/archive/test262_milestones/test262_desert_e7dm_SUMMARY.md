# M128e7dm — DataView length + Symbol.toStringTag

**Desert tip:** **1574 / 2931 (54.0%)**  
**vs e7dl:** 1572 → **1574** (**+2**)  
**vs e7d0:** 566 → **1574** (**+1008**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **29.1%** |
| DataView | **67.9%** |
| TypedArray | **49.4%** |
| TypedArrayConstructors | **58.9%** |

## Changes

- DataView `length` = 1 (required buffer arg only)
- `DataView.prototype[Symbol.toStringTag]` = `"DataView"` (!W !E C)

## Ladder

```
e7dk 1533 → e7dl 1572 → e7dm 1574 (54.0%)
```
