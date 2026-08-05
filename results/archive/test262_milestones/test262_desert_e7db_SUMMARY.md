# M128e7db — buffer-arg ctor: NewTarget + ToIndex + Reflect.construct

**Desert tip:** **1297 / 2931 (44.5%)**  
**vs e7da:** 1282 → **1297** (**+15**)  
**vs e7d0:** 566 → **1297** (**+731**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **27.6%** |
| DataView | 31.2% |
| TypedArray | 47.8% |
| TypedArrayConstructors | **52.7%** |

## Changes

1. **NewTarget check** — `GetType(nt) == FUNCTION` only (bare `TA(buffer)` no longer slips through residual/non-eq undef boxes).
2. **ToIndex(byteOffset/length)** — ToInteger first, then reject true negatives; NaN → 0 (fixes `-0.1` / valueOf paths).
3. **Reflect.construct polyfill** — always `new target(...)` then `setPrototypeOf` for custom newTarget (old apply path cleared engine `__new_target__` and broke natives).

## Next

- more buffer-arg / object-arg / length-arg residual  
- set / detach  
- full-suite rescore  

## Ladder

```
e7d0 566 → e7da 1282 → e7db 1297 (44.5%)
```
