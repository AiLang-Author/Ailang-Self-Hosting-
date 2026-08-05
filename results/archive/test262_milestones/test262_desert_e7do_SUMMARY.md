# M128e7do — ToRelativeIndex (±Inf) + @@species getter

**Desert tip:** **1609 / 2931 (55.2%)**  
**vs e7dn:** 1606 → **1609** (**+3**)  
**vs e7d0:** 566 → **1609** (**+1043**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **29.1%** |
| DataView | **67.9%** |
| TypedArray | **51.7%** |
| TypedArrayConstructors | **59.1%** |

## Changes

- **`JSVM_ToRelativeIndex`**: ToIntegerOrInfinity + clamp; ±∞ and `undefined` handled
- **slice / subarray**: use ToRelativeIndex (unlocks `infinity`, `tointeger-*`)
- **indexOf / lastIndexOf**: +∞/−∞ fromIndex per ES
- **copyWithin**: target/start/end via ToRelativeIndex
- **`%TypedArray%[@@species]`** accessor getter returns `this` (was data prop on each ctor)

## Ladder

```
e7dn 1606 → e7do 1609 (55.2%)
```
