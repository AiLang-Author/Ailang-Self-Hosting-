# Browser JS Conformance — Living Scoreboard

**Updated:** 2026-07-20  
**Branch:** `gpu-45-may-baseline-restore`  
**Plan:** [`JS-DEPENDENCY-PLAN.md`](./JS-DEPENDENCY-PLAN.md)  
**Full baseline:** [`results/FULL_SUITE_M65.md`](./results/FULL_SUITE_M65.md)

---

## Hard goal

**90% full test262 · working JS engine · all features** (language + core built-ins).  
OA/S each ≥90% is a **checkpoint**, not the destination.

| Track | Now (M65) | Checkpoint | Hard bar |
|-------|----------:|-----------:|---------:|
| **Full suite** | **49.6%** | ≥60% mid | **≥90%** |
| **Language** | **71.3%** | ≥80% | **≥90%** |
| **Object** | 72.4% | — | **≥90%** |
| **Array** | 67.0% | — | **≥90%** |
| **String** | 61.7% | — | **≥90%** |
| built-ins overall | 30.3% | climbs with OA/S + Promise/RegExp | **≥90%** usable |
| for-of (language) | **≥90%** | — | ✅ M65 |

---

## Progress ladder

| Milestone | Full pass% | Notes |
|-----------|----------:|-------|
| M29h peak | 43.6% | pre–UTF-16 key regression |
| M31c | 38.3% | UTF-16/`\p` floor |
| M37 | 45.6% | prior high · language **67.7%** |
| M47 | 46.1% | built-in moles · language **65.2%** |
| **M65** | **49.6%** | **baseline** · language **71.3%** · for-of ≥90% |

JSON: `results/test262_full_m65.json` (local; may be gitignored)

---

## March order (dependency)

```
L3 object expr → L2 class → L5 arguments → L6 async → L7 modules
  → B1 Object 90% → B2 Array 90% → B3 String 90%
  → F full 90% (deserts last)
```

| Done | Next |
|------|------|
| L1 names (M48+) | **L3 object** residual (~81%) |
| L4 for-of ≥90% (M65) | **L2 class** (~78–79%, largest language fails) |

See plan for fail-mass tables and gates.

---

## OA/S product slices (M65 full)

| Suite | Pass / Total | % | Need ~90% |
|-------|-------------:|--:|----------:|
| Object | 2470 / 3411 | 72.4% | +600 |
| Array | 2214 / 3304 | 67.0% | +760 |
| String | 759 / 1230 | 61.7% | +348 |

---

## Active work

1. **L3 object expr** — computed names, methods, spread/assign edge.  
2. **L2 class** — private/static/heritage residual (fail-mass).  
3. L5 args → L6 async → L7 modules.  
4. OA/S crush without regressing language.

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'language/expressions/object' -j 8
python3 tools/test262_runner.py --paths 'language/statements/class,language/expressions/class' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```
