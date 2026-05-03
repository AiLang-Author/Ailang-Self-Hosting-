# 04 — UI Framework: Auckland, AucklandBind, AucklandEvent, TextRegion, Dialogs

> **Copyright © 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.**

---

## 1. Overview

The UI Framework provides a complete retained-mode GUI toolkit built on the Auckland layout engine. It handles tree construction, measure/layout/draw passes, data binding, event dispatch, text rendering, and modal dialogs. The framework is self-contained and does not depend on any external UI library.

### Components

| Component | Source File | Lines | Role |
|-----------|------------|-------|------|
| **Auckland** | `Library.Auckland.ailang` | ~1500 | Layout engine: tree, measure, layout, draw |
| **AucklandBind** | `Library.AucklandBind.ailang` | ~700 | Data binding system |
| **AucklandEvent** | `Library.AucklandEvent.ailang` | ~400 | Mouse/key event dispatch, hit testing |
| **TextRegion** | `Library.TextRegion.ailang` | ~700 | Text rendering with wrapping/alignment |
| **PaneDecorator** | `Library.PaneDecorator.ailang` | ~100 | Window chrome decoration |
| **Dialog** | `Library.Dialog.ailang` | ~450 | Modal dialog system |
| **FileDialog** | `Library.FileDialog.ailang` | ~1200 | File browser dialog |
| **AboutDialog** | `Library.AboutDialog.ailang` | ~60 | About dialog |
| **NotepadApp** | `Library.NotepadApp.ailang` | ~150 | Simple text editor app |

---

## 2. Auckland — Layout Engine

### 2.1 Design Philosophy

Auckland is a **retained-mode** UI toolkit, meaning the UI is described as a persistent tree of nodes. Each frame, the engine performs measure → layout → draw passes. This contrasts with immediate-mode GUIs where UI is rebuilt every frame.

Key principles:
- **Box model**: Every node is a rectangle with margins, borders, padding, and content
- **VBOX/HBOX**: Primary layout containers (vertical and horizontal box)
- **Design space**: Layout is computed in a virtual "design" coordinate system, then scaled to physical pixels via `AK_Scale`
- **Dirty tracking**: Only nodes marked dirty are re-measured and re-drawn

### 2.2 Node Tree

```
AKNode (variable size, ~80-120 bytes per node):
    type          — Node type (VBOX, HBOX, TEXT, BUTTON, IMAGE, SPACER, INPUT, etc.)
    flags         — Visibility, dirty, expand, align flags
    parent        — Parent node index
    first_child   — First child node index
    next_sibling  — Next sibling index
    prev_sibling  — Previous sibling index
    child_count   — Number of children
    design_x, design_y, design_w, design_h  — Computed layout in design space
    margin[]      — MARGIN_TOP, RIGHT, BOTTOM, LEFT
    border[]      — BORDER_TOP, RIGHT, BOTTOM, LEFT
    padding[]     — PADDING_TOP, RIGHT, BOTTOM, LEFT
    min_w, min_h  — Minimum size constraints
    max_w, max_h  — Maximum size constraints
    expand_h      — Horizontal expansion weight (for HBOX)
    expand_v      — Vertical expansion weight (for VBOX)
    halign        — Horizontal alignment (LEFT, CENTER, RIGHT, STRETCH)
    valign        — Vertical alignment (TOP, CENTER, BOTTOM, STRETCH)
    action        — Action string (for buttons, inputs)
    text          — Text pointer (for text nodes)
    color_bg      — Background color
    color_fg      — Foreground/text color
    font_inst     — Font instance for text rendering
    surface       — Backing surface (for complex nodes)
    extra[]       — Type-specific extra data (variable size)
```

### 2.3 Contexts

Auckland operates within **contexts**. Each context is a self-contained UI tree with its own root, design size, and state:

```
AKContext (~200 bytes):
    tree_data      — Node array buffer
    tree_count     — Number of nodes
    tree_root      — Root node index
    design_w       — Design width (virtual pixels)
    design_h       — Design height (virtual pixels)
    scale_x        — Physical/design ratio
    scale_y        — Physical/design ratio
    focus_node     — Currently focused node
    action_cb      — Action callback function
    toolbar_mode   — Boolean: compact toolbar layout
    addressbar     — Address bar node reference
    dirty_count    — Number of nodes needing redraw
    dirty_list     — List of dirty node indices
```

Contexts are stored in a pool and identified by index. The display server maintains:
- **Desktop context** (ctx 0) — Global Auckland tree for deskbar, menus, dialogs
- **Per-window toolbar contexts** — One per window for toolbar UI
- **Per-window content contexts** — One per window for app content UI

### 2.4 Context Switching

The display server switches between Auckland contexts during event dispatch:

```
// Save current context
WinView_Save(desktop_ctx)

// Restore window's content context
WinView_Restore(window_idx)

// Dispatch event into window's tree
AK_Event(x, y, event_type)

// Save window context, restore desktop
WinView_Save(window_idx)
WinView_Restore(desktop_ctx)
```

