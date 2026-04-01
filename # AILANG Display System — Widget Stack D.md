# AILANG Display System — Widget Stack Design
*Author: Sean Collins, 2 Paws Machine and Engineering*
*Version: 1.0 — March 31, 2026*

---

## The Problem This Solves

Protocol translation (BeAPI, Wayland, X11) requires mapping foreign draw calls to AILANG primitives. A monolithic design fights this. An orthogonal, bounded design lets each protocol's calls land in the right layer without interference.

```
Wayland wl_surface.attach    → Canvas widget (pixel buffer)
Haiku BTextView              → TextGrid widget → TextBuffer
Wayland wl_shell_surface     → BSP leaf + decorator
Haiku BWindow                → BSP leaf + decorator
X11 XDrawString              → Canvas or TextGrid
```

---

## Layer Stack

```
┌─────────────────────────────────────────┐
│  Protocol Shims                         │
│  BeAPI / Wayland / X11                  │
├─────────────────────────────────────────┤
│  Widget Layer                           │
│  Canvas  TextGrid  Label  Button  Panel │
├─────────────────────────────────────────┤
│  TextBuffer                             │
│  char grid, key input, render           │
├─────────────────────────────────────────┤
│  Surface Pipeline                       │
│  PIXEL_32 surface → RenderFB → FB       │
├─────────────────────────────────────────┤
│  BSP Compositor                         │
│  split / merge / focus / Ring0          │
├─────────────────────────────────────────┤
│  Framebuffer + Input                    │
│  /dev/fb0  /dev/input/eventX            │
└─────────────────────────────────────────┘
```

---

## TextBuffer (Day 5 — Implemented)

**File**: `Library.TextBuffer.ailang`

Fixed-grid character buffer. Owns data, render, and key input translation. Does NOT own positioning.

```
TextBuffer_Create(surf, font)    → handle
TextBuffer_KeyDown(handle, key, shift)
TextBuffer_PutChar(handle, ch)
TextBuffer_PutString(handle, str)
TextBuffer_Render(handle)        → draws into surface
TextBuffer_Destroy(handle)
```

Grid model: `cols = surface_w / char_w`, `rows = surface_h / char_h`.
Scroll: `TextBuffer_ScrollUp()` — shifts all rows up, clears bottom.
Cursor: block cursor, inverted colors at current position.

---

## Widget Layer (Planned)

Each widget type is a thin layer over a TextBuffer or surface. Handles positioning and hit testing. Does NOT own the surface — the BSP leaf owns the surface.

### Widget.TextGrid
Wraps TextBuffer. Adds:
- Margin/padding within pane
- Focus border highlight
- Title bar (optional, thin)

### Widget.Canvas
Free pixel drawing surface. Maps to `Draw_Pix_*` calls.
For Wayland `wl_surface` and Haiku `BView` direct draw.

### Widget.Label
Single-line text, positioned, no input.

### Widget.Button
Label + hit region. Posts to Ring1 on click.

### Widget.Panel
Container for other widgets. Handles layout within a pane.

---

## Pane ↔ Widget Binding

Currently a BSP leaf owns one surface. The widget layer adds a mapping:

```
BSP leaf → WinTable entry → surface → Widget handle
```

A `WidgetTable` (mirrors WinTable structure) maps leaf → widget type + handle.
When a pane is focused and a key arrives, the compositor looks up the widget and calls its key handler.

---

## Key Input Flow (Current → Widget)

**Current** (Day 5):
```
Ring1 KEY_DOWN → DrainRing1BSP → hotkey check (Alt+V etc) → discard
```

**With TextBuffer**:
```
Ring1 KEY_DOWN → DrainRing1BSP → hotkey check
                                → if not hotkey: TextBuffer_KeyDown(focused_tb, key, shift)
                                → TextBuffer_Render(focused_tb)
                                → mark pane dirty → BlitAllSurfaces
```

**With Widget layer**:
```
Ring1 KEY_DOWN → DrainRing1 → hotkey check
                             → Widget_KeyDown(focused_widget, key, shift)
                             → dispatches to widget type handler
                             → mark dirty
```

---

## Protocol Translation Points

### BeAPI → TextBuffer
```
BTextView::Insert(text)   → TextBuffer_PutString(handle, text)
BTextView::KeyDown(ch)    → TextBuffer_PutChar(handle, ch)
BTextView::Invalidate()   → TextBuffer_Render(handle) + Ring2 post
```

### Wayland → Canvas
```
wl_surface.attach(buffer) → copy pixel buffer to Canvas surface
wl_surface.damage(rect)   → Ring3_MarkDirty(surf, rect)
wl_surface.commit()       → compositor tick picks it up
```

### X11 → Canvas or TextGrid
```
XDrawString(dpy, win, gc, x, y, str, len)
  → FontBitmap_DrawString(canvas_surf, font, x, y, str, color)
XFillRectangle → Draw_Pix_FillRect
XCopyArea      → surface blit
```

---

## Implementation Order

1. **TextBuffer** ✅ — Day 5
2. **Wire TextBuffer to focused pane** — TestWindowBSP: type in a pane
3. **Widget.TextGrid** — thin wrapper, focus border
4. **WidgetTable** — BSP leaf → widget binding
5. **Widget.Canvas** — pixel draw surface
6. **Protocol shim seams** — BeAPI first (Haiku affinity)

---

## Design Invariants

- Each layer only calls the layer below it, never above
- No layer knows about protocol details above it
- Surface pipeline is the universal output — everything becomes pixels in a surface
- BSP compositor is layout authority — widgets don't move themselves
- Ring0 is the only path to BSP changes — no direct BSP mutation from widget code

*Copyright © 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.*