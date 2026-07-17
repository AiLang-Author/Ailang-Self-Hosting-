# JS Engine Handoff — M34

**Date:** 2026-07-17  
**Branch:** `gpu-45-may-baseline-restore`  
**Continue:** Object/Array/String → **80% each** (still multi-session).

## Scores (M34)

| Suite | M33 | M34 | Δ |
|-------|----:|----:|--:|
| Object | 61.1% (2074) | **62.5%** (2126/3411) | **+52** |
| Array | 49.1% (1500) | **52.6%** (1607/3081) | **+104** |
| String | 30.9% (377) | **32.4%** (396/1223) | **+19** |

Full suite floor still **38.3% M31c** — do not full-rescore until OA/S near 80%.

## What landed M34

1. **Object.entries / values / fromEntries** installed on harness Object + implementations
2. **Object.assign** — arrays/strings/null sources; TypeError on null target
3. **Object.keys on arrays** — dense indices + ArrSide named props
4. **Object.prototype.toString** — [object Type] brands (Math/JSON/Array/…)
5. **String includes/startsWith/endsWith** — UTF-16 unit search (not C StringContains)
6. **Array forEach/some/every** — thisArg rebind + ArrayCallbackThis + exc

## Gap to 80%

| | Need passes ~ |
|--|-------------:|
| Object | **~+600** (defineProperty 360, defineProperties 230, gOPD 140 dominate) |
| Array | **~+950** (reduce*/map/filter/forEach/some/every ~640) |
| String | **~+580** (split 98, trim 66, replace*, slice/substring) |

## Next order

1. defineProperty residual → 70%+ then defineProperties
2. Array reduce/reduceRight + map hole/species mass
3. String split (empty sep/limit/@@split), slice NaN/ToInteger, trim unicode WS
4. Object.prototype valueOf / propertyIsEnumerable / Symbol.toStringTag

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Array' -j 8
python3 tools/test262_runner.py --paths 'built-ins/String' -j 6
```

Prefer **int**. No Temporal/TA.
