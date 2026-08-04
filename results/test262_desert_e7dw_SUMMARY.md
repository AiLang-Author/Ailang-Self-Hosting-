# M128e7dw — subarray brand/species, with/toReversed/toSorted same-type, species validate

**Desert tip:** **1920 / 2931 (65.8%)**  
**vs e7dv:** 1901 → **1920** (**+19**)  
**vs e7d0:** 566 → **1920** (**+1354**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **40.3%** |
| DataView | **81.8%** |
| TypedArray | **62.1%** (was 60.8%) |
| TypedArrayConstructors | **67.6%** |

## Changes

- **subarray**: TypeError brand check; no detach throw (species gets correct byteOffset after end-detach)
- **TypedArraySpeciesCreate**: ValidateTypedArray + min length on species Construct result
- **with / toReversed / toSorted**: TypedArrayCreateSameType (ignore species/constructor)
- **with**: ToNumber/ToBigInt value before index bounds

## Ladder

```
e7dv 1901 → e7dw 1920 (65.8%)
```
