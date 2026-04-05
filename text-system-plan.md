# AILANG Text System — Design Document v2.0
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.

---

## Overview

The AILANG text system provides print-fidelity vector text rendering built into the display stack from day one. Every text surface is WYSIWYG — what renders on screen is pixel-identical to print output. The system uses TinyVG-backed vector fonts rendered through the existing VIF rasterizer pipeline. No bitmap fonts. No FreeType dependency.

The text system integrates with Auckland Layout Model (ALM) for positioning. Auckland assigns a rectangle. TextRegion renders text into that rectangle. The application's window canvas is the single drawing target — TextRegion draws into it directly, never owns it.

## Core Principle

**One vector pipeline, infinite resolutions.** Font glyphs are stored as TVG vector data. Rendering at any DPI is just changing the rasterize size parameter. A document looks identical on 1080p, 4K, and 300 DPI print because the vectors re-render at the target resolution. No scaling artifacts, no separate asset pipelines per resolution.

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│  Application / Auckland Layout              │
│  "render 12pt DejaVu Sans in this rect"     │
├─────────────────────────────────────────────┤
│  Library.Document          (future)         │
│  Multi-page document management             │
├─────────────────────────────────────────────┤
│  Library.TextRegion                         │
│  String → glyph placement, wrapping, align  │
│  Draws into app canvas at assigned rect     │
├─────────────────────────────────────────────┤
│  Library.PageSurface                        │
│  Canvas creation with paper/DPI metadata    │
├─────────────────────────────────────────────┤
│  Library.Fonts                              │
│  Glyph lookup, metrics, kerning, caching    │
├─────────────────────────────────────────────┤
│  Library.SurfaceBlit                        │
│  Alpha blit, tinted blit, region blit       │
├─────────────────────────────────────────────┤
│  Library.VIF (TVG rasterizer)               │
│  Vector → bitmap for each glyph             │
├─────────────────────────────────────────────┤
│  Library.SuperSample                        │
│  Optional AA via render-at-Nx + downsample  │
├─────────────────────────────────────────────┤
│  Library.DSurface / DDrawPixel              │
│  PIXEL_32 surface primitives                │
├─────────────────────────────────────────────┤
│  Compositor (DCompose)                      │
│  Opaque surface blit to framebuffer         │
└─────────────────────────────────────────────┘
```

## Window Canvas Architecture

### One Canvas Per Window

Each window has a single PIXEL_32 surface — the canvas. Everything draws into this canvas: background fills, widget chrome, text, icons, custom drawing. There is no layer stack, no per-element surfaces, no compositor between elements within a window.

Drawing order follows the Auckland element tree (pre-order traversal). Parent draws first (background), children draw on top. Painter's algorithm. Last writer wins.

### Alpha Blending Is Internal Only

The compositor between windows is opaque — `Surface_BlitOpaque` or raw memcpy. No transparency between windows, ever.

Alpha blending exists only **within** the canvas for app-level rendering:
- Glyph anti-aliasing (TVG rasterizer produces alpha edges)
- `Surface_BlitTinted` composites glyph surfaces onto the canvas with per-pixel alpha
- Vector widget rendering with curved edges, gradients
- Any app-level sprite or overlay compositing

This keeps the expensive per-pixel blend math contained inside the canvas drawing path where it's needed, and out of the windowing system where it would infect every frame.

### TextRegion Replaces TextBuffer

The legacy TextBuffer system (bitmap font, surface-owning, whole-surface FillRect on every render) is replaced by TextRegion. Key differences:

| | TextBuffer (legacy) | TextRegion (current) |
|---|---|---|
| Font source | Bitmap (PSF) | Vector (TVG via VIF) |
| Surface ownership | Owns entire surface | Draws into a rect on any canvas |
| Background | FillRect entire surface every render | Does not touch background |
| Scaling | Fixed cell size | Continuous, DPI-aware |
| Integration | Standalone | Auckland assigns its rect |
| Future | Deprecated | Foundation for all text elements |

TextBuffer continues to function for the bitmap terminal text path during transition. New UI code uses TextRegion exclusively. TextBuffer will be removed once all consumers migrate.

## Canvas Types

### Window Canvas
The window's single drawing surface. Sized to the window's client area (inside decorator). All Auckland-managed elements draw into this canvas.

### Page Canvas
Dimensions derived from real paper sizes at monitor DPI. Apps that create page canvases get print-ready output automatically.

| Paper    | Inches      | @ 96 DPI       | @ 150 DPI       | @ 300 DPI        |
|----------|-------------|----------------|-----------------|------------------|
| Letter   | 8.5 × 11   | 816 × 1056     | 1275 × 1650     | 2550 × 3300      |
| Legal    | 8.5 × 14   | 816 × 1344     | 1275 × 2100     | 2550 × 4200      |
| A4       | 8.27 × 11.69| 794 × 1123    | 1240 × 1754     | 2480 × 3508      |
| A3       | 11.69 × 16.54| 1123 × 1588  | 1754 × 2481     | 3508 × 4962      |

Landscape swaps width and height. Default margins: 1 inch (96px @ 96 DPI).

### Free Canvas
App specifies arbitrary pixel dimensions. For UI elements, windows, panels — anything that isn't a document page.

### Custom Canvas
App specifies physical dimensions (inches or mm) plus DPI. For posters, banners, non-standard paper.

## DPI Strategy

Render at monitor DPI for screen work. The vector font pipeline scales to any size, so DPI is just a multiplier converting physical units (points, inches) to pixels.

When DPI changes (window moves to different display, user changes scaling):
1. `VFont_FlushCache()` — clear rasterized glyph bitmaps
2. `VFont_RasterAll(new_size)` — re-render from vectors at new DPI
3. Auckland re-solves layout — same constraints, new physical pixel dimensions
4. All TextRegions re-render — same text, same layout proportions, different pixels

For print export: re-render from stored vectors at printer DPI. Same document, higher resolution. SuperSample library available if needed for additional quality.

Point size to pixel conversion: `pixel_size = point_size * dpi / 72`

### Cross-Monitor DPI Transition

When a window moves from a 96 DPI zone to a 256 DPI zone:

1. Logical size unchanged — a 360×540 lu window stays 360×540 lu
2. Physical size scales — 360×540 → 960×1440 physical pixels (at 256/96 ratio)
3. Auckland re-solves constraints with new physical dimensions
4. VIF widget sprite sheets re-rasterize from TinyVG at new scale
5. Font glyphs re-rasterize from TVG at new pixel size
6. Canvas resized, full redraw into new canvas
7. One frame, no flicker, no layout jump

The user sees the same physical size (in centimeters) on both monitors, with crisp rendering on both. This works because vectors don't care what size they render at.

## Library Specifications

### Library.SurfaceBlit.ailang ✅ COMPLETE
Foundation layer — compositing one PIXEL_32 surface onto another.

**Functions (all implemented and tested):**
- `Surface_BlitAlpha(dst, src, dst_x, dst_y)` — per-pixel alpha composited blit. Bounds-checked against both surfaces.
- `Surface_BlitTinted(dst, src, dst_x, dst_y, color)` — replace src RGB with tint color, preserve src alpha, composite onto dst. This is how colored text works: glyph is black-on-transparent, tint replaces black with text color.
- `Surface_BlitRegion(dst, src, sx, sy)` — sub-rectangle blit via BlitRegionParams (6-register workaround). For scrolling viewports, partial glyph clips.
- `Surface_BlitOpaque(dst, src, dst_x, dst_y)` — fast path, no alpha math. For backgrounds, solid fills.
- `Surface_BlitRegionSetup(w, h, dst_x, dst_y)` — set BlitRegionParams before calling BlitRegion.

**Implementation notes:**
- All functions fully clipped to both src and dst bounds
- Alpha math uses src-over compositing: `out = src*sa + dst*(255-sa) / 255`
- Tinted blit reads only alpha from source, RGB from tint parameter
- BlitRegion uses FixedPool workaround for 6-register ABI limit

### Library.Fonts.ailang ✅ COMPLETE
Vector font engine — TVG-backed glyph rendering with caching.

**Functions (all implemented and tested):**
- `VFont_Init()` — allocate glyph table (512 entries max)
- `VFont_AddGlyph(codepoint, advance, bearing_x, bearing_y)` — register glyph entry
- `VFont_SetGlyphTVG(idx, tvg_data, tvg_len)` — point glyph at TVG data
- `VFont_FindGlyph(codepoint)` — linear scan lookup by codepoint
- `VFont_RasterGlyph(idx)` — parse TVG, render at current size, cache surface
- `VFont_RasterAll(size)` — batch rasterize all glyphs at given pixel height
- `VFont_FlushCache()` — clear cached surfaces (before re-render at new size)
- `VFont_DrawString(dst_surf, str_ptr, str_len, x, y, color)` — blit tinted glyphs with advance spacing
- `VFont_MeasureWidth(str_ptr, str_len)` — string width in pixels without rendering
- `VFont_GetLineHeight()` — ascender - descender + line_gap, scaled
- `VFont_GetBaseline()` — ascender distance from top, scaled
- `VFont_ScaleMetric(metric_val)` — design units to pixels conversion
- `VFont_LoadVIF(path)` — read packed .vif font file, register all glyphs, zero-copy TVG data
- `VFont_Shutdown()` — flush cache, cleanup

**Font data:**
- Glyph entry: 64 bytes (codepoint, advance, bearing_x, bearing_y, surface, tvg_ptr, tvg_len, flags)
- Font state: em size, ascender, descender, line_gap, render_size
- Glyph lookup: linear scan (sufficient for <512 glyphs, hash table upgrade path exists)

### Library.VIF.ailang ✅ COMPLETE
TinyVG parser and rasterizer — the vector rendering engine.

**Complete feature set:**
- Full TinyVG v1 parser: header, color table, all 11 command types
- Path segments: line, horiz, vert, cubic bezier, quadratic bezier, arc (stub), close
- Bezier flattener: iterative stack-based, 256× precision, depth-limited
- Scanline fill: edge table, even-odd rule, bubble sort intersections
- Alpha blending: src-over compositing in scanfill (TVG_BlendPixel)
- Gradient support: linear + radial, 2-stop interpolation
- Auto-close: unclosed paths get closing edge automatically
- Aspect ratio rendering: TVG_ScaleX/TVG_ScaleY for non-square canvases
- Color packing: TVG_PackColor(r, g, b, a) — use this instead of manual bit math
- VIF container format: magic, version, entry headers, embedded TinyVG blobs

### Library.SuperSample.ailang ✅ COMPLETE
Downsampling for anti-aliased rendering.

- `SS_Down2x(src, dst)` — 2×2 block averaging
- `SS_Down4x(src, dst)` — 4×4 block averaging
- `SS_RenderDown2x/4x` — convenience wrappers

### Library.PageSurface.ailang — TODO
Canvas creation with paper/DPI metadata.

**Data:**
```
PageMeta:
    surface       — PIXEL_32 surface handle
    paper_type    — LETTER / LEGAL / A4 / A3 / FREE / CUSTOM
    orientation   — PORTRAIT / LANDSCAPE
    dpi           — monitor DPI (default 96)
    margin_top    — pixels
    margin_bottom — pixels
    margin_left   — pixels
    margin_right  — pixels
    phys_w_mm     — physical width in millimeters
    phys_h_mm     — physical height in millimeters
