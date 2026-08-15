# AILang CAD — how to use the UI

Press **F1** any time to open this page. Esc closes it.

The Gtk window is chrome. Geometry, tools, and the numbers in the yellow
edit card come from the CAD app. Type into the card; the app does the rest.

---

## Sketch tools

Pick a tool on the **Sketch** tab (or right-click the viewport for the pie).

| Tool | What you do |
|------|-------------|
| **Line** | Click start, click end. Card: **Length**, **Angle**. Tree child **Line**. |
| **Circle** | Center: click center, type **Radius** or **Diameter**. 2-pt / 3-pt: click then the same card. |
| **Rect** | Center: click center, type **Width** / **Height**. 2-pt / 3-pt: click then W/H. |
| **Polygon** | Choose Center / 2-Point / 3-Point, and Triangle…Octagon. See below. |
| **Point** | **Constrain ▾ → Point**. Click to place. Card: **U** / **V**. Enter accepts. |
| **Trim / Fillet 2D** | Click the geometry. Fillet uses the last typed radius. |

**Esc** cancels the current click sequence. The tool stays selected.

---

## The yellow edit card (HUD)

After a center-polygon click, or after a line’s second point, a card opens
in the lower-left of the viewport.

- One **field per row**. The bright row with `=` and a blinking cursor
  is what you are typing into. Empty looks like `Side = ??`.
- Type a number (`20`, `37.45`, `-15`). **Enter** applies that field.
- **Tab** applies (if you typed) and moves to the next field.
- **Esc** closes the card. The last applied value stays.

Polygon (center):

| Row | Meaning |
|-----|---------|
| **Sides** | How many edges (3–64). Enter only changes N; it does not place. |
| **Side** | Edge length in mm. Enter places the polygon. |
| **Diameter** | Circumscribed diameter in mm (coupled to Side). Enter places. |

A second click still places from the rubber-band if you prefer the mouse.

Line:

| Row | Meaning |
|-----|---------|
| **Length** | Segment length in mm. |
| **Angle** | Direction in degrees from +X (0° right, 90° up). |

The card closes when you start the next click, press Esc, or leave it
idle for about 20 seconds. It does not stay up forever.

Construct **Offset** / **Angle** planes use the same card (one field).

---

## Modes and tabs

| Tab | Job |
|-----|-----|
| **Sketch** | Draw and constrain on the active plane. |
| **Solid** | Pick / On Face → **Extrude** (Join/Cut/New) · Revolve · **Modify** (Fillet / Chamfer). |
| **Construct** | Datum, pick plane / face / origin, through 3pt, offset, angle, flip, **Sketch on Plane**. |
| **View** | ISO / Top / Front / …, grid, wireframe, 2D↔3D. |

### Construct — planes

A plane is a recipe (offset / angle / on-face / through 3 pts) hung off
Sketch_0. Offset and Angle always apply to the **active** plane — pick
that plane first.

| Button | What you do |
|--------|-------------|
| **Datum XY / XZ / YZ** | Activate or create a world datum. |
| **Pick Plane** | Click a cyan construction plane, or a **Plane** row in the tree. |
| **From Face** | Click a planar face. Makes a plane only (no sketch). |
| **Origin** | Click a vertex or a point; the active origin moves there. |
| **Through 3pt** | Three clicks. Nearby face verts snap. |
| **Offset / Angle / Flip** | Type mm or degrees on the yellow card, or flip N. |
| **Sketch on Plane** | New UV sketch on the active plane. Camera looks along N. |

Solid **On Face** is still “new sketch on that face.” Use **From Face**
when you only want the plane.

**File** and **Import / Export** live on the **top-left menubar**, not on a ribbon tab.

| Menu | Actions |
|------|---------|
| **File** | New, Open…, Save, Close, Delete…, Name Part, List Docs, Quit |
| **Import / Export** | Import DXF…, Export STEP, Export DXF |

**Open** and **Delete** list every document in Postgres. Click a row (Name + Kind), then Open. You do not have to remember the name.

