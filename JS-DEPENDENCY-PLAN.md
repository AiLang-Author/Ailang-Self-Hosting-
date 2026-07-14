# JS Engine — Dependency-Ordered Fix Plan

**Updated:** 2026-07-14  
**Rule:** Fix in dependency order. No false greens. Mid-gate after every mole.  
**Priority:** **Compliance first**, speed later (engine starts fast enough; optimize after green mass).  
**Style:** **Wrap vs write** — prefer Ailang / existing primitives and thin JS-facing wrappers over hand-rolled C-shaped natives when the primitive already exists.

---

## Status (post M18 scorecard)

| Gate | Result | Mode |
|------|--------|------|
| e2e | **36 asserts / 0 fail** | |
| mid-gate | **e2e + core + curated PASS** | `--with-cats` informational |
| dstr `function/dstr` | **186/186** | |
| gen dstr | **372/372 (100%)** | no-batch |
| fn dstr | **372/372 (100%)** | no-batch |
| generators | **502/556 (90.3%)** | no-batch |
| function | **601/715 (84.1%)** | no-batch |
| call | **63/92 (68.5%)** | no-batch |
| mapped args | **43/43** | no-batch |
| args total | **124/263 (47%)** | no-batch |
| **default suite** | **3594/7689 (47%)** | batch, ~336s |
| **language `--all`** | **10120/23899 (42.5%)** pre-fix; **re-score after M18b** | batch |
| **full `--full`** | ~49–53k | **not run yet** |

**Timing note:** runner idle; harness workers pin cores. ~250ms/test no-batch, ~150ms batch — almost all **compile+VM**, not Python.

**Batch honesty (M18b fixed):** `JSRT_Reset` now rewinds `gval_pool`/`gval_count` (was exhausting mid-suite). Verified:
| Slice | no-batch | batch |
|-------|----------|-------|
| statements/function | 359/451 (79.6%) | **359/451 (79.6%)** |
| generators total | 502/556 (90.3%) | **502/556 (90.3%)** |

Batch dashboards are trustworthy again for these paths.

---

## Gates

```bash
python3 tools/js_midgate.py --rebuild --quick
# honest gen / function
python3 tools/test262_runner.py --categories statements/generators,expressions/generators --no-batch -j 4
# broad language (not full 50k)
python3 tools/test262_runner.py --all -j 4 --output-json /tmp/js_scorecard/language_all.json
# milestone full suite
python3 tools/test262_runner.py --full -j 4 --output-json /tmp/js_scorecard/full.json
```

**Generators / function / call: `--no-batch` for honest scores.**

---

## Strategy

1. **Compliance mass** — close deal-breaker holes (eval, function-code, compound-assign, ops, args edges).  
2. **Use primitives** — wrap Ailang/runtime facilities instead of reimplementing (bind/call already started this; continue for String/Number/ops/eval).  
3. **Speed later** — only after large green regions; startup already fine.  
4. **Foundation already paid** — FDI, nest GenNext, Function.prototype, dstr 100% unblock higher layers.

### Hot mess (default suite, volume × low %)
| Area | Pass% (default batch) | Next approach |
|------|----------------------|---------------|
| eval-code | ~1% | wrap eval pipeline / re-entry; don't hand-roll |
| function-code | ~9% | strict / code paths on Function foundation |
| statementList | ~0% | parse/compile gap |
| compound-assignment + arith/compare | 20–40% | opcode/primitives, not new infra |
| arguments-object (non-mapped) | weak | gen trailing-comma + edges |
| async/await | thin | after sync function solid |

### Strong now
control flow, keywords, **dstr 100%**, **gens 90%**, **function 84%**, mapped args 100%.

---

## March forward

### Done
| Mole | Outcome |
|------|---------|
| **15–16** | dstr 186/186, mapped 43/43 |
| **17a–c** | GenNext / assign clobber / FDI+nest → gen dstr **372/372** |
| **18** | Function.name/length + call/apply/bind + gen proto → gens **502/556** |

### Residual gen (~54)
yield-as-ident / yield* ASI; forbidden-ext; scope/unscopables; TDZ defaults; proto descriptors.

### Next (compliance order)
1. Finish scorecard: language `--all` → then **`--full` (~49k)** at milestone.  
2. Attack hot mess with **wrap-first** (eval, ops, compound-assign).  
3. Call leftovers + function residual.  
4. Speed pass only after big green chunks.

---

## Progress log

| Milestone | Notes |
|-----------|-------|
| M16 | mapped 43/43 |
| M17a–c | gens → **473/556**, gen dstr **372/372** |
| M18 | Function proto surface → **502/556**; scorecard started |
| Scorecard 2026-07-14 | default **47%**; function **84%** no-batch; call **69%**; language-all **42.5%** batch (under-reports stmt gens/func) |

---

## Agent rules

1. Mid-gate green after every mole.  
2. Generators/function/call: `--no-batch` for honest scores.  
3. Update this file when a mole closes.  
4. Language smells → `AILANG-WARTS.md`.  
5. **Compliance > speed.** Prefer **wrap over write**.
