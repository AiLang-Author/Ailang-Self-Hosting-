# Auckland Layout Model — Complete Specification v1.0
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.

---

## 1. Purpose

Auckland is the layout engine for the 2 Paws platform. It takes a tree of UI elements described in HTML-subset markup, computes their positions and sizes using linear constraints on tabstops, and hands each element a rectangle to draw into. One markup definition produces correct layout at any window size, any DPI, any scale factor — from phone to 4K monitor — with no breakpoints, no responsive mode switching, and no redesign.

Auckland is not a web browser engine. It borrows HTML syntax because every developer on earth already knows it. It borrows CSS box model concepts because they're correct. It does not implement the full HTML/CSS specification. It implements the subset that matters for application UI.

---

## 2. Core Principles

1. **One UI, every screen.** The same markup renders on a 480px phone, a 1080p laptop, and a 4K desktop. Constraints scale. Vectors re-render. No asset variants. No layout breakpoints.

2. **Continuous scaling, not discrete.** The scale factor is a real number derived from window geometry. There are no "mobile" and "desktop" modes. There is one mode that smoothly adapts.

3. **DPI is invisible to applications.** The app declares sizes in logical units. The platform converts to physical pixels per zone. Moving a window between monitors triggers automatic re-render.

4. **Constraints, not coordinates.** Applications never specify pixel positions. They declare relationships: "this is to the right of that," "these share equal width," "this group is a 4-column grid." Auckland solves for positions.

5. **Vectors make it free.** Widget assets are TinyVG. Font glyphs are TinyVG. Re-rendering at a new scale costs one rasterization pass — the same pipeline that already runs at startup. No scaling artifacts, no blurry bitmaps, no @2x assets.

---

## 3. Architecture Position

```
┌─────────────────────────────────────────────┐
│  Application Markup (HTML-subset)            │
│  Tags, attributes, action= bindings         │
├─────────────────────────────────────────────┤
│  Auckland Layout Model                       │
│  Parse markup → build element tree →         │
│  generate constraints → solve → assign rects │
├─────────────────────────────────────────────┤
│  Widget Renderer                             │
│  Each element draws into its assigned rect   │
│  using VIF/TVG rasterizer + SurfaceBlit      │
├─────────────────────────────────────────────┤
│  Window Canvas (one PIXEL_32 surface)        │
│  All widgets draw into this single surface   │
├─────────────────────────────────────────────┤
│  Compositor                                  │
│  Opaque blit canvas to framebuffer           │
└─────────────────────────────────────────────┘
```

Auckland sits between markup and rendering. It consumes a tree of elements and produces a flat list of rectangles. Rendering is not Auckland's job — it only computes geometry.

---

## 4. Units and Coordinate System

### 4.1 Logical Units (lu)

All sizes in markup and constraints are in **logical units**. One logical unit equals one pixel at 96 DPI, scale factor 1.0. This is the reference coordinate system.

Conversion to physical pixels:

```
physical_px = logical_units * zone_dpi / 96
```

Or equivalently using the zone's integer scale ratio:

```
physical_px = logical_units * scale_num / scale_den
```

### 4.2 Point Sizes for Text

Font sizes are specified in points (pt). Conversion:

```
logical_px = pt * dpi / 72
```

At 96 DPI: 12pt = 16 logical px. At 256 DPI: 12pt = 42.67 → 43 physical px.

The font pipeline handles this — `VFont_RasterAll(pixel_size)` re-renders all glyphs at the target size. Auckland just computes the pixel_size and passes it down.

### 4.3 Coordinate Origin

(0, 0) is top-left of the window's client area (inside decorator). X increases right. Y increases down. Applications never know their screen position — they only see (0, 0) to (canvas_w, canvas_h).

---

## 5. Scale Factor Model

### 5.1 Computation

Every window has a **design size** — the logical dimensions the markup was authored for. The scale factor is derived from the actual window size relative to the design size:

```
scale_x = current_w / design_w
scale_y = current_h / design_h
scale = min(scale_x, scale_y)
scale = clamp(scale, min_scale, max_scale)
```

Using the minimum preserves aspect ratio. The remaining space (if any) is handled by alignment constraints.

### 5.2 Scale Limits

```html
<window title="Calculator" design-w="320" design-h="480"
        min-scale="0.5" max-scale="3.0">
```

Below `min_scale`: window clips content instead of shrinking further. Scrollbars appear if content overflows.

Above `max_scale`: content centers in the available space. No further enlargement.

Default limits: `min_scale="0.4"` `max_scale="4.0"`

### 5.3 What Scales

When the scale factor changes, these things happen in order:

1. **Constraint re-solve.** All margins, paddings, gaps, and fixed sizes are multiplied by the scale factor. The solver runs once. New rectangles are produced.

2. **VIF sprite sheet regeneration.** Every widget asset (button, scrollbar, checkbox) is re-rasterized from TinyVG source at `base_size * scale`. The sprite sheet cache is rebuilt.

3. **Font re-rasterization.** `VFont_FlushCache()` then `VFont_RasterAll(new_pixel_size)`. Glyphs re-render from TVG vectors at the new size.

4. **Canvas redraw.** Every element redraws into its new rectangle on the window canvas. One

5. **Compositor blit.** Canvas blits to framebuffer. Done.

Total cost: one constraint solve + one VIF re-render pass + one font re-render pass + one canvas redraw. All of these are fast because vectors render at O(edges), not O(pixels²).

### 5.4 DPI-Aware Zone Transitions

When a window moves between zones with different DPI:

```
Zone A: 1920×1080, 96 DPI, scale_num=1, scale_den=1
Zone B: 3840×2160, 256 DPI, scale_num=8, scale_den=3
```

1. Compositor detects zone transition during drag
2. New physical dimensions computed: `logical_size * new_scale_num / new_scale_den`
3. Scale factor recalculated against design size
4. Steps 1-5 from section 5.3 execute
5. Window appears at correct physical size on new monitor — no visible size jump

A 320×480 logical unit calculator window:
- Zone A (96 DPI): 320×480 physical pixels
- Zone B (256 DPI): 853×1280 physical pixels
- Same logical size. Same layout. Same proportions. Different pixel count.

