# 02 — Window Management: WinManager, WinInput, WinRender, WinStack, WinToolbar

> **Copyright © 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.**

---

## 1. Overview

The Window Management layer handles window lifecycle (create, close, minimize, maximize, restore), geometry tracking, hit testing, drag/resize state machines, z-ordering, tab stacking, toolbar rendering, and final framebuffer composition. It is the bridge between low-level input events and the high-level Auckland UI framework.

### Components

| Component | Source File | Lines | Role |
|-----------|------------|-------|------|
| **WinManager** | `Library.WinManager.ailang` | ~1100 | Window CRUD, z-order, focus, geometry, IPC bindings |
| **WinInput** | `Library.WinInput.ailang` | ~400 | Hit testing, drag/resize state machines |
| **WinRender** | `Library.WinRender.ailang` | ~450 | Window decoration + final framebuffer composition |
| **WinStack** | `Library.WinStack.ailang` | ~150 | Tab stacking, tab bar height calculation |
| **WinToolbar** | `Library.WinToolbar.ailang` | ~700 | Per-window toolbar with Auckland layout |

---

## 2. WinManager — Window Lifecycle

### 2.1 Architecture

WinManager maintains three core data structures for up to 8 simultaneous windows:

```
WinGeom[8]    — Per-window geometry (48 bytes each)
    total_w, total_h, canvas_w, canvas_h, x, y

WinView[8]    — Per-window view bindings (variable size each)
    job_ptr, service_id, content_ctx, doc_handle, page_handle,
    bindings (action→handler map), binding_count, view_type,
    header, content, toolbar surfaces

Canvas[8]     — Per-window IPC canvas state
    active, shm_ptr, shm_size, surf, mouse_capture, dirty,
    cursor_native

z_order[8]    — Top-to-bottom window stack (indices into above arrays)
focused       — Currently focused window index (0 = desktop)
count         — Number of active windows
```

### 2.2 Window Creation (`Win_Create`)

Creates a new floating window with default geometry:

```
1. Find free slot (indices 1-7, since 0 = desktop)
2. Surface_Create(BGRA, w, h) → header surface
3. Surface_Create(BGRA, w, h) → content surface
4. Surface_Create(BGRA, w, h) → toolbar surface
5. Fill surfaces with theme colors (window_bg, toolbar_bg, etc.)
6. Draw window decorations (border, header text, close/min/max buttons)
7. Float_Add(content_surface, x, y, w, h) → compositor entry
8. Push to z_order (top of stack)
9. WinView_Init for IPC bindings
10. Stack_Create for tab support
11. Win_Focus(new_idx)
12. Set SysDisplayState.dirty = 1
```

Default window size: 768×576, positioned cascaded from tracked next_x/next_y offsets.

### 2.3 Window Close (`Win_Close`)

```
1. If minimized, remove from minimized list
2. Float_Remove from compositor
3. Surface_Destroy: header, content, toolbar
4. Remove from z_order (shift down)
5. Clear WinGeom, WinView, Canvas slots
6. Deallocate aux data (title strings, stack, bindings)
7. WinMgr.count -= 1
8. If was focused, focus top-most remaining window
9. DeskbarState.needs_refresh = 1
```

### 2.4 Focus Management (`Win_Focus`)

Focus-follows-click model:
```
1. If already focused → no-op
2. Move target window to top of z_order
3. Update WinMgr.focused
4. If target has IPC canvas, send focus event
5. Set dirty = 1 for redraw (active/inactive decoration change)
```

### 2.5 Minimize/Maximize/Restore

**Minimize (`Win_Minimize`):**
1. Remove from z_order
2. Add to minimized list
3. If was focused, focus next window
4. DeskbarState.needs_refresh = 1

**Restore (`Win_Restore`):**
1. Push to top of z_order
2. Remove from minimized list
3. Win_Focus(idx)

**Maximize (`Win_Maximize`):**
1. Save current geometry to WinMaxGeom
2. Set geometry to full screen (minus deskbar area)
3. `Win_ResizeSurfaces` to match new dimensions

**MaxRestore (`Win_MaxRestore`):**
1. Restore geometry from WinMaxGeom
2. `Win_ResizeSurfaces` to match restored dimensions

