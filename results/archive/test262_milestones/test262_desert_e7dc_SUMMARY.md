# M128e7dc — Reflect.construct custom-proto + buffer length modulo

**Desert tip:** **1307 / 2931 (44.8%)**  
**vs e7db:** 1297 → **1307** (**+10**)  
**vs e7d0:** 566 → **1307** (**+741**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **28.6%** |
| DataView | 29.1% |
| TypedArray | 47.2% |
| TypedArrayConstructors | **56.7%** |

## Changes

1. **Reflect.construct isCtor heuristic** — only all-lowercase names count as non-ctor builtins (`map`/`keys`/…); camelCase `newTarget`/`makeCtor` no longer misclassified.
2. **GetPrototypeFromConstructor** — if `newTarget.prototype` is non-object/null, keep default proto from `new target(...)` (do not force `Object.prototype`).
3. **buffer-arg length undefined** — omitted *or* explicit `undefined` length still requires `rem % elementSize == 0`.

## Next

- residual buffer-arg (detach, SAB, defined-*)
- object-arg / set
- full-suite rescore (post e7d7–e7dc)

## Ladder

```
e7d0 566 → e7da 1282 → e7db 1297 → e7dc 1307 (44.8%)
```
