# Document phase: format toolbar + font catalog

**Author:** Sean Collins / 2 Paws Machine and Engineering  
**Date:** 2026-08-25  
**Status:** Active (this phase)  
**Parent:** `DOCUMENT_FACILITY.md` (paper IR, DocView camera, HEAD attrs)  
**Audience:** Display / Auckland / document stack

---

## Why this phase

The Document app is a real typewriter on paper: Letter/Legal/A4, margins, guides, Times-class metrics, Tab stops, space from the face’s own U+0020. The in-app format strip is **not** window chrome. It grew into two packed rows (font, size, Tab, B/I/U, align, then L/T/R/B). That is not space-efficient and it does not scale to a font list.

This phase does two things together, because adding fonts on the current strip would make it worse:

1. **Reorganize the format bar** into one hot-button row plus **dropdown panels** (Word-2000-style context drops, not display chrome).
2. **Font catalog + picker** so the document face is chosen from system VIFs, not hardcoded Times.

Lists, columns, and text boxes are **the next phase after this**. They are listed at the end so the sequence stays explicit.

---

## Goals

- One compact **hot row** always visible: family trigger, size, B/I/U, alignment.
- **Fonts** dropdown: pick a loaded-or-loadable family. Sets `ADocField.FACE`, rebinds layout. Space and Tab already follow that face.
- **Setup** dropdown (margins / page setup): L/T/R/B and Tab spacing. Same `fmt.ml.*` / `fmt.mt.*` / `fmt.tab.*` actions as today.
- Dropdowns are **in-window Auckland groups** (`AKF.VISIBLE` toggle). Not a second compositor overlay, not Deskbar/CascadeMenu.
- System font files stay **VIF in `/system/fonts`**. Catalog is a roster (name, path, face handle), not a new file format.
- Raise Face/Instance caps so a picker can exist without blowing the 8-face table.

## Non-goals (this phase)

- Lists / bullets, newspaper columns, text boxes / FRAM.
- Per-run character style (bold on three letters). HEAD-level B/I/U/size/face only.
- User-installed fonts via FileTree (catalog will accept a path later; no install UI now).
- ODF/DOCX, stylesheets, font preview glyphs in the menu.
- New Auckland `DROPDOWN` tag. Visible groups are enough.
- Scanning the directory at runtime (`readdir`). Register known VIFs at boot; add more as files land.

---

## Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dropdown mechanism | Hidden `group` siblings under the format vbox; `visible="0"` until the trigger is clicked. Second click or the other trigger closes. | Solver already skips `AKF.VISIBLE==0`. No overlay stacking, no new tag. Paper camera grows/shrinks with the bar. |
| Hot vs drop | **Hot:** size −/+, B, I, U, align L/C/R/J. **Fonts drop:** family list. **Setup drop:** L/T/R/B + Tab. | User: common format stays one click; margins and fonts are setup, not every keystroke. |
| Format “tab” | The format strip *is* the format tab. No third drop for B/I/U. | Those stay hot buttons. |
| Font storage | Keep `/system/fonts/*.vif` + `pack_font_vif.py`. FileTree/UUIDStore remains the generic blob store. **New:** `FontCat` roster in display. | Do not invent a second font file format. Picker talks to the roster; layout still uses `VInst_*`. |
| Load policy | Boot: UI Alteix + default doc Times (+ DejaVu if present). Others **load on first pick**. | `FaceConst.MAX` was 8. Plex weights must not all rasterize at boot. |
| Document binding | `ADocField.FACE` (already on the record). Picker writes the face index and `DocLayout_Bind`. | Space/Tab metrics already read the bound instance. |
| Actions | `fmt.drop.font`, `fmt.drop.setup`, `fmt.font.N`. Existing `fmt.sz.*`, `fmt.m*.*`, `fmt.tab.*`, `fmt.align.*`, `fmt.bold` stay. | Still display-owned (`fmt.` prefix). IPCBroker must not relay them to `document.x`. |
| Caps | `FaceConst.MAX` 8→32, `InstConst.MAX` 16→32. | One instance per face+size. 12 pt Times is shared. |

---

## UI layout (`config/document.html`)

