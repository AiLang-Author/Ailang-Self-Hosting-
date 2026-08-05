# M128e6af progress — with multi-var body + eval do-while completion

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `CompileStmtBody` | Multi-var chain under single-stmt `with`/`if`/`while`/`for` (unbraced `with (o) var a=1, b=2`) |
| do-while eval completion | Loop V slot when last stmt; break loads V (UpdateEmpty); with resets V on push |
| scope-var-open/close | Fixed via multi-var under with |

### Measured

| Suite | Score |
|-------|------:|
| **statements/with** | **144/181 (79.6%)** — was 141/181 (e6ae), **+3**; vs 135 start **+9** |

### New passes

- `scope-var-open.js`, `scope-var-close.js`
- `cptn-abrupt-empty.js`

### Residual (~37)

Classic S12.10 for-in/with clusters; Proxy set-mutable (Reflect + gOPD/defineProperty); unscopables accessor throw value; typed-array proto.

### Next

1. Minimal `Reflect` + Proxy `getOwnPropertyDescriptor`/`defineProperty`  
2. unscopables free-var throw value  
3. Classic S12.10 A1.5/7/8/9  
