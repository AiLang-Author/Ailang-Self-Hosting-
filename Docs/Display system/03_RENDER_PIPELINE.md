# 03 — Render Pipeline: Framebuffer, Surfaces, Compositor, Rings, Fonts, VIF

> **Copyright © 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.**

---

## 1. Overview

The Render Pipeline is the lowest layer of the display system. It owns the framebuffer hardware, provides pixel-level drawing primitives, manages surface allocation, composites windows together, renders vector icons and fonts, and produces the final frame displayed on screen.

### Components

| Component | Source File | Lines | Role |
|-----------|------------|-------|------|
| **Framebuffer** | `Library.Framebuffer.ailang` | ~1512 | /dev/fb0 mmap, double-buffer, page flip, pixel primitives |
| **DRenderFB** | `Library.DRenderFB.ailang` | ~150 | Double-buffer init helper |
| **DSurface** | `Library.DSurface.ailang` | ~180 | Pixel surface allocation, access, resize |
| **DSurfaceTypes** | `Library.DSurfaceTypes.ailang` | ~100 | Surface format constants |
| **DDrawPixel** | `Library.DDrawPixel.ailang` | ~250 | Pixel-level drawing primitives |
| **DDrawCell** | `Library.DDrawCell.ailang` | ~200 | Character cell rendering |
| **DCompose** | `Library.DCompose.ailang` | ~550 | Float-based compositor |
| **DComposeTypes** | `Library.DComposeTypes.ailang` | ~100 | Compositor type constants |
| **DComposeFloat** | `Library.DComposeFloat.ailang` | ~150 | Float hit testing |
| **DComposeStack** | `Library.DComposeStack.ailang` | ~200 | Surface stack management |
| **DComposeBSP** | `Library.DComposeBSP.ailang` | ~200 | BSP tree for occlusion |
| **Rings (0-3)** | `Library.DRing*.ailang` | ~500 | Ring buffer IPC between layers |
| **Fonts** | `Library.Fonts.ailang` | ~806 | Vector font (Face+Instance), glyph cache, TVG rasterization |
| **VIF** | `Library.VIF.ailang` | ~1793 | Vector Icon Format parser & renderer |
| **VIcon** | `Library.VIcon.ailang` | ~300 | Vector icon management & lookup |
| **SuperSample** | `Library.SuperSample.ailang` | ~200 | 2x/4x supersampling anti-aliasing |
| **SurfaceBlit** | `Library.SurfaceBlit.ailang` | ~450 | Surface-to-surface blit operations |
| **AudioEngine** | `Library.AudioEngine.ailang` | ~700 | Audio output subsystem (ALSA) |

---

## 2. Framebuffer — Hardware Interface

### 2.1 Initialization (`FB_Init`)

Opens the Linux framebuffer device and maps it into process memory:

```
FB_Init():
    1. open("/dev/fb0", O_RDWR) → fd
    2. ioctl(FBIOGET_VSCREENINFO) → get screen dimensions, bpp, pixel format
    3. ioctl(FBIOGET_FSCREENINFO) → get memory layout, stride/pitch
    4. mmap(fd, size, PROT_READ|PROT_WRITE, MAP_SHARED) → framebuffer pointer
    5. FB_InitDouble() → allocate back buffer, set up page flipping
    6. Store fb_width, fb_height, fb_bpp, fb_pitch, fb_size
```

**Key constraints:**
- The framebuffer is BGRA 32-bit (4 bytes per pixel)
- Pitch (row stride) is obtained from the kernel; may differ from `width × 4`
- `MAP_SHARED` ensures writes are visible to the display controller

### 2.2 Double Buffering (`FB_InitDouble`)

Allocates a back buffer the same size as the framebuffer. All drawing happens on the back buffer. `FB_Flip()` copies the back buffer to the front buffer (or performs a page flip if supported).

```
FB_InitDouble():
    back_buffer = Allocate(fb_size)
    draw_buffer = back_buffer
    FB_ClearBuffer(draw_buffer)
```

