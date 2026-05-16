# Project Memory

## Hard Rules

- **ALWAYS use `master` branch** — never `main`. The `main` branch is a dead orphan with no common ancestor.
- **NEVER read image files** (PNG, JPG, JPEG, BMP, GIF, ICO, SVG, WebP, TIFF, TGA, TVG, etc.) with the Read tool. Causes crashes.
- **ONE browser binary**: `browser_ipc.x` — live IPC browser AND headless test harness. No other browser binaries.
- **No code changes without test baseline** — run WPT suite before and after fixes to verify improvement.

## Build & Run

```bash
# Compiler
./ailang.x <source>.ailang <output>.x

# Browser (the ONE browser)
./ailang.x Applications/browser_ipc.ailang browser_ipc.x

# Headless test mode
./browser_ipc.x --headless input.html output.ppm

# Display server
./ailang.x Main.ailang SysDisplay.x
./SysDisplay.x  # run on TTY (Ctrl+Alt+F2)

# Test runners
python3 tools/wpt_render_runner.py --all              # Full WPT (24k tests)
python3 tools/wpt_render_runner.py --suite css-color  # Single suite
python3 tools/render_test_runner.py                   # Internal regression tests
python3 tools/html5lib_runner.py                      # HTML tokenizer tests
python3 tools/test262_runner.py --full                # JS engine tests

# Headless display server tests
./ailang.x TestCode/test_main.ailang test_main.x && ./test_main.x

# JS engine E2E
./ailang.x TestCode/test_js_e2e.ailang test_js_e2e.x && ./test_js_e2e.x

# Other apps
./ailang.x Applications/calc_ipc.ailang calc_ipc.x
./ailang.x Applications/terminal_ipc.ailang terminal_ipc.x
./ailang.x Applications/claude_ipc.ailang claude_ipc.x
./ailang.x dnd_game.ailang dnd.x
```

## Test Results Baseline (2026-05-16, strict 99.9% pixel threshold)

**WPT Render: 19,970 / 24,021 good (83%), 18 crashes**

| Suite | Score | % |
|-------|-------|---|
| css2-box | 11/11 | 100 |
| css2-colors | 22/22 | 100 |
| css2-ui | 239/239 | 100 |
| css2-values | 28/28 | 100 |
| render-tests | 10/10 | 100 |
| css2-selectors | 612/615 | 99 |
| css2-cascade | 100/101 | 99 |
| css2-box-display | 108/109 | 99 |
| css2-lists | 291/293 | 99 |
| css2-generated-content | 313/316 | 99 |
| css2-borders | 750/763 | 98 |
| css2-fonts | 320/324 | 98 |
| css2-zindex | 51/52 | 98 |
| css2-visuren | 56/57 | 98 |
| css2-backgrounds | 607/625 | 97 |
| css2-margin-padding-clear | 717/739 | 97 |
| css2-tables | 1105/1139 | 97 |
| css2-text | 558/570 | 97 |
| css2-linebox | 239/249 | 95 |
| css-display | 314/341 | 92 |
| css-text | 1737/1878 | 92 |
| css-images | 460/508 | 90 |
| css2-positioning | 525/578 | 90 |
| css2-floats-clear | 222/249 | 89 |
| css-flexbox | 1111/1274 | 87 |
| css-break | 1020/1170 | 87 |
| css2-abspos | 27/31 | 87 |
| css-color | 307/365 | 84 |
| css-pseudo | 297/353 | 84 |
| css-lists | 183/218 | 83 |
| html-rendering | 363/439 | 82 |
| css-contain | 475/580 | 81 |
| css2-normal-flow | 675/850 | 79 |
| css-overflow | 586/737 | 79 |
| css-backgrounds | 642/859 | 74 |
| css-position | 263/354 | 74 |
| css2-floats | 110/147 | 74 |
| selectors | 383/511 | 74 |
| css-sizing | 540/725 | 74 |
| css-fonts | 432/589 | 73 |
| css-grid | 1370/1879 | 72 |
| css-box | 102/150 | 68 |
| cssom-view | 148/220 | 67 |
| css-animations | 152/230 | 66 |
| css-transitions | 126/189 | 66 |
| css-multicol | 461/709 | 65 |
| css-cascade | 79/136 | 58 |
| css-nesting | 25/43 | 58 |
| css-values | 239/465 | 51 |
| css-conditional | 146/318 | 45 |
| css-inline | 94/215 | 43 |
| cssom | 71/208 | 34 |
| css-logical | 20/92 | 21 |

**Other test suites:**
- html5lib tokenizer: 1624/1625 (99.9%)
- Test262 JS (full): 45,865/49,998 (92.5%)
- test_js_e2e: 32/32 (100%)

## Architecture

### Compiler Constraints

- **6-arg limit**: SysV AMD64's 6 register args (RDI, RSI, RDX, RCX, R8, R9) with no spill.
- **StoreValue**: Defaults to 8-byte (qword). Use `StoreValue(addr, val, "dword")` for 4-byte.
- **MemoryCopy/MemorySet**: `CLD` + `REP MOVSB/STOSB` with register save/restore.
- **FixedMul/FixedDiv**: Fixed-point arithmetic. `FixedMul(a, b, bits)` = `(a * b) >> bits`, `FixedDiv(a, b, bits)` = `(a << bits) / b`. Bits: 8, 16, 32, or 64.
- **Top-level code restriction**: No executable code at top level. Use `SubRoutine.Main { ... }` + `RunTask(Main)`.
- **Local variables survive function calls**: Stored at RBP-relative. But FixedPool fields are global — recursive functions clobber each other's FixedPool state. Use locals for per-call state.
- **No stack arrays**: Use FixedPool or if-chains for indexed access.