```

**Functions:**
- `PageSurface_Create(paper_type, orientation, dpi)` — allocate surface at computed dimensions
- `PageSurface_SetMargins(page, top, right, bottom, left)` — set margins, converted to pixels via DPI
- `PageSurface_GetContentRect(page)` → x, y, w, h — usable area inside margins
- `PageSurface_GetDPI(page)` → current DPI
- `PageSurface_GetSurface(page)` → raw PIXEL_32 surface handle

### Library.TextRegion.ailang — TODO
Text placement and layout within a canvas. Replaces TextBuffer for all new UI code.

**Critical design point:** TextRegion does NOT own a surface. It receives a canvas handle and a rectangle from Auckland. It draws text into that rectangle. It does not fill the background — the canvas owner (or Auckland's panel/group background fill) handles that before TextRegion draws.

**Data:**
```
TextRegion:
    dst_surf      — target canvas surface (NOT owned)
    x, y          — top-left position within canvas (from Auckland)
    max_w, max_h  — bounding box for text flow (from Auckland)
    font          — font handle (VFont, not bitmap)
    color         — text color (packed BGRA via TVG_PackColor)
    align         — LEFT / CENTER / RIGHT
    wrap          — 0=no wrap, 1=word wrap
    line_spacing  — multiplier (100 = 1.0x, 150 = 1.5x)
    cursor_x      — current horizontal position (during render)
    cursor_y      — current vertical position (during render)