### 2.3 Page Flip (`FB_Flip`)

```
FB_Flip():
    memcpy(fb_ptr, draw_buffer, fb_size)
```

`FB_FlipFast()` uses a more optimized path (word-at-a-time copy) when the buffer is word-aligned.

### 2.4 Pixel Primitives

| Function | Description |
|----------|-------------|
| `FB_SetPixel(x, y, color)` | Set single pixel (bounds-checked) |
| `FB_SetPixelFast(x, y, color)` | Set pixel (no bounds check) |
| `FB_GetPixel(x, y)` | Read pixel color |
| `FB_Write32(addr, color)` | Write 32-bit value at byte offset |
| `FB_Read32(addr)` | Read 32-bit value at byte offset |
| `FB_HLine(x1, x2, y, color)` | Horizontal line |
| `FB_VLine(x, y1, y2, color)` | Vertical line |
| `FB_Line(x1, y1, x2, y2, color)` | Bresenham line |
| `FB_Rect(x, y, w, h, color)` | Rectangle outline |
| `FB_FillRect(x, y, w, h, color)` | Filled rectangle |
| `FB_FillRectFast(x, y, w, h, color)` | Filled rect (optimized) |
| `FB_Circle(cx, cy, r, color)` | Circle outline |
| `FB_FillCircle(cx, cy, r, color)` | Filled circle |
| `FB_Blit(src, dx, dy, w, h)` | Copy region from surface |
| `FB_BlitTransparent(src, dx, dy, w, h)` | Blit with color key transparency |
| `FB_BlitScaled(src, dx, dy, dw, dh)` | Scaled blit |
| `FB_Clear(color)` | Fill entire framebuffer |
| `FB_ClearBuffer(buf)` | Fill a buffer with color |
| `FB_RGB(r, g, b)` | Pack RGB → 32-bit color |
| `FB_C64Color(index)` | C64 palette color lookup |

### 2.5 Headless Mode (`FB_InitHeadless`)

For testing and headless servers, `FB_InitHeadless` creates an off-screen framebuffer of a configurable size without opening `/dev/fb0`. All drawing operations work identically; screenshots to BMP/PPM are the only output.

---

## 3. Surfaces — Pixel Buffers

### 3.1 Surface Types (`DSurfaceTypes`)

```
SurfaceFormat:
    PIXEL_32    — 32-bit BGRA pixel buffer
    PIXEL_24    — 24-bit BGR (no alpha)
    PIXEL_16    — 16-bit RGB565
    PIXEL_8     — 8-bit indexed (palette)
```

### 3.2 Surface Operations (`DSurface`)

| Function | Description |
|----------|-------------|
| `Surface_Create(format, w, h)` | Allocate pixel buffer, return surface index |
| `Surface_Destroy(surf)` | Free pixel buffer, release surface slot |
| `Surface_Resize(surf, w, h)` | Reallocate to new dimensions (preserves content) |
| `Surface_GetPtr(surf)` | Get pixel data pointer |
| `Surface_GetWidth(surf)` | Get width in pixels |
| `Surface_GetHeight(surf)` | Get height in pixels |
| `Surface_GetFormat(surf)` | Get pixel format |
| `Surface_GetStride(surf)` | Get row stride in bytes |

Surfaces are the fundamental unit of pixel storage. Every window, toolbar, button, icon, and text region is backed by one or more surfaces. The compositor operates on surfaces, not individual pixels.

---

## 4. DCompose — The Compositor

### 4.1 Architecture

DCompose is a float-based compositor. Each window is a "float" — a rectangular surface at a specific (x, y) position with a width and height. Floats are stacked in z-order and composited bottom-to-top.

### 4.2 Float Operations (`DComposeFloat`)

```
FloatEntry (per float):
    surface     — Surface index
    x, y        — Position on screen
    w, h        — Dimensions
    color       — Tint color (0 = no tint)
    flags       — Visibility, opacity, etc.
```

