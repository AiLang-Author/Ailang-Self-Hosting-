# M128e7dr — ArrayBuffer detach + ValidateTypedArray detached

**Desert tip:** **1754 / 2931 (60.2%)**  
**vs e7dq:** 1617 → **1754** (**+137**)  
**vs e7d0:** 566 → **1754** (**+1188**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **29.6%** |
| DataView | **76.1%** (was 67.9%) |
| TypedArray | **57.1%** (was 52.0%) |
| TypedArrayConstructors | **62.2%** |

## Changes

- **`JSVM_AB_Detach` / `IsDetachedBuffer`**: mark buffer, clear data, byteLength → 0
- **`$262.detachArrayBuffer`**: native host hook for test262 (`$DETACHBUFFER`)
- **`ValidateTypedArray`**: TypeError when buffer is detached (all MarkTAMethod paths)
- **DataView** get/set + byteLength/byteOffset: detach TypeError
- **TA element** get/set: detach TypeError
- **TA length/byteLength/byteOffset** getters: detached → **0** (not throw)

## Ladder

```
e7dp 1617 → e7dr 1754 (60.2%)   +137
e7d0 566  → e7dr 1754           +1188
```
