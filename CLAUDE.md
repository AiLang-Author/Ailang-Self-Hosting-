# Project Memory

## Hard Rules

- **ALWAYS use `master` branch** — never `main`. The `main` branch is a dead orphan with no common ancestor; delete it if it appears.
- **NEVER read image files** (PNG, JPG, JPEG, BMP, GIF, ICO, SVG, WebP, TIFF, TGA, TVG, etc.) with the Read tool. This causes crashes. No exceptions.

## Architecture Notes

- **AKContext system:** Explicit `LinkagePool.AKContext` handles. Each context (main window, toolbar, deskbar, menu, dialog) owns its own node buffer, extra table, and event state. `AK_CreateContext()` allocates, all AK_* functions take `ctx` as first param.
- Toolbar actions fire on UP (not DOWN). Action string -> EventRouter queue -> `EventRouter_Drain` in main loop dispatches.
- `Menu_Show` creates its own AKContext, builds tree, renders to surface, destroys context. Surface stored in MenuState. `Menu_Blit` called from `Win_BlitAll`.
- Main loop: Evdev_Poll -> DrainInput -> Win_RenderDirty -> EventRouter_Drain -> IPCBroker_Poll -> Deskbar_Refresh -> DebugLog_Render -> Win_BlitAll -> sleep(16ms).
- Deskbar has its own AKContext stored in `DeskbarState.ak_ctx`. No global swap needed.
- Each window toolbar has its own AKContext stored via `WinMgr_SetToolbarCtx(idx, ctx)`.
- **IPC Broker** (`Display/IPC/Library.IPCBroker.ailang`): Embedded in display server. Unix socket at `/tmp/ailang_display.sock`. Non-blocking `poll(0)` once per frame. 8-client max. Protocol: 4-byte BE length prefix + JSON. Methods: `register`, `window.create`, `window.update` (app->server); `window.created`, `window.closed`, `input.action`, `input.key`, `input.mouse` (server->app).
- **Start Menu** (`Display/Menu/Library.StartMenu.ailang`): Windows XP/7-style popup panel above deskbar. Own AKContext, own surface, positioned overlay. Lists services from PostgreSQL cache + system items.
- **EventRouter action routing**: System actions (`win.`, `app.`, `menu:`, `sys.`, `fd.` prefixes) always handled locally. Non-system actions from IPC-owned windows forwarded to app via `IPCBroker_RouteAction`.
- **Init sequence**: `SysDisplay_Init -> EventRouter_Init -> Dialog_Init -> Menu_Init -> Deskbar_Init -> IPCBroker_Init -> StartMenu_Init -> HTML_Init -> PageSurface_Init -> Doc_Init`

### Compiler Constraints

- **6-arg limit**: SysV AMD64's 6 register args (RDI, RSI, RDX, RCX, R8, R9) with no spill. `analyzer.x` arity checker enforces this.
- **StoreValue**: Defaults to 8-byte (qword) writes. Use `StoreValue(addr, val, "dword")` for 4-byte writes.
- **MemoryCopy/MemorySet**: Emit `CLD` + `REP MOVSB/STOSB` with register save/restore.

### Headless Testing

`FB_InitHeadless(w, h)` allocates anonymous mmap buffer instead of `/dev/fb0`. Test binaries override `RenderFB_InitDouble` to call `FB_InitHeadless(1920, 1080)`.

### HTML Toolbar System

`toolbar=` attribute on `<window>` tag: `"none"` (0), `"about"` (1, default), `"file"` (2), `"full"` (3). `Win_BuildAppToolbar(ctx, mode, app_title)` builds the tree.

## Key Subsystems (Condensed)

### Shared Memory Canvas

Zero-copy pixel streaming via `/dev/shm/ailang_canvas_<win_id>` (`MAP_SHARED`, BGRA). IPC messages: `canvas.attach`, `canvas.present`, `canvas.detach`. Per-window `CanvasState` (48-byte entries): ACTIVE, SHM_PTR, SHM_SIZE, SURF, MOUSE_CAPTURE, DIRTY fields.

### Xvfb Sandboxed Apps (Chrome, VS Code, Ladybird)

3-process stack: Xvfb (virtual X, `-fbdir` for mmap framebuffer) -> app (`--display=:N`) -> xdotool (persistent stdin pipe for input). Direct mmap of Xvfb framebuffer file (xwd format, 3232-byte header offset). Row-by-row viewport copy to ShmCanvas each tick.

