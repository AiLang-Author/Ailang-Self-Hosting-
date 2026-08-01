# Ailang JavaScript Engine — Context Document

> Point Claude / agents at this file to resume JS engine work with full context.
> Last updated: 2026-08-01 (M128e7bh — template-literal 100%)

## Quick Reference

```
Mid-gate:       python3 tools/js_midgate.py [--rebuild|--quick]
Build harness:  ./ailang.x JS-tests/test262_harness.ailang -o test262_harness.x
                ./ailang.x JS-tests/test262_harness_batch.ailang -o test262_harness_batch.x
Category gate:  python3 tools/test262_runner.py --categories expressions/call --no-batch -j 1
Full suite:     python3 tools/test262_runner.py --full -j 8 --timeout 12 \
                  --output-json results/test262_full_m128e7.json
Baseline report: python3 tools/test262_baseline_report.py results/test262_full_NEW.json \
                  --prior results/test262_full_m128e7x.json --label M128e7xx
Status (G2):    results/TEST262_STATUS_M128e7bh.md
Progress log:   results/M128e7_PROGRESS.md
```

### Honest status (2026-08-01, tip e7bh)

| Gate | Result |
|------|--------|
| **G2** (language ≥95%) | **Not met** — gap **~847** (best full e7x) … **~1,775** (latest full e7bb, pre-e7bc) |
| **Built-ins** | **~32–34%** (~15.5k residual) — **blocked on G2**; not the current target |
| Last full suite | **e7bb** 58.65% overall · lang 87.49% · built-ins 32.38% |
| Best full suite | **e7x** 61.35% · lang **91.42%** · G2 gap **847** |
| Full suite since e7bc fix | **Not re-run** — use safety slices; re-full to prove recovery |
| Safety 100% chips | optional-chaining, new.target, array, template-literal, concat, instanceof, in, string |
| Next | Full rescore vs e7x; P0 call eval-spread / line-terminators; class bulk toward G2 |

**Rule:** no false greens; no full-suite burn every chip; full ~50k for milestones / G2 claims.

---

## 1. Architecture Overview

**Pipeline:** JS Source → Lex → Parse → Compile → Load → VM Execute

```
JSEngine.ailang (orchestrator)
    → JSLexer.ailang         — tokenize source into ~30 token types
    → JSParser.ailang        — recursive descent + Pratt precedence → AST
    → JSCompiler.ailang      — walk AST → flat bytecode + constant pool
    → JSVM.ailang            — stack-based interpreter, 90+ opcodes
    → JSRuntime.ailang       — value system, type coercion, allocators
    → JSBridge.ailang        — DOM bindings, native functions, timers
    → JSJIT.ailang           — method JIT (dual-buffer ping-pong GC)
```

### Load-bearing runtime notes (Moles 6–10)

- **Closures:** free vars via `__cenv` / `__parent` (GET_FREE=90, SET_FRAME_ENV=91, SET_FREE=92). Do not dual-write bare outer globals inside functions.
- **Call spread:** CALL_SPREAD (69) + ARR_EXTEND (68) + `JSVM_IterableToArray` (Symbol.iterator).
- **arguments:** snapshot on CALL; restore via GlobalHash_Insert + **fresh** undefined gval — never rebind to `undef_val` singleton (poisons `typeof undefined`).
- **SetGlobal:** refuses mutating immortal singletons.
- **Escaped values:** do not rewind `func_slab` for escaped functions; property values live in `gval_pool`.

---

## 2. Source Files

### Core Engine (Librarys/Browser/)

| File | Lines | Purpose |
|------|-------|---------|
| Library.JSEngine.ailang | 1,251 | Orchestrator — extracts `<script>` from DOM, drives pipeline |
| Library.JSLexer.ailang | 2,526 | Tokenizer — ~45 token types, handles strings/comments/regex |
| Library.JSParser.ailang | 859 | Parser entry — recursive descent + Pratt precedence |
| Library.JSCompiler.ailang | 931 | Compiler entry — AST→bytecode, scope/locals, jump patching |
| Library.JSVM.ailang | 866 | VM entry — init, load bytecode, run loop, call frames |
| Library.JSRuntime.ailang | 604 | Runtime — val_pool, str_slab, func_slab, slab allocators |
| Library.JSBridge.ailang | 5,222 | DOM bindings — document, window, console, Math, setTimeout |
| Library.JSJIT.ailang | 1,032 | Method JIT — dual 2MB RWX buffers, compile on first call |
| Library.JSValidate.ailang | 898 | Syntax validation — truth-table-driven, O(1) lookup |
| Library.JSRegex.ailang | 1,262 | RegExp — Thompson NFA with lazy DFA, namespaced JSRx* |
| Library.JSOop.ailang | 919 | OOP — prototype chains, constructors, instanceof |

