# 08 — Documentation Corrections (Source Code Audit)

> **Audit Date:** 2026-05-16
> **Scope:** All 8 Display System docs vs live source in `Librarys/Display/`
> **Method:** Side-by-side comparison of docs against `.ailang` source, `fonts/`, `icons/`, `Librarys/deprecated/`

---

## Section A: Factual Errors

### A.1 — Font System Description (Critical)

**Where:** `07_PAIN_POINTS.md` §14; `01_SYSTEM_CORE.md` §2.2 step 3

**What the docs say:**
- "Font system is bitmap-only" (Pain Points §14)
- "Fonts loads `.font` bitmap files and renders glyphs as pixel blits" (Pain Points §14)
- "SysDisplay_InitFont() — Load bitmap font fallback" (01_SYSTEM_CORE §2.2 step 3)

**What the source actually does:**
- `Library.Fonts.ailang` (806 lines) is a **vector font engine** using the Face+Instance model.
- Font files are `.vif` (Vector Icon Format), not `.font`.
- The pipeline is: **VIF file → TVG_Parse (Bezier outlines) → TVG_Render (rasterize to pixel surface) → Surface_BlitAlpha (blit glyph to target)**.
- `SysDisplay_InitFont()` at line 460 prints `"[Font] vector init\n"` and returns — it's a stub; actual font loading happens later in `SysDisplay_Init` via `VFont_Init()`, `VFont_LoadVIF("fonts/DejaVuSans.vif")`, and `VFont_LoadFace("fonts/AlteixSans.vif")`.
- The user's description is accurate: **"TVG → VIF → flat packed bitmaps."** TVG rasterizes vector glyphs to cached bitmap surfaces at the requested point size. These cached bitmaps are then alpha-blitted to the target surface.

**Correction:** Replace "bitmap-only" with "vector-sourced, bitmap-cached." The system is vector-capable; the limitation is lack of hinting, subpixel AA, and TTF/OTF support — not the absence of vector data. The `.font` file extension is wrong; it's `.vif`.

**Files to update:** `07_PAIN_POINTS.md` §14, `01_SYSTEM_CORE.md` §2.2 step 3, `03_RENDER_PIPELINE.md` §6 (already partially correct).

---

### A.2 — DPI Scaling Description (Moderate)

**Where:** `00_MASTER_INDEX.md` (layer diagram), `06_DESKTOP_SHELL_CONTENT.md` §8, `01_SYSTEM_CORE.md` §2.5

**What the docs say:**
- "DPI-aware sizing system" (multiple locations)
- "Computes from screen height relative to 1080p reference"

**What the source actually does:**
- `UIScale_Init()` computes `scale_num/scale_den = screen_h / ref_h` where `ref_h` defaults to 1080 (from `ui.cfg` key `ref_height`).
- This is **resolution-based scaling**, not DPI-aware. It does not query EDID, DRM physical dimensions, or `/sys/class/drm/*/modes`.
- The scaling infrastructure (UIScale_Val, GCD-reduced fractions, configurable ref_h) is well-scaffolded for future true-DPI integration.

**Correction:** Replace "DPI-aware" with "resolution-aware" or "screen-height-relative scaling." Note that the scaffolding exists for true DPI integration (e.g., by replacing the `ref_h` derivation with `fb_height_mm / 25.4 * 96` if DRM physical dimensions are available).

**Files to update:** `00_MASTER_INDEX.md` design principle #6, `06_DESKTOP_SHELL_CONTENT.md` §8 title and body, `01_SYSTEM_CORE.md` layer diagram.

---

### A.3 — InputRouter Location and Status (Moderate)

**Where:** `00_MASTER_INDEX.md` file inventory table, `05_INPUT_SYSTEM.md` §6

**What the docs say:**
- InputRouter is at `Library.InputRouter.ailang` in `Librarys/Display/Input/`
- "InputRouter drains Ring1 and forwards events"

**What the source actually does:**
- `Library.InputRouter.ailang` lives at `Librarys/Display/IPC/Library.InputRouter.ailang`, not under `Input/`.
- **InputRouter is dead code** — no file imports it, no function calls `InputRouter_Init()` or `InputRouter_Drain()`. A grep of the entire codebase returns zero callers.
- InputRouter imports `LibraryImport.Focus` which resolves to deprecated `Librarys/deprecated/Library.Focus.ailang`.
- The actual event routing is done inline by `SysDisplay_DrainInput()` which reads Ring1 directly.

**Correction:** Flag InputRouter as **deprecated/vestigial**. Move it to `Librarys/deprecated/`. Remove it from the file inventory. Document that event routing is now done directly by `SysDisplay_DrainInput`.