**Save** uses the same list so you can overwrite, or type a new name. **Save as** is Part / Assembly / Group / Machine — that is the document kind. Assemblies that instance other parts come later; today every kind still stores the current sketch + pad.

The **Guest ▾** chip is on the right of that bar. The app starts as Guest. **Log in…** is chrome only for now (username shown; password is not sent). Logged-in vs everybody is how pgcrypto and capabilities will attach later.

The pill says **SKETCH** or **3D**. The **solid stays in the viewport** whenever
a body exists. Sketch ink and On Face sit on top of the model. **On Face**
turns the camera to that face. **Project** (Sketch tab or sketch pie) shows
or hides the dashed face outline and gold anchors.

---

## Solids, tree, timeline

1. Draw a **closed** sketch (real loops — not a bounding box).
2. **Solid → Profiles**, click the light-red face.
3. **Extrude**. A yellow **EXTRUDE [H=] OP=JOIN** card opens (default 10 mm).
   Type the depth and **Enter**. **Tab** cycles **JOIN** / **CUT** / **NEW**.
   A negative H on a face sketch defaults to **CUT**. Tree row is
   **Extrude H=20** or **Cut H=8**.

On Face → closed sketch → **Extrude**, type `-5` (or Tab to CUT, type `5`).
That is the pocket. There is no separate Cut button — CUT is an Extrude
operation. **Modify ▾** is Fillet / Chamfer.

**Revolve:** pick a profile, Revolve, click an axis line. Card: **`REV [A=360] deg`**.
Type `180` / `90` / `360` and Enter. Tree row is **Revolve  A=180**.

**Chamfer / Fillet Body:** pick the tool, click one or more edges (they
highlight). A yellow **`CHAMFER [D=2] mm`** or **`FILLET [R=2] mm`** card
opens. Type the setback / radius and **Enter**. Tree rows are **Chamfer D=2**
and **Fillet R=2**. Right-click **Edit** reopens the card; type a new D/R
and Enter — it updates that same row (no re-pick). There is no ribbon
**D=2** / **R=2** apply button — the card is the value.

**Save** onto a name that already exists asks **Overwrite** (update that part’s
latest Postgres row: height, angle, DXF) or **Keep** (leave it, pick another
name). A new name just inserts.

**Close / New / Quit** with unsaved work asks:

| Choice | What happens |
|--------|----------------|
| **Save…** | Normal save dialog, then the close/new/quit. |
| **Stash** | Writes `<name>_dirty` and leaves. Next Open (or next launch) asks **Accept** or **Discard**. |
| **Discard** | Throw the changes away. |
| **Cancel** | Stay in the file. |

**Work tree** (left): sketches, then indented pads / fillets. Right-click
a row to Edit or Name. **Expand / Collapse** folds the tree.

**Timeline** (bottom): history from `hist.txt`. Drag the slider, or
◀ ▶ undo/redo. **Prune** drops unused future steps.

---

## Mouse and keys

| Input | Action |
|-------|--------|
| Left click | Sketch point, or pick a profile / face / edge. |
| Drag (no pending click) | Orbit in 3D. |
| Middle drag | Pan. |
| Scroll | Zoom. |
| Right click | Tool pie (stay open for Line / Circle / Polygon variants). |
| Esc | Cancel click / close card / close pie. |
| Tab / Enter | Edit card (see above). |
| F1 | This manual. |
| Ctrl+Q | Quit. |

---

## Naming and save

Work-tree **Name…** (right-click a sketch or the Model row) sets an
alias. The id `Sketch_N` does not change. **File → Save** / **Open** go
to Postgres; the document includes sketch geometry and the history log.
**File → Delete…** drops that named document (confirm first). **File →
Close** clears the workspace without deleting the saved part.

A **polygon** is a sketch child (one indent under Sketch_N). Timeline
step is **Polygon**. Right-click it → **Edit** reopens Sides / Side /
Diameter; Enter rebuilds that n-gon in place. Pads on the same sketch
stay associated.