```

**Functions:**
- `TextRegion_Create(dst_surf, x, y, max_w, max_h)` — create region, returns handle
- `TextRegion_SetFont(region, font)` — set vector font
- `TextRegion_SetColor(region, color)` — set text color (use TVG_PackColor)
- `TextRegion_SetAlign(region, align)` — LEFT / CENTER / RIGHT
- `TextRegion_SetWrap(region, wrap)` — enable/disable word wrapping
- `TextRegion_SetLineSpacing(region, spacing)` — line spacing multiplier (100=1x)
- `TextRegion_SetRect(region, x, y, w, h)` — update rect (called by Auckland on re-solve)
- `TextRegion_MeasureWidth(region, str_ptr, str_len)` → pixel width without wrapping
- `TextRegion_MeasureHeight(region, str_ptr, str_len)` → pixel height with wrapping
- `TextRegion_Render(region, str_ptr, str_len)` — render text into canvas at assigned rect
- `TextRegion_RenderAt(region, str_ptr, str_len, x, y)` — render at specific position override

**Render algorithm:**
```
cursor_x = region.x
cursor_y = region.y + baseline

for each codepoint in string:
    if codepoint == '\n':
        cursor_x = region.x (or aligned position)
        cursor_y += line_height
        continue

    kern = VFont_GetKern(prev_cp, cp)  // when kerning available
    cursor_x += scale(kern)
    
    adv = VFont_ScaleMetric(glyph.advance)
    
    if wrap and cursor_x + adv > region.x + region.max_w:
        // Word wrap: scan back to last space, break there
        cursor_x = region.x
        cursor_y += line_height
        if cursor_y + line_height > region.y + region.max_h:
            break  // overflow — clip
    
    glyph_surf = VFont_RasterGlyph(cp)
    Surface_BlitTinted(dst_surf, glyph_surf, cursor_x, cursor_y, color)
    
    cursor_x += adv
    prev_cp = cp
