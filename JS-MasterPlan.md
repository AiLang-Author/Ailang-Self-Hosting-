> **ARCHIVED 2026-08-05.** Canonical: [`Docs/Browser/JS_ENGINE_MASTER.md`](./Docs/Browser/JS_ENGINE_MASTER.md)

# Test262 100% Conformance Plan — AILang JS Engine

> **Superseded for day-to-day grind:** use [`BROWSER_CONFORMANCE.md`](./BROWSER_CONFORMANCE.md) (product bars + scoreboard) and [`JS-DEPENDENCY-PLAN.md`](./JS-DEPENDENCY-PLAN.md) (moles).  
> This file remains historical Phase planning. **2026-07-16 reality:** full suite **21783/49998 (43.6%)**, language **~68%**, Object **~54%**, Array **~49%** — multi-phase path to 75%+ browser track, not “stuck at 42%.”

## Current State (historical July baseline below)
- **3,121 / 7,689 passing (41.7%)**, 4,360 fails, 116 timeouts
- Engine: ~28K lines across 22 AILang source files

## Failure Breakdown (4,360 fails + 116 timeouts)

| Root Cause | Count | % | Fix Complexity |
|------------|-------|---|----------------|
| Spread/rest operator (`...`) bugs | 873 | 19.5% | MEDIUM — parser has it, runtime broken |
| `assert.throws(ErrorType, fn)` — polyfill ignores error type | 552 | 12.3% | EASY — fix polyfill |
| `new Boolean/Number/String` wrapper objects missing | 325 | 7.3% | MEDIUM — add wrapper types |
| Error/throw semantics (throw in expressions, Error objects) | 364 | 8.1% | MEDIUM — Error constructor + try/catch fixes |
| `class` keyword gaps | 326 | 7.3% | HARD — mostly parsed, compiler/VM gaps |
| `Symbol` type missing | 282 | 6.3% | HARD — new type + iterator protocol |
| Property descriptors incomplete | 218 | 4.9% | MEDIUM — writable/configurable/enumerable |
| `eval()` not implemented | 213 | 4.8% | HARD — requires re-entrant pipeline |
| Try/catch semantics bugs | 213 | 4.8% | MEDIUM — exception propagation fixes |
| Generator runtime gaps | 215 | 4.8% | HARD — yield value passing, iterator |
| `arguments` object incomplete | 64 | 1.4% | MEDIUM — array-like binding |
| Labeled break/continue across loops | 18+ | 0.4% | EASY — already parsed, compiler gap |
| Strict mode enforcement | 131 | 2.9% | MEDIUM — propagate flag through pipeline |
| `with` statement | 85 | 1.9% | MEDIUM — scope chain manipulation |
| `let` as identifier edge cases (ASI) | 50 | 1.1% | EASY — parser fix |
| valueOf/toString coercion (ToPrimitive) | 17+ | 0.4% | MEDIUM — object-to-primitive |
| `delete` operator semantics | 52 | 1.2% | MEDIUM — return value, reference type |
| TCO / `$MAX_ITERATIONS` tests | 24 | 0.5% | SKIP — TCO not required by spec |
| Destructuring timeouts (hang) | 116 | 2.6% | BUG — infinite loop in destructuring |
| Default parameters | 91+ | 2.0% | MEDIUM — param scope, initializer eval |
| Getter/setter in objects | 15 | 0.3% | EASY — already has opcodes |
| Other (ASI, unicode, misc) | ~400 | 8.9% | VARIOUS |

## Implementation Phases (ordered by impact × ease)

### Phase 1: Low-Hanging Fruit (biggest gains, least effort)
**Target: 41.7% → ~58%**

#### 1A. Fix the test harness polyfill
- **File:** `tools/test262_runner.py` (lines 139-221)
- Fix `assert.throws(ErrorType, fn)` to validate the thrown error is `instanceof ErrorType`
- Add `assert._isSameValue()` with proper NaN and ±0 handling
- Fix `preprocess()` — stop converting ALL `throw new *Error()` to `$ERROR()`, this breaks tests that deliberately throw typed errors
- **Impact:** ~552 tests flip from false-fail to real result

#### 1B. Fix destructuring timeouts (116 tests hanging)
- **Files:** `JSCompiler/Library.JSCompStmt.ailang`, `JSVM/Library.JSVMDispatch.ailang`
- Debug: the `for(const [a,b] = ...; ...)` pattern hangs — likely infinite loop in destructuring pattern compilation or iterator dispatch
- **Impact:** 116 timeouts → actual pass/fail

#### 1C. Labeled break/continue across nested loops
- **Files:** `JSCompiler/Library.JSCompStmt.ailang`, `JSVM/Library.JSVMDispatch.ailang`
- Labels are parsed (LABELED_STMT AST node exists). Need: label stack in compiler, jump targets for `break label` / `continue label` that target outer loops
- **Impact:** ~18-40 tests

