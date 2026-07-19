# JS Engine Handoff — M47

**Branch:** `gpu-45-may-baseline-restore`  
**Long goal:** ~**95%** usable JS.  
**Product gate (bumped):** Object, Array, and String each **≥90%** on test262 (**not** aggregate).

## Scores

| Suite | M46 | **M47** | Δ | Need ~**90%** |
|-------|----:|--------:|--:|-------------:|
| **Object** | 72.5% | **72.5%** (2464/3411) | 0 | **~606** |
| **Array** | 68.1% | **68.2%** (2083/3081) | **+4** | **~690** |
| **String** | 62.2% | **62.2%** (759/1223) | 0 | **~342** |

map **81.0%**, filter **81.8%**. Combined OA/S still ~69.1% aggregate — **gate is per-suite 90%**.

## Goal change

| | Old | **New** |
|--|----:|--------:|
| Object | ≥80% | **≥90%** |
| Array | ≥80% | **≥90%** |
| String | ≥80% | **≥90%** |
| Full suite long | ~95% | ~95% |

## What landed M47

1. **Docs/scoreboard** retargeted to **90% each**  
2. **ArraySpeciesCreate** (ES-correcter):
   - non-object constructor → TypeError  
   - **IsConstructor** (natives = CONSTRUCT allowlist only)  
   - `@@species` undefined/null → ArrayCreate  
   - built-in Array → empty CreateArray (ArrPush fill)  
   - +create-species-non-ctor / create-species-undef

## Distance to 90% each

| Suite | Pass | Target 90% | Still need |
|-------|-----:|-----------:|-----------:|
| Object | 2464 | 3070 | **606** |
| Array | 2083 | 2773 | **690** |
| String | 759 | 1101 | **342** |

## Next big levers

1. **concat** (~25% — array-like rewrite like push)  
2. **reduce** residual + **sort/splice**  
3. **String** toLowerCase/indexOf residual + RegExp-free split  
4. **Object** defineProperty redefine / toString tags  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA/fromAsync.
