# 07b — Pain Points Supplement (Source Audit Findings)

> **Added:** 2026-05-16 — Findings from source code audit against documentation.
> These supplement `07_PAIN_POINTS.md` with newly discovered issues.

---

## New Finding A: Dead Code in Active Directory

### A.1 — InputRouter is unreferenced

**What:** `Librarys/Display/IPC/Library.InputRouter.ailang` (108 lines) exists but is **never imported** by any file in the project. Zero callers of `InputRouter_Init()` or `InputRouter_Drain()`.

**Why it matters for onboarding:** A new engineer reading the docs will think InputRouter is a core component of the input pipeline. It's not — it's vestigial. The actual event routing is done inline by `SysDisplay_DrainInput()`.

**Mitigation:**
```
- Move InputRouter.ailang to Librarys/deprecated/
- Remove §6 of 05_INPUT_SYSTEM.md or rewrite to describe 
  the actual inline drain in SysDisplay_DrainInput
- Remove InputRouter from 00_MASTER_INDEX.md file inventory
```

### A.2 — CursorHVIF is dead code

**What:** `Librarys/Library.CursorHVIF.ailang` (Haiku Vector Icon Format cursor) is never imported by any `.ailang` file.

**Mitigation:** Move to deprecated or delete.

---

## New Finding B: Deprecated Directory Not Documented

### B.1 — Five stale files in `Librarys/deprecated/`

| File | Lines | What it was |
|------|-------|-------------|
| `Library.FontTTF.ailang` | 502 | Abandoned TTF/OTF font path |
| `Library.Focus.ailang` | 298 | Old focus system (only imported by dead InputRouter) |
| `Library.PaneManager.ailang` | ~300 | Old pane/window management |
| `Library.WinManagerBU.ailang` | ~1800 | Stale WinManager backup (~73k) |
| `Library.WinManagerbu.ailangbu` | ~1100 | Another stale backup (~42k) |

**Why it matters for onboarding:** A new engineer might find `FontTTF.ailang` and assume TTF support exists or was nearly complete. It wasn't — the VIF/TVG path superseded it. The backups suggest a significant WinManager rewrite occurred; understanding that history helps avoid repeating mistakes.

**Mitigation:**
```
- Add a README.md to Librarys/deprecated/ explaining what each file was
  and why it was superseded
- Or delete the .ailangbu files (they appear to be editor backup artifacts)
- Document the WinManager rewrite motivation in 02_WINDOW_MANAGEMENT.md
```

---

## New Finding C: Font System Documentation Contradiction

### C.1 — Docs disagree on whether fonts are bitmap or vector

**In `07_PAIN_POINTS.md` §14:** "Font system is bitmap-only. Fonts loads `.font` bitmap files."

**In `03_RENDER_PIPELINE.md` §6:** "Vector font engine. VIF file → TVG_Parse → glyph outlines (Bezier curves)."

**The truth:** `03_RENDER_PIPELINE.md` is correct. The current Fonts.ailang (v2, 806 lines) is a Face+Instance vector font engine backed by TVG rasterization. The pipeline is:

```
VIF font file (Bezier glyph outlines + styles)
    ↓
TVG_Parse → per-glyph TVG bytecode (zero-copy from file buffer)
    ↓
TVG_Render → rasterize at requested pixel size to BGRA surface
    ↓
Cache in Instance glyph surface table (512 slots)
    ↓
Surface_BlitAlpha → blit to target surface on draw
```

There are **no `.font` files** in the project. Font files are `.vif`: `fonts/DejaVuSans.vif`, `fonts/AlteixSans.vif`.

**Why §14 of the pain points is wrong:** It was likely written before the v2 Fonts rewrite (which introduced the Face+Instance model and TVG rasterization). The v1 may have been bitmap-only; v2 is not.

**Mitigation:** Rewrite pain point §14. The real font limitations are:
- No TTF/OTF support (abandoned `FontTTF.ailang` attempt)
- No hinting at small sizes
- No subpixel anti-aliasing (only supersampling AA)
- No font fallback chains
- No kerning pair support (kern pair entry type is defined in VIF but not used)

