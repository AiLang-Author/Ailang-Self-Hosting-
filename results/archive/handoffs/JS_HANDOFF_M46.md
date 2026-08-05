# JS Engine Handoff — M46

**Branch:** `gpu-45-may-baseline-restore`  
**Long goal:** ~**95%** usable JS. **Near-term product gate:** OA/S each **≥90%** (not aggregate).

## Scores

| Suite | M45 | **M46** | Δ | Need ~**90%** |
|-------|----:|--------:|--:|-------------:|
| **Object** | 72.5% | **72.5%** (2464/3411) | 0 | ~606 |
| **Array** | 65.1% | **68.1%** (2079/3081) | **+90** | ~694 |
| **String** | 61.3% | **62.2%** (759/1223) | **+10** | ~342 |

### Callback methods (the big lever)

| Method | M45-ish | **M46** |
|--------|--------:|--------:|
| map | ~77% | **80.6%** (174/216) |
| filter | ~78% | **81.4%** (197/242) |
| forEach | ~77% | **81.1%** (154/190) |
| reduce | ~67% | **73.1%** (190/260) |
| reduceRight | ~66% | **73.1%** (190/260) |
| some | ~81% | **85.4%** |
| every | ~83% | **86.2%** |

## What landed M46

1. **ArrayLikeHas/Get invoke accessors** — `__get_N` via `JSBridge__MakeAccKey` + CallFunc (defineProperty getters). Unlocks mid-iteration 8-b tests and inherited accessor paths for **all** callback methods.  
2. **String indexOf/substring/slice ToInteger** — `+Infinity` / `NaN` / ToNumber throw propagation.

## Next levers toward **90% each**

1. **reduce residual (~70)** — remaining 8-b edge cases, length subclass quirks  
2. **ArraySpeciesCreate** (~species create-* fails on map/filter)  
3. **String** remaining ~40 on indexOf/substring/toLowerCase error paths  
4. **Object** defineProperty redefine / toString symbol-tag on builtins  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA/fromAsync.