| Function | Description |
|----------|-------------|
| `Float_Add(surf, x, y, w, h)` | Create new float entry, return index |
| `Float_Remove(idx)` | Remove float from compositor |
| `Float_Move(idx, x, y)` | Update float position |
| `Float_Resize(idx, x, y, w, h)` | Update float position + dimensions |
| `Float_EntryPtr(idx)` | Get pointer to float entry |
| `Float_HitTest(x, y)` | Find top-most float at screen coordinate |

### 4.3 Compositor State

```
Compositor:
    screen_w, screen_h    — Screen dimensions
    float_count           — Number of active floats
    floats[]              — Float entry array
    dirty_slots[]         — Per-slot dirty flags
```

### 4.4 BSP Tree (`DComposeBSP`)

Binary Space Partitioning tree for occlusion culling. Splits the screen into non-overlapping regions, allowing the compositor to skip occluded pixels during blit. This is an optimization for when many windows are stacked.

### 4.5 Float Stack (`DComposeStack`)

Manages the float z-order. Float indices in `floats[]` are ordered bottom-to-top, matching the window manager's `z_order`.

### 4.6 Compositor Tick

`Compose_Tick()` processes ring buffer commands:
- `Compose_TickRing0()` — Host→Compositor commands (tile operations, focus)
- `Compose_TickRing2()` — Compositor→Input feedback (surface positions)
- `Compose_TickRing3()` — Host→Compositor surface lifecycle (create, destroy, resize)

---

## 5. Ring Buffers — Inter-Layer Communication

### 5.1 Architecture

Four ring buffers form a command/event bus between the Host, Compositor, and Input layers:

| Ring | Direction | Entry Size | Max Entries | Purpose |
|------|-----------|------------|-------------|---------|
| Ring0 | Host → Compositor | 32 bytes | 16 | Tile split/merge, focus, quit |
| Ring1 | Input → Host | 32 bytes | 64 | Keyboard, mouse, wheel events |
| Ring2 | Compositor → Input | 16 bytes | 16 | Surface positions, hit-test results |
| Ring3 | Host → Compositor | 16 bytes | 32 | Surface create, destroy, resize |

### 5.2 Ring Entry Format

**Ring0 (Host→Compositor):**
```
[0-3]   command     — Ring0Command enum (FOCUS_SET, QUIT, SPLIT_V, SPLIT_H, MERGE...)
[4-7]   arg0        — Window/surface index
[8-11]  arg1        — Secondary parameter
[12-15] arg2        — Tertiary parameter
```

**Ring1 (Input→Host):**
```
[0-3]   event_type  — Ring1Event enum (KEY_DOWN, KEY_UP, MOUSE_MOVE, MOUSE_DOWN, MOUSE_UP, MOUSE_WHEEL)
[4-7]   param_a     — Key code or mouse X
[8-11]  param_b     — Modifiers or mouse Y
[12-15] data        — Wheel delta or repeat count
```

### 5.3 Ring Operation

All rings use a circular buffer with head/tail pointers:
- **Push:** Write at tail, advance tail (overflow drops oldest)
- **Drain:** Read and advance head until head == tail

---

## 6. Fonts — Vector Font Engine

### 6.1 Architecture

The font system loads vector fonts in VIF (Vector Icon Format) and rasterizes glyphs on demand to a glyph cache.

```
Face (per font file):
    glyph_count    — Number of glyphs in font
    units_per_em   — EM square size
    ascent, descent — Font metrics
    line_gap       — Inter-line spacing
    glyph_data     — Glyph outlines

Instance (per size):
    face           — Parent face index
    size           — Pixel size
    scale          — Size/units_per_em ratio
    glyph_cache    — Rasterized glyph surfaces
```

### 6.2 Key Functions

