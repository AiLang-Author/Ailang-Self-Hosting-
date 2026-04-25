# Project Memory

## Architecture Notes

- **AKContext system:** Explicit `LinkagePool.AKContext` handles. Each context (main window, toolbar, deskbar, menu, dialog) owns its own node buffer, extra table, and event state. `AK_CreateContext()` allocates, all AK_* functions take `ctx` as first param.
- Toolbar actions fire on UP (not DOWN). Action string -> EventRouter queue -> `EventRouter_Drain` in main loop dispatches.
- `Menu_Show` creates its own AKContext, builds tree, renders to surface, destroys context. Surface stored in MenuState. `Menu_Blit` called from `Win_BlitAll`.
- Main loop: Evdev_Poll -> DrainInput -> Win_RenderDirty -> EventRouter_Drain -> IPCBroker_Poll -> Deskbar_Refresh -> DebugLog_Render -> Win_BlitAll -> sleep(16ms).
- Deskbar has its own AKContext stored in `DeskbarState.ak_ctx`. No global swap needed.
- Each window toolbar has its own AKContext stored via `WinMgr_SetToolbarCtx(idx, ctx)`.
- **IPC Broker** (`Library.IPCBroker.ailang`): Embedded in display server. Unix socket at `/tmp/ailang_display.sock`. Non-blocking `poll(0)` once per frame. 8-client max. Protocol: 4-byte BE length prefix + JSON. Methods: `register`, `window.create`, `window.update` (app→server); `window.created`, `window.closed`, `input.action` (server→app).
- **Start Menu** (`Library.StartMenu.ailang`): Windows XP/7-style popup panel above deskbar. Own AKContext, own surface, positioned overlay. "Home" button in deskbar (action `app.home`). Lists services from PostgreSQL cache + system items (About, Screenshot, Quit). Blitted in `Win_BlitAll` after deskbar, before dropdown menus.
- **EventRouter action routing**: System actions (`win.`, `app.`, `menu:`, `sys.`, `fd.` prefixes) always handled locally by the display server. Non-system actions from IPC-owned windows forwarded to app process via `IPCBroker_RouteAction`. This ensures toolbar buttons (Close, About) work on IPC app windows while app-specific buttons (calculator digits, operators) route to the app.
- **Init sequence**: `SysDisplay_Init → EventRouter_Init → Dialog_Init → Menu_Init → Deskbar_Init → IPCBroker_Init → StartMenu_Init → HTML_Init → PageSurface_Init → Doc_Init`

### Compiler Constraints

- **6-arg limit**: SysV AMD64's 6 register args (RDI, RSI, RDX, RCX, R8, R9) with no spill. `analyzer.x` arity checker enforces this.
- **StoreValue**: Defaults to 8-byte (qword) writes. Use `StoreValue(addr, val, "dword")` for 4-byte writes.
- **MemoryCopy/MemorySet**: Emit `CLD` + `REP MOVSB/STOSB` with register save/restore.

### DebugLog_Push Instrumentation

**Scope:** 475 `DebugLog_Push` calls across 16 library files.
**Config:** `DebugLogConst.MAX_ENTRIES` = 256. Toggle with `DebugLog_Toggle()`.
**Tag convention:** `"<module>.<fn>"`, max 9 chars. Second arg = string length.

### Headless Testing

`FB_InitHeadless(w, h)` allocates anonymous mmap buffer instead of `/dev/fb0`. Test binaries override `RenderFB_InitDouble` to call `FB_InitHeadless(1920, 1080)`. Real framebuffer is the default path — no comment-swapping needed.

### HTML Toolbar System

The `<window>` tag supports a `toolbar=` attribute parsed by `Library.AucklandBind.ailang`:
- `toolbar="none"` — no toolbar (TBMode.NONE=0)
- `toolbar="about"` — [About] [spacer] [title] [X] (TBMode.ABOUT=1, default)
- `toolbar="file"` — [File] [About] [spacer] [title] [X] (TBMode.FILE=2)
- `toolbar="full"` — [File] [Edit] [View] [About] [spacer] [title] [X] (TBMode.FULL=3)

`Win_BuildAppToolbar(ctx, mode, app_title)` in `Library.WinToolbar.ailang` builds the tree. `Win_CreateToolbarApp(idx, mode, app_title)` creates surface/context/stores refs. `AppHost_Open` reads `AK_GetToolbarMode(ak_ctx)` from parsed HTML.

### Calculator Expression Buffer

Calculator maintains `expr_buf` (64 bytes) + `expr_len` in `CalcState`. Digits append to buffer, operators append symbol, `=` replaces with result, `C` resets to "0". `Calc_JsonHandle` returns expression string (not just value) in `window.update`. Leading zero handled: if expression is "0", first digit replaces instead of appending.

## Completed Work (Condensed)

