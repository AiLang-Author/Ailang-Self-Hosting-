# 04 — TinyVG Rendering: Command Set, Scene Graph, Wire Format

> **Web 3.0 Protocol Specification — Version 1.0 (Draft)**
> **License: CC0 1.0 Universal (Public Domain Dedication)**

---

## 1. Overview

TinyVG (TVG) is the vector encoding that Web 3.0 uses as a high-performance widget and UI decoration layer. Rather than replacing all rendering primitives, it acts alongside standard HTML/CSS to handle what it does best.

### 1.1 The Refined Role of TVG

- **Core UI widgets:** Buttons, panels, toolbars, cards, gauges, charts, custom controls.
- **Icons & illustrations:** Resolution-independent, tiny, themeable.
- **Fancy overlays & effects:** Glassmorphism, neumorphism, custom borders, animated accents, data visualizations.
- **Server-driven canvas replacement:** For dashboards, editors, games UI, IDEs, etc.
- **Hybrid fallback:** HTML/CSS handles complex text (shaping/kerning) and document flow, while TVG handles everything that benefits from vectors and deterministic deltas.

### 1.2 The TVG Engine

A reference TVG engine parses, rasterizes, and caches vector content. The Web 3.0 wire format uses a compact binary encoding, extended with scene-graph management commands.

### 1.3 Design Goals

| Goal | How |
|------|-----|
| Parse in one pass | Fixed-size command headers, no backtracking |
| Compact | Variable-length integer encoding, shared color table |
| Directly renderable | Commands map 1:1 to rasterizer operations |
| Safe | No function pointers, no allocations from wire data |
| Extensible | Versioned command set with forward-compat skips |

---

## 2. Binary Encoding

### 2.1 Primitive Types

| Type | Encoding | Range |
|------|----------|-------|
| `u8` | 1 byte | 0–255 |
| `u16` | 2 bytes, big-endian | 0–65535 |
| `u32` | 4 bytes, big-endian | 0–4294967295 |
| `u64` | 8 bytes, big-endian | full 64-bit |
| `i16` | 2 bytes, big-endian, two's complement | -32768–32767 |
| `f32` | 4 bytes, IEEE 754 big-endian | single precision |
| `varuint` | LEB128 unsigned | 0–2^28-1 |
| `varint` | LEB128 signed, zigzag | ±2^27 |
| `color` | 4 bytes: R, G, B, A | 0–255 each |
| `node_id` | `varuint` | 0–2^28-1 |
| `string` | `varuint` length + UTF-8 bytes | 0–65535 bytes |

### 2.2 LEB128 Encoding

```
varuint encoding (unsigned):
    while value >= 0x80:
        emit (value & 0x7F) | 0x80
        value >>= 7
    emit value & 0x7F

varint encoding (signed zigzag):
    zigzag = (value << 1) ^ (value >> 63)   ; 64-bit
    encode zigzag as varuint
```

### 2.3 Command Header

Every TVG command begins with a 1-byte opcode followed by opcode-specific fields:

```
Byte 0:     Opcode
Bytes 1+:   Operands (opcode-specific)
```

Total command set: 32 opcodes (5 bits in extended mode, with escape for more).

---

## 3. Scene Graph Commands

These commands manage the retained scene graph on the client.

### 3.1 SG_NODE_CREATE (0x10)

Create a new scene-graph node.

```
[u8: 0x10] [varuint: node_id] [u8: node_type] [varuint: parent_id]
```

Node types:
| Value | Type | Description |
|-------|------|-------------|
| 0x00 | GROUP | Transparent container |
| 0x01 | RECT | Filled rectangle |
| 0x02 | PATH | Arbitrary path |
| 0x03 | TEXT | Text run |
| 0x04 | IMAGE | Raster image reference (for legacy content) |
| 0x05 | GRADIENT | Gradient definition (not rendered directly) |
| 0x06 | CLIP | Clip mask for children |

### 3.2 SG_NODE_DESTROY (0x11)

Remove a node and all its children from the scene graph.

```
[u8: 0x11] [varuint: node_id]
```

### 3.3 SG_NODE_REPLACE (0x12)

Replace a node's content atomically. Combines destroy-all-children + create-new-children.

```
[u8: 0x12] [varuint: node_id] [varuint: child_count]
    (followed by `child_count` × SG_NODE_CREATE inline)
```

### 3.4 SG_TRANSFORM (0x13)

Set the 2D affine transform matrix on a node.

```
[u8: 0x13] [varuint: node_id] [f32×6: matrix]
```

The matrix is stored as [a, b, c, d, tx, ty] where:
```
| a  c  tx |
| b  d  ty |
| 0  0  1  |
```

### 3.5 SG_VISIBLE (0x14)

Show or hide a node.

