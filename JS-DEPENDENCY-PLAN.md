# JS Engine — Plan to **90%** (full suite, all features)

**Updated:** 2026-07-20 (M59 for-of let + IteratorClose GetMethod)  
**Branch:** `gpu-45-may-baseline-restore`  
**Handoff:** [`results/JS_HANDOFF_M47.md`](./results/JS_HANDOFF_M47.md) · full baseline [`results/FULL_SUITE_M47.md`](./results/FULL_SUITE_M47.md)

### Recent moles (post M47)

| Mole | Fix | Slice note |
|------|-----|------------|
| M48–M51b | SetFunctionName, methods/super, Array keys/entries | class/method-def, for-of iterators |
| **M52** | `ASTType.ELISION` vs `[null]`; UTF-16-safe `OBJ_SPREAD`/`Object.assign` getters | for-of ~592/751; **object expr ~917/1161 (79%)** |
| **M53** | Labeled break/continue (parser kept labels; label stack) | for-of **595/751 (80.4%)**; break 18/20; continue 21/24 |
| **M54** | for-of **iterator protocol** (not eager `TO_ARRAY`) + break→`ITER_CLOSE` | for-of **617/751 (83.4%, +22)**; 0 reg |
| **M55** | IteratorClose on return/throw/outer-continue; do-while continue→cond; per-rec `__c__` | for-of **620/751 (83.8%)**; close-via-* green |
| **M56** | Gen.return runs finally; YIELD saves try handlers; force_return abrupt | for-of **625/751 (84.5%, +5)** |
| **M57** | IteratorClose preserves outer try handlers across gen.return | for-of close-via-throw path |
| **M58** | try/finally no-catch normal path; func TDZ hoist | for-of **~632/751** |
| **M59** | ITER_CLOSE GetMethod (`return` getter/null); `FRESH_LET_ENV` per-iter let/const; script_env free-var capture | for-of **630/751 (85.1%)**; head-let/const-fresh + get-method-null green |
| **M60** | free-var TDZ sentinel; IteratorClose throw stack restore; script-var free GET_GLOBAL | for-of **642/751 (86.8%, +12)**; throw.js + init-let green |
| **M61** | for-of member PutValue → IteratorClose; ArrayLikeGet getters on array cursor | for-of **644/751 (87.0%)**; body-put-error + array-key-get-error |
| **M62** | Map/Set + @@iterator; for-of head TDZ env + RESTORE_ENV; typeof free TDZ | for-of **651/751 (88.0%, +7)** |
| **M63** | Map/Set live iterators (tombstones + live coll ref); all for-of map/set-* green | for-of **655/751 (88.5%)** |
| **M64** | String for-of **code points**; let dstr FRESH_LET_ENV + no global leak; dstr assign IteratorClose (non-gen); skip_let_global; GET_LOCAL top-level let | for-of **661/751 (89.3%, +6)**; string-astral, head-let-destructuring, scope-body-lex-*, body-dstr-assign-error green |

**Next:** for-of → 90% (~15 more: cptn, iterator-next-result-type, head-*-fordecl-tdz, residual dstr/TA). **Full suite baseline**. Then L3 object → L2 class → L5 args → L6 async → L7 modules → OA/S.

---

## Goal (hard)

| Bar | Target | Now (M47) |
|-----|-------:|----------:|
| **Full test262** | **≥90%** | **46.1%** (22974/49998) |
| **Language** | **≥90%** | 65.2% |
| **built-ins** (usable surface) | **≥90%** | 28.8% (Temporal/TA deserts dominate fails) |
| **Object / Array / String** | **each ≥90%** | 72.5 / 68.2 / 62.2 |
| Product | Working JS engine, **all language features + core built-ins** | partial |

**Interpretation:** “90% period” means a **usable engine** — language complete enough that real code runs, core Object/Array/String/Function/Promise/RegExp solid, modules/async not deserts forever. Full 50k at 90% ≈ **+22k passes** from today (~500 tests per full-suite pp).

**Not excused by deserts forever:** Temporal / TypedArray / Atomics / full Proxy can stay last-mile, but **language, OA/S, Promise, RegExp, iterators, classes, modules basics** are in scope for 90%.

---

## Why the needle barely moves (and language regressed)

M37 → M47 full: **+174** tests (~**0.35pp**) while OA/S climbed.

| Slice | M37 | M47 | Δ |
|-------|----:|----:|--:|
| full | 45.6% | **46.1%** | **+174** |
| language | **67.7%** | **65.2%** | **−591** |
| built-ins | 25.5% | **28.8%** | **+759** |

