# 01 — System Core: SysDisplay, EventRouter, Screenshot, DebugLog, FPS

> **Copyright © 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.**

---

## 1. Overview

The System Core is the heartbeat of the AILANG Display System. It comprises four tightly coupled components that together form the main event loop, action dispatch, frame capture, and developer diagnostics. These components initialize all subsystems and drive the ~60 FPS render cycle.

### Components

| Component | Source File | Lines | Role |
|-----------|------------|-------|------|
| **SysDisplay** | `Library.SysDisplay.ailang` | ~1500 | Main loop, init, framebuffer ownership, input drain |
| **EventRouter** | `Library.EventRouter.ailang` | ~500 | Action queue, handler registry, dispatch |
| **Screenshot** | `Library.Screenshot.ailang` | ~250 | BMP/PPM framebuffer capture |
| **DebugLog** | (inline in SysDisplay) | ~200 | Ring-buffer debug overlay, FPS counter |

---

## 2. SysDisplay — The Display Server

### 2.1 Role

SysDisplay is the entry point and main loop of the entire display server. It owns the framebuffer, initializes all ~40 subsystem libraries, runs the event/render loop at ~60 FPS, and orchestrates the shutdown sequence.

### 2.2 Initialization Sequence (`SysDisplay_Init`)

```
1. SysDisplay_InitFB()         — Open /dev/fb0, mmap, double-buffer setup
2. Compose_Init(w, h)          — Initialize compositor at screen resolution
3. SysDisplay_InitFont()       — Load vector font (stub, DejaVuSans.vif via TVG)
4. SysDisplay_InitCursor()     — Initialize software cursor, load bitmap shapes
5. WinMgr_Init()               — Window manager data structures
6. SysDisplay_InitDB()         — PostgreSQL connection + schema bootstrap
7. SysDisplay_InitTTY()        — Terminal mode setup (raw input)
8. SysDisplay_InitInput()      — Evdev device discovery + open
9. VIF_Init() / VFont_Init()   — Vector icon format + vector font engine
10. TextRegion_Init()          — Text rendering subsystem
11. VIcon_Init() / VIcon_LoadVIF() — Icon widget pack loading
12. InvertScanlines_Init()     — Scanline direction for top-down rendering
13. SysDisplay_InitScale()     — UI scale factor from UIScale configuration
14. SysDisplay_InitTheme()     — Theme colors piped to UITheme subsystem
15. DebugLog_Init()            — Debug overlay ring buffer
16. Desktop surface creation   — Full-screen BGRA surface, fill with DESKTOP color
17. TextRegion title/help text — "AILANG Display Server" rendered on desktop
18. WinMgr bootstrap           — Desktop = window index 0, z_order[0]
19. DeskbarSpawn()             — Taskbar with start menu, clock, window list
```

### 2.3 Main Loop (`SysDisplay_Run`)

The main loop runs at approximately 60 FPS using `nanosleep` for frame pacing:

```
while running:
    ┌─ Frame Timing ─────────────────────────────────────┐
    │ clock_gettime(CLOCK_MONOTONIC)                     │
    │ delta_ms = (now - last) in milliseconds            │
    │ Accumulate for FPS (update every ~1 second)        │
    ├─ Input Phase ──────────────────────────────────────┤
    │ Evdev_Poll()            — Read /dev/input/event*   │
    │ SysDisplay_DrainInput() — MOUSE_MOVE/DOWN/UP/WHEEL │
    │                           KEY_UP/DOWN dispatch     │
    ├─ Render Phase ─────────────────────────────────────┤
    │ Win_RenderDirty()       — Check for dirty surfaces │
    │ EventRouter_Drain()     — Process action queue     │
    │ IPCBroker_Poll()        — Accept IPC connections   │
    │ Deskbar_Refresh()       — Rebuild if needed        │
    │ DebugLog_Render()       — Debug overlay            │
    ├─ Compose Phase ────────────────────────────────────┤
    │ Win_BlitAll()           — Compose all→framebuffer  │
    ├─ Frame Pacing ─────────────────────────────────────┤
    │ nanosleep(16.67ms)      — ~60 FPS                  │
    └────────────────────────────────────────────────────┘
```

