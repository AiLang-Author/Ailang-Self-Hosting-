# Full test262 suite — M47 baseline

**Date:** 2026-07-19  
**Branch:** `gpu-45-may-baseline-restore`  
**Harness:** post-M47 rebuild (`js_midgate.py --rebuild`)  
**JSON:** `results/test262_full_m47.json`  
**Log:** `results/test262_full_m47.log`  
**Command:**

```bash
python3 tools/test262_runner.py --full -j 8 --timeout 8 \
  --output-json results/test262_full_m47.json
```

**Wall time:** ~46.7 min (2804 s) · **Workers:** 8 · **Mode:** batch

---

## Headline

| Scope | Pass | Total | % | vs M37 (45.6%) | vs M31c (38.3%) | vs M29h peak (43.6%) |
|-------|-----:|------:|--:|---------------:|----------------:|---------------------:|
| **Full** | **22974** | **49998** | **46.1%** | **+174** | **+3845** | **+1191** |
| language | 15581 | 23899 | 65.2% | −591 vs M37 67.7% | up vs 60.4% | — |
| built-ins | 6767 | 23521 | 28.8% | **+759** vs M37 25.5% | up | — |
| annexB | 417 | 1086 | 38.4% | — | — | — |
| staging | 209 | 1492 | 14.0% | — | — | — |

**Timeouts:** 107 · **Errors:** 57 · **Skip:** 0

> New full-suite high-water mark: **46.1%** (was 45.6% M37).  
> Includes M38–M47 (defineProperty, Array holes, pad, PropTable 128, ArrayLike accessors, species, Date, …).

---

## OA/S inside full run

| Suite | Pass / Total | % | vs dedicated M47 slice |
|-------|-------------:|--:|------------------------|
| **Object** | 2464 / 3411 | **72.2%** | matches 72.5% (rounding/status) |
| **Array** | 2083 / 3081 | **67.6%** | matches 68.2% |
| **String** | 759 / 1223 | **62.1%** | matches 62.2% |

Product gate (near-term): **each ≥90%** (not aggregate). Need ~**+606 / +690 / +342**.

---

## Notes

- Language % dipped vs M37 while built-ins climbed hard — net full still **up**. Investigate language regressions only if they block OA/S 90%.  
- Deserts still dominate built-ins fail mass (Temporal / TypedArray / etc.).  
- Next full only at milestone after material OA/S jumps toward 90%.

## Compare ladder

| Milestone | Full pass% | Notes |
|-----------|----------:|-------|
| M29h peak | 43.6% | pre–UTF-16 key regression |
| M31c | 38.3% | UTF-16/`\p` floor |
| **M37** | **45.6%** | prior high |
| **M47** | **46.1%** | **current baseline** |
