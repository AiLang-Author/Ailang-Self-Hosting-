# M128e7dl — DataView ToIndex + NewTarget

**Desert tip:** **1572 / 2931 (53.9%)**  
**vs e7dk:** 1533 → **1572** (**+39**)  
**vs e7d0:** 566 → **1572** (**+1006**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **29.1%** |
| DataView | **67.6%** (was 60.6%) |
| TypedArray | **49.4%** |
| TypedArrayConstructors | **58.9%** |

## Changes

- **`JSVM_ToIndex`**: NaN/undefined → 0; trunc toward 0; RangeError on negatives and ±Infinity
- NDV get/set use ToIndex for byteOffset (fixes `toindex-byteoffset`, NaN/undefined)
- Set: ToIndex **before** value conversion (`index-check-before-value-conversion`)
- DataView ctor: NewTarget required; ToIndex on byteOffset/byteLength

## Ladder

```
e7dj 1481 → e7dk 1533 → e7dl 1572 (53.9%)
```