This save/restore pattern ensures that event dispatch always operates on the correct tree and that modifications to one context don't leak into another.

### 2.5 Measure Pass (`AK_MeasureNode`)

Bottom-up pass that computes each node's preferred size:

```
AK_MeasureNode(node):
    switch node.type:
        HBOX:  measure all children, sum widths, max height
        VBOX:  measure all children, max width, sum heights
        TEXT:  measure text string at current font size
        BUTTON: measure like HBOX with button padding
        IMAGE: return image surface dimensions
        SPACER: return (0, 0) — expands to fill
        INPUT: measure like text with input field padding
    Apply min/max constraints
    Store measured_w, measured_h in node
```

### 2.6 Layout Pass (`AK_LayoutNode`)

Top-down pass that positions children within their parent:

```
AK_LayoutNode(node, x, y, allocated_w, allocated_h):
    Set node.design_x, design_y, design_w, design_h
    Compute content area = allocated - margin - border - padding
    switch node.type:
        HBOX: distribute content_w among expand_h children
        VBOX: distribute content_h among expand_v children
    For each child: AK_LayoutNode(child, child_x, child_y, child_w, child_h)
```

### 2.7 Draw Pass (`AK_DrawNode`)

Renders each node to its backing surface or parent surface:

```
AK_DrawNode(node, surface):
    if not dirty: return
    Draw background (color_bg)
    Draw border
    switch node.type:
        TEXT: TextRegion_Render(text, font_inst, color_fg)
        IMAGE: Surface_BlitAlpha(surface, image_surf, x, y)
        *:     Draw children
    Mark clean
```

### 2.8 Key Functions

| Function | Description |
|----------|-------------|
| `AK_CreateContext(w, h)` | Allocate new Auckland context |
| `AK_DestroyContext(ctx)` | Free context and all nodes |
| `AK_ResetContext(ctx)` | Clear tree, keep context alive |
| `AK_CreateNode(ctx, parent, type)` | Create node, add to parent |
| `AK_AddChild(ctx, parent, child)` | Add existing node as child |
| `AK_SetRoot(ctx, node)` | Set context root node |
| `AK_Scale(ctx)` | Compute scale from design→physical |
| `AK_Solve(ctx)` | Full measure+layout pass |
| `AK_Draw(ctx)` | Full draw pass (dirty nodes only) |
| `AK_ClearChildren(ctx, node)` | Remove all children of node |
| `AK_AllocExtra(node, size)` | Allocate type-specific extra data |

---

## 3. AucklandBind — Data Binding

### 3.1 Role

AucklandBind connects Auckland UI nodes to data sources. When data changes, bound nodes are automatically marked dirty and re-rendered. This implements a simple unidirectional data flow: data → UI.

### 3.2 Binding Model

```
Binding:
    source        — Data source identifier
    path          — Property path within source
    target_node   — Target Auckland node
    target_prop   — Target property on node (text, color, visibility, etc.)
    transform     — Optional transform function
```

### 3.3 Supported Bindings

| Target Property | Node Types | Description |
|----------------|------------|-------------|
| `text` | TEXT, BUTTON, INPUT | Update displayed text |
| `color_bg` | All | Update background color |
| `color_fg` | TEXT, BUTTON | Update text color |
| `visible` | All | Show/hide node |
| `action` | BUTTON | Update action string |
| `image` | IMAGE | Update image surface |
| `value` | INPUT, SLIDER | Update input value |

### 3.4 Update Cycle

```
Bindings_Refresh():
    For each binding:
        new_value = DataSource_Get(source, path)
        if new_value != cached_value:
            Apply to target node
            Mark node dirty
            cached_value = new_value
```

---

## 4. AucklandEvent — Event System

### 4.1 Role

AucklandEvent handles mouse and keyboard event dispatch within an Auckland context. It performs hit-testing against the node tree and routes events to the appropriate node.

### 4.2 Event Types

```
AKMouseEv:
    MOVE   = 0    — Mouse moved
    DOWN   = 1    — Mouse button pressed
    UP     = 2    — Mouse button released
    WHEEL  = 3    — Mouse wheel scrolled

AKKeyEv:
    DOWN   = 0    — Key pressed
    UP     = 1    — Key released
    CHAR   = 2    — Character input (after key mapping)
```

### 4.3 Hit Testing

`AKEvent_HitTest(ctx, x, y)` walks the tree top-down, checking each node's layout bounds. The deepest matching node wins. Hit testing is done in physical pixel coordinates (after `AK_Scale`).

### 4.4 Event Dispatch

