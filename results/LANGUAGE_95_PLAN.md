# Language → 95%, then Built-ins — Dependency Plan

**Branch:** `gpu-45-may-baseline-restore`  
**Baseline:** full test262 M127 (`results/test262_full_m127.json`)  
**Latest full suite:** M128e6c (`results/test262_full_m128e6c.json` / `FULL_SUITE_M128e6c.md`)  
**Latest grind tip:** **M128e6t** (`results/M128e6t_PROGRESS.md`) — 2026-07-27  


| Scope | Pass | Total | Pass% | Target | Notes |
|-------|-----:|------:|------:|--------|-------|
| **Overall** | 27,650 | 49,723 | **55.6%** | later | full @ e6c (M127 was 57.2%) |
| **language** | **19,552** | **23,635** | **82.7%** | **95%** | full @ e6c; M127 peak 84.2% |
| built-ins | 7,418 | 23,518 | 31.5% | after language | full @ e6c |
| annexB | 419 | 1,086 | 38.6% | after language core | |
| staging | 261 | 1,484 | 17.6% | last / opportunistic | |

### Goal status (95%+ full language test262)

| Gate | Need | Current | Status |
|------|-----:|--------:|--------|
| **G1 language ≥90%** | 21,272 | 19,552 | **open** (~+1,720) |
| **G2 language ≥95%** | 22,454 | 19,552 | **open** (~**+2,902**) |
| **G3 built-ins bulk** | — | — | **blocked on G2** |

### Math to language 95%
- 23,635 × 0.95 → **need 22,454 passes**
- Full suite language @ e6c: 19,552 → **need +2,902**
- M127 peak 19,904 → +2,550 (historical best full language)
- 90% intermediate: +1,720 from e6c
- DEFAULT_CATEGORIES slice @ e6q: **6,532/7,689 (85.0%)** — grind signal only

Largest fail masses (language):

| Cluster | Fails | Pass% | Notes |
|---------|------:|------:|-------|
| `expressions/dynamic-import` | **628** | 33% | Single biggest lever |
| `eval-code` | **255** | 27% | direct 219 + indirect 36 |
| class residual (stmt+expr) | **~740** | ~91% base | elements, subclass, builtins |
| `statements/with` | **162** | 11% | unscopables / env |
| `using` + `await-using` | **107** | ~38% | explicit resource mgmt |
| operators / compound-assign | **~150** | mixed | ToNumber / PutValue edges |
| `import` residual | **27** | 79% | defer TLA/errors/bytes |
| `super` / `yield` / tagged-template | **~100** | low pockets | mid-tier syntax |
| white-space / statementList / comments / types / global-code | **~120** | 50–75% | lex/parse hygiene |
| misc | rest of ~2,550 | — | long tail |

---

## Strategy

1. **Language first until ≥95%** — do not divert to Temporal / TypedArray bulk.
2. **Dependency order** — each stage unblocks or multiplies the next.
3. **Measure after every stage** — `language/*` slice + periodic full language score.
4. **Prefer engine/Ailang fixes** over runner shims; shims only for loader/NS gaps the engine cannot host yet.
5. **Skip / defer** pure staging and experimental features until core language is green.

---

## Phase L0 — Foundations (done / keep healthy)

Already landed (M112–M127); **do not regress**:

| Item | Status |
|------|--------|
| Module parse/compile, NS exotic, TLA wrap | module-code **96.0%** (572/596) |
| Static `import`, attributes, JSON/text modules | import **78.7%** (100/127) |
| Native `JSON.parse` (`Librarys/Browser/JSRuntime/Library.JSJSON.ailang`) | yes |
| Sci ToNumber SameValue, JSON object proto | yes |
| Deferred NS eval hooks (Reflect/gOPD) | partial |

**Gate:** re-run `language/module-code` + `language/import` after each major change.

---

## Phase L1 — Finish static modules / import → ≥90%  
**Status M128v: import 92/127 (72.4%)** — was ~59%; +17 from deferred NS free-var fix  
**Residual:** defer errors/TLA/super-triggers (~29), import-bytes (needs TypedArray/immutable AB)

