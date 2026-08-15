# CAD UI usability — live grind

**Replaces:** `CAD_UI_CLEANUP.md` (tabs/pies v1 — done, archived by this file).  
**Date:** 2026-08-15  
**Rule:** Gtk is chrome. Kernel owns camera, geometry, and what “in view” means.

The ribbon/File/HUD/session pass is good enough. This file is the next
work: **see the model, sketch on it, use its edges.**

---

## Locked

- Five work tabs + View. File is a menubar. Guest vs login chrome exists.
- On Face lives on **Solid** + 3D pie (`ontop` / `plane_top`).
- Sketch HUD (line/circ/rect/poly/fillet/point) and Extrude H+JOIN/CUT/NEW / Revolve A / Chamfer D / Fillet R cards.
- Save overwrite vs keep; dirty Close → Save / Stash / Discard.
- **File → Save** / Ctrl+S writes the open name immediately (`saveover`). **Save As…** is the picker. Listing no longer remeshes or enters the old in-window file browser.

---

## Now (this grind)

### 1. Persistent model view

The shaded body stays on screen whenever a solid exists.

| You are | What you should see |
|---------|---------------------|
| Open / Solid / Pick / Profiles | 3D model (already) |
| Sketch tools | **Same 3D model**, sketch ink over it |
| On Face | **Same 3D model**, camera facing that face |

- [x] Do not dump the tess cache on sketch enter (`HoldSolidTess` is a no-op)
- [x] Do not `FB_Clear` the solid when drawing 2D overlay
- [x] Solid tab `profiles` stays in 3D and keeps the body
- [x] On Face looks along the face normal
- [ ] Sketch tab click should not feel like “left the part” (pill can say SKETCH; viewport still the model)
- [ ] Face-on camera after On Face — dogfood on side vs top faces

### 2. Projected geometry (Fusion “Show projections”)

On Face already plants gold frozen points (≤12 verts). Next is **edges**.

| Piece | Status |
|-------|--------|
| Gold anchor points on face verts | exists (`n_face_ref`) |
| Dashed projected face loop | **in** (`show_proj`, default on) |
| Sketch **Project** button + pie **Project** | **in** (`proj` toggle) |
| Coincident / snap to projected edges (not just points) | next |
| RMB “Show / Hide projections” on the sketch row | next |
| Project more than the host face (other edges, axes) | later |

Projected edges are **reference** (dashed). They must not become pad profiles.

### 3. Construction planes (pick + conditions)

Planes are recipes on Sketch_0. You have to **aim** them.

| Action | How |
|--------|-----|
| Pick an existing plane | Construct **Pick Plane** and click the cyan overlay, or click a **Plane** row in the tree |
| Plane on a face | Construct **From Face** → click a planar face (no sketch yet) |
| Set origin | Construct **Origin** → click a vertex or a point on the plane |
| Through 3 points | Construct **Through 3pt** → three clicks (verts snap) |
| Offset / Angle / Flip | Still apply to the **active** plane (pick first) |
| Sketch on that plane | Construct **Sketch on Plane** (also 3D pie) |

Solid **On Face** still means “new sketch on that face.” From Face is the plane-only version.

- [x] Pick plane (3D overlay + tree `N` rows)
- [x] From Face (construction plane, stay in 3D)
- [x] Origin (project click / snap vertex)
- [x] Through 3 points
- [x] Sketch on Plane (`sketch_pln`)
- [ ] Angle about a picked edge (later)
- [ ] Offset distance drag handle (later)

### 4. Still parked (do not start unless we say)

- Solid HUD for Cut / 3D fillet / chamfer
- Users / groups / pgcrypto
- Assembly occurrences
- Measure / Surface tabs
- Kernel Move/Freemove

---

## How to check

1. Open `blockt` (or any pad). You see the solid.
2. Solid → On Face → click a face. Solid stays; view faces that plane; gold points + dashed outline.
3. Sketch → Center Rect on that face. Solid still behind the ink.
4. Project toggles the dashed outline.
5. Solid tab. Still the solid (not an empty 2D pad).

---

## Cmds

| Cmd | Meaning |
|-----|---------|
| `plane_top` / `ontop` | On Face pick |
| `plane_pick` | Activate a construction plane |
| `plane_from` | Plane from a planar face |
| `plane_org` | Set active origin |
| `plane_3pt` | Plane through 3 points |
| `sketch_pln` | New sketch on the active plane |
| `proj` | Toggle projected face edges |
| `profiles` | 3D pick profiles (keeps body) |
