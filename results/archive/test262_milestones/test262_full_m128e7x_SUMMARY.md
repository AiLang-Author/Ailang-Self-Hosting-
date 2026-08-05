# Full test262 regression — M128e7x (2026-07-31)

**Tip:** `a7cefc59` — JS M128e7x: static length() override; class body compile strict  
**Harness:** test262_harness_batch.x  
**Command:**
```bash
python3 tools/test262_runner.py --full --timeout 12 -j 8 \
  --output-json results/test262_full_m128e7x.json
```
**Wall time:** 2914.3s (~**48.6 min**)  
**JSON:** `results/test262_full_m128e7x.json`

---

## Headline

| Metric | Value |
|--------|------:|
| Tests discovered | **49,723** |
| **Pass** | **30,505** |
| Fail | 18,376 |
| Error | 694 |
| Timeout | 148 |
| **Overall pass rate** | **61.35%** (pass/total) |

### vs prior baselines

| Baseline | Overall | Language | Built-ins | Notes |
|----------|--------:|---------:|----------:|-------|
| **M128e7l** | 60.56% | 90.11% | 33.88% | stale gap +1,156 |
| **M128e7x (this run)** | **61.35%** | **91.42%** | **33.86%** | tip a7cefc59 |

---

## Language → G2 (95%)

| | e7l | **e7x** | Δ |
|--|----:|--------:|--:|
| Language pass | 21,298 | **21,607** | +309 |
| Language total | 23,635 | **23,635** | +0 |
| Pass% | 90.11% | **91.42%** | +1.31 pp |
| G2 need (ceil 95%) | 22,454 | **22,454** | |
| **G2 gap** | +1,156 | **+847** | -309 |

**G2 formula:** `ceil(0.95 × language_total) − language_pass`  
At e7x: `ceil(0.95 × 23635) − 21607 = 22454 − 21607 = **847**`

---

## By section

| Section | Pass | Fail | Error | T/O | Total | Pass% |
|---------|-----:|-----:|------:|----:|------:|------:|
| language | 21,607 | 1,460 | 517 | 51 | 23,635 | 91.42% |
| built-ins | 7,963 | 15,333 | 138 | 84 | 23,518 | 33.86% |
| staging | 392 | 1,042 | 38 | 12 | 1,484 | 26.42% |
| annexB | 543 | 541 | 1 | 1 | 1,086 | 50.0% |

---

## Files
- JSON: `results/test262_full_m128e7x.json`
- Stats: `results/test262_full_m128e7x_STATS.json`
- Log: `results/test262_full_m128e7x.log`