### Split Files (subdirectories)

| File | Lines | Purpose |
|------|-------|---------|
| JSRuntime/Library.JSRTCoerce.ailang | 1,333 | Type coercion, JSRT_Add, JSRT__StrConcat, comparison |
| JSRuntime/Library.JSRTObject.ailang | 1,593 | Object/array ops, function descriptors, natives, timers |
| JSRuntime/Library.PropTable.ailang | 486 | Property tables — 264-byte linear-scan, 8KB global hash |
| JSParser/Library.JSParseExpr.ailang | 2,311 | Expression parsing (atoms through arrow functions) |
| JSParser/Library.JSParseStmt.ailang | 2,995 | Statement/declaration parsing |
| JSCompiler/Library.JSCompExpr.ailang | 1,105 | Expression compilation to bytecode |
| JSCompiler/Library.JSCompStmt.ailang | 2,948 | Statement compilation to bytecode |
| JSVM/Library.JSVMDispatch.ailang | 2,177 | Opcode dispatch loop — single Branch over 50+ cases |
| JSVM/Library.JSVMBuiltins.ailang | 676 | Install console, Math, Object, Array, Error, etc. |
| JSVM/Library.JSVMStringMethods.ailang | 1,066 | String methods — charAt, indexOf, slice, split, etc. |
| JSVM/Library.JSVMArrayMethods.ailang | ~1,200 | Array methods — forEach, map, filter, reduce, sort, flat, etc. |

**Total: ~28,000 lines across 22 files**

---

## 3. Memory Architecture

### Value Pool
- 16-byte JSValue objects: `[type:8][payload:8]`
- Max 4M values (`JSRTConst.MAX_VALUES`)
- Types: UNDEFINED(0), NULL(1), BOOLEAN(2), NUMBER(3), STRING(4), OBJECT(5), FUNCTION(6), ARRAY(7), GENERATOR(8)

### String Slab (str_slab)
- 64KB bump allocator for string data
- Used for: property keys, function names, getter/setter keys, ToString cache
- Scope rollback: `str_slab_pos` snaps back to watermark on function return
- **Note:** `JSRT__StrConcat` now uses native `StringConcat` (Arena-backed), NOT the str_slab

### Function Slab (func_slab)
- 64KB bump allocator for 72-byte function descriptors
- Same watermark rollback as str_slab

### Call Frame (72 bytes)
```
+0:  return_pc       +8:  return_sp       +16: locals_base
+24: param_count     +32: local_count     +40: (reserved)
+48: val_watermark   +56: str_watermark   +64: func_watermark
```

### Scope Cleanup
On function return, `JSVM__ReclaimScope` rolls back:
- `val_count` → val_watermark
- `str_slab_pos` → str_watermark
- `func_slab_pos` → func_watermark

Return values in the callee's region are promoted to the parent's slot first. Arena-allocated strings (from `StringConcat`) are outside the str_slab range and survive rollback automatically.

---

## 4. Bytecode Reference

50+ opcodes, format: `[opcode:1][operand:0-3 bytes]`

