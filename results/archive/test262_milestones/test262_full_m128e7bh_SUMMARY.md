# Full test262 regression — M128e7bh

**Tip:** `70ad3b2b`  
**Harness:** test262_harness_batch.x  
**JSON:** `results/test262_full_m128e7bh.json`  
**Wall time:** 2965.6s (~**49.4 min**)  
**Generated:** 2026-08-01T20:25:21.888915+00:00  

---

## Headline

| Metric | Value |
|--------|------:|
| Tests discovered | **49,723** |
| **Pass** | **30,123** |
| Fail | 19,046 |
| Error | 392 |
| Timeout | 162 |
| Skip | 0 |
| **Overall pass rate** | **60.58%** |
| Language pass rate | **88.7%** |
| Built-ins pass rate | **35.22%** |

## Language → G2 (95%)

| | Value |
|--|------:|
| Language pass | 20,964 |
| Language total | 23,635 |
| Pass% | 88.7% |
| G2 need (ceil 95%) | 22,454 |
| **G2 gap** | **1,490** |

## By section

| Section | Pass | Fail | Error | T/O | Total | Pass% |
|---------|-----:|-----:|------:|----:|------:|------:|
| language | 20,964 | 2,303 | 317 | 51 | 23,635 | 88.70% |
| built-ins | 8,283 | 15,085 | 55 | 95 | 23,518 | 35.22% |
| staging | 389 | 1,061 | 19 | 15 | 1,484 | 26.21% |
| annexB | 487 | 597 | 1 | 1 | 1,086 | 44.84% |

## Language top residual categories (by non-pass count)

| Category | Pass | Residual | Total | Pass% |
|----------|-----:|---------:|------:|------:|
| statements/class | 3260 | 1107 | 4367 | 74.7% |
| expressions/class | 3484 | 575 | 4059 | 85.8% |
| statements/for-of | 681 | 70 | 751 | 90.7% |
| import/import-defer | 56 | 45 | 101 | 55.4% |
| statements/using | 38 | 40 | 78 | 48.7% |
| expressions/object | 1124 | 37 | 1161 | 96.8% |
| expressions/yield | 31 | 32 | 63 | 49.2% |
| literals/regexp | 207 | 31 | 238 | 87.0% |
| module-code/top-level-await | 222 | 29 | 251 | 88.4% |
| statements/try | 173 | 28 | 201 | 86.1% |
| eval-code/direct | 262 | 24 | 286 | 91.6% |
| statements/for-in | 91 | 24 | 115 | 79.1% |
| statements/function | 427 | 24 | 451 | 94.7% |
| expressions/new | 36 | 23 | 59 | 61.0% |
| expressions/super | 74 | 20 | 94 | 78.7% |
| expressions/arrow-function | 324 | 19 | 343 | 94.5% |
| expressions/generators | 271 | 19 | 290 | 93.4% |
| expressions/function | 246 | 18 | 264 | 93.2% |
| statements/for | 367 | 18 | 385 | 95.3% |
| statements/switch | 94 | 17 | 111 | 84.7% |
| statements/variable | 163 | 15 | 178 | 91.6% |
| statements/await-using | 81 | 13 | 94 | 86.2% |
| statements/let | 132 | 13 | 145 | 91.0% |
| computed-property-names/class | 17 | 12 | 29 | 58.6% |
| expressions/tagged-template | 15 | 12 | 27 | 55.6% |
| statements/generators | 254 | 12 | 266 | 95.5% |
| eval-code/indirect | 51 | 10 | 61 | 83.6% |
| expressions/assignment | 475 | 10 | 485 | 97.9% |
| expressions/call | 82 | 10 | 92 | 89.1% |
| statements/if | 59 | 10 | 69 | 85.5% |
| comments/hashbang | 20 | 9 | 29 | 69.0% |
| expressions/async-generator | 614 | 9 | 623 | 98.6% |
| expressions/logical-assignment | 69 | 9 | 78 | 88.5% |
| statements/const | 128 | 8 | 136 | 94.1% |
| expressions/property-accessors | 14 | 7 | 21 | 66.7% |
| statements/labeled | 17 | 7 | 24 | 70.8% |
| expressions/compound-assignment | 448 | 6 | 454 | 98.7% |
| expressions/import.meta | 16 | 6 | 22 | 72.7% |
| statements/while | 32 | 6 | 38 | 84.2% |
| expressions/dynamic-import | 936 | 5 | 941 | 99.5% |

## Near-complete language categories (1–25 residual)

