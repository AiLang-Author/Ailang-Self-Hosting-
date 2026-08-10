# AILANG Display System — Complete Documentation

> **Copyright © 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.**

---

## Document Index

| # | Document | Description | Status |
|---|----------|-------------|--------|
| 00 | MASTER_INDEX.md | This file — overview, architecture, dependency map | ✅ |
| 01 | 01_SYSTEM_CORE.md | SysDisplay, EventRouter, Screenshot, DebugLog, FPS | ✅ |
| 02 | 02_WINDOW_MANAGEMENT.md | WinManager, WinInput, WinRender, WinStack, WinToolbar | ✅ |
| 03 | 03_RENDER_PIPELINE.md | Framebuffer, Surfaces, Compositor, Rings, Fonts, VIF | ✅ |
| 04 | 04_UI_FRAMEWORK.md | Auckland, AucklandBind, AucklandEvent, TextRegion, Dialogs | ✅ |
| 05 | 05_INPUT_SYSTEM.md | Evdev, Cursor, IPCBroker, Device Discovery (+ InputRouter archived) | ✅ |
| 06 | 06_DESKTOP_SHELL_CONTENT.md | Deskbar, Menu, StartMenu, CascadeMenu, Theme, Content | ✅ |
| 07 | 07_PAIN_POINTS.md | Pain points, hardening roadmap, prioritized mitigations | ✅ |

---

## Architecture Overview

The AILANG Display System is a complete graphical desktop environment written in the AILANG programming language. It runs directly on the Linux framebuffer (`/dev/fb0`), bypassing X11 and Wayland entirely. The system implements its own window management, compositing, input handling, UI toolkit, and desktop shell.

### System Layers

```
┌─────────────────────────────────────────────────────────┐
│                   DESKTOP SHELL                         │
│  Deskbar │ StartMenu │ CascadeMenu │ Dropdown Menus     │
├─────────────────────────────────────────────────────────┤
│                   UI FRAMEWORK                          │
│  Auckland Layout Engine │ Dialogs │ TextRegion          │
│  FileDialog │ AboutDialog │ NotepadApp                 │
├─────────────────────────────────────────────────────────┤
│                   WINDOW MANAGEMENT                     │
│  WinManager │ WinStack (Z-order) │ WinInput (drag/resize)│
│  WinRender │ WinToolbar                                 │
├─────────────────────────────────────────────────────────┤
│                   SYSTEM CORE                           │
│  SysDisplay (main loop) │ EventRouter (action dispatch)  │
│  Screenshot │ DebugLog │ FPS Tracking                  │
├─────────────────────────────────────────────────────────┤
│                   RENDER PIPELINE                       │
│  Framebuffer │ Surfaces │ DCompose │ Rings │ Fonts     │
│  VIF/VIcon │ SurfaceBlit │ SuperSample │ AudioEngine   │
├─────────────────────────────────────────────────────────┤
│                   INPUT SYSTEM                          │
│  Evdev │ EventRouter │ Cursor │ IPCBroker              │
│  Device Discovery (by-id + fallback)                   │
├─────────────────────────────────────────────────────────┤
│                   THEME & CONFIG                        │
│  UIConfig (key=value loader) │ UITheme (50+ colors)     │
│  UIScale (Resolution-aware scaling)                      │
├─────────────────────────────────────────────────────────┤
│                   CONTENT ENGINE                        │
│  Document (multi-page) │ PageSurface │ Editor          │
│  HTMLParse                                             │
└─────────────────────────────────────────────────────────┘
```

### Data Flow — Main Loop

```
1. Evdev_Poll()           — Read /dev/input/event* → post to Ring1
2. SysDisplay_DrainInput()— Drain Ring1 → route key/mouse to focused window
3. EventRouter_Drain()    — Process action queue → create/destroy windows
4. Deskbar_Refresh()      — Rebuild deskbar if needed (window changes)
5. Win_BlitAll()          — Compose all windows + overlays → framebuffer
6. Cursor_Draw()          — Restore old, save new, draw cursor
7. Deskbar_DrawHotzone()  — Draw checkerboard at screen bottom
8. SysDisplay_Flip()      — Framebuffer page flip (double-buffered)
9. SysDisplay_UpdateFPS()— Track frame timing
```

### Action Routing System

All UI interactions generate **action strings** routed through the EventRouter:

