# 06 — Desktop Shell & Content: Deskbar, Menu, StartMenu, CascadeMenu, Theme, Content

> **Copyright © 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.**

---

## 1. Overview

The Desktop Shell provides the user-facing interface: the taskbar (Deskbar), Start Menu, dropdown menus, cascade submenus, theming, configuration, and the content engine for documents. This layer sits on top of the UI Framework and Window Management layers, completing the desktop experience.

### Components

| Component | Source File | Lines | Role |
|-----------|------------|-------|------|
| **Deskbar** | `Library.Deskbar.ailang` | ~750 | System bar with hotzone reveal |
| **Menu** | `Library.Menu.ailang` | ~450 | Dropdown menus (File/Edit/View/Help) |
| **StartMenu** | `Library.StartMenu.ailang` | ~350 | XP/7-style start menu |
| **CascadeMenu** | `Library.CascadeMenu.ailang` | ~350 | Cascading submenus |
| **UIConfig** | `Library.UIConfig.ailang` | ~300 | Key=value config file loader |
| **UITheme** | `Library.UITheme.ailang` | ~155 | Color theme (50+ colors) |
| **UIScale** | `Library.UIScale.ailang` | ~240 | Resolution-aware sizing system |
| **Document** | `Library.Document.ailang` | ~350 | Multi-page document management |
| **PageSurface** | `Library.PageSurface.ailang` | ~350 | Paper-sized canvases (print resolution DPI) |
| **Editor** | `Library.Editor.ailang` | ~1400 | Text editor widget |
| **HTMLParse** | `Library.HTMLParse.ailang` | ~1100 | HTML parsing engine |

---

## 2. Deskbar — The Taskbar

### 2.1 Design

The Deskbar is a Windows XP/7-style taskbar that auto-hides at the bottom of the screen. It is revealed by moving the mouse into a "hotzone" at the bottom edge. This maximizes usable screen space while keeping the taskbar accessible.

### 2.2 Visual Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [● Start]  [Notepad] [Files] [Calc] [Grep] │ 8 windows  │ [FPS:60]  ▲ 16:42 │
└─────────────────────────────────────────────────────────────────────────────┘
    Start     Quick-launch      Window list       System tray   Clock
    button    service buttons                     + FPS
```

### 2.3 State Machine

```
DeskbarState:
    visible          — 0=hidden, 1=visible
    height           — Taskbar height in pixels (~32px)
    hotzone_h        — Hotzone trigger height (~4px)
    screen_w         — Screen width
    screen_h         — Screen height
    surface          — Taskbar pixel surface
    auckland_ctx     — Auckland context for taskbar widgets
    needs_refresh    — Set to 1 when window list changes
    hotzone_surface  — Checkerboard at screen bottom
    start_menu_open  — Whether Start Menu is open
```

### 2.4 Hotzone Reveal

```
Deskbar_HotzoneCheck(mouse_y):
    if mouse_y >= screen_h - hotzone_h:
        if not visible:
            Deskbar_Show()
            SysDisplayState.dirty = 1
    else if mouse_y < screen_h - height:
        if visible and not start_menu_open and not cascade_open:
            Deskbar_Hide()
            SysDisplayState.dirty = 1
```

### 2.5 Deskbar Sections

**Start button:** Fires `app.home` action → toggles Start Menu.

**Quick-launch service buttons:** Up to 16 service launchers loaded from PostgreSQL `services` table. Each button fires `svc.N` action → `Deskbar_LaunchService(N)` which spawns the service binary.

**Window list:** Shows running windows with their titles. Each entry fires `wf.N` to focus or restore the corresponding window. Max 8 entries displayed.

**System tray:** Shows FPS counter, clock, and screenshot button (`sys.screenshot`).

**Hotzone:** A thin checkerboard pattern at the bottom of screen, rendered by `Deskbar_DrawHotzone()`. It's always drawn as the bottom-most layer of the desktop surface.

### 2.6 Refresh Cycle

`Deskbar_Refresh()` rebuilds the window list when `needs_refresh` is set:
```
1. Clear window list nodes from Auckland tree
2. For each window in WinMgr (excluding desktop):
    a. Create button node with window title
    b. Set action string to "wf.N"
