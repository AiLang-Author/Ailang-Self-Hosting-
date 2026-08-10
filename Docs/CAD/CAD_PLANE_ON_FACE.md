# Plane-on-face + topo naming (product strategy)

**Status:** **v1 done** — face pick + signature rebind (2026-08-09).  
**Depends on:** sketch→profile→pad/revolve (done); origin CS-0 (done).

### Implementation (no AABB faces)

| Piece | Role |
|-------|------|
| `PickFaceRay` | ray vs planar B-Rep faces + UV in-face |
| `CreateFromFace(face, solid)` | plane recipe: live handle + **signature** + **pid** |
| Signature | face centroid + normal; match **in-plane** (height slide OK) |
| `RebindFace` / `EvalFrame` | re-resolve after rebuild; **-1** if lost (no invent) |
| App **OnTop** | click face → sketch; pad → `RebindFace` on new solid |

**AABB face model removed.** `SolidBounds` = vert extents for framing only.

### Bare construction planes (loft / draft setup)

| Cmd / panel | Action |
|-------------|--------|
| **XY** / `plane_xy` | World Sketch_0 plane |
| **XZ** / **YZ** | Datum planes |
| **Off50** / `plane_off N` | Offset active plane along normal by N mm |
| **Flip** / `plane_flip` | Reverse normal (face a partner plane) |
| **Ang90** / `plane_ang N` | New plane rotated N° about local X |
| **SkPln** / `sketch_pln` | New sketch on active plane (no solid needed) |
| **OnTop** | Still: pick solid face → sketch |

Typical loft setup: **XY** → **SkPln** (profile A) → **Off50** → **Flip** → **SkPln** (profile B) → loft verb (next).

### Seeing planes (3D overlay)

Construction planes are **drawn in 3D mode** (`m` / Sketch/3D toggle):

- **Dashed grid** (see-through) ±40 mm UV  
- **Border**: cyan; **active plane** yellow  
- **Axes**: U red, V green, normal cyan; yellow origin  
- **Current sketch** projected onto its plane in cyan  

After **Off / Ang / XY / XZ / YZ / Flip** the app switches to **3D** so the new plane is visible — **orbit** with LMB drag.  
**SkPln** returns to 2D UV for drawing; press **m** again to inspect in 3D.

### UI (dogfood)

1. Pad base solid (Sketch_0). Stay in **3D**.  
2. **OnTop** → status: `click FACE for sketch`.  
3. Orbit if needed; **short LMB click** on a planar solid face.  
4. App enters **sketch** on that face plane.  
5. Draw → Profiles → Pad.

---

## Problem

Creating a sketch “on a face” is where FreeCAD-style **topo naming chaos** starts:
later pads/cuts change face identities, and references break.

## Strategy (wedded plane, not raw face id)

When the user starts a **new sketch on a face**:

1. **Create a `PlaneFeature`** (see `plane_coordinate_tree_spec.md`) **bound to that face**.
2. Place the sketch on that plane (not “floating in world XY”).
3. **Persist the plane as a recipe relative to world XYZ zero**, not only as “face #7”:
   - origin (point / face centroid / …)
   - normal / orientation (angle relative to world axes)
   - offset distance along normal
   - optional modifiers (tilt, flip)
4. Store as repo asset role **`plane_tree`** (JSON) on the revision, plus a **link** from the sketch feature to that plane id in `feature_tree`.

### Why this helps

| Edit | Desired behavior |
|------|------------------|
| Tilt the cylinder / host solid | Plane **stays wed to the face** (re-eval recipe from face + stored offsets) |
| Change face boundary shape | Plane still defined by face attachment + recipe |
| Change height of box under the plane | Plane **follows** the face (attachment re-solved) |

**Alignment drift can happen** — that is acceptable.  
What we **refuse** is silent rebinding to the wrong face (topo chaos).

If the supporting face cannot be re-identified, **loud failure** (same spirit as `CAD_Feat.ResolveNaming` → refuse inventing entities).

---

## Persistent naming role

- **Face/edge pids** (`face_map` asset) name entities for **picking and reattachment**.
- The **sketch does not store “face 12” alone** — it stores **plane id**, and the plane stores **attachment + world-relative recipe**.
- After regen: resolve face via pid map → recompute plane frame → sketch UV stays on that plane.

## Next feature after planes: face projection

Once sketch lives on a face-plane:

- **Project** edges/curves from the underlying face into the sketch plane  
  so the user can hang dimensions / profile off the real solid (odd extrudes/revolves).

That is a **sketcher** feature (project external geometry), not a pure topo feature.

---

## Implementation order

1. ~~Document open/save UI~~ (basic list / open / save / close)
2. **PlaneFeature eval** + `plane_tree` asset write/read  
3. **Sketch on plane** (not only world XY)  
4. **Auto plane-on-face** when “new sketch on face” is invoked  
5. **face_map** pids + `ResolveNaming`  
6. **Project face geometry** into sketch  

---

## Repo asset roles (already reserved)

| Role | Content |
|------|---------|
| `plane_tree` | PlaneFeature JSON (origin, mode, angles, distances) |
| `face_map` | Persistent face/edge ids ↔ topology hints |
| `profile_dxf` | Sketch IR (may later key by plane id) |