**Files to update:** `00_MASTER_INDEX.md` file inventory, `05_INPUT_SYSTEM.md` §6 (rewrite or remove).

---

### A.4 — SysDisplay Init Sequence (Minor)

**Where:** `01_SYSTEM_CORE.md` §2.2

**What the docs say:** 15-step init sequence.

**What the source actually does (19+ steps):**
```
1.  SysDisplay_InitFB()
2.  Compose_Init(w, h)
3.  SysDisplay_InitFont()          ← stub, prints "vector init"
4.  SysDisplay_InitCursor()
5.  WinMgr_Init()
6.  SysDisplay_InitDB()
7.  SysDisplay_InitTTY()
8.  SysDisplay_InitInput()
9.  VIF_Init()
10. VFont_Init()
11. TextRegion_Init()
12. VFont_LoadVIF("fonts/DejaVuSans.vif")     ← missing from docs
13. WinMgr.tab_inst = VFont_UseSize(...)       ← missing from docs
14. VFont_LoadFace("fonts/AlteixSans.vif")     ← missing from docs
15. VIcon_Init()
16. VIcon_LoadVIF(IconTier.WIDGETS, "icons/silver_atoms.vif") ← missing from docs
17. DebugLog_Init()
18. Desktop surface creation
19. Desktop text via TextRegion
```

**Correction:** Add steps 12, 13, 14, 16 to the documented sequence. Note the dual-font loading (DejaVuSans as default body font, AlteixSans as optional title/display font).

**Files to update:** `01_SYSTEM_CORE.md` §2.2.

---

### A.5 — Theme Color Naming Convention (Minor)

**Where:** `02_WINDOW_MANAGEMENT.md` §7, `06_DESKTOP_SHELL_CONTENT.md` §6

**What the docs say:** Color constants like `HEADER_BG_ACTIVE`, `HEADER_BG_INACTIVE`, `HEADER_TEXT_ACTIVE`, `HEADER_TEXT_INACTIVE`, `BORDER_ACTIVE`, `BORDER_INACTIVE`, `TOOLBAR_BG`, `TOOLBAR_BTN_BG`.

**What the source actually does:**
- Colors are stored in `FixedPool.Theme` with flat names: `Theme.header_color`, `Theme.border`, `Theme.text_fg`, `Theme.toolbar_bg`, etc.
- There are NO active/inactive color pairs for headers, borders, or text. Single colors serve all states.
- The docs describe ~50+ colors with active/inactive variants. The code has ~47 flat colors.
- Config key names use the flat scheme: `header_color`, `desktop_bg`, `toolbar_bg`, etc.

**Correction:** Update the color table to match actual `Theme.*` field names. Either (a) document the current flat scheme accurately, or (b) add the active/inactive color pairs to the code and config. Option (a) is lower effort and reflects reality.

**Files to update:** `02_WINDOW_MANAGEMENT.md` §7, `06_DESKTOP_SHELL_CONTENT.md` §6.

---

### A.6 — "Overlapping Libraries" Section (Moderate)

**Where:** `00_MASTER_INDEX.md` "Overlapping Libraries"

**What the docs say:** The following libraries are "used by the Display system":
- `MessagePort`, `MessageQueue`, `MessageTranslate`, `MessageTypes`
- `ShmCanvas`, `ANSICanvas`, `TermFont`, `TUI`
- `DRenderTerm`, `ThreadTrampoline`, `CursorHVIF`

**What the source actually does:**
- **None** of these libraries are imported by `SysDisplay.ailang`, `Main.ailang`, or any Display subsystem file.
- `CursorHVIF` is never imported by any `.ailang` file in the project.
- These are either (a) aspirational/future, (b) used by non-Display parts of the project, or (c) dead code.

**Correction:** Remove these from the Display system documentation or move them to a "Related / External" section with a note that they are not imported by the display server.

**Files to update:** `00_MASTER_INDEX.md` "Overlapping Libraries" section.

---

## Section B: Line Count Discrepancies

| File | Doc Claims | Actual Lines | Delta |
|------|-----------|-------------|-------|
| `Library.VIF.ailang` | ~1500 | 1793 | +293 |
| `Library.Framebuffer.ailang` | ~1200 | 1512 | +312 |
| `Library.UITheme.ailang` | ~300 | 155 | -145 |
| `Library.UIScale.ailang` | ~300 | 240 | -60 |
| `Library.Fonts.ailang` | ~700 | 806 | +106 |
| `Library.SysDisplay.ailang` | ~1500 | 1481 | -19 |
| `Library.EventRouter.ailang` | ~500 | 577 | +77 |
| `Library.WinManager.ailang` | ~1100 | 1132 | +32 |

