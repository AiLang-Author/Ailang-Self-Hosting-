# Library.SVG.ailang — Design Document & Work Plan

## Copyright
Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

---

## 1. Goal

Build a standalone SVG parsing and rendering library in Ailang, placed at
`Librarys/Library.SVG.ailang`. Any component (browser, windowing system,
apps) can import it. The library parses SVG XML into an internal draw-op
list and rasterizes to a pixel surface using the existing VIF/TinyVG
rasterizer backend.

---

## 2. Architecture

```
  SVG source (string/file)
        │
        ▼
  ┌──────────────┐
  │  XML Tokenizer│   Byte-by-byte tag/attr parser (no full DOM needed)
  │  (streaming)  │   Handles: <tag attr="val">, </tag>, self-closing <tag/>
  └──────┬───────┘
         │  element stream
         ▼
  ┌──────────────┐
  │  SVG Element  │   Recognizes SVG elements: rect, circle, ellipse, line,
  │  Dispatcher   │   polyline, polygon, path, text, g, svg, defs,
  └──────┬───────┘   linearGradient, radialGradient, stop, use, clipPath
         │  draw ops
         ▼
  ┌──────────────┐
  │  Path Parser  │   SVG path d="" → absolute commands (M L C Q A Z)
  │  + Normalizer │   Relative→absolute, shorthand→full (S→C, T→Q)
  └──────┬───────┘   Arc→cubic bezier conversion
         │  edges
         ▼
  ┌──────────────┐
  │  Transform    │   Applies transform="" attribute stack:
  │  Stack        │   translate, rotate, scale, skewX, skewY, matrix
  └──────┬───────┘   3×2 affine matrix multiplication (integer 256× fp)
         │
         ▼
  ┌──────────────┐
  │  Edge Builder │   Flattens curves to edges, applies transforms,
  │  + Fill       │   feeds into existing VIF scanline rasterizer
  └──────┬───────┘   (TVG_AddEdge, TVG_FlattenCubic, TVG_ScanFill)
         │
         ▼
  ┌──────────────┐
  │  Surface      │   Pixel output (ShmCanvas/DSurface)
  │  (existing)   │   Supports: flat color, linear gradient, radial gradient
  └──────────────┘
```

### Key Design Decisions

1. **No full DOM tree.** We parse SVG as a stream of elements. For `<g>`
   transforms, we maintain a transform stack (push on `<g>`, pop on `</g>`).
   For `<defs>`, we store gradient/clipPath definitions in lookup tables.

2. **Reuse VIF rasterizer.** The existing `Library.VIF.ailang` already has:
   - Edge list management (TVG_AddEdge, TVG_AddEdge_Raw)
   - Cubic bezier flattening (TVG_FlattenCubic) — 16,384 edge budget
   - Quadratic bezier support (TVG_ReadSegQuad)
   - Scanline fill with anti-aliasing (TVG_ScanFill)
   - Linear + radial gradient pixel shading (TVG_GradPixel)
   - Alpha blending (TVG_BlendPixel)
   - Stroke-to-quad expansion (TVG_StrokeEmit)

3. **Integer-only math.** All coordinates use 256× fixed-point (matching VIF).
   Transform matrices use 256× fixed-point entries. Trigonometry uses the
   existing FixedPointTrig library's sin/cos lookup tables.

4. **Standalone library.** Imports: Arena, VIF (for rasterizer), FixedPointTrig,
   StringUtils. No dependency on Browser, Display/Window, or any app.

---

## 3. SVG Feature Scope

### Phase 1 — Core Shapes (MVP)
| Feature | SVG Element/Attr | Notes |
|---------|-----------------|-------|
| Rectangle | `<rect>` x y width height rx ry | Rounded corners via cubic approx |
| Circle | `<circle>` cx cy r | 4-arc cubic approx (kappa) |
| Ellipse | `<ellipse>` cx cy rx ry | Same 4-arc approach |
| Line | `<line>` x1 y1 x2 y2 | Stroke expansion |
| Polyline | `<polyline>` points | Parse point list, stroke |
| Polygon | `<polygon>` points | Parse point list, fill+stroke |
| Path | `<path>` d | M L H V C S Q T A Z (abs+rel) |
| Fill | fill="#color" | Flat color, hex, named colors |
| Stroke | stroke, stroke-width | Stroke expansion to fill |
| viewBox | viewBox="x y w h" | Coordinate mapping |

