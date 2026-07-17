# JS Engine Handoff — M33 (new session start here)

**Date:** 2026-07-17  
**Branch:** `gpu-45-may-baseline-restore`  
**Why new session:** Compaction API still broken; continue from this file + planning docs.

---

## 0. First 60 seconds

```bash
cd /home/bob/Ailang-Self-Hosting-
git log -5 --oneline
# Read: results/JS_HANDOFF_M33.md, JS-DEPENDENCY-PLAN.md, BROWSER_CONFORMANCE.md
python3 tools/js_midgate.py --rebuild --quick
```

**Product gate:** Object, Array, String each **≥80%**.

---

## 1. Scores (post-M33 slices)

| Suite | Pass/Total | % | vs M32 handoff |
|-------|-----------:|--:|----------------|
| **Object** | **2074/3411** | **61.1%** | was 53.7% (**+244**) |
| **defineProperty** | **771/1131** | **68.4%** | was 55.1% (**+148**) |
| **Array** | **1500/3081** | **49.1%** | was 47.5% (**+49**) |
| **String** | **377/1223** | **30.9%** | was 30.7% (**+2**) |
| midgate e2e+core | **PASS** | | |

Full suite floor unchanged: **19129/49998 (38.3%)** M31c — do not re-run until OA/S milestone.

### Gap to 80%

| | Now | Need ~80% | Still need |
|--|----:|----------:|-----------:|
| Object | 61.1% | ~2729 | **~+655** |
| Array | 49.1% | ~2465 | **~+965** |
| String | 30.9% | ~979 | **~+602** |

---

## 2. What landed (M33)

### OA1 — defineProperty residual
1. **Array index ObjGet/ObjSet** — indices go to `ArrGet`/`ArrSet`, not only ArrSide table (was the root of gOPD value wrong + defineProperty not updating `a[i]`).
2. **ARRAY as Attributes object** — descriptor type check allows `JSType.ARRAY` (arrays are objects in ES).
3. **Top-level `this` / `globalThis`** — InstallBuiltins sets both (compiler emits `GET_GLOBAL("this")`; was ReferenceError).
4. **!configurable redef already present**; data redefine clears old `__get_`/`__set_`.
5. **gOPD accessor attrs** — read real E/C bits; include get/set undefined for partial accessors.
6. **UTF-16-safe accessor keys** on GET/SET for object + array paths (`StrUnit` not `GetByte`).

### A1 (started)
- map/filter: re-bind thisArg each call; propagate callback `exc_prop`.
- `JSVM__ArrayCallbackThis` — thin String box for callback 3rd arg (`instanceof String`) while ArrayLike* still uses string prim.

### Not done
- defineProperty **≥70%** (at **68.4%**, ~22 passes short)
- A1 map/filter/reduce* mass (still ~half fail — holes/species/Math brand/toString tag)
- S1 split/slice/includes

---

## 3. Next order

1. **OA1 finish** — defineProperty → **≥70%** (remaining: Arguments edges, symbols, length redefine, 4-redef residual)
2. **A1** — reduce*/forEach/some/every same thisArg+exc+callback-this pattern; hole/species
3. **S1** — String split (98 fail), slice/substring, includes/starts/ends/indexOf
4. Midgate after every rebuild. Prefer **int**. No Temporal/TA. Full suite only at OA/S 80% milestone.

---

## 4. Key files

| Path | Role |
|------|------|
| `Librarys/Browser/Library.JSBridge.ailang` | defineProperty, gOPD |
| `Librarys/Browser/JSRuntime/Library.JSRTObject.ailang` | ObjGet/ObjSet array indices |
| `Librarys/Browser/JSVM/Library.JSVMDispatch.ailang` | GET/SET accessor keys UTF-16 |
| `Librarys/Browser/JSVM/Library.JSVMBuiltins.ailang` | global this/globalThis |
| `Librarys/Browser/JSVM/Library.JSVMArrayMethods.ailang` | map/filter + ArrayCallbackThis |
| `Librarys/Browser/JSVM/Library.JSVMStringMethods.ailang` | S1 next |

---

## 5. Gates

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object/defineProperty' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Object' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Array' -j 8
python3 tools/test262_runner.py --paths 'built-ins/String' -j 6
```

---

*Handoff complete. New session: open this file first.*
