# Project Memory

## Architecture Notes

- **AKContext system:** Explicit `LinkagePool.AKContext` handles. Each context (main window, toolbar, deskbar, menu, dialog) owns its own node buffer, extra table, and event state. `AK_CreateContext()` allocates, all AK_* functions take `ctx` as first param.
- Toolbar actions fire on UP (not DOWN). Action string -> EventRouter queue -> `EventRouter_Drain` in main loop dispatches.
- `Menu_Show` creates its own AKContext, builds tree, renders to surface, destroys context. Surface stored in MenuState. `Menu_Blit` called from `Win_BlitAll`.
- Main loop: Evdev_Poll -> DrainInput -> AK_DrawDirty -> Win_RenderDirty -> EventRouter_Drain -> DebugLog_Render -> Win_BlitAll -> sleep(16ms).
- Deskbar has its own AKContext stored in `DeskbarState.ak_ctx`. No global swap needed.
- Each window toolbar has its own AKContext stored via `WinMgr_SetToolbarCtx(idx, ctx)`.

### Compiler Constraints

- **6-arg limit**: The compiler targets SysV AMD64's 6 register args (RDI, RSI, RDX, RCX, R8, R9) with no spill. `analyzer.x` arity checker enforces this. Functions needing >6 values must use FixedPool globals for extras.
- **StoreValue**: Defaults to 8-byte (qword) writes. Use `StoreValue(addr, val, "dword")` for 4-byte writes to avoid buffer overflow on pixel data.
- **MemoryCopy/MemorySet**: Emit `CLD` + `REP MOVSB/STOSB` with register save/restore (RSI, RDI, RCX). Safe to use in loops.

### Compiler SSE2 Infrastructure (existing)

- **FPU SSE2 emission**: `Librarys/Compiler/Compile/FPU/X86/Library.FPUEmitX86SSE.ailang` — has scalar/packed double arithmetic (ADDSD, SUBSD, MULSD, DIVSD, SQRTSD, MOVSD, MOVAPD, etc.)
- **FPU SSE2 compilation**: `Librarys/Compiler/Compile/FPU/X86/Library.FPUCompileX86SSE.ailang` — handles Float_Add/Sub/Mul/Div, Vec2 ops, ISqrt, Abs, Min, Max
- **No integer SSE2 yet**: No MOVDQU, PXOR, PUNPCKLBW, etc. — needs new emit functions for memory optimization
- **Byte emission**: `Emit_Byte(b)` in `Library.CEmitCore.ailang:223` writes raw bytes to code buffer
- **MemoryCopy compilation**: `Library.CCompileMem.ailang:543-594` — emits PUSH RSI/RDI/RCX + CLD + REP MOVSB + POP
- **MemorySet compilation**: `Library.CCompileMem.ailang:600-651` — emits PUSH RDI/RCX + CLD + REP STOSB + POP
- **String instructions**: `Library.CEmitX86String.ailang` — X86_RepMovsb (F3 A4), X86_RepStosb (F3 AA), X86_RepMovsq (48 F3 A5), X86_RepStosq (48 F3 AB)

### DebugLog_Push Instrumentation

**Scope:** 475 `DebugLog_Push` calls across 16 library files. Every `Function.*` and `SubRoutine.*` has an entry tag.
**Config:** `DebugLogConst.MAX_ENTRIES` = 256. Toggle with `DebugLog_Toggle()`, rendered by `DebugLog_Render()`.
**Tag convention:** `"<module>.<fn>"` or `"<module>.<fn>.X"`, max 9 chars. Second arg = string length.

### Init Sequence (Library.SysDisplay.ailang)

```
UIConfig_Load("config/ui.cfg")
UITheme_Init()          // loads Theme.* from config
UIScale_Init(w, h)      // loads UIScale.* from config
PaneDecorator_ScaleInit()
PaneDecorator_ThemeInit()  // copies Theme.* -> WinColor.*
```

### Headless Testing

