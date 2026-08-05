# JS Engine Handoff — M41

**Branch:** `gpu-45-may-baseline-restore`  
**Long goal:** ~**95%** usable JS. **Near-term:** Object / Array / String each **≥80%**.

## Scores

| Suite | M40 | **M41** | Δ | Need ~80% |
|-------|----:|--------:|--:|----------:|
| **Object** | 70.7% | **70.6%** (2409/3411) | −3 | ~319 |
| **Array** | 57.7% | **59.1%** (1821/3081) | **+43** | ~643 |
| **String** | 54.2% | **54.5%** (666/1223) | **+3** | ~312 |

map slice: 154/216 (+7). Callbacks gained across reduce*/filter/forEach/some/every.

### Full suite

Still **45.6%** M37 (`results/FULL_SUITE_M37.md`).

## What landed M41

1. **ParseNumberStr** expanded (dependency for array-like `length`):
   - scientific `2E0` / `1e-3`
   - hex `0x0002`
   - `Infinity` / `-Infinity` / `NaN` keywords
2. **ToLength** via ArrayLikeLen: NaN/≤0 → 0; `+Inf` → 2^53−1; cap 2^53−1  
3. **ArraySpeciesCreate**: length **> 2^32−1 → RangeError** (map with `length: "Infinity"`)

## Docs already current

- `JS-DEPENDENCY-PLAN.md` / `BROWSER_CONFORMANCE.md` (M39/M40) — still valid DAG

## Next crush

1. Array map/filter residual (species, holes, strict)  
2. Object defineProperty redefine residual  
3. String non-RegExp  
4. RegExp → replace*

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA / fromAsync desert.