**Stack:** PUSH_CONST(1), PUSH_UNDEF(2), PUSH_NULL(3), PUSH_TRUE(4), PUSH_FALSE(5), POP(6), DUP(7), SWAP(8)
**Vars:** GET_LOCAL(10), SET_LOCAL(11), GET_GLOBAL(12), SET_GLOBAL(13)
**Props:** GET_PROP(16), SET_PROP(17), GET_ELEM(18), SET_ELEM(19)
**Arith:** ADD(20), SUB(21), MUL(22), DIV(23), MOD(24), NEG(25), EXP(26)
**Compare:** EQ(30), NEQ(31), LT(32), GT(33), LTE(34), GTE(35), STRICT_EQ(36), STRICT_NEQ(37)
**Bitwise:** NOT(40), BIT_AND(41), BIT_OR(42), BIT_XOR(43), BIT_NOT(44), SHL(45), SHR(46), TYPEOF(47), USHR(48), INSTANCEOF(49)
**Control:** JMP(50), JMP_FALSE(51), JMP_TRUE(52), JMP_NULLISH(53)
**Functions:** CALL(55), RETURN(56), CLOSURE(57), CONSTRUCT(81), CALL_METHOD(83)
**Objects:** NEW_OBJECT(60), NEW_ARRAY(61), CONCAT(62), OBJ_KEYS(66), ARR_APPEND(67)
**Exceptions:** TRY_PUSH(70), TRY_POP(71), THROW(72)
**Generators:** YIELD(73), GEN_CLOSURE(74), TO_ARRAY(75)
**Async:** ASYNC_CLOSURE(79), AWAIT(80)

---

## 5. Built-in Functions

### Global
`isNaN`, `isFinite`, `parseInt`, `parseFloat`, `Number()`, `String()`, `Boolean()`

### Error constructors
`Error`, `TypeError`, `RangeError`, `ReferenceError`, `SyntaxError`, `URIError`, `EvalError`

### Object
`Object.keys`, `Object.create`, `Object.defineProperty`, `Object.assign`, `Object.freeze`, `Object.is`, `Object.getPrototypeOf`, `Object.getOwnPropertyDescriptor`

### Array
`Array()`, `Array.isArray`, `Array.from`, plus 22 instance methods via dispatch:
`push`, `pop`, `forEach`, `map`, `filter`, `reduce`, `find`, `findIndex`, `some`, `every`, `indexOf`, `lastIndexOf`, `includes`, `join`, `reverse`, `slice`, `concat`, `shift`, `unshift`, `splice`, `fill`, `sort`, `flat`, `flatMap`
- Native IDs: push=98, pop=99, forEach=150, map=151, ... flat=170, flatMap=171
- Implementation: `JSVM/Library.JSVMArrayMethods.ailang`

### String
`String.fromCharCode`, plus instance methods: `charAt`, `charCodeAt`, `indexOf`, `substring`, `slice`, `split`, `toLowerCase`, `toUpperCase`, `trim`, `replace`, `match`, `repeat`, `padStart`, `padEnd`

### Math
Full set: `abs`, `acos`, `asin`, `atan`, `atan2`, `ceil`, `cos`, `exp`, `floor`, `log`, `log10`, `log2`, `max`, `min`, `pow`, `random`, `round`, `sign`, `sin`, `sqrt`, `tan`, `trunc` + constants (PI, E, LN2, etc.)

### RegExp
`RegExp()` constructor, `.test()`, `.exec()`, `.toString()` — Thompson NFA with lazy DFA

### console
`console.log`

### Timers
`setTimeout`, `setInterval` (via JSBridge timer queue, 32 max)

---

## 6. JIT Status

- **Architecture:** Dual 2MB RWX buffers (A/B), ping-pong GC
- **Trigger:** Method JIT — compile on first call
- **Backend:** Platform-agnostic via CEmitCoreArch (x86-64)
- **State:** Functional but underutilized. No tiering, no optimization passes.
- **Register convention:** RAX=scratch/return, RBP=locals, R12=VM stack base, R13=sp, R14=const pool

---

## 7. Tests & Benchmarks (JS-tests/)

All JS test sources and benchmark scripts live in `JS-tests/`:

| File | Purpose | Validates |
|------|---------|-----------|
| bench_js.ailang | Micro-benchmarks with CLOCK_MONOTONIC timing | Actual JS execution: loops, fib, arith, string concat, nested calls, arrays |
| test_js_e2e.ailang | End-to-end integration (HTML + `<script>` + DOM) | Full pipeline: lex→parse→compile→run→DOM mutation |
| test262_harness.ailang | Single-file tc39/test262 conformance harness | ECMAScript spec compliance |
| test262_harness_batch.ailang | Batch mode harness (stdin/stdout protocol) | Bulk test262 runs |
| html5lib_harness.ailang | HTML5 tokenizer conformance | HTML parsing compliance |
| wpt_batch.ailang | W3C Web Platform Tests batch harness | DOM API compliance |
| bench_vs_v8.sh | Ailang JS vs Node/V8 on SunSpider + Octane | Wall-clock performance comparison |
| bench_looped.sh | Steady-state benchmarks (inner loop, no startup) | Pure compute performance |

