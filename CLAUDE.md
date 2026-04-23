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

## Next Up: Deskbar Rewrite and Expansion

User queued this as the next major task after theming.
