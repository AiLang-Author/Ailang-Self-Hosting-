> **ARCHIVED 2026-08-05.** Canonical: [`Docs/Browser/JS_ENGINE_MASTER.md`](./Docs/Browser/JS_ENGINE_MASTER.md)

# Browser JS Engine — Usability Plan

**Date:** 2026-07-12 (baseline) · **Updated:** 2026-07-16  
**Branch:** `gpu-45-may-baseline-restore`  
**Goal:** Usable page scripts + honest conformance. Full test262 100% is *not* the near-term target.

**Living scoreboard / few-day tirage:** [`BROWSER_CONFORMANCE.md`](./BROWSER_CONFORMANCE.md)  
**Dependency / mole history:** [`JS-DEPENDENCY-PLAN.md`](./JS-DEPENDENCY-PLAN.md)

### Product bars (2026-07-16 agreed)

| Track | Near-term | Browser-usable |
|-------|----------:|---------------:|
| Language | ≥72–75% | **≥80%** |
| Core built-ins (Object/Array/String/Function/Promise/…) | ≥55–60% | **≥70–75%** |
| Full suite (~50k) | ≥48–52% | 75–80% = multi-phase |

**Pace:** ~4 days of grind took full suite from **~38% → 43.6%** (+2.5k passes vs 38.5% full49k), Object **~37% → 54%**, class elements **~75%**. That is exceptional velocity for a self-hosted JS engine rewrite — track **pass deltas**, not only “still under 50% full.”

### Test cadence (agreed)

1. Midgate after every rebuild  
2. **Targeted slices** while implementing  
3. Feature-suite after each commit-sized land  
4. **Full `--full` regression after every major milestone** (not every micro-fix)

---

## 1. Fresh baseline (2026-07-12 session)

### Automated suites

| Suite | Result | Notes |
|-------|--------|-------|
| **test262** (default language categories) | **2,857 / 7,689 pass (38.1%)** | 4,639 fail · 128 timeout · 65 harness_eof (crash) · 212.6s · 8 workers |
| **test_js_e2e** | **29 / 32** | 3 fails: DOM `innerHTML` readback (bridge, not core VM) |
| **bench_js** | **8 / 8** | ~494 ms total |

Compare: June 2026 doc baseline was **41.7%** (3,121/7,689) — **~264 fewer passes** now (~3.6 pts). README “92.7%” is an older/full-suite figure and is **not** what this runner reports today.

### Browser smoke (hand-written, real-page features)

**53 / 61 pass (~87%)** — engine is closer to usable than test262 implies. Most test262 fails are edge cases (TCO, typed errors + `instanceof`, `eval`, strict mode, realms, etc.).

**Smoke failures (must-fix for “usable”):**

| # | Feature | Repro | Root cause (diagnosed) |
|---|---------|-------|------------------------|
| 1 | `try { throw 1 } catch(e)` value | catch `e` is always `undefined` at **top-level** | Catch emits `SET_LOCAL` only; top-level `EmitVarGet` always uses `GET_GLOBAL` → binding never visible |
| 2 | `[] instanceof Array` / `{} instanceof Object` | always false | `JSRT_Instanceof` rejects non-`OBJECT` types (arrays are `ARRAY=7`); prototype chain may be incomplete |
| 3 | Object setters `set x(n){}` | getter works, setter doesn’t | `DEF_SETTER` stores `__set_*`; `SET_PROP` never invokes setters |
| 4 | `delete o.a` | property remains | No `DELETE` opcode / incomplete delete semantics |
| 5 | `arguments` object | missing / incomplete | Not bound as array-like in functions |
| 6 | Rest params `...r` | fails | Runtime / compiler rest handling |
| 7 | `Date` / `Date.now` | `typeof Date === 'undefined'` | Builtin not installed |
| 8 | `array.map(fn, thisArg)` | thisArg ignored | Array methods don’t pass thisArg |

**Works well already:** arith, vars, functions, arrows, objects, methods+`this`, arrays + map/filter/reduce/push, for/while/for-in/for-of, classes, promises, async, optional chaining, nullish, template strings, regex `.test`, JSON.parse, Math, spread arrays, simple destructuring, getters, Object.assign/keys, prototypes + `new`.

### test262 worst categories (by fail count)

| Category | Pass% | Fails |
|----------|-------|-------|
| expressions/object | 44.7% | 642 |
| expressions/compound-assignment | 23.8% | 346 |
| eval-code | 4.0% | 333 |
| expressions/assignment | 36.7% | 307 |
| arguments-object | 2.3% | 257 |
| statements/for | 36.6% | 244 (many dstr timeouts) |
| expressions/arrow-function | 30.6% | 238 |
| function-code | 15.2% | 184 |
| expressions/call | 6.5% | 86 |
| expressions/new | **0%** | 59 |
| expressions/array | 5.8% | 49 |

