# Full suite scorecard — M37 harness

**Date:** 2026-07-18  
**Branch:** `gpu-45-may-baseline-restore`  
**Commit (approx):** `a313aacd` (M37) + in-tree midgate rebuild  
**JSON:** `results/test262_full_m37.json`  
**Wall:** ~33 min @ 8 workers batch  

> **Note:** This run used the **M37 batch harness** (unicode escapes, Number ToString, Function index/instanceof).  
> It does **not** include M38 (defineProperty redefine-order + `ParseNumberStr` UTF-16). M38 OA/S slices improved further after this full run.

## Headline

| | Pass | Total | % | vs M31c | vs M29h peak |
|--|-----:|------:|--:|--------:|-------------:|
| **Full** | **22800** | **49998** | **45.6%** | **+3671** (38.3%) | **+1017** (43.6%) |
| language | 16172 | 23899 | **67.7%** | was 60.4% | was ~68% |
| built-ins | 6008 | 23521 | **25.5%** | was 17.4% | was ~20% |

## OA/S in full run (M37 harness)

| Suite | Pass/Total | % |
|-------|-----------:|--:|
| Object | 2267/3414 | 66.4% |
| Array | 1715/3083 | 55.6% |
| String | 671/1334 | 50.3% |

(denominators can differ slightly from path-only slices)

## Context

- Last full before this: **M31c 2026-07-17** — 19129/49998 (**38.3%**) after UTF-16/`\p` regression  
- M29h peak: **21783 (43.6%)**  
- M32–M37 OA/S climb recovered language + built-ins mass without re-full until now  

## Command

```bash
python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_m37.json
```
