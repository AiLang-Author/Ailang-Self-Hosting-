# M128e6ag progress — with free-var + for-in slot collision

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| GET_WITH miss | Free-var / cenv / EnvLookup before global (12.10-0-9 outer `x`) |
| CompileFunc | Clear `with_depth` — nested functions use free-var, not GET_WITH |
| for-in `var` LHS | `AddVarLocal` (function-scoped), not block `AddLocal` |
| AddVarLocal | Unique `abs_slot` across all scopes (was root `lc` only → collided) |

### Measured

| Suite | Score |
|-------|------:|
| **statements/with** | **155/181 (85.6%)** — was 144/181, **+11**; vs 135 start **+20** |

### Classic cluster wins

A1.5_T1, A1.7_T1/2/4, A1.8_T1/2/4, A1.9_*, A1.12_T1/2/4, 12.10-0-9

### Residual (~26)

| Cluster | Notes |
|---------|--------|
| A1.5_T2–T5, A1.4_T4/5, A1.7_T3/5, A1.8_T5, A1.11_T3/5, A1.12_T3/5, A3.4/5 | Abrupt completion / return / throw variants |
| Proxy set-mutable | Reflect + gOPD/defineProperty |
| unscopables-*-err, binding-deleted unscopables | Free-var throw value |
| typed-array proto | |

3 tests fail in batch but pass single harness (has-property-err, unscopables-deleted-*) — possible batch ordering; not blocking.

### Next

Abrupt S12.10 T3/T5; Reflect/Proxy define; unscopables throw value.
