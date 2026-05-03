# AILang JavaScript Engine — Comprehensive Roadmap to 100% Test262 Compliance

**Current: 12,567/23,899 (52.6%)**
**Target: 100% (23,899/23,899)**

---

## Failure Breakdown (11,332 remaining)

| Category | Failures | % of Total | Blocked By |
|----------|----------|-----------|------------|
| Class/dstr (param destructuring) | 3,552 | 31.3% | async-gen overlap (640), Object.defineProperty |
| Async/await/Promise | 4,645 | 41.0% | No Promise type, no async/await syntax |
| Class private fields (#field) | 3,186 | 28.1% | No # token, no private storage |
| Class elements (fields, computed) | 2,164 | 19.1% | No field declarations, computed key compile |
| Destructuring (remaining edge cases) | ~800 | 7.1% | Iterator protocol, edge patterns |
| Float/numeric | 189 | 1.7% | Integer-only numbers |
| Template literals | ~37 | 0.3% | Tagged templates |
| let/const TDZ | ~200 | 1.8% | No TDZ enforcement |

Note: Heavy overlap — many tests hit 2-3 categories (e.g., async-gen-meth with dstr params).

---

## Phase 1: Highest-Impact Quick Wins (Target: +2,000 passes → ~61%)

### 1A. Computed Property Names in Classes
**Impact: ~500 tests** | Files: JSCompiler.ailang
- Parser already handles `[expr]` in class body (lines 4288-4304, stores in N_COND)
- Compiler `JSComp__CompileClass` ignores N_COND — only reads N_NAME_PTR/N_NAME_LEN
- Fix: Check N_COND field; if present, compile key expression and use SET_PROP_COMPUTED (opcode 63)

### 1B. Class Field Declarations (`x = 5` in class body)
**Impact: ~800 tests** | Files: JSParser.ailang, JSCompiler.ailang
- Parser `JSParse__ClassBody` only accepts methods (IDENT followed by `(`)
- Need: Detect IDENT NOT followed by `(` → field declaration
- Parse optional `= expr` initializer
- Compiler: Emit field initializations in constructor prologue (before user constructor body)
- Static fields: Initialize on constructor object after class creation

### 1C. `Object.defineProperty` / `Object.keys` / `Object.create`
**Impact: ~1,200 tests** | Files: JSRuntime.ailang, JSBridge.ailang
- Huge number of tests use `Object.defineProperty` in test setup
- Need: Property descriptor support (configurable, enumerable, writable, get, set)
- `Object.defineProperty(obj, name, descriptor)` — sets property with descriptor
- `Object.keys(obj)` — returns array of own enumerable string keys
- `Object.create(proto)` — creates object with specified prototype
- This unblocks thousands of tests across ALL categories, not just class

### 1D. Template Literal Improvements
**Impact: ~37 tests** | Files: JSParser.ailang, JSCompiler.ailang
- Tagged templates: `tag\`hello ${name}\``
- Pass template string array + substitutions to tag function

---

## Phase 2: Async/Await + Promises (Target: +4,000 passes → ~78%)

This is the single largest blocker. 4,645 tests require it.

### 2A. Promise Type (JSRuntime)
**New JSType: PROMISE = 9** (or 11 if FIXED types take 8-10)

Promise state block (similar to generator's 104-byte block):
```
Offset 0:  state (PENDING=0, FULFILLED=1, REJECTED=2)
Offset 8:  result (JSValue — resolved/rejected value)
Offset 16: then_handlers (linked list of {onFulfilled, onRejected, child_promise})
Offset 24: catch_handlers
```

Key functions:
- `JSRT_CreatePromise()` — allocate promise with PENDING state
- `JSRT_ResolvePromise(promise, value)` — transition to FULFILLED, run then handlers
- `JSRT_RejectPromise(promise, reason)` — transition to REJECTED, run catch handlers
- `JSRT_PromiseThen(promise, onFulfilled, onRejected)` — register handlers, return child promise

### 2B. Microtask Queue (JSVM)
- Simple FIFO queue (ring buffer, 1024 entries)
- Each entry: {callback_fn, arg_value}
- `JSVM__EnqueueMicrotask(fn, arg)` — add to queue
- `JSVM__DrainMicrotasks()` — execute all pending microtasks after each script turn
- Promise resolution enqueues handler callbacks as microtasks

### 2C. Async/Await Syntax (JSLexer + JSParser)
New tokens:
- `KW_ASYNC = 106` — contextual keyword
- `KW_AWAIT = 107` — keyword in async context

New AST types:
- `ASYNC_FUNC_DECL = 55`
- `ASYNC_FUNC_EXPR = 56`
- `ASYNC_ARROW_EXPR = 57`
- `AWAIT_EXPR = 58`
- `ASYNC_GEN_FUNC_DECL = 59`
- `ASYNC_GEN_FUNC_EXPR = 60`

Parser changes:
- `async function foo()` → ASYNC_FUNC_DECL
- `async () => expr` → ASYNC_ARROW_EXPR
- `await expr` → AWAIT_EXPR (only valid in async context)

### 2D. Async Compilation (JSCompiler)
**Reuse generator infrastructure.** An async function is compiled as:

1. Wrap body in implicit generator-like state machine
2. `await expr` compiles to: `compile(expr) → YIELD → resume with resolved value`
3. Function return wraps result in `Promise.resolve(result)`
4. Thrown errors wrap in `Promise.reject(error)`

New opcodes:
- `ASYNC_CLOSURE = 76` — like GEN_CLOSURE but creates async function
- `AWAIT = 77` — like YIELD but integrates with promise resolution

### 2E. Async VM Execution (JSVM)
- `ASYNC_CLOSURE`: Creates function that returns Promise when called
- On call: Create promise, create generator-like state, start execution
- `AWAIT`: Suspend execution, call `.then()` on awaited value, resume on resolution
- On return: Resolve the returned promise with the value
- On throw: Reject the returned promise with the error

---

## Phase 3: Class Advanced Features (Target: +3,000 passes → ~90%)

### 3A. Private Fields (#field)
**Impact: ~3,186 tests** | All layers affected

Lexer:
- Add `PRIVATE_IDENT = 108` token type
- When `#` (char 35) followed by ident start → scan as PRIVATE_IDENT
- Token text includes `#` prefix

Parser:
- Accept PRIVATE_IDENT in class body for field declarations and methods
- Accept PRIVATE_IDENT in member expressions (`this.#field`)

Compiler:
- Implement via **mangled property names**: `#field` → `__pvt_ClassName_field`
- Compile `this.#field` → GET_PROP with mangled name
- Compile `this.#field = val` → SET_PROP with mangled name
- Access check: Only allow in class body scope (compile error outside)

Runtime:
- No runtime changes needed — mangled names stored in regular XSHash
- True privacy enforcement happens at compile time (cannot reference mangled name from outside)
- `#field in obj` → check if mangled property exists

### 3B. Class Static Blocks (`static { ... }`)
**Impact: ~200 tests** | Parser + Compiler
- Parse `static {` as a static initializer block
- Compile as immediate-invoked code after class creation

### 3C. `extends` Expression Improvements
- Computed extends: `class C extends getBase() {}`
- Already partially supported — verify edge cases

---

## Phase 4: Progressive Fixed-Point Numbers (Target: +189 passes → ~91%)

See `floatingpointplan.md` for full architecture.

### Refinements to the Plan

**1. Test262 Compliance Concern:**
The fixed-point approach won't pass Test262 numeric tests that depend on IEEE 754 behavior:
- `0.1 + 0.2 === 0.30000000000000004` — test262 EXPECTS this
- `Number.EPSILON`, `Number.MAX_SAFE_INTEGER` — IEEE 754 constants
- `NaN`, `Infinity`, `-0` — don't exist in fixed-point
- `Math.fround`, `Math.cbrt`, trig functions — need IEEE 754 precision

**Recommendation:** Implement BOTH fixed-point AND IEEE 754.
- Fixed-point (Q8.8/Q16.16/Q32.32) for DOM/layout engine performance
- IEEE 754 double for Test262 compliance and full JS semantics
- Runtime auto-selects: parsed literals with `.` → IEEE 754 (for compliance), internal layout math → fixed-point
- This passes Test262 while keeping the performance advantage for actual browser use

**2. IEEE 754 Double Implementation (for compliance):**
- Reuse existing FPU module in `Librarys/Compiler/Compile/FPU/` (SSE2)
- JSType.FLOAT64 = 11 (new type alongside existing NUMBER=3)
- Parser: `JSParse__ParseFloat` → parse decimal literal to 64-bit double
- Compiler: Store in constant pool with type=11
- Runtime: `JSRT_CreateFloat64(raw_bits)` stores 64-bit IEEE 754 payload
- Arithmetic: SSE2 ADDSD/MULSD/DIVSD for float64 operations
- Mixed int+float: promote int to float64 (CVTSI2SD)

**3. Implementation Order:**
1. IEEE 754 double (passes Test262, ~189 numeric tests)
2. Fixed-point (performance optimization for DOM/layout — does NOT replace IEEE 754)
3. Heuristic: Layout engine paths use fixed-point, general JS uses IEEE 754

---

## Phase 5: Remaining Conformance (Target: 95%+ → 100%)

### 5A. let/const TDZ Enforcement (~200 tests)
- Temporal Dead Zone: reference before declaration = ReferenceError
- Requires: track "initialized" flag per block-scoped variable
- New opcode: `CHECK_TDZ local_idx` — throws if not initialized

### 5B. Iterator Protocol (~500 tests)
- `Symbol.iterator` — requires Symbol type
- `[Symbol.iterator]()` → returns `{next() → {value, done}}`
- Replace TO_ARRAY eager materialization with lazy iterator protocol
- for-of, spread, destructuring all use iterator protocol

### 5C. Proxy/Reflect (~1,000 tests)
- Advanced metaprogramming — significant effort
- Proxy traps, Reflect methods

### 5D. Module System (~365 tests)
- `import`/`export` syntax
- Dynamic `import()`
- Module namespace objects

### 5E. WeakRef/FinalizationRegistry (~100 tests)
- Requires GC (AILang uses arena allocation)
- May need to skip or implement simple refcount scheme

### 5F. RegExp Advanced (~200 tests)
- Named groups, lookbehind, unicode properties
- Library.JSRegex.ailang exists (Thompson NFA) — extend it

---

## Implementation Priority Order

| # | Feature | Est. Passes | Cumulative | % |
|---|---------|------------|------------|---|
| 1 | Object.defineProperty/keys/create | +1,200 | 13,767 | 57.6% |
| 2 | Computed props in classes | +500 | 14,267 | 59.7% |
| 3 | Class field declarations | +800 | 15,067 | 63.0% |
| 4 | Promise type + microtask queue | +500 | 15,567 | 65.1% |
| 5 | async/await syntax + compilation | +3,500 | 19,067 | 79.8% |
| 6 | Private fields (#field) | +2,000 | 21,067 | 88.2% |
| 7 | IEEE 754 doubles | +189 | 21,256 | 88.9% |
| 8 | Iterator protocol (Symbol.iterator) | +500 | 21,756 | 91.0% |
| 9 | let/const TDZ | +200 | 21,956 | 91.9% |
| 10 | Progressive fixed-point (perf) | +0 | 21,956 | 91.9% |
| 11 | Template literal improvements | +37 | 21,993 | 92.0% |
| 12 | Class static blocks | +200 | 22,193 | 92.9% |
| 13 | Proxy/Reflect | +1,000 | 23,193 | 97.0% |
| 14 | Module system | +365 | 23,558 | 98.6% |
| 15 | Remaining edge cases | +341 | 23,899 | 100% |

---

## Immediate Next Steps (Start Now)

### Step 1: Object.defineProperty
This is the #1 blocker across ALL test categories. Implementing it in JSRuntime/JSBridge unblocks ~1,200 tests immediately. The property descriptor model is:

```
descriptor = {
  value: any,           // data descriptor
  writable: boolean,
  get: function,        // accessor descriptor
  set: function,
  enumerable: boolean,
  configurable: boolean
}
```

Current XSHash stores values directly. Need to either:
- A) Add descriptor metadata alongside each property (8 extra bytes per prop)
- B) Store descriptors in a parallel hash (simpler, lower risk to existing code)

### Step 2: Computed Props in Classes
One-shot compiler fix. Parser already done.

### Step 3: Class Fields
Parser + compiler change. Moderate effort.

Then move to async/await (Phase 2) which is the big effort.

---

## HalCode9000 Worker Strategy

- **Worker 1**: Implement Object.defineProperty in JSRuntime (grunt work, well-defined API)
- **Worker 2**: Implement computed prop compilation in JSCompiler (single function edit)
- **Worker 3**: Run test262 subsets after each change to validate
- **Claude**: Architect async/await state machine, review all worker output