| Category | Pass | Residual | Total | Pass% |
|----------|-----:|---------:|------:|------:|
| expressions/delete | 68 | 1 | 69 | 98.6% |
| expressions/template-literal | 56 | 1 | 57 | 98.2% |
| expressions/exponentiation | 43 | 1 | 44 | 97.7% |
| expressions/does-not-equals | 37 | 1 | 38 | 97.4% |
| expressions/coalesce | 23 | 1 | 24 | 95.8% |
| statements/continue | 23 | 1 | 24 | 95.8% |
| statements/break | 19 | 1 | 20 | 95.0% |
| types/object | 18 | 1 | 19 | 94.7% |
| expressions/logical-and | 17 | 1 | 18 | 94.4% |
| expressions/logical-or | 17 | 1 | 18 | 94.4% |
| block-scope/leave | 14 | 1 | 15 | 93.3% |
| statements/empty | 1 | 1 | 2 | 50.0% |
| statements/async-function | 72 | 2 | 74 | 97.3% |
| expressions/in | 34 | 2 | 36 | 94.4% |
| statements/do-while | 34 | 2 | 36 | 94.4% |
| expressions/conditional | 20 | 2 | 22 | 90.9% |
| types/number | 19 | 2 | 21 | 90.5% |
| destructuring/binding | 17 | 2 | 19 | 89.5% |
| statements/return | 14 | 2 | 16 | 87.5% |
| block-scope/shadowing | 13 | 2 | 15 | 86.7% |
| expressions/new.target | 12 | 2 | 14 | 85.7% |
| computed-property-names/object | 10 | 2 | 12 | 83.3% |
| types/undefined | 6 | 2 | 8 | 75.0% |
| expressions/this | 4 | 2 | 6 | 66.7% |
| computed-property-names/to-name-side-effects | 2 | 2 | 4 | 50.0% |
| expressions/async-function | 90 | 3 | 93 | 96.8% |
| literals/string | 70 | 3 | 73 | 95.9% |
| arguments-object/mapped | 40 | 3 | 43 | 93.0% |
| statements/block | 18 | 3 | 21 | 85.7% |
| statements/async-generator | 297 | 4 | 301 | 98.7% |
| statements/with | 177 | 4 | 181 | 97.8% |
| module-code/namespace | 34 | 4 | 38 | 89.5% |
| expressions/await | 18 | 4 | 22 | 81.8% |
| expressions/grouping | 5 | 4 | 9 | 55.6% |
| expressions/dynamic-import | 936 | 5 | 941 | 99.5% |
| types/reference | 24 | 5 | 29 | 82.8% |
| expressions/compound-assignment | 448 | 6 | 454 | 98.7% |
| statements/while | 32 | 6 | 38 | 84.2% |
| expressions/import.meta | 16 | 6 | 22 | 72.7% |
| statements/labeled | 17 | 7 | 24 | 70.8% |
| expressions/property-accessors | 14 | 7 | 21 | 66.7% |
| statements/const | 128 | 8 | 136 | 94.1% |
| expressions/async-generator | 614 | 9 | 623 | 98.6% |
| expressions/logical-assignment | 69 | 9 | 78 | 88.5% |
| comments/hashbang | 20 | 9 | 29 | 69.0% |
| expressions/assignment | 475 | 10 | 485 | 97.9% |
| expressions/call | 82 | 10 | 92 | 89.1% |
| statements/if | 59 | 10 | 69 | 85.5% |
| eval-code/indirect | 51 | 10 | 61 | 83.6% |
| statements/generators | 254 | 12 | 266 | 95.5% |


## vs baselines (this run)

| Baseline | Overall | Language | Built-ins | G2 gap | Δ overall pass | Δ language |
|----------|--------:|---------:|----------:|-------:|---------------:|-----------:|
| **e7x** (best prior) | 61.35% | 91.42% (21,607) | 33.86% | 847 | **−382** | **−643** |
| **e7bb** (last full) | 58.65% | 87.49% (20,679) | 32.38% | 1,775 | **+961** | **+285** |
| **e7bh** (this) | **60.58%** | **88.70%** (20,964) | **35.22%** | **1,490** | — | — |

### Transitions

| | e7x→e7bh | e7bb→e7bh |
|--|--------:|---------:|
| Fixed (bad→pass) | 1,631 | 1,219 |
| Regressed (pass→bad) | 2,013 | 258 |
| **Net** | **−382** | **+961** |

**Read:** e7bc–e7bh recovered most of the e7bb dip vs e7x overall, but language is still **~643** short of e7x (G2 gap 1,490 vs e7x’s 847). Built-ins **improved** to **35.22%** (best of the three fulls).

### Batch vs no-batch note

Some categories that scored **100%** no-batch show 1 residual in batch full (e.g. template-literal 56/57, delete 68/69) — treat as harness/batch flake until no-batch reconfirm.

Artifacts: `results/test262_full_m128e7bh_*.md` · prior compare also under `/tmp/test262_full_m128e7bh_vs_e7bb_*`.
