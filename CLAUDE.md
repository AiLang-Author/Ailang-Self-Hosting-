# Project Memory

## Architecture Notes

- **AKContext system (refactored 2026-04-22):** Replaced global AKTree/AKExtraTable/AKEvent state with explicit `LinkagePool.AKContext` handles. Each context (main window, toolbar, deskbar, menu, dialog) owns its own node buffer, extra table, and event state. No more slot swapping or global corruption. `AK_CreateContext()` allocates, all AK_* functions take `ctx` as first param.
- Toolbar actions fire on UP (not DOWN). Action string -> EventRouter queue -> `EventRouter_Drain` in main loop dispatches.
- `Menu_Show` creates its own AKContext, builds tree, renders to surface, destroys context. Surface stored in MenuState. `Menu_Blit` called from `Win_BlitAll`.
- Main loop: Evdev_Poll -> DrainInput -> AK_DrawDirty -> Win_RenderDirty -> EventRouter_Drain -> DebugLog_Render -> Win_BlitAll -> sleep(16ms).
- Deskbar has its own AKContext stored in `DeskbarState.ak_ctx`. No global swap needed.
- Each window toolbar has its own AKContext stored via `WinMgr_SetToolbarCtx(idx, ctx)`.

### DebugLog_Push Instrumentation

**Scope:** 475 `DebugLog_Push` calls across 16 library files. Every `Function.*` and `SubRoutine.*` has an entry tag. All risky calls have before/after checkpoint tags.

**Config:** `DebugLogConst.MAX_ENTRIES` = 256. Toggle with `DebugLog_Toggle()`, rendered by `DebugLog_Render()`.

**Tag convention:** `"<module>.<fn>"` or `"<module>.<fn>.X"`, max 9 chars. Second arg = string length.

## Completed: Preserve Canvas Content on Window Resize (2026-04-23)

Canvas drawing was lost on resize because `Win_UpdateResize` in `Library.WinInput.ailang` created a new content surface filled with solid background but never copied the old surface content. Fix: `Surface_BlitOpaque(new_content, old_content, 0, 0)` after background fill, before destroying old surface. Old content is preserved at top-left; new area gets background fill.

## Completed: Toolbar Re-render on Window Resize (2026-04-23)

Text disappeared from toolbars during window resize because `Win_UpdateResize` in `Library.WinInput.ailang` recreated the toolbar surface (blank solid fill) but never re-rendered the Auckland tree into it. There was a `// TODO: Phase C` comment where the call should have been. Fix: call `Win_RedrawToolbar(idx)` after surface recreation — this re-solves layout for new dimensions and draws text/buttons into the new surface.

## Completed: TextRegion Pool Exhaustion Fix (2026-04-23)

Text disappeared on 2nd/3rd windows because the global TextRegion pool (32 slots) was a bump allocator that never freed handles. Each `AK_DestroyContext` (menus, dialogs) and `AK_ResetContext` (deskbar refresh) leaked all TR_HANDLEs — once 32 slots consumed, `TextRegion_Create` returned -1 and text rendering stopped.

**Fix:**
- `Library.TextRegion.ailang`: Added free stack (`TRState.free_stack`, `TRState.free_top`). `TextRegion_Create` checks free stack before bumping count. New `TextRegion_Free(handle)` pushes handle onto free stack. Pool size increased 32 → 256 for headroom.
- `Library.Auckland.ailang`: New `AK_FreeContextTR(ctx)` iterates a context's extra table and calls `TextRegion_Free` for each valid `TR_HANDLE`. Called from both `AK_DestroyContext` and `AK_ResetContext` **before** buffer zeroing/dealloc.

**Result:** TR handles are recycled when contexts are destroyed or reset. Pool no longer leaks.

## Completed: HBOX MIN_W Layout Fix (2026-04-23)

Fixed deskbar rendering corruption (duplicated glyphs, overlapping zones, clipped right edge, invisible separators). Root cause: `AK_LayoutNode` HBOX pass and `AK_MeasureNode` used `AKF.WIDTH` for base width calculation, but deskbar buttons only set `AKF.MIN_W`. All buttons contributed 0 to space distribution, so the center GROW zone absorbed the full width and left/right zones collapsed to 0.

**Fix:** Added `MIN_W` fallback in 3 sites in `Library.Auckland.ailang`:
- `AK_MeasureNode` HBOX child width accumulation (+ symmetric MIN_H for VBOX)
- `AK_LayoutNode` HBOX first pass (total_base accumulation)
- `AK_LayoutNode` HBOX second pass (per-child base_w for positioning)