| Function | Description |
|----------|-------------|
| `VFont_Init()` | Initialize font subsystem |
| `VFont_LoadFace(path)` | Load VIF font file, return face index |
| `VFont_LoadVIF(path)` | Legacy: load font and set as default |
| `VFont_CreateInstance(face, size)` | Create sized font instance |
| `VFont_DestroyInstance(inst)` | Free instance resources |
| `VFont_UseSize(size)` | Set default instance for TextRegion |
| `VInst_DrawString(inst, surf, x, y, str)` | Draw text to surface |
| `VInst_MeasureWidth(inst, str)` | Measure text width in pixels |
| `VInst_GetLineHeight(inst)` | Get line height for this size |
| `VInst_GetBaseline(inst)` | Get baseline offset |
| `VInst_GetGlyphSurf(inst, codepoint)` | Get rasterized glyph surface |

### 6.3 Font Pipeline

```
VIF file → TVG_Parse → glyph outlines (Bezier curves)
→ VFont_RasterGlyph → glyph surface (pixel buffer)
→ VFont_DrawString → blit glyphs to target surface
```

Glyphs are cached by codepoint+size. First use of a glyph at a given size triggers rasterization; subsequent uses blit from cache.

---

## 7. VIF/VIcon — Vector Icon Format

### 7.1 VIF (Vector Icon Format)

VIF is a custom binary format for vector graphics. It stores paths, shapes, gradients, and styles in a compact, parseable format similar to SVG but optimized for direct rendering.

### 7.2 TVG (Tiny Vector Graphics) Engine

The TVG subsystem within VIF provides:

| Function | Description |
|----------|-------------|
| `TVG_ParseHeader(buf)` | Read VIF header, extract dimensions |
| `TVG_Parse(buf)` | Full parse: extract all paths, styles, layers |
| `TVG_Render(buf, surf)` | Render VIF to a surface at current size |
| `TVG_ReadSegCmd(buf, off)` | Read segment command byte |
| `TVG_ReadSegCubic(buf, off)` | Read cubic Bezier segment |
| `TVG_ReadSegQuad(buf, off)` | Read quadratic Bezier segment |
| `TVG_ReadSegArc(buf, off)` | Read arc segment |
| `TVG_ScanFill(path, surf)` | Scanline fill for closed paths |
| `TVG_StrokeEmit(buf, path)` | Stroke path with current pen |
| `TVG_GradPixel(x, y, grad)` | Gradient pixel lookup |
| `TVG_BlendPixel(dst, src, alpha)` | Alpha-blend one pixel |
| `TVG_PackColor(r, g, b, a)` | Pack RGBA → 32-bit color |
| `TVG_ScaleX(x)` / `TVG_ScaleY(y)` | Scale coordinate to current size |

### 7.3 VIcon (Vector Icon Management)

VIcon manages icon packs loaded from VIF files:

```
IconTier:
    WIDGETS    — UI widget icons (buttons, checkboxes, tabs, etc.)
    APPS       — Application icons
    MIME       — File type icons
    ACTIONS    — Action/symbol icons
```

| Function | Description |
|----------|-------------|
| `VIcon_Init()` | Initialize icon subsystem |
| `VIcon_LoadVIF(tier, path)` | Load icon pack for a tier |
| `VIcon_Resolve(name)` | Look up icon by name, return rendered surface |
| `VIcon_SetSize(size)` | Set rendering size for subsequent resolves |
| `VIcon_ResolveSize(name, size)` | Resolve icon at specific size |

Silver System Atoms (`silver_atoms.vif`) is the default widget pack, providing:
- Window buttons: close_btn_normal, min_btn_normal, max_btn_normal
- Form widgets: button_body_normal, checkbox_box_on, checkbox_box_off
- Tabs: tab_bg_active, tab_bg_inactive
- Scrollbar parts, radio buttons, toggles, sliders

---

## 8. SurfaceBlit — Surface Operations

### 8.1 Blit Operations

