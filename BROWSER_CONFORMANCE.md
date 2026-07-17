# Browser JS Conformance — Living Scoreboard

**Updated:** 2026-07-17  
**Branch:** `gpu-45-may-baseline-restore`  
**Audience:** grind sessions + product planning for the embedded browser

---

## 0. Progress reality check

| Horizon | Score | Context |
|---------|------:|---------|
| Full suite 2026-07-15 (`full49k`) | **19244 / 49998 (38.5%)** | post-M26k class foundation |
| Full suite 2026-07-16 post Object/Array | **21783 / 49998 (43.6%)** | `/tmp/test262_full_m29h.json` **peak** |
| Full suite 2026-07-17 post UTF-16/`\p` | **19129 / 49998 (38.3%)** | `/tmp/test262_full_m31c.json` · **Δ −2654** vs peak |
| Post-M31d Object/Array/String **slices** | reclaiming | Object **43.6%**, Array **46.1%**, String **29.4%** (not full-run) |

**What happened:** M31a–c delivered real UTF-16 + RegExp Unicode surface, then the first full rescore exposed a **property-key regression**: many paths still treated keys as C strings (`GetByte`/`StringLength`) while JS string keys are UTF-16. That hammered **class**, **Object.defineProperty/create**, and `verifyProperty` / function `name`/`length` mass.

**What is true at the same time:** RegExp/String/unicodeSets **gained** capability; built-ins % is also crushed by **Temporal (~4.6k @ ~0%)** and TypedArray/Map/Set deserts in the denominator.

---

## 1. Goals (agreed)

### Browser-ready means

1. Language + classes (private basics)  
2. Property model (defineProperty, create, freeze/seal, keys)  
3. Arrays + strings usable  
4. Promises enough for fetch/UI  
5. RegExp usable (incl. reasonable Unicode)  
6. DOM bridge path  

**Not this phase:** Temporal, TypedArray/Atomics, full Proxy/Reflect, complete modules.

### Target bars

| Track | Near-term | Browser-useful bar |
|-------|----------:|-------------------:|
| **Object** | ≥65% | **≥80%** (product) |
| **Array** | ≥70% | **≥80%** (product) |
| **String** | ≥65% | **≥80%** (product) |
| **Language** | ≥70% (from 60.4%) | **≥80%** |
| **Full suite** | ≥42–45% reclaim | multi-phase; Temporal still desert |

Optional: report **full excluding Temporal** so deserts don’t drown Object/Array wins.

**Product call:** Object + Array + String at **80%+ each** is the usefulness gate for embedded page JS; Promise/RegExp follow.

---

## 2. Latest scoreboard

### 2.1 Full suite M31c (authoritative floor)

| Scope | Pass / Total | % | vs M29h |
|-------|-------------:|--:|--------:|
| **Full** | **19129 / 49998** | **38.3%** | **−2654** |
| language | 14446 / 23899 | 60.4% | −1864 |
| built-ins | 4087 / 23521 | 17.4% | −761 |
| Object | 1246 / 3411 | 36.6% | large drop |
| Array | 1337 / 3081 | 43.7% | modest drop |
| String | 336 / 1223 | 27.5% | up vs early |
| Promise | 152 / 677 | 22.5% | |
| RegExp | 518 / 1879 | 27.8% | net capability up |
| Temporal | 36 / 4588 | 0.8% | desert |
| class (stmt+expr) | — | ~62.5% post-M31d slice | was ~75% |

JSON: `/tmp/test262_full_m31c.json` · writeup: `results/FULL_SUITE_M31c.md`  
Wall: **~34 min** @ 8 workers.

### 2.2 Post-M31d reclaim slices (same day, not full rescore)

| Suite | Pass / Total | % |
|-------|-------------:|--:|
| Object (all) | **1486 / 3411** | **43.6%** (+240 vs full M31c) |
| Array (all) | **1408 / 3081** | **46.1%** |
| String (all) | **359 / 1223** | **29.4%** |
| RegExp (all) | **513 / 1879** | **27.7%** |
| arrow-function | **310 / 343** | **90.4%** |
| class (stmt+expr) | **5253 / 8426** | **62.5%** |
| midgate e2e+core | **PASS** | |

