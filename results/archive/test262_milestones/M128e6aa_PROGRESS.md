# M128e6aa progress — keyed dstr order + IteratorClose throw restore

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `CompileObjPattern` PROPERTY | Spec order: PropertyName (ToPropertyKey) → member lref → GetV → default → PutValue |
| Bare assign SetFunctionName | `IsAnonFuncDef` on RHS (cover = (function(){}) names) |
| `ITER_CLOSE` GetMethod | Isolate `exc_sp` so return-getter throw does not land in outer `assert.throws` |
| `ITER_CLOSE` early exits | Re-seat `save_throw_v` for kind=1 (already-closed / array mode / done) |
| Array dstr catch | Leave original under irec for kind=1 (DUP before SET_LOCAL); unique temps `__di__`/`__dx__` vs for-of `__ir__` |

### Measured

| Suite | Score |
|-------|------:|
| **expressions/assignment** | **443/485 (98.4%)** |
| keyed-destructuring evaluation order | **pass** |
| default-expr-throws-iterator-return-get-throws | **pass** |
| fn-name-cover | **pass** |
| assignment/dstr (prior 368/368) | held |

### Residual assignment fails (7)

- `default-expr-throws-iterator-return-is-not-callable` — for-of + nested `assert.throws` try vs dstr ITER_CLOSE
- `keyed-…-with-bindings` — with/Proxy has order
- `target-assign-throws-iterator-return-is-not-callable`
- 4× `dstr/*-rtrn-close*` — return-completion IteratorClose

### Next

for-of body try vs CallFunc nested try (exception lands on for-of not assert.throws); with free-var has traps; rtrn-close.
