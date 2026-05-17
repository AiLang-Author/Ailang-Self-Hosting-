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
python3 tools/wpt_render_runner.py --suite css-grid --test grid-lanes  # Single test
python3 tools/render_test_runner.py                   # Internal regression tests
python3 tools/html5lib_runner.py                      # HTML tokenizer tests
python3 tools/test262_runner.py --full                # JS engine tests

# JS engine E2E
./ailang.x TestCode/test_js_e2e.ailang test_js_e2e.x && ./test_js_e2e.x

# Other apps
./ailang.x Applications/calc_ipc.ailang calc_ipc.x
./ailang.x Applications/terminal_ipc.ailang terminal_ipc.x
./ailang.x Applications/claude_ipc.ailang claude_ipc.x
```

## Test Results Baseline (2026-05-16)

**WPT Render: 20,133 / 24,021 (83%), 16 crashes** — 55 suites, strict 99.9% pixel threshold

Top suites (100%): css2-box, css2-colors, css2-stacking, css2-ui, css2-values, css2-zindex, render-tests
Strong (95-99%): css2-cascade, css2-fonts, css2-generated-content, css2-lists, css2-selectors, css2-text, css2-visuren, css2-backgrounds, css2-borders, css2-margin-padding-clear, css2-tables
Weakest (<50%): css-logical (21%), cssom (33%), css-inline (40%), css-conditional (43%)

**Other test suites:**
- html5lib tokenizer: 1624/1625 (99.9%)
- Test262 JS (full): 45,865/49,998 (92.5%)
- test_js_e2e: 32/32 (100%)

**WPT runner notes:**
- Use 1-2 workers (`--workers 1`) for reliable results; 8 workers causes false failures from memory pressure
- Results at `/tmp/wpt_real_results.txt`

## Architecture

### Compiler Constraints

- **6-arg limit**: SysV AMD64 register args (RDI, RSI, RDX, RCX, R8, R9) with no spill.
- **StoreValue**: Defaults to 8-byte (qword). Use `StoreValue(addr, val, "dword")` for 4-byte.
- **FixedMul/FixedDiv**: Fixed-point arithmetic. `FixedMul(a, b, bits)` = `(a * b) >> bits`. Bits: 8, 16, 32, or 64.
- **Top-level code restriction**: No executable code at top level. Use `SubRoutine.Main { ... }` + `RunTask(Main)`.
- **Local variables survive function calls**: Stored at RBP-relative. But FixedPool fields are global — recursive functions clobber each other's state. Use locals for per-call state.
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
- `HTMLLayoutGrid.ailang` — CSS Grid layout algorithm
- `HTMLLayoutUnits.ailang` — Unit conversion (px/em/rem/vw/vh/%), min()/max()/clamp()

**CSS Parser** (`Library.CSSParse.ailang`):
- Rule structure: 88 bytes (selector, combinator, specificity, properties, pseudo flag)
- Pseudo-class classification: interactive (:hover/:focus/:active) → skipped during matching
- Supports: class, ID, element, attribute, combinator (descendant, child, sibling), @media, @keyframes
- CSS custom properties (--var) with var() resolution

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
- 4-byte BE length prefix + JSON protocol

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

## Real-World Rendering Status

**Working**: browserbench.org (with external CSS loaded), simple sites
**Partially working**: W3Schools (needs redirect following), Wikipedia
**Not working**: Google (JS-dependent, display:none), DuckDuckGo (crashes on large HTML)

**Key gaps between WPT and real-world:**
- WPT uses inline `<style>`, real sites use external `<link>` stylesheets
- HTTP redirect following (301/302) — implemented but not in headless
- No JS-driven layout changes (most modern sites depend on JS to show content)
- Pseudo-class selectors (:hover/:focus/:active) now correctly skipped

## HalCode9000 — MCP Server

`Applications/HalCode9000/` — MCP server for LLM workers (DeepSeek). Terminal TUI with streaming, multi-provider support, tool dispatch over IPC.

Build: `./ailang.x Applications/HalCode9000/HalCode9000.ailang Applications/HalCode9000/HalCode9000.x`