| Prefix | Example | Source | Handler |
|--------|---------|--------|---------|
| `win.` | `win.close`, `win.min`, `win.max` | Window toolbar buttons | EventRouter_Internal |
| `app.` | `app.files`, `app.home`, `app.quit`, `app.about` | Deskbar/StartMenu | EventRouter_Internal |
| `sys.` | `sys.screenshot` | Deskbar system tray | EventRouter_Internal |
| `fd.` | `fd.nav`, `fd.select`, `fd.back`, `fd.cancel`, `fd.ok` | FileDialog buttons | FD_HandleAction |
| `sm.` | `sm.programs`, `sm.system` | Start Menu categories | CascadeMenu_Show |
| `menu:` | `menu:file`, `menu:edit`, `menu:view`, `menu:help` | Window toolbar menus | Menu_Show |
| `wf.` | `wf.1` through `wf.8` | Deskbar window list | EventRouter focus |
| `svc.` | `svc.0` through `svc.15` | Deskbar service launchers | Deskbar_LaunchService |
| `doc.` | `doc.new`, `doc.open`, `doc.save` | Menu items | Registered handlers |
| `view.` | `view.zoomin`, `view.zoomout` | Menu items | Registered handlers |

### Ring Buffer Architecture

The system uses a 4-level ring buffer hierarchy for inter-component communication:

| Ring | Direction | Purpose |
|------|-----------|---------|
| Ring0 | Host → Compositor | Commands: tile split/merge, surface operations |
| Ring1 | Input → Host | Events: keyboard, mouse, wheel |
| Ring2 | Compositor → Input | Feedback: surface positions, hit test results |
| Ring3 | Host → Compositor | Surface lifecycle: create, destroy, resize |

### File Inventory

#### System Core (`Librarys/Display/System/`)
| File | Lines | Purpose |
|------|-------|---------|
| `Library.SysDisplay.ailang` | ~1500 | Main display server: init, loop, framebuffer, input drain |
| `Library.EventRouter.ailang` | ~500 | Action queue, handler registry, dispatch |
| `Library.Screenshot.ailang` | ~250 | BMP/PPM framebuffer capture |

#### Window Management (`Librarys/Display/Window/`)
| File | Lines | Purpose |
|------|-------|---------|
| `Library.WinManager.ailang` | ~1100 | Window CRUD, z-order, focus, IPC binding |
| `Library.WinInput.ailang` | ~400 | Hit testing, drag/resize state machines |
| `Library.WinRender.ailang` | ~450 | Window decoration rendering |
| `Library.WinStack.ailang` | ~150 | Z-order stack management |
| `Library.WinToolbar.ailang` | ~700 | Per-window toolbar with Auckland |

#### Render Pipeline (`Librarys/Display/Render/`)
| File | Lines | Purpose |
|------|-------|---------|
| `Library.Framebuffer.ailang` | ~1512 | /dev/fb0 mmap, double-buffer, flip, vsync |
| `Library.DRenderFB.ailang` | ~150 | Framebuffer init double-buffer helper |
| `Library.DSurface.ailang` | ~180 | Pixel surface alloc/free/access |
| `Library.DSurfaceTypes.ailang` | ~100 | Surface format constants |
| `Library.DDrawPixel.ailang` | ~250 | Pixel drawing primitives |
| `Library.DDrawCell.ailang` | ~200 | Character cell rendering |
| `Library.DCompose.ailang` | ~550 | Compositor: float stack, BSP tree |
| `Library.DComposeTypes.ailang` | ~100 | Compositor type constants |
| `Library.DComposeFloat.ailang` | ~150 | Float hit testing |
| `Library.DComposeStack.ailang` | ~200 | Surface stack management |
| `Library.DComposeBSP.ailang` | ~200 | BSP tree for occlusion |
| `Library.DRing.ailang` | ~100 | Ring buffer base |
| `Library.DRing0.ailang` | ~50 | Ring0 (host→compositor) |
| `Library.DRing1.ailang` | ~50 | Ring1 (input→host) |
| `Library.DRing2.ailang` | ~50 | Ring2 (compositor→input) |
| `Library.DRing3.ailang` | ~100 | Ring3 (host→compositor surface ops) |
| `Library.DRingTypes.ailang` | ~100 | Ring entry/event type constants |
| `Library.DZone.ailang` | ~150 | Zone (occlusion region) management |
| `Library.DZoneTypes.ailang` | ~50 | Zone type constants |
| `Library.Fonts.ailang` | ~806 | Font loading, glyph cache, vector rendering via TVG |
| `Library.VIF.ailang` | ~1793 | Vector Icon Format parser/renderer |
| `Library.VIcon.ailang` | ~300 | VIcon (vector icon) management |
| `Library.SuperSample.ailang` | ~200 | 2x/4x supersampling AA |
| `Library.SurfaceBlit.ailang` | ~450 | Surface-to-surface blit operations |
| `Library.AudioEngine.ailang` | ~700 | Audio output subsystem |