| Date | Fix | Key Detail |
|------|-----|-----------|
| 04-22 | AKContext refactor | Global state -> explicit context handles |
| 04-22 | Framebuffer bounds checking | 4-edge clamping in Win_BlitOne/BlitClamped/DrawBorderFB |
| 04-23 | Canvas resize fixes | Background color sampling, content preservation, toolbar re-render |
| 04-23 | TextRegion pool fix | Free stack recycling, pool 32->256 slots |
| 04-23 | UIScale DPI system | `config/ui.cfg` key=value parser, DPI-aware dimensions |
| 04-23 | UI theming system | 42 colors in FixedPool.Theme, loaded from config/ui.cfg |
| 04-23 | CLD fix for REP MOVSB/STOSB | Added CLD before REP instructions |
| 04-23 | Screenshot PPM/BMP support | `/tmp/screenshot.ppm` (P6) + `/tmp/screenshot.bmp` (24-bit) |
| 04-24 | Stack leak fix >6-arg calls | ADD RSP cleanup after MOV RSP,R12 |
| 04-24 | VFont_UseSize caching | Instance caching instead of flush+raster |
| 04-24 | TVG rasterizer hardening | Function split (33+ vars), bounds checks |
| 04-24 | Draw_Pix_FillRect overflow fix | StoreValue qword->dword |
| 04-24 | Text clipping on resize | `AK_FreeContextTR(ak_ctx)` before `Win_RedrawToolbar` |
| 04-24 | Debug overlay rewrite | Own surface, blitted after windows, TR freed on toggle-off |
| 04-24 | MemoryCopy/MemorySet rollout | 20 sites across all blit/fill/init paths — all done |
| 04-24 | Doc content redraw on resize | PageSurface_Resize + App_RefreshDocWindow |
| 04-25 | IPC Broker | Embedded broker, Unix socket, poll(0), client table, JSON dispatch |
| 04-25 | Start Menu | Windows XP/7 popup, Home button, services from PostgreSQL |
| 04-25 | Calculator IPC app | Standalone binary, expression buffer, 10/10 tests |
| 04-25 | HTML toolbar system | `toolbar="about\|file\|full\|none"` attribute, Win_BuildAppToolbar |
| 04-25 | FB_InitHeadless | Test binaries override RenderFB_InitDouble, no comment-swapping |
| 04-25 | EventRouter system action routing | `win.`/`app.`/`menu:`/`sys.`/`fd.` prefixes handled locally, not forwarded to IPC apps |
| 04-25 | Toolbar button width fix | `toolbar_btn_w` 48→60 in ui.cfg, "About" no longer truncated |
| 04-25 | About dialog | `Library.AboutDialog.ailang` — system info, copyright, close button |
| 04-25 | APP_DEVELOPMENT.md | Full app development guide with toolbar, expression buffer, headless testing |

## IPC Pipeline Architecture

Full plan at: `.claude/plans/playful-cuddling-puffin.md`

### Files

| File | Purpose |
|------|---------|
| `Librarys/Library.IPCBroker.ailang` | Embedded IPC broker — socket, poll, client table, message dispatch |
| `Librarys/Library.StartMenu.ailang` | Start Menu panel — Windows XP/7 style overlay |
| `Librarys/Library.AboutDialog.ailang` | About dialog — system info, copyright, license |
| `Librarys/Library.Socket.ailang` | Added `Socket.SetNonBlock(fd)` |
| `Testcode/calc_ipc.ailang` | Standalone IPC calculator client |
| `config/calculator.html` | Calculator layout with `toolbar="about"` |
| `APP_DEVELOPMENT.md` | Application development guide |

### PostgreSQL Services Table

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

Seeded services: notepad (`internal:win.new`), files (`internal:app.files`), calculator (`./calc_ipc.x`).

Related tables: `files` (VFS), `settings` (key-value per app), `users` (accounts), `windows` (state persistence), `encryption_keys` (per-service keys), `service_status` (runtime state — not yet populated).

## Current State (2026-04-25)

### What's Working

- Full display server pipeline: init, rendering, input, window management, compositing
- IPC Broker: embedded Unix socket server, non-blocking poll, client routing, JSON protocol
- Start Menu: popup panel, Home button, PostgreSQL service list, system items
- Calculator: standalone IPC app, expression buffer display, 10/10 tests
- HTML toolbar system: `toolbar="about|file|full|none"`, per-app toolbar presets
- About dialog: system info, copyright, close button
- System action routing: toolbar Close/About work on IPC app windows
- FB_InitHeadless: test binaries opt into headless mode, real FB is default
- 34-step headless stress test: resize + debug + start menu + IPC + calc
- 0 analyzer errors, 10/10 calc tests, 34/34 headless tests

### Build & Run

```
./ailang.x Main.ailang SysDisplay.x    # build display server
./ailang.x Testcode/calc_ipc.ailang calc_ipc.x  # build calculator
./ailang.x Calc.ailang Calc.x          # build calc standalone tests
./ailang.x TestCode/test_main.ailang test_main.x  # build headless tests
./SysDisplay.x                         # run on TTY (Ctrl+Alt+F2)
./Calc.x                               # run calc unit tests
./test_main.x                          # run headless integration tests
```

### Test Programs

- `test_main.ailang` — 34-step headless test (resize, debug, start menu, IPC, calc)
- `calc_ipc.ailang` — standalone IPC calculator client
- `Calc.ailang` — standalone calculator unit tests (10/10)
- `test_offscreen_render.ailang` — 4 render tests (toolbar, menu, deskbar, file dialog)

### Pending Work

- **Scientific calculator** — trig, log, parentheses, full algebra expressions
- **Canvas buffer stream** — mechanism for video output / rich content
- **Keyboard event capture** — Plan A: display server maps number/operator keys to button actions
- **App installer CLI** — tool for registering apps in PostgreSQL (future: checksums, malware check, permissions)
- **Start Menu UI** — Windows XP/7 side navigation, categories, running-app indicators
- **Encryption at rest** — login gates master key, per-service keys from `encryption_keys` table
- **Service status tracking** — populate `service_status` table, child process reaping (waitpid WNOHANG)
- **SSE2 optimization** — Phase 1 remaining: FB_ClearBuffer. Phases 2-3: compiler integer SSE2 emit + intrinsics