```

**Alignment implementation:**
- LEFT: cursor_x starts at region.x (default)
- CENTER: measure line width first, cursor_x = region.x + (region.max_w - line_width) / 2
- RIGHT: measure line width first, cursor_x = region.x + region.max_w - line_width

For CENTER and RIGHT, text is rendered line-by-line: measure the line, compute start x, then render glyphs.

### Library.Document.ailang — FUTURE
Multi-page document management.

- `Doc_Create(paper_type, orientation)` → document handle
- `Doc_AddPage()` → new PageSurface appended to document
- `Doc_GetPage(index)` → PageSurface handle
- `Doc_GetPageCount()` → number of pages
- `Doc_ExportPDF(path)` — render all pages to PDF
- `Doc_Print()` — send to system printer

Page breaks: when TextRegion's cursor_y exceeds `page_height - margin_bottom`, the app (or a future auto-pagination layer) creates a new page and continues layout.

## Font Pipeline ✅ COMPLETE

```
TTF/OTF font file
    ↓ FontForge (tools/export_font_glyphs.py)
Individual SVG glyphs + metrics.json + kerning.json + font_meta.json
    ↓ Python converter (tools/svg2tvg.py)
Individual TVG glyphs
    ↓ VIF packer (tools/pack_font_vif.py)
Single .vif font file
    ↓ Library.Fonts (VFont_LoadVIF)
Cached glyph surfaces at render DPI
    ↓ Library.SurfaceBlit (Surface_BlitTinted)
