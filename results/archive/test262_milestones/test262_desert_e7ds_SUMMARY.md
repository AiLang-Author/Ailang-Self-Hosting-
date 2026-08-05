# M128e7ds — detach edges: AB.detached, set/subarray/ctor

**Desert tip:** **1770 / 2931 (60.8%)**  
**vs e7dr:** 1754 → **1770** (**+16**)  
**vs e7d0:** 566 → **1770** (**+1204**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **34.2%** (was 29.6%) |
| DataView | **76.1%** |
| TypedArray | **57.3%** |
| TypedArrayConstructors | **62.8%** |

## Changes

- **`ArrayBuffer.prototype.detached`** getter
- **`TypedArray.prototype.set`**: IsDetachedBuffer after ToInteger(offset), before Get(src.length)
- **`subarray`**: detach TypeError after ToInteger(begin/end)
- **TypedArray(buffer)**: detach TypeError after ToIndex(byteOffset)

## Ladder

```
e7dr 1754 → e7ds 1770 (60.8%)
```