---

## 6. HTML-Subset Markup

### 6.1 Design Philosophy

The markup is declarative UI definition. It is **not** a document format. There is no text flow, no inline elements wrapping across lines, no float/clear. It is a tree of rectangular containers and leaf widgets.

Think of it as: "HTML for app layout, not HTML for web pages."

### 6.2 Supported Tags

#### Container Tags

```
<window>      — Root element. One per application UI.
<group>       — Generic container. Holds children in a layout.
<panel>       — Visual container with optional border/background.
<scroll>      — Scrollable viewport into content larger than its rect.
<tabs>        — Tab container. Children are tab pages.
<tab>         — Single tab page within <tabs>.
```

#### Widget Tags (Leaf Elements)

```
<button>      — Clickable button. VIF widget asset, 5 states.
<label>       — Static text. TextRegion rendering.
<text>        — Editable text input. TextRegion + cursor + selection.
<display>     — Multi-line read-only text display (calculator screen, log view).
<checkbox>    — Toggle. VIF widget asset.
<radio>       — Radio button group member. VIF widget asset.
<slider>      — Value slider. VIF widget asset.
<progress>    — Progress bar. VIF widget asset.
<image>       — Displays a VIF/TVG vector image.
<canvas>      — Raw drawing surface. App draws via callback.
<spacer>      — Invisible element that consumes space in layout.
<separator>   — Visual divider line.
```

### 6.3 Common Attributes

#### Identity and Binding

```
id="name"                — Unique element identifier for binding/action targets
action="service.method"  — Fires action pool message on interaction
bind="element.property"  — Data binding: action result updates this property
visible="true|false"     — Visibility toggle. Hidden elements excluded from layout.
enabled="true|false"     — Disabled elements render in DISABLED state, ignore input.
```

#### Layout Attributes

```
layout="vbox|hbox|grid|flow"  — Child arrangement (containers only)
cols="N"                       — Column count for grid layout
rows="N"                       — Row count for grid layout (optional, auto-computed)
gap="N"                        — Space between children (logical units)
padding="N"                    — Internal spacing (logical units)
padding="T R B L"              — Per-side padding
align="start|center|end|stretch" — Cross-axis alignment
justify="start|center|end|space-between|space-around" — Main-axis distribution
```

#### Sizing Attributes

```
width="N"          — Fixed width (logical units)
height="N"         — Fixed height (logical units)
min-width="N"      — Minimum width
min-height="N"     — Minimum height
max-width="N"      — Maximum width
max-height="N"     — Maximum height
grow="N"           — Flex grow factor (default 0)
shrink="N"         — Flex shrink factor (default 1)
basis="N|auto"     — Flex basis size
```

#### Visual Attributes

```
bg="color"         — Background color (hex: #1A3A5C or named)
fg="color"         — Foreground/text color
border="N"         — Border width (logical units)
border-color="color"
font="name"        — Font family name (matches loaded VIF font)
font-size="Npt"    — Font size in points
font-weight="normal|bold"
text-align="left|center|right"
```

### 6.4 Tag Reference

#### `<window>`

Root container. One per application. Defines design size and scale limits.

```html
<window title="Scientific Calculator"
        design-w="360" design-h="540"
        min-scale="0.5" max-scale="3.0"
        bg="#1A1A2E">
  <!-- all UI content -->
</window>
```

**Attributes:**
- `title` — Window title (shown in decorator tab)
- `design-w`, `design-h` — Design dimensions in logical units
- `min-scale`, `max-scale` — Scale factor bounds
- `bg` — Window background color

#### `<group>`

Generic container. No visual presence by default. Used purely for layout.

```html
<group layout="hbox" gap="8" padding="12">
  <button label="OK" />
  <button label="Cancel" />
</group>
```

#### `<panel>`

Container with visual presence — background fill and optional border.

```html
<panel bg="#2A2A3E" border="1" border-color="#555" padding="16">
  <label text="Settings" font-size="14pt" />
  <checkbox label="Enable sound" id="sound-toggle" />
</panel>
```

#### `<scroll>`

Scrollable viewport. Content can be larger than the scroll element's assigned rectangle. Scrollbar widgets are auto-generated.

```html
<scroll height="300">
  <group layout="vbox">
    <!-- many items that exceed 300lu height -->
  </group>
</scroll>
```

The scroll element manages a viewport offset internally. The content draws into a surface sized to fit all children. `Surface_BlitRegion` shows the visible portion. Scrollbar widgets (VIF assets) are composited at the edge.

#### `<tabs>` and `<tab>`

Tabbed container. Each `<tab>` child is a page. Only the active tab's content is drawn.

```html
<tabs id="mode-tabs">
  <tab label="Basic">
    <group layout="grid" cols="4"> ... </group>
  </tab>
  <tab label="Scientific">
    <group layout="grid" cols="5"> ... </group>
  </tab>
</tabs>
```

Tab headers are VIF widget assets. Clicking a tab header switches the active page. Auckland re-solves constraints for the new tab's content (or uses cached solution if tab size hasn't changed).

#### `<button>`

Clickable button. Renders from VIF widget sprite sheet (5 states).

```html
<button label="7" action="digit:7"
        width="64" height="64"
        font-size="18pt" />
```

**States:** NORMAL, HOVER, PRESSED, DISABLED, CHECKED
**Events:** action fires on click (mouse-up within bounds)

#### `<label>`

Static text. Renders via TextRegion into its assigned rectangle.

```html
<label text="Total:" font-size="12pt" fg="#CCCCCC"
       text-align="right" />
```

#### `<text>`

Editable text input. TextRegion + cursor + selection handling.

```html
<text id="search-input" placeholder="Search..."
      font-size="12pt" width="200" height="28"
      action="search:query" />
```

Action fires on Enter. `bind="search-input.value"` on another element receives the text content.

#### `<display>`

Multi-line read-only text area. For calculator screens, log views, output panels.

```html
<display id="screen" rows="2" font="DejaVuSansMono"
         font-size="24pt" bg="#0D1117" fg="#00FF88"
         text-align="right" />
```