3. AK_Solve + AK_Draw
4. needs_refresh = 0
```

### 2.7 Service Launch

`Deskbar_LaunchService(service_idx)`:
```
1. Query PostgreSQL for service by priority order where enabled=true
2. If binary_path starts with "internal:":
    Push action string (e.g., "app.files") to EventRouter
3. If binary_path is a real path:
    Fork/exec the service binary with args
    Wait for socket connection on IPC port
    Bind window when app sends WINDOW_CREATE
```

---

## 3. Start Menu

### 3.1 Design

The Start Menu is a two-column menu inspired by Windows XP/7:

```
┌─────────────────────────────┐
│  Programs  ▸                │
│  Documents ▸                │
│  Settings  ▸                │
│  Search    ▸                │
│  Run...                     │
│ ─────────────────────────── │
│  Notepad                    │
│  Files                      │
│  Calculator                 │
│ ─────────────────────────── │
│  About                      │
│  Quit                       │
└─────────────────────────────┘
```

### 3.2 State

```
StartMenuState:
    open            — 0=closed, 1=open
    surface         — Menu pixel surface
    x, y            — Position (anchored to deskbar start button)
    w, h            — Menu dimensions
    auckland_ctx    — Auckland context for menu items
    cascade_menu    — Currently open cascade submenu (-1 = none)
    cascade_surf    — Cascade menu surface
```

### 3.3 Behavior

- **Toggle:** Start button or `app.home` action opens/closes
- **Close on click-outside:** Clicking anywhere outside the menu closes it
- **Close on action:** Selecting an item closes the menu (via `StartMenu_Close()`)
- **Cascade:** Hovering over "Programs", "Documents", etc. opens a CascadeMenu
- **Auto-close cascade:** Moving mouse away closes cascade submenu

### 3.4 Menu Items

| Item | Action | Handler |
|------|--------|---------|
| Programs ▸ | `sm.programs` | CascadeMenu_Show |
| Documents ▸ | `sm.system` | CascadeMenu_Show |
| Notepad | `svc.0` | Deskbar_LaunchService |
| Files | `svc.1` | Deskbar_LaunchService |
| Calculator | `svc.2` | Deskbar_LaunchService |
| About | `app.about` | AboutDialog_Open |
| Quit | `app.quit` | Set running=0 |

---

## 4. Menu — Dropdown Menus

### 4.1 Design

Window toolbar menus provide File, Edit, View, and Help dropdowns. Each menu is an Auckland tree rendered on an overlay surface.

### 4.2 State

```
MenuState:
    open            — Is a menu open?
    which           — Which menu (0=File, 1=Edit, 2=View, 3=Help)
    source_win      — Which window opened the menu
    surface         — Menu surface
    x, y, w, h      — Position (anchored to toolbar button)
    auckland_ctx    — Auckland context
```

### 4.3 Menu Contents

**File menu:**
| Item | Action |
|------|--------|
| New | `doc.new` |
| Open | `doc.open` |
| Save | `doc.save` |
| Save As | `doc.saveas` |
| ───── | |
| Close | `win.close` |
| Quit | `app.quit` |

**Edit menu:**
| Item | Action |
|------|--------|
| Cut | `edit.cut` |
| Copy | `edit.copy` |
| Paste | `edit.paste` |
| Select All | `edit.selectall` |

**View menu:**
| Item | Action |
|------|--------|
| Zoom In | `view.zoomin` |
| Zoom Out | `view.zoomout` |
| Fullscreen | `view.fullscreen` |

**Help menu:**
| Item | Action |
|------|--------|
| About | `app.about` |

### 4.4 Behavior

- **Open:** `menu:file`, `menu:edit`, `menu:view`, or `menu:help` action
- **Hover switch:** Moving mouse from one menu header to another switches which menu is shown
- **Close:** Clicking outside or selecting an item
- **Position:** Anchored below the toolbar button, adjusted if near screen edge

### 4.5 Menu Events

`Menu_Event(x, y, event_type)` dispatches into the menu's Auckland tree using save/restore context switching:
```
1. Save current Auckland context
2. Restore menu's Auckland context
3. AK_Event(x_local, y_local, event_type)
4. If UP event on item with action: fire action, close menu
5. Restore previous context
```

---

## 5. CascadeMenu — Cascading Submenus

### 5.1 Design

CascadeMenu provides fly-out submenus that appear to the right of a parent menu item. Used by the Start Menu for Programs, Documents, Settings.

### 5.2 State

```
CascadeMenuState:
    open            — Is a cascade open?
    parent_menu     — Which parent menu (0=StartMenu programs, 1=documents, etc.)
    surface         — Cascade surface
    x, y, w, h      — Position (anchored to right of parent item)
    auckland_ctx    — Auckland context
