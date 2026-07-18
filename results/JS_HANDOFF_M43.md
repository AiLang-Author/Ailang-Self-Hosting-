# JS Engine Handoff — M43

**Branch:** `gpu-45-may-baseline-restore`  
**Long goal:** ~**95%** usable JS. **Near-term:** OA/S each **≥80%**.

## Scores

| Suite | M42 | **M43** | Δ | Need ~80% |
|-------|----:|--------:|--:|----------:|
| **Object** | 70.7% | **72.0%** (2447/3411) | **+34** | ~280 |
| **Array** | 60.7% | **63.8%** (1949/3081) | **+80** | ~516 |
| **String** | 57.5% | **61.0%** (745/1223) | **+42** | ~233 |

map slice: **168/216 (77.8%)** (was 162/216).  
padStart/padEnd: **24/26 (92%)**.  
not-a-constructor (O/A/S sample 100): **~80%** (fails mostly missing methods).

Full suite still **45.6%** M37 until next milestone.

## What landed M43

1. **Native methods not constructors** — CONSTRUCT allowlist (Number/String/Boolean, Errors, Promise, Array, RegExp, Object, Date); others TypeError  
2. **padStart/padEnd UTF-16** — StrAlloc + StrSetUnit (was SetByte+CreateString corruption)  
3. **OrdinaryCallBindThis (user fns only)** — non-strict null/undefined → global; primitives → Boolean/Number/String boxes with `__value__`; **natives skip** so RequireObjectCoercible still sees null  
4. **Array callback thisArg** — missing → undefined (CallFunc binds global for non-strict); strict keeps undefined  
5. **ArrayToObject** boxes set `__value__` / `__class__`  
6. **PropTable MAX_ENTRIES 64→128** — Array.prototype was full (32 methods + 32 `__a_*`); new props silently dropped  
7. **Array hole → prototype** — ObjGet numeric holes fall through to Array.prototype; GET_ELEM + `in` use HasProperty chain; ArrayLikeHas/Get for map/filter/…

## Residual / known gaps

- map ~48 fails: species/proxy/realm, TypedArray/resizable, array-like getter mid-walk (8-b-*), some inherited accessors  
- pad exception-not-object-coercible (2) — multi-assert state after consecutive TypeErrors breaks later `new Test262Error` (single asserts pass)  
- not-a-constructor fails for unimplemented methods (fromAsync, toSorted, normalize, …)

## Next

1. Array-like getter/delete mid-map (8-b series) + remaining c-i accessors  
2. Object defineProperty redefine residual  
3. String non-RegExp → RegExp  
4. Species/create-species low-hanging if ROI  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Prefer int. No Temporal/TA/fromAsync.