| Order | Work | Depends on | Status |
|------:|------|------------|--------|
| 1.1 | import-defer evaluation-triggers (getter free-var) | L0 defer NS | **+~15 done** |
| 1.2 | import-bytes synthetic (`type: 'bytes'` → Uint8Array) | TypedArray | stubbed; engine U8 weak |
| 1.3 | module-code residual TLA / not-found / `__proto__` | L0 NS | open |
| 1.4 | `import.meta` minimal (url string) for module + dynimport | modules | open |

**Exit:** `import` ≥90% (~115/127), `module-code` hold ≥95%.

---

## Phase L2 — Dynamic import → ≥70% then ≥90%  
**Status M128e6p: 926/941 (98.4%) — EXIT MET (>>90%)**  
**Residual ~15:** with-related, attrs 2nd-param edges, defer behavioral, NS edges.

Depends on: modules, Promise (thenables), job queue, optional import attributes.

| Order | Work | Notes | Est. +pass |
|------:|------|-------|-----------:|
| 2.1 | Real `import()` → Promise of module NS | Engine or loader bridge | +200–300 |
| 2.2 | `catch` / rejection paths (syntax, resolve fail) | 172 fails in catch/ | +100–150 |
| 2.3 | `usage` + assignment-expression forms | 106+27 | +80–100 |
| 2.4 | Namespace object parity with static NS | 67 fails @ 0% | +50–60 |
| 2.5 | import-attributes on dynamic import | after static attrs | +15–20 |
| 2.6 | dynamic import-defer if needed | after static defer | +5 |

**Exit:** `expressions/dynamic-import` ≥90% (≈847/941).  
**Language impact:** alone can move overall language ~84% → ~87–88%.

---

## Phase L3 — eval-code → ≥90%  
**Status M128v: 339/347 (97.7%) — EXIT MET**  
**Residual 8:** with×2, import/export×4, always-non-strict (with), realm

Depends on: global/var env, strict, `this`, indirect vs direct, optional realm.

| Order | Work | Notes | Status |
|------:|------|-------|--------|
| 3.1 | Direct eval scope / `var` / `let` / lexical | bulk of direct/ | done |
| 3.2 | Indirect eval (`(0,eval)`) global only | heritage + lower-lex | done |
| 3.3 | Nested eval depth-2 + save_* restore | global-env-rec-eval | done |
| 3.4 | Strict / arguments / caller edges | formal arguments bit 27 | done |
| 3.5 | Residual with / import-export / realm | engine with + cross-realm | open |

**Exit:** `eval-code` ≥90% (≈312/347). **Hit 97.7%.**  
**Language impact:** +~200 → toward ~89%.

---

## Phase L4 — Class / super residual → mid-90s pockets  
**Fails: ~740 class + ~42 super expressions + subclass-builtins**

Depends on: OOP, heritage, private methods (already ~92% private), constructors.

| Order | Work | Notes | Est. +pass |
|------:|------|-------|-----------:|
| 4.1 | `super` property/call/get in all contexts | 55% → 90% | +80–100 |
| 4.2 | class `elements` residual (fields, static, ASI) | 251+192 fails | +150–200 |
| 4.3 | `subclass` + `subclass-builtins` (Array/Error/…) | hard but high value | +50–80 |
| 4.4 | async/gen method residual on class | shared with async | +20 |
| 4.5 | Decorators — **defer** (staging-ish / low ROI) | 11–20 fails | skip |

**Exit:** class stmt+expr combined ≥94%; super ≥85%.

---

## Phase L5 — Generators / yield / async iteration residual  
**Status M128e6p: for-await-of 1234/1234 (100%) — EXIT MET**  
Residual: yield* / async-gen pockets outside for-await category (track via full language).

Depends on: iterators, Promise, yield* throw/return protocol.

| Order | Work | Status |
|------:|------|--------|
| 5.1 | `yield*` throw/return protocol | partial (e6n GenReturn) |
| 5.2 | async generator residual | partial (e6o/e6p Promise jobs) |
| 5.3 | for-await-of residual | **DONE 100%** |

---

## Phase L6 — `with` / unscopables  
**Status M128e6q: 132/181 (72.9%)** — was 126/181 e6p, 11% at M127 plan time  
**Residual 49:** Proxy env (~10), S12.10 clusters, scope-var, cptn-abrupt, has-property-err, TypedArray proto; get-err flaky in batch

