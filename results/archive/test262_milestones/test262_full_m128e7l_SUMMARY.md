# Full test262 regression — M128e7l (2026-07-29/30)

**Tip:** `cd9eea35` — JS M128e7l: unique `__cc_N`/`__cp_N` nested class slots  
**Harness:** `test262_harness_batch.x` (rebuilt from tip)  
**Command:**
```bash
python3 tools/test262_runner.py --full --timeout 12 -j 8 \
  --output-json results/test262_full_m128e7l.json
```
**Wall time:** 2976 s (~**49.6 min**)  
**JSON:** `results/test262_full_m128e7l.json` (~9.0 MB)

---

## Headline

| Metric | Value |
|--------|------:|
| Tests discovered | **49,723** |
| **Pass** | **30,113** |
| Fail | 18,828 |
| Error | 651 (all `harness_eof` batch flakes) |
| Timeout | 131 |
| **Overall pass rate** | **60.6%** (pass/total) |
| Runner Pass% (excl. errors in denom) | **61.5%** |

### vs prior baselines

| Baseline | Overall | Language | Built-ins | Notes |
|----------|--------:|---------:|----------:|-------|
| M127 (2026-07-25) | 57.2% | 84.2% | 32.5% | older tip |
| **M128e6ak** | **60.1%** | **89.1%** | — | prior full baseline |
| **M128e7l (this run)** | **60.6%** | **90.1%** | **33.9%** | **G1 language ≥90% met** |

**Delta vs e6ak:** +~0.5 pp overall, **+1.0 pp language** (89.1% → **90.1%**).

---

## By section

| Section | Total | Pass | Fail | Err | T/O | Pass% |
|---------|------:|-----:|-----:|----:|----:|------:|
| **language** | 23,635 | **21,298** | 1,812 | 480 | 45 | **90.1%** |
| **built-ins** | 23,518 | **7,967** | 15,342 | 132 | 77 | **33.9%** |
| annexB | 1,086 | 481 | 604 | 1 | 0 | 44.3% |
| staging | 1,484 | 367 | 1,070 | 38 | 9 | 24.7% |
| **TOTAL** | **49,723** | **30,113** | 18,828 | 651 | 131 | **60.6%** |

### Batch note
All **651 errors** are `harness_eof` (batch worker crash/restart). They are **not** counted as passes. Slice re-runs with `--no-batch` remain the source of truth for class/elements (e7l tip: **1461/65 = 95.7%** no-batch).

---

## Language areas (top by volume)

| Area | Total | Pass | Pass% |
|------|------:|-----:|------:|
| expressions | 11,029 | 10,097 | 91.5% |
| statements | 9,337 | 8,443 | 90.4% |
| module-code | 596 | 510 | 85.6% |
| literals | 534 | 427 | 80.0% |
| eval-code | 347 | 313 | 90.2% |
| identifiers | 268 | 216 | 80.6% |
| arguments-object | 263 | 248 | 94.3% |
| function-code | 217 | 209 | 96.3% |
| block-scope | 145 | 141 | 97.2% |
| import | 127 | 81 | 63.8% |

### Language residual clusters (fail+error+timeout path counts)

| Cluster | Count | Notes |
|---------|------:|-------|
| statements/class/elements | 162 | residual private/eval; no-batch ~65 fails |
| statements/class/dstr | 109 | mostly harness_eof; was 1920/1920 green |
| expressions/class/elements | 63 | mirror of statements residual |
| statements/for-of/dstr | 63 | L-E later |
| statements/class/subclass | 61 | L-C next |
| expressions/class/dstr | 37 | batch noise + edges |
| expressions/assignment/dstr | 36 | |
| subclass-builtins | ~49 | bridge to built-ins |
| import-defer | 22 | |

---

## Built-ins (top by volume)

| Builtin | Total | Pass | Pass% | Priority for G4 |
|---------|------:|-----:|------:|-----------------|
| Temporal | 4,588 | 38 | 0.8% | defer (huge/new) |
| Object | 3,411 | 2,483 | **72.8%** | **B1 first** |
| Array | 3,081 | 2,353 | **76.4%** | **B2** |
| RegExp | 1,879 | 564 | 30.0% | B4 |
| TypedArray | 1,438 | 0 | 0.0% | B4 late |
| String | 1,223 | 764 | **62.5%** | **B2** |
| Promise | 677 | 444 | 65.6% | B3 |
| Date | 594 | 46 | 7.7% | B4 late |
| Function | 509 | 310 | 60.9% | **B1** |
| Set / Map | 383 / 204 | 127 / 90 | 33–44% | B3 |
| Proxy | 311 | 37 | 11.9% | B3 |
| Math / Number | 327 / 340 | 124 / 163 | 38–48% | B2 |

---

## Gate status after this run

| Gate | Target | Status |
|------|--------|--------|
| **G1 language ≥90%** | ≥90% | **MET (90.1%)** |
| **G2 language ≥95%** | ≥95% | open (~+1.2k language passes needed) |
| **G3 language 100%** | 100% | later |
| **G4 built-ins bulk** | after G2 | **still blocked for bulk**; Object/Array already strong — limited ROI work OK |

---

## Reproduce

```bash
./ailang.x JS-tests/test262_harness.ailang -o test262_harness.x
./ailang.x JS-tests/test262_harness_batch.ailang -o test262_harness_batch.x
python3 tools/test262_runner.py --full --timeout 12 -j 8 \
  --output-json results/test262_full_m128e7l.json
python3 tools/summarize_test262_full.py results/test262_full_m128e7l.json
```
