# Language → 100% Plan (then Built-ins)

**Date:** 2026-07-29  
**Branch:** `master`  
**Tip:** **M128e7k** (PrivateMethodOrAccessorAdd double-init)  
**Full suite baseline:** M128e6ak — 60.1% overall, language **89.1%**

---

## Where things stand (backfill)

| Gate | Target | Status |
|------|--------|--------|
| **G1 language ≥90%** | ≥90% | nearly (89.1% e6ak full) |
| **G2 language ≥95%** | ≥95% | **active** (~+1.4k passes) |
| **G3 language 100%** | 100% | campaign |
| **G4 built-ins bulk** | after G2 | **blocked** |

### Done (keep green)

| Item | Score | Commit |
|------|------:|--------|
| statements/with | **181/181 (100%)** | e6al |
| class/dstr | **1920/1920 (100%)** | pre-e7 |
| Full suite overall | 60.1% | e6ak |

### Class elements grind (L-B) — active

| Milestone | elements pass/fail | runner pass% |
|-----------|-------------------:|-------------:|
| pre-e7 base | 1326 / 127 (+72 t/o) | 91.3% |
| e7i tip | 1362 / 83 (+8 t/o) | 94.3% |
| **e7j tip** | **1445 / 81 (+8 t/o)** no-batch | **94.7%** |

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

### Phase order

| Phase | Focus | Status |
|-------|-------|--------|
| L-A | class/dstr | **DONE** |
| **L-B** | class/elements residual (~96 fails) | **ACTIVE** |
| L-C | subclass / super | next |
| L-D | eval-code | next |
| L-E… | for-of, residual statements, long tail | later |

### L-B residual clusters (~81 fails)

1. Private brand / nested shadow / double-init methods  
2. Private + direct eval visibility  
3. Optional chain + private (`o?.c.#f`)  
4. Non-extensible private **methods** (fields path green)  
5. eval/supercall-in-field edges  
6. syntax edges (field get/set ASI) — prototype/constructor propname green

### Strategy

1. Language only until ≥95%  
2. Prefer engine/Ailang over shims  
3. Regression every stage: with 100%, dstr 100%, elements delta  
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
