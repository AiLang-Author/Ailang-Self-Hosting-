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

`Library.Framebuffer.ailang` has a **choice path** in `FB_Init` — comment out the real `/dev/fb0` block and uncomment the headless anonymous mmap block. No separate function needed. `TestCode/test_main.ailang` uses this for resize stress testing.

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

## MemoryCopy Rollout Status

| # | File | Function | Status |
|---|------|----------|--------|
| 1 | Library.Framebuffer.ailang | `FB_Flip`, `FB_FlipFast` | Done |
| 2 | Library.SurfaceBlit.ailang | `Surface_BlitOpaque` | Done |
| 3 | Library.WinRender.ailang | `Win_BlitOne`, `Win_BlitClamped` | Uses MemoryCopy with flattened vars |
| 4 | Library.Deskbar.ailang | `Deskbar_Draw` | Done |
| 5 | Library.DDrawPixel.ailang | `Draw_Pix_FillRect` | Done (dword StoreValue + MemoryCopy rows) |

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
- MemoryCopy in all blit/fill paths
- Draw_Pix_FillRect: dword StoreValue (no overflow) + MemoryCopy row duplication
- Window resize: 350+ cycles tested headless (grow, shrink, oscillate, batched, edge drag)
- 86/86 smoke tests pass, 57/57 CoreUtils build

### Build & Run

```
./ailang.x Main.ailang SysDisplay.x
# Switch to TTY: Ctrl+Alt+F2
./SysDisplay.x
# ESC to quit
```

### Test Programs (TestCode/)

- `test_main.ailang` — full system headless resize stress test (350+ cycles)
- `test_offscreen_render.ailang` — 4 render tests (toolbar, menu, deskbar, file dialog)

### Tools

- `./analyzer.x Main.ailang` — full import chain static analysis (arity, double frees, etc.)
- `tools/relmem.py` — memory context builder

### Pending Work

- Deskbar rewrite phases 2-4 (PostgreSQL services, About dialog, fork/exec)
- SSE optimizations (future, one site at a time)
