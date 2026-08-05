# Language suite rescore — M128e7br

**Tip:** `ad922b27` (Reflect + field SuperProp + nested-fn SuperCall fix)

**Date:** 2026-08-02

**JSON:** `results/test262_lang_m128e7br.json`

**Wall:** ~23.7 min (batch, -j 8, timeout 12s)


## Headline

| Metric | Value |
|--------|------:|
| Tests | 23635 |
| Pass | 21290 |
| Fail | 2015 |
| Timeout | 52 |
| Error | 278 |
| **pass/(pass+fail)** | **91.35%** |
| pass/total | 90.08% |

### vs prior full-language baselines

| Tip | Language pass% | Notes |
|-----|---------------:|-------|
| M128e7l full | 90.1% | G1 met |
| M128e7bb full language slice | 87.49% | older metric in SUMMARY |
| **M128e7br language --all** | **91.35%** | this run |
| G2 target | 95% | gap ~849 passes |

## Top residual categories

| Category | Pass | Fail | T/O | Tot | Pass% |
|----------|-----:|-----:|----:|----:|------:|
| `expressions/dynamic-import` | 313 | 628 | 0 | 941 | 33.3% |
| `statements/class` | 4027 | 123 | 16 | 4367 | 97.0% |
| `module-code/top-level-await` | 12 | 239 | 0 | 251 | 4.8% |
| `import/import-defer` | 7 | 94 | 0 | 101 | 6.9% |
| `expressions/class` | 3986 | 52 | 16 | 4059 | 98.7% |
| `statements/for-of` | 690 | 42 | 0 | 751 | 94.3% |
| `statements/using` | 38 | 40 | 0 | 78 | 48.7% |
| `module-code/namespace` | 0 | 38 | 0 | 38 | 0.0% |
| `expressions/yield` | 31 | 25 | 7 | 63 | 55.4% |
| `expressions/object` | 1130 | 31 | 0 | 1161 | 97.3% |
| `literals/regexp` | 207 | 27 | 4 | 238 | 88.5% |
| `statements/try` | 174 | 27 | 0 | 201 | 86.6% |
| `statements/for-in` | 91 | 24 | 0 | 115 | 79.1% |
| `statements/function` | 428 | 22 | 0 | 451 | 95.1% |
| `expressions/new` | 36 | 23 | 0 | 59 | 61.0% |
| `eval-code/direct` | 264 | 22 | 0 | 286 | 92.3% |
| `expressions/generators` | 272 | 18 | 0 | 290 | 93.8% |
| `statements/switch` | 94 | 17 | 0 | 111 | 84.7% |
| `expressions/super` | 77 | 11 | 0 | 94 | 87.5% |
| `import/import-attributes` | 2 | 15 | 0 | 17 | 11.8% |
| `expressions/compound-assignment` | 440 | 3 | 0 | 454 | 99.3% |
| `statements/for` | 371 | 14 | 0 | 385 | 96.4% |
| `expressions/arrow-function` | 329 | 14 | 0 | 343 | 95.9% |
| `expressions/function` | 251 | 13 | 0 | 264 | 95.1% |
| `statements/variable` | 165 | 13 | 0 | 178 | 92.7% |
| `statements/await-using` | 81 | 13 | 0 | 94 | 86.2% |
| `statements/generators` | 254 | 10 | 2 | 266 | 96.2% |
| `expressions/logical-assignment` | 66 | 9 | 0 | 78 | 88.0% |
| `computed-property-names/class` | 17 | 7 | 0 | 29 | 70.8% |
| `expressions/tagged-template` | 15 | 12 | 0 | 27 | 55.6% |
| `statements/let` | 134 | 11 | 0 | 145 | 92.4% |
| `expressions/call` | 82 | 10 | 0 | 92 | 89.1% |
| `statements/if` | 59 | 10 | 0 | 69 | 85.5% |
| `expressions/import.meta` | 12 | 10 | 0 | 22 | 54.5% |
| `expressions/async-generator` | 614 | 9 | 0 | 623 | 98.6% |
| `literals/string` | 64 | 7 | 0 | 73 | 90.1% |
| `comments/hashbang` | 20 | 9 | 0 | 29 | 69.0% |
| `eval-code/indirect` | 53 | 8 | 0 | 61 | 86.9% |
| `statements/labeled` | 17 | 7 | 0 | 24 | 70.8% |
| `expressions/property-accessors` | 14 | 7 | 0 | 21 | 66.7% |
| `statements/const` | 130 | 6 | 0 | 136 | 95.6% |
| `statements/while` | 32 | 6 | 0 | 38 | 84.2% |
| `types/reference` | 24 | 5 | 0 | 29 | 82.8% |
| `module-code/ambiguous-export-bindings` | 4 | 5 | 0 | 9 | 44.4% |
| `import/import-bytes` | 0 | 5 | 0 | 5 | 0.0% |
| `statements/async-generator` | 297 | 3 | 1 | 301 | 99.0% |
| `statements/with` | 177 | 4 | 0 | 181 | 97.8% |
| `expressions/await` | 18 | 4 | 0 | 22 | 81.8% |
| `expressions/grouping` | 5 | 4 | 0 | 9 | 55.6% |
| `expressions/async-function` | 90 | 3 | 0 | 93 | 96.8% |
| `arguments-object/mapped` | 40 | 3 | 0 | 43 | 93.0% |
| `statements/block` | 18 | 2 | 1 | 21 | 90.0% |
| `statements/async-function` | 72 | 1 | 1 | 74 | 98.6% |
| `expressions/template-literal` | 55 | 2 | 0 | 57 | 96.5% |
| `statements/do-while` | 34 | 2 | 0 | 36 | 94.4% |
| `expressions/in` | 34 | 1 | 0 | 36 | 97.1% |
| `expressions/optional-chaining` | 37 | 0 | 0 | 38 | 100.0% |

## Residual bulk (where the remaining ~2.3k non-passes live)

| Area | ~fails | Notes |
|------|-------:|-------|
| **dynamic-import** | ~630 | syntax/catch/usage/namespace |
| **module-code top-level-await** | ~240 | almost unstarted |
| **import-defer** | ~94 | nearly zero |
| **class residual** (dstr/subclass/elements) | ~180 | class wall mostly closed; subclass/dstr edges |
| **for-of** | ~42 | residual iteration |
| **using / await-using** | ~53 | resource management |
| **yield / generators / try / for-in / switch** | ~150 | mid-tier chips |
| timeouts | 52 | flaky/slow |
| harness **error** | 278 | batch noise (esp. statements/class) |

### Class wall status
- `expressions/class` **98.7%** (3986 pass / 52 fail)
- `statements/class` **97.0%** runner p% (4027 pass; +201 error +16 t/o in batch)
- Elements (e7br slice): **~99.5%**

### G2 (≥95% language)
- Current **91.35%** pass/(pass+fail) · **90.08%** pass/total
- Need ~**+1.2k–2.1k** more passes depending on metric
- Fastest ROI for G2 is **not** class anymore — **dynamic-import + modules** dominate residual

## 100% chips (large)
for-await-of, assignment, assignmenttargettype, numeric/bigint literals, most binary ops, delete, async-arrow, array, …
