# JS Engine — Dependency Plan

**Updated:** 2026-07-17 (Object/Array/String **≥80%** product bar)  
**New session:** start at [`results/JS_HANDOFF_M32.md`](./results/JS_HANDOFF_M32.md).

**Goal:** Browser-usable JS. **Product gate:** **Object, Array, and String each ≥80%** on test262. Full suite 100% is multi-phase; see **`BROWSER_CONFORMANCE.md`**.

| Rule | |
|------|--|
| Order | UTF-16 keys → **Object.defineProperty** → **Array callbacks** → **String methods** → polish to 80% → Promise/RegExp → full rescore |
| Honesty | Generators / function / call: **`--no-batch`**. Batch OK after M18b (gval rewind). |
| Style | **Wrap over write** — use Ailang/runtime primitives; thin JS surface |
| Gate | Midgate green after every mole |
| Score | Report **pass deltas (+N)** and **browser-track** (language + core built-ins); full 50k % is trailing |

---

## Summary (now) — 2026-07-17 post M31c full suite

> **Honest floor:** Full suite **19129 / 49998 (38.3%)** after M31a–c (UTF-16 + `\p`/`v`). That is **−2654** vs M29h peak **21783 (43.6%)**.  
> **Not** “RegExp failed” — **UTF-16 property-key regressions** hit language/class + Object attribute mass. RegExp/String still **gained** in places.

| Gate | Score | Notes |
|------|------:|-------|
| e2e + midgate core | **PASS** | post-M31d key fixes |
| **full `--full` (M31c harness)** | **19129 / 49998 (38.3%)** | `/tmp/test262_full_m31c.json` · wall ~34 min @ 8w |
| language | **14446 / 23899 (60.4%)** | was **68.2%** M29h · Δ **−1864** |
| built-ins | **4087 / 23521 (17.4%)** | was **20.6%** · Δ **−761** · Temporal/TA desert still dominate denominator |
| Object (full-run) | **1246 / 3411 (36.6%)** | was **53.9%** · reclaim in progress (M31d) |
| Array (full-run) | **1337 / 3081 (43.7%)** | was ~49% |
| String (full-run) | **336 / 1223 (27.5%)** | mixed; more surface than early M30a |
| Promise (full-run) | **152 / 677 (22.5%)** | |
| RegExp (full-run) | **518 / 1879 (27.8%)** | property-escapes / `v` motion; remeasure after reclaim |
| class (stmt+expr, post-M31d slice) | **~62.5%** combined | was ~75% M29h · reclaim target |

**Living scoreboard:** [`BROWSER_CONFORMANCE.md`](./BROWSER_CONFORMANCE.md) · suite writeup: [`results/FULL_SUITE_M31c.md`](./results/FULL_SUITE_M31c.md)

---

## Gates

```bash
python3 tools/js_midgate.py --rebuild --quick
# UTF-16 key reclaim regression pack
python3 tools/test262_runner.py --paths \
  'language/expressions/arrow-function,built-ins/Object/defineProperty,built-ins/Object/create,built-ins/Function/prototype' \
  -j 6
# core built-ins spine
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
# milestone
python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_<tag>.json
```

### Regression cadence

| When | What |
|------|------|
| Every rebuild | `js_midgate.py --rebuild --quick` |
| While implementing | Feature **slice** |
| UTF-16 key touch | **name / gOPD / hasOwn / defineProperty / create / class** slices |
| Major milestone | Full `--full` + `results/FULL_SUITE_*.md` |

---

## Targeted plan (now) — reclaim first, then built-ins

### Why built-ins look “way behind”

1. **Denominator desert:** Temporal (~4.6k @ ~0%), TypedArray/Map/Set/Proxy/Atomics (~0) sit in `built-ins` and crush the %.  
2. **Real regression:** Object/Array attribute model and class method descriptors broke when JS string keys became UTF-16 while many paths still used `GetByte` / `StringLength` as if keys were C strings.  
3. **True gaps:** Math/JSON/Number depth, Promise edges, String methods, collections — multi-phase even after reclaim.

**Product bar (agreed):** **Object, Array, and String each ≥80%** on their test262 trees to be browser-useful.  
Everything else (Promise/RegExp polish, class reclaim, full %) supports that bar.

**Report both:**
- **Browser-track:** Object + Array + String (primary) + Function + Promise + RegExp  
- **Full suite** (Temporal/TA still desert drag)

### Math to 80% (M31c full denominators)

| Built-in | Now (full M31c) | Post-M31e slice | Need for 80% | Gap (passes) |
|----------|----------------:|----------------:|-------------:|-------------:|
| **Object** | 1246/3411 (36.5%) | **1486 (43.6%)** | ~2729 | **~+1240** |
| **Array** | 1337/3081 (43.4%) | **1408 (46.1%)** | ~2465 | **~+1060** |
| **String** | 336/1223 (27.5%) | **359 (29.4%)** | ~979 | **~+620** |

This is **multi-mole**, not one patch. UTF-16 key reclaim is **necessary but not sufficient**.

### Fail-mass map (where the points are)

**Object (~1480 fails to close):**
| Bucket | Fail ~ | Pass% | Work |
|--------|-------:|------:|------|
| defineProperty | **804** | 29% | attribute model, accessors, redefinition, ToPropertyDescriptor edges |
| defineProperties | **473** | 25% | same + multi-prop order |
| prototype | 182 | 27% | toString/hasOwn/valueOf/isPrototypeOf |
| create | 153 | 52% | props bag + descriptors |
| getOwnPropertyDescriptor | 143 | 54% | attrs + function name/length |
| assign / entries / values / fromEntries | ~95 | low | copy + enum + coercion |
| seal/freeze/preventExt | ~90 | mid | integrity |