---

## New Finding D: Init Sequence Gaps

### D.1 — SysDisplay_InitFont is a stub

**What:** `01_SYSTEM_CORE.md` §2.2 step 3 describes `SysDisplay_InitFont()` as "Load bitmap font fallback." The actual function body:

```c
Function.SysDisplay_InitFont {
    Body: {
        DebugLog_Push("sd.iFnt", 7)
        PrintMessage("[Font] vector init\n")
        ReturnValue(1)
    }
}
```

It's a stub. The real font initialization happens at steps 10-14 of `SysDisplay_Init` (VFont_Init, VFont_LoadVIF, VFont_LoadFace).

**Why it matters:** If someone tries to add font initialization logic to this function, it runs too early — before VIF_Init, VFont_Init, and TextRegion_Init.

**Mitigation:** Either remove `SysDisplay_InitFont` and fold it into the main init, or use it to call `VFont_Init` + `VFont_LoadVIF` and move those calls earlier.

---

## New Finding E: Resolution vs DPI

### E.1 — "DPI-aware" is misleading

**What:** Multiple docs describe `UIScale` as "DPI-aware." It's not. `UIScale_Init()` computes `screen_height / 1080` as a scale ratio. This is **resolution-aware**, not DPI-aware. True DPI requires querying physical display dimensions from EDID or DRM, which the code does not do.

**The scaffolding is good:** `UIScale_Val()`, GCD-reduced fraction, configurable `ref_height` key, and per-category init sub-functions all make it easy to swap in true DPI later. But calling it "DPI-aware" sets wrong expectations.

**Mitigation:** Rename to "resolution-aware scaling" in docs. Add a footnote that true DPI can be integrated by replacing the `ref_height` derivation with `fb_height_mm / 25.4 * 96`.

---

## New Finding F: Color Theme Documentation Mismatch

### F.1 — Docs describe active/inactive color pairs that don't exist

The docs (02_WINDOW_MANAGEMENT §7) describe:
- `HEADER_BG_ACTIVE` / `HEADER_BG_INACTIVE`
- `HEADER_TEXT_ACTIVE` / `HEADER_TEXT_INACTIVE`
- `BORDER_ACTIVE` / `BORDER_INACTIVE`
- etc.

The actual `Theme.*` fields are flat: `header_color`, `border`, `text_fg`, `text_secondary`. There are no active/inactive variants. Window active state does not change header or border color — only the focused window's z-order changes.

**Mitigation:** Either add active/inactive color pairs to UITheme (and use them in WinRender), or update docs to match the current flat scheme. Given the XP/7-inspired design, active/inactive distinction would improve UX.

---

## New Finding G: Main.ailang Import List vs Docs

### G.1 — Docs list imports that Main.ailang doesn't use

The `00_MASTER_INDEX.md` "SysDisplay imports 40+ libraries" list and `01_SYSTEM_CORE.md` §7 both include `PostgreSQL_Complete`, `HTMLParse`, `AucklandBind`, `JSON`, and `VIcon` as SysDisplay imports. These are correct for SysDisplay but the "Overlapping Libraries" section then lists 10+ additional libraries (MessagePort, ShmCanvas, etc.) that are **not imported by any Display component**.

**Mitigation:** See DOC_CORRECTIONS.md §A.6.

---

## Summary — New Pain Points

| # | Pain Point | Impact | Effort | When |
|---|-----------|--------|--------|------|
| 19 | InputRouter is dead code in active path | Low | Low | Anytime (move to deprecated) |
| 20 | CursorHVIF never imported | Low | Low | Anytime |
| 21 | 5 stale files in deprecated/ undocumented | Low | Low | Before onboarding new engineers |
| 22 | SysDisplay_InitFont is a misleading stub | Low | Low | During font system cleanup |
| 23 | Pain points §14 contradicts render pipeline doc | Medium | Low | Immediately |
| 24 | "DPI-aware" naming is misleading | Low | Low | Anytime |
| 25 | Color theme docs describe nonexistent pairs | Medium | Low | Before theme customization docs are written |
