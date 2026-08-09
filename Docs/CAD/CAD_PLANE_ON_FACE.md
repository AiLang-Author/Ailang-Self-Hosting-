# Plane-on-face + topo naming (product strategy)

**Status:** design lock for next kernel tranche (after document UI).  
**Depends on:** orthogonal `CAD_Repo` assets, working open/save, sketcher on a plane.

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
