# JS Engine Handoff — M38

**Branch:** `gpu-45-may-baseline-restore`  
**Goal:** Object / Array / String each **≥80%**

## Scores

| Suite | M37 | **M38** | Δ |
|-------|----:|--------:|--:|
| **Object** | 66.5% (2267) | **68.2%** (2328/3411) | **+61** |
| **Array** | 55.6% (1713) | **57.6%** (1774/3081) | **+61** |
| **String** | 53.5% (654) | **54.2%** (663/1223) | **+9** |

### Full suite (fresh 2026-07-18)

| | Score | Notes |
|--|------:|-------|
| **Full M37 harness** | **22800/49998 (45.6%)** | `results/test262_full_m37.json` · **above M29h peak 43.6%** |
| language | 67.7% | was 60.4% M31c |
| built-ins | 25.5% | was 17.4% M31c |

Full run did **not** include M38 binary; expect full to rise further after next full at milestone.

### Gap to 80%

| | Need ~ |
|--|------:|
| Object | +401 |
| Array | +691 |
| String | +316 |

## What landed M38

1. **defineProperty:** apply data `value` **after** redefine reject (was ObjSet first → SameValue always matched new value; `!W && !C` never threw)
2. **ParseNumberStr:** use **StrUnit/StrLen** (UTF-16 JS strings). `GetByte` on headered payloads made `Number("2")` → NaN → array-like `length:"2"` broken

## What M37 already had (prior)

Number ToString, unicode `\u`/`\x`, Function GET/SET_ELEM, instanceof Function/Array, DescFieldGet accessor-first, trim WS, valueOf.

## Next

1. Object defineProperty residual (`15.2.3.6-4` accessor redefines, propertyHelper) + defineProperties/gOPD  
2. Array map/filter/reduce residual (not fromAsync)  
3. String replace*/match/search (RegExp)  
4. Full suite again only near OA/S 80% or major mole  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA.
