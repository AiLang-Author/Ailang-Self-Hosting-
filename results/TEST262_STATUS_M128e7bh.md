# test262 status — tip M128e7bh

**Date:** 2026-08-01  
**Tip:** `b58baa0d` — multiparts tagged templates; template-literal 100%  
**Branch:** `master`

---

## Full-suite baselines (authoritative)

| Run | Tip | Overall | Language | Built-ins | G2 gap (lang→95%) | Notes |
|-----|-----|--------:|---------:|----------:|------------------:|-------|
| **e7x** (best full) | `a7cefc59` | **61.35%** | **91.42%** (21,607/23,635) | **33.86%** | **847** | Last “healthy” full suite |
| **e7bb** (latest full) | `6dbf7744` | **58.65%** | **87.49%** (20,679/23,635) | **32.38%** | **1,775** | Optional-chain work; mass CallFunc regression |
| e7bc–e7bh | `b58baa0d` | *not re-full* | *slice-measured* | *not re-full* | *est. see below* | Regression fix + P0 chips |

**Artifacts**

| File | Role |
|------|------|
| `results/test262_full_m128e7x.json` + `_SUMMARY.md` | Best full baseline |
| `results/test262_full_m128e7bb.json` + `_SUMMARY.md` | Latest full (soft) |
| `results/test262_full_m128e7bb_KNOCKOUT.md` | P0 residual categories |
| `results/test262_full_m128e7bb_REGRESSION.md` | e7x→e7bb transitions |
| `tools/test262_baseline_report.py` | Compare two full JSON runs |

**G2 formula:** `ceil(0.95 × 23,635) − language_pass` → need **22,454** language passes.

---

## Distance to G2 (language ≥ 95%)

| | Passes still needed |
|--|--------------------:|
| From **e7x** (best full) | **~847** |
| From **e7bb** (latest full, pre-e7bc) | **~1,775** |
| From e7bb **+ measured e7bd–e7bh chips** (~+41 lang) | **~1,730** *(estimate only)* |

**Honest read:** Until a post-e7bc full language rescore, treat **e7x gap ≈ 850** as the optimistic floor and **e7bb gap ≈ 1,775** as the pessimistic ceiling. e7bc was designed to restore e7x-class CallFunc/`assert.throws` behaviour; a full re-run should land **between** those bounds (likely much closer to e7x if e7bc fully recovered the mass regression).

### Language bulk residual (from e7bb knockout — still the grind map)

| Band | Examples |
|------|----------|
| **P0 near-complete** | TCO residuals (coalesce/comma/conditional/call); eval-spread; line-terminator ASI |
| **P1** | super, try, for-of edges, logical-assignment, if |
| **P2 bulk** | `statements/class` (~1.1k residual), `expressions/class` (~600), private fields, for-of bulk |

---

## Distance to built-ins (G3-ish)

| | e7x | e7bb |
|--|----:|-----:|
| Built-ins pass | ~7,960 (33.86%) | **7,616 (32.38%)** |
| Built-ins total | 23,518 | 23,518 |
| Residual (fail+err+t/o) | ~15.5k | **~15.9k** |

**Built-ins are not the G2 target.** G2 is **language ≥ 95%**. Opening bulk Reflect/Proxy/TypedArray/Temporal **before** G2 wastes capacity (see prior plan notes).

When language is G2-ready, built-ins gap is still **~15k tests** (~67% of built-ins still non-pass at e7bb). Expect a separate multi-milestone track (G3), not a single chip.

Rough pass-rate ladder:

| Gate | Meaning | Status |
|------|---------|--------|
| **G1** | Language usable / mid-suite strong | Met long ago for large language slices |
| **G2** | Language ≥ **95%** | **Not met** — ~0.85k–1.8k language passes short |
| **G3** | Built-ins bulk open | **Blocked on G2** — ~32–34% built-ins today |

---

## Regression testing status

| Layer | Status | Cadence |
|-------|--------|---------|
| **Safety pack (no-batch)** | **Green** at e7bh: optional 38/38, new.target 14/14, array 52/52, template-literal 57/57, concat/instanceof/in/string 100% | After every engine chip |
| **Category slices** | Measured per chip; knockout list guides P0 | Continuous grind |
| **Full suite (~50k, ~50 min)** | **Stale since e7bb** (`6dbf7744`) | Next: after more P0 recovery **or** when claiming G2 distance |
| **e7x → e7bb regression** | Documented: **−928 language**, fixed 800 / regressed 1784 | Root cause: CallFunc double-delivery → **e7bc** |
| **e7bc recovery** | Targeted: instanceof/in/concat 100%; assert.throws / Array method TypeError paths improved | **Not proven by full suite yet** |

### Policy (unchanged)

1. Prefer **engine fixes**; no false greens.  
2. **No full suite burn** on every chip — use no-batch safety + knockout slices.  
3. After a **cluster of P0 wins** (or before a G2 claim), re-run:
   ```bash
   python3 tools/test262_runner.py --full -j 8 --timeout 12 \
     --output-json results/test262_full_m128e7bh.json
   python3 tools/test262_baseline_report.py results/test262_full_m128e7bh.json \
     --prior results/test262_full_m128e7x.json --label M128e7bh --tip $(git rev-parse --short HEAD)
   ```
4. Compare to **e7x** (best) and **e7bb** (last full) for regression watch.

---

## 100% chips landed e7ay–e7bh (language)

| Category | Score |
|----------|------:|
| expressions/in (private-in) | 36/36 |
| instanceof | 43/43 |
| concatenation | 5/5 |
| optional-chaining | **38/38** |
| new.target | **14/14** |
| expressions/array | **52/52** |
| expressions/delete | **69/69** |
| template-literal | **57/57** |
| literals/string (recheck) | 73/73 |

Progress log: `results/M128e7_PROGRESS.md`.

---

## Next grind

1. Prove e7bc recovery: **full suite** when ready (or language-only if runner supports it).  
2. P0: call eval-spread; break/continue line-terminators; TCO residual (or accept as long-tail).  
3. P1/P2: class/private/for-of bulk toward G2.  
4. **Do not** open built-ins bulk until language G2.
