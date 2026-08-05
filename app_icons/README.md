# AILANG Application & System Icons (32x32 TVG)

This directory contains source SVGs for application launcher icons and common system/action icons.

## Style
- 32x32 viewBox, consistent with VIcon APP tier rendering at `VIcon_SetSize(32)`.
- Windowed app icons use a dark frame + title bar with classic red/yellow/green traffic-light dots.
- Linear gradients for subtle depth (inspired by silver_system_atoms "silver" look but colored per theme).
- Symbolic content using rect, path (M/L/Q/C/Z), circle, and <linearGradient> in <defs>.
- Clean, low-detail, high-contrast for small rasterization via TVG parser.

## Pipeline
1. Add/edit .svg here (use descriptive hyphenated lowercase names, e.g. `text-editor.svg`).
2. `python3 tools/svg2tvg.py app_icons/ app_icons_tvg/`
3. `python3 tools/pack_widget_vif.py app_icons_tvg/ icons/app_icons.vif`
4. The pack is loaded at runtime into `IconTier.APP` (see Library.VIcon.ailang and SysDisplay).

## Current set (43 icons)
ai-chat, alert, battery, browser, calculator, clock, code, display, download, edit, file, folder, folder-open, gear, help, home, image, info, installer, keyboard, link, lock, mail, media-player, menu, music, network, notepad, paint, power, preferences, refresh, save, search, shutdown, start, terminal, trash, upload, user, video, volume, wifi.

## Adding more
- Prefer the windowed frame + dots for full "app" icons.
- For tiny action symbols, simpler centered glyphs work too.
- Test by compiling a small VIcon consumer or running the display tests.
- Names become the lookup keys in VIcon_Resolve("name").

Copyright © 2026 Sean Collins / AILANG project.