- Chrome: Xvfb :99, fbdir `/tmp/chrome_fb/`, profile `/tmp/chrome_ailang_profile`, `--start-maximized`. Do NOT use `--disable-software-rasterizer`.
- VS Code: Xvfb :98, fbdir `/tmp/vscode_fb/`, profile `/tmp/vscode_ailang_profile`, `--maximize`, `--new-window`.
- Ladybird: Native IPC client (no Xvfb needed) — uses Ailang's ShmCanvas directly via C++ integration in `~/ladybird/UI/Ailang/`.
- PID file system for cleanup (`/tmp/*_ailang_{xvfb,browser,xdotool}.pid`). `DropPriv()` before execve (stat `/home/bob` for uid/gid).
- MOUSE_CAPTURE flag for VM-style mouse forwarding. Mouse move coalescing (one xdotool per tick).
- Persistent Xvfb on resize — no process restart, just ShmCanvas recreate + `xdotool windowsize`.

### Audio Engine

Direct ALSA (`/dev/snd/pcmC0D0p`), S16LE 48kHz stereo. 3-bus mixer (app/system/master). Audio-driven frame sync for video. Volume 0-1024 (256=unity). Replay: must call `Audio_Prepare()` after `Audio_Drop()`.

### Terminal Emulator

PTY + VT100 state machine (NORMAL/ESC/CSI/OSC). 8x16 bitmap font (`Library.TermFont.ailang`). Grid: 4-byte codepoints + BGRA fg/bg per cell. Truecolor (256-color + 24-bit RGB). DEC private modes (?1049/?25/?7/?1). Scrollback ring buffer (1000 lines). UTF-8 multi-byte decoder. Dynamic resize via `TIOCSWINSZ`.

## Library Directory Structure

Import paths use dots: `LibraryImport.Display.Window.WinManager` -> `Librarys/Display/Window/Library.WinManager.ailang`.

```
Librarys/
├── Library.{Arena,XArrays,StringUtils,JSON,HashMap,Socket,ShmCanvas,KeyMap,TextBuffer,TermFont,TUI,Math}.ailang
├── Compiler/                       # Compiler subsystem
├── AIMacro/                        # Macro subsystem
├── Display/                        # Display server
│   ├── System/    # SysDisplay, EventRouter, Screenshot
│   ├── Window/    # WinManager, WinToolbar, WinInput, WinStack, WinRender
│   ├── Input/     # DInputTypes, DInputEvdev, DInputDiscover, Cursor, CursorBitmap
│   ├── UI/        # Auckland, AucklandEvent, AucklandBind, TextRegion, PaneDecorator, Dialog, AboutDialog, FileDialog, NotepadApp
│   ├── Menu/      # Menu, StartMenu, CascadeMenu, Deskbar
│   ├── Render/    # Framebuffer, DRenderFB, DSurface*, DCompose*, DRing*, DZone*, Fonts, VIF, VIcon, AudioEngine
│   ├── Content/   # Document, PageSurface, HTMLParse, Editor
│   ├── Theme/     # UIConfig, UIScale, UITheme
│   └── IPC/       # IPCBroker, InputRouter
├── Browser/                        # JS engine + HTML browser
│   # JSLexer, JSParser, JSCompiler, JSRuntime, JSVM, JSBridge, JSEngine
│   # HTMLTokenizer, HTMLDom, CSSParse, HTMLLayout, HTMLRender
└── DnD/                            # D&D RPG game
    ├── Engine/    # DND, GameConfig, World, Portal, Encounter, DICE
    ├── Character/ # Character, Item, EquipScreen
    ├── Battle/    # BattleScreen
    ├── Commerce/  # Shop, Inn
    ├── Save/      # Save, SaveScreen
    └── Web/       # HTMLBroadcast, DND_HTML_Output_engine
```

IPC apps only import generic root libs — no Display/ imports.

## PostgreSQL Services

```sql
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE,
    binary_path TEXT, args TEXT, autostart BOOLEAN DEFAULT false,
    restart_policy TEXT DEFAULT 'never', depends_on TEXT,
    run_as TEXT DEFAULT 'nobody', priority INTEGER DEFAULT 50,
    enabled BOOLEAN DEFAULT true, encryption_key_id INTEGER,
    display_name TEXT
)
```

Seeded: notepad, files, calculator, grep, canvas_demo, videoplayer, terminal, claude, chrome, ladybird.

## Build & Run

```
./ailang.x Main.ailang SysDisplay.x                        # display server
./ailang.x Applications/calc_ipc.ailang calc_ipc.x         # calculator
./ailang.x Applications/grep_ipc.ailang grep_ipc.x         # grep
./ailang.x Testcode/canvas_demo.ailang canvas_demo.x       # canvas demo
./ailang.x Applications/videoplayer.ailang videoplayer.x   # video player
./ailang.x Applications/terminal_ipc.ailang terminal_ipc.x # terminal
./ailang.x Applications/claude_ipc.ailang claude_ipc.x     # claude code
./ailang.x Applications/chrome_ipc.ailang chrome_ipc.x     # chrome browser
./ailang.x Applications/vscode_ipc.ailang vscode_ipc.x    # VS Code
./ailang.x Applications/ladybird_ipc.ailang ladybird_ipc.x # Ladybird browser (native IPC)
./ailang.x dnd_game.ailang dnd.x                           # DnD game
./ailang.x Calc.ailang Calc.x                              # calc unit tests
./ailang.x TestCode/test_main.ailang test_main.x           # headless tests (125 steps)
./ailang.x TestCode/test_js_e2e.ailang test_js_e2e.x       # JS engine E2E tests
./ailang.x TestCode/bench_js.ailang bench_js.x             # JS benchmark (fib)
./ailang.x Applications/browser_ipc.ailang browser_ipc.x   # Ailang native browser
./SysDisplay.x                                              # run on TTY (Ctrl+Alt+F2)
```

