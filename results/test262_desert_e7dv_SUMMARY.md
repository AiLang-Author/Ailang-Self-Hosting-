# M128e7dv — fill/copyWithin/slice detach + AB species

**Desert tip:** **1901 / 2931 (65.1%)**  
**vs e7du:** 1876 → **1901** (**+25**)  
**vs e7d0:** 566 → **1901** (**+1335**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **40.3%** (was 34.2%) |
| DataView | **81.8%** |
| TypedArray | **60.8%** (was 59.9%) |
| TypedArrayConstructors | **67.5%** |

## Changes

- **fill / copyWithin**: after coercion, detached TA → TypeError
- **slice (TA)**: count>0 + detached source → TypeError
- **ArrayBuffer[@@species]** getter → this
- **ArrayBuffer.prototype.slice**: SpeciesConstructor + Construct + same/size checks
- **indexOf/lastIndexOf**: detached during fromIndex → -1 (without breaking every/forEach iteration)

## Ladder

```
e7du 1876 → e7dv 1901 (65.1%)
```