### External Benchmark Suites (in /home/bob/quickjs-benchmarks/)

| Suite | Location | Tests |
|-------|----------|-------|
| SunSpider 1.0 | sunspider-1.0/ | 26 tests: 3d, access, bitops, controlflow, crypto, date, math, regexp, string |
| Octane | octane/ | 15 tests: richards, deltablue, crypto, raytrace, earley-boyer, navier-stokes, splay, code-load, regexp, box2d, gbemu, zlib, pdfjs, mandreel, typescript |
| Kraken 1.0 | kraken-1.0/ | 30 tests: ai, audio, imaging, json, crypto |
| Kraken 1.1 | kraken-1.1/ | 30 tests (minor version updates) |

### Compiled Test Binaries (project root)
- `bench_js.x` — JS micro-benchmarks (actual execution)
- `test_js_e2e.x` — E2E integration tests
- `test262_harness.x` — tc39 harness (lightweight, 54KB)
- `test262_harness_batch.x` — batch harness
- `html5lib_harness.x` — HTML5 tokenizer
- `wpt_batch.x` — WPT DOM tests
- `browser.x` — full browser with JS engine

---

## 8. Resource Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Bytecode buffer | 512KB | Compiler stops if exceeded |
| Constants | 65,536 | Per program unit |
| Value pool | 4M objects | OOM halt if exceeded |
| Locals per scope | 1,024 | Overflow rejects variable |
| Scope nesting | 256 | Parser error if exceeded |
| Call frames | 1,024 | Stack overflow detected |
| Value stack | 16,384 | Underflow/overflow detected |
| str_slab | 64KB | Shared with func_slab |
| func_slab | 64KB | Shared with str_slab |
| Native functions | 64 | Table size |
| Timers | 32 | setTimeout/setInterval queue |
| JIT buffer | 2MB x 2 | Ping-pong A/B |
| Step limit | 1M default | Configurable via JSVM_SetMaxSteps |

---

## 9. Conformance Master Plan

> **Full plan:** [`JS-MasterPlan.md`](JS-MasterPlan.md)

### Baseline (2026-06-15): 3,121 / 7,689 = 41.7%

| Phase | Target | Key Work |
|-------|--------|----------|
| **Phase 1** | 41.7% → 58% | Fix polyfill (assert.throws type checking), destructuring timeouts, labeled break/continue, try/catch semantics, delete semantics, ASI/let edge cases |
| **Phase 2** | 58% → 75% | Wrapper objects (new Boolean/Number/String), spread/rest runtime fixes, arguments object, property descriptors, ToPrimitive coercion |
| **Phase 3** | 75% → 90% | Error constructors, class completion, Symbol type, iterator protocol, generator runtime, eval(), strict mode, with statement |
| **Phase 4** | 90% → 100% | Default param scoping, getter/setter edge cases, for-in semantics, remaining ASI, unicode identifiers, coercion edge cases |

### Top Failure Buckets

| Root Cause | Failing Tests | Fix Complexity |
|------------|---------------|----------------|
| Spread/rest runtime bugs | 873 (19.5%) | MEDIUM |
| Polyfill assert.throws ignores error type | 552 (12.3%) | EASY |
| Error/throw semantics | 364 (8.1%) | MEDIUM |
| new Boolean/Number/String wrappers | 325 (7.3%) | MEDIUM |
| class keyword gaps | 326 (7.3%) | HARD |
| Symbol type missing | 282 (6.3%) | HARD |
| Property descriptors incomplete | 218 (4.9%) | MEDIUM |
| eval() not implemented | 213 (4.8%) | HARD |
| try/catch semantics | 213 (4.8%) | MEDIUM |
| Generator runtime | 215 (4.8%) | HARD |
| Strict mode enforcement | 131 (2.9%) | MEDIUM |
| Destructuring timeouts | 116 (2.6%) | BUG |

---

## 10. Current Work State

### Session 4 Completed (2026-06-15, evening)
- **Loop-created objects bug fixed:** `JSRT_ObjSet` was storing JSValue *pointers* from mutable stack slots into PropTable. When loop variable mutated, all objects sharing that pointer saw the updated value. Fix: added value copy at top of `JSRT_ObjSet` — allocates fresh val_pool slot and copies 16-byte JSValue before storing.
  - File: `JSRuntime/Library.JSRTObject.ailang`
