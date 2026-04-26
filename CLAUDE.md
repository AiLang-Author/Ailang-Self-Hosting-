# Project Memory

## Architecture Notes

- **AKContext system:** Explicit `LinkagePool.AKContext` handles. Each context (main window, toolbar, deskbar, menu, dialog) owns its own node buffer, extra table, and event state. `AK_CreateContext()` allocates, all AK_* functions take `ctx` as first param.
- Toolbar actions fire on UP (not DOWN). Action string -> EventRouter queue -> `EventRouter_Drain` in main loop dispatches.
- `Menu_Show` creates its own AKContext, builds tree, renders to surface, destroys context. Surface stored in MenuState. `Menu_Blit` called from `Win_BlitAll`.
- Main loop: Evdev_Poll -> DrainInput -> Win_RenderDirty -> EventRouter_Drain -> IPCBroker_Poll -> Deskbar_Refresh -> DebugLog_Render -> Win_BlitAll -> sleep(16ms).
- Deskbar has its own AKContext stored in `DeskbarState.ak_ctx`. No global swap needed.
- Each window toolbar has its own AKContext stored via `WinMgr_SetToolbarCtx(idx, ctx)`.
- **IPC Broker** (`Library.IPCBroker.ailang`): Embedded in display server. Unix socket at `/tmp/ailang_display.sock`. Non-blocking `poll(0)` once per frame. 8-client max. Protocol: 4-byte BE length prefix + JSON. Methods: `register`, `window.create`, `window.update` (app→server); `window.created`, `window.closed`, `input.action`, `input.key`, `input.mouse` (server→app).
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
| 04-25 | input.key IPC message | Display server forwards keyboard events to IPC app windows via `IPCBroker_SendKey` |
| 04-25 | Grep IPC app | Hardware keyboard capture, regex+fixed search, file buttons, result streaming |
| 04-25 | KeyMap library | Scancode-to-character mapping tables for keyboard input |
| 04-25 | TextBuffer library | Multi-line text buffer with cursor, insert, delete, Enter/line-split |
| 04-25 | File dialog | Full file browser with directory traversal, file type filtering |
| 04-25 | Shared memory canvas | Zero-copy pixel streaming: app mmaps `/dev/shm`, server blits from same mapping |
| 04-25 | Canvas demo | Animated BGRA gradient proves shm pipeline end-to-end |
| 04-25 | Video player adapter | fork/exec ffmpeg, pipe() + dup2() stdout capture, raw BGRA → shm canvas, SIGSTOP/SIGCONT |
| 04-26 | Audio engine volume fix | Max gain 256→1024 (4x), ffmpeg `-af volume=2.0` pre-boost, fixed 27x gain stacking |
| 04-26 | Second-replay audio fix | `Audio_Drop` leaves ALSA in SETUP state — added `Audio_Prepare` + ring buffer reset |
| 04-26 | Audio-driven frame sync | `Mixer_GetSamplesWritten` audio clock, video presents only when `audio_pos/1600 >= frames_presented`, frame drop/hold |
| 04-26 | Terminal emulator | PTY + VT100 parser + 8x16 bitmap font + ShmCanvas + dynamic resize, `ls` and `claude` confirmed working |
| 04-26 | TermFont library | Embedded VGA ROM 8x16 font (95 glyphs, 1520 bytes), unrolled bit-test rendering |
| 04-26 | IPCBroker ctrl key | `IPCBroker_SendKey` extended to 6 args, `KeyMod.ctrl` forwarded to IPC apps |
| 04-26 | Terminal dynamic resize | `window.resized` → recalc grid, realloc buffers, recreate canvas, TIOCSWINSZ ioctl |
| 04-26 | Terminal scrollback + scrollbar | Ring buffer (1000 lines), Shift+PageUp/Down, proportional thumb scrollbar |
| 04-26 | Truecolor SGR | 256-color + 24-bit RGB: fg/bg arrays widened to BGRA dwords, ESC[38;5;Nm, ESC[38;2;R;G;Bm |
| 04-26 | DEC private modes | ?1049 alt screen buffer, ?25 cursor visibility, ?7 autowrap, ?1 app cursor keys |
| 04-26 | CSI insert/delete/scroll | CSI P/@/X (delete/insert/erase chars), CSI r (scroll regions), CSI S/T (scroll up/down) |
| 04-26 | UTF-8 terminal support | Multi-byte decoder in parser, grid widened from 1-byte to 4-byte codepoints |
| 04-26 | TermFont box-drawing | 42 extended glyphs: single/double box-drawing, rounded corners, block elements, symbols |
| 04-26 | TermFont glyph fallback | Dotted rectangle placeholder for unknown Unicode codepoints |
| 04-26 | Terminal rendering fix | `Term_RenderRow`/`Term_RenderRow_At` chars offset was cell-based not byte-based (÷4 wrong), caused garbled text on rows >0 |
| 04-26 | Canvas resize snap | `Term_HandleResize` snaps canvas to cell grid (cols×8, rows×16) to prevent glyph overflow |
| 04-26 | UTF-8 invalid byte fix | Invalid continuation byte now reprocessed in NORMAL state instead of silently dropped |
| 04-26 | ScrollRegionDown overlap fix | Replaced forward MemoryCopy with bottom-up row-by-row copy to prevent overlap corruption |
| 04-26 | OSC ESC\\ terminator fix | ESC in OSC state transitions to ESC state so ST (ESC \\) terminates OSC correctly |
| 04-26 | Terminal test expansion | 125-step headless test: 20 terminal steps + 31 Chrome steps (canvas, actions, keys, ctrl, resize, burst, mouse fwd, detach) |
| 04-26 | Claude Code IPC app | Dedicated CLI wrapper — fork of terminal_ipc, execs claude 2.1.14, 800x600 window, xterm-256color, update blockers |
| 04-26 | Chrome IPC app | Sandboxed browser: Xvfb :99 + google-chrome + ffmpeg x11grab → ShmCanvas, xdotool input forwarding, 15fps, 3-process management |
| 04-26 | IPC mouse forwarding | `IPCBroker_SendMouse` — VM-style mouse capture for IPC canvas windows, cursor auto-hide, xdotool mousemove/mousedown/mouseup |
| 04-26 | MOUSE_CAPTURE flag | Per-window flag in CanvasFields — only sandboxed apps (Chrome) capture mouse, not terminal/videoplayer. `ShmCanvas_AttachCapture()` sets `capture_mouse:1` in attach JSON |
| 04-26 | Mouse move coalescing | Deferred mouse moves — stores pending position, `Chrome_FlushMouse()` sends one xdotool per tick instead of fork/exec per event |
| 04-26 | Chrome session isolation | `--user-data-dir=/tmp/chrome_ailang_profile` — Chrome was joining existing session instead of starting in Xvfb, rendering nothing |
| 04-26 | Chrome ffmpeg draw_mouse | Added `-draw_mouse 1` to ffmpeg x11grab args — Xvfb cursor now captured in frame output |
| 04-26 | xdotool DISPLAY env fix | `--display` flag doesn't work for xdotool key/type/mousemove — must pass `DISPLAY=:99` in envp. Was passing empty envp + invalid `--display` arg, so all input went to null display |

## Chrome Browser (Sandboxed)

Runs Chrome inside a virtual X display (Xvfb), never touches the real framebuffer. ffmpeg captures the virtual display as raw BGRA pixels — same pipeline as the video player. xdotool forwards keyboard input.

**3-process stack:** Xvfb :99 (virtual X) → google-chrome --display=:99 (isolated browser) → ffmpeg -f x11grab (screen capture). Started in order, killed in reverse.

**Security:** Chrome runs in its own X session with `--user-data-dir=/tmp/chrome_ailang_profile` (forces independent instance, won't join existing Chrome sessions). No GPU (--disable-gpu), no extensions, no sync, no first-run wizard, muted audio. Software rendering only.

**Frame rate:** 30fps capture, 5ms main loop tick. `-draw_mouse 1` ensures Xvfb cursor appears in captured frames.

**Keyboard:** xdotool fork/exec per keystroke (~2-5ms). Printable chars via `xdotool type`, special keys via `xdotool key`. Ctrl combos (Ctrl+L=URL bar, Ctrl+T=new tab, Ctrl+W=close tab, Ctrl+R=reload). Toolbar: Back (alt+Left), Forward (alt+Right), Reload (F5).

**Mouse:** VM-style capture via `MOUSE_CAPTURE` flag (set via `ShmCanvas_AttachCapture`). Only sandboxed apps request capture — regular canvas apps (terminal, videoplayer) don't. When mouse is over a captured canvas, all events forwarded to app, display server cursor auto-hidden. Mouse leaves → cursor reappears. Mouse moves coalesced: `Chrome_FlushMouse()` sends one `xdotool mousemove` per tick (not per event). Button mapping: IPC 0→X11 1 (left), IPC 1→X11 3 (right), IPC 2→X11 2 (middle).

**Resize:** Kills all 3 processes, destroys/recreates ShmCanvas at new size, relaunches all 3 at new resolution.

**Prerequisites:** `sudo apt install xvfb xdotool google-chrome-stable`

## Audio Engine & A/V Sync

Direct ALSA kernel interface — no PulseAudio, no PipeWire, just syscalls to `/dev/snd/pcmC0D0p`. PipeWire/Pulse disabled: `systemctl --user disable --now pipewire.socket pipewire-pulse.socket`.

**Format:** S16LE, 48kHz, stereo. Period 1024-4096 frames, buffer 8192-65536 frames.

**3-bus mixer:** App bus (video/media), System bus (UI sounds), Master volume. Ring buffers (65536 bytes each). Mix formula: `out = clamp16((app_s * app_vol + sys_s * sys_vol) / 256 * master_vol / 256)`. Volume range 0-1024 (256 = unity, 1024 = 4x gain).

**Gain chain:** ffmpeg `-af volume=2.0` (float precision pre-boost) → app_vol 256 (unity) → master_vol 256 (unity, user-adjustable via Up/Down keys). Total default: 2x. Max possible: 2 × 4 × 4 = 32x.

**Audio-driven frame sync:** ALSA hardware crystal = master clock. `Mixer_DrainTick` increments `samples_written` per period pushed to hardware. Video player calculates `expected_frame = audio_pos / 1600` (= samples / (48000/30fps)). Present when `expected >= presented`, drop frames if behind by >2, hold if ahead.

**Replay fix:** `Audio_Drop()` → ALSA SETUP state. Must call `Audio_Prepare()` + reset ring buffer positions + clear `mix_pending` + `Mixer_ResetClock()` before next playback.

**Key bindings (video player):** Space=play/pause, S=stop, Up/Down=volume ±64 (range 0-1024), M=mute/unmute.

## Shared Memory Canvas System

Zero-copy pixel streaming for IPC apps. Both processes mmap the same `/dev/shm/ailang_canvas_<win_id>` file with `MAP_SHARED`. App writes BGRA pixels directly, display server blits from the shared mapping. JSON socket carries control messages only, never pixel data.

**IPC messages:** `canvas.attach` (win_id, shm_path, w, h), `canvas.present` (win_id), `canvas.detach` (win_id)

**Server side** (`Library.IPCBroker.ailang`): `canvas.attach` handler opens shm file, mmaps it, creates surface header pointing to shared memory. `Win_BlitAll` checks `Canvas_GetActive(i)` and substitutes the canvas surface.

**App side** (`Library.ShmCanvas.ailang`): `ShmCanvas_Create(win_id, w, h)` creates shm file, ftruncate, mmap. `ShmCanvas_Present(sock, win_id)` sends JSON. Pixel helpers: `ShmCanvas_SetPixel`, `ShmCanvas_Clear`, `ShmCanvas_FillRect`.

**Canvas state** (`Library.WinManager.ailang`): Per-window `CanvasState` table (8 entries × 40 bytes): ACTIVE, SHM_PTR, SHM_SIZE, SURF, MOUSE_CAPTURE fields. MOUSE_CAPTURE distinguishes sandboxed apps (Chrome) from regular canvas apps (terminal, videoplayer).

**Video player pattern:** fork/exec ffmpeg with `-f rawvideo -pix_fmt bgra -s 640x480 pipe:1`, capture stdout via pipe()+dup2(), read frames directly into shm buffer, present each frame. SIGSTOP/SIGCONT for pause/resume.

## Terminal Emulator

Standalone IPC app (`terminal_ipc.ailang`, ~191KB binary). Follows videoplayer architecture: IPC socket + ShmCanvas + 5ms tick loop.

**PTY setup:** Open `/dev/ptmx`, ioctl `TIOCSPTLCK` (unlock), ioctl `TIOCGPTN` (get slave number), build `/dev/pts/N` path. Fork: child does `setsid` + open slave + `TIOCSCTTY` + `dup2(0/1/2)` + `execve /bin/bash -i` with envp (`TERM=xterm`, `HOME`, `PATH`, `LANG`). Parent: close slave, set master non-blocking via `fcntl`.

**VT100 parser:** State machine (NORMAL/ESC/CSI/OSC). Handles: printable chars, LF, CR, BS, TAB, BEL. CSI commands: cursor move (A/B/C/D/H/G/d), erase display (J), erase line (K), SGR colors (m), save/restore cursor (s/u), insert/delete lines (L/M), cursor horizontal absolute (G).

**SGR colors:** 16-color ANSI palette (standard 8 + bright 8) in BGRA dwords. Attributes: bold (maps low→bright fg), reverse video. Codes: 0=reset, 1=bold, 7=reverse, 30-37/90-97=fg, 40-47/100-107=bg, 39/49=default.

**Font:** `Library.TermFont.ailang` — embedded VGA ROM 8x16 bitmap font (public domain). 95 glyphs (ASCII 32-126), 1520 bytes. Unrolled 8-pixel-per-row bit-test rendering via `TermFont_DrawCharFgBg(buf, stride, x, y, ch)`.

**Grid:** `TermGrid.chars` (4 bytes/cell, dword codepoints), `TermGrid.fg_arr` (4 bytes/cell, BGRA dword), `TermGrid.bg_arr` (4 bytes/cell, BGRA dword). Default 80x24 = 1920 cells. Dynamic on resize.

**Keyboard:** Arrow keys → ESC sequences, Backspace→0x7F, Enter→0x0D, Tab→0x09, Escape→0x1B. Ctrl+key → `ch & 0x1F` (Ctrl+C=0x03, Ctrl+D=0x04). Regular printable chars written directly to PTY master.

**Dynamic resize:** Handles `window.resized` IPC message. Recalculates COLS/ROWS from pixel dimensions (snapped to 8x16 cell grid). Allocates new grid buffers, copies old content row-by-row. Destroys+recreates ShmCanvas. Sends `TIOCSWINSZ` ioctl so bash/programs get `SIGWINCH`.

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
| `Librarys/Library.ShmCanvas.ailang` | App-side shared memory canvas — create/attach/present/destroy shm pixel buffers |
| `Librarys/Library.KeyMap.ailang` | Keycode-to-character mapping for keyboard input |
| `Librarys/Library.TextBuffer.ailang` | Multi-line text buffer with cursor, insert, delete, line split |
| `Testcode/grep_ipc.ailang` | Grep IPC client — pattern search with keyboard capture |
| `Testcode/canvas_demo.ailang` | Animated gradient demo — proves shm canvas pipeline |
| `Testcode/videoplayer.ailang` | Video player — fork/exec ffmpeg, pipe raw BGRA frames to shm canvas |
| `config/grep.html` | Grep window layout — textfield, file buttons, checkboxes, results panel |
| `config/canvas_demo.html` | Canvas demo window — black panel for pixel streaming |
| `config/videoplayer.html` | Video player window — canvas + transport controls (play/pause/stop/open) |
| `Librarys/Library.TermFont.ailang` | Embedded 8x16 VGA bitmap font for terminal rendering (95 glyphs, ASCII 32-126) |
| `Testcode/terminal_ipc.ailang` | Terminal emulator — PTY + VT100 parser + ShmCanvas + dynamic resize |
| `config/terminal.html` | Terminal window layout — black panel with file toolbar |
| `Testcode/claude_ipc.ailang` | Claude Code app — fork of terminal, execs claude CLI via PTY, 800x600 100x37 grid |
| `config/claude.html` | Claude Code window layout — dark panel with about toolbar |
| `Testcode/chrome_ipc.ailang` | Chrome browser — Xvfb + google-chrome + ffmpeg x11grab, ShmCanvas, xdotool input |
| `config/chrome.html` | Chrome window layout — nav buttons, URL bar, canvas panel |

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

Seeded services: notepad (`internal:win.new`), files (`internal:app.files`), calculator (`./calc_ipc.x`), grep (`./grep_ipc.x`), canvas_demo (`./canvas_demo.x`), videoplayer (`./videoplayer.x`), terminal (`./terminal_ipc.x`), claude (`./claude_ipc.x`), chrome (`./chrome_ipc.x`).

Related tables: `files` (VFS), `settings` (key-value per app), `users` (accounts), `windows` (state persistence), `encryption_keys` (per-service keys), `service_status` (runtime state — not yet populated).

## Current State (2026-04-26)

### What's Working

- Full display server pipeline: init, rendering, input, window management, compositing
- IPC Broker: embedded Unix socket server, non-blocking poll, client routing, JSON protocol
- IPC `input.key` messages: display server forwards keyboard events to IPC app windows
- Start Menu: popup panel, Home button, PostgreSQL service list, system items
- Calculator: standalone IPC app, expression buffer display, 10/10 tests
- Grep IPC app: hardware keyboard capture, regex/fixed search, file selection, results streaming
- Shared memory canvas: zero-copy pixel streaming via `/dev/shm`, app writes BGRA, server blits
- Canvas demo: animated gradient proves shm pipeline end-to-end
- Video player: fork/exec ffmpeg, dual-pipe (video+audio), shm canvas, SIGSTOP/SIGCONT pause
- Audio engine: direct ALSA kernel interface (`/dev/snd/pcmC0D0p`), 3-bus mixer, S16LE 48kHz stereo
- Audio-driven frame sync: `samples_written` audio clock, video holds/drops frames to match audio position
- Volume control: 0-1024 range (256=unity, 1024=4x), ffmpeg `-af volume=2.0` pre-boost, Up/Down/M keys
- HTML toolbar system: `toolbar="about|file|full|none"`, per-app toolbar presets
- About dialog: system info, copyright, close button
- File dialog: full file browser with directory traversal
- TextBuffer: multi-line text editing with cursor management
- KeyMap: scancode-to-character translation tables
- System action routing: toolbar Close/About work on IPC app windows
- FB_InitHeadless: test binaries opt into headless mode, real FB is default
- Terminal emulator: PTY fork/exec bash, VT100 escape parser, 8x16 bitmap font, ShmCanvas rendering, dynamic resize
- Terminal truecolor: 256-color + 24-bit RGB (ESC[38;5;N, ESC[38;2;R;G;B), BGRA dword grid
- Terminal DEC modes: alt screen (?1049), cursor visibility (?25), autowrap (?7), app cursor keys (?1)
- Terminal CSI: insert/delete/erase chars (P/@/X), scroll regions (r), scroll up/down (S/T)
- Terminal UTF-8: multi-byte decoder, 4-byte codepoint grid, box-drawing/block/symbol glyphs (42 extended)
- Terminal scrollback: 1000-line ring buffer, Shift+PageUp/Down, proportional thumb scrollbar
- IPC `input.key` ctrl field: `IPCBroker_SendKey` extended to 6 args (job, win, keycode, ch, shift, ctrl)
- IPC `input.mouse` forwarding: `IPCBroker_SendMouse` (6 args: job, win, x, y, event, button), VM-style canvas capture, cursor auto-hide
- 125-step headless stress test: resize + debug + start menu + IPC + calc + about + filedialog + notepad + keyboard + canvas + terminal + chrome + mouse
- 0 analyzer errors, 10/10 calc tests, all headless tests pass
- Claude Code IPC app: dedicated CLI wrapper, fork of terminal emulator, execs claude 2.1.14 via PTY, 800x600 100x37 grid, xterm-256color
- Chrome browser: sandboxed via Xvfb + ffmpeg x11grab, 3-process management, xdotool keyboard+mouse forwarding, 30fps capture, toolbar nav, `--user-data-dir` session isolation, `-draw_mouse 1`, mouse move coalescing
- SysDisplay.x binary: ~665KB, terminal_ipc.x: ~232KB, claude_ipc.x: ~232KB

### Build & Run

```
./ailang.x Main.ailang SysDisplay.x                    # build display server
./ailang.x Testcode/calc_ipc.ailang calc_ipc.x         # build calculator
./ailang.x Testcode/grep_ipc.ailang grep_ipc.x         # build grep
./ailang.x Testcode/canvas_demo.ailang canvas_demo.x   # build canvas demo
./ailang.x Testcode/videoplayer.ailang videoplayer.x   # build video player
./ailang.x Testcode/terminal_ipc.ailang terminal_ipc.x # build terminal emulator
./ailang.x Testcode/claude_ipc.ailang claude_ipc.x     # build claude code app
./ailang.x Testcode/chrome_ipc.ailang chrome_ipc.x     # build chrome browser
./ailang.x Calc.ailang Calc.x                          # build calc standalone tests
./ailang.x TestCode/test_main.ailang test_main.x       # build headless tests
./SysDisplay.x                                          # run on TTY (Ctrl+Alt+F2)
./Calc.x                                                # run calc unit tests
./test_main.x                                           # run headless integration tests
```

### Test Programs

- `test_main.ailang` — 125-step headless test (resize, debug, start menu, IPC, calc, about, filedialog, notepad, keyboard, canvas, terminal, chrome: canvas/actions/keys/ctrl/resize/burst/mouse-fwd/detach)
- `calc_ipc.ailang` — standalone IPC calculator client
- `grep_ipc.ailang` — grep IPC client with keyboard capture and regex search
- `canvas_demo.ailang` — animated gradient via shm canvas pipeline
- `videoplayer.ailang` — ffmpeg video player via fork/exec + pipe + shm canvas
- `terminal_ipc.ailang` — terminal emulator via PTY + VT100 parser + 8x16 bitmap font + ShmCanvas
- `claude_ipc.ailang` — Claude Code CLI wrapper via PTY + VT100 + ShmCanvas (100x37 grid, xterm-256color)
- `chrome_ipc.ailang` — Sandboxed Chrome browser via Xvfb + ffmpeg x11grab + ShmCanvas + xdotool input
- `Calc.ailang` — standalone calculator unit tests (10/10)
- `test_offscreen_render.ailang` — 4 render tests (toolbar, menu, deskbar, file dialog)
- `test_filedialog.ailang` — file dialog integration tests

### Pending Work

- **Terminal polish** — toolbar actions (File menu), cursor blink, mouse reporting (?1000h/?1006h for TUI apps)
- **Window manager scroll** — scrollable content areas for canvas/terminal windows
- **Audio fine-tuning** — test volume/clipping on TTY2 with various media files, dial in gain chain
- **Audio engine split** — extract AudioEngine from display server into standalone audio.ailang service
- **ffmpeg command pipe** — modified ffmpeg with control pipe for seek/jump (user downloading from git)
- **Video player seek** — FF/RW buttons need command pipe or restart-with-offset approach
- **Grep file dialog** — replace hardcoded file list with proper file browser dialog
- **Scientific calculator** — trig, log, parentheses, full algebra expressions
- **App installer CLI** — tool for registering apps in PostgreSQL (future: checksums, malware check, permissions)
- **Start Menu UI** — Windows XP/7 side navigation, categories, running-app indicators
- **Encryption at rest** — login gates master key, per-service keys from `encryption_keys` table
- **Service status tracking** — populate `service_status` table, child process reaping (waitpid WNOHANG)
- **SSE2 optimization** — Phase 1 remaining: FB_ClearBuffer. Phases 2-3: compiler integer SSE2 emit + intrinsics