### Kernel Module Path (`-kmod`)

`./ailang.x -kmod source.ailang ail_payload.o` produces ET_REL. Drop into `kernel_module/shim/`, `make`, `sudo insmod ail_combined.ko`. Steps 1-5 done, step 6 (insmod test) pending dedicated Linux box.

## Ladybird Browser Integration

Native IPC client (no Xvfb sandboxing needed). C++ integration in `~/ladybird/UI/Ailang/` (10 files, ~1100 lines):
- `AilangIPC.h/cpp` — socket client, JSON protocol, ShmCanvas management
- `Application.h/cpp` — extends `WebView::Application`, IPC message dispatch, toolbar actions (`lb.back`/`lb.fwd`/`lb.reload`)
- `WebContentView.h/cpp` — `ViewImplementation` for Ailang backend, BGRx8888->BGRA paint, keyboard/mouse mapping
- `Events.cpp` — evdev scancode -> `Web::UIEvents::KeyCode` (95 mappings)
- `main.cpp` + `CMakeLists.txt`

Window config: `config/ladybird.html` (1024x700, `toolbar="about"`).
Build: `~/ladybird/Build/release/bin/Ladybird` (compiled, 2.4MB).

## JavaScript Engine (Phase 6)

Bytecode VM architecture: `<script>` source -> JSLexer (tokenize) -> JSParser (recursive descent AST) -> JSCompiler (AST -> bytecode + constant pool) -> JSVM (fetch-decode-execute) -> JSRuntime (values, coercion, built-ins) -> JSBridge (DOM bindings) -> JSEngine (orchestrator).

7 libraries in `Librarys/Browser/`:

| Library | LOC | Role |
|---------|-----|------|
| JSLexer | ~900 | Tokenizer, ~49 token types (KW_VAR=70 through KW_STATIC=105) |
| JSParser | ~1100 | Recursive descent, Pratt precedence, ~40 AST node types |
| JSCompiler | ~1100 | AST -> bytecode (~50 opcodes), constant pool, local resolution |
| JSRuntime | ~1000 | JSValue (16-byte tagged: type+payload), coercion, object/array ops |
| JSVM | ~1100 | Branch-dispatch loop (O(1) opcode dispatch), 4096-deep value stack |
| JSBridge | ~900 | DOM bindings: getElementById, innerHTML/textContent, addEventListener, console.log, setTimeout |
| JSEngine | ~700 | Orchestrator: extract `<script>` tags, lex->parse->compile->run pipeline |

**Value types**: UNDEFINED(0), NULL(1), BOOLEAN(2), NUMBER(3, 64-bit signed int), STRING(4), OBJECT(5, XSHash), FUNCTION(6), ARRAY(7, XArray), GENERATOR(8). Integer-only for v1 (no floats). No GC — arena per-page lifetime.

**Key patterns**:
- `JSCompDot` FixedPool for MEMBER_DOT assignment compilation (survives recursive JSComp__CompileExpr calls)
- `JSBridgeTmp` / `JSVMTmp` FixedPools for clobber-safe temporaries across function calls
- `JSRT_ToString` returns JSValue pointer; use `JSRT_GetPayload()` to extract raw C string
- `JSBridge__GetDomIdx` checks `__dom_idx` property on JS wrapper objects to map back to DOM nodes

**Test suites**: `test_js_e2e.ailang` (9 tests, 31/32 assertions passing — variable-to-innerHTML assignment WIP), `bench_js.ailang` (7 micro-benchmarks, 5.9x faster than V8 overall; fib(20) 41x, arith 89x).

**Status**: String literal innerHTML mutation works end-to-end. Variable-to-innerHTML assignment has a stack ordering issue in SET_PROP dispatch (obj resolves as NUMBER instead of OBJECT). Under investigation.

**Build**: `./ailang.x TestCode/test_js_e2e.ailang test_js_e2e.x && ./test_js_e2e.x`

### Implemented Features (completed across sessions)