### Browser Pipeline

```
HTML source -> HTMLTokenizer -> HTMLDom -> CSSParse -> HTMLLayout -> HTMLRender -> Canvas (PPM)
```

**Layout modules** (in `Librarys/Browser/`):
- `HTMLLayout.ailang` — Core: FixedPools, init, cmd helpers, hit-test, GetDisplay
- `HTMLLayoutColors.ailang` — Color parsing (named, hex, rgb, hsl, hwb, px/em/vw/vh)
- `HTMLLayoutCSS.ailang` — Selector matching, property resolution, margin/padding/border
- `HTMLLayoutFlex.ailang` — Float state, FlexLayout, text emission/word-wrap
- `HTMLLayoutEngine.ailang` — LY__LayoutNode recursive DFS, block/inline/flex dispatch
- `HTMLLayoutTraversal.ailang` — Display detection, grid/flex/block dispatch

**Headless mode** (`browser_ipc.ailang`):
- Reads `/proc/self/cmdline` for `--headless` flag
- `./browser_ipc.x --headless input.html output.ppm`
- Always renders 1024x700 canvas
- Full pipeline: tokenize -> DOM -> CSS -> JS -> layout -> render -> PPM

### JavaScript Engine

Bytecode VM: JSLexer -> JSParser -> JSCompiler -> JSVM -> JSRuntime -> JSBridge

- 11 libraries, ~23,300 LOC
- Test262: 92.5% (45,865/49,998)
- Zero-alloc hot path (ring buffers, slabs, PropTable)
- JIT for leaf functions (x86-64 native)

### Display Server (SysDisplay.x)

- Framebuffer compositor (`/dev/fb0`)
- Auckland widget toolkit (AKContext per window/toolbar/menu)
- IPC broker (Unix socket `/tmp/ailang_display.sock`, JSON protocol)
- Evdev input, multi-window, deskbar, start menu

### IPC Protocol

4-byte BE length prefix + JSON. Methods: `register`, `window.create`, `window.update` (app->server); `window.created`, `window.closed`, `input.action`, `input.key`, `input.mouse` (server->app).

## Library Directory Structure

Import paths use dots: `LibraryImport.Browser.HTMLLayoutGrid` -> `Librarys/Browser/Library.HTMLLayoutGrid.ailang`

```
Librarys/
├── Library.{Arena,XArrays,StringUtils,JSON,HashMap,Socket,ShmCanvas,KeyMap,TextBuffer,TermFont,TUI,Math}.ailang
├── Compiler/        # Self-hosting compiler
├── Display/         # Display server (windows, input, rendering, IPC)
├── Browser/         # JS engine + HTML browser rendering
└── DnD/             # D&D RPG game engine
```

## Key Files

| Purpose | Path |
|---------|------|
| Browser app | `Applications/browser_ipc.ailang` |
| Layout engine | `Librarys/Browser/Library.HTMLLayoutEngine.ailang` |
| Layout traversal | `Librarys/Browser/Library.HTMLLayoutTraversal.ailang` |
| Layout core | `Librarys/Browser/Library.HTMLLayout.ailang` |
| CSS parser | `Librarys/Browser/Library.CSSParse.ailang` |
| HTML tokenizer | `Librarys/Browser/Library.HTMLTokenizer.ailang` |
| HTML DOM | `Librarys/Browser/Library.HTMLDom.ailang` |
| HTML renderer | `Librarys/Browser/Library.HTMLRender.ailang` |
| JS engine entry | `Librarys/Browser/Library.JSEngine.ailang` |
| WPT test runner | `tools/wpt_render_runner.py` |
| Render test runner | `tools/render_test_runner.py` |
| Display server | `Main.ailang` |

## WPT Test Runner Usage

```bash
# Full suite (all 56 suites, ~24k tests, ~35 min)
python3 tools/wpt_render_runner.py --all

# Single suite
python3 tools/wpt_render_runner.py --suite css-grid

# Focused test
python3 tools/wpt_render_runner.py --suite css-grid --test grid-lanes

# Results location
/tmp/wpt_real_results.txt  # Full run output

# Test thresholds:
#   PASS: >= 99.9% pixel match
#   PARTIAL: 90-99.9% pixel match
#   FAIL: < 50% pixel match
```

## Known Rendering Bugs (from WPT failures)

1. **CSS Grid** — `display:grid` falls back to block stacking (no grid algorithm)
2. **CSS Logical Properties** — `margin-inline`, `padding-block` etc. not implemented
3. **Container Queries** — `@container` not parsed/evaluated
4. **CSSOM** — computed style API incomplete
5. **CSS Inline** — inline-block vertical alignment issues
6. **Float wrapping** — float clearing/wrapping edge cases in css2-floats
7. **display:contents** — still renders box (borders/backgrounds) when it shouldn't
8. **Root background propagation** — body bg doesn't propagate to canvas root

## Headless Testing Pattern

`FB_InitHeadless(w, h)` allocates anonymous mmap buffer instead of `/dev/fb0`. Test binaries override `RenderFB_InitDouble` to call `FB_InitHeadless(1920, 1080)`.

## HalCode9000 — MCP Server

`Applications/HalCode9000/` — MCP server for cheap LLM workers (DeepSeek). Terminal TUI with streaming, multi-provider support, tool dispatch over IPC.

Build: `./ailang.x Applications/HalCode9000/HalCode9000.ailang Applications/HalCode9000/HalCode9000.x`
