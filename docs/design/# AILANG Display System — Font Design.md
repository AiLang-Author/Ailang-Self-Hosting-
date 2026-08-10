# AILANG Display System — Font Design
*Author: Sean Collins, 2 Paws Machine and Engineering*
*Version: 1.0 — March 31, 2026*

---

## Architecture

```
Library.Font.ailang         — unified interface, registry, dispatch
Library.FontBitmap.ailang   — built-in 8x8 and 8x16 bitmap fonts
Library.FontPSF.ailang      — Linux PSF1/PSF2 console fonts
Library.FontBDF.ailang      — BDF bitmap distribution format
Library.FontTTF.ailang      — TrueType/OpenType stub (impl pending)
```

## Design Principles

- **Handle-based** — fonts identified by integer handle (0..15), not pointers
- **Registry pattern** — parallel arrays indexed by handle: types, heights, widths, baselines, data_ptrs
- **Backend-agnostic dispatch** — `Font_DrawString(surf, handle, x, y, str, color)` works for any backend
- **Surface-first** — all draw operations target a PIXEL_32 surface, not the framebuffer directly
- **No per-frame allocation** — font data loaded once, reused for lifetime of handle

## Current Status

| Backend | Status | Notes |
|---------|--------|-------|
| FontBitmap | ✅ Working | 8x8 and 8x16, full ASCII 32-126, built-in no file needed |
| FontPSF | Stub | Architecture defined, file I/O path ready |
| FontBDF | Stub | Architecture defined, parser partially implemented |
| FontTTF | Stub | Requires bezier rasterizer, significant work |

## FontBitmap Details

Built-in 8x8 and 8x16 fonts, full ASCII coverage (32-126). Generated at init time via `FontBitmap_Generate8x8/16()`. No file I/O required.

**Key fix applied**: original `FontBitmap_DefineChar8` took 10 args, exceeding the 6-arg ABI limit. Fixed by splitting into `FontBitmap_DefLo` (rows 0-3) and `FontBitmap_DefHi` (rows 4-7), 6 args each. Descenders on g, j, p, q, y now render correctly.

**Draw path**: `FontBitmap_DrawChar(surf, handle, x, y, ch, color)` → `DPix_PutPixel(surf, x+col, y+row, color)` — pixel goes into surface buffer, not framebuffer.

## Usage

```ailang
Font_Init()
handle = Font_CreateBuiltin(8)    // 8x8 built-in
Compose_SetFont(handle)           // register with compositor for pane labels
FontBitmap_DrawString(surf, handle, x, y, "Hello", 0xFFFFFF)
```

## Integration Points

- `Library.DCompose.ailang` — `DisplayFont` FixedPool, `Compose_SetFont()`, `WinCreate_ForLeaf` labels
- `Library.TextBuffer.ailang` — font handle stored per buffer, used in `TextBuffer_Render()`
- `TestWindowBSP.ailang` — `InitFont()` creates handle, calls `Compose_SetFont()`

## Adding PSF Font Support

1. `Font_LoadTyped(path, FontType.PSF)` → `FontPSF_Load(handle, path)`
2. Opens file, reads PSF1/PSF2 header, loads glyph bitmap data
3. `FontPSF_DrawChar(surf, handle, x, y, ch, color)` — same signature as bitmap
4. Linux console fonts at `/usr/share/consolefonts/*.psf.gz` (need gunzip or uncompressed)

## Future: TTF

TrueType requires:
1. Table parsing (cmap, glyf, loca, hhea, hmtx)
2. Quadratic bezier evaluation
3. Scan-line rasterization
4. Glyph cache (rasterize once per size, cache bitmap)

Will share bezier infrastructure with `Library.CursorHVIF.ailang`.
Estimated: ~1500 lines for basic hinting-free support.