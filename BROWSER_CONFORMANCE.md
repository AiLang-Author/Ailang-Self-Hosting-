# Browser JS Conformance — Living Scoreboard

**Updated:** 2026-07-19 (M47)  
**Branch:** `gpu-45-may-baseline-restore`  
**Handoff:** [`results/JS_HANDOFF_M47.md`](./results/JS_HANDOFF_M47.md)  
**Plan:** [`JS-DEPENDENCY-PLAN.md`](./JS-DEPENDENCY-PLAN.md)

---

## 0. Progress reality check

| Horizon | Score | Context |
|---------|------:|---------|
| Full suite 2026-07-16 M29h **peak** | **21783 / 49998 (43.6%)** | pre–UTF-16 key regression |
| Full suite 2026-07-17 M31c | **19129 / 49998 (38.3%)** | UTF-16/`\p` + key regressions |
| Full suite 2026-07-18 M37 | 22800 / 49998 (45.6%) | prior high |
| **Full suite 2026-07-19 M47** | **22974 / 49998 (46.1%)** | **new high** · `results/FULL_SUITE_M47.md` |
| language (full M47) | **65.2%** | was 67.7% M37 (net still up full) |
| built-ins (full M47) | **28.8%** | was 25.5% M37 · Temporal desert still dominates |
| **Object / Array / String M47 slices** | **72.5% / 68.2% / 62.2%** | product bar **90% each** |

**Long goal:** ~**95%** usable JS engine for embedded browser.  
**Near-term product gate:** Object + Array + String each **≥90%** (not aggregate).

---

## 1. Goals

### Browser-ready means

1. Language + classes (private basics)  
2. Property model (defineProperty, create, freeze/seal, keys)  
3. Arrays + strings usable  
4. Promises enough for fetch/UI  
5. RegExp usable (incl. reasonable Unicode)  
6. DOM bridge path  

**Not this phase:** Temporal, TypedArray/Atomics, full Proxy/Reflect, complete modules, `Array.fromAsync`.

### Target bars

| Track | Now (M47) | Product bar | Long |
|-------|----------:|------------:|-----:|
| **Object** | **72.5%** | **≥90%** | ≥95% |
| **Array** | **68.2%** | **≥90%** | ≥95% |
| **String** | **62.2%** | **≥90%** | ≥95% |
| **Language** | 65.2% full | ≥90% | ≥95% |
| **Full suite** | **46.1%** | ≥60% mid | **~95%** |

---

## 2. Latest scoreboard

### 2.1 Full suite M47 (authoritative high-water)

| Scope | Pass / Total | % | vs M37 | vs M31c | vs M29h |
|-------|-------------:|--:|-------:|--------:|--------:|
| **Full** | **22974 / 49998** | **46.1%** | **+174** | **+3845** | **+1191** |
| language | 15581 / 23899 | 65.2% | −591 | up | — |
| built-ins | 6767 / 23521 | 28.8% | **+759** | up | up |

JSON: `results/test262_full_m47.json` · writeup: `results/FULL_SUITE_M47.md`  
Includes M38–M47 harness.

### 2.2 OA/S product slices (M47)

| Suite | Pass / Total | % | Δ M46 | Need ~**90%** |
|-------|-------------:|--:|------:|-------------:|
| **Object** | **2464 / 3411** | **72.5%** | 0 | **~+606** |
| **Array** | **2083 / 3081** | **68.2%** | **+4** | **~+690** |
| **String** | **759 / 1223** | **62.2%** | 0 | **~+342** |

### 2.3 Recent moles

| Mole | Focus |
|------|--------|
| **M45** | array-like mutators; includes; Symbol.toStringTag |
| **M46** | ArrayLike accessor Get/Has; String ToInteger Inf/NaN |
| **M47** | **Product bar → 90% each**; ArraySpeciesCreate IsConstructor + species undef |

---

## 3. Active plan — crush to **90% each** by dependency

### Done (keep green)

- [x] UTF-16 string surface + key reclaim (M31+)  
- [x] Number ToString scientific / short form (M37)  
- [x] String unicode escapes in lexer + CreateString UTF-8 (M37)  
- [x] Function indexed props + instanceof Function/Array (M37)  
- [x] defineProperty reject before write (M38)  
- [x] ParseNumberStr on UTF-16 (M38)  
- [x] **new String index keys stable** (M39)  
- [x] **Boolean/Number/String.prototype → Object.prototype** (M39)  
- [x] **DescField accessor keys UTF-16** (M39)  
- [x] **defineProperties enumerable only** (M39)  

### Next crush order

1. **Object defineProperty residual** (`15.2.3.6-4` redefine, propertyHelper, symbols) + **gOPD**  
2. **defineProperties residual** + create/assign/keys  
3. **Array callbacks** map/filter/reduce/forEach (array-like; **not** fromAsync)  
4. **String** indexOf/slice/substring/trim residual (non-RegExp)  
5. RegExp → replace/match/search  
6. Promise polish → language reclaim → full rescore toward 95%  

### Fail mass (M39)

| Area | ~fails | Note |
|------|-------:|------|
| Object/defineProperty | 288 | redefine mass |
| Object/defineProperties | 175 | residual |
| Object/gOPD | 119 | |
| Array reduce* | ~100 ea | |
| Array fromAsync | 95 | **skip desert** |
| Array map/filter/… | 50–70 ea | |
| String replace*/match/search | high | RegExp dep |

---

## 4. Commands

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_<tag>.json
```

Prefer int. No Temporal/TA. Full suite only at milestones.