`Library.Framebuffer.ailang` has a **choice path** in `FB_Init` — comment out the real `/dev/fb0` block and uncomment the headless anonymous mmap block. No separate function needed. `TestCode/test_main.ailang` uses this for resize stress testing. When switching to headless, also remove the `RenderFB_InitDouble` override in test_main.ailang (the library's own init path handles it).

## Completed Work (Condensed)

| Date | Fix | Key Detail |
|------|-----|-----------|
| 04-22 | AKContext refactor | Global state -> explicit context handles. Commit `1f65c03` |
| 04-22 | Framebuffer bounds checking | 4-edge clamping in Win_BlitOne/BlitClamped/DrawBorderFB |
| 04-23 | Canvas resize fixes | Background color sampling, content preservation, toolbar re-render |
| 04-23 | TextRegion pool fix | Free stack recycling, pool 32->256 slots |
| 04-23 | HBOX MIN_W layout fix | MIN_W fallback in AK_MeasureNode/AK_LayoutNode |
| 04-23 | UIScale DPI system | `config/ui.cfg` key=value parser, DPI-aware dimensions |
| 04-23 | SVG tooling + widget icons | 63 Silver system atom SVGs -> TVG -> VIF |
| 04-23 | UI theming system | 42 colors in FixedPool.Theme, loaded from config/ui.cfg |
| 04-23 | CLD fix for REP MOVSB/STOSB | Added CLD before REP instructions. Commit `ce0c420` |
| 04-23 | Register save/restore for REP | Push/pop RSI,RDI,RCX around REP MOVSB; RDI,RCX around REP STOSB |
| 04-23 | Screenshot PPM support | `/tmp/screenshot.ppm` (P6) + `/tmp/screenshot.bmp` (24-bit) |
| 04-23 | MemoryCopy rollout sites 1,2,4 | FB_Flip/FlipFast, Surface_BlitOpaque, Deskbar_Draw |
| 04-24 | Stack leak fix >6-arg calls | ADD RSP cleanup after MOV RSP,R12 for args 7+ |
| 04-24 | VInst_DrawString 7-arg fix | Color moved to FontState.draw_color global (7->6 params) |
| 04-24 | VFont_UseSize caching | Instance caching instead of flush+raster on every size switch |
| 04-24 | TVG rasterizer hardening | Function split (33+ vars), bounds checks, debug prints removed |
| 04-24 | FB_FontDefineChar refactor | 10 args -> 2 args (char + packed 64-bit int) |
| 04-24 | Draw_Pix_FillRect overflow fix | StoreValue qword->dword + MemoryCopy row duplication |
| 04-24 | Text clipping on resize fix | `AK_FreeContextTR(ak_ctx)` before `Win_RedrawToolbar` in `Win_UpdateResize` |
| 04-24 | Win_DrawBorderFB rewrite | SetByte x4 per pixel -> StoreValue dword + MemoryCopy row duplication |
| 04-24 | Border color -> gunmetal | `border=0xFF4A4A50` (was white 0xFFFFFFFF) — visible on any canvas |
| 04-24 | Debug overlay rewrite | Own surface (dbg_surf 700x400), blitted after windows in Win_BlitAll — always on top, no crash on Win_Create |
| 04-24 | FB_FillRectFast optimization | StoreValue dword + MemoryCopy rows (was 4 SetByte per pixel) |
| 04-24 | FB_HLine/VLine optimization | StoreValue dword per pixel (was FB_Write32 = 4 SetByte + DebugLog_Push) |
| 04-24 | Deskbar_DrawHotzone optimization | StoreValue dword per pixel (was 4 SetByte per pixel) |
| 04-24 | Doc_WriteText clipping fix | TextRegion height = remaining space from cursor to content bottom (was full content height) |
| 04-24 | App_BlitPageToWindow MemoryCopy | Main.ailang byte-by-byte blit -> MemoryCopy per row |
| 04-24 | MemoryCopy/MemorySet rollout | 15 sites: RenderFB_Flush/FlushRect, AK_ResetContext, VIF_Init ×3, VFont_Init ×2, VFont_LoadFace, FB_Init ×2, TextRegion_Init, Dialog_Init, Doc_Init, CursorBitmap ×2 |
| 04-24 | Doc content redraw on resize | PageSurface_Resize + App_RefreshDocWindow — page resized, cursor reset, text re-rendered, re-blitted on Win_ApplyResize |

## MemoryCopy Rollout Status

| # | File | Function | Status |
|---|------|----------|--------|
| 1 | Library.Framebuffer.ailang | `FB_Flip`, `FB_FlipFast` | Done |
| 2 | Library.SurfaceBlit.ailang | `Surface_BlitOpaque` | Done |
| 3 | Library.WinRender.ailang | `Win_BlitOne`, `Win_BlitClamped` | Uses MemoryCopy with flattened vars |
| 4 | Library.Deskbar.ailang | `Deskbar_Draw` | Done |
| 5 | Library.DDrawPixel.ailang | `Draw_Pix_FillRect` | Done (dword StoreValue + MemoryCopy rows) |
| 6 | Library.WinRender.ailang | `Win_DrawBorderFB` | Done (dword StoreValue + MemoryCopy rows) |
| 7 | Library.Framebuffer.ailang | `FB_FillRectFast` | Done (dword StoreValue + MemoryCopy rows) |
| 8 | Library.Framebuffer.ailang | `FB_HLine` | Done (StoreValue dword per pixel) |
| 9 | Library.Framebuffer.ailang | `FB_VLine` | Done (StoreValue dword per pixel) |
| 10 | Library.Deskbar.ailang | `Deskbar_DrawHotzone` | Done (StoreValue dword per pixel) |
| 11 | Library.DRenderFB.ailang | `RenderFB_Flush` | Done (MemoryCopy per row) |
| 12 | Library.DRenderFB.ailang | `RenderFB_FlushRect` | Done (MemoryCopy per row) |
| 13 | Library.Auckland.ailang | `AK_ResetContext` | Done (MemorySet ×2) |
| 14 | Library.VIF.ailang | `VIF_Init` | Done (MemorySet ×3) |
| 15 | Library.Fonts.ailang | `VFont_Init`, `VFont_LoadFace` | Done (MemorySet ×3) |
| 16 | Library.Framebuffer.ailang | `FB_Init` | Done (MemorySet ×2) |
| 17 | Library.TextRegion.ailang | `TextRegion_Init` | Done (MemorySet) |
| 18 | Library.Dialog.ailang | `Dialog_Init` | Done (MemorySet) |
| 19 | Library.Document.ailang | `Doc_Init` | Done (MemorySet) |
| 20 | Library.CursorBitmap.ailang | `CursorBitmap_AllocMasks` | Done (MemorySet ×2) |

## SSE2 Optimization Plan (In Progress)

### Phase 1: Replace expensive byte-by-byte loops with MemoryCopy/MemorySet (no compiler changes needed)

| # | File | Function | Lines | Current | Target | Status |
|---|------|----------|-------|---------|--------|--------|
| 1 | Library.DRenderFB.ailang | `RenderFB_Flush` | 107-111 | GetByte/SetByte per byte | MemoryCopy per row | Done |
| 2 | Library.DRenderFB.ailang | `RenderFB_FlushRect` | 173-177 | GetByte/SetByte per byte | MemoryCopy per row | Done |
| 3 | Library.Auckland.ailang | `AK_ResetContext` | 320-326 | SetByte per byte (two loops) | MemorySet zero fill | Done |
| 4 | Library.Framebuffer.ailang | `FB_ClearBuffer` | 414-418 | FB_Write32 per pixel | MemorySet or StoreValue+MemoryCopy | Pending |
| 5 | Library.Framebuffer.ailang | `FB_FillRectFast` | 717-731 | SetByte x4 per pixel | StoreValue dword + MemoryCopy rows | Done |
| 6 | Library.Framebuffer.ailang | `FB_HLine` | 614-618 | SetByte x4 per pixel | StoreValue dword per pixel | Done |
| 7 | Library.Framebuffer.ailang | `FB_VLine` | 651-655 | SetByte x4 per pixel | StoreValue dword per pixel | Done |
| 8 | Library.VIF.ailang | Buffer zero-init | 221,232,243 | SetByte per byte | MemorySet zero fill | Done |
| 9 | TestCode/test_main.ailang | `App_BlitPageToWindow` | 418-421 | GetByte/SetByte per byte | MemoryCopy per row | Done |
| 10 | Library.Fonts.ailang | `VFont_Init` | 170,178 | SetByte per byte (two loops) | MemorySet zero fill | Done |
| 11 | Library.Fonts.ailang | `VFont_LoadFace` | 334 | SetByte per byte | MemorySet zero fill | Done |
| 12 | Library.Framebuffer.ailang | `FB_Init` | 183-192 | SetByte per byte (two loops) | MemorySet zero fill | Done |
| 13 | Library.TextRegion.ailang | `TextRegion_Init` | 72 | SetByte per byte | MemorySet zero fill | Done |
| 14 | Library.Dialog.ailang | `Dialog_Init` | 81-85 | SetByte per byte | MemorySet zero fill | Done |
| 15 | Library.Document.ailang | `Doc_Init` | 58-62 | SetByte per byte | MemorySet zero fill | Done |
| 16 | Library.CursorBitmap.ailang | `CursorBitmap_AllocMasks` | 87-92 | SetByte per byte (two masks) | MemorySet zero fill × 2 | Done |

### Phase 2: Add integer SSE2 emit functions to compiler

New functions needed in `Library.FPUEmitX86SSE.ailang`:
- `X86_Movdqu_Load(xmm, reg)` — MOVDQU XMMn, [reg] (load 128-bit unaligned)
- `X86_Movdqu_Store(reg, xmm)` — MOVDQU [reg], XMMn (store 128-bit unaligned)
- `X86_Movdqa_Load/Store` — aligned 128-bit variants
- `X86_Pxor(xmm1, xmm2)` — XOR for zero-init
- `X86_Pshufd(xmm1, xmm2, imm)` — broadcast dword to all 4 lanes
- `X86_Punpcklbw` etc. for byte manipulation

### Phase 3: Add SSE2 compiler intrinsics

New intrinsics in `Library.CCompileMem.ailang`:
- `MemoryCopy16(dst, src, count)` — 16-byte aligned MOVDQA loop with REP MOVSB tail
- `MemorySet16(dst, val, count)` — 16-byte MOVDQA fill loop with REP STOSB tail
- `MemoryZero16(dst, count)` — PXOR XMM0,XMM0 + MOVDQA loop

### Impact Priority (highest first)

1. **RenderFB_Flush/FlushRect** — called per-frame for surface->FB copy, now MemoryCopy per row (DONE)
2. **FB_FillRectFast** — used for direct FB rectangle fills, now StoreValue dword + MemoryCopy (DONE)
3. **FB_HLine/VLine** — used for line drawing, 4 SetByte per pixel
4. **AK_ResetContext** — called on deskbar refresh, zero-fills two buffers byte-by-byte
5. **FB_ClearBuffer** — buffer initialization
6. **VIF buffer init** — font rasterizer zero-fill

## Bugs Fixed This Session (04-24, details for debugging)

### Bug 1: Text clipping on resize (FIXED)

**Root cause**: `Win_UpdateResize` (Library.WinInput.ailang:408-430) created new toolbar surfaces and called `Win_RedrawToolbar(idx)` but the AKContext's old TextRegion handles persisted with stale clipping bounds from the old surface dimensions. When `AK_DrawNode` ran, it found existing TR handles (`tr >= 0`) and called `TextRegion_SetRect/SetSurface`, but the old handles had cached internal state that didn't fully update.

**Fix**: Added `AK_FreeContextTR(ak_ctx)` call at line 422-426 before `Win_RedrawToolbar`. This frees all TextRegion handles in the extra table, so `AK_DrawNode` sees `tr < 0` and creates fresh handles with correct bounds from the re-solved layout.

**Why AK_FreeContextTR not AK_ResetContext**: `AK_ResetContext` zeros the entire tree (node buffer + extra buffer + counters), destroying the toolbar's node structure. `AK_FreeContextTR` only walks the extra table freeing TR handles, preserving the tree so `AK_Draw` -> `AK_Solve` -> `AK_DrawNode` can re-measure, re-layout, and re-draw with fresh TextRegions.

### Bug 2: Window borders not visible (FIXED)

**Root cause**: `Win_DrawBorderFB` (Library.WinRender.ailang:245-354) used 4x `SetByte` per pixel to write BGRA channels individually, and hardcoded alpha byte to 0: `SetByte(buf, Add(off, 3), 0)`. The color `WinColor.BORDER = 0xFFFFFFFF` (white with alpha=0xFF from config/ui.cfg `border=0xFFFFFFFF`) was being decomposed into separate bytes with alpha discarded.

**Fix**: Rewrote to use `StoreValue(addr, col, "dword")` which writes the full 32-bit color (including alpha=0xFF) in one instruction, plus `MemoryCopy` for row duplication. Four border strips (top/bottom/left/right) each fill one row with dword writes, then MemoryCopy remaining rows. Proper bounds clamping preserved for all 4 strips.

**Performance**: Old: 4 SetByte calls per pixel (~22,000 function calls per window border). New: 1 StoreValue per pixel in first row + MemoryCopy for remaining rows.

### Bug 3: Debug overlay crash on Win_Create + text vanishing under windows (FIXED)

**Root cause (crash)**: `DebugLog_Render` created a `TextRegion` handle (`dbg_tr`) bound to `desktop_surf` and cached it forever. When toggling debug off, the TR was never freed, leaking pool slots. Combined with toolbar TRs from new windows, the 256-slot pool could exhaust, causing `TextRegion_Create` to return -1 and `TR_Ptr(-1)` to compute an invalid address → segfault.

**Root cause (vanishing)**: The debug overlay was drawn to `desktop_surf` (z=0, bottom of compositing stack). `Win_BlitAll` composited the desktop first, then blitted windows on top. Any window overlapping the overlay region (10,140, 700x400) overwrote the debug text in the framebuffer.

**Fix**: Complete rewrite of `DebugLog_Render` lifecycle:
1. Created dedicated `SysDisplayState.dbg_surf` (700x400 surface) — debug overlay renders here, not `desktop_surf`
2. TextRegion coordinates changed from desktop-absolute (14,144) to surface-relative (4,4)
3. `Win_BlitAll` now blits `dbg_surf` at (10,140) **after** all windows + deskbar + menu, **before** cursor — always on top
4. `DebugLog_Toggle` OFF path frees both `dbg_tr` (via `TextRegion_Free`) and `dbg_surf` (via `Surface_Destroy`), resetting both to 0 — no TR pool leaks
5. Shutdown path also frees both resources
6. Forced `SysDisplayState.dirty = 1` every frame when debug enabled (FPS/stats update)

### Bug 4: Window border color invisible on white canvas (FIXED)

**Root cause**: `border=0xFFFFFFFF` (white) in config/ui.cfg — identical to default canvas/document backgrounds.

**Fix**: Changed to `border=0xFF4A4A50` (dark gunmetal gray) — highly distinctive, unlikely to match any canvas color.

### Bug 5: Doc_WriteText TextRegion clipping extends past page (FIXED)

**Root cause**: `Doc_WriteText` (Library.Document.ailang:345-350) created each TextRegion with `ch = PageSurface_GetContentH(page)` — the full content area height (e.g. 468px). This height was used regardless of the cursor's current Y position. When cursor was at Y=200, the TextRegion had bounds `(16, 200, 588, 468)`, computing `bottom_edge = 200 + 468 = 668` — far past the actual page surface boundary (500px). While `Surface_BlitTinted` clips at the surface edge, the TextRegion's internal layout believed it had 468px of room below the cursor, causing incorrect wrapping and overflow calculations.

**Fix**: Changed `ch` to compute remaining space from cursor to the bottom content edge: `ch = (content_y + content_h) - cy`. For example: cursor at Y=200, content_y=16, content_h=468 → `ch = (16+468) - 200 = 284`. The TextRegion now correctly knows how much vertical room remains. Returns early if `ch <= 0` (cursor past content bottom).

### Bug 6: Document canvas text not redrawing on window resize (FIXED)

**Root cause**: `Win_UpdateResize` (Library.WinInput.ailang:293-442) creates new content surfaces on every mouse move during resize, copies old pixels via `Surface_BlitOpaque`, but the document's **page surface** (in PageTable) is never resized and `Doc_WriteText` is never called again. Expanded areas show only the background color fill. The page surface retains its original dimensions from `App_CreateDocWindow` forever.

**Fix** (4 files):
1. **Library.PageSurface.ailang** — Added `PageSurface_Resize(page, w, h)`: destroys old surface, creates new one at new dimensions, fills white, updates PageTable metadata in-place (no slot leak).
2. **Main.ailang (App_CreateDocWindow)** — Now stores doc/page handles per-window via `WinView_SetDocHandle(win_idx, doc)` / `WinView_SetPageHandle(win_idx, page)`. These accessors already existed in WinManager but were unused.
3. **Main.ailang (App_RefreshDocWindow)** — New function: reads doc/page from WinView, calls `PageSurface_Resize` to match new canvas dims, restores 16px margins, resets doc cursor to (0,0), calls `App_WriteContent(doc)` to re-render all text, calls `App_BlitPageToWindow` to copy page to content surface.
4. **Library.WinInput.ailang (Win_ApplyResize)** — On mouse UP, checks `WinView_GetDocHandle(idx) >= 0` and calls `App_RefreshDocWindow(idx)`. This defers re-rendering to mouse release (not every pixel of drag), matching standard window manager behavior.

**Why mouse UP not every mouse move**: `Win_UpdateResize` already recreates surfaces on every move (expensive). Adding full doc re-render per move would add VFont_UseSize + 11× Doc_WriteText + TextRegion_Create/Render/Measure + MemoryCopy blit per pixel of drag. Deferring to UP means the user sees bg color in expanded areas during drag, then text appears on release.

**WinView defaults**: `WinView_Init` and `WinView_Clear` both set `DOC_HANDLE = -1` and `PAGE_HANDLE = -1`, so windows without documents are safely skipped by the `>= 0` check.

## In Progress: Deskbar Rewrite

Full plan at: `.claude/plans/transient-sauteeing-pike.md`

### Vision

Rewrite placeholder deskbar into full system bar with 3 zones:
- **Left**: App launchers from PostgreSQL `services` table
- **Center**: Live window list (click to focus, auto-refreshes on create/close/focus)
- **Right**: System tray (user label, About dialog)

### Phase Plan

1. **Phase 1**: Three-zone layout + window list + `AK_ResetContext` + refresh triggers
2. **Phase 2**: PostgreSQL service loading + dynamic launchers + `svc.N` routing
3. **Phase 3**: About dialog (new `Library.AboutDialog.ailang`)
4. **Phase 4**: Fork/exec service launching (SystemCall 57/59)

### Key Technical Decisions

- `AK_ResetContext(ctx)` zeros node+extra buffers without dealloc/realloc
- Refresh trigger: `DeskbarState.needs_refresh = 1` set in `Win_Create`/`Win_Close`/`Win_Focus`
- Pre-allocated action strings: `"wf.1"` through `"wf.7"` (max 8 windows)
- Theme colors: `deskbar_win_bg/fg`, `deskbar_win_act_bg`, `deskbar_sep`
- UIScale: `deskbar_win_btn_w` (96px default)

## Current State (2026-04-24)

### What's Working

- Full display server init pipeline through to document windows
- Font instance caching (VFont_UseSize)
- TVG vector font rasterization with hardened bounds checks
- MemoryCopy in all blit/fill paths (10 sites done)
- Draw_Pix_FillRect: dword StoreValue (no overflow) + MemoryCopy row duplication
- Win_DrawBorderFB: dword StoreValue + MemoryCopy (replaces 4x SetByte per pixel)
- FB_FillRectFast/HLine/VLine: StoreValue dword (replaces FB_Write32/SetByte x4)
- Deskbar_DrawHotzone: StoreValue dword (replaces SetByte x4)
- TextRegion handles freed on resize (AK_FreeContextTR) — no more stale clipping
- F12 debug overlay: own surface (dbg_surf), composited after windows, TR freed on toggle-off
- Border color: gunmetal 0xFF4A4A50 (visible on any canvas)
- Document content redraws on resize (PageSurface_Resize + App_RefreshDocWindow on Win_ApplyResize)
- Window resize: 350+ cycles tested headless (grow, shrink, oscillate, batched, edge drag)
- F12 debug overlay: 19-step headless stress test (toggle, open/close windows, resize, rapid cycling)
- 86/86 smoke tests pass, 57/57 CoreUtils build

### Build & Run

```
./ailang.x Main.ailang SysDisplay.x
# Switch to TTY: Ctrl+Alt+F2
./SysDisplay.x
# ESC to quit
```

### Test Programs (TestCode/)

- `test_main.ailang` — full system headless test: resize stress (9 steps) + F12 debug overlay stress (10 steps)
- `test_offscreen_render.ailang` — 4 render tests (toolbar, menu, deskbar, file dialog)

### Tools

- `./analyzer.x Main.ailang` — full import chain static analysis (arity, double frees, etc.)
- `tools/relmem.py` — memory context builder

### Pending Work

- Performance hunting: profile and optimize remaining hot paths before threading
- SSE2 optimization Phase 1 remaining: RenderFB_Flush/FlushRect (#1,#2 — CRITICAL per-frame), AK_ResetContext (#3), FB_ClearBuffer (#4), VIF buffer init (#8)
- SSE2 phases 2-3 (compiler integer SSE2 emit + intrinsics)
- Deskbar rewrite phases 2-4 (PostgreSQL services, About dialog, fork/exec)
- Display bug hunting (more issues likely lurking)