**Array (~1120 fails to close) — almost all `Array/prototype`:**
| Method family | Fail ~ | Notes |
|---------------|-------:|-------|
| reduce / reduceRight | ~280 | callback args, holes, array-like, species |
| map / filter / forEach / some / every | ~450 | same callback contract |
| indexOf / lastIndexOf / includes | ~170 | SameValueZero, fromIndex |
| splice / slice / concat | ~210 | **sparse** + species + generic |
| sort | 40 | comparefn + ToString |
| push/pop/shift/unshift | ~80 | length / extensible |
| ES2023: toSpliced/with/toSorted/toReversed/at | ~100 | **missing surface** |
| from / of / fromAsync | ~140 | from partial; fromAsync absent |

**String (~640 fails to close) — almost all `String/prototype`:**
| Method family | Fail ~ | Notes |
|---------------|-------:|-------|
| split | 100 | regex + limit + UTF-16 |
| trim / trimStart / trimEnd | ~110 | unicode whitespace |
| replace / replaceAll | ~70 | regex + functional + global |
| substring / slice | ~70 | index clamp |
| match / search / matchAll | ~80 | RegExp coupling |
| case maps + locale* | ~90 | full Unicode casefold optional |
| includes/startsWith/endsWith/indexOf | ~90 | position + search string |
| valueOf / toString / at / normalize | ~50 | boxing + missing |

### Priority DAG (Object / Array / String = product)

```
[R0] UTF-16 keys (gOPD/attrs)          ✓ M31d–e, finish edges
        │
        ├─► [OA1] Object.defineProperty + defineProperties   ← largest Object mass
        │         accessors, [[DefineOwnProperty]], !configurable
        │
        ├─► [OA2] Object.create / gOPD / keys / assign
        │
        ├─► [A1] Array callback methods (map/filter/reduce*/forEach/some/every)
        │         array-like, holes, thisArg, species light
        │
        ├─► [A2] Array mutation/slice/concat/splice + length
        │
        ├─► [S1] String split/slice/substring/indexOf/includes family
        │
        ├─► [S2] String replace/replaceAll + match/search (RegExp)
        │
        ├─► [A3/S3] Missing surface: Array.at/to*; String.at/replaceAll completeness
        │
        └─► [R5] Full rescore — Object/Array/String each ≥80% gate

Parallel: class reclaim (unblocks method descriptors) when OA1 needs it.
Defer: Temporal, TypedArray, Map/Set, full locale casefold, fromAsync.
```

| Phase | Work | Gate (slice) |
|-------|------|----------------|
| **OA1** | Object defineProperty / defineProperties honesty | defineProperty **≥70%** of 1131; defineProperties **≥60%** |
| **OA2** | create, gOPD, keys, assign, integrity | Object overall **≥65%** |
| **OA3** | remaining Object (entries/values/fromEntries/symbols) | Object **≥80%** |
| **A1** | callback methods hole/array-like/thisArg | map+filter+reduce* combined **≥75%** |
| **A2** | splice/slice/concat/sort/push family | Array overall **≥70%** |
| **A3** | `at`, `to*`, of/from polish | Array **≥80%** |
| **S1** | index/slice/split/includes/starts/ends | those methods **≥70%** each |
| **S2** | replace/replaceAll/match/search/trim* | String overall **≥65%** |
| **S3** | boxing toString/valueOf, at, pad, remaining | String **≥80%** |

### Gates (run every mole)

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object/defineProperty' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Object' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Array/prototype' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Array' -j 8
python3 tools/test262_runner.py --paths 'built-ins/String/prototype' -j 6
python3 tools/test262_runner.py --paths 'built-ins/String' -j 6
# milestone only when Object AND Array AND String slices all ≥80%
python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_<tag>.json
```

### Built-ins honesty table

| Built-in | Full M31c | Post-M32 slice | Bar |
|----------|----------:|---------------:|-----|
| **Object** | 36.5% | **62.5%** (defineProperty **~68%**) | **≥80%** |
| **Array** | 43.4% | **52.6%** | **≥80%** |
| **String** | 27.5% | **32.4%** | **≥80%** |
| Function | 27.5% | — | support attrs |
| Promise | 22.5% | — | after OA/S |
| RegExp | 27.8% | ~27.7% | after OA/S |
| Temporal / TA / Map | ~0% | — | **defer** (not in 80% bar) |

---

## RegExp / Unicode (parked under OA/S)

| Pri | Target | Status |
|-----|--------|--------|
| P0 UTF-16 | DONE M31a | |
| P2 `\p` BMP | DONE M31b–c | property-escapes **202/613** |
| P3 unicodeSets | Surface M31c | **68/152** |
| P1 lookbehind/dups | Residual | after Object/Array/String climb |

---

## Done recently

- **M31a–c** UTF-16, `\p`, unicodeSets surface; full suite **38.3%**  
- **M31d–e** property-key reclaim; Object **36→44%** slice, Array **43→46%**, String **27→29%**

## Next mole (start here)

1. **OA1** — Object.defineProperty attribute / accessor redefinition (largest single fail bucket).  
2. **A1** — Array callback contract (holes + array-like) — shared infrastructure for half of Array fails.  
3. **S1** — String split + slice/substring + includes family (high product value, bounded surface).
