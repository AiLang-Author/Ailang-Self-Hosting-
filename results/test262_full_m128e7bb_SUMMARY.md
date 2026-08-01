# Full test262 regression — M128e7bb

**Tip:** `6dbf7744`  
**Harness:** test262_harness_batch.x  
**JSON:** `results/test262_full_m128e7bb.json`  
**Wall time:** 2936.2s (~**48.9 min**)  
**Generated:** 2026-08-01T01:19:04.798843+00:00  

---

## Headline

| Metric | Value |
|--------|------:|
| Tests discovered | **49,723** |
| **Pass** | **29,162** |
| Fail | 19,995 |
| Error | 404 |
| Timeout | 162 |
| Skip | 0 |
| **Overall pass rate** | **58.65%** |
| Language pass rate | **87.49%** |
| Built-ins pass rate | **32.38%** |

## Language → G2 (95%)

| | Value |
|--|------:|
| Language pass | 20,679 |
| Language total | 23,635 |
| Pass% | 87.49% |
| G2 need (ceil 95%) | 22,454 |
| **G2 gap** | **1,775** |

## By section

| Section | Pass | Fail | Error | T/O | Total | Pass% |
|---------|-----:|-----:|------:|----:|------:|------:|
| language | 20,679 | 2,578 | 323 | 55 | 23,635 | 87.49% |
| built-ins | 7,616 | 15,753 | 55 | 94 | 23,518 | 32.38% |
| staging | 381 | 1,066 | 25 | 12 | 1,484 | 25.67% |
| annexB | 486 | 598 | 1 | 1 | 1,086 | 44.75% |

## Language top residual categories (by non-pass count)

| Category | Pass | Residual | Total | Pass% |
|----------|-----:|---------:|------:|------:|
| statements/class | 3200 | 1167 | 4367 | 73.3% |
| expressions/class | 3421 | 638 | 4059 | 84.3% |
| statements/for-of | 661 | 90 | 751 | 88.0% |
| expressions/object | 1116 | 45 | 1161 | 96.1% |
| import/import-defer | 56 | 45 | 101 | 55.4% |
| statements/using | 38 | 40 | 78 | 48.7% |
| expressions/yield | 27 | 36 | 63 | 42.9% |
| literals/regexp | 207 | 31 | 238 | 87.0% |
| expressions/super | 64 | 30 | 94 | 68.1% |
| statements/try | 171 | 30 | 201 | 85.1% |
| module-code/top-level-await | 222 | 29 | 251 | 88.4% |
| statements/for | 356 | 29 | 385 | 92.5% |
| statements/function | 422 | 29 | 451 | 93.6% |
| expressions/arrow-function | 318 | 25 | 343 | 92.7% |
| eval-code/direct | 262 | 24 | 286 | 91.6% |
| expressions/compound-assignment | 430 | 24 | 454 | 94.7% |
| expressions/tagged-template | 3 | 24 | 27 | 11.1% |
| statements/for-in | 91 | 24 | 115 | 79.1% |
| expressions/function | 241 | 23 | 264 | 91.3% |
| expressions/new | 36 | 23 | 59 | 61.0% |
| expressions/call | 73 | 19 | 92 | 79.3% |
| expressions/generators | 272 | 18 | 290 | 93.8% |
| statements/variable | 160 | 18 | 178 | 89.9% |
| statements/switch | 94 | 17 | 111 | 84.7% |
| statements/let | 129 | 16 | 145 | 89.0% |
| expressions/assignment | 471 | 14 | 485 | 97.1% |
| expressions/template-literal | 43 | 14 | 57 | 75.4% |
| statements/await-using | 81 | 13 | 94 | 86.2% |
| computed-property-names/class | 17 | 12 | 29 | 58.6% |
| statements/generators | 254 | 12 | 266 | 95.5% |
| statements/const | 125 | 11 | 136 | 91.9% |
| eval-code/indirect | 51 | 10 | 61 | 83.6% |
| module-code/namespace | 28 | 10 | 38 | 73.7% |
| statements/if | 59 | 10 | 69 | 85.5% |
| comments/hashbang | 20 | 9 | 29 | 69.0% |
| expressions/logical-assignment | 69 | 9 | 78 | 88.5% |
| expressions/array | 44 | 8 | 52 | 84.6% |
| expressions/async-generator | 616 | 7 | 623 | 98.9% |
| expressions/property-accessors | 14 | 7 | 21 | 66.7% |
| statements/labeled | 17 | 7 | 24 | 70.8% |

## Near-complete language categories (1–25 residual)

