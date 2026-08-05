# M128e6ad progress — compound A6 (eval_var_env + RESOLVE_FREE)

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `GET_FREE` | Probe `eval_var_env` **before** free-var `__cenv` (eval `var` shadows free-var) |
| Compound IDENT `op=` | Emit `RESOLVE_FREE` before GetValue/RHS (A6 PutValue Reference) |

### Measured

| Suite | Score |
|-------|------:|
| **compound-assignment** | **430/454 (96.4%)** — was 408/454 (91.5%), **+22** |
| A6 `x *= (eval("var x=2"), 4)` | **pass** |
| assignment (prior e6ac) | held 0 fails |

### Residual compound (~16 fails + timeouts)

Likely A7 strict-order edge cases / other PutValue paths.

### Next

Remaining compound A7*; operators; expand Proxy get trap if needed.
