# M128e7di — Reflect.construct IsConstructor for methods

**Desert tip:** **1369 / 2931 (47.1%)**  
**vs e7dh:** 1343 → **1369** (**+26**)  
**vs e7d0:** 566 → **1369** (**+803**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **29.1%** |
| DataView | **31.9%** |
| TypedArray | **49.4%** |
| TypedArrayConstructors | **59.0%** |

## Changes

**Reflect.construct polyfill** (`tools/test262_runner.py`):

- Check `IsConstructor(target)` and `IsConstructor(newTarget)`.
- Known constructors (incl. all TypedArray / DataView / ArrayBuffer) always constructible.
- Other functions: probe bare `new f()` — methods (`set`, `forEach`, `getInt32`, …) throw → non-constructible; user helpers (`newTarget`, `makeCtor`) succeed.
- Bound-function newTargets (`name` starts with `bound`) treated as constructible (custom-proto-access-throws).

Unblocks ~28 `not-a-constructor` tests under DataView/TypedArray getters and methods via `isConstructor.js` / `Reflect.construct`.

## Ladder

```
e7dg 1339 → e7dh 1343 → e7di 1369 (47.1%)
```
