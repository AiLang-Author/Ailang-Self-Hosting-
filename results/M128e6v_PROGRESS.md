# M128e6v progress — PutValue Reference (A5/A6 + free-var)

**Date:** 2026-07-28  
**Branch:** `master`  
**Tip:** after e6u IdentifierName

---

## This commit

### Engine

| Area | Change |
|------|--------|
| `GET_WITH` resolve-only miss | `WithRef.valid=2` (outer/declarative) — A6 T3 |
| `SET_WITH` | valid=2 skips live with; valid=1 + !stillExists + strict → RE (putvalue-lref) |
| `RESOLVE_FREE` (op 125) | Capture free-var env on `__cenv` before RHS (skip own) |
| `SET_FREE` | Prefer `FreeRef` over eval-introduced own binding |
| `SetDynOrGlobal` | If FreeRef valid for name, do not clobber frame-env eval local |

### Measured

| Suite | Score | Notes |
|-------|------:|-------|
| **assignment** | **430/485 (95.6%)** | was 426 @ e6u |
| A5 T1–T3 | pass | held |
| A6 T1–T3 | **pass** | was fail |
| putvalue-lref (strict delete) | **pass** | was fail |
| with | hold check | |

### Residual assignment (~55)

dstr nested/yield/iterator-close, fn-name cover, private/rest, 11.13.1-4-14-s, …

---

## Goal

Language ≥95% still open on full suite (~+2.9k from e6c). Assignment slice now **95.6%**.
