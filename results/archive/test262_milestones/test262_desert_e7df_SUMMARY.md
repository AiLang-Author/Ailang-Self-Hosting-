# M128e7df — object-arg: Function + GetMethod(@@iterator)

**Desert tip:** **1338 / 2931 (46.0%)**  
**vs e7de:** 1336 → **1338** (**+2**)  
**vs e7d0:** 566 → **1338** (**+772**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 28.6% |
| DataView | 29.1% |
| TypedArray | **48.7%** |
| TypedArrayConstructors | **58.6%** |

## Changes

1. **object-arg accepts Function** — ES Type(Object) includes functions (`var obj = function(){}` iterator tests).
2. **GetMethod(@@iterator)** — GetProperty; null/undefined → array-like; present non-callable → TypeError; callable → iterate.
3. **JSVM_IterableToArray** — accept FUNCTION type as iterable source.

## Note

Tried ES-strict `ToBigInt(Number) → TypeError` but it regressed desert ~−40 (many BigInt TA paths still feed numbers). Deferred; keep NumberToBigInt in ToBigInt for now.

## Next

- ES ToBigInt Number TypeError with TA element source hygiene  
- buffer-arg SAB/detach  
- set same-buffer / species  

## Ladder

```
e7dd 1324 → e7de 1336 → e7df 1338 (46.0%)
```