- **Arrow functions** — ARROW token in JSLexer, ARROW_EXPR(47) AST node in JSParser (`IsArrowHead` lookahead + `ArrowFunc` parser), compiled via `JSComp__CompileFunc` reuse in JSCompiler. Supports `x => expr`, `(x, y) => expr`, `(x, y) => { stmts }`. Concise body auto-wrapped in RETURN_STMT→BLOCK.
- **Error constructors** — Handlers 15-21 in JSRT_CallNative for Error/TypeError/RangeError/ReferenceError/SyntaxError/URIError/EvalError. Each creates object with `name`, `message`, `__class__` properties. Registered as globals in JSVM_InstallBuiltins via `JSBridge__CreateNativeFunc`. `JSRT_Instanceof` checks `__class__` property against function name.
- **Native handler dispatch** — VM threshold at 22: handlers 0-21 go to JSRT_CallNative (0-14 math/type, 15-21 Error ctors), handlers 22+ go to JSBridge_Dispatch. All JSBridge native IDs bumped by +6 (CONSOLE_LOG=22 through MATH_FLOOR=42).
- **Generators** — Full `function*`/`yield`/`.next()`/`.return()`/`.throw()` implementation across all layers. KW_YIELD(101) token in JSLexer, YIELD_EXPR(48)/GEN_FUNC_DECL(49)/GEN_FUNC_EXPR(50) AST nodes in JSParser, GEN_CLOSURE(74)/YIELD(73) opcodes in JSCompiler, GENERATOR(8) value type in JSRuntime with 104-byte state block (private stack + frames), coroutine-style VM state swapping in JSVM (save/restore pc/sp/fp/stack/frames). Generator object created on CALL to generator function, `.next()` resumes via `JSVM__GenNext` with full state isolation. Supports `function*`, `*method()`, `function*()` expressions, `yield`, `yield*` (delegate), `yield` as expression with `.next(value)` pass-through.
- **Regex** — Added by user externally (Library.JSRegex.ailang, Thompson NFA, 1217 lines)
- **OOP** — Added by user externally (Library.JSOop.ailang, 920 lines)
- **Exponentiation (`**`)** — STAR_STAR/STAR_STAR_ASSIGN tokens in JSLexer, precedence 11 (right-associative) in JSParser Pratt table, EXP opcode (26) in compiler/VM, `JSRT_Exp` iterative squaring in runtime.
- **Numeric separators (`1_000`)** — JSLexer skips `_` (95) in decimal digit scanning, JSParser `ParseInt` skips `_` during value computation.
- **Nullish coalescing (`??`)** — NULLISH token in JSLexer, precedence 1 in parser, short-circuit compilation via `JMP_NULLISH` opcode (53) — jumps if top-of-stack is NOT null/undefined.
- **Logical assignment (`&&=`, `||=`, `??=`)** — AND_ASSIGN, OR_ASSIGN, NULLISH_ASSIGN tokens, wired through parser `IsAssignOp` and compiler compound-assignment dispatch. Simplified semantics (always evaluates RHS); proper short-circuit TODO.
- **Class syntax** — Full basic class support across all layers. **JSLexer**: KW_CLASS(102), KW_EXTENDS(103), KW_SUPER(104), KW_STATIC(105) tokens. **JSParser**: CLASS_DECL(51), CLASS_EXPR(52), SUPER_EXPR(53) AST nodes; `JSParse__ClassDecl`, `JSParse__ClassExpr`, `JSParse__ClassBody` parse class declarations/expressions with constructor, methods, static methods, get/set accessors, extends clause. **JSCompiler**: `JSComp__CompileClass` (~450 lines) compiles classes to constructor function + prototype object using existing opcodes (CLOSURE, NEW_OBJECT, SET_PROP, GET_PROP) — no new VM opcodes needed. Extends sets up `__proto__` chain. `__super__` local holds parent constructor for super() calls. Methods compiled as closures and set on prototype. Statics set on constructor. **JSValidate**: KW_CLASS added to stmt_start and expr_start tables, KW_SUPER added to expr_start. **Parser keyword range**: Extended from 70-100 to 70-105 in 4 locations (object literal property keys, get/set accessor detection, dot member access) to accept `class`/`extends`/`super`/`static` as property names per ES spec. Class-only test262 results: statements/class 2401/4367 (55.0%), expressions/class 943/4059 (23.2%), total 3344/8426 (39.7%).
- **For-of loops** — Eager-materialization approach using TO_ARRAY opcode. **JSParser**: FOR_OF_STMT(54) AST node, contextual `of` keyword detection (IDENT with bytes 111,102) in both var-decl and expression-init branches of `JSParse__ForStmt`. Reuses `for_is_in` flag to skip condition/update clauses. **JSCompiler**: TO_ARRAY(75) opcode, FOR_OF_STMT compilation (~200 lines) mirrors FOR_IN_STMT pattern — `compile(rhs) → TO_ARRAY → __vals__ local, __idx__=0, loop: if idx>=vals.length break, lhs=vals[idx], body, idx++, goto loop`. **JSVM**: Case 75 (TO_ARRAY) — arrays pass through unchanged, strings split into single-character arrays via `JSRT_CreateStringLen(ptr, 1)`, fallback returns empty array. Design trade-off: eager materialization loses lazy generator iteration but covers the vast majority of test262 for-of tests. Result: +267 net passes (11,861 → 12,128).
- **Object.defineProperty / Object.keys / Object.create / Array.isArray** — Full Object and Array global implementation. 14 native handler IDs (43-56). Object.defineProperty stores getter as `__get_<prop>`, setter as `__set_<prop>`, value directly. Object.keys wraps `JSRT_ObjKeys()`. Object.create sets `__proto__`. Object.assign copies own enumerable props. Object.freeze sets `__frozen__` flag. Array.isArray checks JSType.ARRAY. Array.from copies arrays/splits strings. Object.getOwnPropertyDescriptor builds descriptor object. Object.is does SameValue comparison. Registered in JSVM_InstallBuiltins using JSRT__Push/Pop (not JSBridge__Push/Pop) since JSBridge may not be initialized. Result: ~+500 passes.
- **Class method destructuring parameters** — Class body parameter parser was only accepting simple IDENT tokens. Replaced with full destructuring-aware parsing matching the FuncExpr path: supports `{ x, y }` object patterns, `[ a, b ]` array patterns, `...rest` parameters, and `= default` values. All patterns use AST__Push/Pop to protect 8 local variables (ASTTmp.first, ASTTmp.last, ASTTmp.done, mflags, method, param_first, param_last, p_done) across recursive JSParse__ParseBindTarget/JSParse__Assign calls. Result: ~+2,000 passes.
- **Destructuring assignment + for-of destructuring** — Two-part fix. **(1) For-of with patterns**: JSParser `JSParse__VarDeclSingle` now skips `=` requirement when next token is `in` or `of` (contextual detection, skip_semi=1 for-loop context). JSCompiler FOR_OF_STMT handler checks `forof_dstr_pat = JSParse_GetRight(lhs_n)` — when pattern exists, stores element in `__dt__` temp local and dispatches to `JSComp__CompileArrayPattern`/`JSComp__CompileObjPattern`. **(2) Assignment destructuring**: Cover grammar conversion via `JSParse__CoverToPattern` — recursive walker converts ARRAY_LIT(25)→ARRAY_PATTERN(42), OBJECT_LIT(24)→OBJECT_PATTERN(43), UNDEF_LIT→NULL_LIT (holes), SPREAD_ELEMENT→REST_ELEMENT, nested patterns recursed. Called from `JSParse__Assign` when `=` follows ARRAY_LIT/OBJECT_LIT. JSValidate assign_target table extended with types 24,25,42,43. Compiler ASSIGN handler detects ARRAY_PATTERN/OBJECT_PATTERN LHS → compile RHS, DUP (return value), store in `__dt__` temp, dispatch to pattern compilers. Result: +422 net passes (12,128 → 12,550).

