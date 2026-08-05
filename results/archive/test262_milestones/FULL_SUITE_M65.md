# Full test262 suite — M65 baseline

**Date:** 2026-07-20  
**Branch:** `gpu-45-may-baseline-restore`  
**Harness:** post-M65 rebuild  
**JSON:** `results/test262_full_m65.json`  
**Log:** `results/test262_full_m65.log`  
**Command:**

```bash
python3 tools/test262_runner.py --full -j 8 --timeout 20 \
  --output-json results/test262_full_m65.json
```

**Wall time:** ~47.1 min (2824 s) · **Workers:** 8 · **Mode:** batch

---

## Headline

| Scope | Pass | Total | % | vs M47 (46.1%) | vs M37 (45.6%) |
|-------|-----:|------:|--:|---------------:|---------------:|
| **Full** | **24807** | **49998** | **49.6%** | **+1833 (+3.5pp)** | **+2035** |
| **language** | **17032** | **23899** | **71.3%** | **+1451 (+6.1pp)** | **+3.6pp vs 67.7%** |
| **built-ins** | **7118** | **23521** | **30.3%** | **+351 (+1.5pp)** | **+4.8pp vs 25.5%** |

**Timeouts:** 77 · **Fail+error:** ~25114 · **Skip:** 0

> New full-suite high-water: **49.6%**. Language reclaim (M48–M65) drove most of the jump.

---

## OA/S inside full run

| Suite | Pass / Total | % | Need for 90% |
|-------|-------------:|--:|-------------:|
| **Object** | 2470 / 3411 | **72.4%** | **+600** |
| **Array** | 2214 / 3304 | **67.0%** | **+760** |
| **String** | 759 / 1230 | **61.7%** | **+348** |

Product gate: **each ≥90%** (not aggregate).

---

## Language slices (dependency-relevant)

| Slice | Pass / Total | % | Fail mass | Notes |
|-------|-------------:|--:|----------:|-------|
| **for-of** | ~671 / 751 | **~89–91%** | ~80 | **≥90% dedicated (M65)**; residual dstr/TA |
| **generators** (stmt+expr) | ~502 / 556 | **~90%** | ~50 | solid |
| **arrow-function** | 316 / 343 | **92.1%** | 27 | solid |
| **object** expr | 936 / 1161 | **80.6%** | 225 | **next language mole (L3)** |
| **class** (stmt) | 3414 / 4367 | **78.2%** | 953 | **L2 — largest language fails** |
| **class** (expr) | 3221 / 4059 | **79.4%** | 838 | with stmt class ~1.8k fails |
| **arguments-object** | 119 / 263 | **45.2%** | 144 | L5 |
| **for-await-of** | 656 / 1234 | **53.2%** | 578 | L6 |
| **async** expr | 325 / 776 | **41.9%** | 451 | L6 |
| **module-code** | 380 / 748 | **50.8%** | 368 | L7 |
| **dynamic-import** | 413 / 997 | **41.4%** | 584 | L7 |

---

## Built-in fail deserts (last-mile)

| Built-in | Pass / Total | % | Fails |
|----------|-------------:|--:|------:|
| Temporal | 36 / 4588 | 0.8% | **4552** |
| TypedArray | 0 / 2174 | 0% | **2174** |
| RegExp | 570 / 1896 | 30.1% | 1326 |
| Date | 46 / 594 | 7.7% | 548 |
| Promise | 191 / 677 | 28.2% | 486 |
| Atomics | 0 / 382 | 0% | 382 |
| Proxy | 0 / 311 | 0% | 311 |
| Function | 163 / 509 | 32.0% | 346 |

Deserts dominate built-in fail count; **do not grind Temporal/TA first**.

---

## Compare ladder

| Milestone | Full pass% | Language | Notes |
|-----------|----------:|---------:|-------|
| M29h peak | 43.6% | — | pre–UTF-16 key regression |
| M31c | 38.3% | — | UTF-16/`\p` floor |
| M37 | 45.6% | 67.7% | prior high before OA/S thrash |
| M47 | 46.1% | 65.2% | built-in moles; language dip |
| **M65** | **49.6%** | **71.3%** | **current baseline**; for-of ≥90% |

---

## Distance to 90%

| Track | Pass | Target 90% | Still need |
|-------|-----:|-----------:|-----------:|
| Full | 24807 | ~44998 | **~+20191** |
| Language | 17032 | ~21509 | **~+4477** |
| Object | 2470 | ~3070 | **+600** |
| Array | 2214 | ~2974 | **+760** |
| String | 759 | ~1107 | **+348** |

---

## Notes

- Language **reclaimed** M37→M65 (+3.6pp language, +6.1pp vs M47).  
- for-of language gate **done** (dedicated 672/751 = 90.8%).  
- Next full only after material L3 object / L2 class / OA/S jumps.