Composited onto target canvas
```

Any TTF/OTF font can be imported with three commands:
```bash
fontforge -script tools/export_font_glyphs.py MyFont.ttf fonts/myfont/ --range 32-126
python3 tools/svg2tvg.py fonts/myfont/glyphs/ fonts/myfont/tvg/
python3 tools/pack_font_vif.py fonts/myfont/ fonts/MyFont.vif
```

## Color Packing Convention

All colors in the text system use BGRA packed format via `TVG_PackColor(r, g, b, a)`:

```ailang
black = TVG_PackColor(0, 0, 0, 255)
white = TVG_PackColor(255, 255, 255, 255)
red   = TVG_PackColor(255, 0, 0, 255)
```

**Never construct colors manually with Multiply/Add.** Always use `TVG_PackColor`. This ensures correct byte order and alpha channel.

All `WinColor` constants must include alpha=255 in the high byte. Colors without alpha (e.g., `0x1A3A5C`) have alpha=0 and will produce invisible pixels during blending operations.

## Progress Worksheet

### Phase 1: Vector Rendering Pipeline ✅ COMPLETE
- [x] TinyVG parser (header, color table, commands)
- [x] Command dispatch (fill_path, fill_rect, fill_poly, draw_line_*, outline_fill_*)
- [x] Path segments (line, horiz, vert, cubic, quad, arc_stub, close)
- [x] Bezier flattener (iterative, 256x precision)
- [x] Scanline fill (edge table, even-odd rule)
- [x] Alpha blending (src-over compositing)
- [x] Auto-close unclosed paths
- [x] Gradient support (linear + radial, 2-stop)
- [x] Color packing/unpacking (BGRA)
- [x] VIF container structure (FixedPools, cache table)
- [x] Test harness (Test.VIFParse.ailang)
- [x] Tiger test — complex vector file renders correctly
- [x] Folder icon test — UI widget renders correctly

### Phase 2: Font Pipeline Tools ✅ COMPLETE
- [x] FontForge glyph exporter (tools/export_font_glyphs.py)
- [x] SVG → TVG converter (tools/svg2tvg.py)
- [x] VIF font packer (tools/pack_font_vif.py)
- [x] Build script (tools/build_font_vif.sh)
- [x] DejaVu Sans export — 94 ASCII glyphs converted
- [x] Glyph render test — all glyphs render through full pipeline

### Phase 3: Font Library ✅ COMPLETE
- [x] Library.Fonts.ailang — glyph table, metrics, caching
- [x] VFont_AddGlyph / VFont_SetGlyphTVG / VFont_FindGlyph
- [x] VFont_RasterGlyph / VFont_RasterAll / VFont_FlushCache
- [x] VFont_ScaleMetric / VFont_GetLineHeight / VFont_GetBaseline
- [x] VFont_DrawString — tinted blit with advance spacing
- [x] VFont_MeasureWidth — string width measurement
- [x] VFont_LoadVIF — load packed .vif font file, zero-copy TVG data
- [x] Multi-size rendering (flush cache, re-raster at new size)
- [x] Test: "Hello World!", full pangram, multiple colors, multiple sizes

### Phase 4: Surface Blit ✅ COMPLETE
- [x] Library.SurfaceBlit.ailang
- [x] Surface_BlitAlpha — per-pixel alpha composited blit
- [x] Surface_BlitTinted — color-tinted blit for text rendering
- [x] Surface_BlitRegion — sub-rectangle blit with BlitRegionParams
- [x] Surface_BlitOpaque — fast path, no alpha math
- [x] All functions fully clipped to both src and dst bounds
- [x] Test: blit glyph surfaces onto target, multi-color text

### Phase 5: Display Server Integration ✅ COMPLETE
- [x] VIF_Init + VFont_Init + VFont_LoadVIF in SysDisplay_Start
- [x] TextRegion_Init in SysDisplay_Start
- [x] Vector font rendering on desktop surface via TextRegion
- [x] WinColor alpha fix (all colors now include alpha=255)
- [x] Line height formula fix (ascender + descender, not ascender - descender)
- [x] Color packing via TVG_PackColor throughout
- [x] TextBuffer retained for child window keyboard routing (deprecated path)
- [ ] Strip debug prints from VIF parser for production

### Phase 6: TextRegion ✅ COMPLETE
- [x] Library.TextRegion.ailang
- [x] TextRegion_Create with bounding box (does NOT own surface)
- [x] Font/color/align/wrap properties
- [x] SetRect — Auckland calls this on re-solve
- [x] SetVAlign — TOP / MIDDLE / BOTTOM vertical alignment
- [x] MeasureWidth — string width without rendering (for intrinsic sizing)
- [x] MeasureHeight — string height with wrapping (for intrinsic sizing)
- [x] Render — full glyph placement with advance + kerning
- [x] Word wrap at region boundary with word-break scan
- [x] Alignment (left, center, right)
- [x] Vertical alignment (top, middle, bottom)
- [x] Line spacing control
- [x] Optional background fill per region
- [x] Overflow clipping at region boundary
- [x] Cursor position tracking after render
- [x] Zero-width/height guard (prevents infinite loop)
- [x] Test: 10-case visual test, all passing
- [x] Integrated into SysDisplay desktop
- [x] Integrated into Auckland draw pass

### Phase 7: PageSurface
- [ ] Library.PageSurface.ailang
- [ ] Paper type constants (Letter, Legal, A4, A3)
- [ ] PageSurface_Create with DPI-based dimension calculation
- [ ] Margin management (set/get, physical unit conversion)
- [ ] Content rect computation
- [ ] Test: create Letter page, verify dimensions

### Phase 8: Auckland Layout Integration ✅ CORE COMPLETE
- [x] AKNode structure (256 bytes per node, tag/tree/layout/sizing/solved fields)
- [x] AKExtra structure (128 bytes, per-tag-type data: colors, text, actions)
- [x] Tree construction API (AK_CreateNode, AK_AddChild, AK_SetRoot)
- [x] Node get/set helpers (AK_Get, AK_Set, AK_ExtraGet, AK_ExtraSet)
- [x] Measure pass (bottom-up intrinsic sizing using TextRegion_MeasureWidth/Height)
- [x] Layout pass — VBOX (vertical flex distribution with grow factors)
- [x] Layout pass — HBOX (horizontal flex distribution with grow factors)
- [x] Layout pass — GRID (N-column grid with equal cell sizing)
- [x] Scale factor computation (canvas size vs design size, integer ratio)
- [x] Cross-axis alignment (start, center, end, stretch)
- [x] Min/max constraints on flex children
- [x] Padding and gap scaling
- [x] AK_DrawNode — pre-order tree traversal, painter's algorithm
- [x] Panel rendering (background fill, border)
- [x] Button rendering (fill, border, centered text with vertical alignment)
- [x] Label rendering (text via TextRegion with vertical alignment)
- [x] Separator rendering (horizontal in vbox, vertical in hbox)
- [x] Spacer support (invisible flex element)
- [x] TR_HANDLE initialized to -1 (prevents handle collision bug)
- [x] All expressions flattened for 6-register ABI
- [x] Test: 21-node layout with panel, hbox, grid, spacer, bottom bar — all correct
- [ ] Flow layout
- [ ] Scroll container
- [ ] Tabs container
- [ ] Named tabstop alignment
- [ ] Markup parser (HTML-subset → AKNode tree)
- [ ] Theme system integration

### Phase 9: Supersampling Integration
- [x] Library.SuperSample.ailang — 2x and 4x downsampling
- [ ] Wire into font rendering: render glyphs at 2x, downsample
- [ ] Test: compare AA vs non-AA text quality

### Phase 10: Document System — FUTURE
- [ ] Library.Document.ailang
- [ ] Multi-page management
- [ ] Page break detection
- [ ] PDF export
- [ ] Print support

### Phase 11: TextBuffer Deprecation
- [ ] All text consumers migrated to TextRegion
- [ ] Remove Library.TextBuffer.ailang
- [ ] Remove Library.Font.ailang (bitmap font)
- [ ] Remove Library.FontBitmap.ailang
- [ ] Remove Library.FontPSF.ailang

## File Inventory

### Complete (implemented and tested):
```
Librarys/Library.VIF.ailang              — TVG parser + rasterizer
Librarys/Library.SurfaceBlit.ailang      — surface compositing (alpha, tinted, region, opaque)
Librarys/Library.Fonts.ailang            — vector font engine (load, raster, cache, draw, measure)
Librarys/Library.SuperSample.ailang      — 2x/4x downsampling
Librarys/Library.TextRegion.ailang       — region-bounded vector text (wrap, align, valign, clip)
Librarys/Library.Auckland.ailang         — layout engine core (vbox, hbox, grid, flex, draw)
tools/export_font_glyphs.py              — FontForge TTF → SVG + metrics
tools/svg2tvg.py                         — SVG → TVG converter
tools/pack_font_vif.py                   — TVG + metrics → .vif font file
tools/build_font_vif.sh                  — full pipeline script
fonts/DejaVuSans.vif                     — packed font (94 glyphs, 14.5 KB)
fonts/dejavu-sans/                       — exported font data (SVG, TVG, metrics)
```

### Existing (not modified by text system):
```
Librarys/Library.DSurface.ailang         — surface primitives
Librarys/Library.DSurfaceTypes.ailang    — type constants
Librarys/Library.DDrawPixel.ailang       — pixel draw ops
Librarys/Library.DCompose.ailang         — compositor
Librarys/Library.DComposeFloat.ailang    — floating windows
Librarys/Library.WinManager.ailang       — window manager
Librarys/Library.SysDisplay.ailang       — display server entry
Librarys/Library.Framebuffer.ailang      — framebuffer ops
```

### TODO:
```
Librarys/Library.PageSurface.ailang      — print-fidelity canvases
Librarys/Library.AucklandParse.ailang    — markup parser (HTML-subset → AKNode tree)
Librarys/Library.AucklandTheme.ailang    — theme pack loader + property resolution
Librarys/Library.AucklandWidget.ailang   — widget draw functions (VIF sprite sheets)
Librarys/Library.AucklandEvent.ailang    — hit testing + event routing
```

### Deprecated (to be removed after migration):
```
Librarys/Library.TextBuffer.ailang       — bitmap text buffer (replaced by TextRegion)
Librarys/Library.Font.ailang             — bitmap font system (replaced by Library.Fonts)
Librarys/Library.FontBitmap.ailang       — bitmap font renderer
Librarys/Library.FontPSF.ailang          — PSF font loader
```

## Full Roadmap — Text Through GPU

### Milestone 1: Text System ✅ MOSTLY COMPLETE
**Goal:** Render styled vector text on surfaces.

- [x] Library.SurfaceBlit — alpha/tinted surface-to-surface compositing
- [x] Library.Fonts — glyph lookup, rasterize, cache, draw, measure
- [x] Library.VIF — TVG rasterizer
- [x] Font pipeline tools — TTF to VIF in three commands
- [x] VFont_LoadVIF — load packed font files at runtime
- [x] VFont_DrawString — tinted glyph blit with advance spacing
- [ ] Library.TextRegion — wrapping, alignment, region-bounded rendering
- [ ] Library.PageSurface — paper-sized canvases with DPI metadata

### Milestone 2: Auckland Layout Integration
**Goal:** Markup-driven UI with auto-positioned text regions.

- [ ] Auckland solver (measure + layout passes)
- [ ] Markup parser (HTML-subset → AKNode tree)
- [ ] TextRegion as `<label>`, `<text>`, `<display>` tag renderer
- [ ] Widget rendering via VIF sprite sheets
- [ ] Scale factor model with VIF/font re-rasterization
- [ ] Test: scientific calculator from markup

### Milestone 3: Document Model
**Goal:** Multi-page documents with page breaks and export.

- [ ] Library.Document — page array, add/get/count
- [ ] Page break detection — cursor overflow triggers new page
- [ ] Scroll view — compositor shows viewport into document pages
- [ ] PDF export — serialize vector display list to PDF path operators
- [ ] Print — write PDF, shell to `lp` via CUPS

### Milestone 4: Scrolling
**Goal:** Content larger than viewport with smooth scrolling.

- [ ] Scroll offset per window/region
- [ ] Surface_BlitRegion drives viewport — blit visible sub-rectangle
- [ ] Scroll events from input adjust offset
- [ ] Scrollbar widgets (VIF assets) auto-generated

### Milestone 5: Widget System
**Goal:** Interactive UI elements from TVG vector assets.

- [ ] Widget entry type in VIF — 5 states per widget
- [ ] TVG widget asset sets — buttons, checkboxes, radio, sliders, scrollbars
- [ ] Widget state machine — input events swap displayed state
- [ ] Sprite sheet caching per scale level
- [ ] Text input widget — TextRegion + cursor + selection

### Milestone 6: Display List Architecture
**Goal:** Capture vector commands for multi-backend rendering.

- [ ] Display list format — ordered draw command sequence
- [ ] Record mode — append instead of immediate rasterize
- [ ] Playback to CPU rasterizer
- [ ] Playback to PDF backend
- [ ] Invalidation — re-rasterize dirty regions only

### Milestone 7: SPIR-V / GPU Backend
**Goal:** GPU-accelerated rendering.

- [ ] SPIR-V shader for filled paths
- [ ] SPIR-V shader for gradients
- [ ] Vulkan surface integration
- [ ] Display list playback to GPU
- [ ] Glyph atlas on GPU
- [ ] CPU rasterizer as fallback

### Architecture Evolution

```
Today (Milestones 1-5):
    App → Auckland markup → vector render → PIXEL_32 canvas → opaque blit → framebuffer

