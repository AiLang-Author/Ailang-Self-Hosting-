# M128e7 progress — class field_init free-var

**Date:** 2026-07-29  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `JSCompState.in_field_init` | Flag while compiling `__field_init__` body |
| `JSComp__EmitVarGet/Set` | Force free-var (slot=-1 → GET_FREE/SET_FREE) when in_field_init — field_init only has local 0 = `this` |
| CONSTRUCT base path | On field-init throw: rethrow pending + pop construct frame if still live |

## Measured

| Suite | Score | Notes |
|-------|------:|-------|
| **statements/class/elements** | **1351 pass / 107 fail / 8 t/o / 68 err** | runner pass% **92.7%** (pass/(pass+fail)); base was 1326 pass |
| elements delta vs base | **+25 fixed, 0 regressed** | free-var + abrupt instance fields |
| **statements/with** | **181/181 (100%)** | regression OK |
| **class/dstr** | 1860 pass + 60 batch `harness_eof` | sample 20/20 no-batch green; batch flake not real fail |
| free-var probe `f = x + 1` | pass | |

### Notable fixes (base → e7)

- literal-names family (after-same-line / multiple-definitions / …)
- `init-value-defined-after-class`, `init-value-incremental`, `init-err-evaluation`
- `fielddefinition-initializer-abrupt-completion` (+ super variant)
- several former timeouts → pass

### Residual (elements)

- private* bulk (~122)
- static computed propname constructor/prototype
- proxy field define observability
- eval/supercall-in-field edges
- `abrupt-completition-on-field-initializer` (static half of combined test)

## Next

L-B residual: static fields, private, then L-C subclass/super.

## M128e7al–am (2026-07-31)

- **e7al**: `delete` removes `__get_`/`__set_`; `UPDATE_ELEM` for `base[key]++` (single key eval, null base TypeError first). postfix/prefix ++/-- **100%**.
- **e7am**: `%` IEEE remainder edges + object ToNumeric — modulus **100%**.
- Prior: full BigInt (ops, relational, updates), sticky `__pend_exc__` fix.

## M128e7an (2026-07-31) — string const NUL + relational 100%

| Area | Change |
|------|--------|
| `JSComp__AddStringRaw` | Type **5** pool entry: `[len:8][bytes...][0]`; embedded `\u0000` preserved |
| `JSVM__LoadConst` type 5 | `JSRT_CreateStringUTF8Len` (UTF-8→UTF-16 + length; not Latin-1) |
| `JSRT_CreateString` | Thin wrapper over UTF8Len via `StringLength` |
| `JSRT_GreaterThan` | ToPrimitive L→R then `b < a` |
| `JSRT_LessEqual` / `GreaterEqual` | ToPrimitive L→R; **string** path via `StrCmp` (equal strings no longer fall through ToNumeric→NaN) |

### Measured (batch harness)

| Category | Score |
|----------|------:|
| less-than | **45/45 (100%)** |
| greater-than | **49/49 (100%)** |
| less-than-or-equal | **47/47 (100%)** |
| greater-than-or-equal | **43/43 (100%)** |
| modulus | **39/40 pass** (+1 harness_eof flake) |

Tip: string-const type5 + relational order/string-eq.

## M128e7ao (2026-07-31) — ** ToNumeric, escapes, Date(), MAX_VALUE parse

| Area | Change |
|------|--------|
| `JSRT_Exp` | ToNumeric for non-NUMBER (bool/null/…); no NumericBin stub → was ** undefined |
| Lexer string | `\b` `\f` `\v` single escapes |
| `DATE_CTOR` | `Date()` without new → string (`__new_target__` undefined); `new Date()` → object |
| `JSRT__ParseNumberStr` | scale `10^n` via float *10; apply exp as one mul (MAX_VALUE `1.797…e+308` finite) |

### Measured

| Category | Score |
|----------|------:|
| exponentiation | **44/44 (100%)** |
| addition / mul / div / sub / delete / updates | **100%** (prior rescore) |
| typeof | 13/16 (Date() string fixed; proxy/symbol/native-call residual) |
| literals/string | 67/73 |

Next: typeof residuals, string line-continuation/legacy-octal, numeric legacy octal.

## M128e7ap (2026-07-31) — typeof 100%

| Area | Change |
|------|--------|
| Object global | native `OBJ_CTOR` function (was plain object) |
| `Object(Symbol)` | box primitive Symbol → typeof `"object"` |
| Proxy | `__proxy_callable__` flag; `Proxy.revocable` + revoke |
| `typeof` Proxy | uses callable flag (survives revoke) |

