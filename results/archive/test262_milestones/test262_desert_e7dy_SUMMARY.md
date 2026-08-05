# M128e7dy — map species TypedArrayCreate validate (exc_prop)

**Desert tip:** **1972 / 2931 (67.6%)**  
**vs e7dx:** 1938 → **1972** (**+34**)  
**vs e7d0:** 566 → **1972** (**+1406**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **40.3%** |
| DataView | **81.8%** |
| TypedArray | **64.2%** (was 63.3%) |
| TypedArrayConstructors | **70.6%** (was 67.6%) |

## Changes

- **TypedArraySpeciesCreate**: reject `Array` species early; after Construct reject non-TA / short length via `exc_prop` (avoids ThrowValue VM-error under map)
- **ArrMap**: post-create TypedArray brand check

## Ladder

```
e7dx 1938 → e7dy 1972 (67.6%)
```
