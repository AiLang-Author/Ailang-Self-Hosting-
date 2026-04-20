# AILANG Display System — Cursor Design
*Author: Sean Collins, 2 Paws Machine and Engineering*
*Version: 1.0 — March 31, 2026*

---

## Architecture

```
Library.Cursor.ailang        — unified interface, config, dispatch, draw
Library.CursorBitmap.ailang  — built-in bitmap shapes (arrow/beam/crosshair/hand)
Library.CursorHVIF.ailang    — HVIF vector cursor loader (stub, impl pending)
```

## Design Principles

- **Config-driven** — caller sets `CursorConfig` before `Cursor_Init()`. No hardcoded shape.
- **Allocate once** — mask data allocated at load time, reused every frame. No per-frame allocation.
- **Save/restore** — pixels under cursor saved before draw, restored before next draw. No trail artifacts.
- **Orthogonal** — cursor knows nothing about BSP, surfaces, or Ring1. It only knows framebuffer.
- **Extensible** — new backends slot in via `CursorConfig.type`. Caller code unchanged.

## Data Flow

```
Evdev_Poll() → Ring1_Post(MOUSE_MOVE, x, y)
     ↓
DrainRing1 → Cursor_SetPos(x, y) → WBSPState.dirty = 1
     ↓
BlitAllSurfaces() → DrawCursor() → Cursor_Draw()
     ↓
Cursor_Restore()   — write saved pixels back to old position
Cursor_Save()      — save pixels at new position
Cursor_BlitMask()  — draw black outline, then white fill
FB_FlipFast()
```

## CursorState Fields

| Field | Purpose |
|-------|---------|
| `x, y` | Current cursor position (screen coords) |
| `shape` | Active shape index |
| `black_mask, white_mask` | Allocated mask buffers for current shape |
| `mask_w, mask_h, mask_stride` | Dimensions of current mask |
| `hotspot_x, hotspot_y` | Offset from top-left to click point |
| `save_buf` | Saved pixels under cursor (mask_w × mask_h × 4 bytes) |
| `save_x, save_y` | Position we saved from |
| `save_valid` | 1 = save_buf has valid data to restore |
| `scr_w, scr_h` | Screen bounds for clipping |

## Mask Format

Each shape has two masks — black outline and white fill — stored as packed bit arrays.

```
stride = ceil(mask_w / 8)
size   = mask_h * stride
bit(row, col) = (mask[row * stride + col/8] >> (7 - col%8)) & 1
```

MSB = leftmost pixel. Black mask drawn first (outline), white mask drawn on top (fill).

## Built-in Shapes

| Shape | Size | Hotspot |
|-------|------|---------|
| ARROW | 12×20 | (0, 0) top-left tip |
| BEAM | 3×18 | (1, 9) center of stem |
| CROSSHAIR | 15×15 | (7, 7) center pixel |
| HAND | 14×20 | (4, 0) fingertip |

## Adding a New Shape

1. Add constant to `FixedPool.CursorShape` in `Library.Cursor.ailang`
2. Add `CursorBitmap_LoadMyShape()` in `Library.CursorBitmap.ailang`
3. Add dispatch case in `CursorBitmap_Load()`
4. Define `FixedPool.MyShapeDim { W, H, STRIDE }`
5. Call `CursorBitmap_AllocMasks()` then populate rows with `SetRow1/SetRow2`

## HVIF Future

When `Library.CursorHVIF.ailang` is implemented:
- Set `CursorConfig.type = CursorType.HVIF`
- Set `CursorConfig.path` to `.hvif` file path
- `Cursor_Init()` calls `CursorHVIF_Load()` which rasterizes to black/white masks
- Everything above the mask level is unchanged

HVIF rasterizer will reuse bezier infrastructure from `Library.FontTTF.ailang` once that is implemented. Both share quadratic bezier curves and scan-line fill.

## Performance Notes

Current: full surface reblit on every mouse move event.
Fix (deferred): dirty rect per pane — only reblit the region under old cursor position.
The save/restore eliminates trail artifacts at zero cost beyond the rect copy.