# SysDisplay Progress Update
*Author: Sean Collins, 2 Paws Machine and Engineering*
*Date: April 2, 2026*

---

## Architecture Change: BSP Split → Float Layer

`TestWindowBSP.ailang` (700 lines, BSP-driven splits) has been refactored into:

```
Librarys/
  Library.PaneManager.ailang    — TBMap, pane lifecycle, sync, render, blit
  Library.InputRouter.ailang    — Ring1 drain, hotkeys, focus routing
  Library.SysDisplay.ailang     — init, shutdown, main loop orchestration
  Library.WinManager.ailang     — floating window management (NEW)
  Library.PaneDecorator.ailang  — color/style authority, no cycling (NEW)
  Library.DCompose.ailang       — compositor now COLORBLIND (refactored)

SysDisplay.ailang               — thin entry point (5 lines)
```

**Key architectural decision:** Windows are now Float layer entries, not BSP splits. BSP geometry engine is preserved for future tiling but SysDisplay no longer drives BSP splits directly.

---

## Window Model

Each window = three layers:

```
[ border_w = 4px  — FB geometry, never on canvas    ]
[ header canvas   — 20px, black bg, white title      ]
[ border_w = 4px  — separator between header/content ]
[ content canvas  — TB + user text                   ]
[ border_w = 4px  — bottom border                    ]
```

- **Canvas** = surface. Hard boundary. Nothing draws outside it.
- **Border** = drawn directly to FB, not on any surface.
- **Header** = its own surface. Future: tabs, widgets.
- `WinColor` pool in `PaneDecorator` is color authority. No cycling.

---

## Working Features

| Feature | Status |
|---------|--------|
| Desktop window (full screen) | ✅ |
| Alt+V — new floating window (80% size, centered) | ✅ |
| Alt+Q — close focused window | ✅ |
| ESC — quit | ✅ |
| Click to focus | ✅ |
| Drag header to move | ✅ |
| Drag border — geometry resizes correctly | ✅ |
| Horizontal border + canvas resize | ✅ |
| Window title in header | ✅ |
| Z-order (new window on top) | ✅ |
| Up to 8 windows | ✅ |
| Cursor changes to crosshair on border | ✅ |
| Desktop stays focused (index 0, uncloseable) | ✅ |
| Min window size 200x200 canvas | ✅ |

---

## Known Bugs

### Bug 1 — Desktop Wrong Height (200px bar)
- Desktop canvas renders with ~200px height instead of full screen height
- Root cause: unknown. Diagnostic prints needed in `SysDisplay_Start` before
  desktop `Win_Create` to read `Compositor.screen_h` — suspect `BSP_Init` not
  running or failing, leaving `Compositor.screen_h = 0`, causing clamp to fire
- See: `SysDisplay Bug Constitution — April 2026`

### Bug 2 — Vertical Border Resize Broken
- Horizontal resize (LEFT/RIGHT edges) works correctly including canvas recreation
- Vertical resize (TOP/BOTTOM edges) does not change window height
- Root cause: unknown. Diagnostic prints needed in `Win_UpdateResize` after `dy`
  is computed to read `dy`, `edge`, `orig_h`
- See: `SysDisplay Bug Constitution — April 2026`

---

## Non-Blocking Known Issues

| Issue | Notes |
|-------|-------|
| Desktop has border + header | idx=0 should be borderless. Skip `Win_DrawBorderFB` and separator in `Win_BlitAll` when `i == 0` |
| Resize debug spam | `Win_DebugPrint("RESIZE START")` fires on every mousedown on border. Remove before release |
| Desktop flicker on child window typing | Double buffer flip shows background briefly. Address with dirty region optimization |
| Surface recreation on every mouse move during resize | Known design issue. Move recreation to mouse-up (`Win_ApplyResize`) once resize is confirmed stable |

---

## Decorator Separation of Concerns

```
PaneDecorator  — color constants, SetFont, PaneDecorator_Draw
WinManager     — calls decorator, draws border to FB
SysDisplay     — picks color by name (WinColor.DESKTOP, WinColor.WINDOW)
DCompose       — COLORBLIND, geometry only
```

Future: JSON window descriptor → SysDisplay unpacks → Win_Create with all fields.

---

## File Sizes (approximate)

| File | LOC |
|------|-----|
| Library.WinManager.ailang | ~900 |
| Library.SysDisplay.ailang | ~300 |
| Library.PaneDecorator.ailang | ~80 |
| Library.DCompose.ailang | ~400 |
| SysDisplay.ailang | 8 |