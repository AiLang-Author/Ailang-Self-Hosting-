# JS Engine — Dependency Plan

**Updated:** 2026-07-15  
**Goal:** Language compliance mass first; speed later. No false greens.

| Rule | |
|------|--|
| Order | Fix **dependencies first** (ops → assign → call → function → eval → class → modules → async) |
| Honesty | Generators / function / call: **`--no-batch`**. Batch OK after M18b (gval rewind). |
| Style | **Wrap over write** — use Ailang/runtime primitives; thin JS surface |
| Gate | Midgate green after every mole |

---

## Summary (now)

| Gate | Score | Notes |
|------|------:|-------|
| e2e + midgate core | **PASS** | post-M26k |
| function dstr | **186/186** | |
| gen dstr | **372/372** | no-batch |
| generators | **~90%** | no-batch |
| call | **~79%** | no-batch; M21 spread-err 16/16 |
| mapped args | **43/43** | |
| assignment | **~86%** | M20e |
| compound-assignment | **~66%** | M19d |
| arrow-function | **~92%** | M22 |
| **class\*** (stmt+expr) | **5975/8551 (~70%)** | M26a–k foundation |
| **private\*** | **~69%+** (elements private **68.7%** post-M26k.2) | M26k + static/setter brand |
| **language** (full-run slice) | **16278/24744 (65.8%)** | post-M26k full |
| **built-ins** | **2804/23770 (11.8%)** | core partial; Temporal/TA drag |
| **full `--full` (49998)** | **19244/49998 (38.5%)** | post-M26k; JSON `/tmp/full49k.json` |

**Batch fix (M18b):** `JSRT_Reset` rewinds `gval_pool` — batch no longer under-reports statements/function & generators.

**Timing:** Full 50k ~33 min @ 16 workers batch.

---

