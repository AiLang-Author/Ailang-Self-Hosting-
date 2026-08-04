# M128e7dt — DV/iterator/ctor detach order

**Desert tip:** **1813 / 2931 (62.1%)**  
**vs e7ds:** 1770 → **1813** (**+43**)  
**vs e7d0:** 566 → **1813** (**+1247**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **34.2%** |
| DataView | **81.6%** (was 76.1%) |
| TypedArray | **57.8%** (was 57.3%) |
| TypedArrayConstructors | **63.2%** (was 62.8%) |

## Changes

- **NDVGetN/SetN**: IsDetachedBuffer after ToIndex (get) / after value convert (set) — ES order
- **ARR_VALUES/KEYS/ENTRIES**: ValidateTypedArray when `this` is TypedArray
- **TypedArray(buffer, offset, length)**: ToIndex(offset)+ToIndex(length) then IsDetached

## Ladder

```
e7ds 1770 → e7dt 1813 (62.1%)
```