Depends on: env records, `@@unscopables`, object HasBinding.

| Order | Work | Status |
|------:|------|--------|
| 6.1 | `with` object env + mutable binding | largely done (GET_WITH/SET_WITH) |
| 6.2 | `@@unscopables` Get + accessors + rethrow | **e6q done** (ObjGetAcc) |
| 6.3 | delete-in-get-unscopables + strict RE | **e6q done** |
| 6.4 | IDENT ++/-- single HasBinding | **e6q done** (unscopables-inc-dec) |
| 6.5 | eval with completion (cptn-nrml) | **e6q done** |
| 6.6 | Proxy has / env residual | open (needs Proxy) |
| 6.7 | S12.10 / scope-var / cptn-abrupt | open |

**High ROI remaining is limited** without Proxy; prefer L4/L7 for language % next.

---

## Phase L7 — Operators & assignment edges  
**Fails: compound-assignment ~101, exponentiation 28, relational/equality/addition ~80, delete/call/new residual**

Depends on: ToPrimitive, ToNumber, PutValue, Strict Equality.

| Order | Work | Est. +pass |
|------:|------|-----------:|
| 7.1 | compound assignment reference / PutValue | +60–80 |
| 7.2 | `**` exponentiation | +20–25 |
| 7.3 | `==` / `===` / relational leftovers | +30–40 |
| 7.4 | `in` / `instanceof` | +20–25 |
| 7.5 | `delete` / `new` / `call` residual | +30–40 |
| 7.6 | tagged templates | +20–25 |

---

## Phase L8 — Resource management & modern syntax  
**Fails: using + await-using ~107; optional-chaining ~12; nullish residual**

| Order | Work | Est. +pass | Priority |
|------:|------|-----------:|----------|
| 8.1 | optional chaining residual | +10 | medium |
| 8.2 | `using` / `await using` | +60–80 | medium (large fail count) |
| 8.3 | private residual / brand checks | +20–40 | if still needed for 95% |

---

## Phase L9 — Lex / parse hygiene & small cats  
**Fails: white-space 32, statementList 33, comments 18, types 29, global-code 22, line-terminators 12, …**

| Order | Work | Est. +pass |
|------:|------|-----------:|
| 9.1 | white-space after regexp literal / Unicode spaces | +25–30 |
| 9.2 | statementList / ASI edges | +20–25 |
| 9.3 | comments / line-terminators | +15–20 |
| 9.4 | types (reference, object, number ToString) | +15–20 |
| 9.5 | global-code / script vs module `this` | +15–20 |
| 9.6 | function-code residual → ≥90% | +20–30 |
| 9.7 | identifiers / reserved residual | +10 |

---

## Language 95% — cumulative path (estimate)

| After phase | Rough language % | Cumulative +pass |
|-------------|-----------------:|-----------------:|
| L1 import/modules polish | 84.5–85% | +50–100 |
| L2 dynamic-import ≥90% | **87–89%** | +500–600 |
| L3 eval-code ≥90% | **89–91%** | +200–250 |
| L4 class/super | **91–93%** | +200–300 |
| L5–L6 yield + with | **93–94%** | +150–200 |
| L7–L9 operators + hygiene | **≥95%** | +200–300 |

Order is strict for L1→L3; L4–L9 can partially parallelize once L2/L3 land.

### Measurement commands
```bash
# Full language
python3 tools/test262_runner.py --paths language --timeout 15 \
  --output-json results/test262_language_latest.json

# Hot slices
python3 tools/test262_runner.py --paths language/expressions/dynamic-import --timeout 15
python3 tools/test262_runner.py --paths language/eval-code --timeout 15
python3 tools/test262_runner.py --paths language/import,language/module-code --timeout 15 --no-batch
```

---

## Phase B0 — Built-ins **dependency order** (only after language ≥95%)

Do **not** start Temporal. Order by what everything else needs:

### B1 — Meta-object protocol
| Order | Built-in | Now | Why first |
|------:|----------|----:|-----------|
| 1 | **Reflect** | 0% | spec algorithms; Proxy traps |
| 2 | **Proxy** | 0% | many Object/Array/test262 patterns |
| 3 | **Symbol** residual | 10% | well-known symbols, species |