## Gates

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --categories expressions/compound-assignment -j 4
python3 tools/test262_runner.py --categories expressions/call --no-batch -j 4
python3 tools/test262_runner.py --categories statements/generators,expressions/generators --no-batch -j 4
# broad
python3 tools/test262_runner.py --all -j 4 --output-json /tmp/js_scorecard/language_all.json
# milestone
python3 tools/test262_runner.py --full -j 4 --output-json /tmp/js_scorecard/full.json
```

---

## Dependency-ordered march (forward)

Attack **fail volume × foundational** first. Class/modules/async sit on top of ops+function+iter.

| Mole | Target | Why first | Fail mass (lang-all) |
|------|--------|-----------|----------------------|
| **M19** | compound-assignment + core arith/bitwise | Pure opcode; unblocks assign/class code | ~280 compound alone |
| **M20** | assignment LHS / strict assign edges | Builds on M19 | ~200 assignment |
| **M21** | call spread **error paths** (not TCO) | Completes call; spread already partial | call residual ~29 |
| **M22** | function residual + function-code + TDZ defaults | Function surface after M18 | ~92 + ~172 |
| **M23** | eval-code | Needs call/function solid | ~292 @ 16% |
| **M24** | arguments edges (gen trailing-comma etc.) | Mapped done; gen/unmapped edges | ~139 |
| **M25** | for-of / iterator close | Gens solid; for-of next | ~386 for-of |
| **M26** | class (+ super) | Largest remaining volume | ~2000+2000 fails |
| **M27** | modules / import / dynamic-import | After class patterns | ~384+168+588 |
| **M28** | async / await / async-gen / for-await-of | Last major ES2017+ block | large |

**Skip / deprioritize:** TCO optional tests; forbidden-ext caller (legacy); pure whitespace unicode edges.

### M19 progress
- **Done:** Boxing; ParseNumberStr; **Number.POSITIVE_INFINITY/NEGATIVE_INFINITY/NaN**; Mod 0%0→NaN; **ToPrimitive** (toString/valueOf); **TO_PROP_KEY + CHECK_COERCIBLE** for compound `base[prop] op=` (ES5 order, key once). Compound **38%→65.6%** (275→298).  
- **Left:** private #fields ~48; A5/A6 putvalue+**with**/eval (~66, needs `with` stmt); 11.13.2-s strict eval (~31, M23); putvalue global-delete (~22); whitespace ~11.

### M20 progress
- **Done (M20a):** LHS-first `base[prop]=`; SET_ELEM single ToPropertyKey.  
- **Done (M20b):** CoverToPattern default swap; stack pollution; RHS result stash → **341**.  
- **Done (M20c):** `EmitDstrBind` for MEMBER_DOT/BRACKET targets; `THROW_CONST` + const name registry; TDZ on write. **341→372 (78.6%)**.  
- **Done (M20d):** OBJ_SPREAD string/array index keys; array dstr try→`ITER_CLOSE` on throw; LRef-before-IteratorStep; `ITER_CLOSE` kind 0/1; CallFunc restore. Assign **372→395**.  
- **Done (M20e):** GenReturn closes open iter (rtrn-close); track open_iter on GET_ITER; GET_ITER defers next-callability; close suite **47/47**. Assign **395→407 (86.0%)**.  
- **Left:** yield-ident residual; put-let TDZ free; S11 with/eval; fn-name; ~12 timeouts.



### Full scorecard 2026-07-15 (post-M26k)
- **Full:** 19244/49998 (**38.5%**), T/O 55, error 56. JSON: `/tmp/full49k.json`
- **Language:** 16278/24744 (**65.8%**) — up from ~59.9% post-M20e.
- **Built-ins:** 2804/23770 (**11.8%**) — core libs partial; desert is Temporal/TA/collections.

#### Active tirage (post-M26k) — knock out 1→5

| # | Target | Why | Gate / notes |
|---|--------|-----|--------------|
| **1** | **class/elements residual** | Largest language fail mass left inside class | static private, private setters, async private; elements **1777/2962 (60%)** |
| **2** | **core built-ins Array / Object** | High leverage; language already depends on them; getting close | Array ~21%, Object ~19%; method/descriptor depth — **not** Temporal/TA |
| **3** | **for-await-of / async** | Second language fail mass after class | for-await-of **47%** (653 fails); M28 track; needs async foundation |
| **4** | **Array length descriptor** | Last M26j Array subclass edge | **Done (M29e):** `subclass/builtin-objects/Array` **5/5** (legacy); gOPD w/e/c + truncate/RangeError |
| **5** | **Temporal / TypedArray / collections** | Only after core built-ins | See **OOS vs built-ins** below — not language-syntax residual |

**Also in queue (after / interleaved when unblocking):** M23 eval-code; M27 modules/dynamic-import; M25 for-of residual; M26e/i/h edges; M22 function residual.

#### Language fail mass (post-M26k full-run, largest absolute fails)
| Area | Fail ~ | Pass% | Notes |
|------|-------:|------:|-------|
| statements/class | 1313 | 70% | elements private residual dominates |
| expressions/class | 1178 | 71% | same |
| for-await-of | 653 | 47% | **#3** |
| dynamic-import | 588 | 41% | M27 |
| async-generator (expr) | 287 | 54% | M28 |
| object (expr) | 261 | 78% | residual |
| eval-code/direct | 255 | 11% | M23 |
| for-of | 203 | 73% | M25 residual |
| with | 163 | 10% | scope chain / M23 |

#### Built-ins: core vs deferred (not “language OOS syntax”)

test262 splits **`language/`** (syntax + semantics) vs **`built-ins/`** (standard library).  
The near-zero buckets are **not language-syntax OOS** — they are **library implementation tracks**. We still deprioritize them relative to language mass, but for different reasons:

| Bucket | Status | Treatment |
|--------|--------|-----------|
| **Core built-ins** — Array, Object, Function, String, Number, Boolean, Error, RegExp, JSON, Math, Promise (partial) | Partial; language/DOM already use them | **In scope soon** — tirage **#2** (Array/Object first). “Getting close” = surface exists, methods/descriptors incomplete |
| **Subclass hooks** — `extends Array/Error` | Error + Array SuperCall landed | tirage **#4** length attrs; other natives as needed |
| **Deferred library tracks** — Temporal (~4.5k), TypedArray family (~2k), DataView, Map/Set/WeakMap/WeakSet, Proxy, Reflect, Atomics, ArrayBuffer, SharedArrayBuffer, Iterator helpers | ~0% | **Separate tracks** after core Array/Object. Standard ES, but huge greenfield — do **not** count as language residual moles |
| **Staging / annexB piles** | Mixed | Only when unblocking a language mole |

So: Temporal/TypedArray are **out of the language-mole tirage**, not “invalid JS.” They’re real features that live under `built-ins/` and wait until core libs are honest.

**Last-round treatment for built-ins:** Language moles first (tirage #1, #3). Core Array/Object (#2) when language mass plateaus — “getting close,” method/descriptor depth. Desert libraries (#5: Temporal, TypedArray, Map/Set, Proxy, Atomics, …) get the **last round** only after core built-ins are honest — not interleaved with class/async.

#### Mole order (current)
M26 foundation **done** (a–k). Next: tirage **1→5** above.  
Legacy M22→M23→M24→M25→M27→M28 still valid as supporting tracks when a tirage item depends on them (e.g. #3 needs async/M28; modules stay M27).

### M26 progress
- **Done (M26a–d):** super.prop; default `super(...args)`; CONSTRUCT rest; fdesc+88 class kind; CallFunc/bound bare TypeError; SuperCall object rebind; derived return TypeError; bound CALL dispatch. Subclass non-builtin **23/37**.

#### M26 remainder pack (knock out 1-by-1)

| # | Mole | Target | Why | Gate slice |
|---|------|--------|-----|------------|
| **a** | **M26e** | derived `this` TDZ + double-`super` + super-must-be-called | Foundational | `definition/this-*` |
| **b** | **M26f** | `extends null` heritage | Small, pure class eval | `class-definition-null-proto*` |
| **c** | **M26g** | static `super` (methods/get/set) | SuperBase for static = parent ctor | `super/in-static-*` |
| **d** | **M26h** | `new.target` | Meta property | `new.target` under class/functions |
| **e** | **M26i** | class definition residual | methods/accessors/name/length/proto | `definition/*` minus this-TDZ |
| **f** | **M26j** | builtin subclassing | `extends Array/Error/...` | `subclass/builtin-objects` |
| **g** | **M26k** | private fields/methods | Largest mass — last | `elements/private*`, `#` |

**Order:** a→b→c→d→e then f; **g last**.

- **Done (M26e / remainder a):** `this_tdz` flag + GET_GLOBAL `this` TDZ; SuperProperty TDZ; `frame_this_st` UNINIT/INIT; first SuperCall binds construct `this`; double SuperCall runs parent then RefError on bind (-3); SuperCall only when callee is class parent or `__super__`; derived undefined return uses GetThisBinding (super object return). **this-check-ordering PASS**.  
- **M26e residual:** full `this-access-restriction{,-2}` (extends Object SuperCall native; double-super after object-return base).  
- **Done (M26f / remainder b):** `null.prototype` → null for extends-null wiring; `null-proto-super` TypeError on `super()`; `class-definition-parent-proto-null` PASS. Residual: `Object.getPrototypeOf(function)` vs `Function.prototype` identity (deeper, M26i).  
- **Done (M26g / remainder c):** static SuperBase = `this.__super__`; FUNCTION getters/setters; CALL_METHOD restores this; assign `obj.prop=` leaves RHS. Super suite **8/8**.  
- **Done (M26h / remainder d):** parse/compile `new.target`; CONSTRUCT sets `__new_target__`, CALL clears (SuperCall keeps). new.target suite **6/14** (core call/new/fpapply/fpcall). Residual: super/Reflect/ASI/member.  
- **Done (M26i / remainder e):** getPrototypeOf(Function); class prototype/constructor descriptors; methods non-enumerable + no .prototype; gOPD accessors; extends [[Prototype]]; multi-level SuperCall this-TDZ. definition **30→39/65**.  
- **Done (M26j partial / remainder f):** Error SuperCall reuses this + new.target; CALL/CALL_SPREAD SuperCall finish for natives; Error.prototype stamp. Error suite 2/3. Array/etc. residual.  
- **Done (M26k / remainder g foundation):** weak brand private fields/methods — skip CLASS_FIELD method install (was bogus method-install of `#fields` during class eval); GET/SET TypeError without brand; private_init on field_init; hide # from Object.keys; field_init this. elements private-named **494/994 (~50%)**; private\* overall **~69%**. Residual → tirage **#1**: static private, private setters, async private, true brands.
- **Done (M26j Array polish):** SuperCall→Array ctor via CALL_SPREAD StringMethod + this-init; stamp `[[Prototype]]` from `new.target.prototype`. Array **4/5**. Residual → tirage **#4**: length descriptor attrs.
- **M26k.2–3 (tirage #1 crumbs):** static private; accessor brand (`__get_#`/`__set_#`); getter-only SET TypeError; hide `#` from hasOwn/gOPD. elements private **1302/1894 (68.7%)**, non-async **~77%**. Residual (defer): async private, unicode privatename stringvalue, true nested brands, BigInt receiver, super-init order.
- **M29a–b (tirage #2 Object):** defineProperty ToObject/mixed/non-callable get-set; empty-desc creates prop (defaults all-false); real **defineProperties**; preventExtensions/isExtensible. Slice defineProperty+defineProperties+extens **797/1841 (43.3%)** (defineProperty alone was ~21%). Residual: redefinition edges, symbols, Array sparse holes.
- **M29c (Array holes):** elision→PUSH_HOLE; ArrHas (raw 0); ArrSet grow with holes; `in` on array indices; methods skip holes. Array overall **21.2%** (was 21.0%) — foundation in place; bulk fails remain species/thisArg/ToObject/length. Residual Object redef + Array depth.
- **M29d (Array call/array-like partial):** CallFunc dispatches natives (abs.call); map/forEach TypeError on null this / non-callable; array-like helpers; call arg-buffer overlap fix. map+forEach+filter **28.2%** (was ~25%). Residual: Function.prototype.call on natives still weak for array methods (shared env/this), species, length attrs.
- **M29e (tirage #2 gaps 1–3 + #4 length):** permanent `Array.prototype.*` natives (push/map/every/…); `.call`/`.apply` this-prefer for array methods; every/some/reduce array-like + TypeError; reduce 4-arg callback; gOPD array length `{w:true,e:false,c:false}`; `arr.length=` ToUint32/RangeError + ArrSetLen truncate/grow. map+forEach+filter **55.5%** (was 28.2%); every+some+reduce **54.7%**; Array/length **40.7%**; subclass Array **5/5**. Residual: species, reduceRight, Object redef, deep length defineProperty edges.
- **M29f (method depth):** find/findIndex array-like+TypeError+thisArg, **visit holes** (Get every index); indexOf/lastIndexOf/includes array-like; **reduceRight** (id 174); **flatMap** real impl; **Array.from** array-like+mapFn; keep 172–173 values/iterator on Bridge (not StringMethod). map+forEach+filter **56.0%**; find/findIndex **65%**; indexOf **67%**; reduceRight **46%**; from **32%**. Residual: species, includes SameValueZero (NaN), Object redef, length defineProperty depth.
- **Next (tirage #2 cont.):** species / Object residual / includes NaN. Then #3 async; #5 desert last.

### M22 progress
- **Done (M22a):** Arrow formal default+pattern wrap → arrow **92.4%**.
- **Done (M22b):** Formal TDZ for defaults → trio **87.8%** (929/1058); arrow **93.0%**.
- **Left:** lexical this/super/new.target; scope-body-lex; strict 13.x; annexB function-code.

### M21 progress
- **Done:** IterableToArray throw/getter/gen; call **79%**; spread-err **16/16**.  
- **Left on call:** eval-spread (M23), TCO (skip), object-spread, with.

---

## Strong foundations (do not regress)

| Area | Status |
|------|--------|
| dstr (fn+gen) | 100% |
| generators | 90% (FDI-at-call, nest GenNext) |
| Function.name/length/call/apply/bind | M18 |
| mapped arguments | 43/43 |
| batch isolation | M18b gval rewind |
| control flow / keywords / ASI / block-scope | strong |

---

## History (compact)

| When | What |
|------|------|
| M15–16 | dstr 186/186, mapped 43/43 |
| M17a–c | GenNext CALL-like first-resume; assign clobber; FDI-at-call + nest → gen dstr **372/372**, gens **473→502** |
| M18 | Function.name/length + call/apply/bind + gen [[Prototype]] |
| M18b | Batch gval_pool rewind → language-all **42%→56%** (+3321 pure honesty) |
| M19a | Number/Boolean/String boxing + ToNumber unbox → compound **38%→59%** |
| M19c | `JSRT__ParseNumberStr` — string ToNumber invalid→NaN (not 0) |
| M19d | Number.Inf/NaN; Mod NaN edges; ToPrimitive; compound bracket key-once → compound **65.6%** |
| M20a | assignment LHS-first for `base[prop]=`; SET_ELEM single ToPropertyKey → assign **63.5%** |
| M20b | dstr-assign: cover default swap; stack pollution fix; RHS result stash → assign **74.9%** |
| M20c | dstr member targets + const TypeError on reassign → assign **78.6%** |
| M20d | obj-rest-str; thrw/nrml IteratorClose + LRef-first; CallFunc restore → assign **83.5%** |
| M21 | IterableToArray throw/getter/gen rethrow → call **69%→79%**, spread-err **16/16** |
| M22a | `Object.prototype.isPrototypeOf`/`hasOwnProperty`; CONSTRUCT accepts fn as .prototype → function stmt **80%→81%** |
| Scorecard 2026-07-14 | language-all **13441/23899**; gens 90%; function stmt 81%; call **79%**; compound **66%** |
| Full 2026-07-14 post-M20e | full **17617/49998 (35.3%)**; language **~59.9%**; assign **86%**; close **47/47** |
| M22a | arrow formal default+pattern wrap → arrow **92.4%** |
| M22b | formal TDZ defaults → trio **87.8%** |
| M26a–d | super/default-ctor/rest/class-kind/bare-call |
| M26e–i | this TDZ; extends null; static super; new.target; definition descriptors |
| M26j | Error + Array SuperCall subclassing (Array 4/5) |
| M26k | private fields foundation (weak brand); elements private ~50% |
| Full 2026-07-15 post-M26k | full **19244/49998 (38.5%)**; language **65.8%**; built-ins **11.8%**; class\* **~70%** |

---

## Agent rules

1. Midgate green after every mole.  
2. No false greens — generators/function/call claim only with `--no-batch` when in doubt.  
3. Update this file when a mole closes (one row in History + Status numbers).  
4. Smells → `AILANG-WARTS.md`.  
5. Compliance > speed. Wrap > write.