### 2.3 Recent moles

| Mole | Focus |
|------|--------|
| M26–M30 | class private, Object model, Array, String/Promise, RegExp depth |
| **M31a** | UTF-16 code-unit strings + `codePointAt` |
| **M31b–c** | `\p`/`\P` BMP + unicodeSets `v` surface |
| **M31c full** | 38.3% baseline; regression map |
| **M31d+** | UTF-16 **property-key** reclaim (gOPD, FuncProp, ObjHas, attr keys, defineProperty accessors) |

---

## 3. Active plan — Object / Array / String → **80% each**

### 3.1 Why 80%

Page JS is not useful if property model, arrays, and strings are “half-right.”  
**Gate:** `built-ins/Object`, `built-ins/Array`, `built-ins/String` each **≥80%** on test262 paths.

| | M31c full | M31e slice | Need 80% | Gap |
|--|----------:|-----------:|---------:|----:|
| Object | 36.5% | **43.6%** | 80% | **~+1240** passes |
| Array | 43.4% | **46.1%** | 80% | **~+1060** |
| String | 27.5% | **29.4%** | 80% | **~+620** |

### 3.2 Fail mass (where to grind)

1. **Object:** defineProperty (**804** fail) + defineProperties (**473**) dominate; then create/gOPD/assign.  
2. **Array:** `Array/prototype` (**~1540** fail) — reduce*/map/filter/forEach/some/every + splice/slice/concat; ES2023 `to*`/`at` missing.  
3. **String:** `String/prototype` (**~800** fail) — split, trim*, replace/replaceAll, slice/substring, match/search, case maps.

### 3.3 Campaign phases

| Phase | Focus | Exit gate |
|-------|--------|-----------|
| **OA1** | defineProperty + defineProperties | defineProperty ≥70%; Object overall ≥55% |
| **OA2** | create, gOPD, keys, assign, freeze/seal | Object ≥65% |
| **OA3** | entries/values/fromEntries + polish | **Object ≥80%** |
| **A1** | callback methods (holes, array-like, thisArg) | map/filter/reduce* ≥75% combined |
| **A2** | splice/slice/concat/sort/length mutators | Array ≥70% |
| **A3** | `at`, `toSpliced`/`toSorted`/`toReversed`/`with`, from/of | **Array ≥80%** |
| **S1** | split, slice, substring, includes/starts/ends/indexOf | those ≥70% |
| **S2** | replace/replaceAll, match/search, trim* | String ≥65% |
| **S3** | toString/valueOf boxing, at, pad, remaining | **String ≥80%** |

**Order:** OA1 → A1 (shared callback/attr infrastructure) → S1 → OA2/A2/S2 → A3/S3/OA3 → full rescore.

### 3.4 Dependency note

UTF-16 key correctness (M31d–e) unblocks descriptor tests; **keep fixing residual GetByte-as-C key paths** whenever Object/class flakes appear.  
Class reclaim helps method `.name` / non-enumerable defaults but is secondary to OA1.

### 3.5 Defer (not required for 80% OA/S)

Temporal, TypedArray, Map/Set, Proxy, full locale casefold, Array.fromAsync, Script `\p` mass.

---

## 4. Gates

```bash
python3 tools/js_midgate.py --rebuild --quick
# product spine
python3 tools/test262_runner.py --paths 'built-ins/Object' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Array' -j 8
python3 tools/test262_runner.py --paths 'built-ins/String' -j 6
# hot buckets
python3 tools/test262_runner.py --paths 'built-ins/Object/defineProperty' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Array/prototype' -j 8
python3 tools/test262_runner.py --paths 'built-ins/String/prototype' -j 6
# when all three ≥80%
python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_<tag>.json
```
