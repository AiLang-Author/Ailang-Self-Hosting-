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

| Track | Near-term (after reclaim) | Browser-usable |
|-------|---------------------------:|----------------|
| **Language** | **≥70–72%** (recover from 60.4%) | **≥80%** |
| **Core built-ins** (no Temporal/TA/Map) | **≥50%** combined | **≥70%** |
| **Full suite** | **≥42–45%** (recover toward peak) | multi-phase **≥75%** |

Optional: report **full excluding Temporal** so deserts don’t drown Object/Array wins.

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

## 3. Active plan — reclaim → core built-ins → RegExp polish

### 3.1 Dependency DAG

```
[R0] UTF-16 property keys correct          ← M31d in flight / extend
        │
        ├─► [R1] Class reclaim (≥70%)
        ├─► [R2] Object property model (≥50% → 54% prior)
        ├─► [R3] Array + String spine
        └─► [R4] Promise + RegExp depth (P1 lookbehind; P3 set algebra)

Defer: Temporal, TypedArray, Map/Set, Proxy, Script \p mass, modules
```

### 3.2 Ranked work

| Pri | Work | Success signal |
|-----|------|----------------|
| **R0** | Finish key audit (`MakeAttrKey`, OwnNames, Dispatch only const-C for cpay) | midgate; gOPD name/length; hasOwn; defineProperty attrs |
| **R1** | Class method/name/descriptor reclaim | class combined **≥70%** |
| **R2** | Object defineProperty/create/keys/freeze | Object **≥50%** |
| **R3** | Array holes/methods + String methods | Array **≥48%**; String no unit corruption |
| **R4** | Promise residual; RegExp P1/P3 | Promise **≥25%**; RegExp **≥35%** |
| **R5** | Full rescore | full **≥42%** (toward M29h peak) |

### 3.3 Built-ins honesty (full M31c)

Browser-track should emphasize Object/Array/String/Function/Promise/RegExp — not Temporal.

| Built-in | % (full M31c) | After M31d slice | Priority |
|----------|--------------:|-----------------:|----------|
| Object | 36.6% | **43.6%** | R2 |
| Array | 43.7% | **46.1%** | R3 |
| String | 27.5% | **29.4%** | R3 |
| Function | 27.5% | — | R0/R1 |
| Promise | 22.5% | — | R4 |
| RegExp | 27.8% | ~27.7% | R4 |
| Temporal / TA / Map | ~0% | — | **defer** |

### 3.4 RegExp Unicode (parked under reclaim)

| Item | Status |
|------|--------|
| P0 UTF-16 | ✓ |
| P2 `\p` BMP | ✓ GC generated stable; property-escapes **202/613** |
| P3 `v` surface | ✓ **68/152**; deepen later |
| P1 lookbehind/dups | residual |

---

## 4. Gates

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths \
  'built-ins/Object,built-ins/Array,built-ins/String' -j 8
python3 tools/test262_runner.py --paths \
  'language/statements/class,language/expressions/class' -j 8
# after R0–R2
python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_<tag>.json
```