When `WIDTH=0` and `MIN_W>0`, MIN_W is used as the effective base width. This is correct CSS-like behavior — MIN_W should be the floor for layout space reservation.

## Completed: Framebuffer Bounds Checking (2026-04-22)

Added full 4-edge framebuffer clamping to `Win_BlitOne`, `Win_BlitClamped`, and `Win_DrawBorderFB` in `Library.WinRender.ailang`. Prevents segfaults when windows are partially off-screen.

## Completed: AKContext Refactor (2026-04-22)

Replaced global AKTree/AKExtraTable/AKEvent with explicit `LinkagePool.AKContext` handles. Fixed toolbar menu freeze caused by global state corruption during slot swapping. All AK_* functions now take `ctx` as first parameter. Commit: `1f65c03`.

## Completed: UIScale DPI System (2026-04-23)

- `Librarys/Library.UIConfig.ailang` — key=value config parser, supports `0x` hex, 128-entry max
- `Librarys/Library.UIScale.ailang` — DPI-aware dimension scaling, reads from `config/ui.cfg`
- `config/ui.cfg` — central config file for dimensions and colors
- All dimension constants across WinToolbar, Deskbar, WinRender, Menu, FileDialog, Dialog read from `UIScale.*`

## Completed: SVG Tooling + Widget Icons (2026-04-23)

- `tools/svg2tvg.py` — extended for widget SVGs (gradients, transforms, complex paths)
- `tools/pack_widget_vif.py` — batch packs TVG files into VIF container
- 63 Silver system atom SVGs converted to TVG and packed into `icons/silver_atoms.vif`
- Fixed stroke path reversal bug and gradient coordinate mismatch in SVG→TVG converter

## Completed: UI Theming System (2026-04-23)

Centralized all hardcoded color values into a single config-driven theme system.

### Files

- **`Librarys/Library.UITheme.ailang`** (NEW) — `FixedPool.Theme` with 42 color fields (all `CanChange=True`), `UITheme_Init()` loads from `config/ui.cfg` with fallback defaults
- **`config/ui.cfg`** — extended with 42 ARGB hex color entries (all optional, defaults match previous hardcoded values)

### Init Sequence (in Library.SysDisplay.ailang)

```
UIConfig_Load("config/ui.cfg")
UITheme_Init()          // loads Theme.* from config
UIScale_Init(w, h)      // loads UIScale.* from config
PaneDecorator_ScaleInit()
PaneDecorator_ThemeInit()  // copies Theme.* → WinColor.*
```

### Color Migration Summary

| File | Sites | What changed |
|------|-------|-------------|
| Library.PaneDecorator.ailang | 9 | WinColor fields CanChange=True, bridge function copies Theme→WinColor |
| Library.WinToolbar.ailang | 6 | toolbar_bg, text_secondary, toolbar_close_bg/fg |
| Library.Deskbar.ailang | 8 | deskbar_bg, btn_bg/fg, btn2_bg/fg (hotzone checkerboard raw bytes kept) |
| Library.WinRender.ailang | 4 | tabbar_bg, tab_active_bg, tab_icon, tab_text |
| Library.Menu.ailang | 4 | menu_bg/fg/sep via MenuConst bridge, menu_border |
| Library.Auckland.ailang | 7 | ak_sep, ak_btn_bg/fg, ak_btn_border/hover/pressed, text_disabled |
| Library.FileDialog.ailang | 7 | fd_path_text, fd_list_bg/border, fd_sep, fd_dir/file/empty_text |

### Theme Color Groups (FixedPool.Theme keys)

- Desktop/window: `desktop_bg`, `window_bg`, `dialog_bg`, `panel_bg`, `terminal_bg`
- Chrome: `border`, `header_color`
- Text: `text_fg`, `text_bg`, `text_secondary`, `text_disabled`, `text_light`
- Toolbar: `toolbar_bg`, `toolbar_close_bg`, `toolbar_close_fg`
- Deskbar: `deskbar_bg`, `deskbar_btn_bg/fg`, `deskbar_btn2_bg/fg`, `deskbar_hot_fg/bg`
- Tabs: `tabbar_bg`, `tab_active_bg`, `tab_icon`, `tab_text`
- Menu: `menu_bg`, `menu_fg`, `menu_sep`, `menu_border`
- Auckland: `ak_sep`, `ak_btn_bg/fg`, `ak_btn_border/hover/pressed`
- FileDialog: `fd_path_text`, `fd_list_bg/border`, `fd_sep`, `fd_dir/file/empty_text`
- Debug: `debug_bg`

