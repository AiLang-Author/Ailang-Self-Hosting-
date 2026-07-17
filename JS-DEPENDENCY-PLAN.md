# JS Engine — Dependency Plan

**Updated:** 2026-07-17 (post full-suite M31c + UTF-16 key reclaim)  
**Goal:** Browser-usable JS: language mass + **core built-ins** honesty. Full test262 100% is multi-phase; see **`BROWSER_CONFORMANCE.md`**.

| Rule | |
|------|--|
| Order | Fix **dependencies first** (UTF-16 key correctness → language reclaim → **Object/Array/String** → Promise → RegExp depth → modules/async residual) |
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

**Report both:**
- **Browser-track core:** Object + Array + String + Function + Number + Math + JSON + Error + Promise (exclude Temporal/TA/Map/Set).  
- **Full suite** for honesty.

### Priority DAG

```
[R0] UTF-16 property-key correctness     ← active (M31d+)
        │  gOPD / FuncPropGet-Set / ObjHas / MakeAttrKey /
        │  defineProperty accessors / ObjKeys / GlobalHash
        │
        ├─► [R1] Reclaim language class + method name/attrs
        │         statements/class + expressions/class ≥70%+
        │
        ├─► [R2] Reclaim Object property model
        │         defineProperty / create / keys / freeze-seal
        │         Object ≥50%+ (toward prior 54%)
        │
        ├─► [R3] Array + String spine
        │         Array ≥48%+; String method honesty
        │
        └─► [R4] Promise residual + RegExp depth
                  (P1 lookbehind / named; P3 set algebra; Script \p later)

Defer: Temporal, TypedArray, Map/Set, Proxy, full UCD, modules mass
```

| Pri | Work | Why | Success signal |
|-----|------|-----|----------------|
| **R0** | Finish **UTF-16 key** audit (no GetByte-as-C on prop names) | Unblocks class/Object/verifyProperty mass | midgate green; `gOPD(fn,"name")` + hasOwn; Object.keys enum bits |
| **R1** | **Class reclaim** | Largest language drop (~1171 pass→fail in full Δ) | class combined **≥70%** |
| **R2** | **Object reclaim** | defineProperty/create/keys | Object **≥50%** slice; defineProperty climb |
| **R3** | **Array/String** residual | Product + score | Array **≥48%**; String methods no UTF-16 corruption |
| **R4** | **Promise + RegExp** | Browser track | Promise **≥25%**; RegExp **≥35%** full-run |
| **R5** | Full rescore | Honest baseline after R0–R2 | full **≥42%** (recover toward M29h) |

### R0 checklist (implementation)

Already landed M31d (partial):
- [x] gOPD `name` / `length` / `prototype` via `StrEq`
- [x] `FuncPropGet` fixed slots via `StrEq`
- [x] `FuncPropSet` / `ObjHas` function+array length
- [x] `MakeAttrKey` / GetAttrBits / defineProperty `__get_`/`__set_` builders
- [x] GlobalHash unit hash; ObjKeys/OwnNames StrUnit + no double-CreateString
- [ ] Exhaust remaining Dispatch `GetByte(cpay)` only for **const-pool C** keys (OK); document
- [ ] propertyHelper-heavy name tests (arrow `name.js`) still need helper/include path — track separately
- [ ] Regression pack green before next full run

### Built-ins honesty table (post-M31c full run)

| Built-in | Pass / Total | % | Notes |
|----------|-------------:|--:|-------|
| Object | 1246 / 3411 | 36.6% | reclaim R2 |
| Array | 1337 / 3081 | 43.7% | close to prior ~49% |
| String | 336 / 1223 | 27.5% | more surface than early |
| Function | 139 / 509 | 27.5% | name/length attrs |
| Promise | 152 / 677 | 22.5% | |
| RegExp | 518 / 1879 | 27.8% | `\p`/`v` landed; more to go |
| Number | 74 / 340 | 21.8% | |
| Math | 64 / 327 | 19.6% | |
| JSON | 20 / 165 | 12.3% | |
| Temporal | 36 / 4588 | 0.8% | **defer** |
| TypedArray+ctors | 0 / ~2.1k | 0% | **defer** |
| Map/Set/Proxy | 0 | 0% | **defer** |

---

## RegExp / Unicode (status — not the primary bottleneck now)

| Pri | Target | Status |
|-----|--------|--------|
| P0 UTF-16 | DONE M31a | |
| P2 `\p` BMP | DONE M31b–c | GC generated stable; property-escapes **202/613** |
| P3 unicodeSets | Surface M31c | **68/152**; deepen set algebra later |
| P1a/b lookbehind/dups | Residual | Parallel when reclaim stable |

Do **not** pour into Script `\p` or full UCD until R0–R2 recover language/Object.

---

## Done recently

- **M31a** UTF-16 strings  
- **M31b–c** `\p`/`\P` + unicodeSets surface  
- **M31c full suite** baseline 38.3%  
- **M31d+** UTF-16 key reclaim (gOPD / FuncProp / ObjHas / attr keys)

---

## Optional next after reclaim

M23 eval-code; M25 for-of residual; M27 modules; M28 for-await-of; Promise/RegExp depth.
