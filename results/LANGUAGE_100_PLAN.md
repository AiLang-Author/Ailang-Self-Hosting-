# Language → 100% Plan (then Built-ins)

**Date:** 2026-07-29  
**Branch:** `master`  
**Tip:** e6al (with 100%) + full suite M128e6ak baseline  
**Active grind:** M128e7 class field_init free-var → elements residual  

---

## Goals

| Gate | Target | Baseline (e6ak full) | Status |
|------|--------|---------------------:|--------|
| **G1 language ≥90%** | ≥90% | **~89.1%** | nearly |
| **G2 language ≥95%** | ≥95% | ~89% | **active** |
| **G3 language 100%** | 100% | ~2.5k fails | **campaign** |
| **G4 built-ins bulk** | after G2/G3 | 33.8% | **blocked** |

### Math (language ~23.6k tests)

| Target | Approx passes needed | From ~89% |
|--------|---------------------:|-----------|
| 95% | ~22.45k | **~+1.4k** |
| 100% | all | **~+2.6k** |

---

## Strategy

1. **Language only** until ≥95% (ideally 100% core); no Temporal/TypedArray bulk.
2. **Dependency order** below; measure after every stage.
3. **Slices:** class elements / dstr / subclass; regression: `statements/with` + dstr.
4. **Prefer engine/Ailang** over runner shims.
5. **Commit + push** when a cluster moves and regressions stay green.

### Regression watch (every stage)

```bash
# must stay 100%:
python3 tools/test262_runner.py --categories statements/with --timeout 10 --no-batch -j 4
# dstr must stay 100% (1920):
python3 tools/test262_runner.py --paths statements/class/dstr --timeout 12 -j 8
# cluster under test:
python3 tools/test262_runner.py --paths statements/class/elements --timeout 12 -j 8
```

---

## Phase order

### L-A — Class dstr — **DONE** (1920/1920)

| Order | Work | Status |
|------:|------|--------|
| A1–A4 | Method/gen/async/static/ctor dstr | **100%** |

### L-B — Class elements — **ACTIVE** (~91%, ~206 residual)

| Order | Work | Status |
|------:|------|--------|
| B1 | Public instance fields + free-var in field_init | **M128e7 in flight** |
| B2 | Public static fields | next |
| B3 | Private `#` fields/methods | residual bulk |
| B4 | Static blocks / computed residual | residual |

**Known B1 fix (M128e7):** `in_field_init` forces free-var GET_FREE/SET_FREE
(not outer script GET_LOCAL). Field-init only has local 0 = `this`.
CONSTRUCT path: clean rethrow + pop frame on field-init abort.

### L-C — Subclass / super (~90+ + expressions/super)

| Order | Work |
|------:|------|
| C1 | `extends` + SuperCall |
| C2 | `super.prop` / `super[prop]` |
| C3 | subclass-builtins |

### L-D — Eval-code (~189)

direct then indirect (env, strict, new.target).

### L-E — Iteration + residual statements

for-of, for-in, try, variable/let-const edges.

### L-F — Syntax edges

regexp language, yield/generators, tagged-template, modules TLA/import-defer.

### L-G — Long tail → 100%

global-code, function-code, operators, using (if required).

---

## Defer

| Area | Why |
|------|-----|
| built-ins bulk | After language 95%+ |
| staging / annexB | Optional |
| decorators | Tiny + proposal edge |

---

## Done (keep green)

| Item | Score |
|------|------:|
| statements/with | **181/181 (100%)** e6al |
| class/dstr | **1920/1920 (100%)** |
| block-scope | ~97% |
| arguments-object | ~94% |
| Full suite overall | 60.1% e6ak |
| language | 89.1% e6ak |

---

## Current grind

**Active:** L-B class/elements residual (private bulk ~122 fails)  
**Next:** private methods/fields → L-C subclass/super → L-D eval-code  
**Commit series:** M128e7, M128e7b…  

### Fail mass (e6ak full language)

| Fails | Folder |
|------:|--------|
| ~753 | statements/class (dstr green; elements/subclass residual) |
| ~173 | expressions/class |
| ~189 | eval-code |
| ~94 | statements/for-of |
| ~70 | literals/regexp |
| residual | yield, assignment, import-defer, using, …

---

## Progress log

| Date | Slice | Score | Notes |
|------|-------|------:|-------|
| 2026-07-29 | with | 181/181 | e6al |
| 2026-07-29 | full | 60.1% / lang 89.1% | e6ak |
| 2026-07-29 | class/dstr | 1920/1920 | L-A done |
| 2026-07-29 | class/elements base | 1326/1534 (~86.4% pass; +timeouts) | pre-e7 |
| 2026-07-29 | class/elements e7 probe | 1328/1534 | partial free-var |
| 2026-07-29 | M128e7 field_init free-var | *measuring* | in_field_init + CONSTRUCT abort |
| 2026-07-29 | M128e7c private method !W | not-writable + set-access pass | PrivateSet method kind |
