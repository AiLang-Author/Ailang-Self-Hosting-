# AILANG Text System — Design Document & Progress Worksheet
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

## Overview

The AILANG text system provides print-fidelity vector text rendering built into the display stack from day one. Every text surface is WYSIWYG — what renders on screen is pixel-identical to print output. The system uses TinyVG-backed vector fonts rendered through the existing VIF rasterizer pipeline. No bitmap fonts. No FreeType dependency.

The architecture aligns with HTML/CSS concepts so developers familiar with web layout will understand the model immediately. Long-term, the Auckland layout engine will automate box positioning, but the text system works standalone without it.

## Core Principle

**One vector pipeline, infinite resolutions.** Font glyphs are stored as TVG vector data. Rendering at any DPI is just changing the rasterize size parameter. A document looks identical on 1080p, 4K, and 300 DPI print because the vectors re-render at the target resolution. No scaling artifacts, no separate asset pipelines per resolution.

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│  Application                                │
│  "render 12pt DejaVu Sans on Letter page"   │
├─────────────────────────────────────────────┤
│  Library.Document          (future)         │
│  Multi-page document management             │
├─────────────────────────────────────────────┤
│  Library.TextRegion                         │
│  String → glyph placement, wrapping, align  │
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
│  Surface → framebuffer                      │
└─────────────────────────────────────────────┘
```

## Canvas Types

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
1. Font_FlushCache() — clear rasterized glyph bitmaps
2. Font_RasterAll(new_size) — re-render from vectors at new DPI
3. TextRegion re-renders — same text, same layout, different pixels

For print export: re-render from stored vectors at printer DPI. Same document, higher resolution. SuperSample library available if needed for additional quality.

Point size to pixel conversion: `pixel_size = point_size * dpi / 72`

## Library Specifications

### Library.SurfaceBlit.ailang
Foundation layer — compositing one PIXEL_32 surface onto another.

**Functions:**
- `Surface_BlitAlpha(dst, src, dst_x, dst_y)` — blit src onto dst with alpha compositing. Respects src alpha channel per pixel. Bounds-checked.
- `Surface_BlitTinted(dst, src, dst_x, dst_y, color)` — blit src onto dst, replacing src RGB with tint color while preserving src alpha. This is how colored text works: glyph is black-on-transparent, tint replaces black with text color.
- `Surface_BlitRegion(dst, src, sx, sy, sw, sh, dx, dy)` — blit a sub-rectangle of src onto dst. For partial glyph blits, clipping, scrolling.

**Implementation notes:**
- Inner loop reads src pixel, reads dst pixel, blends, writes dst pixel
- Alpha math already proven in TVG_BlendPixel — same formula
- Tinted blit: `out_rgb = tint_rgb`, `out_a = src_a` — then alpha blend onto dst
- All functions bounds-check against both src and dst dimensions

### Library.PageSurface.ailang
Canvas creation with paper/DPI metadata.

**Data:**
```
PageMeta (FixedPool per instance, or allocated struct):
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
- `PageSurface_Create(paper_type, orientation, dpi)` — allocate surface at computed dimensions, set default 1-inch margins, return handle
- `PageSurface_SetMargins(page, top, right, bottom, left)` — set margins in physical units (inches or mm), converted to pixels via DPI
- `PageSurface_GetContentRect(page)` → x, y, w, h — usable area inside margins
- `PageSurface_GetDPI(page)` → current DPI
- `PageSurface_GetPhysicalSize(page)` → width_mm, height_mm
- `PageSurface_Clear(page, color)` — fill with background color (white for documents)
- `PageSurface_GetSurface(page)` → raw PIXEL_32 surface handle for drawing

**Paper type constants:**
```
FixedPool.PaperType {
    "LETTER":    Initialize=0
    "LEGAL":     Initialize=1
    "A4":        Initialize=2
    "A3":        Initialize=3
    "FREE":      Initialize=10
    "CUSTOM":    Initialize=11
}
FixedPool.Orientation {
    "PORTRAIT":  Initialize=0
    "LANDSCAPE": Initialize=1
}
```

### Library.TextRegion.ailang
Text placement and layout within a surface.

