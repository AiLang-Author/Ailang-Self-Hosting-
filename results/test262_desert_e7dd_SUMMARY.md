# M128e7dd — compiler: const_map save/restore per function

**Desert tip:** **1324 / 2931 (45.5%)**  
**vs e7dc:** 1307 → **1324** (**+17**)  
**vs e7d0:** 566 → **1324** (**+758**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 28.6% |
| DataView | 29.1% |
| TypedArray | **48.5%** |
| TypedArrayConstructors | **57.0%** |

## Root cause

Named function expressions mark their immutable name slot with `const_map[slot]=2`.  
`tdz_map` was saved/cleared/restored per function compile; **`const_map` was not**.

After harness helpers like:

```js
makeIterable = function makeIterable(TA, primitiveOrIterable) { ... }
```

any later `(function(a,b){ var sample; sample = ... })` reused absolute slot 2 for the first body local. `EmitVarSet` treated it as the named-FE name → **sloppy silent no-op** on assignment. Classic test262 pattern `var sample; sample = new TA(...)` failed under `testTypedArray.js`.

## Fix

In `JSComp__CompileFunction` (Library.JSCompStmt.ailang): save/clear/restore `const_map` alongside `tdz_map` (including error-path restore).

## Next

- residual set / object-arg / detach  
- full-suite rescore (const_map leak affects far beyond desert)  
- buffer-arg SAB  

## Ladder

```
e7d0 566 → e7da 1282 → e7db 1297 → e7dc 1307 → e7dd 1324 (45.5%)
```
