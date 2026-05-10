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
- **FixedMul/FixedDiv**: Compiler primitives for fixed-point arithmetic. `FixedMul(a, b, bits)` = `(a * b) >> bits`, `FixedDiv(a, b, bits)` = `(a << bits) / b` (direct IDIV, exact, signed). `bits` must be a compile-time constant: 8 (Q8.8), 16 (Q16.16), 32 (Q32.32), or 64 (Q64.64). FixedDiv guards division-by-zero (returns 0). All widths handle negative values correctly via signed IMUL/IDIV. Implementation: `Librarys/Compiler/Compile/FPU/X86/Library.FPUCompileX86FixedPoint.ailang` (compile layer, Branch/Case dispatch) + `Library.FPUEmitX86FixedPoint.ailang` (x86-64 byte emission). Tests: `TestCode/TestFixedPointPrimitives.ailang` (36/36 passing, zero tolerance).
- **Top-level code restriction**: AILang does not allow executable code (variable assignment, function calls that store results) at the top level outside of `SubRoutine`/`Function` bodies. Top-level has RBP=0 (no stack frame), so local variable stores crash. Use `SubRoutine.Main { ... }` + `RunTask(Main)` for entry points. FixedPool declarations are fine at top level (they're globals via R15).

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
│   # JSLexer, JSParser, JSCompiler, JSRuntime, JSVM, JSBridge, JSEngine, JSJIT
│   # JSRegex, JSOop, JSValidate
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

11 libraries in `Librarys/Browser/` (~23,300 LOC total):

| Library | LOC | Role |
|---------|-----|------|
| JSLexer | 1798 | Tokenizer, ~49 token types (KW_VAR=70 through KW_STATIC=105), template escape validation |
| JSParser | 5116 | Recursive descent, Pratt precedence, ~55 AST node types, class/destructuring/for-of |
| JSCompiler | 4135 | AST -> bytecode (~75 opcodes), constant pool, local resolution, class compilation |
| JSRuntime | 3370 | JSValue (16-byte tagged: type+payload), coercion, object/array/generator ops |
| JSVM | 2361 | Branch-dispatch loop, 4096-deep value stack, generator coroutines, eval() |
| JSBridge | 2073 | DOM bindings + Object/Array/Error globals (56 native handlers) |
| JSEngine | 902 | Orchestrator: extract `<script>` tags, lex->parse->compile->run pipeline |
| JSJIT | 1032 | x86-64 JIT compiler via CEmit ARCH backend, param_block calling convention |
| JSRegex | 1216 | Thompson NFA regex engine (user-authored) |
| JSOop | 919 | Prototype chain, instanceof, property descriptors (user-authored) |
| JSValidate | 382 | Token validation tables for parser lookahead |
| PropTable | ~420 | FixedPool property tables (replaced XSHash) — linear-scan object props + open-addressed global hash |

**Value types**: UNDEFINED(0), NULL(1), BOOLEAN(2), NUMBER(3, IEEE 754 double bits in 64-bit payload), STRING(4), OBJECT(5, PropTable), FUNCTION(6), ARRAY(7, XArray), GENERATOR(8). Full IEEE 754 floating point via SSE2 intrinsics (`Float_Add`, `Float_Sub`, `Float_Mul`, `Float_Div`, `Float_FromInt`, `Float_ToInt`, `Float_Lt`, `Float_Gt`, `Float_Eq`, etc.). `JSRT_CreateNumber(n)` stores `Float_FromInt(n)`, `JSRT_CreateFloat(bits)` stores raw double bits. Extracting integer from NUMBER payload requires `Float_ToInt(JSRT_GetPayload(...))`. No GC — zero-alloc hot path via fixed pools, ring buffers, and slab allocators.

**Memory architecture (zero-alloc hot path)**:
- `val_pool` — 65536-entry ring buffer for JSValue slots (16 bytes each, ~1 MB). `JSRT__AllocValue()` bumps cursor, wraps at capacity.
- `str_slab` — 512 KB bump allocator for string data. `JSRT__StrSlabAlloc(sz)` bumps cursor, wraps at capacity. Used by `JSRT_CreateString`, `JSRT_CreateStringLen`, `JSRT__StrConcat`.
- `func_slab` — 64 KB bump allocator for function descriptors (64 bytes each, 1024 slots). `JSRT__FuncSlabAlloc()`.
- `gen_slab` — 512 KB bump allocator for generator state (stack + frames). `JSRT__GenSlabAlloc(sz)`.
- `PropTable` — 4096-entry × 264-byte ring buffer slab (~1.03 MB) for object property tables. Linear scan array (16 entries per object, 16 bytes per entry: key_ptr + value). `PropTable_Alloc()` bumps cursor. Replaced XSHash entirely.
- `GlobalHash` — 512-slot open-addressed hash table (8 KB, fixed lifetime) for global variables. DJB2 hash, linear probing. `GlobalHash_Lookup` / `GlobalHash_Insert`.
- `const_val_pool` — Static 32 KB + 64 KB buffers for bytecode constant value cache (used when ≤4096 constants; Allocate fallback for oversized programs only).
- Static backup buffers for `JSVM__CallFunc` (re-entrant calls) and `JSVM__GenNext` (generator resume): pre-allocated at init, no per-call allocation.
- All runtime Allocate() calls eliminated. Only init-time (~100 calls), compiler scope save (recursive/cold), and peripheral I/O subsystems use Arena.

**Key patterns**:
- `JSCompDot` FixedPool for MEMBER_DOT assignment compilation (survives recursive JSComp__CompileExpr calls)
- `JSBridgeTmp` / `JSVMTmp` FixedPools for clobber-safe temporaries across function calls
- `JSRT_ToString` returns JSValue pointer; use `JSRT_GetPayload()` to extract raw C string
- `JSBridge__GetDomIdx` checks `__dom_idx` property on JS wrapper objects to map back to DOM nodes

**Test suites**: `test_js_e2e.ailang` (9 tests, 32/32 assertions passing), `bench_js.ailang` (8 micro-benchmarks including JIT).

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
- **Optional chaining (`?.`)** — QUESTION_DOT token in JSLexer, compiled via JMP_NULLISH short-circuit in JSCompiler. Supports `obj?.prop`, `obj?.method()`, `obj?.[expr]`. Chains correctly with nested access.
- **Catch destructuring + parameterless catch** — JSParser handles `catch ({ message })` and `catch` (no parens). Compiler dispatches destructuring pattern to CompileObjPattern/CompileArrayPattern on catch parameter.
- **Template literal escape validation** — JSLexer rejects legacy octal escapes (`\1`-`\9`), `\0` followed by digit, invalid `\xNN`, and invalid `\uXXXX`/`\u{...}` in template literals. Sets `JSTokState.error = 1` and `JSLex_Tokenize` returns 0 on error. Result: template-literal category 54/57 (94.7%).
- **Private class members + instance fields as own properties** — Private fields (`#x`), private methods (`#method()`), and private accessors (`get #x()`, `set #x(v)`) work via name mangling: `#foo` stored as literal property name `"#foo"`. Since `#` is not a valid JS identifier character, user code cannot access private members externally — privacy is syntactic with zero new infrastructure. **Lexer**: PRIVATE_NAME(120) token already tokenizes `#identifier`. **Parser**: dot member access already accepts PRIVATE_NAME (JSParseExpr.ailang:1274), class body parser accepts PRIVATE_NAME for fields/methods. **Instance fields**: Compiled as `__field_init__` closure stored on prototype. Closure takes `this_obj` as parameter, sets each field via `GET_LOCAL 0; <init>; SET_PROP`. **VM**: RETURN handler (JSVMDispatch.ailang:1004-1019) calls `__field_init__` after constructor returns — looks up `__proto__.__field_init__`, calls via `JSVM__CallFunc`. Frame pointer saved before `JSVM__CallFunc` to avoid invalidation (CallFunc zeroes frames buffer). Static fields compiled directly onto constructor via `GET_GLOBAL ctor_slot; <init>; SET_PROP`. **Limitation**: Parent class `__field_init__` not chained through `super()`. **Files**: JSCompStmt.ailang (lines 1875-2013), JSVMDispatch.ailang (lines 997-1024).
- **Array named properties (ArrSide)** — Arrays can now hold named properties (`a.foo = 42`). Since ARRAY JSValues store an XArray pointer at offset +8 (no room for a PropTable), a side table (`ArrSide`) maps array JSValue pointers to PropTable handles. 256-entry linear scan, 16 bytes per entry `[arr_ptr(8) | proptable_ptr(8)]`. `ArrSide_Lookup` for reads, `ArrSide_GetOrCreate` for writes (lazy PropTable allocation). Integrated into `JSRT_ObjGet` and `JSRT_ObjSet` with ARRAY type checks before the OBJECT-only rejection. Reset in `GlobalHash_Reset`. **Files**: `Library.PropTable.ailang` (ArrSide functions + state), `Library.JSRTObject.ailang` (ObjGet/ObjSet ARRAY handlers).
- **SWAP opcode + property increment** — New SWAP opcode (value 8) swaps top two stack elements. Required for correct postfix property increment (`o.x++`) which must return the old value. **Postfix `o.x++`**: `compile(o), DUP, GET_PROP, SWAP, DUP, GET_PROP, PUSH_CONST 1, ADD, SET_PROP` → old value on stack. **Prefix `++o.x`**: `compile(o), DUP, GET_PROP, PUSH_CONST 1, ADD, SET_PROP, re-compile(o), GET_PROP` → new value. Also handles MEMBER_BRACKET via re-eval approach. **Files**: `Library.JSCompiler.ailang` (SWAP=8 in JSOp), `Library.JSVMDispatch.ailang` (Case 8 handler), `Library.JSCompExpr.ailang` (UPDATE_EXPR MEMBER_DOT/MEMBER_BRACKET handlers).
- **Getter key stability (str_slab)** — DEF_GETTER/DEF_SETTER (opcodes 64, 65, 76, 77) now copy `__get_`/`__set_` key strings from transient `JSVMCallBuf.getter_buf` to stable `str_slab` memory via `JSRT__StrSlabAlloc` + `MemoryCopy` before passing to `JSRT_ObjSet`. Previously, PropTable stored the pointer to the shared 128-byte `getter_buf`, causing pointer-equality false matches when GET_PROP's getter check overwrote the buffer with a different key — resulting in infinite recursion on any `this.<prop>` access inside getter bodies. The JSBridge `Object.defineProperty` path was unaffected (uses per-call buffer from `JSBridgeStack.pool`). **Files**: `Library.JSVMDispatch.ailang` (cases 64, 65, 76, 77). Result: +892 tests (44,648 → 45,540).
- **JIT Compiler (x86-64 native code generation)** — Full working JIT for leaf functions via CEmit ARCH backend. **Architecture**: `Library.JSJIT.ailang` uses the CEmit layer (`Library.CEmitCore.ailang` + `Library.CEmitCoreArch.ailang` + X86 backend) to emit native x86-64 instructions into executable mmap'd buffers. **Register convention**: R12=stack base ptr, R13=sp index, R14=const pool, RBP=locals base, RBX=scratch. **param_block pattern**: Stable 32-byte heap block allocated at JIT_Init. JIT_Execute writes [stack_base, sp, locals_ptr, const_pool] before each native call. Prologue loads from baked param_block address (stable across calls). Epilogue writes sp back. **Supported opcodes**: GET_LOCAL, SET_LOCAL, ADD, SUB, MUL, DIV, RETURN, HALT. Locals at `rbp + idx*8` matching VM's 8-byte slot size. **Compilation**: `JIT_Compile(func_idx)` scans bytecode, emits prologue+opcodes+epilogue, resolves fixups. Unsupported opcodes bail (function stays interpreted). **Performance**: `add(a,b)` compiles to 220 bytes native. 10k calls in ~5.5ms. **Files**: `Library.JSJIT.ailang` (JIT orchestrator), `Library.CEmitCoreArch.ailang` (arch-neutral emit API including `Emit_MovRaxRbp`), `Librarys/Compiler/CodeEmit/X86/Library.CEmitX86Reg.ailang` (x86 backend including `X86_MovRaxRbp`).

### Test262 Conformance (as of 2026-05-10)

Build & run: `./ailang.x TestCode/test262_harness.ailang test262_harness.x && python3 tools/test262_runner.py --all` (language only, ~24K tests) or `--full` (language + built-ins + annexB + staging, ~50K tests).

**Batch harness** (fast): `./ailang.x TestCode/test262_harness_batch.ailang test262_harness_batch.x` — streams tests via stdin (4-byte LE length prefix + source), writes 1-byte results to fd 4 (original stdout saved via dup2). Runner auto-detects batch binary and uses it by default; `--no-batch` for legacy per-process mode.

**Overall (full): 45,540 / 49,998 passing (91.8%)** — 4,068 failures, 263 timeouts

Milestones: 11,861 (2026-05-02) → 12,550 (destructuring) → 17,488 (class+OOP) → 17,759 (optional chaining) → 16,421 (stable after zero-alloc refactor) → 16,884 (statement validation + async params + static blocks) → 18,000/43,034 (TDZ scope fix) → 44,648 (conservative ScanString validation, 2026-05-09) → 45,540 (getter key stability fix, 2026-05-10).

#### Benchmark Results (Phenom II X6 3.2GHz, DDR3)

- **SunSpider 1.0**: 26/26 passing (100%)
- **Kraken 1.1**: 14/14 passing (100%)
- **Octane**: 15/15 benchmarks parse+execute (100%), including multi-part (gbemu, typescript, zlib)
- **E2E tests**: 32/32 passing (9 integration tests)
- **Internal micro-benchmarks** (8 tests) vs V8 (Node.js v18, JIT-warmed):

| Benchmark | Ailang | V8 | Ratio | Winner |
|---|---|---|---|---|
| JIT leaf 10k calls | 10.2 ms | 0.04 ms | 268x | V8 |
| loop 100k iters | 2.3 ms | 0.27 ms | 8.6x | V8 |
| fib(20) recursive | 0.14 ms | 0.34 ms | 0.4x | **Ailang** |
| arith 50k iters | 0.14 ms | 0.37 ms | 0.4x | **Ailang** |
| obj props 10k iters | 0.15 ms | 0.09 ms | 1.7x | V8 |
| string concat 1k | 0.12 ms | 0.09 ms | 1.4x | V8 |
| nested calls 10k | 0.15 ms | 0.03 ms | 6.0x | V8 |
| array 5k push+sum | 0.16 ms | 0.17 ms | 0.9x | **Ailang** |
| **TOTAL** | **13.3 ms** | **1.4 ms** | **9.6x** | |

Ailang beats V8 on fib(20), arith, and array ops. V8 wins on JIT leaf calls (full optimizing compiler) and nested calls (inline caching).

#### Known bugs (active)

- **Comma operator**: 3+ operand chains broken.
- **`new C().method()` chaining**: Method call on inline `new` expression doesn't bind `this` correctly. `var c = new C(); c.method()` works fine.
- **Parent field init in extends**: `class B extends A { b = 2 }` — B's `__field_init__` runs but A's does not. Parent fields not initialized via `super()` chain.

#### Remaining failure categories (4,068 failures as of 2026-05-10)

| Category | Failures | Root cause |
|---|---|---|
| class/elements | ~300 | Missing early error checks (static semantics), async generator yield*, unicode private names |
| class/dstr | ~100 | Rest-into-object `[...{props}]` (48), computed key eval in destructuring (24), misc |
| dynamic-import | ~335 | No module support |
| async-generator | ~240 | yield* delegation, edge cases |
| regexp | ~388 | Literal validation, named groups, misc |
| expressions/object | ~154 | Edge cases |
| Other | ~2,551 | Spread across many categories |

## Pending Work

### JS Engine — Active Priorities (2026-05-10)

**Current: 45,540/49,998 (91.8%) full. Next target: 93%+.**

Ordered fix list (high ROI first, modules last):
1. ~~**Fix getter key stability**~~ (~892 tests) — **DONE 2026-05-10.** DEF_GETTER/DEF_SETTER stored `__get_`/`__set_` keys in shared transient `JSVMCallBuf.getter_buf`. PropTable pointer-equality fast path matched wrong getter when buffer was overwritten by nested GET_PROP, causing infinite recursion on any `this.<prop>` access inside getter bodies. Fix: copy key to `str_slab` via `JSRT__StrSlabAlloc` + `MemoryCopy`. All 4 opcodes fixed (64, 65, 76, 77). **Files**: JSVMDispatch.ailang cases 64/65/76/77.
2. **Static semantic checks for class elements** (~300 tests) — ContainsArguments, ContainsSuperCall in field initializers (116), AllPrivateNamesValid (76), HasDirectSuper (40), `#` whitespace/escape validation (62), field-named-constructor (8), yield-as-identifier (16), ASI (4). Implementation in JSValidate library.
3. **Rest-into-object + computed key eval in destructuring** (~110 tests) — `[...{props}]` in CompileArrayPattern, computed property eval in CompileObjPattern.
4. **AllPrivateNamesValid** (~56 tests) — Early error for `#name` used outside class that declares it.
5. **Async generator fixes** (~281 tests) — yield* delegation, edge cases.
6. **RegExp literal validation** (~174 tests) — Named groups, character class ranges, misc.
7. **Module support** (last) — dynamic-import (~335 tests).

Progress log:
- 2026-05-02: Baseline 11,861 (49.6%)
- 2026-05-03: +1,969 (class, for-of, destructuring) → 12,550
- 2026-05-04: +5,209 (class+OOP, optional chaining, template validation) → 17,759 peak
- 2026-05-06: arguments object, CountVars fix for nested scopes, benchmarks vs V8, IEEE 754 float fixes
- 2026-05-07: Private class members (name mangling), instance fields as own properties (__field_init__ closure), fixed JSVM__CallFunc frame corruption in RETURN handler
- 2026-05-08: Zero-alloc hot path complete — str_slab, func_slab, gen_slab, PropTable ring buffer, static backup buffers, const_val_pool cache. XSHash fully replaced by PropTable/GlobalHash. SunSpider 26/26, Kraken 14/14, Octane 15/15 all passing.
- 2026-05-09: Conservative ScanString validation (PeekAt-only `\u`/`\x` validation, line terminator rejection, unterminated string detection — +1,614 tests). Getter `this` binding fix (`JSVM__SetGlobal("this", obj)` in GET_PROP inline getter). GET_GLOBAL experiment reverted (caused 24k regression — GlobalHash stores JSValue pointers that go stale in ring buffer). Full: 43,034→44,648 (+1,614). Commit 1caa865.
- 2026-05-10: Getter key stability fix — DEF_GETTER/DEF_SETTER `__get_`/`__set_` keys copied from transient getter_buf to stable str_slab. Root cause: PropTable pointer-equality matched wrong getter via shared buffer address, causing infinite recursion on `this.<prop>` in getter bodies. +892 tests. Full: 44,648→45,540 (91.8%).

### Other Pending

- **Ladybird live testing** — performance tuning, tab management
- **Terminal polish** — cursor blink, mouse reporting
- **Audio engine split** — extract from display server
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
