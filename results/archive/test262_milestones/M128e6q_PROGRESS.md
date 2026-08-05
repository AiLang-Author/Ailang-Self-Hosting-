# M128e6q progress — with @@unscopables + eval completion

**Date:** 2026-07-27  
**Branch:** `gpu-45-may-baseline-restore`  
**Tip commits:** e6p for-await 100% → **e6q** with HasBinding / cptn  
**JSON:** `results/test262_with_m128e6q2.json`, `results/test262_forawait_m128e6q.json`,  
`results/test262_language_m128e6q.json`, `results/test262_dynimport_m128e6p.json`

---

## Goal status: language ≥95% test262 (full JS VM)

| Gate | Criterion | Latest measured | Status |
|------|-----------|-----------------|--------|
| **G0** | Full suite (all sections) | **27 650 / 49 723 (55.6%)** @ e6c | tracking only |
| **G1** | language ≥ **90%** (~21 272 / 23 635) | **~82.7%** full language @ e6c (~19 552) | **not met** — ~+1.7k passes |
| **G2** | language ≥ **95%** (~22 454 / 23 635) | same baseline | **not met** — ~**+2 900** language passes from e6c |
| **G3** | Open built-ins bulk (Reflect/Proxy/…) | blocked on G2 | **blocked** |

### Distance math (section totals from full suite M128e6c)

| Metric | Value |
|--------|------:|
| Full language total | 23 635 |
| Pass @ e6c full suite | 19 552 (**82.7%**) |
| Passes needed for 90% | 21 272 → **+1 720** |
| Passes needed for 95% | 22 454 → **+2 902** |
| Full suite overall | 55.6% (built-ins still ~31%) |

**DEFAULT_CATEGORIES slice** (subset of language, post-e6q harness):  
**6 532 / 7 689 (85.0%)** — useful grind signal, **not** the G2 denominator.

### Goal narrative

We are **~12 pp short of language 95%** on the full language tree (82.7% → 95%).  
High-leverage work already closed or near-closed:

| Slice | Score | Role for 95% |
|-------|------:|--------------|
| **for-await-of** | **1234/1234 (100%)** | L5 done |
| **dynamic-import** | **926/941 (98.4%)** | L2 done (was bottleneck) |
| **eval-code** | **339/347 (97.7%)** | L3 done |
| **with** | **132/181 (72.9%)** | L6 in progress (+6 this commit) |
| **class (stmt)** | **3976/4367 (~91%)** | L4 residual (~390 fails) |
| assignment / compound | large DEFAULT residual | L7 next |

**Estimated path to G2:** finish with residual where cheap → class/elements residual → assignment/PutValue → operator/hygiene long tail → full language rescore.  
**Do not** divert to Temporal / TypedArray bulk until G2.

---

## This commit (M128e6q)

### Engine

| Area | Change |
|------|--------|
| `JSVM__ObjGetAcc` | OrdinaryGet with `__get_*` accessors; leaves `exc_prop` for dispatch |
| GET_WITH / SET_WITH | `@@unscopables` Get invokes getters; rethrow at dispatch only |
| Get/SetMutableBinding | re-HasProperty after unscopables (delete-in-get + strict RE) |
| UPDATE_EXPR IDENT | single Get for `++`/`--` (unscopables once) |
| `cptn_prop` + CompileBlock | with body eval completion → `cptn-nrml` |

### Measured deltas

| Suite | Before | After |
|-------|-------:|------:|
| statements/with | 126/181 (69.6%) e6p | **132/181 (72.9%)** e6q2 |
| for-await-of | 100% e6p | **100%** held |
| dynimport | 926/941 (98.4%) e6p | held (not rescore this tip) |

**With +6 fixed (0 regressions vs e6p):**  
unscopables-inc-dec, get/set-mutable-binding-deleted-in-get-unscopables (×4), cptn-nrml.

**Isolation pass / batch flaky:** unscopables-get-err, unscopables-prop-get-err  
**Still ~49 with fails:** Proxy env, has-property-err, S12.10 clusters, scope-var, cptn-abrupt, TypedArray proto.

---

## Next grind (dependency order)

1. **L7** assignment / compound-assignment residual (DEFAULT: 75 + 67 fails)  
2. **L4** class residual rescore + elements  
3. **L6** with residual only where high leverage (avoid Proxy bulk)  
4. Full **language** rescore → update G1/G2 distance  
5. Built-ins **after** language ≥95%

### Rebuild harness after pull

```bash
./ailang.x JS-tests/test262_harness_batch.ailang -o test262_harness_batch.x
./ailang.x JS-tests/test262_harness.ailang -o test262_harness.x
python3 tools/test262_runner.py --categories statements/with --timeout 12
```