**Data:**
```
TextRegion:
    dst_surf      — target PIXEL_32 surface
    x, y          — top-left position within surface
    max_w, max_h  — bounding box for text flow
    font          — font handle (from Library.Fonts)
    color         — text color (packed BGRA)
    align         — LEFT / CENTER / RIGHT
    wrap          — 0=no wrap, 1=word wrap
    line_spacing  — multiplier (100 = 1.0x, 150 = 1.5x)
    cursor_x      — current horizontal position (during render)
    cursor_y      — current vertical position (during render)
```

**Functions:**
- `TextRegion_Create(dst_surf, x, y, max_w, max_h)` — create region, returns handle
- `TextRegion_SetFont(region, font)` — set font for this region
- `TextRegion_SetColor(region, color)` — set text color
- `TextRegion_SetAlign(region, align)` — LEFT / CENTER / RIGHT
- `TextRegion_SetWrap(region, wrap)` — enable/disable word wrapping
- `TextRegion_SetLineSpacing(region, spacing)` — line spacing multiplier (100=1x)
- `TextRegion_MeasureWidth(region, str_ptr, str_len)` → pixel width of string (no wrapping)
- `TextRegion_MeasureHeight(region, str_ptr, str_len)` → pixel height with wrapping
- `TextRegion_Render(region, str_ptr, str_len)` — render text into dst_surf
- `TextRegion_RenderAt(region, str_ptr, str_len, x, y)` — render at specific position override

**Render algorithm:**
```
cursor_x = region.x
cursor_y = region.y + baseline
prev_cp = 0

for each codepoint in string:
    kern = Font_GetKern(prev_cp, cp)
    cursor_x += scale(kern)
    
    if wrap and cursor_x + glyph_advance > region.x + region.max_w:
        cursor_x = region.x
        cursor_y += line_height
        if cursor_y + line_height > region.y + region.max_h:
            break  // overflow
    
    glyph_surf = Font_RasterGlyph(cp, size)
    blit_x = cursor_x + scale(bearing_x)
    blit_y = cursor_y - scale(bearing_y)
    Surface_BlitTinted(dst_surf, glyph_surf, blit_x, blit_y, color)
    
    cursor_x += scale(advance)
    prev_cp = cp
```

### Library.Document.ailang (Future)
Multi-page document management.

- `Doc_Create(paper_type, orientation)` → document handle
- `Doc_AddPage()` → new PageSurface appended to document
- `Doc_GetPage(index)` → PageSurface handle
- `Doc_GetPageCount()` → number of pages
- `Doc_ExportPDF(path)` — render all pages to PDF
- `Doc_Print()` — send to system printer

Page breaks: when TextRegion's cursor_y exceeds `page_height - margin_bottom`, the app (or a future auto-pagination layer) creates a new page and continues layout.

## Font Pipeline (Complete)

```
TTF/OTF font file
    ↓ FontForge (tools/export_font_glyphs.py)
Individual SVG glyphs + metrics.json + kerning.json + font_meta.json
    ↓ Python converter (tools/svg2tvg.py)
Individual TVG glyphs
    ↓ VIF packer (tools/pack_font_vif.py)
Single .vif font file
    ↓ Library.Fonts (Font_LoadVIF)
Cached glyph surfaces at render DPI
    ↓ Library.SurfaceBlit
Composited onto target surface
```

Any TTF/OTF font can be imported with three commands:
```bash
fontforge -script tools/export_font_glyphs.py MyFont.ttf fonts/myfont/
python3 tools/svg2tvg.py fonts/myfont/glyphs/ fonts/myfont/tvg/
python3 tools/pack_font_vif.py fonts/myfont/ MyFont.vif
```

## Progress Worksheet

### Phase 1: Vector Rendering Pipeline
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

### Phase 2: Font Pipeline Tools
- [x] FontForge glyph exporter (tools/export_font_glyphs.py)
- [x] SVG → TVG converter (tools/svg2tvg.py)
- [x] VIF font packer (tools/pack_font_vif.py)
- [x] Build script (tools/build_font_vif.sh)
- [x] DejaVu Sans export — 94 glyphs converted
- [x] Glyph render test — letter "A" renders through full pipeline

### Phase 3: Font Library (AILang)
- [x] Library.Fonts.ailang — glyph table, metrics, kerning, cache
- [x] Font_AddGlyph / Font_SetGlyphTVG / Font_FindGlyph
- [x] Font_RasterGlyph / Font_RasterAll / Font_FlushCache
- [x] Font_GetKern / Font_ScaleMetric
- [x] Font_DrawString (skeleton — needs SurfaceBlit)
- [ ] Font_LoadVIF — load packed .vif font file
- [ ] Wire Font_DrawString to SurfaceBlit for actual rendering

