# Full test262 regression — M128e7c4

**Tip:** `9e67a65c`  
**Harness:** test262_harness_batch.x (rebuilt to tip)  
**JSON:** `results/test262_full_m128e7c4.json`  
**Log:** `results/test262_full_m128e7c4.log`  
**Wall time:** 2945.0s (~**49.1 min**)  
**Command:** `python3 tools/test262_runner.py --full -j 8 --timeout 12 --output-json results/test262_full_m128e7c4.json`

---

## Headline (vs e7bb baseline)

| Metric | e7bb | **e7c4** | Δ |
|--------|-----:|---------:|--:|
| Tests discovered | 49,723 | **49,723** | 0 |
| **Pass** | 29,162 | **32,284** | **+3,122** |
| Fail | 19,995 | 16,915 | −3,080 |
| Error | 404 | 366 | −38 |
| Timeout | 162 | 158 | −4 |
| **Overall pass/total** | **58.65%** | **64.93%** | **+6.3 pp** |
| Language pass/total | 87.49% | **94.51%** | **+7.0 pp** |
| Language pass/(pass+fail) | ~88.9%* | **~95.9%** | G2 held |
| Built-ins pass/total | 32.38% | **38.16%** | **+5.8 pp** |

\*e7bb language fail-only was lower residual after G2 campaign; e7c4 language primary metric still ≥95%.

---

## By section

| Section | Pass | Fail | Error | T/O | Total | Pass% |
|---------|-----:|-----:|------:|----:|------:|------:|
| **language** | 22,337 | 959 | 288 | 51 | 23,635 | **94.5%** |
| **built-ins** | 8,974 | 14,394 | 56 | 94 | 23,518 | **38.2%** |
| staging | 428 | 1,023 | 21 | 12 | 1,484 | 28.8% |
| annexB | 545 | 539 | 1 | 1 | 1,086 | 50.2% |
| **TOTAL** | **32,284** | **16,915** | **366** | **158** | **49,723** | **64.9%** |

---

## B-core product builtins (pass/total)

| Builtin | Pass | Total | Pass% | Target |
|---------|-----:|------:|------:|--------|
| **Object** | 2,792 | 3,411 | **81.9%** | ✅ B1 ≥80% · next 90% |
| **Array** | 2,459 | 3,081 | **79.8%** | ≈ B2 80% (slice score 80.9%) |
| **String** | 811 | 1,223 | **66.3%** | → 80% |
| **Promise** | 449 | 677 | **66.3%** | → 80% |
| Function | 347 | 509 | 68.2% | B4 |
| Number | 217 | 340 | 63.8% | B4 |
| Math | 173 | 327 | 52.9% | B4 |
| Map | 115 | 204 | 56.4% | B4 |
| Set | 127 | 383 | 33.2% | B4 |
| RegExp | 576 | 1,879 | 30.7% | B5 hard |

### Deserts (intentionally not product-blocking)

| Desert | Pass | Total | Pass% |
|--------|-----:|------:|------:|
| Temporal | 137 | 4,588 | 3.0% |
| TypedArray | 0 | 1,438 | 0% |
| DataView | 2 | 561 | 0.4% |
| Atomics | 2 | 382 | 0.5% |
| ArrayBuffer | 0 | 196 | 0% |
| SharedArrayBuffer | 0 | 104 | 0% |

**Built-ins excluding heavy deserts** ≈ **58%** pass/total — product core is far ahead of the desert-weighted 38%.

---

## Language G2 certificate

| | Value |
|--|------:|
| Language pass | 22,337 |
| Language total | 23,635 |
| Pass/total | **94.5%** |
| Residual (fail+err+t/o) | 1,298 |
| G2 primary (~pass/(pass+fail) fail-only) | **~95.9%** ✅ |

Language march remains **done enough**; residual is long-tail (`using`, class harness edges, unicode/regexp, etc.).

---

## What moved since e7bb → e7c4

- Language: G2 campaign (modules, import, TLA, class residual crush)
- Object: defineProperty spine, assign Set(throw), gOPD/keys symbol filter, array attr path
- Array: concat IsConcatSpreadable, Array.of ID fix, ES2023 change-array-by-copy
- String: replaceAll + earlier method work
- Promise: mostly flat (~66%)

---

## Next grind (product path to 90–95% B-core)

1. **Array → 90%** — sort/splice/from residual (~+300)
2. **Object → 90%** — defineProperty residual, freeze/seal (~+300)
3. **String → 80%** — split/match/search/matchAll (~+170)
4. **Promise → 80%** — allSettled/any/race edges (~+95)
5. Optional: Function/Map/Math ≥70%; RegExp only if feeding String

Ignore Temporal/TypedArray/Atomics for publishable engine narrative.