`rows` determines the height in text lines. Content scrolls if it exceeds row count.

#### `<canvas>`

Raw drawing surface. The application draws into it via a registered callback.

```html
<canvas id="plot" width="400" height="300"
        plugin="graphing.x" />
```

The plugin receives the canvas surface handle and dimensions. Auckland places it. The plugin draws whatever it wants inside the bounds.

#### `<spacer>`

Invisible layout element. Consumes space to push siblings apart.

```html
<group layout="hbox">
  <label text="Left" />
  <spacer grow="1" />
  <label text="Right" />
</group>
```

#### `<separator>`

Visual divider. Horizontal in vbox, vertical in hbox.

```html
<group layout="vbox">
  <label text="Section 1" />
  <separator />
  <label text="Section 2" />
</group>
```

Renders as a 1lu line in the border color.

---

## 7. Layout Algorithm

### 7.1 Layout Modes

Each container has a layout mode that determines how children are positioned.

#### `vbox` — Vertical Box

Children stack top to bottom. Each child gets the full container width (or its own width if smaller). Heights are distributed based on flex properties.

```
┌──────────────┐
│   Child A    │
├──────────────┤
│   Child B    │
├──────────────┤
│   Child C    │
└──────────────┘
```

#### `hbox` — Horizontal Box

Children stack left to right. Each child gets the full container height (or its own height if smaller). Widths are distributed based on flex properties.

```
┌────┬────┬────┐
│ A  │ B  │ C  │
└────┴────┴────┘
```

#### `grid` — Grid

Children placed in a grid with `cols` columns. Rows auto-computed. All cells in a column share width. All cells in a row share height. Children fill cells in reading order (left to right, top to bottom).

```
cols="3":
┌────┬────┬────┐
│ 1  │ 2  │ 3  │
├────┼────┼────┤
│ 4  │ 5  │ 6  │
├────┼────┼────┤
│ 7  │ 8  │ 9  │
└────┴────┴────┘
```

Grid cells are equal-width by default. Individual children can specify `grow` to claim more space within their column, but column widths are uniform unless overridden.

#### `flow` — Flow Layout

Children placed left to right, wrapping to next row when container width is exceeded. For tag clouds, icon grids, dynamic content where item count varies.

```
┌────┬────┬────┐
│ A  │ B  │ C  │
├────┼────┼────┘
│ D  │ E  │
└────┴────┘
```

### 7.2 Flex Distribution

For `vbox` and `hbox`, space is distributed using flex properties modeled on CSS Flexbox (simplified):

**Phase 1 — Base sizes:**
- Elements with explicit `width`/`height`: use that value (scaled by scale factor)
- Elements with `basis="auto"`: use intrinsic size (measured content)
- Elements with `basis="N"`: use N logical units

**Phase 2 — Remaining space:**
- Sum base sizes + gaps. Remaining = container_size - sum.
- If remaining > 0: distribute proportionally to `grow` factors
- If remaining < 0: shrink proportionally to `shrink` factors, respecting `min-width`/`min-height`

**Phase 3 — Alignment:**
- `align` controls cross-axis position (e.g., vertical position in hbox)
- `justify` controls main-axis distribution when there's leftover space after flex

### 7.3 Constraint Generation

Auckland converts the element tree + layout attributes into linear constraints on tabstops.

A **tabstop** is a named position on either the X or Y axis. Every element has four tabstops: `left`, `right`, `top`, `bottom`.

Constraints are linear equations:

```
element.left   = parent.left + parent.padding_left + offset
element.right  = element.left + element.width
element.top    = prev_sibling.bottom + gap
element.bottom = element.top + element.height
```

For a 4-column grid:

```
col_width = (parent.content_width - 3 * gap) / 4
child[0].left  = parent.content_left
child[0].right = child[0].left + col_width
child[1].left  = child[0].right + gap
child[1].right = child[1].left + col_width
...
```

The solver resolves all tabstop values in a single pass (topological order — parent before children, siblings in layout order). This is not an iterative constraint solver like Cassowary — the constraints form a DAG, so one pass suffices.

### 7.4 Solve Order

```
1. Parse markup → build element tree
2. Measure intrinsic sizes (bottom-up)
   - Leaf elements: measure text, widget asset size, explicit dimensions
   - Containers: sum children sizes + gaps + padding
3. Solve constraints (top-down)
   - Root element: assigned window client rect
   - Each container: distribute available space to children per layout mode
   - Each child: compute left, right, top, bottom tabstops
4. Apply scale factor
   - All solved positions and sizes multiplied by current scale
5. Output: flat list of (element_id, x, y, w, h) tuples
```

### 7.5 Incremental Re-solve

Auckland caches the element tree and constraint graph. On window resize:

1. Recompute scale factor
2. Re-solve constraints with new root dimensions (one pass)
3. Diff against previous solution — only elements that moved or resized are marked dirty
4. Dirty elements redraw. Clean elements are untouched.

On visibility toggle (`visible="false"` → `visible="true"`):

1. Insert/remove element from constraint graph
2. Re-solve affected branch only (siblings and parent)
3. Redraw affected region

---

## 8. Tabstop System

### 8.1 Definition

A tabstop is a named integer coordinate on one axis. Every element defines tabstops. The solver assigns values to all tabstops.

```
Element "btn_ok":
    tab_left   = 120
    tab_right  = 200
    tab_top    = 340
    tab_bottom = 380
```

The element's assigned rectangle is:
```
x = tab_left
y = tab_top
w = tab_right - tab_left
h = tab_bottom - tab_top
```

### 8.2 Tabstop Algebra

Constraints are expressed as relationships between tabstops:

```
A.left = B.right + gap          — A starts where B ends, plus gap
A.width = B.width               — A and B have equal width
A.center_x = parent.center_x   — A is horizontally centered in parent
A.right = parent.right - padding — A's right edge is padded from parent
```

Center tabstops are derived: `center_x = (left + right) / 2`

### 8.3 Named Tabstops

Applications can declare custom tabstops for cross-branch alignment:

