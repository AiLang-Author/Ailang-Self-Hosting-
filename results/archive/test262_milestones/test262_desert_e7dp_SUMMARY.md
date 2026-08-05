# M128e7dp — IsConstructor methods + toLocaleString name + fill ToRelativeIndex

**Desert tip:** **1617 / 2931 (55.5%)**  
**vs e7do:** 1609 → **1617** (**+8**)  
**vs e7d0:** 566 → **1617** (**+1051**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **29.1%** |
| DataView | **67.9%** |
| TypedArray | **52.0%** |
| TypedArrayConstructors | **59.8%** |

## Changes

- **`JSVM__IsConstructor`**: reject MethodDefinition (fdesc+88==4) and generators — unlocks `TypedArray.from/of` called on methods
- **`toLocaleString`**: distinct native with correct `.name` (was alias of `toString`)
- **`fill`**: start/end via `JSVM_ToRelativeIndex`

## Ladder

```
e7do 1609 → e7dp 1617 (55.5%)
```