- **22 Array methods implemented:** forEach, map, filter, reduce, find, findIndex, some, every, indexOf, lastIndexOf, includes, join, reverse, slice, concat, shift, unshift, splice, fill, sort, flat, flatMap
  - New file: `JSVM/Library.JSVMArrayMethods.ailang` (~1200 lines) — `JSVM__MatchArrayMethod` (byte-by-byte name matching) + all method implementations
  - New native IDs 150-171 in `Library.JSBridge.ailang` (JSNativeID FixedPool)
  - Dispatch routing in `JSVM/Library.JSVMDispatch.ailang` (both CALL sites) and `JSVM/Library.JSVMStringMethods.ailang`
  - Import + buffer allocation in `Library.JSVM.ailang` (JSArrMethodBuf.arg0 = 32-byte pre-allocated callback arg buffer)
  - Callback methods (forEach, map, filter, reduce, find, findIndex, some, every, sort) use `JSVM__CallFunc` for re-entrant JS calls
  - Sort uses insertion sort (stable, O(n²)) with optional comparator callback
  - Flat uses recursive helper with depth parameter
- **JSRT_ToString for ARRAY type fixed:** Was returning empty string `""`. Now iterates array elements, recursively calls JSRT_ToString on each, joins with "," per JS spec. Uses JSRT__StrConcat (Arena-backed) for recursion safety.
  - File: `JSRuntime/Library.JSRTCoerce.ailang` (lines 332-380)
- **All array methods verified:** 24/24 test cases pass (forEach, map, filter, reduce, find, findIndex, some, every, indexOf, lastIndexOf, includes, join, reverse, slice, concat, shift, unshift, splice, fill, sort, sort-desc, flat, toString)
- **Regression clean:** bench_js.x 8/8 pass (485ms), e2e 29/32 pass (same 3 DOM innerHTML readback failures as before)
- **Correctness:** 88/88 tests now pass (loop-created objects bug was the last one)

### Session 3 Completed (2026-06-15, afternoon)
- **Global variable corruption fix (gval_pool):** `JSVM__SetGlobal` now copies values into a persistent `gval_pool` (16K slots, 256KB) that is NOT subject to scope reclamation watermark rollback. Previously, values written to globals inside functions pointed to val_pool slots that got reclaimed by `JSVM__ReclaimScope` on return, causing use-after-free corruption when subsequent allocations overwrote the stale memory.
  - Files: `Library.JSRuntime.ailang` (added gval_pool/gval_count state, MAX_GVALS=16384, JSRT__AllocGlobalValue), `Library.JSVM.ailang` (rewrote JSVM__SetGlobal with fast-path update-in-place and slow-path new-slot allocation)
  - Fast path: existing global → update type+payload in-place (zero allocation)
  - Slow path: new global → allocate persistent gval slot + str_slab key copy
- **toUpperCase/toLowerCase swapped IDs:** STR_TO_LOWER=70, STR_TO_UPPER=71 (were reversed)
  - File: `Library.JSBridge.ailang`
- **string.repeat() method:** Added STR_REPEAT=97, matcher, dispatch using native StringRepeat
  - Files: `Library.JSBridge.ailang`, `Library.JSVMStringMethods.ailang`, `Library.JSVMDispatch.ailang`
- **arr.push()/pop() methods:** Added ARR_PUSH=98, ARR_POP=99, array method matching in GET_PROP
  - Files: `Library.JSBridge.ailang`, `Library.JSVMStringMethods.ailang`, `Library.JSVMDispatch.ailang`
- **Math.min/max with 3+ args:** Rewrote handlers to iterate all arguments via WhileLoop
  - File: `Library.JSRTObject.ailang`
- **Float_ToInt fixes for 5 string methods:** charAt, charCodeAt, substring, slice, substr now properly convert IEEE-754 doubles to integer indices
- **Correctness test suite:** 87/88 pass (1 known: loop-created objects share values)
- **bench_js.x:** All 8 benchmarks pass, total 536ms
- **SunSpider adapted:** controlflow-recursive, bitops-bitwise-and, math-partial-sums, fib(30), tak(18,12,6) all produce correct results