```
[u8: 0x14] [varuint: node_id] [u8: visible]  ; 0 = hide, 1 = show
```

### 3.6 SG_ZORDER (0x15)

Move a node within its parent's child list.

```
[u8: 0x15] [varuint: node_id] [varint: delta]  ; positive = forward, negative = backward
```

### 3.7 SG_STYLE (0x16)

Set rendering style on a node.

```
[u8: 0x16] [varuint: node_id] [u8: style_flags] [fields...]
```

Style flags (bitmask):
| Bit | Name | Followed By |
|-----|------|-------------|
| 0 | FILL | `color` — fill color |
| 1 | STROKE | `color` + `f32` width |
| 2 | OPACITY | `f32` — 0.0 to 1.0 |
| 3 | GRADIENT | `varuint` — gradient node ID |
| 4 | STROKE_CAP | `u8` — cap style |
| 5 | STROKE_JOIN | `u8` — join style |
| 6 | FONT | `varuint` — font resource ID |
| 7 | FONT_SIZE | `f32` — font size in points |

---

## 4. Path Commands

These commands define path geometry. They operate on a current path being built, then the path is assigned to a node.

### 4.1 PATH_BEGIN (0x20)

Start a new path.

```
[u8: 0x20] [varuint: node_id]
```

### 4.2 PATH_MOVE (0x21)

Move pen to absolute coordinates.

```
[u8: 0x21] [f32: x] [f32: y]
```

### 4.3 PATH_LINE (0x22)

Draw line from current pen to absolute coordinates.

```
[u8: 0x22] [f32: x] [f32: y]
```

### 4.4 PATH_QUAD (0x23)

Draw quadratic Bezier curve.

```
[u8: 0x23] [f32: cx] [f32: cy] [f32: x] [f32: y]
; cx,cy = control point; x,y = endpoint
```

### 4.5 PATH_CUBIC (0x24)

Draw cubic Bezier curve.

```
[u8: 0x24] [f32: cx1] [f32: cy1] [f32: cx2] [f32: cy2] [f32: x] [f32: y]
```

### 4.6 PATH_ARC (0x25)

Draw elliptical arc.

```
[u8: 0x25] [f32: rx] [f32: ry] [f32: x_axis_rotation]
           [u8: large_arc_flag] [u8: sweep_flag]
           [f32: x] [f32: y]
```

### 4.7 PATH_CLOSE (0x26)

Close the current subpath with a line to the starting point.

```
[u8: 0x26]
```

### 4.8 PATH_END (0x27)

Finalize the path and assign it to the node specified in PATH_BEGIN. After this, path commands are committed to the scene graph.

```
[u8: 0x27]
```

### 4.9 PATH_RECT (0x28) — Shortcut

Create a rectangular path in one command.

```
[u8: 0x28] [varuint: node_id] [f32: x] [f32: y] [f32: w] [f32: h]
```

### 4.10 PATH_RRECT (0x29) — Shortcut

Create a rounded-rectangle path in one command.

```
[u8: 0x29] [varuint: node_id] [f32: x] [f32: y] [f32: w] [f32: h] [f32: rx] [f32: ry]
```

### 4.11 PATH_CIRCLE (0x2A) — Shortcut

```
[u8: 0x2A] [varuint: node_id] [f32: cx] [f32: cy] [f32: r]
```

### 4.12 PATH_ELLIPSE (0x2B) — Shortcut

```
[u8: 0x2B] [varuint: node_id] [f32: cx] [f32: cy] [f32: rx] [f32: ry]
```

---

## 5. Text Commands

### 5.1 TEXT_SET (0x30)

Set text content on a TEXT node. The text is UTF-8 encoded.

```
[u8: 0x30] [varuint: node_id] [string: text]
```

### 5.2 TEXT_GLYPH_RUN (0x31)

Set pre-shaped glyph run (for complex text layout done server-side).

```
[u8: 0x31] [varuint: node_id] [varuint: glyph_count]
    (followed by `glyph_count` × [u16: glyph_id] [f32: x_offset] [f32: y_offset])
```

### 5.3 TEXT_MEASURE (0x32) — Server Query

Request the client to measure text and return the bounds. This is the ONLY client-initiated computation allowed, and only for text measurement where font metrics are client-local.

The client responds with an EVENT containing measured bounds. The server uses this to compute layout before sending the final TVG commands.

```
[u8: 0x32] [varuint: query_id] [varuint: font_resource] [f32: font_size] [string: text]
```

Response EVENT (client → server):
```json
{
  "action": "text:measured",
  "payload": {
    "query_id": 1,
    "width": 145.3,
    "height": 14.0,
    "baseline": 11.0
  }
}
```

---

## 6. Gradient Commands

### 6.1 GRAD_LINEAR (0x38)

Define a linear gradient.

