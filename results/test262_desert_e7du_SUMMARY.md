# M128e7du — TA internals detach web-reality + DV ctor

**Desert tip:** **1876 / 2931 (64.3%)**  
**vs e7dt:** 1813 → **1876** (**+63**)  
**vs e7d0:** 566 → **1876** (**+1310**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **34.2%** |
| DataView | **81.8%** (was 81.6%) |
| TypedArray | **59.9%** (was 57.8%) |
| TypedArrayConstructors | **67.6%** (was 63.2%) |

## Changes

- **IntegerIndexedElementGet/Set**: detached → `undefined` / convert-then-no-op (no TypeError)
- **IsValidIntegerIndex**: detached → false
- **HasProperty / Delete / GetOwnProperty / DefineOwnProperty**: detach + canonical numeric keys
- **GET_ELEM/SET_ELEM**: JS string indexes via `ParseCanonicalIndex` + non-integer numeric keys
- **DataView ctor**: IsDetachedBuffer after ToIndex(offset) (+ NewTarget proto)
- **OwnPropertyKeys**: empty integer indexes when detached (for-in)

## Ladder

```
e7dt 1813 → e7du 1876 (64.3%)
```
