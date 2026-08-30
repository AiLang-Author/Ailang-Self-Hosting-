# PlaceHUD — themed rubber-band + numeric HUD

**Author:** Sean Collins / 2 Paws Machine and Engineering  
**Date:** 2026-08-25  
**Status:** Plan (infrastructure, not a table)  
**Used by:** page tables, text boxes, images, CAD rect/sketch place, **text select/copy**  
**Parent:** `DOC_PHASE_TABLES.md`, CAD ToolsHud (W/H commit is the same *idea*, different host)

---

## Why this exists

Rubber-band is not a table feature. It is “press on a point, remember it, size a box.” The box is then **either** a new object **or** a selection. CAD already does origin + HUD W/H for rectangles. Document tables want the same gesture on paper. Select-to-copy wants the same press–drag, then a range instead of a frame.

Build **one** themed HUD + band engine in display. Hosts plug in coordinates and a commit callback. Do not copy CAD’s `hud_kind` into DocView.

---

## Gesture (all hosts)

1. Tool on (Table, Text box, CAD Rect, or implicit **select** in caret mode).
2. Mouse **down**: store origin `(x0, y0)` in the host’s space. Crosshair if placing; I-beam if selecting.
3. Mouse **move** (button held): store corner `(x1, y1)`. Draw the band every frame. HUD W/H follow the mouse.
4. **Type** in the HUD: W and H (inches v1). Band resizes from the origin. Tab cycles fields. Enter commits. Esc cancels.
5. Mouse **up**:
   - **Place tools:** commit the rect (clamped). Host creates table/frame/sketch rect.
   - **Select:** commit is the range under the rect (or the drag line for text). Copy is Ctrl+C / Edit menu, not mouse-up.
6. Units are a display enum later (`INCH` now, `MM` / `PT` later). Internal store is always **points** for documents, host units for CAD.

Origin stays put. Only the opposite corner moves. That is CAD-sketcher rubber-band, not “center-out.”

---

## Consumers

| Consumer | Origin | Band means | Commit |
|---|---|---|---|
| Page table | Paper pt, inside margins | Outer box of the grid | Frame + empty table |
| Text box | Paper pt | Frame | `FRAM` TEXT |
| Image | Paper pt | Frame | `FRAM` IMAGE |
| CAD rect | Sketch UV / plane | Rectangle | Existing `CA_RectCommitHud` |
| **Text select / copy** | Caret hit at down | Live selection highlight (band optional) | `SEL_A`/`SEL_B`; clipboard on Copy |

Select is the one we already almost have in TEXTFIELD (`AK_TextfieldDrag`). DocView has click-caret only — no drag. Routing DOCVIEW through PlaceHUD **select** mode is how copy-by-drag lands without a second mouse stack.

---

## What we add (the “few feature additions”)

| Piece | Today | Add |
|---|---|---|
| Press–move–release on DocView | Down → `DocView_Click` only. Move ignores DOCVIEW. | `DocView_Drag` / `DocView_Up`. Auckland move/up if `pressed` is DOCVIEW |
| Band state | None | FixedPool `PlaceHud`: tool, origin, corner, live, unit, field (W/H), host id |
| Live paint | Full DocView blit | 1px `Theme.place_band` rect in camera space (full repaint while dragging is OK) |
| Numeric HUD | CAD-only, not themed with document chrome | Small overlay: `X Y` read-only, `W H` editable, unit label. Theme = format bar (`toolbar_*` / new `hud_*`) |
| Parse | `DocFmt_ParseInch` exists | Reuse; later `PlaceHud_Parse` honors `PlaceHud.unit` |
| Cursor | Crosshair exists | Place tool → CROSSHAIR; select stays I-beam |
| Clamp | None | Host callback `clamp(x0,y0,x1,y1)` — document clamps to content box |
| Commit / cancel | None | Host `commit` / `cancel`. Esc and tool-off cancel |

