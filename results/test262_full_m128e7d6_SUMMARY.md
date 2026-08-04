# Full test262 regression — M128e7d6

**Tip harness:** e7d6 bind CallBuf + TA @@iterator + Reflect.ownKeys (`29bf9992`)  
**Harness:** `test262_harness_batch.x` (e7d6 tip; e7d7 BigInt TA landed mid-run as separate binary)  
**JSON:** `results/test262_full_m128e7d6.json`  
**Log:** `results/test262_full_m128e7d6.log`  
**Wall time:** 3193.9s (~**53.2 min**)  
**Command:** `python3 tools/test262_runner.py --full -j 8 --timeout 12 --output-json results/test262_full_m128e7d6.json`

---

## Headline (vs e7c4)

| Metric | e7c4 | **e7d6 full** | Δ |
|--------|-----:|--------------:|--:|
| Tests discovered | 49,723 | **49,723** | 0 |
| **Pass** | 32,284 | **33,494** | **+1,210** |
| Fail | 16,915 | 15,671 | −1,244 |
| Error | 366 | 379 | +13 |
| Timeout | 158 | 179 | +21 |
| **Overall pass/total** | **64.93%** | **67.36%** | **+2.4 pp** |
| Language pass/total | 94.51% | **94.59%** | +0.1 pp |
| Built-ins pass/total | 38.16% | **43.13%** | **+5.0 pp** |

Language still ≥95% on pass/(pass+fail) residual; overall climb is almost entirely **built-ins** from the bind fix.

---

## By section

| Section | Pass | Fail | Error | T/O | Total | Pass% |
|---------|-----:|-----:|------:|----:|------:|------:|
| **language** | 22,356 | 919 | 294 | 66 | 23,635 | **94.6%** |
| **built-ins** | 10,143 | 13,208 | 69 | 98 | 23,518 | **43.1%** |
| staging | 453 | 1,001 | 16 | 14 | 1,484 | 30.5% |
| annexB | 542 | 543 | 0 | 1 | 1,086 | 49.9% |
| **TOTAL** | **33,494** | **15,671** | **379** | **179** | **49,723** | **67.4%** |

---

## B-core product builtins (pass/total)

| Builtin | e7c4 | **e7d6** | Δ pp |
|---------|-----:|---------:|-----:|
| **Object** | 81.9% | **82.2%** (2806/3414) | +0.3 |
| **Array** | 79.8% | **84.5%** (2604/3083) | **+4.7** |
| **String** | 66.3% | **67.0%** (894/1334) | +0.7 |
| **Promise** | 66.3% | **66.3%** (449/677) | 0 |
| Function | 68.2% | 68.0% (350/515) | −0.2 |

Array jumped hard: `Function.prototype.bind` CallBuf clobber had been poisoning any harness/test path that used `.bind` for factories or partial application (including Array method tests that rely on bound callbacks).

---

## Desert (AB/DV/TA) in full dump

| Surface | Pass/Total | Pass% |
|---------|----------:|------:|
| ArrayBuffer | 46/196 | 23.5% |
| DataView | 195/561 | 34.8% |
| TypedArray | 512/1438 | 35.6% |
| TypedArrayConstructors | 326/737 | 44.2% |

Standalone desert e7d6 was **1040/2931 (35.7%)**; e7d7 BigInt element fix (after this full run started) is **1112/2931 (38.2%)**. Next full rescore should pick up e7d7 + more.

---

## What moved the needle

1. **FUNC_BOUND CallBuf snapshot** — `f.bind(null,a)(b)` no longer clobbers call args; mass unblocks TypedArray `makeCtorArg.bind` + any other `.bind` partial-arg use.
2. TA ctor `@@iterator` + `Reflect.ownKeys` polyfill (smaller, desert-focused).

## Next

- Full rescore at **e7d7** tip (BigInt64/BigUint64 real Get/Set) for another ~70 desert + spillover.
- Continue desert: species/map/filter, set edges, detach, length accessors.
- Product path: String/Promise toward 80%; Array already past 80%.
