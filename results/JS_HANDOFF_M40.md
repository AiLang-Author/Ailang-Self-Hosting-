# JS Engine Handoff — M40

**Branch:** `gpu-45-may-baseline-restore`  
**Long goal:** ~**95%** usable JS. **Near-term:** Object / Array / String each **≥80%**.

## Scores

| Suite | M39 | **M40** | Δ | Need ~80% |
|-------|----:|--------:|--:|----------:|
| **Object** | 69.5% | **70.7%** (2412/3411) | **+41** | ~316 |
| **Array** | 57.7% | **57.7%** (1778/3081) | −1 | ~686 |
| **String** | 54.3% | **54.2%** (663/1223) | −1 | ~315 |

### Object sub-slices M40

| | Pass/Total |
|--|----------:|
| defineProperty | 867/1131 |
| defineProperties | 459/632 |
| gOPD | 211/328 |

### Full suite

Still **45.6%** M37 harness (`results/FULL_SUITE_M37.md`). Re-full after OA/S near 80%.

## What landed M40

1. Plan docs refreshed: `JS-DEPENDENCY-PLAN.md`, `BROWSER_CONFORMANCE.md` (M39 state + DAG)
2. **gOPD descriptors use Object.prototype** via `JSBridge__CreateUserObject`  
   - Root cause: `JSRT_CreateObject` leaves `[[Prototype]]` null → `desc.hasOwnProperty` missing  
   - Unblocks propertyHelper / `hasOwnProperty("get"|"set")` mass

## Already landed (M39 — keep green)

- new String index **slab keys**
- B/N/S.prototype → Object.prototype  
- DescField **MakeAccKey** (UTF-16)
- defineProperties **enumerable only**
- Array.length attr defaults

## Next crush

1. defineProperty `15.2.3.6-4` residual (~260)
2. Array map/filter/reduce (not fromAsync)
3. String non-RegExp polish
4. RegExp path for replace*

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA.
