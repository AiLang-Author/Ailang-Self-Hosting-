# Document phase: page tables (and the pieces under them)

**Author:** Sean Collins / 2 Paws Machine and Engineering  
**Date:** 2026-08-25  
**Status:** Plan (not building the whole product in one cut)  
**Parent:** `DOCUMENT_FACILITY.md`, `DOC_PHASE_FONTS_TOOLBAR.md`  
**Depends on:** paper IR, DocView camera, font catalog, lists (done)

---

## What you described

Not an in-flow Word “Insert 3×4 at caret.” A **page table**:

1. Draw a rectangle on the sheet (inside the margins).
2. Pick a font face/size for that table.
3. Name the columns (header row).
4. Number the rows (gutter, not data).
5. Size follows content (rows grow as you type).
6. Look is themeable (grid, header, numbers).

That is closer to a **framed object on paper** than to typewriter wrap. Text boxes will use the same frame + rubber-band path later. So the expensive part is **infrastructure**, not the table grid itself.

It gets complicated in a hurry if we pretend those are one PR.

---

## Two different “columns”

| | Page columns | Page table |
|---|---|---|
| Shape | Split the content box; text flows down col 1 then col 2 | Rectangle on the page; grid of cells |
| Rows | No | Yes (header + numbered data rows) |
| Lives in | Section / HEAD | Frame list on the document |
| Create | Setup spinner 1–4 | Rubber-band (or insert-at-caret fallback) |

Page-flow columns stay a later, smaller wrap change. This phase is **tables as page objects**.