**Key design decisions:**
- **Single-threaded, cooperative**: No locks, no thread synchronization. All subsystems get their turn each frame.
- **Dirty tracking**: `SysDisplayState.dirty` flag avoids unnecessary full-frame blits. Set to 1 when any input, action, or IPC event occurs.
- **Frame timing**: Delta time in milliseconds is tracked per frame, with a smoothed FPS counter that updates every second.
- **Double-buffered**: The framebuffer uses page flipping. Drawing goes to the back buffer; `Win_BlitAll` composes to back, then flip.

### 2.4 Global State (`SysDisplayState`)

```
SysDisplayState:
    running:      Integer   — 1 while main loop executes; set to 0 for clean exit
    dirty:        Integer   — Force next frame to recompose (0 or 1)
    frame_count:  Integer   — Monotonic frame counter (wraps at 2^31)
    frame_ms:     Integer   — Delta time for current frame in milliseconds
    last_sec:     Integer   — CLOCK_MONOTONIC seconds at frame start
    last_nsec:    Integer   — CLOCK_MONOTONIC nanoseconds at frame start
    fps:          Integer   — Smoothed frames-per-second (updated ~1/sec)
    fps_accum:    Integer   — Accumulated delta_ms for FPS calculation
    fps_frames:   Integer   — Frame count within current FPS window
    db_conn:      Integer   — PostgreSQL connection handle (0 if unavailable)
    desktop_surf: Integer   — Surface index for full-screen desktop background
```

### 2.5 Drain Input (`SysDisplay_DrainInput`)

This is the most complex function in the display server. It reads events from Ring1 (input buffer) and dispatches them through a carefully ordered hit-test chain:

**MOUSE_MOVE path:**
1. CascadeMenu overlay → if open, forward event
2. StartMenu overlay → if open, forward event
3. Menu overlay → if open, forward event; else close overlays if click outside
4. Deskbar hover detection → reveal/hide the hotzone taskbar
5. Window resize drag → if resize in progress, update geometry
6. Window drag → if drag in progress, update position
7. Content area hover → route to window's Auckland content tree

**MOUSE_DOWN path (hit-test priority):**
1. CascadeMenu → highest priority overlay
2. StartMenu → intercept clicks when open
3. Menu → dropdown menu overlay
4. Deskbar → if visible and click is in deskbar area
5. Window border → resize hit (takes priority over content)
6. Window toolbar → focus + Auckland event dispatch
7. Window address bar → focus + address bar event
8. Window header → focus + start drag
9. Window content → focus + Auckland content event

**MOUSE_UP path:**
- Ends any active resize or drag operation
- Routes UP events through the same overlay/content chain

**KEY_DOWN path:**
- **ESC** → close menu, start menu, cascade, or quit
- **Alt+V** → `Win_New()` — create a new window
- **F12** → toggle DebugLog overlay
- **F11** → toggle fullscreen
- All other keys → route to focused window's content

### 2.6 Database Bootstrap (`SysDisplay_InitDB`)

Connects to PostgreSQL (`ailang_system` database, user `bob`) and bootstraps the system schema. All DDL uses `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` patterns, making the bootstrap idempotent and safe to run every boot.

Tables created:
- **services** — Deskbar service launchers (name, binary_path, args, autostart, restart_policy, priority, enabled)
- **files** — Virtual filesystem (parent_id, name, type, blob_path, permissions, owner)
- **settings** — Key-value app settings (app_id, key, value)
- **users** — Authentication (username, password_hash, role)
- **windows** — Window state persistence (service_id, title, x, y, w, h, flags)

Default services seeded: notepad, files, calculator, grep, canvas_demo, videoplayer, chrome, ladybird.

---

## 3. EventRouter — Action Queue & Dispatch

### 3.1 Role

The EventRouter is the "what happens" side of the event system. All UI interactions generate **action strings** that are queued and dispatched in the main loop AFTER all Auckland rendering contexts are restored. This deferred dispatch pattern prevents re-entrant state corruption — window creation, IPC messages, and state mutations happen at a safe point in the frame.

### 3.2 Architecture

```
┌─────────────────┐     push()     ┌──────────────────┐     drain()     ┌─────────────────┐
│ SysDisplay      │ ──Ring1 drain──→│ ActionQueue       │ ───────────────→│ Dispatch        │
│ WinToolbar      │                │ (circular, 16 max) │                │ (registered +   │
│ AK_FireAction   │                └──────────────────┘                │  internal)      │
└─────────────────┘                                                    └─────────────────┘
```

