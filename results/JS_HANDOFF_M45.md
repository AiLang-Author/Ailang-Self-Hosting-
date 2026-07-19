# JS Engine Handoff — M45

**Branch:** `gpu-45-may-baseline-restore`  
**Long goal:** ~**95%** usable JS. **Near-term:** OA/S each **≥80%**.

## Scores

| Suite | M44 | **M45** | Δ | Need ~80% |
|-------|----:|--------:|--:|----------:|
| **Object** | 72.4% | **72.5%** (2464/3411) | **+2** | ~265 |
| **Array** | 64.0% | **65.1%** (1989/3081) | **+34** | ~476 |
| **String** | 61.3% | **61.3%** (749/1223) | 0 | ~229 |

pop **18/23 (78%)** (was ~30%). shift **15/20 (75%)**.

Full suite still **45.6%** M37 until next milestone.

## What landed M45

1. **Array-like pop/push/shift/unshift** — `ArrayLikeGet/Set/Delete/SetLen`; length writeback on objects  
2. **reverse** — array-like + hole-preserving swap  
3. **includes** — missing arg → undefined; `+Infinity` fromIndex → false  
4. **Symbol.toStringTag** well-known + **Object.prototype.toString** prefers `@@toStringTag`

## Next (biggest remaining gaps)

1. **reduce/map/filter** residual (~50–90 each): species, mid-iteration getters (8-b), proxies  
2. **String** indexOf/substring/slice ToInteger + ToString error paths (~40 combined)  
3. **Object defineProperty** redefine / hasOwn edge cases  
4. fill/copyWithin/splice array-like polish  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA/fromAsync.
