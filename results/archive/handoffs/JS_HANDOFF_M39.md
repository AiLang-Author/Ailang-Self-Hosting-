# JS Engine Handoff — M39

**Branch:** `gpu-45-may-baseline-restore`  
**Long goal:** usable JS engine ~**95%** full suite; **near-term product gate:** Object / Array / String each **≥80%** by dependency order.

## Scores

| Suite | M38 | **M39** | Δ | Need ~80% |
|-------|----:|--------:|--:|----------:|
| **Object** | 68.2% | **69.5%** (2371/3411) | **+43** | ~357 |
| **Array** | 57.6% | **57.7%** (1779/3081) | **+5** | ~685 |
| **String** | 54.2% | **54.3%** (664/1223) | **+1** | ~314 |

### Full suite (last complete)

| | Score | When |
|--|------:|------|
| **Full** | **22800/49998 (45.6%)** | 2026-07-18 M37 harness · `results/FULL_SUITE_M37.md` |

M38/M39 not yet in a full rescore. Re-full near OA/S 80% or major mole.

## What landed M39 (dependency fixes)

1. **`new String` indices** — PropTable key ptrs must be **slab-copied** (`IntToStr` static buffer collapsed all indices to last digit). Same for `Object(string)` box path.
2. **Boolean/Number/String.prototype → Object.prototype** — re-link after Object exists (early install had `object_proto==0`). Fixes `new Boolean() instanceof Object`.
3. **DescField Get/Has** — **MakeAccKey** with StrUnit (UTF-16 keys from getOwnPropertyNames). Unblocked defineProperties on accessor Properties bags.
4. **defineProperties** — only **enumerable** own keys (skip array `length` etc.).
5. **GetAttrBits** — Array.length default `W !E !C`; Function name/length `!W !E C`.

## Dependency march (80% → 95%)

```
Object.defineProperty / gOPD / attributes  ──►  Array callbacks (map/filter/reduce)
        │                                              │
        ▼                                              ▼
  defineProperties / assign / keys              indexOf/concat/slice species
        │                                              │
        └──────────► String methods (non-RegExp) ──────┘
                              │
                              ▼
                     RegExp + replace/match/search
                              │
                              ▼
                     Promise / async / language reclaim
                              │
                              ▼
                     full suite 80%+ → 95% (Temporal/TA still desert drag)
```

**Now:** keep Object attribute mass + Array array-like (String boxes fixed).  
**Skip:** fromAsync, Temporal, TypedArray deserts until core is green.

## Next moles

1. Object defineProperty `15.2.3.6-4` residual + gOPD (~100+)  
2. Array map/filter/reduce/forEach residual (not fromAsync)  
3. String indexOf/substring/slice (non-locale, non-RegExp)  
4. Midgate every rebuild; OA/S rescore; full only at milestones  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA.