```html
<window>
  <group layout="vbox">
    <group layout="hbox">
      <label text="Name:" width="80" />
      <text id="name-input" tabstop-left="form-field-left" grow="1" />
    </group>
    <group layout="hbox">
      <label text="Email:" width="80" />
      <text id="email-input" tabstop-left="form-field-left" grow="1" />
    </group>
  </group>
</window>
```

Both inputs share the named tabstop `form-field-left`, so they align vertically regardless of label widths. The solver adds: `name-input.left = email-input.left = form-field-left`.

---

## 9. Rendering Pipeline

### 9.1 Canvas Ownership

Each window has **one** PIXEL_32 surface — the canvas. All elements draw into this single surface. There is no layer stack, no per-element surfaces, no compositor between elements.

Elements draw in tree order (pre-order traversal). Parent draws first (background), then children draw on top. Painter's algorithm. Last writer wins.

### 9.2 Element Rendering

Each element type has a draw function that receives:
- Canvas surface handle
- Assigned rectangle (x, y, w, h) from Auckland
- Element state (normal, hover, pressed, disabled, checked)
- Element properties (colors, text content, font, etc.)

```
Auckland_Solve() → rect_list
for each (element, rect) in rect_list:
    element.draw(canvas, rect.x, rect.y, rect.w, rect.h)
```

### 9.3 Widget Rendering via VIF

Widget elements (button, checkbox, slider, etc.) render from VIF sprite sheet:

1. At startup or scale change: rasterize each widget × each state from TinyVG at `base_size * scale` → cache as sprite sheet
2. Per frame: `Surface_BlitOpaque(canvas, sprite_sheet, src_rect, dst_rect)` — one blit per widget
3. State change (hover, press): change `src_rect` offset in sprite sheet. No re-rasterization.

### 9.4 Text Rendering via TextRegion

Text elements (label, text, display) render via TextRegion:

1. TextRegion receives canvas handle, assigned rectangle, text content, font, color, alignment
2. TextRegion calls `VFont_DrawString` to blit tinted glyph surfaces into the canvas
3. Word wrap respects rectangle width. Overflow clips at rectangle bottom.

### 9.5 Dirty Region Optimization

Auckland tracks which elements changed. On a state change (hover, text edit, visibility toggle):

1. Mark affected elements dirty
2. Redraw dirty elements and any elements that overlap their rectangles
3. Compositor blits the canvas to framebuffer

Full canvas redraw only happens on window resize or scale change. Most frames only redraw the elements that actually changed.

---

## 10. Event Routing

### 10.1 Hit Testing

Input events arrive with (x, y) coordinates in window-local space. Auckland performs hit testing against the solved rectangle list.

Hit test is a reverse pre-order traversal (deepest, last-drawn element first). The first element whose rectangle contains (x, y) is the hit target.

For overlapping elements (e.g., a button inside a panel inside a group), the deepest child wins.

### 10.2 Event Types

```
MOUSE_ENTER   — cursor entered element rect
MOUSE_LEAVE   — cursor left element rect
MOUSE_DOWN    — button pressed within element rect
MOUSE_UP      — button released within element rect
CLICK         — MOUSE_DOWN + MOUSE_UP within same element
KEY_DOWN      — keyboard key pressed (routed to focused element)
KEY_UP        — keyboard key released
TEXT_INPUT    — character input (routed to focused text element)
FOCUS_IN      — element received keyboard focus
FOCUS_OUT     — element lost keyboard focus
VALUE_CHANGE  — slider/checkbox value changed
```

### 10.3 Action Dispatch

When an element with `action="service.method"` receives a CLICK event:

1. Auckland constructs an action pool message with the element's current state/value
2. Posts to the application's action pool channel
3. Service Manager routes to the appropriate service (light tier: LISTEN/NOTIFY, heavy tier: job queue)
4. Result returns with batch_id
5. If a `bind="target.property"` exists, Auckland updates the target element and marks it dirty

---

## 11. DPI and Cross-Monitor Behavior

### 11.1 Zone DPI

Each compositor zone has a DPI value and integer scale ratio:

```
Zone 0: 1920×1080, 96 DPI,  scale 1:1
Zone 1: 3840×2160, 192 DPI, scale 2:1
Zone 2: 2560×1440, 144 DPI, scale 3:2
```

### 11.2 Window on Zone Transition

When a window moves from Zone 0 (96 DPI) to Zone 1 (192 DPI):

1. **Logical size unchanged.** A 360×540 logical unit window stays 360×540 logical units.
2. **Physical size doubles.** 360×540 → 720×1080 physical pixels.
3. **Scale factor recalculated.** New physical dimensions / design dimensions.
4. **Constraint re-solve.** Margins, gaps, padding scale to new physical pixels.
5. **VIF re-render.** Widget assets rasterize at 2× size from TinyVG source.
6. **Font re-render.** `VFont_FlushCache()` + `VFont_RasterAll(new_px_size)`. Glyphs re-render from TVG vectors.
7. **Canvas resize.** New physical-pixel-sized surface allocated.
8. **Full redraw.** All elements draw into new canvas at new scale.
9. **One frame.** No flicker, no layout jump, no visible transition artifact.

The user sees: a window that is the same physical size in centimeters on both monitors, with crisp rendering on both. No size jump. No blurriness.

### 11.3 Multi-DPI Sprite Sheet Cache

The VIF sprite sheet cache is keyed by scale factor. If a window has been on both zones, both sprite sheets are cached. Dragging back to Zone 0 hits the cache — no re-rasterization.

Cache eviction: LRU per window. Maximum 3 cached scale levels per widget set. Beyond that, oldest evicted and re-rendered on demand.

---

## 12. Scrolling

### 12.1 Scroll Container

The `<scroll>` element creates a viewport into content larger than its assigned rectangle.

**Data:**
```
scroll_offset_x   — current horizontal scroll position
scroll_offset_y   — current vertical scroll position
content_w         — total content width (computed from children)
content_h         — total content height (computed from children)
viewport_w        — visible width (from Auckland rect)
viewport_h        — visible height (from Auckland rect)
```

### 12.2 Scroll Rendering

