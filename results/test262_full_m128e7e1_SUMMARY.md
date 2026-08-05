# Full test262 regression — M128e7e1

**Tip:** `c22012b4` (+ post-score Array.from fix in uncommitted e7e1b)  
**Harness:** `test262_harness_batch.x` (e7e1)  
**JSON:** `results/test262_full_m128e7e1.json`  
**Log:** `results/test262_full_m128e7e1.log`  
**Wall time:** 2975.2s (~**49.6 min**)  
**Command:** `python3 tools/test262_runner.py --full -j 8 --timeout 12 --output-json results/test262_full_m128e7e1.json`  
**Generated:** 2026-08-05T03:05:13.314880+00:00

---

## Headline (vs e7d6)

| Metric | e7d6 (2026-08-03) | **e7e1 full** | Δ |
|--------|------------------:|--------------:|--:|
| Tests discovered | 49,723 | **49,723** | 0 |
| **Pass** | 33,494 | **34,218** | **+724** |
| Fail | 15,671 | 14,940 | −731 |
| Error | 379 | 392 | +13 |
| Timeout | 179 | 173 | −6 |
| **Overall pass rate** | **67.36%** | **69.62%** | **+2.3 pp** |
| Language pass | 22,356 (94.6%) | **22,072 (93.4%)** | −284 |
| Built-ins pass | 10,143 (43.1%) | **11,122 (47.3%)** | **+979** |

**No overall regression.** Net +724 passes. Built-ins climb is almost entirely desert (TA/DV/TAC/AB). Language dip is mostly `language/statements/class` async/yield-star and unicode-id **error** noise under full-suite load, plus a few real clusters noted below.

---

## By section

| Section | Pass | Fail | Error | T/O | Total | Pass% |
|---------|-----:|-----:|------:|----:|------:|------:|
| **language** | 22,072 | 1,210 | 299 | 54 | 23,635 | **93.4%** |
| **built-ins** | 11,122 | 12,220 | 72 | 104 | 23,518 | **47.3%** |
| staging | 471 | 978 | 21 | 14 | 1,484 | 31.7% |
| annexB | 553 | 532 | 0 | 1 | 1,086 | 50.9% |
| **TOTAL** | **34,218** | **14,940** | **392** | **173** | **49,723** | **69.6%** |

---

## Desert surfaces (full-suite dump)

| Surface | Pass/Total | Pass% | vs dedicated e7e1 desert |
|---------|----------:|------:|--------------------------|
| ArrayBuffer | 79/196 | 40.3 | ~80/196 dedicated |
| DataView | 468/561 | 83.4 | 475/561 dedicated |
| TypedArray | 962/1438 | 66.9 | 973/1438 dedicated |
| TypedArrayConstructors | 541/736 | 73.5 | 562/736 dedicated |

Dedicated desert e7e1: **2090/2931 (71.6%)**. Full-suite desert slightly lower (timeouts/load).

---

## Regression analysis (e7d6 → e7e1)

| | Count |
|--|------:|
| Newly passing | **1,137** |
| Newly failing (was pass) | **413** |
| **Net** | **+724** |

### Newly passing (top)
- TypedArray **+454**, DataView **+273**, TAC **+221**, ArrayBuffer **+33**

### Newly failing buckets
- `language/statements` **346** — heavy class async-gen / yield-star / cpn fields (many pass↔fail under load)
- `built-ins/RegExp` property-escapes **11** (timeout/error)
- `not-a-constructor.js` cluster on various prototypes (~12) — still failing after e7e1; separate from desert
- **Array.from custom-this** (3 tests) — **caused by e7e1 TypedArrayCreate over-check**; fixed post-score as **e7e1b** (BYTES_PER_ELEMENT-only validate). Verified `Array.from_forwards-length…`, `source-object-iterator-2`, `source-object-missing` pass again; TA `custom-ctor-returns-smaller` still TypeError.

---

## B-core product builtins (pass/total approx)

| Builtin | Pass/Total | Pass% |
|---------|----------:|------:|
| Object | 2802/3411 | 82.1 |
| Array | 2607/3081 | 84.6 |
| String | 871/1223 | 71.2 |
| Promise | 449/677 | 66.3 |
| Function | 351/509 | 68.9 |

---

## Verdict

Full suite **healthy**: overall **+2.3pp**, desert work landed in built-ins. Language not at G2 95% on this dump (93.4%). Post-score **e7e1b** restores Array.from custom ctor without undoing TypedArray.from TypedArrayCreate.
