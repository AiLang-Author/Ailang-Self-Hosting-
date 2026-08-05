# Language → 90% then Built-ins — Plan

> **Superseded for targets:** see **`results/LANGUAGE_95_PLAN.md`**  
> Full suite M127: language **84.2%** → target **95%** (+2,550); overall 57.2%.

**Branch:** `gpu-45-may-baseline-restore`  
**Full suite baseline:** M127 — overall 57.2%, language 84.2%, built-ins 32.5%  
**Ordering:** L1–L9 language ≥95% → B1–B7 built-ins (Reflect→…→Temporal last)

---

## Phase A — Language categories ≥90%

| Order | Cluster | M110 | Latest | Target | Notes |
|------:|---------|-----:|-------:|-------:|-------|
| 1 | **module-code** | 30.7% | **90.4%** (M125, 675/748) | 90% | **HIT** (need dynimport/eval next) |
| 2 | **import** | ~13% | **78.7%** (M127, 100/127 real) | 90% | JSON native + defer triggers; need ~115/127 |
| 3 | **dynamic-import** | 46% | — | 90% | After modules |
| 4 | **eval-code** | 52% | — | 90% | Parallelizable |
| 5 | **function-code** | 68% batch | multipath ~92% earlier | 90% batch | Rescore multipath |
| 6 | Mid cats | various | — | 90% | super, yield, call, for-in, … |

### Module-code substeps
1. ~~export/import parse + compile unwrap~~ (M112)
2. ~~runner self-import + FIXTURE inline~~ (M112b)
3. ~~Anonymous `export default` + name default~~ (M113)
4. ~~`import * as ns` namespace object (data props)~~ (M113, partial 20/46)
5. Remaining instn-/eval-export / namespace edges
6. ~~Top-level await async IIFE wrap~~ (M114: TLA 75.5%)
7. Remaining module fails (~182) → 90%

### Math for module-code 90%
- 748 tests × 0.9 ≈ **674** passes (need ~+322 from 352)
- Non-TLA max ~461; TLA is 287 @ 10.8% → **TLA required**

---

## Phase B — Language toward ~95%
with, using/await-using, small expression ops, white-space, statementList, etc.

---

## Phase C — Built-ins lift
Review dependencies (Proxy, species, TypedArray, Promise jobs), then Object/Array → Promise → TypedArray. Temporal last.

---

## Commits
- M112: export/import keywords + parse/compile
- M112b: module preprocess self-import + fixtures
- M113: anon default + namespace objects (in progress)
- (next) M114: top-level await in modules
- M118: live default imports, let/const TDZ aliases, IEE re-exports, safe fnGlobalObject, local-bndng (+26 → 82.5%)
- M118b: export*as default, live ns getters, eval-this, iee trailing comma
- M119: ns exotic (set/delete/gOPD shim), export*, string expnames, star-props, keyword import names
- M120: NS uninit/TDZ, setPrototypeOf, star equality cache, live import renames, string imports
- M121: nested export*as NS, ambiguous export* omit, defineOwnProperty+freeze, NS brand side-table
- M122: gOPS polyfill, recorded NS export keys (fixes __ and ownKeys sort/types)
- M123: identity-based star ambiguity (same NS dual export*), GetModuleNamespace cache,
  fixture import*as, string export*as "Name", cycle star expand, gOPD hide non-exports
- M124: multi-hop ResolveExport (IEE cycles), side-effect fixture isolation (uniq-env),
  new Function→globalThis (same-global); 668/748 ~89.4%
- M125: RequestedModules source order, import attributes strip, per-fixture defaults,
  NS __proto__ via Reflect, for-in→Object.keys TDZ; **675/748 ~90.4% HIT**
- M126: JSON/text synthetic modules + import defer lazy NS; import 38→99/182 (with FIXTUREs)
- M127: **Native JSJSON** in `Librarys/Browser/JSRuntime/Library.JSJSON.ailang` (UTF-16 JSON.parse);
  ToNumber sci scale single-div SameValue; JSON objects get Object.prototype;
  runner: skip `*_FIXTURE.js`, deferred NS GetModuleExportsList via Reflect/gOPD shims,
  "Deferred Module" toStringTag, nested-defer multipass rewrites;
  **import 100/127 (78.7%)** — attrs 17/17, defer 79/101; need ~+15 for 90%
  (bytes×5, TLA defer, error races, super/private, residual NS identity)