Content is drawn into an oversized internal surface at full content dimensions. The visible portion is blitted to the canvas via `Surface_BlitRegion`:

```
Surface_BlitRegionSetup(viewport_w, viewport_h, scroll_rect_x, scroll_rect_y)
Surface_BlitRegion(canvas, content_surface, scroll_offset_x, scroll_offset_y)
```

### 12.3 Scrollbar Widgets

Scrollbars are VIF widget assets auto-generated by Auckland when content exceeds viewport. They render at the right and/or bottom edge of the scroll rect. Scrollbar thumb size is proportional to viewport/content ratio. Scrollbar interaction adjusts scroll offset.

---

## 13. Example Markup

### 13.1 Scientific Calculator

```html
<window title="Scientific Calculator"
        design-w="360" design-h="540"
        min-scale="0.5" max-scale="3.0"
        bg="#1A1A2E">

  <panel id="screen-panel" bg="#0D1117" padding="8" border="1" border-color="#333">
    <display id="screen" rows="2"
             font="DejaVuSansMono" font-size="28pt"
             fg="#00FF88" text-align="right" />
  </panel>

  <tabs id="mode-tabs">
    <tab label="Basic">
      <group layout="grid" cols="4" gap="4" padding="8">
        <button label="7" action="digit:7" grow="1" />
        <button label="8" action="digit:8" grow="1" />
        <button label="9" action="digit:9" grow="1" />
        <button label="÷" action="divide"  grow="1" fg="#FF6B6B" />

        <button label="4" action="digit:4" grow="1" />
        <button label="5" action="digit:5" grow="1" />
        <button label="6" action="digit:6" grow="1" />
        <button label="×" action="multiply" grow="1" fg="#FF6B6B" />

        <button label="1" action="digit:1" grow="1" />
        <button label="2" action="digit:2" grow="1" />
        <button label="3" action="digit:3" grow="1" />
        <button label="−" action="subtract" grow="1" fg="#FF6B6B" />

        <button label="0" action="digit:0" grow="1" />
        <button label="." action="decimal"  grow="1" />
        <button label="=" action="equals"   grow="1" bg="#4CAF50" />
        <button label="+" action="add"      grow="1" fg="#FF6B6B" />
      </group>
    </tab>

    <tab label="Scientific">
      <group layout="grid" cols="5" gap="4" padding="8">
        <button label="sin" action="fn:sin" grow="1" />
        <button label="cos" action="fn:cos" grow="1" />
        <button label="tan" action="fn:tan" grow="1" />
        <button label="π"   action="const:pi" grow="1" />
        <button label="e"   action="const:e"  grow="1" />

        <button label="x²"  action="fn:square" grow="1" />
        <button label="√x"  action="fn:sqrt"   grow="1" />
        <button label="xⁿ"  action="fn:power"  grow="1" />
        <button label="log" action="fn:log"     grow="1" />
        <button label="ln"  action="fn:ln"      grow="1" />
      </group>
    </tab>

    <tab label="Graph">
      <canvas id="plot" grow="1" plugin="graphing.x" />
    </tab>
  </tabs>
</window>
```

### 13.2 Form Layout with Tabstop Alignment

```html
<window title="User Profile" design-w="480" design-h="360" bg="#1A2A1A">
  <group layout="vbox" padding="24" gap="12">

    <label text="User Profile" font-size="18pt" fg="#FFFFFF" />
    <separator />

    <group layout="hbox" gap="8">
      <label text="Name:" width="100" text-align="right" fg="#CCCCCC" />
      <text id="name" tabstop-left="fields" grow="1"
            placeholder="Enter name" />
    </group>

    <group layout="hbox" gap="8">
      <label text="Email:" width="100" text-align="right" fg="#CCCCCC" />
      <text id="email" tabstop-left="fields" grow="1"
            placeholder="user@example.com" />
    </group>

    <group layout="hbox" gap="8">
      <label text="Role:" width="100" text-align="right" fg="#CCCCCC" />
      <text id="role" tabstop-left="fields" grow="1"
            placeholder="Developer" />
    </group>

    <spacer grow="1" />

    <group layout="hbox" gap="8" justify="end">
      <button label="Cancel" action="form:cancel" width="100" />
      <button label="Save" action="form:save" width="100" bg="#4CAF50" />
    </group>

  </group>
</window>
```

### 13.3 File Browser (Scroll + Dynamic Content)

```html
<window title="Files" design-w="640" design-h="480" bg="#1A2A2A">
  <group layout="vbox" padding="0" gap="0">

    <panel bg="#252525" padding="8">
      <group layout="hbox" gap="8">
        <button label="←" action="nav:back" width="32" height="32" />
        <button label="→" action="nav:forward" width="32" height="32" />
        <button label="↑" action="nav:up" width="32" height="32" />
        <text id="path-bar" grow="1" height="28"
              bind="nav.current_path" />
      </group>
    </panel>

    <scroll grow="1">
      <group id="file-list" layout="vbox" gap="2" padding="4">
        <!-- Populated dynamically by file service -->
      </group>
    </scroll>

    <panel bg="#252525" padding="4">
      <label id="status" text="Ready" font-size="10pt" fg="#888888" />
    </panel>

  </group>
</window>
```

---

## 14. Element Tree Data Structure

### 14.1 Node Structure

```
AKNode (allocated struct, 128 bytes per node):
    tag_type        — TAG_WINDOW, TAG_GROUP, TAG_BUTTON, etc.
    id_hash         — hash of id string for fast lookup
    parent          — pointer to parent node
    first_child     — pointer to first child (linked list)
    next_sibling    — pointer to next sibling
    child_count     — number of direct children

    // Layout input (from markup)
    layout_mode     — VBOX, HBOX, GRID, FLOW
    cols            — grid column count
    gap             — gap between children (logical units)
    padding_t       — padding top
    padding_r       — padding right
    padding_b       — padding bottom
    padding_l       — padding left
    align           — cross-axis alignment
    justify         — main-axis justification

    // Sizing input
    width           — explicit width (0 = auto)
    height          — explicit height (0 = auto)
    min_w           — minimum width
    min_h           — minimum height
    max_w           — maximum width (0 = unlimited)
    max_h           — maximum height (0 = unlimited)
    grow            — flex grow factor
    shrink          — flex shrink factor
    basis           — flex basis (0 = auto)

    // Solved output (written by solver)
    solved_x        — left edge (physical pixels)
    solved_y        — top edge (physical pixels)
    solved_w        — width (physical pixels)
    solved_h        — height (physical pixels)

    // Render state
    dirty           — needs redraw
    visible         — included in layout
    enabled         — accepts input
    state           — NORMAL/HOVER/PRESSED/DISABLED/CHECKED

    // Type-specific data pointer
    extra           — points to tag-specific data (text content, action string, etc.)
```

