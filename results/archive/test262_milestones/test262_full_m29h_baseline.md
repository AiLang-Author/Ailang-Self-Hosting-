# test262 full baseline — post M29h

- **Date:** 2026-07-15
- **Commit:** cdbe1ec8 (M29h) + join polish pending
- **Command:** `python3 tools/test262_runner.py --full --jobs 8 --output-json results/test262_full_m29h_baseline.json`
- **TOTAL:** 49998 tests, wall 1956.6s
- **Pass:** 20322/49998 (**40.6%**)
- **Fail:** 29535  **T/O:** 86

| Category | Pass | Fail | T/O | Pass% |
|----------|-----:|-----:|----:|------:|
| language/expressions | 7411 | 3657 | 18 | 66.9% |
| language/statements | 6183 | 3130 | 24 | 66.2% |
| built-ins/Temporal | 60 | 4528 | 0 | 1.3% |
| built-ins/Object | 1248 | 2163 | 0 | 36.6% |
| built-ins/Array | 1415 | 1640 | 26 | 45.9% |
| built-ins/RegExp | 364 | 1512 | 3 | 19.4% |
| built-ins/TypedArray | 0 | 1438 | 0 | 0.0% |
| staging/sm | 166 | 1242 | 3 | 11.8% |
| built-ins/String | 277 | 946 | 0 | 22.6% |
| annexB/language | 407 | 438 | 0 | 48.2% |
| language/module-code | 364 | 383 | 1 | 48.7% |
| built-ins/TypedArrayConstructors | 0 | 736 | 0 | 0.0% |
| built-ins/Promise | 108 | 569 | 0 | 16.0% |
| built-ins/Date | 67 | 527 | 0 | 11.3% |
| built-ins/DataView | 0 | 561 | 0 | 0.0% |
| language/literals | 437 | 97 | 0 | 81.8% |
| built-ins/Iterator | 7 | 503 | 0 | 1.4% |
| built-ins/Function | 156 | 353 | 0 | 30.6% |
| built-ins/Set | 0 | 383 | 0 | 0.0% |
| built-ins/Atomics | 0 | 382 | 0 | 0.0% |
| language/eval-code | 53 | 294 | 0 | 15.3% |
| built-ins/Number | 108 | 232 | 0 | 31.8% |
| built-ins/Math | 115 | 212 | 0 | 35.2% |
| built-ins/Proxy | 0 | 311 | 0 | 0.0% |
| language/identifiers | 237 | 30 | 1 | 88.4% |
| language/arguments-object | 126 | 137 | 0 | 47.9% |
| annexB/built-ins | 36 | 205 | 0 | 14.9% |
| language/function-code | 57 | 160 | 0 | 26.3% |
| built-ins/Map | 0 | 204 | 0 | 0.0% |
| built-ins/ArrayBuffer | 0 | 196 | 0 | 0.0% |