### 3.3 Action Queue

A circular buffer of 16 entries, each 24 bytes:

```
ActionQueueEntry:
    [0-7]   action_ptr   — Pointer to null-terminated action string
    [8-15]  action_len   — Length of action string
    [16-23] source_win   — Window index that generated the action
                            -1 = desktop/taskbar
                             0 = desktop surface (unused)
                            1+ = window index
```

**Queue behavior:**
- `EventRouter_Push(action_ptr, action_len, source_win)` — enqueue; drops oldest if full
- `EventRouter_Drain()` — process all pending actions FIFO; returns count processed

### 3.4 Dispatch Priority

When an action is dequeued, dispatch follows a 3-tier priority:

**Tier 1 — System actions (always handled locally):**
Actions prefixed with `win.`, `app.`, `sys.`, `fd.`, `sm.`, or `menu:` are display server commands. They are never forwarded to external IPC processes.

**Tier 2 — IPC routing (app-owned windows):**
If the action is NOT a system action AND `source_win >= 1` AND the window has an IPC job binding, the action is forwarded to the external app process via `IPCBroker_RouteAction()`.

**Tier 3 — Internal handlers:**
The registered handler table is checked first (generic dispatch for `doc.*`, `view.*`, etc.), then hardcoded handlers fire for known action strings.

### 3.5 Internal Action Handlers

| Action | Handler | Effect |
|--------|---------|--------|
| `win.close` | `Win_Close(target)` | Close focused or source window |
| `win.min` | `Win_Minimize(target)` | Minimize window |
| `win.max` | `Win_Maximize(target)` | Maximize/restore window |
| `app.files` | `FileDialog_Open(0, 0, 14)` | Open file browser dialog |
| `fd.*` | `FD_HandleAction()` | File dialog navigation |
| `wf.1`–`wf.8` | `Win_Focus()` / `Win_Restore()` | Focus or restore window from deskbar |
| `svc.0`–`svc.15` | `Deskbar_LaunchService()` | Launch a registered service |
| `app.home` | `StartMenu_Toggle()` | Toggle Start Menu |
| `app.quit` | `SysDisplayState.running = 0` | Exit display server |
| `app.about` | `AboutDialog_Open()` | Open About dialog |
| `sys.screenshot` | `Screenshot_SavePPM()` + `Screenshot_Save()` | Save framebuffer to BMP+PPM |
| `about.close` | `AboutDialog_Close()` | Close About dialog |
| `menu:file` | `Menu_Show(0, source_win)` | Show File menu |
| `menu:edit` | `Menu_Show(1, source_win)` | Show Edit menu |
| `menu:view` | `Menu_Show(2, source_win)` | Show View menu |
| `menu:help` | `Menu_Show(3, source_win)` | Show Help menu |

### 3.6 Handler Registry

Apps can self-register custom action handlers at runtime via `EventRouter_RegisterHandler(action_str, callback)`. The registry holds 16 entries, each 16 bytes (action string pointer + callback function pointer). During dispatch, registered handlers are checked **before** hardcoded handlers.

**No-op callback pattern:** `EventRouter_NoOpCallback` is used as a placeholder callback for toolbar/menu/dialog nodes, suppressing `AK_FireAction` during event dispatch. The actual action is read manually from the focus node after context restore.

---

## 4. Screenshot — Framebuffer Capture

### 4.1 Role

Captures the current draw buffer (back buffer) to disk in both BMP and PPM formats. Used for debugging, documentation, and the `sys.screenshot` action.

### 4.2 BMP Output (`Screenshot_Save`)

Output path: `/tmp/screenshot.bmp`

**Format:** 24-bit BMP (BITMAPINFOHEADER), bottom-up row order, BGR pixel packing.

**Algorithm:**
1. Get framebuffer dimensions and draw buffer pointer
2. Compute BMP row stride (3 bytes/px, padded to 4-byte boundary)
3. Build 54-byte header:
   - File header (14 bytes): `BM` signature, file size, data offset
   - DIB header (40 bytes): width, height, 24-bit, BI_RGB, image size
4. Write header to file
5. For each row (bottom to top): read BGRA from framebuffer row, convert to BGR, write with padding
6. Close file

