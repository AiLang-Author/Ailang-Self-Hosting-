# M128e6ak progress — with 99.4% (cptn-abrupt-empty)

**Date:** 2026-07-29  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| Loop completion V | Dual-write durable global `__cptn` on EXPR / with-reset / do-while seed |
| Break/continue/do-exit | `GET_GLOBAL_SOFT("__cptn")` for eval completion (survives stack clobber) |
| with + loop_cptn | Enable `cptn_prop` when `loop_cptn_slot` live so body updates V |
| Eval SP | Reserve absolute locals before expr stack (`JSComp_GetLocalSlotCount`) |

### Root cause (cptn-abrupt-empty)

`do { with({}) { 3; break; } }` stored completion in absolute stack locals that the
expression stack (starting at SP=0) clobbered. Empty break looked fine (undef
singleton), non-empty values became garbage/undefined.

### Measured (`--no-batch`)

| Suite | Score |
|-------|------:|
| **statements/with** | **180/181 (99.4%)** — was 179/181 |

### Residual (1)

| Test | Notes |
|------|--------|
| `set-mutable-binding-binding-deleted-with-typed-array-in-proto-chain.js` | VM error on Int32Array polyfill + Object.create + delete/set NaN |

### Carry forward

1. TypedArray ObjectEnv deleted-binding sloppy (polyfill/Set path)  
2. G2 language ≥95% overall  