**Timeouts (128):** almost all `statements/for/dstr/*` — destructuring in for-init infinite-loops (must not hang the browser).

---

## 2. Strategy

### What “usable browser JS” means

A script in a page should reliably:

1. Define/call functions, use objects/arrays, control flow  
2. Throw/catch (including primitive throws)  
3. Use `new`, prototypes, `instanceof` for Array/Object/Error  
4. Mutate objects (including getters/setters), `delete`  
5. Touch DOM via bridge (`getElementById`, `innerHTML`, events)  
6. Not hang the UI (no infinite destructuring loops)  
7. Common web APIs: `Date`, `JSON`, `Math`, `console`, timers  

**Not required soon:** full `eval`, realms, TCO, complete property descriptors, every strict-mode early error, Symbol complete, Proxy.

### Process

1. One fix / mole at a time  
2. Minimal repro → implement → midgate rebuild → **feature slice**  
3. After each fix: record **pass delta (+N, +pp)**  
4. **Full test262 `--full` after major feature milestones** (see `BROWSER_CONFORMANCE.md` §4)  
5. Optional: browser-track % (language + core built-ins; Temporal excluded)

### Priority queue (2026-07-16 — next few days)

| Order | Fix | Browser impact | Gate |
|------:|-----|----------------|------|
| **1** | Array holes + reduce/map/filter/forEach | High | Array ≥55% |
| **2** | String.prototype depth | High | String ≥35–45% |
| **3** | Promise / async enough for pages | High | Promise ≥25–35% |
| **4** | RegExp usable (not property-escapes) | Medium–high | non-escape climb |
| **5** | Defer Temporal / TypedArray / Map/Set/Proxy | — | out of sprint |

### Priority queue (2026-07-12 historical — mostly done)

| Order | Fix | Effort | Browser impact | test262 upside |
|------:|-----|--------|----------------|----------------|
| **1** | Top-level catch binding: also `SET_GLOBAL` | XS | High — try/catch on page scripts | try/catch + many assert paths |
| **2** | `instanceof` for ARRAY (+ FUNCTION) + Array/Object.prototype link | S–M | High — feature detect / libs | array/new/object tests |
| **3** | Invoke `__set_*` on `SET_PROP` / `SET_PROP_COMPUTED` | S | High — accessors | getter/setter tests |
| **4** | Implement `delete` operator (opcode + ObjDelete) | S–M | Medium | ~62 delete tests |
| **5** | Kill destructuring timeouts (for-init dstr hang) | M | **Critical** (no hangs) | 128 timeouts → real results |
| **6** | Rest parameters runtime | M | Medium (modern scripts) | rest / spread bucket |
| **7** | `arguments` object basics (length + indexing) | M | Medium (legacy) | ~257 arguments tests |
| **8** | Install `Date` + `Date.now` / `new Date` | S | High for web | few language tests; big real-world |
| **9** | Array method `thisArg` | S | Low–med | some array method tests |
| **10** | DOM `innerHTML` readback (e2e 3 fails) | M | **Browser-critical** | e2e only |
| **11** | Harness `assert.throws` type check | S | None for browser; cleaner scores | unmasks false fails (~500+) |
| later | Error `instanceof`, wrappers, Symbol, eval, class gaps | Hard | Spec polish | large |

---

## 3. Diagnostic notes (code pointers)

### Fix 1 — catch binding (ready)

- **Compiler:** `JSCompiler/Library.JSCompStmt.ailang` TRY_STMT ~1112–1124  
  Emits `DUP` + `SET_LOCAL` only.  
- **Bug:** `Library.JSCompiler.ailang` `JSComp__EmitVarGet` lines ~685–690: when `func_nesting==0`, **always** `GET_GLOBAL` even if a local exists.  
- **Inside functions:** catch works (smoke proved).  
- **Fix:** On catch bind, after `SET_LOCAL`, also `DUP` + `SET_GLOBAL(catchName)` so top-level reads see the thrown value. (Minimal, local to TRY_STMT.)

### Fix 2 — instanceof

- `JSRuntime/Library.JSRTCoerce.ailang` `JSRT_Instanceof` ~917: rejects if `atype != OBJECT` → arrays fail.  
- Allow `ARRAY` (and likely `FUNCTION`) as left-hand types; ensure `NEW_ARRAY` / object create sets `__proto__` to `Array.prototype` / `Object.prototype`.

