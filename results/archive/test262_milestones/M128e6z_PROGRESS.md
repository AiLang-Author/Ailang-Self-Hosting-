# M128e6z progress — dstr cover SetFunctionName + free-var bare `var`

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `JSComp__IsAnonFuncDef` | Unwrap `PAREN_EXPR` for IsAnonymousFunctionDefinition |
| Array/obj dstr defaults | Use IsAnonFuncDef — `(function(){})` named, `(0,fn)` not |
| `JSVM__EnvLookup` | Return **0** when not found (not `undef_val`) |
| `GET_FREE` | Only throw RE when lookup miss (0); found-undefined OK |

### Measured

| Suite | Score |
|-------|------:|
| **assignment/dstr** | **368/368 (100%)** |
| cover fn-name ×3 | pass |
| obj-prop-name-evaluation-error | pass |
| A6 / obj-rest-order | held |

### Notes

Bare `var a` free-var reads failed because EnvLookup returned `undef_val` for both miss and found-undefined; GET_FREE then required HasGlobal (missing under EvalString).