```
AK_Event(ctx, x, y, ev_type, data):
    hit_node = AKEvent_HitTest(ctx, x, y)
    if hit_node >= 0:
        switch ev_type:
            MOUSE_DOWN: AK_SetFocus(ctx, hit_node)
            MOUSE_UP:   if hit_node == focus_node and has action:
                            AK_FireAction(ctx, hit_node)
            KEY_DOWN:   if has focus_node and is INPUT:
                            AK_InputChar(ctx, focus_node, data)
```

### 4.5 Fire Action

`AK_FireAction(ctx, node)` reads the node's `action` string and calls the context's `action_cb`. This is the bridge between Auckland events and the EventRouter action queue.

---

## 5. TextRegion — Vector Text Rendering

### 5.1 Role

TextRegion renders multi-line text with wrapping, alignment, and styling using the vector font engine. Unlike simple character-cell text, TextRegion supports proportional fonts, kerning, and anti-aliased glyph rasterization.

### 5.2 TextRegion Object

```
TextRegion:
    surface       — Target surface
    x, y          — Position on surface
    w, h          — Bounding box
    font_inst     — Font instance (size + face)
    color         — Text color (RGBA packed)
    wrap          — Word-wrap enabled (0 or 1)
    halign        — Horizontal alignment (LEFT, CENTER, RIGHT)
    valign        — Vertical alignment (TOP, CENTER, BOTTOM)
    line_spacing  — Extra spacing between lines
    text          — Current text string
```

### 5.3 Key Functions

| Function | Description |
|----------|-------------|
| `TextRegion_Init()` | Initialize subsystem |
| `TextRegion_Create(surf, x, y, w, h)` | Create text region |
| `TextRegion_Destroy(tr)` | Free text region |
| `TextRegion_SetColor(tr, color)` | Set text color |
| `TextRegion_SetWrap(tr, wrap)` | Enable/disable word wrap |
| `TextRegion_SetAlign(tr, h, v)` | Set alignment |
| `TextRegion_Render(tr, str, len)` | Render text string |
| `TextRegion_Measure(tr, str, len)` | Measure text dimensions |

### 5.4 Rendering Algorithm

```
TextRegion_Render(tr, str, len):
    1. Clear bounding box area with transparent pixels
    2. Split text into words/lines based on wrap setting
    3. For each line:
        a. Measure line width
        b. Compute x offset based on halign
        c. For each glyph in line:
            glyph_surf = VInst_GetGlyphSurf(font_inst, codepoint)
            Surface_BlitAlpha(surface, glyph_surf, x + pen_x, y)
            pen_x += glyph_advance
        d. y += line_height + line_spacing
```

---

## 6. PaneDecorator — Window Chrome

### 6.1 Role

PaneDecorator renders the visual chrome around window content: borders, title bar with text, and the close/minimize/maximize button row. It draws directly to the window's header surface.

### 6.2 Decoration Elements

- **Title bar background**: Filled rectangle using HEADER_BG color
- **Title text**: Left-aligned, 8px indent, using vector fonts
- **Close button**: Right-aligned, red hover highlight
- **Minimize/Maximize buttons**: Right of close button
- **Border**: 1-2px line around window perimeter

---

## 7. Dialog — Modal System

### 7.1 Role

Dialog provides a modal overlay system. When a dialog is open, it captures all input events until dismissed. Dialogs render on top of all windows in z-order.

### 7.2 Dialog State

```
DialogState:
    open          — Is any dialog open?
    type          — Current dialog type
    surface       — Dialog pixel surface
    x, y, w, h    — Dialog position and size
    result        — Dialog result value
    callback      — Result callback function
```

### 7.3 FileDialog

FileDialog is a full file browser with:
- **Navigation**: Directory tree, path breadcrumbs, back/forward
- **File list**: Scrollable list with icons, names, sizes, dates
- **Actions**: Open, Cancel, Select, New Folder
- **Backed by PostgreSQL**: Reads from the `files` table
- **Action prefix**: `fd.nav`, `fd.select`, `fd.back`, `fd.cancel`, `fd.ok`

### 7.4 AboutDialog

Simple modal showing:
- "AILANG Display System" title
- Version information
- Copyright notice
- Close button → fires `about.close` action

### 7.5 NotepadApp

A minimal text editor demonstrating the Auckland+TextRegion integration:
- Single TEXT input node with multi-line support
- Menu bar with File (New, Open, Save) and Edit actions
- Uses registered handlers for `doc.new`, `doc.open`, `doc.save`

---

## 8. Dependencies

```
Auckland → DSurface, DDrawPixel, TextRegion, Fonts, VIF, JSON
AucklandBind → Auckland
AucklandEvent → Auckland
TextRegion → Fonts, VIF, DSurface, SurfaceBlit
PaneDecorator → DSurface, DDrawPixel, UITheme
Dialog → Auckland, AucklandEvent, DSurface, UITheme
FileDialog → Dialog, Auckland, AucklandEvent, PostgreSQL_Complete, UIConfig
AboutDialog → Dialog, Auckland
NotepadApp → Auckland, AucklandEvent, TextRegion
```