### Test262 Conformance (as of 2026-05-04)

`tools/test262_runner.py` has been fully unblocked — `UNSUPPORTED_FEATURES = set()`, `UNSUPPORTED_SOURCE_PATTERNS = []`, `should_skip()` always returns `(False, "")`.

Build & run: `./ailang.x TestCode/test262_harness.ailang test262_harness.x && python3 tools/test262_runner.py`

Use `--all` flag for full suite: `python3 tools/test262_runner.py --all`

#### Full Suite (23,899 tests, --all flag)

**Overall: 17,759 / 23,899 passing (74.5%)** — post optional chaining, template literals, catch destructuring, parallel runner

Previous: 17,488/23,899 (73.4%). Net +271 from template literal fixes, optional chaining, catch param destructuring/parameterless catch, scope infrastructure (WIP).

#### Benchmark Results

- **SunSpider 1.0**: 26/26 passing (100%) — all tests execute correctly
- **Octane**: 8/8 core benchmarks parse+execute (richards, deltablue, crypto, raytrace, earley-boyer, navier-stokes, splay, code-load)
- **Internal micro-benchmarks**: 6.3ms total (fib(20)=0.147ms, loop 100k=5.4ms, arith 50k=0.14ms)

**Full suite failure breakdown by category:**

| Category | Total | Pass | Fail | Pass% | Root cause |
|---|---|---|---|---|---|
| statements/class | ~4367 | ~2401 | ~1966 | 55.0% | Async methods, private fields, destructuring/default/rest params, computed props |
| expressions/class | ~4059 | ~943 | ~3116 | 23.2% | Same as above; expressions have more edge cases |
| expressions/object | 1161 | 902 | 259 | 77.7% | Computed props, shorthand methods, getters/setters, spread |
| expressions/assignment | 485 | 185 | 300 | 38.1% | Destructuring patterns |
| for-await-of | ~1100 | ~6 | ~1094 | 0.5% | No async/await |
| for-of | ~600 | ~80 | ~520 | 13.3% | No for-of iterator protocol |
| expressions/arrow-function | 343 | 132 | 211 | 38.5% | Destructuring params, async arrows |
| dynamic-import | ~370 | ~5 | ~365 | 1.4% | No module support |
| async-generator | ~470 | ~4 | ~466 | 0.9% | No async/await |
| async-function (expressions+declarations) | ~350 | ~0 | ~350 | 0% | No async/await |
| expressions/template-literal | 57 | 20 | 37 | 35.1% | Tagged templates, nesting |
| identifiers | 268 | 148 | 120 | 55.2% | Unicode escapes, reserved word edge cases |
| block-scope/syntax | 113 | 14 | 99 | 12.4% | let/const block scoping syntax |
| literals/numeric | 157 | 87 | 70 | 55.4% | Float literals, hex/octal edge cases |
| statements/switch | 111 | 40 | 71 | 36.0% | let/const scoping in case blocks |
| statements/variable | 178 | 140 | 38 | 78.7% | let/const TDZ semantics |
| compound-assignment | 454 | 383 | 71 | 84.4% | Destructuring in compound targets |