### 2.6 Surface Resize (`Win_ResizeSurfaces`)

When window geometry changes (resize, maximize, restore):
```
1. Surface_Resize(header, new_width, header_height)
2. Surface_Resize(content, new_canvas_w, new_canvas_h)
3. Surface_Resize(toolbar, new_width, toolbar_height)
4. If has tab bar: Surface_Resize(tab_surface, ...)
5. Redraw all decorations
```

### 2.7 IPC Bindings (WinView)

Each window can bind to an external IPC process:
- `job_ptr` — IPCBroker job handle for the app process
- `service_id` — Database service ID
- `bindings` — Custom action→handler mapping
- `content_ctx` — Auckland context handle for the content area
- `doc_handle` / `page_handle` — Document/view references

`WinView_Save` and `WinView_Restore` handle the save/restore of Auckland context data when switching between the desktop context and a window's content context.

### 2.8 Z-Order (`WinMgr_ZGet` / `WinMgr_ZSet`)

Simple array-based z-order stack:
- Index 0 = bottom-most (desktop)
- Higher indices = closer to viewer
- `z_count` tracks active entries
- Focus operation moves window to top (highest index)

---

## 3. WinInput — Hit Testing & State Machines

### 3.1 Hit Testing Hierarchy

WinInput provides a layered hit-test system that determines which window region (if any) is under the cursor:

| Function | Region | Purpose |
|----------|--------|---------|
| `Win_HitTest(x, y)` | Content area | Returns window index or -1 |
| `Win_HeaderHitTest(x, y)` | Title bar / header | Drag target |
| `Win_ToolbarHitTest(x, y)` | Toolbar area | Button/icon clicks |
| `Win_AddrBarHitTest(x, y)` | Address bar | URL/navigation bar |
| `Win_BorderHitTest(x, y)` | Window border | Resize target (returns edge code) |
| `Win_ProbeBorder(x, y)` | Border edge probe | Which edge (N/S/E/W/NE/NW/SE/SW) |

### 3.2 Border Hit Test

`Win_BorderHitTest` returns:
- `-1` — Miss (not on a border)
- `0-7` — Window index (if click is within resize border of that window)

Border width is defined by `DecorConfig.border_w`. The function checks windows in z-order (top-down), returning the first match.

Edge codes from `Win_ProbeBorder`:
```
0 = N (top edge)      4 = NE (top-right corner)
1 = S (bottom edge)   5 = NW (top-left corner)
2 = E (right edge)    6 = SE (bottom-right corner)
3 = W (left edge)     7 = SW (bottom-left corner)
```

### 3.3 Drag State Machine

Three-phase drag for window repositioning:

```
Win_StartDrag(idx, x, y):
    drag_idx = idx
    drag_start_x = x
    drag_start_y = y
    drag_orig_x = Win_GetX(idx)
    drag_orig_y = Win_GetY(idx)

Win_UpdateDrag(x, y):
    dx = x - drag_start_x
    dy = y - drag_start_y
    new_x = drag_orig_x + dx
    new_y = drag_orig_y + dy
    Win_SetGeom(idx, new_x, new_y, w, h)
    Float_Move(float_entry, new_x, new_y)
    dirty = 1

Win_StopDrag():
    drag_idx = -1
```

Drag only applies to MOUSE_MOVE events while `drag_idx >= 0`.

### 3.4 Resize State Machine

Four-phase resize with live geometry updates:

```
Win_StartResize(idx, x, y):
    resize_idx = idx
    resize_start_x = x
    resize_start_y = y
    resize_orig_x = Win_GetX(idx)
    resize_orig_y = Win_GetY(idx)
    resize_orig_w = Win_GetTotalW(idx)
    resize_orig_h = Win_GetTotalH(idx)
    resize_edge = Win_ProbeBorder(idx, x, y)

Win_UpdateResize(x, y):
    dx = x - resize_start_x
    dy = y - resize_start_y
    Apply edge-specific geometry delta:
        N: y += dy, h -= dy
        S: h += dy
        E: w += dx
        W: x += dx, w -= dx
        (similar for corners)
    Clamp to minimum size (MIN_W × MIN_H)
    Win_SetGeom(...)
    Float_Resize(float_entry, new_x, new_y, new_w, new_h)
    dirty = 1

Win_ApplyResize():
    Win_ResizeSurfaces(idx)   // Rebuild surfaces to new size
    Win_ResizeToolbar(idx)    // Rebuild toolbar layout
    resize_idx = -1
```

