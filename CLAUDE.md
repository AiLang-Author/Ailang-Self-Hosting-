# Project Memory

## Hard Rules

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

## Pending Work

- **Ladybird live testing** — test `ladybird_ipc.x` on live display server, performance tuning, tab management
- **Terminal polish** — toolbar actions, cursor blink, mouse reporting (?1000h/?1006h)
- **Audio engine split** — extract from display server into standalone service
- **Video player seek** — FF/RW via command pipe or restart-with-offset
- **Scientific calculator** — trig, log, parentheses
- **Start Menu UI** — side navigation, categories, running-app indicators
- **Encryption at rest** — login gates master key, per-service keys
- **SSE2 optimization** — FB_ClearBuffer, compiler integer SSE2 emit