**Tier analysis (by fixability, updated post for-of):**

- ~~**Tier 1 — Destructuring assignment**~~ — DONE (2026-05-03). Cover grammar conversion + for-of pattern binding. +422 passes.
- **Tier 2 — Class improvements (~5000 remaining failures):** Basic class works. Remaining failures are async methods, private fields (`#field`), destructuring/default/rest params in class methods, computed property names in classes.
- **Tier 3 — Template literal improvements (~37 failures):** Tagged templates, nested expressions. Small scope, quick win.
- **Tier 4 — let/const TDZ + block scoping (~200 failures):** Proper temporal dead zone enforcement, block-scoped declarations in switch/for. Moderate compiler work.
- **Tier 5 — Async/await (~1800 failures, 15%):** for-await-of, async generators, async functions. Requires Promise implementation + async state machine. Very high effort. Defer.
- ~~**for-of + iterator protocol**~~ — DONE (2026-05-03). Basic for-of via TO_ARRAY eager materialization. Full iterator protocol (Symbol.iterator/.next()/.done) deferred — current approach covers arrays and strings.

## Pending Work

### JS Engine — Test262 Conformance Push (active)

**Current: 17,759/23,899 (74.5%). Target: 80%+ (~19,100 passing).**

Class syntax implemented (2026-05-03): +1,280 genuine new passes. statements/class at 55.0%, expressions/class at 23.2%.
For-of loops implemented (2026-05-03): +267 net passes via TO_ARRAY eager materialization. Crossed 50% milestone.
Destructuring fixes (2026-05-03): +422 net passes. Two fixes: (1) for-of with var/let/const destructuring LHS (parser skip `=` when `in`/`of` follows pattern, compiler stores element in `__dt__` temp and dispatches to CompileArrayPattern/CompileObjPattern), (2) standalone assignment destructuring via cover grammar conversion (ARRAY_LIT→ARRAY_PATTERN, OBJECT_LIT→OBJECT_PATTERN in JSParse__Assign, new JSParse__CoverToPattern recursive walker, compiler handles ASSIGN with pattern LHS).

#### Priority 1: Template Literal Improvements (~37 recoveries)

- Tagged templates: `tag\`hello ${name}\`` — pass template array + substitutions to tag function
- Nested template literals in expressions

#### Priority 3: let/const Block Scoping (~200 recoveries)

- TDZ enforcement (reference before declaration = ReferenceError)
- Block-scoped declarations in switch cases, for heads
- const reassignment errors

#### Lower Priority (defer)

- **Async/await (~1800 failures)** — Requires Promise implementation, event loop, async state machine. Very high effort. Defer.
- **Dynamic import (~365 failures)** — Module system. Defer.
- **JS engine innerHTML variable assignment** — SET_PROP stack ordering bug when RHS is a variable (obj pops as NUMBER not OBJECT); string literal path works

### Plan for HalCode9000 Worker Deployment

Use HalCode9000 MCP workers (cheap DeepSeek tokens) for parallelizable grunt work:
- **Worker 1**: Analyze test262 failure categories, extract patterns from failing tests
- **Worker 2**: Implement feature syntax in JSLexer + JSParser (token + AST node additions)
- **Worker 3**: Implement feature compilation in JSCompiler (bytecode generation)
- **Worker 4**: Run test262 subsets during development to validate progress
- Claude (expensive model) orchestrates, reviews, and handles architectural decisions

### Floating Point — Q16.16 / Q8.8 Fixed-Point Plan

JS engine currently uses 64-bit signed integers only. Plan for numeric precision:

- **Q16.16 wide mode** (2x 64-bit ints): left int = high 32 bits, right int = low 32 bits. Gives 16 bits integer + 16 bits fractional per component. Use MemoryCopy/MemorySet (both SSE2 via REP MOVSB/STOSB) for bulk operations.
- **Q8.8 compact mode** (1x 64-bit int): upper 56 bits integer, lower 8 bits fractional. Fits in a single JSValue payload slot.
- **Runtime detector**: pick mode at startup based on precision requirements. Q8.8 for game/UI math, Q16.16 for financial/scientific.
- This avoids needing actual IEEE 754 float support in the compiler while giving fractional math that passes Test262 numeric tests. The SSE2 REP MOVSB/STOSB path is already in the compiler.