### Session 2 Completed (2026-06-15, morning)
- **StringConcat swap:** `JSRT__StrConcat` now uses native `StringConcat` (Arena-backed, SSE2 copy) instead of str_slab bump alloc + byte-at-a-time MemoryCopy
- **is_last_stmt POP leak fix:** CompileBlock no longer leaks POP for non-last statements
- **GET_GLOBAL fix for top-level:** Top-level reads of function-mutated variables now use GET_GLOBAL

### Known Issues
- **DOM innerHTML readback:** 3 e2e tests fail — innerHTML mutations execute but DOM text readback doesn't return the new value. This is a DOM/Bridge issue, not JS engine.

### Build Commands
```
./ailang.x JS-tests/test262_harness.ailang test262_harness.x
./ailang.x JS-tests/test_js_e2e.ailang test_js_e2e.x
./ailang.x JS-tests/bench_js.ailang bench_js.x
```

---

## 11. Compiler Backend (Native Intrinsics Used by JS Engine)

The JS runtime calls these native intrinsics that the AILang compiler implements as optimized x86-64:

| Intrinsic | Compiler File | Implementation |
|-----------|--------------|----------------|
| StringLength(ptr) | FPU/X86/Library.FPUCompileX86String.ailang | SSE2 PCMPEQB + PMOVMSKB + BSF (16 bytes/cycle) |
| StringCompare(a, b) | FPU/X86/Library.FPUCompileX86String.ailang | SSE2 16-byte parallel compare |
| StringCopy(dst, src) | FPU/X86/Library.FPUCompileX86String.ailang | SSE2 16-byte bulk copy |
| StringIndexOf(str, ch) | FPU/X86/Library.FPUCompileX86String.ailang | SSE2 broadcast + parallel scan |
| StringConcat(a, b) | Compile/Modules/Library.CCompileStringCore.ailang | Arena_Alloc + byte copy (not yet SSE2) |
| MemoryCopy(dst, src, n) | (core builtin) | Used by str_slab code, JSBridge |
| Arena_Alloc(size) | (core builtin) | Free-list arena allocator |

**Note:** `StringConcat` in the compiler backend still uses byte-at-a-time copy loops (lines 258-282 of CCompileStringCore.ailang). Upgrading these to SSE2 bulk copy would further improve concat performance.

---

## 12. Test262 Conformance Results (2026-06-15)

Full tc39/test262 run via `python3 tools/test262_runner.py --verbose --output-json /tmp/test262_results.json`

- **Mode:** batch (8 workers), 5s per-test timeout
- **Wall time:** 223.7s
- **Overall:** 3,121 / 7,481 passing (41.7%), 116 timeouts

### Per-Category Breakdown

