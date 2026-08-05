# M128e6ah progress — with classic abrupt + var hoist + WITH_POP

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `HoistFuncVars` | Pre-register function `var` locals so `return value; var value` is local undefined, not with free-var |
| `EmitPendingWithPop` | break/continue/return emit WITH_POP for withs entered inside loop |
| `next_abs_slot` | Monotonic local slots (no reuse after PopScope); catch no longer clobbers for-in body vars |
| Program locals | Headroom +256 for for-in/catch temps |

### Measured

| Suite | Score |
|-------|------:|
| **statements/with** | **171/181 (94.5%)** — was 155/181, **+16**; vs 135 start **+36** |

### Classic S12.10

Nearly all A1.4/5/7/8/9/11/12 and A3.4/5 variants green (break/throw/return).

### Residual (~10)

| Tests | Notes |
|-------|--------|
| Proxy set-mutable (2) | Reflect + getOwnPropertyDescriptor/defineProperty |
| typed-array proto set (2) | |
| unscopables err / binding-deleted (4) | Pass single-harness; batch may leak state |
| has-property-err, cptn-abrupt-empty | Pass single-harness; batch-only red |

### Next

1. Batch harness isolation for Proxy/unscopables  
2. Minimal Reflect + Proxy define traps  
3. TypedArray proto SetMutableBinding  
