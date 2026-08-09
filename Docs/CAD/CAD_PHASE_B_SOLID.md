# Phase B — Sketch → Solid

**Parent:** `CAD_CORE_COMPETITIVE_PLAN.md`  
**After:** Phase A (DXF/sketch IR complete)  
**Architecture:** Feat = recipes only. Sketch → tool or body solid via Topo; cuts via Bool.Difference (restricted domain, honest).

---

## What is DXF “bulge”? (aside)

On an **LWPOLYLINE**, each vertex can carry group **42 = bulge**:

```text
bulge = tan(θ / 4)
```

where **θ** is the included angle of a circular arc from this vertex to the next.

| bulge | Geometry |
|------:|----------|
| `0` | Straight segment (line) |
| `> 0` | Arc CCW from this point to next |
| `< 0` | Arc CW |
| `±1` | Semicircle |

FreeCAD / QCAD / AutoCAD emit bulges instead of separate `ARC` entities when you draw polylines with arc segments.  
We already convert them in **A1** via `CAD_Sketch.AddBulgeSegment` (uses `Atan` / `Atan2`).  
A “FreeCAD bulge fixture” just means a DXF **exported from FreeCAD** with non-zero 42 values — good for regression; not a new feature.

---

## Layer contracts (Phase B)

| Library | Adds | May call |
|---------|------|----------|
| `CAD_Feat` | `ExtrudeCut`, `RevolveProfile` | Sketch, Topo, Bool, Num |
| `CAD_Topo` | only if new solid builder needed | Geom, Store, Num |
| `CAD_Bool` | no change unless domain expand | Topo |
| `CAD_IO` / CLI | load+cut / revolve demos | Feat |

**Verbs:** `ExtrudeProfile` (pad), `ExtrudeCut` (pocket), `RevolveProfile` (pad lathe).

---

## Sub-phases

### B1 — Extrude pad refine  **[done interactive 2026-08-08]**
- Multi-loop pad + interactive multi-circle/dogbone outer envelope  
- `MakePolyPrism` cap **2048** (was 64 — blocked peanut/dogbone pads)  
- Live sketch: circles/arcs as entities; projection tess on clone only  
- Demos: `demo_peanut_pad`, `demo_trim_circle`, look-at `dogbone.png` / `solid.png`

### B2 — Extrude cut  **[done]**
- `CAD_Feat.ExtrudeCut(body, sketch, depth)`  
- Rect → `CreateRectPocket`; pure circle → `CreateHole`; through poly → plate shell  
- Demos: `demo_extrude_cut`, `_circle`, `_poly`  

### B3 — Revolve pad  **[kernel done; app UI next]**
- Sketch **X = radius**, **Y = height** → solid Z; full 360° about +Z  
- Rect on-axis → cylinder; xmin>0 → `MakeAnnulusPrism` tube  
- **Next grind:** wire revolve into `cad_app` (tool + look-at), same buffer path as pad  

### B4 — Revolve cut  **[kernel done]**
- `CAD_Feat.RevolveCut(body, sketch, angle)`  
- On-axis revolve tool + box body → hole recipe / Difference  
- Demo: `demo_revolve_cut` 

### B5 — Analytic prefer  **[partial]**
- Pure-circle extrude → `MakeCylinderSolid`  
- Mixed profiles still poly prism after tess  

### B6 — Draft + midplane  **[done]**
- `ExtrudeDraft(sketch, h, draft_rad, outward)` — rect only → `MakeRectFrustum`  
- `ExtrudeSymmetric(sketch, h)` — pad centered on z=0

---

## Gates

```bash
./CAD/smoke_phase_b.sh
```

| Test | Expect |
|------|--------|
| Rect ExtrudeCut | pocket STEP |
| Circle ExtrudeCut | 2 FACE_BOUND |
| Poly through ExtrudeCut | 2 FACE_BOUND |
| Revolve on-axis / washer | cyl + tube STEP |
| RevolveCut | 2 FACE_BOUND |

---

## Exit criteria (B1–B6 core)

- [x] ExtrudeCut rect / circle / through poly  
- [x] RevolveProfile cylinder + tube  
- [x] RevolveCut box − revolved cylinder  
- [x] ExtrudeDraft rect frustum + ExtrudeSymmetric  
- [x] `./CAD/smoke_phase_b.sh`  

**B5** partial. Fusion/FreeCAD feature map (target vs now):

| Fusion / FreeCAD | Ours |
|------------------|------|
| Pad | `ExtrudeProfile` / `CreatePad` |
| Pocket | `ExtrudeCut` |
| Revolution | `RevolveProfile` |
| Groove | `RevolveCut` |
| Draft (pad) | `ExtrudeDraft` (rect) |
| Midplane | `ExtrudeSymmetric` |
| Fillet / Chamfer | Blend (plane–plane / box corner) |
| Hole | `CreateHole` |
| Loft / Sweep | not yet |
| Shell (box open) | `Shell` thickness |
| Linear / circular pattern | `LinearPattern` / `CircularPattern` (box compound) |
| Mirror | `Mirror` (box compound) |