### Phase 2 — Transforms & Grouping
| Feature | SVG Element/Attr | Notes |
|---------|-----------------|-------|
| Group | `<g>` | Push/pop transform + style |
| Translate | transform="translate(x,y)" | Matrix op |
| Rotate | transform="rotate(a)" | Uses FixedPointTrig |
| Scale | transform="scale(sx,sy)" | Matrix op |
| Matrix | transform="matrix(a,b,c,d,e,f)" | Direct 3×2 |
| Nested SVG | `<svg>` inside `<svg>` | New viewport/viewBox |

### Phase 3 — Paint & Gradients
| Feature | SVG Element/Attr | Notes |
|---------|-----------------|-------|
| Opacity | opacity, fill-opacity, stroke-opacity | Alpha multiply |
| Linear gradient | `<linearGradient>` + `<stop>` | Reuse TVG_GradPixel |
| Radial gradient | `<radialGradient>` + `<stop>` | Reuse TVG_GradPixel |
| Gradient units | objectBoundingBox, userSpaceOnUse | Coord mapping |
| fill-rule | evenodd, nonzero | Winding direction |

### Phase 4 — Text & Advanced
| Feature | SVG Element/Attr | Notes |
|---------|-----------------|-------|
| Text | `<text>` x y | Render via Library.Fonts |
| Font selection | font-family, font-size | Map to VIF font instances |
| Use/Symbol | `<use>` href="#id" | Reference reuse |
| ClipPath | `<clipPath>` | Clip mask via edge intersection |
| Style attr | style="fill:red;stroke:blue" | Inline CSS parse |
| Class/CSS | `<style>` block | Basic selector matching |

### Phase 5 — Browser Integration
| Feature | Notes |
|---------|-------|
| `<img src="*.svg">` | Browser calls SVG_Render into sub-surface |
| CSS background-image: url(*.svg) | Same pathway |
| Inline `<svg>` in HTML | Browser DOM → SVG parser handoff |
| SVG ↔ VIF cache | Render once, cache bitmap at target size |

---

## 4. Data Structures

```
FixedPool.SVGParse {
    "data":     Initialize=0    // Source SVG bytes (Address)
    "size":     Initialize=0    // Source length
    "pos":      Initialize=0    // Current parse position
    "error":    Initialize=0    // Error flag
}

FixedPool.SVGState {
    "surf":     Initialize=0    // Target surface (Address)
    "surf_w":   Initialize=0    // Surface width (pixels)
    "surf_h":   Initialize=0    // Surface height (pixels)
    "vb_x":     Initialize=0    // viewBox origin X (256× fp)
    "vb_y":     Initialize=0    // viewBox origin Y (256× fp)
    "vb_w":     Initialize=0    // viewBox width (256× fp)
    "vb_h":     Initialize=0    // viewBox height (256× fp)
}

// Transform stack — 6 entries per level (a,b,c,d,e,f), max 32 nesting
FixedPool.SVGXform {
    "stack":    Initialize=0    // Address of 32×6×8 = 1536 bytes
    "depth":    Initialize=0    // Current nesting depth
}

// Gradient table — up to 64 gradients, indexed by hash of id string
FixedPool.SVGGradTable {
    "data":     Initialize=0    // Address of gradient entries
    "count":    Initialize=0
}

// Per-gradient entry: 80 bytes
//   [0]  type (0=linear, 1=radial)
//   [8]  x1/cx  [16] y1/cy  [24] x2/fx  [32] y2/fy  [40] r
//   [48] stop_count
//   [56] stop_offsets_ptr (array of 256× fp offsets)
//   [64] stop_colors_ptr  (array of packed ARGB)
//   [72] id_hash
```

---

## 5. Public API

```
Function.SVG_Init { }
    // Allocate transform stack, gradient table, scratch buffers

Function.SVG_Render {
    Input: svg_data: Address    // SVG source bytes
    Input: svg_len: Integer     // Source length
    Input: surf: Address        // Target surface
    Input: surf_w: Integer      // Surface width
    Input: surf_h: Integer      // Surface height
    Output: Integer             // 0=fail, 1=ok
}
    // Main entry point. Parses SVG and renders to surface.

Function.SVG_RenderFile {
    Input: path: Address        // File path string
    Input: surf: Address
    Input: surf_w: Integer
    Input: surf_h: Integer
    Output: Integer
}
    // Convenience: read file then call SVG_Render

Function.SVG_Shutdown { }
    // Free all allocated memory
```

---

## 6. Implementation Plan — Ordered Work Items

### WP-1: XML Tokenizer
- Byte-by-byte parser: skip `<?xml?>`, `<!-- -->`, `<!DOCTYPE>`
- Extract tag name, attributes (key="value" pairs)
- Detect open `<tag>`, close `</tag>`, self-close `<tag/>`
- Store current tag + up to 16 attributes in scratch buffers
- Test: parse basic SVG, emit tag/attr list to stdout