### Phase 4: Surface Blit
- [ ] Library.SurfaceBlit.ailang
- [ ] Surface_BlitAlpha — alpha-composited surface-to-surface blit
- [ ] Surface_BlitTinted — color-tinted blit for text rendering
- [ ] Surface_BlitRegion — sub-rectangle blit
- [ ] Test: blit glyph surfaces onto a target surface

### Phase 5: Page Surface
- [ ] Library.PageSurface.ailang
- [ ] Paper type constants (Letter, Legal, A4, A3)
- [ ] PageSurface_Create with DPI-based dimension calculation
- [ ] Margin management (set/get, physical unit conversion)
- [ ] Content rect computation
- [ ] Test: create Letter page, verify dimensions

### Phase 6: Text Region
- [ ] Library.TextRegion.ailang
- [ ] TextRegion_Create with bounding box
- [ ] Font/color/align/wrap properties
- [ ] MeasureWidth — string width without rendering
- [ ] MeasureHeight — string height with wrapping
- [ ] Render — full glyph placement with advance + kerning
- [ ] Word wrap at region boundary
- [ ] Alignment (left, center, right)
- [ ] Line spacing control
- [ ] Test: render "Hello World" on a Letter page

### Phase 7: Supersampling Integration
- [x] Library.SuperSample.ailang — 2x and 4x downsampling
- [ ] Wire into font rendering: render glyphs at 2x, downsample
- [ ] Test: compare AA vs non-AA text quality

### Phase 8: Document System (Future)
- [ ] Library.Document.ailang
- [ ] Multi-page management
- [ ] Page break detection
- [ ] PDF export
- [ ] Print support

### Phase 9: Auckland Layout Engine (Future)
- [ ] Box model (margin, border, padding, content)
- [ ] Block/inline layout
- [ ] Flexbox-like container layout
- [ ] TextRegion integration — auto-sized text boxes
- [ ] HTML-like element tree → layout computation

## File Inventory

```
Librarys/
    Library.VIF.ailang              — TVG parser + rasterizer (done)
    Library.SuperSample.ailang      — 2x/4x downsampling (done)
    Library.Fonts.ailang            — font engine (done, needs VIF loader)
    Library.SurfaceBlit.ailang      — surface compositing (TODO)
    Library.PageSurface.ailang      — print-fidelity canvases (TODO)
    Library.TextRegion.ailang       — text layout + rendering (TODO)
    Library.DSurface.ailang         — surface primitives (existing)
    Library.DDrawPixel.ailang       — pixel draw ops (existing)
    Library.DCompose.ailang         — compositor (existing)

tools/
    export_font_glyphs.py           — FontForge TTF → SVG + metrics
    svg2tvg.py                      — SVG → TVG converter
    pack_font_vif.py                — TVG + metrics → .vif font file
    build_font_vif.sh               — full pipeline script

fonts/
    dejavu-sans/
        font_meta.json              — font-level metrics
        metrics.json                — per-glyph metrics
        kerning.json                — kerning pairs
        glyphs/                     — 94 SVG glyph files
        tvg/                        — 94 TVG glyph files
```

## Full Roadmap — Text Through GPU

### Milestone 1: Text System (Current Focus)
**Goal:** Render styled text on print-fidelity page surfaces.

1. Library.SurfaceBlit — alpha/tinted surface-to-surface compositing
2. Library.PageSurface — paper-sized canvases with DPI/margin metadata
3. Library.TextRegion — string layout with wrapping, alignment, kerning
4. Font_LoadVIF — load packed .vif font files at runtime
5. Wire Font_DrawString through SurfaceBlit for actual glyph placement
6. Test: "Hello World" on a Letter page with DejaVu Sans

### Milestone 2: Document Model
**Goal:** Multi-page documents with page breaks and export.

1. Library.Document — page array, add/get/count
2. Page break detection — cursor overflow triggers new page
3. Scroll view — compositor shows viewport into document pages
4. PDF export — serialize vector display list to PDF path operators
5. Print — write PDF, shell to `lp` via CUPS
6. Test: multi-page text document, export to PDF, print

### Milestone 3: Scrolling
**Goal:** Content larger than viewport with smooth scrolling.