### 3.5 Key Event Dispatch

`Win_KeyDown(keycode)` routes keyboard events to the focused window's Auckland content context. If the focused window has an IPC canvas, the key event is forwarded to the external process instead.

---

## 4. WinRender — Composition & Decoration

### 4.1 `Win_BlitAll` — Main Composition

The coronary artery of the render pipeline. Called once per frame when dirty:

```
Win_BlitAll():
    1. FB_ClearBuffer(draw_buffer) if dirty
    2. For each window in z_order (bottom to top):
        Win_BlitOne(idx)
    3. Blit cursor (save/restore pixels)
    4. Blit deskbar hotzone
    5. Blit debug overlay (if enabled)
    6. FB_Flip() — page flip to show new frame
```

### 4.2 `Win_BlitOne` — Per-Window Blit

Blits a single window to the framebuffer:

```
Win_BlitOne(idx):
    1. Get window geometry and float entry
    2. If minimized → skip
    3. Win_DrawBorderFB(idx)    — Window border (1-2px, theme-colored)
    4. Win_DrawHeader(idx)      — Title bar with text and buttons
    5. Win_DrawTabBar(idx)      — Tab bar if stack has multiple tabs
    6. Blit content surface     — Copy content pixels to framebuffer
    7. Blit toolbar surface     — Copy toolbar pixels to framebuffer
    8. Blit address bar         — If present
```

### 4.3 Window Decorations

**Border:** `Win_DrawBorderFB` draws a 1-2 pixel border using the active/inactive color scheme:
- All windows: `WinColor.BORDER` (resolved from `Theme.border` via UITheme)

**Header:** `Win_DrawHeader` draws the title bar:
- Background fill: `window_bg` from Theme (or `WinColor.WINDOW` alias)
- Title text: window title string, left-aligned, 8px inset
- Close button: right side, × symbol, red-tinted on hover
- Minimize button: right side, − symbol
- Maximize button: right side, □ symbol

**Tab Bar:** `Win_DrawTabBar` draws stacked tabs when `WinStack_Get(idx) >= 0`:
- Tab background: `tab_active_bg` for active, `tabbar_bg` for inactive
- Tab close button: small × on each tab
- Tab text: window title truncated to TAB_MAX_W

### 4.4 `Win_RenderDirty` — Dirty Check

Returns 1 if any window's content surface has the dirty flag set (from Auckland `DrawDirty`). Used by the main loop to decide whether to force a full recompose even when `SysDisplayState.dirty` is 0.

---

## 5. WinStack — Tab Stacking

### 5.1 Role

WinStack provides a lightweight tab stacking system where multiple windows can be grouped into a single frame with a tab bar. Each stack holds up to 8 tabs.

### 5.2 Data Structure

```
StackTable[8] — 8 possible stacks, each 48 bytes:
    tab_surf    — Tab bar surface (rendered)
    tab_count   — Number of tabs in stack
    tab_bar_h   — Computed tab bar height
    active_win  — Which tab is active (0 = first)
    win_list    — Array of 8 window indices in this stack
    active      — Whether this stack slot is in use

WinStackMap[8] — Maps window index → stack index (-1 = not stacked)
```

### 5.3 Tab Bar Height Calculation

`Stack_CalcHeight(tab_count, canvas_w)`:
```
tabs_per_row = canvas_w / TAB_MAX_W
row_count = ceil(tab_count / tabs_per_row)
tab_bar_h = row_count * TAB_ROW_H
```

The tab bar height is dynamically computed based on window width and number of tabs. Windows too narrow to fit all tabs in one row will get a multi-row tab bar.

### 5.4 Stack Operations

- `Stack_Create(win_idx)` — Allocate new stack, add window as first tab
- Tab switching: change `active_win`, mark surface dirty
- Tab close: remove from list, destroy window if last tab
- Tab detach: remove from stack, create new standalone window

---