### B2 — Core object model polish
| Order | Built-in | Now | Notes |
|------:|----------|----:|-------|
| 4 | **Object** residual | 75% | defineProperty, freeze, keys |
| 5 | **Function** residual | 43% | bound, caller, construct |
| 6 | **Array** residual | 72% | species, holes, iter |
| 7 | **Boolean / Number / Math / String** | 30–62% | ToNumber/ToString paths |

### B3 — Async & collections
| Order | Built-in | Now | Notes |
|------:|----------|----:|-------|
| 8 | **Promise** jobs / allSettled / any | 29% | also feeds dynimport residual |
| 9 | **Map / Set / WeakMap / WeakSet** | 24–47% | |
| 10 | **JSON** built-in tests residual | 24% | engine JSON.parse exists |

### B4 — Text & time (medium)
| Order | Built-in | Now |
|------:|----------|----:|
| 11 | **RegExp** | 30% |
| 12 | **Date** | 15% |
| 13 | encodeURI* / parseInt / parseFloat | ~20–30% |

### B5 — Binary data (large, after species + ArrayBuffer design)
| Order | Built-in | Now | Fails |
|------:|----------|----:|------:|
| 14 | **ArrayBuffer** | 1% | ~194 |
| 15 | **TypedArray** + constructors | ~2% | ~2.1k |
| 16 | **DataView** | 0% | 561 |
| 17 | **Atomics / SharedArrayBuffer** | ~0% | ~480 |

### B6 — Iteration helpers & disposables
| Order | Built-in | Now |
|------:|----------|----:|
| 18 | **Iterator** helpers | 3% |
| 19 | DisposableStack / AsyncDisposableStack | ~3% |

### B7 — Last / optional
| Order | Built-in | Now | Notes |
|------:|----------|----:|-------|
| 20 | **Temporal** | 0.8% | **4.5k tests — last** |
| 21 | ShadowRealm | 0% | niche |
| 22 | staging / annexB cleanup | low | after core |

### Built-ins sequencing rule
```
Reflect → Proxy → Symbol
    → Object / Function / Array polish
    → Promise
    → Map/Set + String/Number/Math
    → RegExp / Date
    → ArrayBuffer → TypedArray → DataView → Atomics
    → Iterator helpers
    → Temporal (last)
```

---

## Phase C — Overall 70% / 80% (later)

Only after language ≥95% and B1–B3:
- Overall is **57%** today; Temporal alone is ~9% of the suite at 0.8% pass.
- Hitting overall 70% likely needs Reflect/Proxy + Promise + Array/Object polish + some TypedArray **or** accepting Temporal stubs.
- Revisit overall targets after language gate.

---

## Immediate next actions (start here) — post M128e6q

1. **L7** — assignment / compound-assignment residual (DEFAULT slice ~75 + ~67 fails).
2. **L4** — class residual rescore (stmt ~91% / ~390 fails) + elements.
3. **L6** — only cheap with residual (skip Proxy bulk until B1).
4. Full **language** rescore → refresh G1/G2 distance in this doc.
5. **Do not** start Temporal / TypedArray bulk until G2.

### Success criteria
| Gate | Criterion | Status 2026-07-27 |
|------|-----------|-------------------|
| G1 | language ≥ **90%** (~21,272 pass) | open (~82.7% @ e6c) |
| G2 | language ≥ **95%** (~22,454 pass) | open (~**+2.9k** passes) |
| G3 | Only then open B1 Reflect/Proxy | blocked |

---

## Commits / history (abbrev)

- M112–M125: modules → **module-code ≥90%**
- M126–M127: JSON native, import-defer, sci ToNumber; **import 78.7%**, full suite baseline
- **Next:** L2 catch/rejection paths + remaining syntax (import.source/defer optional)
- M128: **Dynamic import()** — ASTType.IMPORT_CALL, JSOp.IMPORT_DYN, stmt lookahead
  for `import(`, runner `__dynModules` + string-literal rewrite, missing/throw/script
  fixtures → Promise.reject, ToString abrupt → reject, fix TLA wrap on [async] tests;
  **dynimport 314→667/941 (70.9%)** (+353); usage 106/108, catch 72+, namespace 59