| Category | Pass | Residual | Total | Pass% |
|----------|-----:|---------:|------:|------:|
| expressions/delete | 68 | 1 | 69 | 98.6% |
| expressions/async-arrow-function | 59 | 1 | 60 | 98.3% |
| statements/continue | 23 | 1 | 24 | 95.8% |
| statements/break | 19 | 1 | 20 | 95.0% |
| types/object | 18 | 1 | 19 | 94.7% |
| expressions/logical-and | 17 | 1 | 18 | 94.4% |
| expressions/logical-or | 17 | 1 | 18 | 94.4% |
| block-scope/leave | 14 | 1 | 15 | 93.3% |
| expressions/comma | 5 | 1 | 6 | 83.3% |
| statements/empty | 1 | 1 | 2 | 50.0% |
| statements/async-function | 72 | 2 | 74 | 97.3% |
| statements/do-while | 34 | 2 | 36 | 94.4% |
| expressions/coalesce | 22 | 2 | 24 | 91.7% |
| expressions/conditional | 20 | 2 | 22 | 90.9% |
| types/number | 19 | 2 | 21 | 90.5% |
| destructuring/binding | 17 | 2 | 19 | 89.5% |
| statements/return | 14 | 2 | 16 | 87.5% |
| block-scope/shadowing | 13 | 2 | 15 | 86.7% |
| computed-property-names/object | 10 | 2 | 12 | 83.3% |
| types/undefined | 6 | 2 | 8 | 75.0% |
| expressions/this | 4 | 2 | 6 | 66.7% |
| computed-property-names/to-name-side-effects | 2 | 2 | 4 | 50.0% |
| literals/string | 70 | 3 | 73 | 95.9% |
| expressions/in | 33 | 3 | 36 | 91.7% |
| statements/block | 18 | 3 | 21 | 85.7% |
| expressions/dynamic-import | 937 | 4 | 941 | 99.6% |
| statements/async-generator | 297 | 4 | 301 | 98.7% |
| arguments-object/mapped | 39 | 4 | 43 | 90.7% |
| expressions/await | 18 | 4 | 22 | 81.8% |
| expressions/new.target | 10 | 4 | 14 | 71.4% |
| expressions/grouping | 5 | 4 | 9 | 55.6% |
| expressions/optional-chaining | 33 | 5 | 38 | 86.8% |
| types/reference | 24 | 5 | 29 | 82.8% |
| statements/while | 32 | 6 | 38 | 84.2% |
| expressions/import.meta | 16 | 6 | 22 | 72.7% |
| expressions/async-generator | 616 | 7 | 623 | 98.9% |
| statements/with | 174 | 7 | 181 | 96.1% |
| statements/labeled | 17 | 7 | 24 | 70.8% |
| expressions/property-accessors | 14 | 7 | 21 | 66.7% |
| expressions/array | 44 | 8 | 52 | 84.6% |
| expressions/logical-assignment | 69 | 9 | 78 | 88.5% |
| comments/hashbang | 20 | 9 | 29 | 69.0% |
| statements/if | 59 | 10 | 69 | 85.5% |
| eval-code/indirect | 51 | 10 | 61 | 83.6% |
| module-code/namespace | 28 | 10 | 38 | 73.7% |
| statements/const | 125 | 11 | 136 | 91.9% |
| statements/generators | 254 | 12 | 266 | 95.5% |
| computed-property-names/class | 17 | 12 | 29 | 58.6% |
| statements/await-using | 81 | 13 | 94 | 86.2% |
| expressions/assignment | 471 | 14 | 485 | 97.1% |

## Files

| Artifact | Path |
|----------|------|
| Raw JSON | `results/test262_full_m128e7bb.json` |
| Stats | `results/test262_full_m128e7bb_STATS.json` |
| Knockout list | `results/test262_full_m128e7bb_KNOCKOUT.md` |
| Regression watch | `results/test262_full_m128e7bb_REGRESSION.md` |
| Regression JSON | `results/test262_full_m128e7bb_REGRESSION.json` |
| Log | `results/test262_full_m128e7bb.log` |

## Notes

- Mode: **batch** harness (`-j 8`, timeout 12s). Some fails re-pass in isolation (batch pollution / harness_eof).
- Isolation recheck of 40 random language “regressed” paths: **8 PASS / 32 FAIL** → majority are real fails, not only flakes.
- vs e7x (`a7cefc59`): net language **−928** pass; fixed 800 language, regressed 1784 language.
- Known session wins that stay green in full suite: `in` private-in, `instanceof` samples, `concatenation` S9.8_A5_T2, optional-chaining short-circuit family.
- **Do not treat overall 58.65% as “worse engine only”** without triage: class/private bulk + Array method edges dominate residual; batch noise adds margin.

## Command to regenerate

```bash
python3 tools/test262_runner.py --full --timeout 12 -j 8 \
  --output-json results/test262_full_m128e7bb.json
python3 tools/test262_baseline_report.py results/test262_full_m128e7bb.json \
  --prior results/test262_full_m128e7x.json --label M128e7bb --tip $(git rev-parse --short HEAD)
```