```
[u8: 0x38] [varuint: node_id] [f32: x1] [f32: y1] [f32: x2] [f32: y2]
           [u8: spread_method] [varuint: stop_count]
    (followed by `stop_count` × [f32: offset] [color: color])
```

Spread methods: 0 = pad, 1 = reflect, 2 = repeat.

### 6.2 GRAD_RADIAL (0x39)

Define a radial gradient.

```
[u8: 0x39] [varuint: node_id] [f32: cx] [f32: cy] [f32: fx] [f32: fy] [f32: r]
           [u8: spread_method] [varuint: stop_count]
    (followed by `stop_count` × [f32: offset] [color: color])
```

---

## 7. Layout Commands

Web 3.0 layout uses a dual-engine approach. Complex document flow is handled by the HTML DOM. For TVG widget interiors, Web 3.0 uses the **Auckland Layout Model** (inspired by Haiku OS)—a constraint-based system using min/max/preferred sizes and weights, completely replacing overly complex CSS Flexbox/Grid.

### 7.1 LAYOUT_ANCHOR_HTML (0x40)

Dynamically anchors a TVG node's bounding box to the computed geometry of an HTML element in the document flow. This is how TVG overlays, widgets, and canvas elements sync with the DOM.

```
[u8: 0x40] [varuint: node_id] [string: html_id]
```

### 7.2 LAYOUT_SET (0x41)

Set a node's layout bounds in physical pixels.

```
[u8: 0x40] [varuint: node_id] [i16: x] [i16: y] [u16: w] [u16: h]
```

### 7.2 LAYOUT_ANCHOR (0x41)

Anchor a node relative to another node.

```
[u8: 0x41] [varuint: node_id] [varuint: anchor_to]
           [u8: my_edge] [u8: their_edge] [i16: offset]
```

Edges: 0 = top, 1 = right, 2 = bottom, 3 = left, 4 = center_h, 5 = center_v.

### 7.3 LAYOUT_FLEX (0x42)

Set flex container parameters on a GROUP node.

```
[u8: 0x42] [varuint: node_id]
           [u8: direction]    ; 0 = row, 1 = column
           [u8: justify]      ; 0 = start, 1 = end, 2 = center, 3 = space_between, 4 = space_around
           [u8: align]        ; 0 = start, 1 = end, 2 = center, 3 = stretch
           [u16: gap]         ; spacing between children in pixels
```

### 7.4 LAYOUT_GRID (0x43)

Set CSS-grid-like parameters on a GROUP node.

```
[u8: 0x43] [varuint: node_id]
           [varuint: columns] [varuint: rows]
           [u16: col_gap] [u16: row_gap]
    (followed by `columns` × [u16: col_width] or [u8: 0xFF + f32: flex])
    (followed by `rows` × [u16: row_height] or [u8: 0xFF + f32: flex])
```

---

## 8. Resource Commands

### 8.1 RES_FONT (0x50)

Register a font resource for use by TEXT nodes.

```
[u8: 0x50] [varuint: resource_id] [string: family_name]
           [u8: weight] [u8: italic] [varuint: data_length]
    (followed by `data_length` bytes of VIF-encoded font data)
```

### 8.2 RES_ICON (0x51)

Register a pre-defined icon. The icon data is itself a TVG command stream.

```
[u8: 0x51] [varuint: resource_id] [string: icon_name]
           [varuint: data_length]
    (followed by `data_length` bytes of TVG commands for the icon)
```

### 8.3 RES_IMAGE (0x52)

Register a raster image (for legacy content; use sparingly).

```
[u8: 0x52] [varuint: resource_id]
           [u16: width] [u16: height] [u8: encoding]
           [varuint: data_length]
    (followed by `data_length` bytes of image data)
```

Encodings: 0 = raw BGRA, 1 = PNG, 2 = JPEG, 3 = WebP lossless.

### 8.4 RES_RELEASE (0x53)

Release a resource. The client may reclaim memory.

```
[u8: 0x53] [varuint: resource_id]
```

---

## 9. Batch Commands

### 9.1 BATCH_BEGIN (0x00)

Start a batch. The client defers rendering until BATCH_END.

```
[u8: 0x00] [u8: flags]
```

Flags: 0x01 = atomic (all or nothing), 0x02 = high_priority.

### 9.2 BATCH_END (0x01)

End a batch and trigger re-render.

```
[u8: 0x01]
```

### 9.3 BATCH_ABORT (0x02)

Discard all commands since BATCH_BEGIN.

```
[u8: 0x02]
```

---

## 10. Complete Example: Button Widget

The server wants to render a "Save" button at position (100, 50), 80×30 pixels, with a rounded-rect background, gradient fill, and text.

### 10.1 TVG Command Stream (Hex + Annotated)