## 6. WinToolbar — Per-Window Toolbar

### 6.1 Role

WinToolbar creates and manages the Auckland-based toolbar for each window. The toolbar holds icon buttons (back, forward, home, etc.), an address bar, and menu trigger buttons (File, Edit, View, Help).

### 6.2 Toolbar Creation

Each window's toolbar is built as an Auckland tree:

```
WinToolbar_Create(idx):
    1. Surface_Create for toolbar pixels
    2. AK_CreateContext for toolbar Auckland tree
    3. Build node tree:
        Root (HBOX)
        ├── Back button (icon: arrow_left)
        ├── Forward button (icon: arrow_right)
        ├── Home button (icon: home)
        ├── Spacer (stretch)
        ├── Address bar (text input region)
        ├── Spacer
        ├── Menu:File button (text: "File")
        ├── Menu:Edit button (text: "Edit")
        ├── Menu:View button (text: "View")
        └── Menu:Help button (text: "Help")
    4. AK_Measure + AK_Layout + AK_Draw
    5. Store context handle in WinMgr
```

### 6.3 Toolbar Event Dispatch

`Win_ToolbarEvent(idx, x, y, event_type)`:
1. Save current Auckland context
2. Restore toolbar's Auckland context
3. AK_Event(x_local, y_local, event_type) — hit-test and dispatch into tree
4. If a button was clicked, the action callback fires → EventRouter_Push
5. Restore previous Auckland context

### 6.4 Toolbar Resize

`Win_ResizeToolbar(idx)` — Rebuilds toolbar layout after window resize:
1. Surface_Resize to new width (height stays constant)
2. AK_SetDesignW/AK_SetDesignH on toolbar context
3. AK_Measure + AK_Layout + AK_Draw

---

## 7. Theme Integration

Window decorations use the `Theme` FixedPool (from `UITheme`) to source all
colors. The `WinColor` struct provides shorthand aliases (`.BORDER`, `.WINDOW`)
that resolve to Theme fields at draw time.

| Theme Field | WinColor Alias | Usage |
|-------------|---------------|-------|
| `header_color` | — | Window title bar text color |
| `border` | `WinColor.BORDER` | Window border (1–2px) |
| `window_bg` | `WinColor.WINDOW` | Window content background fill |
| `text_fg` | — | Header/title text foreground |
| `text_secondary` | — | Dimmed/inactive text |
| `toolbar_bg` | — | Toolbar background |
| `toolbar_close_bg` | — | Close button fill |
| `toolbar_close_fg` | — | Close button × symbol |
| `toolbar_min_bg` | — | Minimize button fill |
| `toolbar_max_bg` | — | Maximize button fill |
| `tabbar_bg` | — | Tab bar background |
| `tab_active_bg` | — | Active tab highlight |
| `tab_text` | — | Tab label text |

All colors are overridable via `ui.cfg` key=value pairs loaded by
`UIConfig_GetInt` at `UITheme_Init` time.

---

## 8. DecorConfig

A sizing configuration shared across window management:

```
DecorConfig:
    header_h      — Title bar height (typically 24-28px, scale-aware)
    border_w      — Border width (1-2px)
    toolbar_h     — Toolbar height (typically 28-32px)
    button_w      — Header button width
    tab_max_w     — Maximum tab width
    tab_row_h     — Tab row height
    tab_icon_w    — Tab icon width
    tab_pad       — Tab padding
    min_w         — Minimum window width (typically 200px)
    min_h         — Minimum window height (typically 150px)
```

---

## 9. Dependencies

```
WinManager → DSurfaceTypes, DSurface, DDrawPixel, DComposeTypes,
             DComposeFloat, Cursor, CursorBitmap, UIConfig, UITheme,
             UIScale, WinStack, IPCBroker

WinInput → WinManager, DComposeFloat

WinRender → DSurfaceTypes, DSurface, DDrawPixel, DComposeFloat,
            WinManager, WinStack, Cursor, Deskbar, DebugLog, Fonts,
            TextRegion, UIScale, UITheme

WinStack → WinManager, UIScale

WinToolbar → DSurfaceTypes, DSurface, DDrawPixel, WinManager,
             Auckland, AucklandEvent, EventRouter, VIF
```