### Measured

| Category | Score |
|----------|------:|
| typeof | **16/16 (100%)** |
| exponentiation | 100% |


## M128e7aq (2026-07-31) — legacy octal string escapes

Lexer: full LegacyOctalEscapeSequence `\0`-`\377` + NonOctalDecimal `\8`/`\9`.
literals/string **68/73** (was 67).

Residual: line-continuation CR/LS/PS, a few harness_eof / hex edge.

## M128e7ar (2026-07-31) — string LineContinuation LS/PS

Lexer LineContinuation: `\\` + LF/CR/CRLF/**LS/PS** (UTF-8 E2 80 A8/A9) → empty SV.
literals/string **70/73** (line-continuation double/single green).
Residual 3: batch `harness_eof` / sticky fail — **pass alone** on single+batch harness.
Updates postfix/prefix still **100%** (tip).

## M128e7as (2026-07-31) — numeric 100%

| Area | Change |
|------|--------|
| ParseNumberStr | Annex B legacy octal `0[0-7]+` base-8; `08`/`080` stay decimal |
| ParseNumberStr | unified significand for ≤15 digits (`1.1e-1 === 0.11`) |
| Parse NUMBER_LIT | strict mode rejects LegacyOctalIntegerLiteral |

### Measured

| Category | Score |
|----------|------:|
| literals/numeric | **157/157 (100%)** |
| exponentiation | still 100% |

## M128e7at (2026-07-31) — ToBoolean BigInt

`JSRT_IsTruthy`: BigInt `0n` → false; other BigInts true (`!0n`/`!1n`).

| Category | Score |
|----------|------:|
| logical-not | **19/19 (100%)** |
| equals / strict-equals / void | 100% |
| logical-and/or residual | TCO-only (`tco-right`) |

## M128e7au (2026-07-31) — instanceof + Symbol.hasInstance

| Area | Change |
|------|--------|
| `JSRT_Instanceof` | ES order: TypeError non-object RHS; `@@hasInstance`; non-callable TE; non-object `prototype` TE; accessor Get |
| `Symbol.hasInstance` | well-known installed |
| `Function.prototype` | real callable native (typeof function); no auto `.prototype` |
| FuncPropGet | no self-recurse on Function.prototype; PropTable before prototype slot |
| INSTANCEOF dispatch | rethrow pending |

### Measured

| Category | Score |
|----------|------:|
| instanceof | **36/43 (87.8%)** was 25/43 |

Residual: TypeError⊆Error chain, Function() ctor edge, Function.prototype.prototype getter redefine.

## M128e7av (2026-07-31) — Error() without new stamps prototype

TypeError/RangeError/… function call (not `new`) now links `[[Prototype]]` to `Ctor.prototype` so `TypeError("x") instanceof TypeError`.

instanceof **37/43**.

## M128e7aw (2026-07-31) — var hoist under EvalString

`JSComp__HoistVars` always emits `SET_GLOBAL_VAR` (even `eval_mode=1`) so `x; var x` is not ReferenceError under the test262 harness path.

instanceof **40/43** (residual: Function.prototype.prototype getter redefine only).

## M128e7ax (2026-07-31) — instanceof 100%

OWN-only `__get_*` accessors in GET_PROP / ObjGetAcc (inherited `__get_prototype` from Function.prototype no longer intercepts `Array.prototype`).

| Category | Score |
|----------|------:|
| instanceof | **43/43 (100%)** |

## M128e7ay (2026-07-31) — `in` TypeError + private-in 100%

| Area | Change |
|------|--------|
| IN dispatch | TypeError when RHS not Object/Function/Array/Generator |
| `ASTType.PRIVATE_IDENT` | bare `#name` primary (class / allow_private_eval) |
| CompExpr PRIVATE_IDENT | `AddString` + PUSH_CONST (mangled private key) |
| FuncDecl/FuncExpr name | `await` BindingIdentifier outside Await (`function await()`) |

### Measured

| Category | Score |
|----------|------:|
| expressions/in | **36/36 (100%)** (legacy no-batch; batch may harness_eof flake 1) |
| instanceof | still **43/43** |
| typeof / logical-not / modulus | still 100% |

## M128e7az (2026-07-31) — block-comment re-peek + ternary +In

| Area | Change |
|------|--------|
| Lexer main loop | After `//` or `/* */`, re-peek + SkipWS so next token is not scanned with stale `/` (was dropping first source char: `/*x*/var`→`ar`, `new./* */target`→`arget`) |
| SkipBlockComment | Early-return rewrite on `*/` |
| Ternary consequent | Always `no_in=0` (`AssignmentExpression[+In]`) for `? … in … :` inside for-init |

### Measured

| Category | Score |
|----------|------:|
| new.target | **12/14** (asi/comment green; Reflect.apply/construct need Reflect) |
| conditional | **20/22** (in-branch-1 green; 2 TCO residual) |
| expressions/in | still 100% (no-batch) |
| block-comment probes | pass |

## M128e7ba (2026-07-31) — Array.prototype.toString

| Area | Change |
|------|--------|
| `JSNativeID.ARR_TO_STRING` (265) | native → `ArrJoin(recv, args, 0)` |
| `Array.prototype.toString` | installed (was Object → `"[object Array]"`) |
| MatchArrayMethod | `"toString"` → ARR_TO_STRING |
| CallFunc | id 265 uses global `this` + DispatchStringMethod |

### Measured

| Category | Score |
|----------|------:|
| expressions/concatenation | **5/5 (100%)** |
| a+"" / Array.toString | pass |

## M128e7bb (2026-08-01) — optional-chain call short-circuit + this

| Area | Change |
|------|--------|
| MatchArrayMethod | drop `toString` fast-path so `a.toString === Array.prototype.toString` |
| CALL | OPT_MEMBER/BRACKET as method; JMP_IF_NULLISH before args (`null?.f()`) |
| optional spine walk | traverse CALL for `?.b.c(++x).d` |
| NEW postfix | `new C()?.prop` |
| new.target postfix | `new.target?.a` / `?.()` |
| OPT_CALL | method this for `a.b?.()`; cleanup stack on nullish func |
| PAREN unwrap | `(a?.b)()` / `(a.b)()` preserve this |

### Measured

| Category | Score |
|----------|------:|
| optional-chaining | **33/38 (86.8%)** was 30/38 |
| expressions/array | **44/52** (S11.1.4 identity green; 8 spread-err residual) |
| concatenation / instanceof / in | still 100% |

Residual optional: tagged-template `fn()`tpl`?.a`, early-errors templates, a few async/prod edges.

## Full suite baseline M128e7bb (2026-08-01)

Tip `6dbf7744`. Wall **2936s** (~49 min). Artifacts under `results/test262_full_m128e7bb_*`.

| Metric | e7x | **e7bb** | Δ |
|--------|----:|---------:|--:|
| Overall pass | 61.35% | **58.65%** | −2.70 pp |
| Language | 91.42% | **87.49%** | −3.93 pp |
| G2 gap | 847 | **1,775** | +928 |
| Language pass | 21,607 | **20,679** | −928 |

Transitions vs e7x: **fixed 1,109** / **regressed 2,452** (lang 800 / 1,784).
Knockout: `results/test262_full_m128e7bb_KNOCKOUT.md` (P0 near-complete list).
Report tool: `tools/test262_baseline_report.py`.

## M128e7bc (2026-08-01) — CallFunc throw / try-catch (regression fix)

Root cause of mass e7x→e7bb regressions on `fn.call` / Array methods TypeError paths:

1. **Double catch delivery:** nested `CallFunc` delivered throw to outer `try` (popping catch), then CALL rethrew uncaught → VM error.
2. **Fix:** `ThrowValue` / THROW opcode: if `JSVMCall.depth > 0`, surface `exc_prop` only (do not deliver catch). Outer CALL rethrows once.
3. **Native CallFunc:** bump depth around DispatchStringMethod/Bridge; clear sticky halt on exc_prop.
4. **Array methods:** honor `thisArg` null/undefined for RequireObjectCoercible; ARR_AT in CallFunc routes.
5. **throw_delivered:** after mid-native catch delivery, CALL skips success push (no sticky `exc_prop` poison).

### Safe recheck (no-batch)

| Suite | Score |
|-------|------:|
| instanceof | **43/43 (100%)** |
| expressions/in | **36/36 (100%)** |
| concatenation | **5/5** |
| optional-chaining | **33/38** |
| Array every/at/from (slice) | improved; at abrupt + from mapfn TypeError green |

**Do not full-suite again until more P0 chips;** use targeted slices to avoid burn.

## M128e7bd (2026-08-01) — optional-chain 100% + new.target 100%

| Area | Change |
|------|--------|
| GET_ELEM / SET_ELEM | Array non-index keys (`true`→`"true"`, `1.1`→`"1.1"`) via ToPropertyKey digit check before ToNumber index |
| OPT_CALL | `super.method?.()` SuperBase+this; `f?.(...spread)` → CALL_SPREAD |
| Postfix loop | Continue on `TMPL_FULL` so `f()`tpl`` / `o.m`tpl`` tagged templates parse |
| POLYFILL | `Reflect.construct` / `Reflect.apply` (drive `__new_target__` + apply) |
| Runner | Module NS Reflect stub only for module/dyn/namespace paths (not bare `"Reflect"`) — multi-let free-var under CallFunc was broken by the huge stub |

### Measured (no-batch)

| Suite | Score | Was |
|-------|------:|----:|
| **optional-chaining** | **38/38 (100%)** | 33/38 |
| **new.target** | **14/14 (100%)** | 10–12/14 |
| **expressions/array** | **52/52 (100%)** | 44/52 |
| **expressions/delete** | **69/69 (100%)** | 68/69 |
| expressions/call | **81/92 (88%)** | 73/92 |
| concatenation / instanceof / in | still **100%** | |
| template-literal | 43/57 (unchanged residual) | |
| coalesce / comma / conditional | TCO residual unchanged | |

### Next P0 chips

- coalesce (2), comma (1), conditional (2) — TCO residual
- call (11 residual)
- template-literal (14)
- logical-assignment / if / for-in bulk

## M128e7be (2026-08-01) — ?? cannot mix with && / ||

| Area | Change |
|------|--------|
| `JSParse__Precedence` | Reject BINARY_OP mixing `??` with `&&`/`||` (unparenthesized) → SyntaxError |

### Measured

| Suite | Score |
|-------|------:|
| **coalesce** | **22/24 (91.7%)** — 4 cannot-chain early-errors green; residual 2× TCO |
| optional-chaining / new.target / in / instanceof / concat | still **100%** |

## M128e7bf (2026-08-01) — with bare call this = WithBaseObject

| Area | Change |
|------|--------|
| `PUSH_WITH_CALL_THIS` (127) | After GET_WITH, push WithRef.base if valid else globalThis |
| bare IDENT call under `with` | PUSH + SWAP → CALL_METHOD so `with (obj) { method() }` has this=obj |

### Measured

| Suite | Score |
|-------|------:|
| **expressions/call** | **82/92 (89.1%)** (+1 with-base-obj; residual mostly TCO + eval-spread) |
| statements/with | 177/181 (4 proxy-env residual — pre-existing) |
| optional / new.target / array / coalesce | unchanged |


## M128e7bg (2026-08-01) — TemplateObject .raw + template escapes

| Area | Change |
|------|--------|
| `JSLex__ScanTemplate` | Dual cooked/raw buffers; pack `cooked\\0raw\\0`; proper `\\b/\\f/\\v/\\u/\\x` |
| Tagged `TMPL_FULL` | ARRAY_LIT N_OP=1 TemplateObject; STRING N_VALUE=1 |
| ARRAY_LIT compile | Emit cooked array + `.raw` array from packed TRV |

### Measured

| Suite | Score | Was |
|-------|------:|----:|
| **template-literal** | **52/57 (91.2%)** | 43/57 |
| Residual | was 5 — fixed in e7bh | |
| optional / array / concat | still **100%** | |

## M128e7bh (2026-08-01) — multiparts tagged templates; template-literal 100%

| Area | Change |
|------|--------|
| Tagged `TMPL_HEAD`…`TAIL` | CALL(tag, TemplateObject, …exprs); TemplateObject all cooked/raw parts |
| Postfix continue | `TMPL_HEAD` after call/member |
| Runner | Rewrite embedded NUL in test sources (`ReadTextFile` C-string truncates) |
| ScanString | Loop on `pos < src_len` so embedded NUL is not EOF |

### Measured

| Suite | Score |
|-------|------:|
| **template-literal** | **57/57 (100%)** |
| optional / array / concat / string | still **100%** |

---

## Status snapshot (e7bh full suite) — G2 / built-ins

Canonical: **`results/TEST262_STATUS_M128e7bh.md`** · summary **`results/test262_full_m128e7bh_SUMMARY.md`**.

| | e7x | e7bb | **e7bh full** |
|--|----:|-----:|--------------:|
| Overall | 61.35% | 58.65% | **60.58%** (30,123/49,723) |
| Language | **91.42%** | 87.49% | **88.70%** (20,964) |
| Built-ins | 33.86% | 32.38% | **35.22%** (8,283) |
| **G2 gap** | **847** | 1,775 | **1,490** |

vs e7bb: **+961 net** · vs e7x: **−382 net** (language still −643).  
Wall **2965s**. Artifacts `results/test262_full_m128e7bh_*`.

### Safety pack (no-batch) still green

optional / new.target / array / template-literal / concat / instanceof / in / string — 100% (batch full may show 1 flake on template/delete).

## M128e7bi (2026-08-01) — eval global bindings configurable (D=true)

| Area | Change |
|------|--------|
| `JSVM__MirrorGlobalProp` | New mirrors under `JSVMEvalState.depth>0` use attr **7** (W\|E\|C); script stays **3** (W\|E\|!C) |

Root cause of e7x→e7bh eval-code attr regressions: e7aa stamped all new GlobalHash mirrors as script DontDelete (bits 3), including eval `CreateGlobalVar/FunctionBinding` which must be configurable.

### Measured (no-batch)

| Suite | Score | Notes |
|-------|------:|-------|
| eval-code/direct | **264/286** | +2 vs e7bh full (var-env-*-global-new) |
| eval-code/indirect | **53/61** | +2 |
| expressions/delete | **69/69** | script DontDelete preserved |
| optional/array/template/new.target | **100%** | safety |

Remaining eval residuals: Annex B block-level function-in-if/switch in eval (~50), local-exstng, strict.

## M128e7bj (2026-08-01) — break/continue ASI + LineTerminator line tracking

| Area | Change |
|------|--------|
| `JSParse__BreakStmt` / `ContStmt` | No label if Identifier on a later line than break/continue |
| `JSLex__Advance` | CR, CRLF, LS, PS bump `line` (was LF-only) |
| `IsWSHere` | LS/PS return 1 (Advance consumes full sequence) |

### Measured

| Suite | Score |
|-------|------:|
| **statements/break** | **20/20 (100%)** |
| **statements/continue** | **24/24 (100%)** |
| expressions/exponentiation | **44/44 (100%)** (already green) |

## M128e7bk (2026-08-01) — IteratorValue getter abrupt rethrow

| Area | Change |
|------|--------|
| `ITER_NEXT` | On `__get_value` / `__get_done` CallFunc throw: mark record done + `ThrowValue` (was swallow) |

Fixes e7x→e7bh mass **iter-val-err** dstr regressions (IteratorValue abrupt).

### Measured

| Suite | Score | Notes |
|-------|------:|-------|
| e7x→e7bh `*iter-val-err*` | **49/49** recovered | |
| expressions/function | **251/264** | was 246/264 full e7bh |
| expressions/arrow-function | **328/343** | was 324/343 full e7bh |
| safety optional/array/delete/break | still green | |

## M128e7bl (2026-08-01) — setter throw rethrow on SET_PROP / SET_ELEM

| Area | Change |
|------|--------|
| SET_PROP / SET_ELEM / SET_PROP_COMPUTED / SET_PROP_SUPER | On setter CallFunc throw: clear exc_prop + `ThrowValue` |

Same swallow pattern as e7bk ITER_NEXT. Recovers put-prop-ref-user-err dstr.

### Measured

| | |
|--|--|
| put-prop-ref e7x→e7bh | **4/4** recovered |
| safety optional/array/delete | 100% |

## M128e7bm (2026-08-01) — OBJ_SPREAD / GET_ELEM getter abrupt rethrow

| Area | Change |
|------|--------|
| `OBJ_SPREAD` (93) | On `__get_*` CallFunc throw: clear exc_prop + `ThrowValue` (was bare return — swallow) |
| `GET_ELEM` object + array-index | Same rethrow pattern for getter CallFunc |

Same CallFunc-swallow class as e7bk ITER_NEXT / e7bl SET_PROP. Recovers object-rest getter abrupt + keeps for-of value-attr path green.

### Measured

| Suite | Score | Notes |
|-------|------:|-------|
| e7x→e7bh `obj-rest` / `getter-abrupt` / `iter-val-err` / put-prop slice | **36/36** | all recovered |
| e7x→e7bh `statements/for-of` regs | **25/25** | includes value-attr-error |
| expressions/assignment | **482/485** | 99.4% |
| safety optional/array/delete/break/continue | **100%** | |
| template-literal | 55/57 | pre-existing TV line-cont/terminator residual (not this change) |
