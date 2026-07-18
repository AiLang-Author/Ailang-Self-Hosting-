# JS Engine — Dependency Plan

**Updated:** 2026-07-18 (M42)  
**New session:** start at [`results/JS_HANDOFF_M42.md`](./results/JS_HANDOFF_M42.md).

**Goal:** Browser-usable JS → long **~95%** full suite.  
**Product gate (near-term):** **Object, Array, and String each ≥80%** on test262 trees.

| Rule | |
|------|--|
| Order | **Object attributes** → **Array callbacks / array-like** → **String methods (non-RegExp)** → RegExp/replace → Promise → full rescore |
| Honesty | Generators / function / call: **`--no-batch`** when needed |
| Style | **Wrap over write** — Ailang/runtime primitives; thin JS surface |
| Gate | Midgate green after every mole |
| Deserts | **Skip** Temporal, TypedArray, fromAsync until core ≥80% |
| Score | Report **pass deltas (+N)**; full 50k only at milestones |

---

## Summary (now) — 2026-07-18 post M39

> **Full suite floor (M37 harness):** **22800 / 49998 (45.6%)** — **above M29h peak 43.6%**.  
> Writeup: [`results/FULL_SUITE_M37.md`](./results/FULL_SUITE_M37.md).  
> M38/M39 not yet in a full rescore.

| Gate | Score | Notes |
|------|------:|-------|
| e2e + midgate core | **PASS** | post-M39 |
| **full (M37 harness)** | **22800 / 49998 (45.6%)** | `results/test262_full_m37.json` · wall ~33 min |
| language (full M37) | **67.7%** | was 60.4% M31c |
| built-ins (full M37) | **25.5%** | was 17.4% · Temporal still desert |
| **Object slice M42** | **2413 / 3411 (70.7%)** | need ~**+357** → 80% |
| **Array slice M42** | **1869 / 3081 (60.7%)** | need ~**+685** |
| **String slice M42** | **703 / 1223 (57.5%)** | need ~**+314** |

**Living scoreboard:** [`BROWSER_CONFORMANCE.md`](./BROWSER_CONFORMANCE.md)

---

## Dependency DAG (march to 80% → 95%)

```
┌─────────────────────────────────────────────────────────────┐
│  Object.defineProperty / gOPD / attr bits / redefine        │  ← M33–M39 in flight
│  defineProperties (enumerable only) / wrapper prototypes    │  ← M39 landed
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Array-like: String boxes (stable index keys), Function[i]  │  ← M37/M39
│  Number("n") / length string (ParseNumberStr UTF-16)        │  ← M38
│  Array callbacks: map/filter/reduce/forEach/some/every      │  ← NEXT mass
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  String methods: trim* (mostly done), indexOf, slice,       │
│  substring, split (non-RegExp) → then replace*/match/search │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  RegExp + Promise + language reclaim → full 80%+ → ~95%     │
└─────────────────────────────────────────────────────────────┘
```

**Skip until core green:** `Array.fromAsync`, Temporal, TypedArray/Atomics, Map/Set/Proxy deserts.

---

## Landed moles (M31 → M39)

| Mole | Focus | OA/S impact |
|------|--------|-------------|
| M31a–e | UTF-16 strings + key reclaim | full 38.3% floor |
| M32–M33 | defineProperty array indices, this, accessors | Object climb |
| M34–M35 | entries/fromEntries, wrappers, method this, String.proto | String +13pp |
| M36–M37 | Number ToString, unicode `\u`/`\x`, Function index, instanceof | full **45.6%** |
| **M38** | defineProperty value-after-reject; ParseNumberStr StrUnit | O+61 A+61 |
| **M39** | String index slab keys; B/N/S → Object.prototype; DescField MakeAccKey; defineProperties enumerable; Array.length attrs | O+43 |

### M39 detail (done — keep testing)

- **Slab-copy** `new String` / `Object(string)` index keys (`IntToStr` static buf)
- Re-link **Boolean/Number/String.prototype → Object.prototype** after Object install
- **DescField** accessor keys via `JSBridge__MakeAccKey` (UTF-16 field names)
- **defineProperties** only **enumerable** own keys
- **GetAttrBits** Array.length `W !E !C`; Function name/length `!W !E C`

---

## Next (crush residual)

### OA1 — Object (need ~+357)

| Bucket | Fail ~ | Work |
|--------|-------:|------|
| defineProperty | **288** | mostly `15.2.3.6-4` redefine / propertyHelper / symbols |
| defineProperties | **175** | residual after enumerable filter |
| gOPD | **119** | function name/length, array length, accessors |
| seal/freeze/create/assign/keys | ~120 | attrs + enum |

### A1 — Array (need ~+685)

| Bucket | Fail ~ | Work |
|--------|-------:|------|
| reduce / reduceRight | ~100 each | array-like, callback args, holes |
| map/filter/forEach/some/every | ~50–70 each | thisArg, species, array-like |
| fromAsync | **95** | **DESERT — skip** |
| concat / indexOf / lastIndexOf | ~50 | species, fromIndex, String boxes |

### S1 — String (need ~+314)

| Bucket | Fail ~ | Work |
|--------|-------:|------|
| replaceAll / replace / match / search | high | **RegExp dependency** |
| split / raw / locale* | medium | locale desert lower ROI |
| trimEnd / indexOf / substring / slice | medium | non-RegExp polish |

---

## Gates

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
# milestone only
python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_<tag>.json
```

| When | What |
|------|------|
| Every rebuild | midgate `--rebuild --quick` |
| While implementing | feature **slice** |
| OA/S mole done | Object + Array + String slices |
| Major milestone | full `--full` + `results/FULL_SUITE_*.md` |

Prefer int. No Temporal/TA. Full suite only at milestones.
