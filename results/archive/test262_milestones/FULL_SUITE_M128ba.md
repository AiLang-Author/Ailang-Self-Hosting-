# Full test262 suite — M128ba

**Date:** 2026-07-26  
**Branch:** `gpu-45-may-baseline-restore`  
**JSON:** `results/test262_full_m128ba.json`  
**Log:** `results/test262_full_m128ba.log`  
**Dynimp tip:** 898/941 (95.6%) — `results/test262_dynimp_m128ba.json`

```bash
./ailang.x JS-tests/test262_harness.ailang -o test262_harness.x
./ailang.x JS-tests/test262_harness_batch.ailang -o test262_harness_batch.x
python3 tools/test262_runner.py --full -j 8 --timeout 15 \
  --output-json results/test262_full_m128ba.json
```

**Wall time:** ~47.8 min (2866 s) · **Workers:** 8 · **Mode:** batch  
**Discovered:** 49 723 tests

---

## Headline

| Metric | M128ba | M110 baseline | Δ |
|--------|--------|---------------|---|
| **Pass** | **25 676 / 49 723 (51.6%)** | 28 291 / 49 998 (56.6%) | **−4.95 pp** (−2 615 net on common) |
| Fail | 23 834 | — | |
| Timeout | 153 | — | |
| Error | 60 | — | |

Common tests vs M110: **regressed 4 649**, **improved 2 062** (net −2 587).

---

## By top area

| Area | Pass | Total | Rate |
|------|-----:|------:|-----:|
| **language** | 17 332 | 23 635 | **73.3%** |
| built-ins | 7 589 | 23 518 | 32.3% |
| annexB | 502 | 1 086 | 46.2% |
| staging | 253 | 1 484 | 17.0% |

**Language total (paths under `language/`):** ~17 798 / 24 480 (**72.7%**) toward the 95% language goal.

---

## Language highlights (where we ground)

| Slice | Notes |
|-------|--------|
| **dynamic-import** | **improved +447** vs M110; suite slice **898/941 (95.6%)** |
| **eval-code** | improved +342 / regressed −98 (net strong) |
| **module-code** | improved +348 / regressed −56 |
| **import** | improved +538 / regressed −9; slice ~92/127 (72%) |
| **expressions** | improved +610 overall; dynamic-import clean |

### Language residual (full suite language/*)

| Subdir | Pass rate (approx) |
|--------|-------------------|
| expressions | 86.9% |
| statements | **54.2%** ← hole |
| eval-code | 81.6% |
| module-code | 83.4% |
| import | 74.8% |
| block-scope | 96.6% |
| identifiers | 91.0% |

---

## Critical regression: `language/statements/class`

| | Count |
|--|------:|
| **Regressed vs M110** | **~3 045** |
| for-await-of regressed | 126 |
| Other statements | smaller |

Class regressions dominate the full-suite drop. These are **not** explained by dynimport runner shims alone — they track **harness rebuild from a dirty engine tree** (class/async/Promise work in flight). **Next grind priority after dynimp: restore class pass rate.**

Sample fail families: `accessor-name-inst/*`, `accessor-name-static/*`, computed names, for-await-of edges.

---

## Built-ins (deferred per plan)

Top fail volumes: Temporal (4.5k), TypedArray (1.4k), RegExp (1.4k), Object, Array, Date, DataView, String, Promise, …

Built-ins net vs M110: regressed 524 / improved 410.

---

## Dynimp residual after M128ba (~41 fails)

- `with` syntax (~18)
- import-attributes 2nd-param remainder (~10) — **non-object TypeError now green**
- import-defer behavioral (5)
- nested NS defineOwn / props (4)
- root: custom-primitive, import-errored-module, eval-self-once, timeouts

---

## Takeaways

1. **Dynamic-import ≥95% achieved** (suite + full-suite improvements).  
2. **Full suite headline regressed** mainly from **`statements/class` (~3k)** — must triage before claiming language 95%.  
3. **Eval / modules / import** net improved vs M110.  
4. Path to language 95%: restore class → push statements → finish import defer/bytes → with → broader expression residual; built-ins later.

---

## Root cause of the huge class regression (A/B confirmed)

**Not dynimport runner shims alone.** Confirmed 2026-07-26:

| Harness build | `class C {}` smoke |
|---------------|--------------------|
| **Committed HEAD (M126)** `git stash` of dirty Browser libs | **PASS** |
| **Dirty tree** (uncommitted M128 eval + dynimp + Promise + CallFunc, …) | **FAIL** (`VM error`, parse/compile OK) |

**Mechanism:**
1. Dynimp/eval work lived only as a **large dirty working tree** (~+3.4k lines across 15 `Librarys/Browser/*` files), never committed as gated milestones.
2. Full suite required **rebuilding** `test262_harness*.x` from that tree.
3. That bake-in pulled **all** uncommitted engine changes (eval, free-var, Promise.prototype then, CallFunc depth, async RETURN adopt, IMPORT_DYN, …).
4. Something in that bundle **breaks class declaration evaluation** (even bare `class C {}` → VM error ~420 steps). Failure mode is **uniform `vm_error`**, not parse/compile.
5. M110 full suite (~90% class) was run with a harness built from a **class-green tip** (`04ebcd7d` era), not this dirty stack.

**Why full-suite % fell while dynimp rose:** dynimp/eval/modules **improved** on common tests (+2k), but class alone **regressed ~3k** → net full-suite −2.6k.

### How to avoid next time

1. **Slice gates before rebuild-for-full:** after any engine change that needs a harness rebuild, always run:
   ```bash
   python3 tools/test262_runner.py --paths language/statements/class -j8 --timeout 10
   python3 tools/test262_runner.py --paths language/expressions/dynamic-import -j8 --timeout 15
   python3 tools/test262_runner.py --paths language/eval-code -j8 --timeout 15
   ```
   Fail the change if class drops more than a small budget (e.g. −20 tests).

2. **Commit (or worktree) milestones:** land eval / dynimp / Promise on branches or commits with green class+eval+dynimp; do not accumulate multi-thousand-line dirty engines.

3. **Separate harness pins:** keep a known-good `test262_harness_m110.x` (or build from tag) for comparison; never overwrite without a class smoke.

4. **Bisect dirty stack:** `git stash` / worktree rebuild is enough to prove “dirty vs HEAD”; then bisect files (CompStmt, Dispatch, Bridge, Builtins) for the class VM error.

5. **Full suite only after slice gates** — not as the first discovery of a 3k regression.

## Next actions

1. **Restore class** on dirty tree (bisect CompStmt/Dispatch/Bridge/Builtins vs HEAD).  
2. Re-run `language/statements/class` slice → target ≥85–90%.  
3. Re-run language + optional full suite.  
4. Continue import-defer + dynimp residual.
