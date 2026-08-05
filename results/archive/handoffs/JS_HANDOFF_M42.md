# JS Engine Handoff — M42

**Branch:** `gpu-45-may-baseline-restore`  
**Long goal:** ~**95%** usable JS. **Near-term:** OA/S each **≥80%**.

## Scores

| Suite | M41 | **M42** | Δ | Need ~80% |
|-------|----:|--------:|--:|----------:|
| **Object** | 70.6% | **70.7%** (2413/3411) | +4 | ~315 |
| **Array** | 59.1% | **60.7%** (1869/3081) | **+48** | ~595 |
| **String** | 54.5% | **57.5%** (703/1223) | **+37** | ~275 |

map slice: **162/216 (75%)** (+8).

Full suite still **45.6%** M37 until next milestone.

## What landed M42

1. **`new Array(n)` holes** — was `n×undefined` (ArrHas true for all); now **ArrSetLen** raw holes  
2. **Callback methods order** — **ToLength before IsCallable** (length getter side effects on TypeError)  
3. **Default `this`** for map/filter/forEach/some/every — global when no thisArg (non-strict)  
4. **ToPrimitive** failure → **TypeError** (not silent undef → NaN)

## Next

1. Array map residual (~54) + reduce*/filter  
2. Object defineProperty redefine  
3. String non-RegExp → RegExp  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA/fromAsync.