### Other

- **Ladybird live testing** — test `ladybird_ipc.x` on live display server, performance tuning, tab management
- **Terminal polish** — toolbar actions, cursor blink, mouse reporting (?1000h/?1006h)
- **Audio engine split** — extract from display server into standalone service
- **Video player seek** — FF/RW via command pipe or restart-with-offset
- **Scientific calculator** — trig, log, parentheses
- **Start Menu UI** — side navigation, categories, running-app indicators
- **Encryption at rest** — login gates master key, per-service keys
- **SSE2 optimization** — FB_ClearBuffer, compiler integer SSE2 emit

---

## HalCode9000 — MCP Server for Cheap LLM Workers

`Applications/HalCode9000/` — MCP server written in native AILang. Fire it up to run cheap DeepSeek (or other LLM) workers with full tool access. Terminal-mode TUI with streaming, multi-provider support, and agentic tool dispatch over IPC.

### MCP Tools (cc_tools/)

Each tool is a standalone IPC subprocess spawned by HalCode9000. The server dispatches tool calls from the model to these workers over abstract Unix sockets:

| Tool | Source | Socket | Description |
|------|--------|--------|-------------|
| Bash | `cc_bash_ipc.ailang` | `@halcode/Bash` | Shell execution, 30s default / 55s max timeout |
| Read | `cc_read_ipc.ailang` | `@halcode/Read` | File read |
| Write | `cc_write_ipc.ailang` | `@halcode/Write` | File write |
| Ls | `cc_ls_ipc.ailang` | `@halcode/Ls` | Directory listing |
| Head | `cc_head_ipc.ailang` | `@halcode/Head` | File head (first N lines) |
| WebFetch | `cc_webfetch_ipc.ailang` | `@halcode/WebFetch` | URL fetch |
| PgMem | `cc_pgmem_ipc.ailang` | `@halcode/PgMem` | PostgreSQL memory/context store |
| Relmem | `cc_relmem_ipc.ailang` | `@halcode/Relmem` | Relational memory — codebase symbol index |

All tools share the 60-second `IPCDispatch` hard timeout. Protocol: abstract Unix sockets, JSON over length-prefixed frames.

**Key value prop:** DeepSeek flash tokens are dirt cheap. Spin up HalCode9000 instances as disposable workers for grunt work — bulk file processing, code search, test runs, refactoring passes — while the expensive model (Claude) focuses on architecture and decision-making. Each worker gets the full tool suite above, so it can read/write/execute autonomously.

### Build commands

```
cd /mnt/c/Users/Sean/Documents/AILangSH
./ailang.x Applications/HalCode9000/HalCode9000.ailang Applications/HalCode9000/HalCode9000.x
./ailang.x Applications/HalCode9000/cc_tools/cc_bash_ipc.ailang     Applications/HalCode9000/cc_bash_ipc.x
./ailang.x Applications/HalCode9000/cc_tools/cc_read_ipc.ailang     Applications/HalCode9000/cc_read_ipc.x
./ailang.x Applications/HalCode9000/cc_tools/cc_write_ipc.ailang    Applications/HalCode9000/cc_write_ipc.x
./ailang.x Applications/HalCode9000/cc_tools/cc_ls_ipc.ailang       Applications/HalCode9000/cc_ls_ipc.x
./ailang.x Applications/HalCode9000/cc_tools/cc_head_ipc.ailang     Applications/HalCode9000/cc_head_ipc.x
./ailang.x Applications/HalCode9000/cc_tools/cc_webfetch_ipc.ailang Applications/HalCode9000/cc_webfetch_ipc.x
./ailang.x Applications/HalCode9000/cc_tools/cc_pgmem_ipc.ailang    Applications/HalCode9000/cc_pgmem_ipc.x
./ailang.x Applications/HalCode9000/cc_tools/cc_relmem_ipc.ailang   Applications/HalCode9000/cc_relmem_ipc.x
cd Applications/HalCode9000 && ./HalCode9000.x
```

HalCode9000.ailang imports backends/ and UI.ailang transitively — a single compile of HalCode9000.ailang rebuilds everything except the cc_tools.

### Provider menu (startup)

```
1. Anthropic  (claude-sonnet-4-6)
2. OpenAI     (gpt-4o)
3. Grok       (xAI) — grok-3-mini-fast  ← NOTE: Grok/xAI, NOT Groq (different company)
4. Gemini     (gemini-2.0-flash)
5. Local      (localhost:11434, ollama)
6. DeepSeek   (deepseek-v4-flash)
```