### 14.2 Tag Type Constants

```
FixedPool.AKTag {
    "WINDOW":     Initialize=1
    "GROUP":      Initialize=2
    "PANEL":      Initialize=3
    "SCROLL":     Initialize=4
    "TABS":       Initialize=5
    "TAB":        Initialize=6
    "BUTTON":     Initialize=10
    "LABEL":      Initialize=11
    "TEXT":        Initialize=12
    "DISPLAY":    Initialize=13
    "CHECKBOX":   Initialize=14
    "RADIO":      Initialize=15
    "SLIDER":     Initialize=16
    "PROGRESS":   Initialize=17
    "IMAGE":      Initialize=18
    "CANVAS":     Initialize=19
    "SPACER":     Initialize=20
    "SEPARATOR":  Initialize=21
}
```

### 14.3 Layout Mode Constants

```
FixedPool.AKLayout {
    "VBOX":  Initialize=0
    "HBOX":  Initialize=1
    "GRID":  Initialize=2
    "FLOW":  Initialize=3
}

FixedPool.AKAlign {
    "START":    Initialize=0
    "CENTER":   Initialize=1
    "END":      Initialize=2
    "STRETCH":  Initialize=3
}

FixedPool.AKJustify {
    "START":         Initialize=0
    "CENTER":        Initialize=1
    "END":           Initialize=2
    "SPACE_BETWEEN": Initialize=3
    "SPACE_AROUND":  Initialize=4
}
```

---

## 15. Solver Implementation

### 15.1 Algorithm: Single-Pass DAG Solve

Auckland's constraints form a directed acyclic graph. Parent sizes constrain child sizes. Sibling positions depend on preceding siblings. No circular dependencies exist by construction.

The solver is two passes:

**Pass 1 — Measure (bottom-up):**
Walk the tree in post-order (children before parents). Each node computes its intrinsic size:
- Leaf nodes: measure content (text width/height, widget base size, explicit dimensions)
- Containers: sum children intrinsic sizes + gaps + padding along layout axis

**Pass 2 — Layout (top-down):**
Walk the tree in pre-order (parents before children). Each node distributes its assigned space to its children:
- Root: assigned the full window client rect
- vbox/hbox: flex distribution algorithm
- grid: divide width by cols, compute row heights
- flow: place children left-to-right, wrap at container edge

### 15.2 Complexity

Pass 1: O(n) — visit each node once, bottom-up
Pass 2: O(n) — visit each node once, top-down
Total: O(n) where n = number of elements in the tree

No iteration. No convergence testing. No constraint relaxation. One pass each direction, done.

For a typical application (50-200 elements), this takes microseconds.

### 15.3 Scale Factor Application

Scale is applied during Pass 2. When distributing space:

```
actual_gap = gap * scale
actual_padding = padding * scale
actual_min_w = min_w * scale
actual_fixed_w = width * scale  (if width != 0)
```

Flex distribution operates on the remaining space after scaled fixed sizes and gaps are subtracted. `grow` and `shrink` factors are dimensionless ratios — they don't scale.

---

## 16. Markup Parser

### 16.1 Scope

The parser reads HTML-subset markup and builds the AKNode tree. It is not a general-purpose HTML parser. It handles:

- Self-closing tags: `<button label="OK" />`
- Open/close pairs: `<group> ... </group>`
- Quoted attribute values: `key="value"`
- Numeric attribute values (parsed to integers)
- Color values: `#RRGGBB` parsed to packed BGRA with alpha=255
- Nested elements to arbitrary depth

It does **not** handle:
- Comments (ignored if encountered)
- Entities (`&amp;` etc.)
- CDATA sections
- Namespaces
- Processing instructions
- DOCTYPE
- Unquoted attribute values

### 16.2 Parse Output

The parser outputs a tree of AKNode structs with all attributes resolved to their typed fields. String values (labels, placeholders, action strings) are interned into a string table.

### 16.3 Error Handling

Parse errors are fatal. Malformed markup means a broken UI — there is no graceful degradation. The parser reports the line number and nature of the error, then exits. Fix the markup, relaunch.

This is an application platform, not a web browser. Developers write correct markup.

---

## 17. Integration with Platform

### 17.1 Application Startup Sequence

```
1. Service Manager reads entity manifest
2. Finds markup file (markup/main.html)
3. Parser builds AKNode tree
4. Auckland measures intrinsic sizes (Pass 1)
5. Window requests canvas from compositor (size = design size * zone scale)
6. Auckland solves layout (Pass 2) with canvas dimensions
7. VIF renders widget sprite sheet at current scale
8. VFont renders font glyphs at current scale
9. All elements draw into canvas (tree-order traversal)
10. Compositor blits canvas to framebuffer
11. Application enters event loop
```

### 17.2 Event Loop Integration

```
Every tick:
  1. Input events arrive from compositor (Ring 1)
  2. Auckland hit-tests mouse events against solved rects
  3. State changes (hover, press) applied to hit element
  4. Action events dispatched to action pool
  5. Bind results update target elements
  6. Dirty elements redraw into canvas
  7. If any dirty: compositor blits canvas
```

### 17.3 Resize Handling

```
Window resize event:
  1. New canvas dimensions known
  2. Recompute scale factor
  3. If scale changed beyond threshold (>0.01):
     a. Re-rasterize VIF sprite sheet at new scale
     b. Re-rasterize font glyphs at new scale
  4. Auckland re-solves layout (Pass 2) with new dimensions
  5. Full canvas redraw (all elements)
  6. Compositor blits
```