Milestone 6:
    App → Auckland markup → display list → CPU rasterize → canvas → framebuffer
                                         → PDF serialize → file/print

Milestone 7:
    App → Auckland markup → display list → GPU tessellate+shade → GPU surface → display
                                         → CPU rasterize (fallback)
                                         → PDF serialize
```

The app markup never changes. Auckland always produces rectangles. The rendering backend is swappable. Display list is the universal intermediate format.

## Design Decisions

1. **Vector only, no bitmaps as source** — eliminates scaling/DPI complexity permanently. Bitmaps exist only as cached rasterization output.
2. **Monitor DPI as truth** — render at display DPI, re-render from vectors for print.
3. **Print-fidelity from day one** — PageSurface maps to real paper sizes.
4. **One canvas per window** — no layer stack, no per-element surfaces, no compositor between elements. Painter's algorithm.
5. **Alpha blending is canvas-internal only** — the compositor between windows is opaque. Expensive per-pixel blending stays inside the canvas where it's needed (glyph anti-aliasing, vector edges).
6. **TextRegion does not own its surface** — it draws into a rectangle on the canvas. Auckland assigns the rectangle. Background fills are someone else's job.
7. **Auckland integration** — TextRegion is what `<label>`, `<text>`, and `<display>` tags resolve to. Auckland measures text for intrinsic sizing, assigns rectangles, TextRegion renders.
8. **Font import is three commands** — any TTF/OTF to production-ready VIF in seconds.
9. **Continuous scaling** — one UI definition works at every DPI and window size. No breakpoints, no responsive modes.
10. **Color packing via TVG_PackColor** — never construct BGRA colors manually. Always include alpha.

## How to Import a New Font
```bash
fontforge -script tools/export_font_glyphs.py /path/to/Font.ttf fonts/fontname/ --range 32-126
python3 tools/svg2tvg.py fonts/fontname/glyphs/ fonts/fontname/tvg/
python3 tools/pack_font_vif.py fonts/fontname/ fonts/FontName.vif
```

## How to Render Text (AILang — Current API)
```ailang
VIF_Init()
VFont_Init()
VFont_LoadVIF("fonts/DejaVuSans.vif")
VFont_RasterAll(32)  // 32px height
color = TVG_PackColor(255, 255, 255, 255)  // white, full alpha
VFont_DrawString(canvas, "Hello!", 6, x, y, color)
```

## How to Render Text (AILang — TextRegion API)
```ailang
VIF_Init()
VFont_Init()
TextRegion_Init()
VFont_LoadVIF("fonts/DejaVuSans.vif")
VFont_RasterAll(24)

