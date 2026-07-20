# JS Engine — Plan to **90%** (full suite, all features)

**Updated:** 2026-07-20 (M65 full baseline)  
**Branch:** `gpu-45-may-baseline-restore`  
**Full baseline:** [`results/FULL_SUITE_M65.md`](./results/FULL_SUITE_M65.md) · JSON `results/test262_full_m65.json`  
**Prior:** [`results/FULL_SUITE_M47.md`](./results/FULL_SUITE_M47.md)

### Headline (M65 full 50k)

| Scope | Pass / Total | % | vs M47 |
|-------|-------------:|--:|-------:|
| **Full** | **24807 / 49998** | **49.6%** | **+1833 (+3.5pp)** |
| **Language** | **17032 / 23899** | **71.3%** | **+1451 (+6.1pp)** |
| **built-ins** | **7118 / 23521** | **30.3%** | **+351** |
| Object | 2470 / 3411 | 72.4% | +6 |
| Array | 2214 / 3304 | 67.0% | +131 |
| String | 759 / 1230 | 61.7% | ~flat |

### Recent moles (M48–M65 language reclaim)

| Mole | Fix | Slice |
|------|-----|-------|
| M48–M51b | SetFunctionName, methods/super, Array keys/entries | class / iterators |
| M52–M58 | elision, labels, for-of protocol, IteratorClose, gen.return, try/finally | for-of climb |
| M59–M63 | FRESH_LET_ENV, free-var TDZ, Map/Set live iterators | for-of → 88.5% |
| **M64/M64b** | string code points, let dstr scope, `var let`, bare `let` ASI | for-of 89.7% |
| **M65** | for-let validation scope, multi-var body, next getters, eval cptn | for-of **672/751 (90.8%)** ✅ |

**L4 for-of language gate: DONE (≥90%).** Residual ~80 fails = dstr/TA/Proxy deserts — last-mile.

---

## Goal (hard) — unchanged

| Bar | Target | **Now (M65 full)** |
|-----|-------:|-------------------:|
| **Full test262** | **≥90%** | **49.6%** |
| **Language** | **≥90%** | **71.3%** |
| **Object / Array / String** | **each ≥90%** | 72.4 / 67.0 / 61.7 |
| Product | Usable JS engine, all language features + core built-ins | marching |

**~+20k full-suite passes** still needed (~500 tests per full pp). Deserts (Temporal/TA/Atomics/Proxy) are **not** the next grind.

---

## March order (reset after for-of 90%)

```
PHASE L — Language (ACTIVE)
  L1  SetFunctionName / names          ✅ largely done (M48+)
  L2  class residual (stmt+expr ~1.8k fails)     ← biggest language fail mass
  L3  object literal / computed / methods (~225 fails @ 80.6%)
  L4  for-of / iterators / generators          ✅ for-of ≥90% (M65)
  L5  arguments-object (~45%)
  L6  async / await / for-await (~40–53%)
  L7  modules / dynamic-import (~41–51%)
        │
        ▼  language ≥ ~80–85%, then keep climbing to 90%
PHASE B — Built-ins to product bar
  B1  Object → 90%   (need +~600)
  B2  Array  → 90%   (need +~760)
  B3  String → 90%   (need +~348; RegExp-backed paths later)
  B4  Function / Promise / RegExp / Map-Set / Date basics
        │
        ▼  OA/S each ≥90%, language ≥90%
PHASE F — Full suite → 90%
  F1  remaining fail mass / controlled desert stubs
  F2  full 50k only at milestones
```

### Why this order (dependency)

| Priority | Slice | Why next |
|----------|-------|----------|
| **1. L3 object** | expr object ~81% | Feeds class methods, OA built-ins, spread/assign; smaller surface than class |
| **2. L2 class** | ~78–79% | Largest language fail mass; needs object/method/super solid |
| **3. L5 arguments** | ~45% | Call/apply/strict; unblocks many built-in tests |
| **4. L6 async** | async + for-await | Real apps; for-of protocol already green |
| **5. L7 modules** | module-code + import | Product modules after async basics |
| **6. B1–B3 OA/S** | 72/67/62% | Product bar; after language core stops thrashing |
| **Last** | Temporal / TA / Atomics / Proxy | Fail mass only; not usability-critical first |

**Optional interleave:** if a class mole needs object computed/method-def, do that object sub-mole first (L3 micro-before L2).

---

## Active focus — post-M65

| Item | Status |
|------|--------|
| for-of ≥90% | **DONE** (dedicated 672/751) |
| Full suite M65 baseline | **DONE** (49.6%) |
| **Next mole** | **L3 object expr** residual (computed names, methods, spread/assign edge, __proto__) |
| Then | L2 class fail clusters (private/static/heritage/fn-name residual) |
| Gate | midgate + object slice + class smoke |

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'language/expressions/object' -j 8
python3 tools/test262_runner.py --paths 'language/statements/class,language/expressions/class' -j 8
```

---

## Distance math (M65)

| Track | Pass | Target 90% | Still need |
|-------|-----:|-----------:|-----------:|
| Full | 24807 | ~44998 | **~+20191** |
| Language | 17032 | ~21509 | **~+4477** |
| Object | 2470 | ~3070 | **+600** |
| Array | 2214 | ~2974 | **+760** |
| String | 759 | ~1107 | **+348** |

Class reclaim alone (stmt+expr → 90%) ≈ **+1.0–1.2k language** if achievable — real full-suite pp without desert thrash.

---

## Rules

| Rule | |
|------|--|
| Goal | **90% full engine, all features** |
| Order | **Language by dependency** (object → class → args → async → modules), **then OA/S**, then deserts |
| Honesty | Generators / call / function: `--no-batch` when needed |
| Gate | Midgate green after every mole |
| Score | Report **pass deltas (+N)**; full 50k at milestones only |
| for-of residual | dstr/TA/Proxy last-mile — do not block L3/L2 |

---

## Compare ladder

| Milestone | Full % | Language % | Notes |
|-----------|-------:|-----------:|-------|
| M37 | 45.6% | 67.7% | pre OA/S thrash high |
| M47 | 46.1% | 65.2% | built-in moles; language dip |
| **M65** | **49.6%** | **71.3%** | **current**; for-of ≥90% |