**Caps (Letter, 1" margins, 12pt):**  **8 columns**, **32 rows** v1. Four page-flow columns remain the newsletter max when we get there.

---

## What we do not have today

| Piece | Today | Need |
|---|---|---|
| Rubber-band | Missing. Mouse: click caret on DocView; drag exists for TEXTFIELD select and scrollbar thumbs only. No press-move-release rect. Crosshair cursor already exists. | `DocBand` tool: down stores paper pt, move paints a rect, up commits |
| XOR / overlay stroke | DocView paints into the window canvas. No live overlay layer. | Draw the band in DocView paint from session scratch (xor or invert later; **v1 = fill a 1px Theme rect each frame**) |
| Frame list | `DocKind.TABLE` reserved. Live editor is one UTF-8 run. `FRAM` on disk reserved, not wired. | Per-doc object table: kind, box in **points**, z, face, size_pt |
| Cell model | None | Header names + row-major cell runs (or one run with cell breaks). Row-number gutter is **not** a cell |
| DocView drag | `DocView_Click` on down only. Auckland move does not call DocView. | `DocView_Drag` / `DocView_Up` from `AK_EventMouseMove` / `Up` when tool ≠ caret |
| Table theme | `Theme.page_bg`, `border`, `text_fg`, `ak_selection_bg` | New keys (below). Paint reads Theme, never hex |
| Dynamic size | Paper size is fixed; typewriter paginates | Table **box height** grows with row count × row_h; width stays the rubber-band (or Setup). Clip/scroll inside the box v2 |

---

## Recommended shape

```
Document
  TEXT run          — typewriter (already)
  Frame table       — 0..N page objects
    Frame: kind=TABLE, x_pt, y_pt, w_pt, h_pt, z, face, size_pt
    Table: ncol, nrow, col_w[], row_h[], header[ncol] names
           cells[nrow][ncol] runs (plain UTF-8, HEAD-level face/size of the table)
           flags: row_numbers=1, header=1
```

Coordinates stay **points**. Camera maps with `LAYOUT_DPI=96` like everything else. Frames sit **in the content box** (clamped to margins on commit). They do **not** reflow the typewriter around them in v1 (text draws through; z later). Overlap is allowed; hit-test topmost.

**Skin:** the table is a painted widget. Colors come from Theme. Changing dark/light restyles every table. No per-table palette v1.

Theme keys to add (defaults from current chrome, override in `ui.cfg`):

| Key | Role |
|---|---|
| `table_grid` | Cell stroke |
| `table_header_bg` | Header fill |
| `table_header_fg` | Header ink |
| `table_cell_bg` | Body fill (usually page_bg) |
| `table_cell_fg` | Body ink |
| `table_rownum_bg` | Number gutter |
| `table_rownum_fg` | Number ink |
| `table_sel_bg` | Active cell |
| `table_band` | Rubber-band while dragging |

That **is** “skinnable infrastructure.” Full theme editor / per-table skins wait.

**Dynamic size:**  
- Column count fixed at create (2–8). Equal widths in the rect.  
- Header row always present; click and type names.  
- Data rows start at 1; **Enter in the last row appends a row** (cap 32).  
- Box `h_pt` = (1 header + nrow) × row_h + grid. Rubber-band sets **width** (and min height); height grows down, still inside bottom margin if it fits, else clip.  
- Row numbers = 1…nrow in the gutter; not editable, not in the cell model.

**Font:** table-level face + size_pt from the current document font/size at create. Change later via the existing Fonts/size controls while a cell is focused.

---

## Create UX (v1)

1. Format bar: **Table** tool (toggle). Cursor → crosshair over the sheet.
2. Press-drag inside the content box. Live rectangle (Theme.table_band).
3. Release: clamp to margins; reject if smaller than 2 col × (header+1 row).  
   Default **3 columns**, 1 data row, header blanks (“Col A” …).
4. Focus header cell 0. Type names. Tab next header. Enter → first data cell.
5. Click Table tool again (or Esc) → back to typewriter caret.

No column-name dialog. The header **is** the name UI.

Fallback if rubber-band is not ready: Insert Table drops a default rect at caret y, full content width, 3 cols — same model, worse UX. Prefer not to ship the fallback if rubber-band is the first cut.

---

## Build order (do not skip)

### P0 — Rubber-band (shared)

**Do not invent a table-only drag.** Use **PlaceHUD** (`docs/display/PLACE_HUD.md`): origin on down, live corner on move, W/H HUD, inches (mm later). Same engine for tables, text boxes, CAD place, and **text select/copy**.

DocView tools: `CARET | PLACE | SELECT`.  
Place: down stores paper pt, drag paints `Theme.place_band`, HUD W/H, up → `PlaceHud_Commit` → empty table frame.  
Select: same down/move; commit is `SEL_A`/`SEL_B` (Copy already works once the range is set).

Auckland must route DOCVIEW **move and up**, not only click.

### P1 — Frame table (empty grid)

Frame records on the document. Hit-test: point in box → cell. Paint grid from Theme. No typing yet. Prove rubber-band creates a themed empty table.

### P2 — Cells + header + row numbers

Caret in a cell. Type into that cell’s run. Tab/Shift+Tab. Enter next row / append. Header row + number gutter. Table font = document face/size at create.

### P3 — Grow + clamp

Append rows, recompute `h_pt`, clamp to page bottom. Col widths stay equal in `w_pt`.

**Not in this phase:** nested tables, merge, formulas, text wrap around frames, page-flow columns, per-cell fonts, dragging to resize cols (need rubber-band *on handles* — after P0 is proven).

---

## Why theme now

Hardcoding `0xFF2A4068` on grid lines means every table is a special case when the desktop theme changes. Five Theme keys is cheaper than a “skin engine.” Tables **look** skinned because they read the same Theme the rest of the shell uses.

---

## Risks

- Rubber-band without XOR will flicker; accept full DocView repaint while dragging (already dirty-on-move for caret).
- Frames vs typewriter z: v1 paint frames **after** body ink so they sit on top. Text underneath is covered, not wrapped.
- Call-clobber: band corners, cell indices, frame ids live in FixedPools (`DocBand`, `DocFrame`).
- Two `display.x` processes still kill windows; one compositor on hot-swap.
- 8×32 cells × small runs is fine; do not one-run-the-whole-table (insert in cell 0 would shift every cell).

---

## Decision

Page tables are **framed, themed grids**, created by **rubber-band**, not typewriter columns.  

**First code cut is P0 rubber-band + Theme keys + empty frame on commit** — not the full spreadsheet. P1–P3 stack on that. Text boxes later reuse P0/P1.

---

## Files (when we cut P0)

| File | Role |
|---|---|
| `docs/display/DOC_PHASE_TABLES.md` | This plan |
| `Librarys/Display/Theme/Library.UITheme.ailang` | `table_*` keys |
| `config/ui.cfg` | Defaults |
| `Librarys/Display/Content/Library.DocView.ailang` | Tool, drag, band paint |
| `Librarys/Display/UI/Library.AucklandEvent.ailang` | DOCVIEW move/up |
| `Librarys/Display/Content/Library.AilangDoc.ailang` | Frame table (P1) |
| `config/document.html` | Table tool button |