#### 1D. Try/catch/finally semantics fixes
- **Files:** `JSVM/Library.JSVMDispatch.ailang` (TRY_PUSH/TRY_POP/THROW handlers)
- Fix: exception in catch block, finally always runs, ReferenceError for undefined variables in try blocks, re-throw behavior
- **Impact:** ~213 tests

#### 1E. `delete` operator return value and reference semantics
- **File:** `JSVM/Library.JSVMDispatch.ailang`, `JSCompiler/Library.JSCompExpr.ailang`
- `delete obj.prop` must return true/false per spec
- `delete x` on unresolvable reference returns true
- `delete x` on var declaration returns false
- **Impact:** ~52 tests

#### 1F. ASI / `let` as identifier edge cases
- **File:** `Librarys/Browser/Library.JSLexer.ailang`, `JSParser/Library.JSParseStmt.ailang`
- `let` followed by newline before `{` or identifier = ASI, `let` used as identifier in non-strict
- **Impact:** ~50 tests

### Phase 2: Core Runtime Gaps
**Target: ~58% → ~75%**

#### 2A. Wrapper objects: `new Boolean()`, `new Number()`, `new String()`
- **Files:** `Library.JSBridge.ailang`, `Library.JSRuntime.ailang`, `JSRuntime/Library.JSRTCoerce.ailang`
- Add OBJECT subtypes for Boolean/Number/String wrappers
- `new Number(42)` creates object, `Number(42)` returns primitive
- ToPrimitive calls valueOf/toString on wrapper objects
- **Impact:** ~325 tests

#### 2B. Spread/rest operator runtime fixes
- **Files:** `JSVM/Library.JSVMDispatch.ailang` (CALL_SPREAD, ARR_EXTEND, TO_ARRAY), `JSCompiler/Library.JSCompExpr.ailang`
- Opcodes exist (ARR_EXTEND, CALL_SPREAD, TO_ARRAY) but runtime handling has bugs
- Fix: `f(...arr)`, `[...arr]`, `{...obj}`, rest parameters `function(a, ...rest)`
- **Impact:** ~873 tests (largest single bucket)

#### 2C. `arguments` object as array-like binding
- **Files:** `Library.JSVM.ailang`, `JSCompiler/Library.JSCompStmt.ailang`
- Create `arguments` local in every non-arrow function scope
- Set `arguments.length` = actual arg count
- Set `arguments[0]`, `arguments[1]`, ... = arg values
- `arguments.callee` in non-strict mode
- **Impact:** ~64 direct + unlocks many other tests

#### 2D. Property descriptors (writable, configurable, enumerable)
- **Files:** `JSRuntime/Library.JSRTObject.ailang`, `JSRuntime/Library.PropTable.ailang`
- PropTable entries need 3 flag bits: writable, configurable, enumerable
- `Object.defineProperty` must enforce flags
- `Object.getOwnPropertyDescriptor` must return descriptor object
- `Object.freeze` / `Object.seal` / `Object.preventExtensions` use descriptors
- for-in must skip non-enumerable
- **Impact:** ~218 tests

#### 2E. ToPrimitive / valueOf / toString coercion
- **Files:** `JSRuntime/Library.JSRTCoerce.ailang`
- When object used in arithmetic/comparison, call `valueOf()` or `toString()`
- Hint parameter: "number" tries valueOf first, "string" tries toString first
- **Impact:** ~17 direct + fixes many coercion edge cases across arithmetic/comparison tests

### Phase 3: Major Missing Features
**Target: ~75% → ~90%**

#### 3A. Error constructor objects
- **Files:** `Library.JSBridge.ailang`, `JSVM/Library.JSVMBuiltins.ailang`
- `Error`, `TypeError`, `RangeError`, `ReferenceError`, `SyntaxError` as constructable objects
- `err.message`, `err.name`, `err.stack` properties
- `instanceof Error` must work
- Engine must throw proper TypeError/ReferenceError/RangeError at appropriate points
- **Impact:** ~364 tests (error/throw) + enables proper assert.throws validation

#### 3B. `class` declaration/expression completion
- **Files:** `JSCompiler/Library.JSCompStmt.ailang`, `JSVM/Library.JSVMDispatch.ailang`, `Library.JSOop.ailang`
- Parser already handles class syntax
- Need: constructor calls, method definitions, static methods, super calls, extends, computed method names
- class expressions (anonymous classes)
- **Impact:** ~326 tests

#### 3C. `Symbol` primitive type
- **Files:** `Library.JSRuntime.ailang` (new type 9), `Library.JSBridge.ailang`
- `Symbol()`, `Symbol('desc')`, `Symbol.for()`, `Symbol.keyFor()`
- Well-known symbols: `Symbol.iterator`, `Symbol.toPrimitive`, `Symbol.hasInstance`, `Symbol.toStringTag`
- typeof Symbol() === "symbol"
- **Impact:** ~282 tests + prerequisite for iterators

