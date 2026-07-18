# JS Engine Handoff — M35

**Branch:** `gpu-45-may-baseline-restore`  
**Goal:** Object / Array / String each **≥80%**

## Scores

| Suite | M34 | M35 | Δ |
|-------|----:|----:|--:|
| **Object** | 62.5% | **62.9%** (2136/3411) | +10 |
| **Array** | 52.6% | **53.1%** (1620/3081) | +13 |
| **String** | 32.4% | **43.7%** (533/1223) | **+137** |

### Gap to 80%

| | Need ~ |
|--|------:|
| Object | +593 |
| Array | +845 |
| String | +446 |

## What landed M35

1. **Boolean/Number/String.prototype valueOf + toString** (read `__value__`)
2. **Object(value)** boxes primitives via OBJ_CTOR; **Object() callable** via `__ctor__` on CALL
3. **defineProperties** uses getOwnPropertyNames (non-enumerable keys)
4. **CALL/CALL_METHOD** string methods use bound `this` (not FuncEnv) — fixes `obj.method = String.prototype.X`
5. **new String** boxes length + index properties

String.prototype.split **75%**, slice/substring **~55%**.

## Next (priority)

1. String trim unicode WS; replace/replaceAll; remaining split RegExp edges  
2. Object defineProperty residual + defineProperties mass  
3. Array reduce*/splice/concat; skip fromAsync desert or stub  
4. new String length if still flaky; unary + on Boolean wrappers  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA. Full suite only at milestone.