### Important Notes

- Dynamic color modifications (hover lighten +30, press darken -30, disabled grayscale) in Auckland button rendering stay as runtime computation — only the base/fallback colors are themed
- Deskbar hotzone checkerboard (raw SetByte for BGRA channels) not themed — would need color unpacking utility
- `UIConfig MAX_ENTRIES` = 128 (25 dimension + 42 color = 67 used)

**Last commit:** `b5b613a` on `ak-context-refactor` — all theming work saved

## In Progress: Deskbar Rewrite (2026-04-23)

Full plan at: `.claude/plans/transient-sauteeing-pike.md`

### Vision

Rewrite placeholder deskbar into full system bar with 3 zones:
- **Left**: App launchers from PostgreSQL `services` table
- **Center**: Live window list (click to focus, auto-refreshes on create/close/focus)
- **Right**: System tray (user label, About dialog)

PostgreSQL is the backbone — `services` table already exists with binary_path/args/enabled/priority. Convention: `binary_path = "internal:action.name"` fires EventRouter action, otherwise fork/exec.

### Phase Plan

1. **Phase 1**: Three-zone layout + window list + `AK_ResetContext` + refresh triggers
2. **Phase 2**: PostgreSQL service loading + dynamic launchers + `svc.N` routing + `display_name` column + default service seeds
3. **Phase 3**: About dialog (new `Library.AboutDialog.ailang`)
4. **Phase 4**: Fork/exec service launching (SystemCall 57/59)

### Key Technical Decisions

- **`AK_ResetContext(ctx)`** needed in Library.Auckland.ailang — zeros node+extra buffers without dealloc/realloc. Critical for tree rebuild on window list refresh.
- **Refresh trigger**: `DeskbarState.needs_refresh = 1` set in `Win_Create`/`Win_Close`/`Win_Focus`, checked in main loop after `EventRouter_Drain`
- **Pre-allocated action strings**: `"wf.1"` through `"wf.7"` avoid allocation per refresh (max 8 windows)
- **Service ID actions**: `"svc.N"` where N is services.id from postgres
- **Internal actions**: services with `binary_path = "internal:win.new"` strip prefix and push to EventRouter

### New Theme Colors Added

- `deskbar_win_bg`, `deskbar_win_fg`, `deskbar_win_act_bg`, `deskbar_sep`

### New UIScale Dimensions Added

- `deskbar_win_btn_w` (96px default)

### PostgreSQL Tables Used

- `services` — app registry (name, display_name, binary_path, enabled, priority)
- `service_status` — runtime PID tracking (service_id, pid, state, started_at)
- `users` — user info for system tray label

### Files Modified Per Phase

| Phase | New Files | Modified Files |
|-------|-----------|----------------|
| 1 | — | Auckland, Deskbar, EventRouter, SysDisplay, WinManager, UITheme, UIScale, ui.cfg |
| 2 | — | Deskbar, EventRouter, SysDisplay |
| 3 | Library.AboutDialog.ailang | EventRouter, SysDisplay |
| 4 | — | Deskbar |

**Last commit:** `826e151` on `ak-context-refactor` — all prior work saved

## Completed: Screenshot PPM Support (2026-04-23)

Added PPM (P6) output mode to `Library.Screenshot.ailang` alongside existing BMP. PPM chosen because Claude Code's Read tool segfaults on BMP files but handles PNG/JPG/PPM reliably.

### Files

- **`Librarys/Library.Screenshot.ailang`** (NEW) — `Screenshot_Save()` (BMP) + `Screenshot_SavePPM()` (PPM P6) + `SS_WriteDecimal()` helper
- **`Librarys/Library.EventRouter.ailang`** — `sys.screenshot` action now calls both `Screenshot_SavePPM()` then `Screenshot_Save()`

### Output Files

- `/tmp/screenshot.ppm` — PPM P6 binary (RGB, top-to-bottom, no padding, no compression). Use this for Claude Code viewing.
- `/tmp/screenshot.bmp` — 24-bit BMP (BGR, bottom-up, padded). Fallback for standard image viewers.

### PPM Format Notes

- Header: ASCII `"P6\n{width} {height}\n255\n"` followed by raw RGB bytes
- Pixel conversion: BGRA (framebuffer) → RGB (swap B↔R, drop alpha)
- Rows: top-to-bottom (no reversal needed unlike BMP)
- No row padding required
- To convert for external use: `convert /tmp/screenshot.ppm /tmp/screenshot.png`
