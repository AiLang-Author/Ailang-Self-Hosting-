# test262 full rescore — post M27 + M29h

- **Date:** 2026-07-16  
- **Tip commits:** `fb35d62f` (M27c2) · `04989b70` (M29h Array)  
- **Command:** `python3 tools/test262_runner.py --full --jobs 8 --output-json /tmp/test262_full_m29h.json`  
- **TOTAL:** 49998 · wall ~1953s  
- **Pass:** **21783 / 49998 (43.6%)**  
- **Fail:** 28085 · **T/O:** 81  

Compare:

| Snapshot | Pass | % |
|----------|-----:|--:|
| full49k (2026-07-15 post-M26k) | 19244 | 38.5% |
| mid-Object grind | 21090 | 42.2% |
| **this run** | **21783** | **43.6%** |

| Root | Pass | Total | % | Δ vs full49k-ish |
|------|-----:|------:|--:|------------------:|
| language | 16310 | 23899 | 68.2% | +~0.5–2 pp language lift |
| built-ins | 4848 | 23521 | 20.6% | large (Object/Array) |
| annexB | 443 | 1086 | 40.8% | — |
| staging | 182 | 1492 | 12.2% | — |

| Built-in | Pass / Total | % |
|----------|-------------:|--:|
| Object | 1837 / 3411 | 53.9% |
| Array | ~1504 / 3081 | ~49% |
| String | ~294 / 1334 | ~22% |
| Promise | ~110 / 677 | ~16% |
| Temporal | 60 / 4588 | 1.3% |

**Next:** Array reduce/map/filter holes → String → Promise → RegExp. See `BROWSER_CONFORMANCE.md`.
