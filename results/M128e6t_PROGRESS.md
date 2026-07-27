# M128e6t progress — global PutValue attrs, Math constants, WhiteSpace

**Date:** 2026-07-27  
**Branch:** `master`  
**Tip:** M128e6t (after e6s SetFunctionName)

---

## This commit

### Engine

| Area | Change |
|------|--------|
| `JSVM__MirrorGlobalProp` | New global from PutValue → attr bits **7** (W\|E\|C). Var D=false still `SET_GLOBAL_VAR`. |
| `JSBridge__GetAttrBits` | Stop treating **all** `__*` names as internal. Only engine mangled prefixes (`__a_`, `__get_`, `__set_`, `__proto__`, …). Fixes test262 `11.13.1-4-1` (`__ES3_1_…`). |
| `JSBridge__CreateMathObj` | Math constants `{W,E,C}=false` via `SetAttrBits(…, 0)`. |
| `JSLex__IsWSHere` / `SkipWS` | Full ES WhiteSpace + LineTerminator UTF-8 (ASCII + NBSP + USP + ZWNBSP + LS/PS). |
| Tokenize loop | Always `SkipWS` + re-peek (was ASCII-only gate). |
| `IsIdentStart` / `IsIdentCont` / `ScanIdent` | Do not swallow WhiteSpace UTF-8 as IdentPart (`var x\u00a0= 2`). |

### Measured

| Suite | Score | Notes |
|-------|------:|-------|
| `11.13.1-4-1` | **pass** | was fail (attrs on `__ES3_…`) |
| `S8.12.4_A1` | pass | held |
| Math.E prop-desc / value | **pass** | constants bits 0 |
| white-space | **42/67 (62.7%)** | `between-nbsp` fixed |
| assignment | **420/485 (86.6%)** | +attrs path |
| compound-assignment | **397/454 (87.4%)** | |
| with | **133/181 (73.5%)** | held |

**Residual white-space (25):** all `after-regular-expression-literal-*` — harness-concat div-vs-regex context (even ASCII SP fails). Not pure WS.

### Goal status (language ≥95%)

Unchanged full-suite baseline until next language rescore: ~82.7% @ e6c; G2 still ~+2.9k.

---

## Next

1. Assignment residual (A6 free-var, private compound, putvalue-strict, …)
2. Class residual
3. after-regex-literal only if div_table/ASI fix is cheap
4. Full language rescore when cluster wins accumulate