#### Input System (`Librarys/Display/Input/` + `IPC/`)
| File | Lines | Purpose |
|------|-------|---------|
| `Library.DInputTypes.ailang` | ~250 | Linux evdev structs, key codes, mouse state |
| `Library.DInputEvdev.ailang` | ~350 | Evdev read/poll, key/mouse event processing |
| `Library.DInputDiscover.ailang` | ~400 | Device discovery (by-id + /proc fallback) |
| `Library.Cursor.ailang` | ~350 | Cursor save/restore/draw, shape switching |
| `Library.CursorBitmap.ailang` | ~350 | Bitmap cursor masks (4 shapes) |
| `Library.InputRouter.ailang` | ~200 | ☠️ DEAD/VESTIGIAL — Ring1 drain, hotkey dispatch; functionally replaced by EventRouter |
| `Library.IPCBroker.ailang` | ~1000 | Inter-process communication broker |

#### UI Framework (`Librarys/Display/UI/`)
| File | Lines | Purpose |
|------|-------|---------|
| `Library.Auckland.ailang` | ~1500 | Layout engine: tree, measure, layout, draw |
| `Library.AucklandBind.ailang` | ~700 | Data binding system |
| `Library.AucklandEvent.ailang` | ~400 | Mouse/key event dispatch, hit testing |
| `Library.TextRegion.ailang` | ~700 | Text rendering with wrapping/alignment |
| `Library.PaneDecorator.ailang` | ~100 | Window chrome decoration |
| `Library.Dialog.ailang` | ~450 | Modal dialog system |
| `Library.FileDialog.ailang` | ~1200 | File browser dialog |
| `Library.AboutDialog.ailang` | ~60 | About dialog |
| `Library.NotepadApp.ailang` | ~150 | Simple text editor app |

#### Desktop Shell (`Librarys/Display/Menu/` + `Theme/` + `Content/`)
| File | Lines | Purpose |
|------|-------|---------|
| `Library.Menu.ailang` | ~450 | Dropdown menus (File/Edit/View/Help) |
| `Library.Deskbar.ailang` | ~750 | System bar with hotzone reveal |
| `Library.StartMenu.ailang` | ~350 | XP/7-style start menu |
| `Library.CascadeMenu.ailang` | ~350 | Cascading submenus |
| `Library.UIConfig.ailang` | ~300 | Key=value config file loader |
| `Library.UITheme.ailang` | ~155 | Color theme (50+ colors, resolution-aware) |
| `Library.UIScale.ailang` | ~240 | Resolution-aware sizing system |
| `Library.Document.ailang` | ~350 | Multi-page document management |
| `Library.PageSurface.ailang` | ~350 | Paper-sized canvases (print resolution DPI) |
| `Library.Editor.ailang` | ~1400 | Text editor widget |
| `Library.HTMLParse.ailang` | ~1100 | HTML parsing engine |

---

## Key Dependencies

### SysDisplay imports 40+ libraries:
```
Framebuffer, DRenderFB, Arena, DSurfaceTypes, DSurface, DDrawPixel,
DRingTypes, DRing1, DRing0, DComposeTypes, DComposeFloat, DCompose,
DInputTypes, DInputEvdev, DInputDiscover, KeyMap, TextRegion,
Cursor, CursorBitmap, PaneDecorator, WinManager, Auckland,
AucklandEvent, PostgreSQL_Complete, HTMLParse, AucklandBind,
VIF, SurfaceBlit, Fonts, EventRouter, Menu, Deskbar, WinToolbar,
UIConfig, UITheme, UIScale, JSON, VIcon
```

---

## Design Principles

1. **No X11/Wayland** — Direct framebuffer access via `/dev/fb0` mmap
2. **Own Window Manager** — Float-based windows, focus-follows-click
3. **Auckland Layout Engine** — Custom retained-mode UI toolkit with VBOX/HBOX
4. **Action Queue Pattern** — All side effects deferred through EventRouter
5. **Save/Restore Cursor** — No hardware cursor; software cursor with pixel save/restore
6. **Resolution-Aware** — UIScale computes from screen height relative to 1080p reference
7. **PostgreSQL-Backed** — Service registry, config, and app data in PostgreSQL
8. **IPC-Ready** — IPCBroker routes actions to external app processes
9. **Config-Driven** — ui.cfg key=value overrides for all colors and dimensions
10. **Debug-First** — DebugLog ring buffer (F12 toggle), verbose logging throughout

## Build & Run

The display server is compiled from `Library.SysDisplay.ailang` which imports
all subsystem libraries. The compiled binary runs as a standalone process that:
1. Opens `/dev/fb0` and maps the framebuffer
2. Discovers keyboard/mouse via `/dev/input/by-id/` or `/proc/bus/input/devices`
3. Opens `/dev/input/event*` in non-blocking mode
4. Initializes PostgreSQL connection
5. Enters the main render loop at ~60 FPS

Exit via ESC key or `app.quit` action.