The threshold prevents thrashing during interactive resize. Sub-threshold resizes reuse existing sprite sheets and let flex distribution handle the size change.

---

## 18. Theme System

### 18.1 Overview

Every application declares a theme pack that provides the complete visual identity: widget assets (VIF), fonts (VIF), color palette, spacing defaults, and sizing defaults. Individual elements can override any theme property inline. No CSS cascade, no inheritance chains — just two levels: theme default, then element override.

### 18.2 Theme Pack Structure

A theme pack is a directory or bundled archive containing:

```
themes/modern-dark/
    theme.json          — palette, spacing, font refs, sizing defaults
    widgets.vif         — button/checkbox/slider/scrollbar/radio/progress
                          each with 5 states (normal/hover/pressed/disabled/checked)
    fonts/
        primary.vif     — primary UI font
        mono.vif        — monospace font (for <display>, <text> code mode)
        heading.vif     — optional heading font
```

Or packed as a single distributable:

```
modern-dark.2ptheme
    manifest.json
    widgets.vif
    primary.vif
    mono.vif
```

### 18.3 Theme Manifest (theme.json)

```json
{
  "name": "modern-dark",
  "version": "1.0",
  "author": "Designer Name",

  "fonts": {
    "primary": "fonts/primary.vif",
    "mono": "fonts/mono.vif",
    "heading": "fonts/heading.vif"
  },

  "palette": {
    "bg":           "#1A1A2E",
    "fg":           "#E0E0E0",
    "accent":       "#4CAF50",
    "accent-hover": "#66BB6A",
    "accent-press": "#388E3C",
    "surface":      "#252540",
    "border":       "#3A3A5C",
    "error":        "#FF5252",
    "warning":      "#FFC107",
    "muted":        "#888899",
    "selection":    "#4CAF5044"
  },

  "typography": {
    "font-size":         "12pt",
    "heading-size":      "18pt",
    "mono-size":         "11pt",
    "line-spacing":      120,
    "heading-weight":    "bold"
  },

  "spacing": {
    "gap":               8,
    "padding":           12,
    "margin":            16,
    "border-width":      1,
    "border-radius":     4
  },

  "sizing": {
    "button-height":     36,
    "button-min-width":  64,
    "input-height":      32,
    "checkbox-size":     20,
    "radio-size":        20,
    "slider-height":     24,
    "scrollbar-width":   12,
    "tab-height":        32,
    "separator-width":   1
  },

  "widgets": "widgets.vif"
}
```

### 18.4 Markup Declaration

The `<theme>` tag is declared once inside `<window>`, before any content elements:

```html
<window title="My App" design-w="360" design-h="540">

  <theme pack="modern-dark" />

  <group layout="vbox">
    <button label="Normal" action="do:thing" />
    <button label="Override" action="do:other"
            font-size="18pt" height="80" bg="#FF5722" />
  </group>

</window>
```

The `pack` attribute resolves to a theme directory or .2ptheme file. All theme defaults apply to every element in the window.

Inline overrides on any element take priority over theme defaults:

```html
<!-- Uses theme button-height, theme font-size, theme colors -->
<button label="Default" />

<!-- Overrides height and bg, inherits everything else from theme -->
<button label="Custom" height="80" bg="#FF5722" />

<!-- Overrides font entirely for this label -->
<label text="Special" font="heading" font-size="24pt" fg="#FFD700" />
```

### 18.5 Resolution Order

Property lookup for any element, checked in order:

```
1. Element has explicit attribute?  → use it
2. Theme manifest has a default?    → use it
3. Platform hardcoded default?      → use it
```

First match wins. Three levels, no ambiguity, no specificity rules. The platform defaults are sensible fallbacks that work without any theme (plain appearance, system font, neutral colors).

### 18.6 Theme Properties Available for Override

Any property from the theme manifest can be overridden per-element via attributes:

**Colors:** `bg`, `fg`, `accent`, `border-color`
**Typography:** `font`, `font-size`, `font-weight`, `text-align`, `line-spacing`
**Spacing:** `gap`, `padding`, `margin`, `border`, `border-radius`
**Sizing:** `width`, `height`, `min-width`, `min-height`, `max-width`, `max-height`

### 18.7 Font Resolution

The `font` attribute on any element resolves through the theme:

```html
<label font="mono" text="code style" />
```

Looks up `"mono"` in the theme's `fonts` map → resolves to `fonts/mono.vif` → loads and caches at current scale. If the font name doesn't match a theme font key, it's treated as a direct VIF file path.

### 18.8 Widget Asset Resolution

Widget elements (`<button>`, `<checkbox>`, `<slider>`, etc.) resolve their visual assets from the theme's `widgets.vif`:

1. Theme loads `widgets.vif` at startup
2. Widget VIF contains entries named by widget type and state: `button_normal`, `button_hover`, `button_pressed`, `button_disabled`, `button_checked`
3. On scale change: all widget assets re-rasterize from TinyVG at new scale → sprite sheet rebuilt
4. Per-frame: widget draws are sprite sheet blits, zero vector rendering cost

Custom widget packs from third-party designers just need to follow the naming convention in the VIF. Drop in a new `widgets.vif`, change the theme `pack` reference, entire app re-skins.

### 18.9 Theme Hot-Swap

Changing themes at runtime:

1. Load new theme manifest
2. Load new widget VIF → rasterize sprite sheet at current scale
3. Load new font VIFs → rasterize glyphs at current scale
4. Update theme property table
5. Auckland re-solves layout (spacing/sizing defaults may have changed)
6. Full canvas redraw with new theme
7. One frame

Applications don't need to handle theme changes. Auckland and the widget renderer handle it automatically.

### 18.10 Distributable Themes

Theme packs are publishable assets:

- Designer creates theme with custom VIF widgets, fonts, colors, spacing
- Packages as `.2ptheme` file
- Users install by dropping in themes directory
- Any app can reference it by name
- Widget assets re-render at any scale/DPI automatically (vectors)
- No bitmap assets to maintain per resolution

