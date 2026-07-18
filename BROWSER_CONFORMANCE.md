# Browser JS Conformance — Living Scoreboard

**Updated:** 2026-07-18 (M39)  
**Branch:** `gpu-45-may-baseline-restore`  
**Handoff:** [`results/JS_HANDOFF_M39.md`](./results/JS_HANDOFF_M39.md)  
**Plan:** [`JS-DEPENDENCY-PLAN.md`](./JS-DEPENDENCY-PLAN.md)

---

## 0. Progress reality check

| Horizon | Score | Context |
|---------|------:|---------|
| Full suite 2026-07-16 M29h **peak** | **21783 / 49998 (43.6%)** | pre–UTF-16 key regression |
| Full suite 2026-07-17 M31c | **19129 / 49998 (38.3%)** | UTF-16/`\p` + key regressions |
| **Full suite 2026-07-18 M37** | **22800 / 49998 (45.6%)** | **new high** · `results/FULL_SUITE_M37.md` |
| language (full M37) | **67.7%** | was 60.4% M31c |
| built-ins (full M37) | **25.5%** | Temporal desert still dominates |
| **Object / Array / String M39 slices** | **69.5% / 57.7% / 54.3%** | product bar 80% each |

**Long goal:** ~**95%** usable JS engine for embedded browser.  
**Near-term product gate:** Object + Array + String each **≥80%**.

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

| Track | Now (M39) | Product bar | Long |
|-------|----------:|------------:|-----:|
| **Object** | **69.5%** | **≥80%** | ≥90% |
| **Array** | **57.7%** | **≥80%** | ≥90% |
| **String** | **54.3%** | **≥80%** | ≥90% |
| **Language** | 67.7% full | ≥80% | ≥90% |
| **Full suite** | **45.6%** | ≥50% mid | **~95%** |

---

## 2. Latest scoreboard

### 2.1 Full suite M37 (authoritative high-water)

| Scope | Pass / Total | % | vs M31c | vs M29h |
|-------|-------------:|--:|--------:|--------:|
| **Full** | **22800 / 49998** | **45.6%** | **+3671** | **+1017** |
| language | 16172 / 23899 | 67.7% | +2726 | ~flat |
| built-ins | 6008 / 23521 | 25.5% | +1921 | up |

JSON on disk: `results/test262_full_m37.json` (often gitignored) · writeup: `results/FULL_SUITE_M37.md`  
**Note:** Full used **M37** harness; M38/M39 fixes not yet re-scored on full 50k.

### 2.2 OA/S product slices (M39)

| Suite | Pass / Total | % | Δ M38 | Need ~80% |
|-------|-------------:|--:|------:|----------:|
| **Object** | **2371 / 3411** | **69.5%** | +43 | **~+357** |
| **Array** | **1779 / 3081** | **57.7%** | +5 | **~+685** |
| **String** | **664 / 1223** | **54.3%** | +1 | **~+314** |

### 2.3 Recent moles

| Mole | Focus |
|------|--------|
| M31–M35 | UTF-16, defineProperty climb, wrappers, method this, String.proto |
| **M37** | Number ToString, `\u`/`\x`, Function index, instanceof Function/Array · full **45.6%** |
| **M38** | defineProperty value-after-reject; ParseNumberStr StrUnit |
| **M39** | String index slab keys; B/N/S → Object.prototype; DescField MakeAccKey; defineProperties enumerable-only; Array.length attrs |

---

## 3. Active plan — crush to 80% by dependency

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