```
┌─ format vbox (min-h 32, not locked to 70) ─────────────────────────┐
│ [Fonts] Times  − 12 +   B I U   │  L C R J  │  [Setup]            │  ← hot row
├─ drop_font (visible 0|1) ─────────────────────────────────────────┤
│  Times │ Alteix Sans │ DejaVu Sans │ IBM Plex …                   │
├─ drop_setup (visible 0|1) ────────────────────────────────────────┤
│  L − 1.00 +   T − 1.00 +   R − 1.00 +   B − 1.00 +   Tab − 4 +   │
└───────────────────────────────────────────────────────────────────┘
┌─ <docview> camera ─────────────────────────────────────────────────┐
```

- Format chrome is **in the app HTML**, not `WinToolbar`.
- Only one drop open at a time.
- Ids: `font`, `sz`, `ml`, `mt`, `mr`, `mb`, `tab`, `drop_font`, `drop_setup`.

---

## Font catalog

Roster entry (32 bytes):

| Field | Meaning |
|-------|---------|
| NAME | Display string (data-segment literal) |
| PATH | `/system/fonts/….vif` |
| FACE | Face table index, or −1 until first pick |

Boot registration (order = `fmt.font.N` index):

| N | Name | Path | Face at boot |
|---|------|------|----------------|
| 0 | Times | `TimesRoman.vif` | default `doc_face` |
| 1 | Alteix Sans | `AlteixSans.vif` | UI face (already loaded) |
| 2 | DejaVu Sans | `DejaVuSans.vif` | loaded if present |
| 3 | IBM Plex Sans | `IBMPlexSans-Regular.vif` | on demand |
| 4 | IBM Plex Medium | `IBMPlexSans-Medium.vif` | on demand |
| 5 | IBM Plex Bold | `IBMPlexSans-Bold.vif` | on demand |

`FontCat_EnsureFace(i)`: if FACE ≥ 0 return it; else `VFont_LoadFace(PATH)` and store. Then `ADoc_Set(FACE)`, `DocLayout_Bind`, update the `font` label.

Space and Tab: unchanged formula — U+0020 of **that** face; tab cell = 3×space or `n`/`0` if wider.

---

## Implementation sequence

1. Planning doc (this file).
2. `visible` attribute in AucklandBind; Face/Instance caps.
3. `FontCat_*` in the font engine; register at SysDisplay init.
4. `document.html` one hot row + two drops; hide drops by default.
5. `DocFmt_Apply`: drop toggles, `fmt.font.N`.
6. Hot-swap **one** `display.x` (do not start a second compositor) + copy HTML to `/system/config/document.html`.

## Later phases (not this PR)

| Next | What | Why after fonts |
|------|------|-----------------|
| Lists / bullets | Paragraph marker + hanging indent | Needs a paragraph layer on the run; still typewriter |
| Columns | 1–3 columns in the content box | Wrap/tab become per-column |
| Text boxes | `FRAM` on paper, own run, hit-test | First objects-on-paper; do not redo lists inside every frame afterward |

---

## Files

| File | Change |
|------|--------|
| `docs/display/DOC_PHASE_FONTS_TOOLBAR.md` | This plan |
| `docs/display/00_MASTER_INDEX.md` | Link |
| `config/document.html` | Hot row + drops |
| `Librarys/Display/UI/Library.AucklandBind.ailang` | `visible` attr |
| `Librarys/Display/Render/Library.Fonts.ailang` | Caps + FontCat |
| `Librarys/Display/System/Library.SysDisplay.ailang` | Register catalog |
| `Librarys/Display/Content/Library.DocView.ailang` | Drop + font actions |
| Guest `/system/config/document.html` | Deploy with display |

## Risks

- Two `display.x` processes paint the same framebuffer (window “starts then dies”). Kill extras; leave svc_daemon’s child, or start **one**.
- Invisible groups with leftover `height=` may still reserve space — rely on `VISIBLE` skip, not height 0 alone.
- `fmt.font.N` must stay on the display side of ActionRelay (same as other `fmt.*`).
- IBM Plex VIFs missing on a given image: EnsureFace fails, keep current face, no crash.