This is the design equivalent of the font pipeline: one source of truth (TinyVG vectors + manifest), infinite output resolutions.

### 18.11 Platform Default Theme

The platform ships with a built-in default theme that provides baseline styling when no `<theme>` tag is declared:

```json
{
  "name": "platform-default",
  "palette": {
    "bg": "#1A2A1A",
    "fg": "#FFFFFF",
    "accent": "#4488CC",
    "surface": "#252525",
    "border": "#555555"
  },
  "typography": {
    "font-size": "12pt",
    "line-spacing": 120
  },
  "spacing": {
    "gap": 6,
    "padding": 8,
    "border-width": 1
  },
  "sizing": {
    "button-height": 32,
    "input-height": 28
  }
}
```

This ensures every app is usable even without a theme pack. It's intentionally plain — themes are where visual identity lives.

---

## 19. Implementation Roadmap

### Phase 1: Core Solver ✅ COMPLETE
- [x] AKNode structure (256 bytes, 31 fields across identity/tree/layout/sizing/solved/state)
- [x] AKExtra structure (128 bytes, per-tag-type data: colors, text, borders, actions)
- [x] Tree construction API (AK_CreateNode, AK_AddChild, AK_SetRoot)
- [x] Node get/set helpers (AK_Get, AK_Set, AK_ExtraGet, AK_ExtraSet)
- [x] AK_AllocExtra with TR_HANDLE initialized to -1
- [x] Measure pass (bottom-up intrinsic sizing via TextRegion_MeasureWidth/Height)
- [x] Layout pass — VBOX (vertical flex with grow factors, cross-axis alignment)
- [x] Layout pass — HBOX (horizontal flex with grow factors, cross-axis alignment)
- [x] Layout pass — GRID (N-column equal-cell grid)
- [x] Scale factor computation (integer ratio, min of width/height ratios)
- [x] Min/max constraints on flex children
- [x] Padding and gap with scale factor application
- [x] AK_Draw — solve + render entire tree
- [x] AK_DrawNode — pre-order traversal, painter's algorithm
- [x] Panel rendering (background fill, 4-side border)
- [x] Button rendering (fill, border, centered+middle text via TextRegion)
- [x] Label rendering (text via TextRegion with horizontal + vertical alignment)
- [x] Separator rendering (orientation from parent layout mode)
- [x] Spacer support (invisible flex element for pushing content)
- [x] All expressions flattened for 6-register ABI
- [x] Test: 21-node layout tree renders correctly (panel, hbox, grid, spacer, bottom bar)

### Phase 2: TextRegion
- Library.TextRegion.ailang
- Region-bounded vector text rendering
- Word wrap at region width
- Text alignment (left, center, right)
- Line spacing control
- MeasureWidth / MeasureHeight for intrinsic sizing
- Test: render wrapped text into a fixed rectangle

### Phase 3: Markup Parser
- Tokenizer (tags, attributes, text content)
- Tree builder (open/close matching, self-closing)
- Attribute parsing (strings, numbers, colors, enums)
- String table for interned values
- Test: parse calculator markup, verify tree structure

### Phase 4: Widget Rendering
- VIF sprite sheet generation at arbitrary scale
- Widget draw functions (button, checkbox, slider, etc.)
- State management (normal, hover, pressed, disabled, checked)
- Integration with Auckland rects
- Test: render a grid of buttons at multiple scales

### Phase 5: Event Routing
- Hit testing against solved rect list
- State transitions (mouse enter/leave/down/up)
- Focus management (tab order, click-to-focus)
- Action dispatch to action pool
- Bind result updates
- Test: interactive button clicks, text input

### Phase 6: Window Integration
- Replace TextBuffer with Auckland-managed layout
- Window canvas as Auckland render target
- Resize triggers Auckland re-solve
- Zone transition triggers re-rasterize + re-solve
- Test: calculator app running in windowed display server

### Phase 7: Advanced Layout
- Flow layout
- Scroll container with viewport + scrollbar widgets
- Tabs container with tab switching
- Named tabstop alignment
- Test: file browser with scrollable list

---

## 19. Non-Goals

Auckland explicitly does NOT implement:

1. **Text reflow.** No inline elements wrapping around floats. This is app UI, not document layout.
2. **CSS cascade.** No style inheritance, no specificity, no !important. Each element's style is explicit.
3. **Percentage-based sizing.** Use `grow` factors instead. They're cleaner.
4. **Media queries.** Continuous scaling replaces breakpoints entirely.
5. **Animation framework.** Apps animate by updating element properties and marking dirty. Auckland re-solves if layout properties change.
6. **DOM manipulation API.** The tree is built at parse time. Dynamic content (file lists, search results) is handled by the service populating container children via the action pool.
7. **Accessibility tree.** Future consideration, not in v1.
8. **RTL/BiDi layout.** Future consideration, not in v1.

---

## 20. Design Decisions Summary

1. **HTML syntax, not HTML semantics.** Tags map to platform primitives, not document elements.
2. **Single-pass solver, not Cassowary.** The constraint graph is a DAG by construction. No iteration needed.
3. **Flex model from CSS, simplified.** grow/shrink/basis cover 95% of layout needs without the full CSS spec.
4. **No percentages.** Flex factors are better. `grow="1"` on two siblings = 50/50 split. `grow="2"` + `grow="1"` = 67/33. No ambiguity about "percent of what?"
5. **Continuous scaling over breakpoints.** One layout that smoothly scales is simpler and more correct than multiple discrete layouts.
6. **Parse errors are fatal.** Developers fix markup. The platform doesn't guess.
7. **One canvas per window.** No per-element surfaces. No layer compositor. Painter's algorithm, tree order.
8. **Sprite sheet caching.** Widget assets rasterize once per scale level. Per-frame cost is a rectangle blit, not a vector render.
9. **Vectors make DPI invisible.** The entire DPI problem dissolves because re-rendering at any size is a built-in capability of the pipeline.
10. **Auckland is geometry only.** It computes rectangles. It does not draw. It does not handle input. It does not know about surfaces. Clean separation.
