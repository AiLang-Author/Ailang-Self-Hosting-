# M128e6x progress — obj-rest computed exclude + `1.` NumericLiteral

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `CompileObjPattern` rest | Delete **computed** prior keys from rest (re-eval key expr) |
| `JSLex__ScanNumber` | `1.` is valid DecimalLiteral (consume `.` even without fraction) |

### Measured

| Suite | Result |
|-------|--------|
| `obj-rest-computed-property*` | **pass** |
| `obj-rest-non-string-computed-*` | **pass** (needs `1.` lex) |
| obj-rest overall | **~25/26** (order residual) |
| `obj-rest-order` | fail — OwnPropertyKeys integer-index sort |

A6 / 8.14.4 / cover held.

### Next

`JSRT_ObjKeys` / OBJ_SPREAD: integer-index keys ascending before other strings (OwnPropertyKeys); symbol enumerable own for rest getters.