### WP-2: SVG Path Parser
- Port `tokenize_path()` + `parse_path()` from svg2tvg.py to Ailang
- Commands: M m L l H h V v C c S s Q q T t A a Z z
- `to_absolute()` — convert all relative to absolute coords
- Shorthand expansion: S→C, T→Q (reflection of previous control point)
- Arc (A) → cubic bezier approximation (endpoint arc parameterization)
- Test: parse test SVG paths, verify absolute command output

### WP-3: Color Parser
- Parse hex: #RGB, #RRGGBB, #RRGGBBAA
- Parse named colors: black white red green blue yellow cyan magenta
  orange purple gray silver maroon navy teal olive + SVG named color set
- Parse `rgb(r,g,b)` and `rgba(r,g,b,a)` functional notation
- Opacity multiplication
- Test: verify color parsing against known values

### WP-4: Core Shape Rendering
- `<rect>` → path (with rx/ry rounded corners)
- `<circle>` + `<ellipse>` → 4-arc cubic bezier path
- `<line>` → stroke expansion
- `<polyline>` + `<polygon>` → point list → edges
- `<path>` → parse d, feed edges to VIF rasterizer
- Fill: flat color via TVG_ScanFill + TVG_FillWithColor
- Stroke: expand to fill via TVG_StrokeEmit
- viewBox mapping: SVG coords → surface pixel coords (256× fp)
- Test: render tests/svg/basic/*.svg to PPM, visual verification

### WP-5: Transform Stack
- 3×2 affine matrix: [a b c d e f]
- Matrix multiply: combine parent × child
- Parse transform="..." attribute: translate, rotate, scale, skewX, skewY, matrix
- Apply to coordinates before edge emission
- Push on `<g>`, pop on `</g>`
- Test: render tests/svg/basic/transform.svg, verify positioning

### WP-6: Gradient Support
- Parse `<defs>` section for `<linearGradient>`, `<radialGradient>`, `<stop>`
- Store in SVGGradTable indexed by id hash
- Resolve `fill="url(#id)"` references
- Feed gradient params to existing TVG_GradPixel for scanline shading
- Support objectBoundingBox + userSpaceOnUse coordinate modes
- Test: render gradient test SVGs

### WP-7: Text Rendering
- Parse `<text>` element: x, y, font-size, font-family, text-anchor
- Map font-family → VIF font face (via Library.Fonts)
- Create temporary font instance at requested size
- Render glyphs at transformed position
- Test: render tests/svg/basic/text.svg

### WP-8: SVG Test Runner
- Create tools/svg_runner.py (similar to acid_runner.py)
- Render each tests/svg/basic/*.svg through headless pipeline
- Compare output to reference images (or manual inspection)
- Report: element count, edge count, pass/fail, pixel analysis

### WP-9: Browser Integration
- Add SVG MIME type detection in browser
- `<img>` with .svg src → SVG_Render into sub-surface
- Inline `<svg>` → hand off from HTML parser to SVG parser
- Size negotiation: intrinsic SVG size vs CSS width/height

---

## 7. File Layout

```
Librarys/
    Library.SVG.ailang          ← Main library (this file)

tests/svg/
    basic/                      ← 18 hand-crafted SVG test files
        rect.svg, circle.svg, path_lines.svg, etc.
    spec/                       ← W3C SVG test suite files (future)

tools/
    svg_runner.py               ← SVG test runner (future)
    svg2tvg.py                  ← Existing SVG→TVG converter (reference)
```

---

## 8. Dependencies

| Library | Purpose |
|---------|---------|
| Library.Arena | Memory allocation |
| Library.VIF (Display/Render) | TinyVG rasterizer backend |
| Library.FixedPointTrig | Sin/cos for rotate transforms |
| Library.StringUtils | String comparison, parsing helpers |
| Library.Fonts (Display/Render) | Text rendering (Phase 4) |

---

## 9. Risk / Notes

- **Edge budget**: VIF rasterizer has 16,384 edge limit. Complex SVGs with
  many curves may hit this. Mitigation: increase MAX_EDGES or render in
  tiles.
- **Arc conversion**: svg2tvg.py currently degrades arcs to line segments.
  The Ailang library should implement proper endpoint-to-center arc
  conversion and approximate with cubic beziers.
- **No float**: All math is integer. Precision loss possible at small scales.
  The 256× fixed-point gives ~0.004px resolution which is adequate for
  screen rendering.
- **No CSS cascade**: The SVG library handles presentation attributes and
  inline style="" only. Full CSS cascade within SVG is Phase 4+.
- **No animation**: `<animate>`, `<animateTransform>` etc. are out of scope
  for the initial library.