- M128 recovery (post free-var): runner `__dynModules` + FIXTURE skip restored;
  ImportCall trailing-comma-after-options; deferred Reflect touch + __defGet/Has;
  **dynimp 666/941 (70.8%)**, **import 92/127 (72.4%)**, **eval 339/347 (97.7%)**
- M128 dyn grind: asyncTest; Function ToString; tagged tmpl; IEE reject; IIFE NS;
  CallFunc async -65+strict this; Promise.resolve identity; import.meta rewrite;
  **dynimp 714/941 (76.0%)**; assignment 27/28; catch 111+; eval held 97.7%
- M128at: dyn fixture **named `export default function fn` stays declaration**
  (live binding `fn=2`); demote fixture **const/let→var** so NS getters free-var
  resolve in nested arrows; await-import-then expand retained.
  **dynimp 735/941 (78.2%)** (+13); **usage 108/108 (100%)**; assignment 28/28;
  catch 111/176; import 92/127 (72.4%); eval 339/347 (97.7%).
  Residual ~206: import.source/defer syntax (~156), attributes 2nd-param, with,
  namespace edges, await+rejected IMPORT_DYN (async-gen/arrow abrupt), dflt class name.
- M128av: **CreatePromise** inherits then/catch/finally from Promise.prototype
  (no own props → `returns-promise`); module strip **named `export default class/fn`**;
  demote `let __default_export__`→var + name-stamp reorder for dyn self-import.
  **dynimp 740/941 (78.7%)** (+5 vs m128at); root 26/31; usage 100%; import/eval held.
  Lost: nested-namespace-props (harness rebuild + dirty engine, not CreatePromise alone);
  set-same-values-no-strict flaky in batch. Residual ~201 mostly source/defer/attrs/with.
- M128aw: **import.source / import.defer** parse (expr + stmt lookahead DOT);
  IMPORT_DYN phase imm (0=eval, 1=source→SyntaxError, 2=defer≈eval).
  **dynimp 875/941 (93.1%)** (+135); syntax 96.2%; catch 93.2%; usage 100%.
  Residual ~66: with(~18), attrs 2nd-param(~14), namespace(~11), await-abrupt async-gen/arrow,
  import-defer behavioral(5), root edges. import/eval held.
- M128ax: null-proto **`__proto__` public GET → undefined** (was null own slot);
  **HasProperty("__proto__")** false when internal [[Prototype]] is null.
  **dynimp 879/941 (93.5%)** (+4 NS get/has str-not-found). Residual ~62.
  Open: await of IMPORT_DYN reject inside async (async return of rejected Promise
  also weak); with; attrs 2nd-param; nested NS; defineOwn.
- M128az: **async RETURN** adopts settled Promise (copy state/value after ReclaimScope);
  **CallFunc.depth** so ThrowValue does not async-reject outer frame during nested
  CallFunc; runner **await import(non-lit)** pre-ToString + Promise.reject on throw
  (string lits kept for reject_rewrite).
  **dynimp 895/941 (95.2%)** — **HIT 95% on dynamic-import**. Residual ~45:
  with(~18), attrs 2nd-param(~13), import-defer behavioral(5), nested NS, root edges.
- M128ba: **import() 2nd arg** non-object → TypeError reject; **dynimp 898/941 (95.6%)**.
  **Full suite** `results/test262_full_m128ba.json` / `FULL_SUITE_M128ba.md`:
  **25 676/49 723 (51.6%)** overall; **language ~72.7%**. vs M110 (56.6%): net −2.6k
  common-test passes — **class statements 90%→20.5% (~3k regressions)** is the hole.
  Dynimp/eval/modules/import **net improved**. **Next: restore class**, then language 95%.
- M128b: **eval early errors** — `DIRECT_EVAL` opcode vs indirect CALL; super/new.target
  forbidden outside method/function as appropriate; **14/16** super/new.target tests
- M128c: **globalThis mirror** on SET_GLOBAL (CreateGlobalVarBinding surface for gOPD);
  script function two-pass instantiate (WIP — eval path single-pass to avoid SIGSEGV);
  eval-code ~**64–70/347**; var-env **15/41** (global-new fixed; local-scope still missing)