CAD can keep its own HUD *content* (fillet R, extrude H) but should **share** band geometry + chrome + unit field when placing a rect. Do not rewrite ToolsHud in v1; document is the first client, CAD adopts the band when it is boring.

---

## HUD chrome (themed, reusable)

Looks like the document **Setup** drop / CAD dim HUD: dark panel, steel buttons, inch values.

```
┌ Origin 1.00in, 2.00in ┐  W [ 3.50 ]  H [ 2.00 ]  in   [OK]
```

- Position: follow the band (near the moving corner) **or** dock under the format bar. Dock is easier (no extra overlay compositor). Follow-the-band is nicer; v1 dock is fine.
- Same Auckland `visible` drop pattern as Fonts/Setup **or** paint into DocView. Docked HTML group `id="place_hud"` avoids a third compositor. CAD has no document.html — so the HUD must also be **paintable without HTML** (DrawString + buttons as hit rects in the host canvas).

**Decision:** implement PlaceHUD as **code-drawn chrome** (Theme + hit rects), not HTML. Then CAD and Document both call `PlaceHud_Draw(canvas, …)` and `PlaceHud_Hit(mx,my)`. HTML drops stay for Fonts/Setup.

Theme keys:

| Key | Use |
|---|---|
| `place_band` | Rubber-band stroke |
| `hud_bg` | Panel fill |
| `hud_fg` | Labels / values |
| `hud_input_bg` | W/H wells |
| `hud_accent` | Active field |

Defaults copy `toolbar_*` / `ak_input_*` so it matches the shell without a new palette.

---

## Select / copy (same engine, different commit)

- Caret tool + drag on empty paper = **select mode** (no Table tool).
- Down: `SEL_A = hit(x0,y0)`.
- Move: `SEL_B = hit(x1,y1)`; paint selection behind glyphs (already `Theme.ak_selection_bg`). Optional faint `place_band` around the glyph box — not required v1.
- Up: leave the selection. Ctrl+C / Edit Copy already exist once `SEL_A ≠ SEL_B`.
- Does **not** open the W/H HUD. Numeric HUD is for **place** tools only.

That is “rubber-band might require a few feature additions”: DocView drag + selection paint we already designed in DOCUMENT_FACILITY (Shift+arrow exists; **mouse-drag select does not**).

---

## Units

Internal: **points** on paper (72 pt = 1 in). CAD keeps its own numeric type.

Display: `PlaceHud.unit = INCH` v1. HUD shows two decimals (`3.50`). Parse with the existing inch parser. `MM` is a format flag later, not a second solver.

---

## Build order

| Cut | What | Unlocks |
|---|---|---|
| **H0** | Pool + DocView down/move/up + band paint + Esc | Visible rubber-band on the Letter sheet |
| **H1** | Code-drawn HUD W/H, live sync mouse ↔ fields, Enter/Tab | Numeric place; CAD-like |
| **H2** | Select-drag on DocView (SEL_A/B) + existing Copy | Copy-by-mouse |
| **H3** | Theme keys; clamp-to-margins | Tables P0 commit empty frame into the band |

Tables P1–P3 stay on top of H3. Text boxes reuse H3.

---

## Non-goals (this infra)

- Metric UI (flag only).
- Center-out band, rotation, 3-point rect.
- XOR overlay (full DocView dirty while dragging).
- Replacing CAD fillet/extrude HUDs in the same PR.
- Column-resize handles (second band, later).

---

## Files (when we cut H0)

| File | Role |
|---|---|
| `docs/display/PLACE_HUD.md` | This plan |
| `Librarys/Display/Content/Library.PlaceHud.ailang` | Pool, parse, draw, hit |
| `Librarys/Display/Content/Library.DocView.ailang` | Tool, drag, band, select |
| `Librarys/Display/UI/Library.AucklandEvent.ailang` | DOCVIEW move/up |
| `Librarys/Display/Theme/Library.UITheme.ailang` | `place_band`, `hud_*` |
| `Librarys/Display/Input/Library.Cursor.ailang` | CROSSHAIR while placing |
