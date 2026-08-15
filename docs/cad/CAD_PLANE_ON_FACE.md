# Plane-on-face + Sketch_0 lineage

**Status:** identity + persist tree in (2026-08-13). Signature rebind is last-resort only.  
**Normative:** `CAD_Kernel_Design_v3.md` §1.4.  
**Do not** treat signature-matching as the long-term identity model.

---

## Root rule (locked)

**Sketch_0 is the part root.** It owns origin `O` / `+X` / `+Y` (usually world XY).

- Every later **plane** stores `parent_plane` (slot 17) and is a **recipe** on that parent: offset, angle, flip, or “on face of a body grown from this lineage.”
- Every later **sketch** stores `plane_id` and is **UV only**. World XYZ = `EvalFrame(plane) × (u,v,0)`.
- Regen walks **Sketch_0 → child planes → sketches → features**. No heuristic “find a similar face and hope.”
- Reorder or orphan Sketch_0 is unsupported. Loud fail, never silent renumber.

Offset / angle already write `parent`. Face planes now do the same: `CA_SketchOnFace` parents the new plane to the **active plane** (the one that grew the solid), which chains to `CadApp.sk0_plane`.

Signature rebind (`centroid+normal`) is a **last-resort loud miss** if the live face handle died — not the source of truth.

---

## What exists

| Piece | Role |
|-------|------|
| `CreateWorldXY` | Sketch_0 home plane (`sk0_plane`) |
| `CreateOffset` / `CreateAngleX/Y` / `Flip` | Child recipes; parent in slot 17 |
| `CreateFromFace` + `SetParent` | Face plane hung off Sketch_0 lineage |
| `PickFaceRay` / OnTop | Click planar B-Rep face → new sketch |
| `RebindFace` | Signature fallback after rebuild; **-1** if lost |
| `MapLocal` | UV → world via evaluated frame |

**AABB is not a face.** `SolidBounds` is framing only.

---

## Cmds

| Cmd | Action |
|-----|--------|
| `plane_xy` | Activate Sketch_0 |
| `plane_off N` | Offset active along normal |
| `plane_ang N` | Rotate about local X |
| `plane_flip` | Reverse normal |
| `plane_pick` | Click a construction plane (or tree Plane row) to activate |
| `plane_from` | Click a planar face → construction plane only (no sketch) |
| `plane_org` | Click a vertex/point → move active origin there |
| `plane_3pt` | Click three points → new plane |
| `sketch_pln` | New sketch on active plane |
| Sketch on Face (`plane_top`) | Click a planar face → **new** UV sketch parented to Sketch_0 (not Sketch_0 itself) |

---

## Still to grind

1. Dogfood: Sketch_0 pad → OnTop → named face → sketch → pad/cut; no XY fallback  
2. Project face edges — dashed loop + gold anchors (`proj` toggle). Snap-to-edge next.  
3. Dim values on the Constrain tab (solver already origin-relative)

---

## Repo roles

| Role | Content |
|------|---------|
| `plane_tree` | PT1 JSON: `sk0`/`act`/`skpl` + `P` recipe rows (parent pid, mode, offset/angle bits, frame, sig) |
| `face_map` | FM1 JSON: stable plane pid ↔ face signature (Sketch_0 lineage, not “face #7”) |
| `profile_dxf` | Sketch IR; `skpl` in `plane_tree` rebinds UV on load |

HUD (`hud.txt`): `sk0=` `pl=` `par=` `face=` `n=` — real pids, not 0/1 flags.  
Regen after pad: `CA_RegenPlaneTree` walks registration order (parents first). FACE miss is logged, never silent XY.
