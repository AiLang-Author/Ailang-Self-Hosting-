# Full test262 suite — M128e6ak baseline

**Date:** 2026-07-29  
**Harness:** `test262_harness_batch.x` (e6ak tip at suite start; e6al with-100% landed mid-run and does not affect this binary)  
**Command:**
```bash
python3 tools/test262_runner.py --full -j 8 --timeout 15 \
  --output-json results/test262_full_m128e6ak.json
```
**Wall time:** 3012.9s (~50.2 min)  
**JSON:** `results/test262_full_m128e6ak.json`  
**Log:** `results/test262_full_m128e6ak.log`

---

## Headline

| Metric | M127 (prior) | **M128e6ak** | Δ |
|--------|-------------:|-------------:|--:|
| Tests | 49,723 | **49,723** | — |
| Pass | 28,457 (57.2%) | **29,878 (60.1%)** | **+1,421 / +2.9pp** |
| Fail | 20,871 | 19,121 | −1,750 |
| Error | 317 | 603 | +286 |
| Timeout | 78 | 121 | +43 |

Runner Pass% column (pass / (pass+fail)): **~61.0%**.

---

## By section

| Section | Total | Pass | Pass% |
|---------|------:|-----:|------:|
| **language** | 23,635 | 21,070 | **89.1%** |
| built-ins | 23,518 | 7,956 | 33.8% |
| annexB | 1,086 | 481 | 44.3% |
| staging | 1,484 | 371 | 25.0% |
| **TOTAL** | **49,723** | **29,878** | **60.1%** |

Prior M127 language was **84.2%** → language **+4.9pp**.

---

## language highlights

| Sub | Total | Pass | Pass% |
|-----|------:|-----:|------:|
| expressions | 11,055 | 10,120 | 91.5% |
| statements | 9,359 | 8,203 | 87.6% |
| arguments-object | 263 | 248 | 94.3% |
| block-scope | 145 | 141 | 97.2% |
| module-code | 596 | 512 | 85.9% |
| eval-code | 816 | 627 | 76.8% |
| global-code | 195 | 83 | 42.6% |

**statements/with** in this full run: **179/181 (98.9%)** — e6al lands **181/181 (100%)** separately.

---

## Largest language fail clusters

| Fails | Folder |
|------:|--------|
| 753 | statements/class |
| 173 | expressions/class |
| 117 | eval-code/direct |
| 94 | statements/for-of |
| 72 | eval-code/indirect |
| 70 | literals/regexp |
| 40 | statements/using |
| 39 | expressions/yield |
| 38 | expressions/assignment |
| 38 | import/import-defer |

---

## Parallel landings this session

| Commit | notes |
|--------|--------|
| e6ak | with 180/181 — durable `__cptn` completion |
| **e6al** | **with 181/181 (100%)** — deleted Set + array proto |

---

## Carry forward (G2 language ≥95%)

1. **statements/class** + **expressions/class** (largest desert)  
2. eval-code direct/indirect  
3. for-of / for-in residuals  
4. built-ins bulk (TypedArray, Intl, Temporal, …) for overall ≥65%  