1. Scroll offset per BSP leaf — content surface has a viewport window
2. Surface_BlitRegion drives the viewport — blit visible sub-rectangle
3. Scroll events from input (mouse wheel, keyboard) adjust offset
4. Clamp scroll bounds to content dimensions
5. Scroll position feeds into compositor blit path
6. Test: long text document scrolls smoothly in a BSP leaf

### Milestone 4: Widgets
**Goal:** Interactive UI elements from TVG vector assets.

1. Widget entry type in VIF — 5 states per widget (normal/hover/pressed/disabled/checked)
2. TVG widget asset sets — buttons, checkboxes, radio, sliders, scrollbars
3. Widget state machine — input events (hover, click, release) swap displayed state
4. Widget layout — position widgets within surfaces, hit testing
5. Scrollbar widget — wired to scroll offset from Milestone 3
6. Text input widget — combines widget chrome with TextRegion for editable text
7. Source TVG widget sets from Papirus/existing icon themes or design custom
8. Test: clickable button, functional scrollbar, text input field

### Milestone 5: Display List Architecture
**Goal:** Capture vector commands instead of immediately rasterizing.

1. Display list format — ordered sequence of draw commands with parameters
2. Record mode — same API calls (fill_path, fill_rect, etc.) append to list instead of rasterizing
3. Playback to CPU rasterizer — current path, unchanged behavior
4. Playback to PDF backend — emit PDF path operators from display list
5. Display list per surface — each window/page has its own command stream
6. Invalidation — only re-rasterize dirty regions of the display list
7. Test: render a page, export same display list to PDF, verify visual match

### Milestone 6: SPIR-V / GPU Backend
**Goal:** GPU-accelerated rendering of the vector pipeline.

1. SPIR-V shader for filled paths — tessellate beziers to triangles, fragment shader fills
2. SPIR-V shader for gradients — linear/radial as fragment shader uniforms
3. SPIR-V shader for alpha blending — standard GPU blend state
4. Vulkan surface integration — GPU surfaces replace PIXEL_32 for display
5. Display list playback to GPU — same commands, GPU draw calls instead of CPU scanfill
6. Glyph atlas on GPU — rasterize glyphs to GPU texture, blit from atlas
7. Compositor on GPU — window surfaces as textured quads, composited in one pass
8. Fallback — CPU rasterizer remains for systems without Vulkan (pre-2012 hardware)
9. Target: any GPU with Vulkan 1.0 (2012+), SPIR-V runs everywhere via MoltenVK on macOS

### Milestone 7: 3D Integration (Future)
**Goal:** UI surfaces as objects in 3D space.

1. 2D surfaces become textured quads with z-coordinate
2. Projection matrix converts 2D layout to 3D scene
3. Same vector pipeline, same display list, 3D coordinate space
4. Applications: spatial computing, VR desktop, 3D UI panels
5. The vector data doesn't care what coordinate space it lives in

### Architecture Evolution

```
Today (Milestone 1-4):
    App → vector commands → CPU rasterize → PIXEL_32 → framebuffer

Milestone 5:
    App → display list → CPU rasterize → PIXEL_32 → framebuffer
                       → PDF serialize → file/print

Milestone 6:
    App → display list → GPU tessellate+shade → GPU surface → display
                       → CPU rasterize (fallback)
                       → PDF serialize

Milestone 7:
    App → display list → GPU → 3D scene graph → display
```

The app code never changes. The display list is the universal intermediate format. Backends are swappable. This is the same architecture as Skia, Core Graphics, and Direct2D — but clean, because there's no legacy.

## Design Decisions

1. **Vector only, no bitmaps** — eliminates scaling/DPI complexity permanently
2. **Monitor DPI as truth** — render at display DPI, re-render from vectors for print
3. **Print-fidelity from day one** — page canvases map to real paper sizes, no reformatting for print
4. **HTML-aligned concepts** — TextRegion ≈ text node, PageSurface ≈ page box, future Auckland layout ≈ CSS box model
5. **Existing pipeline reuse** — TVG rasterizer handles glyphs identically to icons/widgets
6. **Font import is three commands** — any TTF/OTF to production-ready VIF in seconds
7. **Separation of concerns** — SurfaceBlit is generic (used by text, icons, UI), TextRegion is text-specific, PageSurface is document-specific