# JS Engine Handoff — M44

**Branch:** `gpu-45-may-baseline-restore`  
**Long goal:** ~**95%** usable JS. **Near-term:** OA/S each **≥80%**.

## Scores

| Suite | M43 | **M44** | Δ | Need ~80% |
|-------|----:|--------:|--:|----------:|
| **Object** | 72.0% | **72.4%** (2462/3411) | **+15** | ~267 |
| **Array** | 63.8% | **64.0%** (1955/3081) | **+6** | ~510 |
| **String** | 61.0% | **61.3%** (749/1223) | **+4** | ~229 |

reduce: **174/260 (66.9%)** · reduceRight: **172/260 (66.2%)** · pad/trim improving.

Full suite still **45.6%** M37 until next milestone.

## What landed M44

1. **trimEnd UTF-16** — `CreateStringLen` treated ptr as Latin-1; now `CreateStringSlice`  
2. **reduce / reduceRight / flatMap** — **ToLength before IsCallable** (length getter side effects)  
3. **Date as real constructor** — was object+`__ctor__`; now native func + `Date.prototype.__class__`  
4. **Date native ID collision fix** — `DATE_NOW`/`DATE_CTOR` were **172/173** overlapping **ARR_VALUES**/**ARR_ITER_NEXT** (Date.now was array-iterator path). Now **175/176**  
5. **Date.now** — returns number (coarse ms via multiply; no broken clock_gettime)

## Residual / next

- reduce still ~86 fails: species/proxy/getter mid-walk (same class as map 8-b)  
- Object toString Symbol.toStringTag / proxies  
- String indexOf/slice/substring residual  
- Array includes / forEach residual  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA/fromAsync.