Most counts are within acceptable range. The significant misses are VIF (+293), Framebuffer (+312), and UITheme (-145). Update these.

---

## Section C: Stale / Dead / Unused Code

### C.1 — Deprecated Directory (`Librarys/deprecated/`)

These files exist but are **never imported** by any active `.ailang` source file:

| File | Lines | Status |
|------|-------|--------|
| `Library.FontTTF.ailang` | 502 | Dead — abandoned TTF/OTF attempt. Superseded by VIF/TVG path. |
| `Library.Focus.ailang` | 298 | Dead — old focus management. Imported ONLY by the dead `InputRouter.ailang`. |
| `Library.PaneManager.ailang` | ~300 | Dead — old pane/window management. Superseded by WinManager. |
| `Library.WinManagerBU.ailang` | ~1800 | Backup — stale copy of WinManager (73k bytes). |
| `Library.WinManagerbu.ailangbu` | ~1100 | Backup — another stale copy (42k bytes). |

### C.2 — Active but Unreferenced Files

| File | Lines | Status |
|------|-------|--------|
| `Library.InputRouter.ailang` | 108 | **Dead** — not imported by any file. Depends on deprecated `Focus.ailang`. Should move to deprecated. |
| `Library.CursorHVIF.ailang` | unknown | **Dead** — Haiku Vector Icon Format cursor. Never imported by any file. |

### C.3 — Missing Files Referenced by Docs

| Doc Reference | Reality |
|---------------|---------|
| `Library.InputRouter.ailang` in `Input/` | Exists in `IPC/`, but is dead code anyway |
| `silver_atoms.vif` as "widget pack" | Exists at `icons/silver_atoms.vif` (18,816 bytes) — location correct, file present |

---

## Section D: Architecture Diagram Corrections

### D.1 — 10-Phase Main Loop

The documented 10-phase loop in `00_MASTER_INDEX.md` and `01_SYSTEM_CORE.md` is largely accurate but the actual loop in `SysDisplay_Run()` at line 1203 matches:

```
while running:
    clock_gettime → delta_ms, FPS accumulation
    Evdev_Poll()
    SysDisplay_DrainInput()       ← handles all overlays, drag/resize, hotkeys
    Win_RenderDirty()
    EventRouter_Drain()           ← action dispatch
    IPCBroker_Poll()
    Deskbar_Refresh()
    DebugLog_Render()
    Win_BlitAll()                 ← composition + cursor + flip
    nanosleep(16.67ms)
```

No correction needed — the docs match the code here.

### D.2 — Ring Buffer Architecture

The 4-ring description in `00_MASTER_INDEX.md` accurately matches the source in `Library.DRing0-3.ailang`. No correction needed.

---

## Section E: Summary of Required Doc Changes

| Priority | Doc | Section | Issue |
|----------|-----|---------|-------|
| **P0** | 07_PAIN_POINTS | §14 | "Bitmap-only fonts" → "Vector with cached bitmaps" |
| **P0** | 01_SYSTEM_CORE | §2.2 step 3 | InitFont stub, not bitmap fallback |
| **P0** | 05_INPUT_SYSTEM | §6 | InputRouter path wrong + dead code |
| **P1** | 00_MASTER_INDEX | Overlapping Libs | Remove 10+ unimported libraries |
| **P1** | 06_DESKTOP_SHELL | §8 | "DPI-aware" → "Resolution-aware" |
| **P1** | 02_WINDOW_MANAGEMENT | §7 | Color names don't match Theme fields |
| **P2** | 01_SYSTEM_CORE | §2.2 | Add missing init steps 12-14, 16 |
| **P2** | 00_MASTER_INDEX | File inventory | Update line counts for VIF, FB, UITheme, UIScale |
| **P2** | 03_RENDER_PIPELINE | §6 | Font pipeline is accurate, keep |
| **P3** | 00_MASTER_INDEX | Design principles | Update "DPI-Aware" wording |

---

## Section F: What the Docs Got Right

The following sections are accurate and need no changes:

- Ring buffer architecture (4 rings, direction, purpose)
- Action routing system (prefix table, dispatch priority)
- WinManager CRUD, z-order, focus model
- Evdev device discovery (by-id + /proc fallback)
- Software cursor save/restore mechanism
- Auckland retained-mode layout engine description
- Deskbar hotzone reveal behavior
- Start Menu / Menu / CascadeMenu overlay model
- Compositor float-based architecture
- Pain Points §1-13, 15-18 (all accurate)
- Build & Run instructions
- Design Principles #1-5, 7-10