**What happened:** moles M38–M47 were **built-in / property-model** work (defineProperty, ArrayLike accessors, species, pad UTF-16, PropTable 128, Date ID, CallFunc this-bind, etc.). That **reclaimed OA/S** and built-ins mass, but several shared paths **broke language tests**:

1. **SetFunctionName / `function.name` (~492 of ~740 language regressions)**  
   Class / arrow / dstr defaults need `[[DefineOwnProperty]]` for `name` (`!W` `C`). Ordinary `SET_PROP` hit `CanAssign` fail → empty names → **class fn-name dstr** cascade.  
   **M48:** FUNCTION + `"name"` → `JSRT_FuncPropSet`; compiler emits SetFunctionName for param defaults, array/obj dstr (local **and** global), object-literal properties.

2. **Shared VM / property / CallFunc changes**  
   this-bind on natives, PropTable size, array hole→proto, species Construct — intended for built-ins, but language tests use the same object model and fail when semantics drift.

3. **Math:** 1pp full ≈ **500** tests. Language −591 nearly cancelled built-ins +759 → full only +174.

**Lesson:** Prefer **language-safe** property/CallFunc changes; after every built-in mole, rescore a **language slice** (class + dstr + object), not only OA/S.

---

## March order (to 90% full)

```
PHASE L — Language reclaim (NOW)
  L1  SetFunctionName complete (class/param/dstr/object lit)   ← M48 in flight
  L2  class residual (private, static, heritage)
  L3  object literal / computed / methods
  L4  for-of / iterators / generators
  L5  arguments-object
  L6  async / await / for-await (not desert)
  L7  modules / dynamic-import basics
        │
        ▼  language ≥ ~80% then keep climbing
PHASE B — Built-ins to product bar
  B1  Object → 90% (defineProperty residual, gOPD, freeze/seal)
  B2  Array  → 90% (concat, reduce residual, sort/splice, species done)
  B3  String → 90% (non-RegExp polish → RegExp-backed replace/match)
  B4  Function / Promise / RegExp / Date / Map-Set basics
        │
        ▼  OA/S each ≥90%, language ≥90%
PHASE F — Full suite → 90%
  F1  close deserts that still own fail mass (or ship stubs that pass tests)
  F2  full 50k rescore at milestones only
```

**Gates after every mole:**

```bash
python3 tools/js_midgate.py --rebuild --quick   # must PASS
# language smoke (cheap):
python3 tools/test262_runner.py --paths 'language/expressions/object,language/statements/class,language/expressions/arrow-function' -j 8
# product:
python3 tools/test262_runner.py --paths 'built-ins/Object,built-ins/Array,built-ins/String' -j 8
```

Full 50k only at milestones (post L1 reclaim, post OA/S 80%, post OA/S 90%, …).

---

## Distance math (M47)

| Track | Pass | Target 90% | Still need |
|-------|-----:|-----------:|-----------:|
| Full | 22974 | ~44998 | **~+22000** |
| Language | 15581 | ~21509 | **~+5928** |
| Object | 2464 | 3070 | **+606** |
| Array | 2083 | 2773 | **+690** |
| String | 759 | 1101 | **+342** |

Language reclaim from names alone may be **+400–700** (class/dstr). That is real full-suite movement (~1pp) **without** more built-in thrash.

---

## Active mole — M48+ (language first)

| Item | Status |
|------|--------|
| SET_PROP function.name → FuncPropSet | **landed** (153dff57) |
| Param default SetFunctionName | in compiler |
| Array/obj dstr SetFunctionName (local+global) | in compiler |
| Object-literal `{bar: function(){}}` name | in compiler |
| midgate green + language slice rescore | **next** |
| Commit residual M48 when green | next |

Then knock bugs in order: remaining class fn-name → object expr → for-of → arguments → async/modules.

---

## Rules

| Rule | |
|------|--|
| Goal | **90% full engine, all features** — not aggregate OA/S-only theater |
| Order | **Language first**, then OA/S, then deserts |
| Honesty | Generators / call / function: `--no-batch` when needed |
| Style | Wrap over write — Ailang primitives, thin JS surface |
| Gate | Midgate green after every mole |
| Score | Report **pass deltas (+N)**; full 50k at milestones |
| Regression | Language slice must not tank while “winning” built-ins |

---

## Living docs

- Scoreboard: [`BROWSER_CONFORMANCE.md`](./BROWSER_CONFORMANCE.md)
- Full M47: [`results/FULL_SUITE_M47.md`](./results/FULL_SUITE_M47.md)
- Session handoff: [`results/JS_HANDOFF_M47.md`](./results/JS_HANDOFF_M47.md)
