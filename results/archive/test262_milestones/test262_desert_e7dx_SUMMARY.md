# M128e7dx — TA values/keys/entries brand + iterator + join sep

**Desert tip:** **1938 / 2931 (66.4%)**  
**vs e7dw:** 1920 → **1938** (**+18**)  
**vs e7d0:** 566 → **1938** (**+1372**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **40.3%** |
| DataView | **81.8%** |
| TypedArray | **63.3%** (was 62.1%) |
| TypedArrayConstructors | **67.6%** |

## Changes

- **CALL + CallFunc**: ValidateTypedArray for `__ta_meth__` natives that go via Bridge (values/keys/entries)
- **ARR_ITER_NEXT**: TypedArray path uses TA_Length / TA_Get
- **join**: ToString(separator) before empty-length early return

## Ladder

```
e7dw 1920 → e7dx 1938 (66.4%)
```
