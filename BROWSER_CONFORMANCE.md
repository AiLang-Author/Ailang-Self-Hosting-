# Browser JS Conformance — Living Scoreboard

**Updated:** 2026-07-19  
**Branch:** `gpu-45-may-baseline-restore`  
**Plan:** [`JS-DEPENDENCY-PLAN.md`](./JS-DEPENDENCY-PLAN.md)  
**Handoff:** [`results/JS_HANDOFF_M47.md`](./results/JS_HANDOFF_M47.md)

---

## Hard goal

**90% full test262 · working JS engine · all features** (language + core built-ins).  
OA/S each ≥90% is a **checkpoint**, not the destination.

| Track | Now (M47) | Checkpoint | Hard bar |
|-------|----------:|-----------:|---------:|
| **Full suite** | **46.1%** | ≥60% mid | **≥90%** |
| **Language** | 65.2% | ≥80% | **≥90%** |
| **Object** | 72.5% | — | **≥90%** |
| **Array** | 68.2% | — | **≥90%** |
| **String** | 62.2% | — | **≥90%** |
| built-ins overall | 28.8% | climbs with OA/S + Promise/RegExp | **≥90%** usable |

---

## Progress ladder

| Milestone | Full pass% | Notes |
|-----------|----------:|-------|
| M29h peak | 43.6% | pre–UTF-16 key regression |
| M31c | 38.3% | UTF-16/`\p` floor |
| M37 | 45.6% | prior high · language **67.7%** |
| **M47** | **46.1%** | **baseline** · language **65.2%** (−591) · built-ins +759 |
| M48+ | TBD | SetFunctionName · **language first** |

JSON: `results/test262_full_m47.json`

---

## Why language fell while built-ins rose

See plan. Short version:

- M38–M47 optimized **Object/Array/String/property model**.
- Shared paths (`function.name` !W, CallFunc this, PropTable, species, array holes) **broke class/dstr/name tests** (~492 of ~740 language regressions).
- Net full **+174** only: language −591 ≈ cancelled half of built-ins gains.
- **Fix order now:** reclaim language (SetFunctionName → class → object → for-of → arguments → async/modules), **then** grind OA/S to 90% each, **then** full 90%.

---

## OA/S product slices (M47)

| Suite | Pass / Total | % | Need ~90% |
|-------|-------------:|--:|----------:|
| Object | 2464 / 3411 | 72.5% | +606 |
| Array | 2083 / 3081 | 68.2% | +690 |
| String | 759 / 1223 | 62.2% | +342 |

---

## Active work

1. **M48 residual** — finish SetFunctionName paths (dstr global, object lit stack-safe); midgate; language slice.  
2. Knock language bugs in fail-mass order (class → object → for-of → arguments).  
3. Resume OA/S crush without regressing language.

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'language/statements/class,language/expressions/object' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```
