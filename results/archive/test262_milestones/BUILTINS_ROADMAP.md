# Path to Built-ins (after Language gates)

**Date:** 2026-07-30  
**Branch:** `master`  
**Tip at suite:** M128e7l (`cd9eea35`)  
**Full suite:** `results/test262_full_m128e7l.json` — see `test262_full_m128e7l_SUMMARY.md`

> Strategy: **language first**, then bulk built-ins. Prefer pure engine/Ailang over shims.

---

## Full suite snapshot (M128e7l) — measured

| Metric | Value |
|--------|------:|
| Tests | **49,723** |
| **Overall pass** | **30,113 / 49,723 (60.6%)** |
| **Language** | **21,298 / 23,635 (90.1%)** — **G1 met** |
| **Built-ins** | **7,967 / 23,518 (33.9%)** |
| annexB | 481 / 1,086 (44.3%) |
| staging | 367 / 1,484 (24.7%) |
| Wall | ~49.6 min (`-j 8`, timeout 12) |
| vs M128e6ak | overall 60.1% → **60.6%**; language 89.1% → **90.1%** |

---

## Gates (decision tree)

| Gate | Metric | Status after e7l full |
|------|--------|------------------------|
| **G1** | language ≥ **90%** | **DONE** |
| **G2** | language ≥ **95%** | **active** (~+1,160 language passes ≈ 95%) |
| **G3** | language **100%** | later |
| **G4** | built-ins bulk | **blocked for bulk** until G2; **limited B1 ROI allowed now** |

**Rule:** Full bulk built-ins (G4) opens when language ≥ 95%. Until then, language residual is primary; Object/Array/Function polish only when it unblocks language or is trivial.

---

## Phase A — Language G1 → G2 (primary now)

**Need:** ~**1,160** more language passes (90.1% → 95% of 23,635).

### A1 — Class residual (highest ROI)

| Cluster | Approx residual | Approach |
|---------|----------------:|----------|
| private + **direct eval** visibility | ~25 elements | Seed PrivateEnvironment in `JSVM_Eval`; allow `#name` parse; brand via `save_fp` home |
| class **subclass** / super | ~61 + subclass-builtins ~49 | L-C: super property, SuperCall edges, builtin subclass |
| elements other private | ~40 | non-extensible methods, remaining brand |
| eval-in-field / arguments early errors | ~14 | early-error completeness |
| for-of / assignment **dstr** | ~100 | L-E after class |

**Keep green:**
```bash
python3 tools/test262_runner.py --categories statements/with --timeout 10 --no-batch -j 4
python3 tools/test262_runner.py --paths language/statements/class/dstr --timeout 12 --no-batch -j 6
python3 tools/test262_runner.py --paths language/statements/class/elements --timeout 12 --no-batch -j 6
```

**Exit A:** full-suite language ≥ **95%** (or elements residual &lt; 40 no-batch and subclass &lt; 30).

---

## Phase B — Built-ins bulk (G4) — after G2

Order by **test volume × current pass% leverage** (from e7l full data).

### B1 — Foundation (start first when G4 opens; light work OK now)

| Builtin | Pass% now | Why |
|---------|----------:|-----|
| **Object** | 72.8% (2483/3411) | defineProperty / keys / freeze — cascades everywhere |
| **Function** | 60.9% (310/509) | bind/call/apply, constructor |
| **Error** hierarchy | (in Object/Function area) | assert-heavy |

### B2 — Core data

| Builtin | Pass% now | Notes |
|---------|----------:|-------|
| **Array** | 76.4% (2353/3081) | methods + from/isArray gaps |
| **String** | 62.5% (764/1223) | methods / unicode |
| **Number** / **Math** | 48% / 38% | statics completeness |
| **Boolean** | high / thin | quick win |

### B3 — Collections & async

| Builtin | Pass% now | Notes |
|---------|----------:|-------|
| **Promise** | 65.6% | all/race/any/allSettled |
| **Map** / **Set** | 44% / 33% | iterators + species |
| **Proxy** / **Reflect** | 12% / 38% | complete traps |
| **Symbol** | 10% | well-known + registry |
| **WeakMap** / **WeakSet** | 0% | after Map/Set |

### B4 — Text, binary, time (later)

| Builtin | Pass% now | Notes |
|---------|----------:|-------|
| **RegExp** | 30% | large surface; engine exists |
| **JSON** | 19% | parse/stringify |
| **Date** | 8% | timezone last |
| **TypedArray** / **ArrayBuffer** / **DataView** / **Atomics** | ~0% | after core data |
| **Temporal** | 0.8% (4588 tests) | **defer** — not product-critical |

### B5 — Global & annex

- `parseInt` / `parseFloat` / `encodeURI*` / globalThis polish  
- **annexB** / **staging** — not product gates  

---

## Phase C — Measurement cadence

| When | What |
|------|------|
| Every language cluster | with + dstr + elements (**no-batch** for elements) |
| After major tip / weekly | `--full` → SUMMARY.md |
| Before declaring G2 or G4 open | full suite required |

```bash
python3 tools/test262_runner.py --full --timeout 12 -j 8 \
  --output-json results/test262_full_<tip>.json
python3 tools/summarize_test262_full.py results/test262_full_<tip>.json \
  | tee results/test262_full_<tip>_SUMMARY.md
```

---

## Recommended grind order (next 2–4 weeks)

1. **Private + direct eval** (elements residual #1) → re-score elements no-batch  
2. **Subclass / super** (L-C) — also reduces subclass-builtins fails  
3. Full suite checkpoint → aim **language ≥ 93%** mid-gate  
4. for-of dstr + eval-code edges  
5. Full suite → **language ≥ 95% (G2)**  
6. Open **B1 Object/Function** bulk + keep language mop  

---

## Anti-goals (until G2)

- Bulk Temporal / TypedArray before language 95%  
- Runner shims that hide real engine gaps  
- Chasing staging/annexB for vanity metrics  

---

*Updated from M128e7l full suite 2026-07-30.*
