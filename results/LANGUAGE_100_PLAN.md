# Language → 100% Plan (then Built-ins)

**Date:** 2026-07-30  
**Branch:** `master`  
**Tip:** **M128e7m** (private visible to direct eval) (unique `__cc_N` nested class slots)  
**Full suite baseline:** **M128e7l** — **60.6%** overall, language **90.1%**  
**Prior:** M128e6ak — 60.1% / lang 89.1%

---

## Where things stand

| Gate | Target | Status |
|------|--------|--------|
| **G1 language ≥90%** | ≥90% | **MET** (90.1% e7l full) |
| **G2 language ≥95%** | ≥95% | **active** (~+1.16k language passes) |
| **G3 language 100%** | 100% | campaign |
| **G4 built-ins bulk** | after G2 | **blocked** (see `BUILTINS_ROADMAP.md`) |

### Done (keep green)

| Item | Score | Commit |
|------|------:|--------|
| statements/with | **181/181 (100%)** no-batch | e6al |
| class/dstr | **1920/1920 (100%)** no-batch | pre-e7 |
| Full suite overall | **60.6%** | e7l full |
| Full suite language | **90.1%** | e7l full |

### Class elements grind (L-B) — active

| Milestone | elements pass/fail | runner pass% |
|-----------|-------------------:|-------------:|
| pre-e7 base | 1326 / 127 (+72 t/o) | 91.3% |
| e7i tip | 1362 / 83 (+8 t/o) | 94.3% |
| e7j tip | 1445 / 81 (+8 t/o) no-batch | 94.7% |
| e7k tip | 1449 / 77 (+8 t/o) no-batch | 95.0% |
| e7l tip | 1461 / 65 (+8 t/o) no-batch | 95.7% |
| **e7m tip** | **1467 / 59 (+8 t/o)** no-batch | **96.1%** |

### Commits this campaign (master → github)

| Commit | Summary |
|--------|---------|
| e6al | with 100% |
| e6ak | full suite baseline 60.1% |
| **e7** | field_init free-var GET_FREE |
| **e7b** | static field `this`; Proxy define/get |
| **e7c** | private method not-writable |
| **e7d** | static `constructor()` method; PrivateFieldAdd TypeErrors |
| **e7j** | class `.prototype` !W; static `['constructor']` field attrs |
| **e7k** | PrivateMethodOrAccessorAdd on construct; double-init TypeError |
| **e7l** | unique `__cc_N`/`__cp_N` — nested class in static fields |
| **e7l full** | full suite 60.6% / lang 90.1% — G1 |

### Phase order

| Phase | Focus | Status |
|-------|-------|--------|
| L-A | class/dstr | **DONE** |
| **L-B** | class/elements residual (~65 no-batch) | **ACTIVE** |
| **L-C** | subclass / super | next (61+ fails in full) |
| L-D | eval-code / private+direct eval | next (ROI) |
| L-E… | for-of dstr, residual statements | later |
| **G4** | built-ins bulk | after G2 — plan in `BUILTINS_ROADMAP.md` |

### L-B residual clusters (~65 fails no-batch)

1. Private + **direct eval** visibility  
2. Non-extensible private methods / remaining brand edges  
3. eval/supercall-in-field / arguments early errors  
4. Nested private static — **usage/shadow green** (e7l)  
5. Double-init private methods — **green** (e7k)  

### Strategy

1. Language until ≥95% (G2), then bulk built-ins  
2. Prefer engine/Ailang over shims  
3. Regression: with 100%, dstr 100%, elements no-batch; full suite on major tips  
4. Commit + push on green clusters  


```bash
python3 tools/test262_runner.py --categories statements/with --timeout 10 --no-batch -j 4
python3 tools/test262_runner.py --paths language/statements/class/elements --timeout 12 -j 8
```

---

## Progress log

| Date | Slice | Score | Notes |
|------|-------|------:|-------|
| 2026-07-29 | with | 181/181 | e6al |
| 2026-07-29 | full | 60.1% / lang 89.1% | e6ak |
| 2026-07-29 | class/dstr | 1920/1920 | L-A done |
| 2026-07-29 | elements base | 1326 pass | pre-e7 |
| 2026-07-29 | M128e7 field free-var | +25-ish | in_field_init |
| 2026-07-29 | M128e7b static this + Proxy | merged ~1404/1534 true | |
| 2026-07-29 | M128e7c private method !W | not-writable green | |
| 2026-07-29 | M128e7d static ctor + PFA | **1350/96 (93.4%)** | tip |
| 2026-07-29 | M128e7e optional chain cont. | elements 1351/95 | o?.c.#f short-circuit |
| 2026-07-29 | M128e7g private setter-only get | **1356/90 (93.8%)** | +5; TypeError no getter |
| 2026-07-29 | M128e7h private setter placeholder | **1357/89** | static missing getter |
| 2026-07-29 | M128e7i computed `#` + PRIVATE div | **1362/83 (94.3%)** | +7 clobber/visibility |
| 2026-07-29 | M128e7j class prototype !W + ctor field | **1445/81 (94.7%)** nb | static `['prototype']` TypeError; static `['constructor']` enumerable; stamp after MakeConstructor |
| 2026-07-29 | M128e7k private method install on construct | **1449/77 (95.0%)** nb | PrivateMethodOrAccessorAdd; double-init TypeError; brand fdesc check |
| 2026-07-29 | M128e7l unique class temp slots | **1461/65 (95.7%)** nb | nested static field class no longer clobbers `__cc__` |
| 2026-07-30 | **full suite M128e7l** | **60.6% / lang 90.1%** | 30113/49723 pass; built-ins 33.9%; **G1 met**; +0.5pp vs e6ak |
| 2026-07-30 | M128e7m private+direct eval | **1467/59 (96.1%)** nb | PrivateEnv seed; eval code switch; field_define clear |