region = TextRegion_Create(canvas, 20, 100, 400, 200)
TextRegion_SetColor(region, TVG_PackColor(255, 255, 255, 255))
TextRegion_SetWrap(region, 1)
TextRegion_SetAlign(region, TRAlign.CENTER)
TextRegion_SetVAlign(region, TRVAlign.MIDDLE)
TextRegion_Render(region, "Hello World! This text wraps.", 28)
```

## How to Build a Layout (AILang — Auckland API)
```ailang
VIF_Init()
VFont_Init()
TextRegion_Init()
AK_Init()
VFont_LoadVIF("fonts/DejaVuSans.vif")
VFont_RasterAll(18)

AKTree.design_w = 640
AKTree.design_h = 480

// Build tree
win = AK_CreateNode(AKTag.WINDOW)
AK_Set(win, AKF.LAYOUT_MODE, AKLayout.VBOX)
AK_Set(win, AKF.PAD_T, 16)
AK_Set(win, AKF.PAD_R, 16)
AK_Set(win, AKF.PAD_B, 16)
AK_Set(win, AKF.PAD_L, 16)
AK_Set(win, AKF.GAP, 12)
AK_SetRoot(win)

btn = AK_CreateNode(AKTag.BUTTON)
AK_Set(btn, AKF.GROW, 1)
AK_Set(btn, AKF.HEIGHT, 40)
AK_ExtraSet(btn, AKExtra.STR_PTR, "Click Me")
AK_ExtraSet(btn, AKExtra.STR_LEN, 8)
AK_AddChild(win, btn)