```
00 02              ; BATCH_BEGIN (high_priority)

; Create the gradient first
38 01              ; GRAD_LINEAR node_id=1
    00 00 00 00    ;   x1=0.0
    00 00 00 00    ;   y1=0.0
    00 00 00 00    ;   x2=0.0
    41 F0 00 00    ;   y2=30.0
    00             ;   spread=pad
    02             ;   2 stops
    00 00 00 00    ;     stop 0: offset 0.0
    20 80 40 FF    ;              color #204080 (full opacity)
    3F 80 00 00    ;     stop 1: offset 1.0
    40 80 C0 FF    ;              color #4080C0 (full opacity)

; Create the button background (rounded rect)
29 02              ; PATH_RRECT node_id=2
    42 C8 00 00    ;   x=100.0
    42 48 00 00    ;   y=50.0
    41 A0 00 00    ;   w=80.0
    41 F0 00 00    ;   h=30.0
    40 E0 00 00    ;   rx=7.0
    40 E0 00 00    ;   ry=7.0

; Style: fill with gradient
16 02              ; SG_STYLE node_id=2
    09             ;   flags = FILL | GRADIENT
    FF FF FF FF    ;     fill color (white, overridden by gradient)
    01             ;     gradient node_id=1

; Create text node
10 03 03 02        ; SG_NODE_CREATE id=3 type=TEXT parent=2

; Set text content
30 03              ; TEXT_SET node_id=3
    04 53 61 76 65 ;   "Save"

; Style the text
16 03              ; SG_STYLE node_id=3
    40             ;   flags = FONT
    00             ;     font_resource=0 (system default)

; Position the text centered in button
40 03              ; LAYOUT_SET node_id=3
    00 6E 00 36    ;   x=110, y=54
    00 3C 00 16    ;   w=60, h=22

; Position the button in the region
40 02              ; LAYOUT_SET node_id=2
    00 64 00 32    ;   x=100, y=50
    00 50 00 1E    ;   w=80, h=30

01                 ; BATCH_END (render)
```

### 10.2 Total Wire Size

```
Gradient:   1+1 + 4×4 + 1+1 + (4+4)×2  = 38 bytes
RRect:      1+1 + 4×6                  = 26 bytes
Style (bg): 1+1 + 1+4+1               =  8 bytes
Create txt: 1+1+1+1+1                 =  5 bytes
Text set:   1+1 + 1+4                 =  7 bytes
Style txt:  1+1 + 1+1                 =  4 bytes
Layout txt: 1+1 + 2+2+2+2            = 10 bytes
Layout btn: 1+1 + 2+2+2+2            = 10 bytes
Batch:      2 bytes                    =  2 bytes
                                    ---------------
                                     Total: 110 bytes
```

A PNG screenshot of the same button: ~2,500 bytes. **TVG is 22× smaller.**

---

## 11. TVG Command Grammar (BNF)

```bnf
<tvg-stream>    ::= <tvg-command>*

<tvg-command>   ::= <batch-cmd>
                  | <sg-cmd>
                  | <path-cmd>
                  | <text-cmd>
                  | <grad-cmd>
                  | <layout-cmd>
                  | <resource-cmd>

<batch-cmd>     ::= <batch-begin> | <batch-end> | <batch-abort>

<sg-cmd>        ::= <sg-node-create> | <sg-node-destroy> | <sg-node-replace>
                  | <sg-transform> | <sg-visible> | <sg-zorder> | <sg-style>

<path-cmd>      ::= <path-begin> (<path-move> | <path-line> | <path-quad>
                  | <path-cubic> | <path-arc> | <path-close>)* <path-end>
                  | <path-rect> | <path-rrect> | <path-circle> | <path-ellipse>

<text-cmd>      ::= <text-set> | <text-glyph-run> | <text-measure>

<grad-cmd>      ::= <grad-linear> | <grad-radial>

<layout-cmd>    ::= <layout-set> | <layout-anchor> | <layout-flex> | <layout-grid>

<resource-cmd>  ::= <res-font> | <res-icon> | <res-image> | <res-release>
```

---

## 12. Client Compliance Levels

| Level | Required Commands | Description |
|-------|-------------------|-------------|
| **Core** | BATCH, SG_NODE_CREATE/DESTROY, SG_TRANSFORM, SG_VISIBLE, SG_STYLE, PATH_RECT/RRECT, TEXT_SET, LAYOUT_SET, RES_FONT | Basic widget rendering |
| **Standard** | Core + all path commands, all gradient commands, LAYOUT_ANCHOR, LAYOUT_FLEX, RES_ICON | Full application UI |
| **Advanced** | Standard + LAYOUT_GRID, TEXT_GLYPH_RUN, TEXT_MEASURE, RES_IMAGE, stream compression | Complex dashboards, rich text |