#### 3D. Iterator protocol
- **Files:** `JSVM/Library.JSVMDispatch.ailang`
- Object with `[Symbol.iterator]()` returning `{next() → {value, done}}`
- Required for: for-of, spread, destructuring, Array.from, generators
- **Impact:** unlocks generators, for-of, spread fixes

#### 3E. Generator function runtime
- **Files:** `JSVM/Library.JSVMDispatch.ailang` (YIELD, GEN_CLOSURE handlers)
- Generator objects: `.next(value)`, `.return(value)`, `.throw(error)`
- Suspended execution state: save/restore PC, SP, locals
- Implements iterator protocol
- **Impact:** ~215 tests

#### 3F. `eval()` function
- **Files:** `Library.JSBridge.ailang`, `Library.JSEngine.ailang`
- Re-entrant: lex→parse→compile→run within current scope
- Direct eval: inherits calling scope
- Indirect eval `(0,eval)(...)`: uses global scope
- Strict eval: creates own scope
- **Impact:** ~213 tests

#### 3G. Strict mode enforcement
- **Files:** all compiler + VM files
- Propagate `is_strict` flag from parser through compiler to VM
- Strict mode rules: no `with`, no octal, no duplicate params, no `arguments`/`eval` assignment, `this` is undefined (not global), ReferenceError on undeclared assignment
- **Impact:** ~131 tests + many indirect

#### 3H. `with` statement
- **Files:** `JSParser/Library.JSParseStmt.ailang`, `JSCompiler/Library.JSCompStmt.ailang`, `JSVM/Library.JSVMDispatch.ailang`
- Dynamic scope: property lookup on with-object before outer scope
- New opcodes: PUSH_WITH_SCOPE, POP_WITH_SCOPE
- **Impact:** ~85 tests

### Phase 4: Edge Cases and Polish
**Target: ~90% → 100%**

#### 4A. Default parameters with proper scope
- Evaluate default in parameter scope (between outer and body scope)
- TDZ for parameters referencing later params
- **Impact:** ~91 tests

#### 4B. Getter/setter edge cases in object literals
- Already has DEF_GETTER/DEF_SETTER opcodes
- Fix: computed getter/setter names, getter/setter in classes
- **Impact:** ~15 tests

#### 4C. for-in semantics edge cases
- Property enumeration order
- Prototype chain enumeration
- Deleted properties during iteration
- **Impact:** ~12 tests

#### 4D. Remaining ASI rules
- Semicolon insertion after return/throw/continue/break + newline
- No LineTerminator before postfix ++/--
- **Impact:** ~50 tests

#### 4E. Unicode identifier support
- `\u{XXXX}` in identifiers
- Unicode categories for identifier start/continue
- **Impact:** ~20 tests

#### 4F. Remaining type coercion edge cases
- `+[]`, `+{}`, `"" + obj`, comparison with null/undefined
- Abstract relational comparison spec compliance
- **Impact:** scatters across arithmetic/comparison tests

#### 4G. TCO tests (24 tests)
- These use `$MAX_ITERATIONS` which is a test262 harness variable
- Need to either set it to a reasonable value in polyfill, or implement proper tail calls
- **Impact:** 24 tests

## Verification Strategy

After each phase:
```bash
# Rebuild harnesses
./ailang.x JS-tests/test262_harness.ailang test262_harness.x
./ailang.x JS-tests/test262_harness_batch.ailang test262_harness_batch.x

# Run full suite
python3 tools/test262_runner.py --output-json /tmp/test262_results.json

# Quick regression check
./test_js_e2e.x
```

Track pass rate after each sub-task. Any regression = stop and fix before proceeding.

## Critical Files (modification targets)

| File | Purpose | Phases |
|------|---------|--------|
| `tools/test262_runner.py` | Test harness polyfill | 1A |
| `JSCompiler/Library.JSCompStmt.ailang` | Statement compilation | 1B,1C,2C,3B,3H,4A |
| `JSCompiler/Library.JSCompExpr.ailang` | Expression compilation | 1E,2B |
| `JSVM/Library.JSVMDispatch.ailang` | Opcode dispatch | 1B,1C,1D,1E,2B,3B,3D,3E,3H |
| `Library.JSBridge.ailang` | Built-in registration | 2A,2C,3A,3C,3F |
| `JSRuntime/Library.JSRTCoerce.ailang` | Type coercion | 2A,2E,4F |
| `JSRuntime/Library.JSRTObject.ailang` | Object operations | 2D |
| `JSRuntime/Library.PropTable.ailang` | Property storage | 2D |
| `Library.JSRuntime.ailang` | Value pool, types | 2A,3C |
| `Library.JSVM.ailang` | VM init, frame mgmt | 2C,3E,3G |
| `Library.JSOop.ailang` | OOP/prototype | 3B |
| `Library.JSLexer.ailang` | Tokenizer | 1F,4E |
| `JSParser/Library.JSParseStmt.ailang` | Statement parser | 1F,3H |
| `Library.JSEngine.ailang` | Pipeline orchestrator | 3F |
| `JSVM/Library.JSVMBuiltins.ailang` | Built-in install | 3A |