### Fix 3 — setters

- `DEF_SETTER` (op 65) stores `__set_<name>` (`JSVMDispatch`).  
- `GET_PROP` invokes `__get_*`; `SET_PROP` does **not** invoke `__set_*` — only `JSBridge_SetProp` / `JSRT_ObjSet`.

### Fix 5 — dstr hang

- Timeouts clustered on `statements/for/dstr/*`.  
- Suspect infinite loop in for-init destructuring compile or iterator `next` in `JSCompStmt` / `JSVMDispatch`.

---

## 4. Commands

```bash
# Rebuild
./ailang.x JS-tests/test262_harness.ailang -o test262_harness.x
./ailang.x JS-tests/test262_harness_batch.ailang -o test262_harness_batch.x
./ailang.x JS-tests/test_js_e2e.ailang -o test_js_e2e.x

# Full suite (~3–4 min)
python3 tools/test262_runner.py --verbose --output-json /tmp/test262_results.json -j 8

# Targeted
python3 tools/test262_runner.py --categories statements/for,expressions/delete -j 8

# Smoke (manual / script)
# write JS to /tmp/test262_current.js && ./test262_harness.x
```

---

## 5. Progress log

| When | Change | Smoke | test262 |
|------|--------|-------|---------|
| 2026-07-12 | Baseline | 53/61 | 2857/7689 (38.1%) · 128 T/O |
| 2026-07-12 | **Fix #1:** top-level catch `SET_GLOBAL` mirror (`JSCompStmt` TRY_STMT) | try_catch fixed | (default suite unchanged until full re-run) |
| 2026-07-12 | **Fix #2:** instanceof identity + Array/Object/Error prototypes | **57/63** smoke; 15/15 instanceof | **2887/7689 (38.5%)** · 117 T/O · **+30 pass** |
| 2026-07-12 | **Fix #3:** invoke `__set_*` on SET_PROP (+ stable defineProperty keys) | **58/63** smoke; setters work | (full suite not re-run) |
| 2026-07-12 | **Fixes #4–8:** delete, Date.now, arguments, rest, map thisArg | **63/63 smoke** | (full suite not re-run) |
| 2026-07-15 | Post-M26k full | — | **19244/49998 (38.5%)** full · language 65.8% · built-ins 11.8% |
| 2026-07-15–16 | M26k.8–k.11 private/yield*/brand · class elements ~75% | — | language → ~68% |
| 2026-07-16 | M27a–c Object property model | — | Object **1274→1837** (+563) |
| 2026-07-16 | M29h Array.of/copyWithin/findLast/ToObject | — | Array **1412→1504** (+92) |
| 2026-07-16 | **Full rescore post Object+Array** | — | **21783/49998 (43.6%)** · **+2539** vs 38.5% · built-ins 20.6% |

### Fix #2 details
- `JSRT_SameRef` — compare type+payload (ObjSet copies wrappers)
- `JSRT_Instanceof` — ARRAY/FUNCTION/GENERATOR LHS; Object bag RHS; payload walk
- `JSRTState.object_proto` / `array_proto`; NEW_OBJECT/NEW_ARRAY + `CreateArray` set `[[Prototype]]`
- ArrSide keyed by **payload** (survives `var a=[]` global copy)
- Native CONSTRUCT stamps `__proto__` on returned Error objects
- `JSRT_ObjKeys` skips `__*` internal keys (for-in / Object.keys regression fix)

### Fix #3 details
- `SET_PROP` / `SET_PROP_COMPUTED`: look up `__set_<name>`, bind `this`, `JSVM__CallFunc(setter, [value])`
- Was pure data-store; getters already worked via GET_PROP — asymmetric bug
- `Object.defineProperty` getter/setter keys now str_slab-stable (were transient buffers)
- Note: object-literal *computed* accessors `{set [k](){}}` still broken (compiler/DEF_*_COMPUTED path)

### Fixes #4–8 details
- **#4 delete:** `DELETE_PROP` opcode 39; compile `delete o.x` / `delete o[k]`; `JSRT_ObjDelete`
- **#5 Date.now:** `Date` global + `DATE_NOW` via `clock_gettime(CLOCK_REALTIME)`
- **#6 arguments:** build OBJECT with `.length` + `"0"…"n"` at CALL; `SetGlobal("arguments")`
- **#7 rest:** compiler sets bit 31 of param_count; CALL packs `arg_buf[rest..]` into array
- **#8 map/forEach/filter thisArg:** set `this` from 2nd arg before callback