**BGRA→BGR conversion:** Drops the alpha channel and swaps R/B. The framebuffer uses BGRA byte order (standard Linux framebuffer), while BMP expects BGR.

### 4.3 PPM Output (`Screenshot_SavePPM`)

Output path: `/tmp/screenshot.ppm`

**Format:** PPM P6 binary (Netpbm), top-down row order, RGB pixel packing, no padding.

**Algorithm:**
1. Get framebuffer dimensions and draw buffer pointer
2. Build ASCII header: `P6\n{width} {height}\n255\n`
3. Write header to file
4. For each row (top to bottom): read BGRA, convert to RGB, write raw
5. Close file

**BGRA→RGB conversion:** Same as BMP but output order is RGB (swap B and R).

### 4.4 Helper Functions

- `SS_WriteLE16(buf, off, val)` — Write 16-bit little-endian integer
- `SS_WriteLE32(buf, off, val)` — Write 32-bit little-endian integer
- `SS_WriteDecimal(buf, off, val)` — Write integer as ASCII decimal digits

---

## 5. DebugLog — Developer Diagnostics

### 5.1 Role

A ring-buffer diagnostic system embedded in the display server. Provides real-time categorized logging and an on-screen overlay toggleable via F12.

### 5.2 Architecture

```
DebugLog ring buffer (N entries):
    Each entry: [timestamp (8), category (4), message (variable)]

Categories (2-character codes):
    "LOOP"   — Main loop iteration marker
    "DN"/"UP" — Mouse button down/up
    "MV"     — Mouse move
    "ERdr"   — EventRouter drain
    "AKdd"   — Auckland draw dirty
    "DI.ok"  — Drain input complete
    "sd.*"   — SysDisplay internal markers (init phases, loop phases)
    "er.*"   — EventRouter internal markers
```

### 5.3 Debug Overlay

When enabled (F12), a semi-transparent overlay is rendered showing:
- **FPS** — Current frames-per-second
- **Frame time** — Last frame delta in ms
- **Frame count** — Monotonic frame number
- **Dirty flag** — Whether current frame forced a recompose
- **Window count** — Active window count
- **Log ring** — Most recent log entries with timestamps

The overlay is rendered to its own surface and composited as the top-most layer during `Win_BlitAll`.

---

## 6. FPS Tracking

### 6.1 Algorithm

FPS is computed using a rolling 1-second window:

```
Each frame:
    delta_ms = time_since_last_frame
    fps_accum += delta_ms
    fps_frames += 1

    if fps_accum >= 1000:
        fps = (fps_frames * 1000) / fps_accum
        fps_accum = 0
        fps_frames = 0
```

### 6.2 Frame Pacing

After composition, the main loop calls `nanosleep({tv_sec=0, tv_nsec=16666666})` which is `1/60` second = ~16.67 ms. This provides a ~60 FPS cap. If composition takes longer than 16.67 ms (e.g., many windows, complex layouts), the sleep is effectively skipped and the actual frame rate drops below 60.

---

## 7. Dependencies

SysDisplay imports 40+ libraries spanning all subsystems:

```
Framebuffer, DRenderFB, Arena, DSurfaceTypes, DSurface, DDrawPixel,
DRingTypes, DRing1, DRing0, DComposeTypes, DComposeFloat, DCompose,
DInputTypes, DInputEvdev, DInputDiscover, KeyMap, TextRegion,
Cursor, CursorBitmap, PaneDecorator, WinManager, Auckland,
AucklandEvent, PostgreSQL_Complete, HTMLParse, AucklandBind,
VIF, SurfaceBlit, Fonts, EventRouter, Menu, Deskbar, WinToolbar,
UIConfig, UITheme, UIScale, JSON, VIcon
```

EventRouter has lighter dependencies:
```
StringUtils, WinManager, Menu, FileDialog, Deskbar, AboutDialog, Screenshot
```

Screenshot depends only on:
```
Framebuffer
```

---

## 8. Exit & Cleanup

The display server exits cleanly when `SysDisplayState.running` is set to 0. This happens via:
- **ESC key** — When no menus/overlays are open
- **`app.quit` action** — From Start Menu or deskbar

On exit, the main loop terminates, and control returns to the entry point. A future enhancement may add explicit framebuffer unmap, PostgreSQL disconnect, and input device close.
