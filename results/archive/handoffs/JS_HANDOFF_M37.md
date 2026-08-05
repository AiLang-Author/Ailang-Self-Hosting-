# JS Engine Handoff — M37

**Branch:** `gpu-45-may-baseline-restore`  
**Goal:** Object / Array / String each **≥80%**

## Scores

| Suite | M35 | M36 (uncommitted) | **M37** | Δ vs M36 |
|-------|----:|------------------:|--------:|---------:|
| **Object** | 62.9% | 63.6% (2163) | **66.5%** (2267/3411) | **+104** |
| **Array** | 53.4% | 53.4% (1630) | **55.6%** (1713/3081) | **+83** |
| **String** | 43.9% | 44.7% (546) | **53.5%** (654/1223) | **+108** |

### Gap to 80%

| | Need ~ |
|--|------:|
| Object | +462 |
| Array | +752 |
| String | +325 |

## What landed M37

1. **Number ToString** — 15 significant digits + round-trip shorten (fixes `"123.456000…00306"` → `"123.456"`); scientific for ≥1e21 / &lt;1e-6 kept
2. **Object.prototype.valueOf** + trim WS BMP set (IsTrimWS)
3. **DescFieldGet** prefers own accessor over undefined data placeholder (defineProperty Attributes with `get:`)
4. **GET_ELEM / SET_ELEM** treat FUNCTION as object-like (array methods on callables / `fn[i]=`)
5. **instanceof** walks implicit Function.prototype / Array.prototype (ObjGet `__proto__` skipped them)
6. **String `\uXXXX` / `\u{…}` / `\xNN`** decode in lexer; **CreateString** UTF-8→UTF-16 (invalid → Latin-1)
7. float_buf 48→96 for sci/fractional format scratch

String.prototype.trim slice: **123/129 (95.3%)**.

## Next (priority)

1. Object defineProperty residual (~325) + defineProperties (~222) + gOPD (~118)
2. Array reduce*/map/filter/indexOf/concat; skip fromAsync desert (~95@0%)
3. String replace*/search/match/split RegExp edges; locale* desert
4. Template string `\u` still placeholder (`?`) — fix if template tests matter

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA. Full suite only at milestone.