// Solve and draw
AK_Draw(canvas, 640, 480)
```

## Known Issues and Lessons Learned

### Expression Flattening Requirement
The AILang 6-register ABI requires all expressions to be flattened to single operations per line. Nested expressions like `Add(cx, Multiply(col, Add(cell_w, gap)))` cause silent failures — the code compiles but produces incorrect results or hangs at runtime. Always flatten:
```ailang
// WRONG — nested, will fail silently
cell_x = Add(cx, Multiply(col, Add(cell_w, gap)))

// CORRECT — flattened
cell_step = Add(cell_w, gap)
cell_off = Multiply(col, cell_step)
cell_x = Add(cx, cell_off)
```
A compiler ticket has been filed to improve error reporting for nested expressions.

### TR_HANDLE Initialization
Extra data blocks are zero-initialized from the allocator. Any field used as a handle with -1 sentinel must be explicitly initialized to -1 in `AK_AllocExtra`. Handle 0 is a valid TextRegion, so the default zero value causes handle collision between nodes.

### Line Height Formula
Font descent is stored as a positive value in VIF files. The line height formula must ADD ascender + descender (not subtract): `line_height = ascender + descender + line_gap`. The old formula `ascender - descender` produced heights smaller than a single glyph.

### WinColor Alpha
All packed BGRA colors must include alpha=255 in the high byte. Colors without alpha (e.g., `0x1A3A5C`) have alpha=0 and produce invisible pixels during any blending operation. Always use `TVG_PackColor(r, g, b, 255)`.

### Variable Scoping in Loops
AILang may have scoping issues when the same variable name is used in multiple WhileLoop blocks within the same function. Using distinct variable names for each loop (e.g., `cnode` vs `child`) works around this. Compiler investigation pending.

## Git Status
All committed and pushed to origin/master.
Latest relevant commits:
- "Auckland layout engine: vbox/hbox/grid solver, flex grow, alignment, vertical text centering, panels, separators, buttons, labels. TR_HANDLE init fix. Expression flattening for grid layout."
- "TextRegion: vector text layout engine replaces bitmap text on desktop. Word wrap, alignment, line spacing, overflow clip. Auckland-ready rect interface."
- "VIF_Init added to SysDisplay_Start — vector font pipeline active in display server"
- "WinColor alpha fix — all colors include alpha=255"
- "Text rendering: spaces, baseline alignment, proper aspect ratio scaling"
- "SurfaceBlit: alpha, tinted, region, opaque blits. Blit test working."
- "Font pipeline + text system design document"
- "VIF: TinyVG rasterizer with gradients, alpha blending, supersampling library"
