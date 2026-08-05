# Full test262 suite — M110 baseline

**Date:** 2026-07-23  
**Branch:** `gpu-45-may-baseline-restore`  
**Tip:** `04ebcd7d` (M110c AWAIT reject catch) · M109 for-await · M110 async yield*  
**JSON:** `results/test262_full_m110.json`  
**Log:** `results/test262_full_m110.log`

```bash
./ailang.x JS-tests/test262_harness.ailang -o test262_harness.x
./ailang.x JS-tests/test262_harness_batch.ailang -o test262_harness_batch.x
python3 tools/test262_runner.py --full -j 8 --timeout 15 \
  --output-json results/test262_full_m110.json
```

**Wall time:** ~47.1 min (2825 s) · **Workers:** 8 · **Mode:** batch

---

## Headline

| Scope | Pass | Total | % | vs M97 |
|-------|-----:|------:|--:|-------:|
| **Full** | **28291** | **49998** | **56.6%** | **+316 (+0.6pp)** |
| **language** | **19685** | **23899** | **82.4%** | **+~7pp** (denom drift) |
| **built-ins** | **7704** | **23521** | **32.8%** | **regressed vs M97** |
| annexB | 545 | 1086 | 50.2% | — |
| staging | 357 | 1492 | 23.9% | — |

**Timeouts:** 78 · **error:** 328 · **fail:** 21301

> Full-suite high-water: **56.6%** (was M97 56.0% / 27975).

---

## Language wins (batch full suite)

| Slice | M97 | M110 | Δ passes |
|-------|----:|-----:|---------:|
| for-await-of | 58.6% | **96.0%** | +461 |
| async-generator expr | 45.3% | **91.5%** | +288 |
| async-generator stmt | 76.7% | **90.4%** | +41 |
| async-function expr | 60.2% | **90.3%** | +28 |
| async-function stmt | 81.1% | **91.9%** | +8 |
| class stmt | 84.0% | **90.1%** | +265 |
| class expr | 86.5% | **92.4%** | +241 |
| arguments-object | 81.0% | **95.1%** | +37 |
| function-code | 51.6% | 68.1% | +62 |

Multipath (`--no-batch`) for async slices already ≥90% pre-full-suite; batch full confirms.

---

## Built-in regressions (investigate)

| Built-in | M97 | M110 | Δ |
|----------|----:|-----:|--:|
| Array | 82.7% | 72.4% | **-317** |
| Date | 48.4% | 22.2% | **-162** |
| RegExp | 35.3% | 30.1% | -101 |
| Object | 77.0% | 75.0% | -69 |
| Promise | 38.1% | 29.1% | -61 |

Suspect: M109/M110 iterator/await/thenable changes side-effects. **Priority: restore Array first** (~317 free passes → full +0.6pp alone).

---

## Still far from 90% (language, n≥30)

- module-code 30.7%, import 12.6%, dynamic-import 46.1%
- with 10.5%, await-using/using ~30–46%
- eval-code 51.7%, global-code 52.3%
- many small expression ops 50–80%
- function-code 68.1% (batch; multipath earlier ~92%)

---

## Next grind order

1. **Bisect/fix Array regression** (largest built-in drop)
2. Date / Promise / RegExp follow-on if same root cause
3. **Modules** linker (module-code ~31%)
4. Object → 90% (defineProperty clusters)
5. Promise.all / race / any / allSettled