```
Category                                       Total   Pass   Fail   T/O   Pass%
=============================================================================
statements/for                                   385    296     25    39   92.2%
statements/break                                  20     19      1     0   95.0%
statements/continue                               24     21      3     0   87.5%
statements/return                                 16     14      2     0   87.5%
statements/variable                              178    152     26     0   85.4%
statements/if                                     69     59     10     0   85.5%
punctuators                                       11     10      1     0   90.9%
expressions/void                                   9      8      1     0   88.9%
keywords                                          25     25      0     0  100.0%
expressions/coalesce                              24     20      4     0   83.3%
expressions/exponentiation                        44     33      9     0   78.6%
statements/block                                  21     15      5     1   75.0%
block-scope                                      145    103     42     0   71.0%
statements/switch                                111     79     32     0   71.2%
statements/while                                  38     27     11     0   71.1%
statements/do-while                               36     25     11     0   69.4%
expressions/logical-not                           19     13      6     0   68.4%
literals                                         534    354    179     0   66.4%
expressions/logical-or                            18     11      7     0   61.1%
identifiers                                      268    161    107     0   60.1%
statements/labeled                                24     14      9     1   60.9%
expressions/conditional                           22     13      9     0   59.1%
line-terminators                                  41     24     17     0   58.5%
expressions/logical-and                           18     10      8     0   55.6%
expressions/grouping                               9      5      4     0   55.6%
future-reserved-words                             54     29     25     0   53.7%
reserved-words                                    27     13     14     0   48.1%
comments                                          52     25     27     0   48.1%
expressions/postfix-increment                     38     18     20     0   47.4%
expressions/less-than                             45     21     24     0   46.7%
expressions/strict-equals                         30     14     16     0   46.7%
expressions/template-literal                      57     26     31     0   45.6%
expressions/postfix-decrement                     37     17     20     0   45.9%
expressions/prefix-decrement                      34     15     19     0   44.1%
expressions/bitwise-not                           16      7      9     0   43.8%
expressions/object                              1161    471    603    42   43.9%
asi                                              102     44     58     0   43.1%
expressions/greater-than                          49     21     28     0   42.9%
expressions/prefix-increment                      33     14     19     0   42.4%
statements/async-function                         74     30     44     0   40.5%
expressions/assignment                           485    178    274    31   39.4%
expressions/async-function                        93     36     57     0   38.7%
expressions/typeof                                16      6     10     0   37.5%
expressions/in                                    36     13     23     0   36.1%
expressions/arrow-function                       343    123    219     0   36.0%
global-code                                       42     15     27     0   35.7%
expressions/unary-minus                           14      5      9     0   35.7%
expressions/greater-than-or-equal                 43     15     28     0   34.9%
expressions/division                              45     15     30     0   33.3%
expressions/left-shift                            45     15     30     0   33.3%
expressions/comma                                  6      2      4     0   33.3%
expressions/bitwise-and                           30     10     20     0   33.3%
statements/expression                              3      1      2     0   33.3%
expressions/less-than-or-equal                    47     15     32     0   31.9%
destructuring                                     19      6     13     0   31.6%
expressions/unsigned-right-shift                  45     14     31     0   31.1%
expressions/multiplication                        40     12     28     0   30.0%
expressions/right-shift                           37     11     26     0   29.7%
expressions/instanceof                            43     12     31     0   27.9%
expressions/modulus                               40     11     29     0   27.5%
expressions/subtraction                           38     10     28     0   26.3%
function-code                                    217     56    161     0   25.8%
types/string                                      24      6     18     0   25.0%
expressions/compound-assignment                  454    108    346     0   23.8%
expressions/does-not-equals                       38      9     29     0   23.7%
expressions/equals                                47     11     36     0   23.4%
expressions/unary-plus                            17      4     13     0   23.5%
expressions/logical-assignment                    78     16     62     0   20.5%
directive-prologue                                62     12     50     0   19.4%
expressions/addition                              48      8     40     0   16.7%
identifier-resolution                             14      2     12     0   14.3%
white-space                                       67      9     58     0   13.4%
expressions/bitwise-or                            30      4     26     0   13.3%
expressions/bitwise-xor                           30      4     26     0   13.3%
types/undefined                                    8      1      7     0   12.5%
types                                            113     14     99     0   12.4%
computed-property-names                           48      5     43     0   10.4%
rest-parameters                                   11      1     10     0    9.1%
statementList                                     80      7     73     0    8.8%
expressions/call                                  92      7     79     2    8.1%
expressions/array                                 52      3     49     0    5.8%
arguments-object                                 263     14    237     0    5.6%
types/object                                      19      1     18     0    5.3%
eval-code                                        347     14    333     0    4.0%
expressions/new                                   59      1     58     0    1.7%
source-text                                        1      0      1     0    0.0%
=============================================================================
TOTAL                                           7689   3121   4360   116   41.7%
```

### Strengths (>70% pass rate)
- **Control flow:** for (92%), break (95%), continue (88%), return (88%), if (86%), while/do-while (69-71%), switch (71%)
- **Variable declarations:** 85.4%
- **Block scope (let/const):** 71.0%
- **Keywords:** 100%
- **Punctuators:** 90.9%
- **Nullish coalescing:** 83.3%
- **Exponentiation:** 78.6%

### Weaknesses (<20% pass rate)
- **eval-code:** 4.0% — no eval() implementation
- **arguments-object:** 5.6% — arguments not fully spec-compliant
- **expressions/new:** 1.7% — constructor dispatch gaps
- **expressions/array:** 5.8% — array literal edge cases
- **statementList:** 8.8%
- **rest-parameters:** 9.1%
- **computed-property-names:** 10.4%

### E2E Integration (test_js_e2e.x)
- **29/32 pass** — same 3 DOM innerHTML readback failures (DOM/Bridge issue, not JS engine)