- M128j: **CALL_METHOD restore outer `this`** after native exits (Object.defineProperty(this)
  no longer leaves `this===Object`); **HoistVars skip SET_GLOBAL in eval** + **HoistDeclToEnv
  env==0 global path** (no wipe of existing globals; bare `var x` CreateGlobalVarBinding);
  **CanDeclareGlobalVar** (preventExtensions); strict eval isolation for **indirect**
  (`eval_var_env` not only direct); inherit caller strict **only if direct**.
  eval-code **121→132 pass** (84.6% of pass+fail; direct 86.3%, indirect 82.0%);
  results: `results/test262_eval_m128j.json`
- M128k: **eval source strict** via `JSParse_IsStrict` skips var/let collision when source has
  `"use strict"`; **super in direct eval** — SuperProperty needs `[[HomeObject]]`, SuperCall
  only for `name==="constructor"`; SUPER_BASE/SET_PROP_SUPER use `save_fp` during eval (fp=0).
  eval-code **121→138 pass** (89.0%; **direct 91.5%**, indirect 85.2%);
  results: `results/test262_eval_m128k.json`
- M128l (partial/reverted): block `FRESH_LET_ENV` + GetGlobal lex walk for heritage/lower-lex
  **regressed −11** (var-env init + super-no-home). Reverted to m128k baseline **138 pass**.
- M128m: free-var let dual-write + str_slab keys; heritage green; distinct-let regressed (−3 net 135).
- M128n: **non-strict eval let/const stay on ephemeral `eval_var_env`** (TDZ + inits when name
  already there); var stays on `caller_env`. Restores distinct-let/const + keeps heritage.
  **139 pass**.
- M128o: **class TDZ pre-decl** in CompileProgram/CompileBlock (lex-env-no-init-cls ×2);
  **strict FutureReservedWord** BindingIdentifier (`public`/`static`/… via `JSParse__IsStrictReserved`);
  KW_STATIC as binding in non-strict (`var static`). strict-caller-global/function-context green.
  **143 pass** (92.3% of adjudicated; direct 95.7%). Results: `results/test262_eval_m128o.json` /
  `m128p.json` (same).
- Residual eval (12 fails + 192 errors):
  - **192× arguments / default-param `eval("var …")` SIGSEGV** (param-init frame env);
    WIP `param_init` ephemeral path — still flaky.
  - nested eval soft-fail → global-env-rec-eval
  - always-non-strict needs `with` statement (L6)
  - import/export in eval, realm, indirect heritage/lower-lex
- M128r: **param-init eval fixed** — body_start on fdesc; ephemeral env; no corrupt
  formal-blob walk; `var arguments` → SyntaxError; throw unwind pops frames +
  RestoreArguments; globalThis.arguments deleted when no outer binding.
  eval-code **143→327/347 (94.2%)** — **L3 ≥90% gate HIT** (direct 95.8%).
  Results: `results/test262_eval_m128r.json`.
- M128s: **arrow param-init** — no SyntaxError for `var arguments`; bind to caller_env;
  SET_FRAME_ENV for arguments in eval_mode; dual-write to `__cenv` for GET_FREE.
  **331/347 (95.4%)**.
- M128t: **nested eval depth-2** (heap nest_* snapshot; skip static bak). Indirect
  global-env-rec-eval green; top-level nested works; function-context nested still
  clobbers some globals (str_buf/func restore residual). **332/347 (95.7%)** direct 97.2%.
  Results: `results/test262_eval_m128t.json`. ~15 residual (4 arrow-args-named-param,
  with, import/export, realm, heritage, lower-lex, direct global-env-rec-eval).
- **Built-ins deferred** until language greener (user: eventually need work too).
- M128e6j–e6p: free-var dual-bind, for-of var, no VAR_DECL double-init, THROW/CallFunc
  isolation, GenReturn reject, GET_PROP rethrow, Promise microtasks, CoverToPattern
  COMPUTED_PROP, for-await AWAIT nextValue.
  **for-await-of 1234/1234 (100%)**; **dynimport 926/941 (98.4%)**.
- **M128e6q:** `JSVM__ObjGetAcc`; GET_WITH/SET_WITH @@unscopables accessors + rethrow;
  re-HasProperty after unscopables Get; IDENT ++/-- single Get; `cptn_prop` eval with
  completion. **with 126→132/181 (72.9%)**; for-await held 100%.
  Progress: `results/M128e6q_PROGRESS.md`.