```

### 5.3 Behavior

- **Open:** Hovering over a Start Menu item with the `sm.` action prefix
- **Close:** Moving mouse away from both the parent item and the cascade surface
- **Hit test:** `CascadeMenu_HitTest(x, y)` returns 1 if point is inside the cascade or its parent item
- **Nested cascades:** Not currently supported (one level deep)

### 5.4 Hit Test Logic

The cascade hit test is "sticky" — it includes a tolerance zone between the parent item and the cascade surface so the user can move the mouse diagonally without the menu closing.

---

## 6. UITheme — Color System

### 6.1 Architecture

UITheme defines 50+ named color constants used throughout the display system. Colors are 32-bit packed BGRA.

### 6.2 Color Categories

| Category | Count | Colors |
|----------|-------|--------|
| Desktop | 1 | DESKTOP background |
| Window chrome | 8 | `window_bg`, `header_color`, `border`, `toolbar_bg`, `toolbar_close_bg`, `toolbar_min_bg`, `toolbar_max_bg`, `text_fg` |
| Toolbar buttons | 4 | BTN_HOVER, BTN_PRESSED, BTN_DISABLED, BTN_TEXT |
| Tabs | 4 | `tabbar_bg`, `tab_active_bg`, `tab_text`, `tab_icon` |
| Deskbar | 11 | `deskbar_bg`, `deskbar_btn_bg`, `deskbar_btn_fg`, `deskbar_btn2_bg`, `deskbar_btn2_fg`, `deskbar_hot_fg`, `deskbar_hot_bg`, `deskbar_win_bg`, `deskbar_win_fg`, `deskbar_win_act_bg`, `deskbar_sep` |
| Menu | 5 | `menu_bg`, `menu_fg`, `menu_sep`, `menu_border`, `panel_bg` |
| Dialog | 3 | `dialog_bg`, `panel_bg`, `text_fg` |
| Input | N/A | (not yet themable — uses hardcoded values) |
| Scrollbar | 4 | SCROLLBAR_BG, SCROLLBAR_THUMB, SCROLLBAR_HOVER, SCROLLBAR_ARROW |
| Content | 4 | DOCUMENT_BG, PAGE_BG, PAGE_SHADOW, EDITOR_BG |
| Debug | 2 | DEBUG_OVERLAY_BG, DEBUG_TEXT |

### 6.3 Default Theme

The default theme is a dark blue/grey scheme reminiscent of Windows Classic with modern flat-design influences:
- Desktop: dark grey (#2D2D2D)
- Active header: navy blue (#1E3A5F)
- Inactive header: darker grey (#3A3A3A)
- Text: white (#FFFFFF)
- Accent: light blue (#4A90D9)

### 6.4 Theme Loading

`UITheme_Load()` applies defaults, then overrides from `ui.cfg`:
```
UIConfig_Load("ui.cfg")
For each known color key:
    value = UIConfig_Get(key)
    if value != "":
        UITheme_SetColor(key, parse_hex(value))
