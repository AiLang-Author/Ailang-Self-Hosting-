# M128e6ab progress — for-of nest compile + gen rtrn-close

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `CompileFunc` | Save/clear/restore `loop_depth`, `finally_depth`, `iter_depth`, `label_depth` so nested funcs inside for-of do not inherit outer stacks |
| for-of `var` | `EmitVarSet` dual-write (local + FRAME_ENV/global) for free-var closure |
| `GenTrackOpenIter` | Track when `active_gs` set; promote rec to **gval_pool** (survives ReclaimScope after yield) |
| `GenReturn` | If open iter was closed, skip force_return resume into dstr/for-of try (dead irec locals) |

### Measured

| Suite | Score |
|-------|------:|
| **expressions/assignment** | **449/485 (99.8%)** |
| non-callable return under for-of + assert.throws | **pass** |
| array-elem/rest/trlg **rtrn-close** ×4 | **pass** |
| for-of var closure | **pass** |
| finally on gen.return | **held** |

### Residual (1)

- `keyed-destructuring-…-with-bindings` — with/Proxy `has` evaluation order

### Next

with free-var ResolveBinding order for keyed dstr targets under `with`.