Option 3 is **Grok by xAI** (`api.x.ai`). The HalCode9000.ailang currently labels it "Groq" — needs renaming to "Grok / xAI".

### UI layout (5-row prompt, as of 2026-04-30)

```
[chat scrollback region]
 ─────────────────────────  ← top rule (straight ─, no ╭/╰)
 > input here               ← body row (1 row)
 ─────────────────────────  ← bottom rule
   ↑1234 ↓567   /help · /clear · /quit   ← hint row (tok_in/tok_out left, commands right-aligned)
```

- `UILayout.prompt_h = 5` (quote + top_rule + body + bot_rule + hint)
- `UI.SetTokens(in, out)` — stores to UILayout.tok_in/tok_out, repaints hint row
- `UI.SetQuote(text)` — paints a dim status/quote line above the prompt box
- `UI.AnimTick()` — ticks mascot animation during model TTFT wait (call from idle poll loop)
- `UI.ChatPrintDim(s)` — dim+italic print for DeepSeek reasoning_content stream

### Known UI.ailang issue to never repeat

The Write tool wrote a literal `\n` (backslash-n, 0x5c 0x6e) at the end of UI.ailang as part of a test marker comment. The AILang lexer saw `\` at column 1 as "Unknown character" and refused to compile. Fixed by trimming the trailing garbage bytes. **Never append `\n` as literal text to .ailang files** — it must be an actual newline byte.

### DeepSeek tool_calls fix (backends/OpenAI.ailang)

Library.JSON's XSHash dropped `tool_calls` when `reasoning_content` was also present in the same object (root cause unclear — bucket collision or ordering). Fix: `OpenAI_BuildAssistantMsgStr()` builds the entire assistant message as raw JSON via `StringConcat` + `JSON.EscapeString`, then `ParseJSON` back. Bypasses XSHash for that object entirely.

**Critical**: OpenAI `arguments` field must be a JSON-encoded STRING (not inline object): `"arguments": "{\"path\":\"/etc/hostname\"}"`. Use `JSON.EscapeString(args_ptr)` before inserting.

### Token display

Both Anthropic and OpenAI backends now call `UI.SetTokens(in, out)` after each turn instead of printing dim text to chat. Anthropic reads `message.usage.input_tokens` from `message_start` event, `usage.output_tokens` from `message_delta` event.

### Relmem (cc_relmem_ipc) — current state and pending redesign

**Current state (2026-04-30):**
- Index at `~/.claude/relmem/index.json` (~4MB, already built)
- Socket: `@halcode/Relmem` (abstract Unix socket, bypasses WSL2 tmpfs)
- Path guard added to `Op_Index`: rejects `/`, `/mnt`, `/mnt/c*`, `/home` — returns error instead of hanging

**Pending redesign (user-specified):**
`Op_Index` must be redesigned to **require model interaction** rather than walking the filesystem itself:
1. **Clear** — drop existing index entries for the project path
2. **Stash** — model uses Bash to enumerate files (e.g. `find <path> -name "*.ailang" | head -500`); op=index without a `files` param should return instructions for this step
3. **Grep into results** — op=index with `files=<newline-separated-paths>` processes each listed file using grep-style symbol extraction (not the full AILang AST Walker)

This replaces the recursive `Walker_Walk` entirely. The bespoke `Walker_RecurseDir` / `Walker_ProcessFile` / `Parser_Dispatch` chain stays for now but `Op_Index` should no longer call it. Until redesign is done, the path guard prevents hangs.

### WSL2 Hard Rules (system prompt rules 1-5)

Encoded in `CCConst.SYSTEM_PROMPT` in `HalCode9000.ailang`:
1. NEVER `find /`, `/mnt`, `/mnt/c` — unbounded, hangs permanently
2. Use `Relmem op=symbols` to locate files in the indexed codebase
3. If using `find`, scope to a specific known subdirectory
4. Never produce unbounded output — always pipe through `head`/`grep`/`tail`
5. NEVER `Relmem op=index` with broad paths — index already built, use `op=symbols`

### Known crash: ~1700 output tokens causes death

Observed consistently: model responses that reach approximately 1700 tokens cause a crash/hang. Not a one-time event — reproducible. Likely a history buffer overflow or a per-turn output buffer cap in the streaming path. **Not yet diagnosed or fixed.** Check `CCHistory`, `AgentLoop.ailang` turn buffer, and `TUI_BufferWriteStr` overflow.

### Bash tool timeout

`cc_bash_ipc.ailang`: `DEFAULT_TIMEOUT = 30` seconds. `timeout_secs=0` from the model maps to 30s, capped at 55s (so IPCDispatch's 60s fence always fires last). Already implemented.

### IPCDispatch

60-second hard timeout on all tool calls via `Socket.SetRecvTimeout(fd, 60000)`. After timeout: returns `"tool TIMED OUT (60s): <name>"` to model. `IPCDispatch_Reconnect` called to flush stale socket state.