```

---

## 7. UIConfig — Configuration

### 7.1 File Format

Simple `key=value` text format, one entry per line:
```
# Comment lines start with #
header_bg_active=1E3A5F
desktop_bg=2D2D2D
font_title=16
border_w=2
```

### 7.2 API

| Function | Description |
|----------|-------------|
| `UIConfig_Load(path)` | Parse config file into key-value store |
| `UIConfig_Get(key)` | Get string value for key |
| `UIConfig_GetInt(key)` | Get integer value for key |
| `UIConfig_Set(key, value)` | Set override at runtime |

### 7.3 Configurable Values

All 50+ colors, plus:
- Header height, border width, toolbar height
- Tab dimensions (max width, row height, icon width, padding)
- Font sizes (title, body, button, tab, menu)
- Minimum window size
- Animation flags
- Debug overlay opacity

---

## 8. UIScale — Resolution-Aware Sizing

### 8.1 Algorithm

`UIScale` computes a scale factor based on screen height relative to a 1080p reference:

```
reference_h = 1080
actual_h = screen_height
scale = actual_h / reference_h
```

All UI dimensions (fonts, icons, margins, buttons) are multiplied by this scale factor. This ensures the UI looks consistent across different resolutions — from 720p laptops to 4K displays.

### 8.2 Scaled Dimensions

```
UIScale:
    font_title      — Title font size (scaled)
    font_body       — Body text size
    font_button     — Button text size
    font_tab        — Tab text size
    font_menu       — Menu text size
    header_h        — Title bar height
    border_w        — Window border width
    toolbar_h       — Toolbar height
    button_w        — Button width
    tab_max_w       — Maximum tab width
    tab_row_h       — Tab row height
    tab_icon_w      — Tab icon width
    tab_pad         — Tab padding
    menu_item_h     — Menu item height
    deskbar_h       — Deskbar height
    icon_size       — Default icon size
```

---

## 9. Content Engine

### 9.1 Document (`Library.Document.ailang`)

Multi-page document management:

```
Document:
    page_count      — Number of pages
    pages[]         — Array of PageSurface handles
    current_page    — Active page index
    file_path       — Associated file path
    dirty           — Unsaved changes flag
```

| Function | Description |
|----------|-------------|
| `Document_Create()` | Create empty document |
| `Document_AddPage(doc)` | Append new page |
| `Document_RemovePage(doc, idx)` | Remove page |
| `Document_GetPage(doc, idx)` | Get page surface handle |
| `Document_Load(path)` | Load document from file |
| `Document_Save(doc, path)` | Save document to file |

### 9.2 PageSurface (`Library.PageSurface.ailang`)

Paper-sized canvases with configurable DPI:

```
PageSurface:
    surface         — Pixel surface
    width_pts       — Width in points (1/72 inch)
    height_pts      — Height in points
    dpi             — Dots per inch (default 96)
    margin_pts      — Print margins
```

Standard page sizes: Letter (8.5×11"), A4 (210×297mm), Legal (8.5×14").

### 9.3 Editor (`Library.Editor.ailang`)

Full text editor widget (~1400 lines):

| Feature | Description |
|---------|-------------|
| Multi-line | Text wrapping, line numbers |
| Selection | Mouse drag and keyboard (Shift+Arrow) |
| Cursor | Blinking insertion caret |
| Scroll | Vertical and horizontal scrollbars |
| Undo/Redo | Edit history stack |
| Clipboard | Cut/Copy/Paste |
| Font | Configurable font face and size |
| Syntax | Basic syntax highlighting hooks |

### 9.4 HTMLParse (`Library.HTMLParse.ailang`)

HTML parsing engine (~1100 lines):

| Feature | Description |
|---------|-------------|
| Tokenizer | Tag, text, comment, doctype tokens |
| Tree builder | DOM-like node tree |
| Tags | h1-h6, p, div, span, a, img, br, ul, ol, li, table, tr, td, b, i, u, pre |
| Attributes | id, class, href, src, width, height, style (partial) |
| Rendering | Lays out HTML tree into Auckland nodes |
| CSS | Minimal inline style support (color, font-size, text-align) |

---

## 10. Dependencies

```
Deskbar → Auckland, AucklandEvent, WinManager, EventRouter, PostgreSQL_Complete,
          UITheme, UIScale, Cursor, Fonts, TextRegion

Menu → Auckland, AucklandEvent, WinManager, EventRouter, UITheme, UIScale

StartMenu → Auckland, AucklandEvent, CascadeMenu, Deskbar, UITheme, UIScale

CascadeMenu → Auckland, AucklandEvent, UITheme, UIScale

UIConfig → StringUtils (key=value parsing)

UITheme → UIConfig

UIScale → Framebuffer (for screen dimensions)

Document → PageSurface, StringUtils

PageSurface → DSurface, DDrawPixel

Editor → Auckland, AucklandEvent, TextRegion, Fonts, StringUtils

HTMLParse → Auckland, AucklandBind, TextRegion, Fonts, StringUtils, JSON
```