| Function | Description |
|----------|-------------|
| `Surface_BlitAlpha(dst, src, x, y)` | Alpha-blend src onto dst at position |
| `Surface_BlitTinted(dst, src, x, y, color)` | Tinted alpha blit |
| `Surface_BlitRegion(dst, src, dx, dy, sx, sy, sw, sh)` | Blit rectangular region |
| `Surface_BlitOpaque(dst, src, x, y)` | Opaque copy (no alpha) |
| `Surface_BlitRegionSetup()` | Pre-compute blit parameters |

### 8.2 Alpha Blending

`Surface_BlitAlpha` implements per-pixel alpha compositing:
```
for each pixel (px, py) in src:
    src_color = src[py][px]
    src_a = (src_color >> 24) & 0xFF
    if src_a == 0: continue (fully transparent)
    if src_a == 255: dst[dy+py][dx+px] = src_color (fully opaque)
    else:
        dst_color = dst[dy+py][dx+px]
        dst_r = blend(src_r, dst_r, src_a)
        dst_g = blend(src_g, dst_g, src_a)
        dst_b = blend(src_b, dst_b, src_a)
        dst[dy+py][dx+px] = pack(dst_r, dst_g, dst_b, 255)
```

---

## 9. SuperSample — Anti-Aliasing

### 9.1 Modes

| Mode | Factor | Description |
|------|--------|-------------|
| 1x | No AA | Direct rendering (default) |
| 2x | 4 samples/px | Render at 2x resolution, box-filter down |
| 4x | 16 samples/px | Render at 4x resolution, box-filter down |

### 9.2 Algorithm

```
SuperSample_Render(render_fn, w, h, factor):
    1. Allocate temp surface at w*factor × h*factor
    2. Call render_fn(temp_surface, w*factor, h*factor)
    3. For each output pixel (x, y):
        avg = average of factor×factor block in temp_surface
        output[x][y] = avg
    4. Free temp surface
```

---

## 10. AudioEngine — Audio Output

### 10.1 Architecture

The AudioEngine provides ALSA-based audio output with a software mixer:

```
AudioEngine:
    pcm_handle      — ALSA PCM device handle
    buffer_size     — Hardware buffer size (frames)
    period_size     — Interrupt period size
    sample_rate     — Typically 44100 or 48000 Hz
    channels        — 2 (stereo)
    format          — S16_LE (16-bit signed, little-endian)
```

### 10.2 Mixer

The software mixer allows multiple "applications" to submit audio buffers that are mixed into a single output stream:

```
Mixer:
    app_buffers[8]  — Per-app ring buffers (16-bit stereo interleaved)
    mix_buffer      — Temporary mix-down buffer
    samples_written — Total samples output counter
```

| Function | Description |
|----------|-------------|
| `Mixer_Init()` | Initialize mixer |
| `Mixer_AppWrite(app_id, samples, count)` | Submit audio from app |
| `Mixer_SysWrite(samples, count)` | Submit system audio (alerts) |
| `Mixer_DrainTick()` | Mix and write one period to ALSA |
| `Mixer_Clamp16(val)` | Clamp to 16-bit signed range |

### 10.3 Playback Loop

```
Mixer_DrainTick():
    1. Clear mix_buffer
    2. For each active app: mix app_buffer into mix_buffer (additive, clamped)
    3. snd_pcm_writei(pcm, mix_buffer, period_size)
    4. Advance app read pointers
```

---

## 11. Dependencies

```
Framebuffer → (none — raw Linux syscalls)
DRenderFB → Framebuffer
DSurface → Allocate/Deallocate (system memory)
DDrawPixel → DSurface
DCompose → DComposeTypes, DComposeFloat, DComposeStack, DComposeBSP, DRing0-3
Fonts → VIF, TVG (for glyph parsing)
VIF → (self-contained TVG engine)
VIcon → VIF, DSurface
SurfaceBlit → DSurface
SuperSample → DSurface
AudioEngine → ALSA (libasound via syscalls)
```
