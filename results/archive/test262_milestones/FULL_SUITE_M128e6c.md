# Full test262 suite — M128e6c

**Date:** 2026-07-27  
**Branch:** `gpu-45-may-baseline-restore`  
**Tip commits:** free-var dual-bind (e6) · class slot clobber (e6b) · GET_LOCAL dual-read (e6c)  
**Note:** Suite harness was **e6c** (pre GET_PROP_SUPER e6d).  
**JSON:** `results/test262_full_m128e6c.json`  
**Log:** `results/test262_full_m128e6c.log`

```bash
python3 tools/test262_runner.py --full -j 8 --timeout 15 \
  --output-json results/test262_full_m128e6c.json
```

**Wall time:** ~47.5 min (2848 s) · **Workers:** 8 · **Mode:** batch  
**Discovered:** 49 723 tests

---

## Headline

| Metric | M128e6c | M128ba | M127 | Δ e6c−m128ba | Δ e6c−m127 |
|--------|--------:|-------:|-----:|-------------:|-----------:|
| **Pass** | **27 650 (55.6%)** | 25 676 (51.6%) | 28 457 (57.2%) | **+1 974** | −807 |
| Fail | 21 848 | — | 20 871 | | |
| Timeout | 169 | — | 78 | | |
| Error | 56 | — | 317 | | |

## By section

| Section | Total | Pass | Pass% |
|---------|------:|-----:|------:|
| **language** | 23 635 | **19 552** | **82.7%** |
| built-ins | 23 518 | 7 418 | 31.5% |
| annexB | 1 086 | 419 | 38.6% |
| staging | 1 484 | 261 | 17.6% |
| **TOTAL** | **49 723** | **27 650** | **55.6%** |

M127 language was 84.2% (19 904) — language **−352** vs m127 peak.

---

## Regression watch

### vs M128ba (dirty class tip) — net **+3.97 pp**

| Direction | Count | Top families |
|-----------|------:|--------------|
| **Gains** | 3 557 | **class stmts +2 846**, with +106, compound-assign +66, super +51 |
| Regressions | 1 583 | class expr −310, eval direct −170, for-await −119, dynimp −115 |

Class recovery from M128ba collapse is the dominant story.

### vs M127 (best full baseline) — net **−1.62 pp**

| Direction | Count | Top families |
|-----------|------:|--------------|
| **Gains** | 1 752 | **dynimp +491**, Array proto +124, **with +106**, eval +71, class +66/+53 |
| Regressions | 2 559 | **class stmts −333**, **class expr −309**, **for-await −245**, annexB eval −120 |

---

## Slice gates at suite time (e6c harness)

| Gate | Score |
|------|------:|
| statements/class | 3670/4367 (**84.7%**) — was 68.7% pre dual-read; M128c peak 90.7% |
| expressions/super | 65/94 (69.1%); e6d GET_PROP_SUPER → **71.3%** |
| statements/with | 125/181 (**69.1%**) |

---

## Post-suite grind (same session, after score)

| Gate | At suite (e6c) | After e6d–e6f |
|------|---------------:|--------------:|
| statements/class | 84.7% | **91.3%** (3958/4367) |
| expressions/super | 69.1% | **74.5%** (70/94) |
| statements/with | 69.1% | 69.1% (125/181) |

**e6f fix:** init-path early `ReturnValue` skipped let/const TDZ clear → every top-level `let` read used THROW_TDZ.

### Next priorities
1. Re-full suite (expect language ≫ 82.7% with class restored).  
2. for-await-of residual (−245 vs m127).  
3. with residual / unscopables.  
4. Language toward 95%.
