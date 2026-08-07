# AILang CAD Kernel vs OCCT — Capability Audit

**Date:** 2026-08-07  
**Sources:** live kernel demos/smokes; OCCT Modeling Algorithms overview (BRepAlgoAPI, BRepFilletAPI, BRepBuilderAPI, BRepOffsetAPI, BRepFeat).  
**Stance:** honest domain labels, not marketing. We do **not** match OCCT breadth; we match a usable competitive *core path* for drawing → solid → STEP/view.

---

## 1. OCCT modeling map (what FreeCAD sits on)

| OCCT area | Packages (examples) | Role |
|-----------|---------------------|------|
| Geometry | `Geom_*`, `Geom2d_*` | Curves/surfaces analytic + NURBS |
| Topology | `TopoDS_*`, `BRep_*` | B-Rep containers |
| Build | `BRepBuilderAPI_*` | Make edge/face/solid, primitives |
| Booleans | `BRepAlgoAPI_*` | Fuse / Common / Cut / Section (general) |
| Fillet/Chamfer | `BRepFilletAPI_*` | Variable-R, multi-edge, complex supports |
| Offset/shell/pipe | `BRepOffsetAPI_*` | Shell, pipe, thick solid |
| Features | `BRepFeat_*` | Local features / split |
| Sweep/prism | `BRepPrimAPI_*` / sweep | Prism, revolve, pipe |
| Mesh | `BRepMesh_*` | Deflection tess |
| Exchange | STEP/IGES readers-writers | Full interchange |

Reference: [OCCT Modeling Algorithms guide](https://dev.opencascade.org/doc/overview/html/occt_user_guides__modeling_algos.html).

---

## 2. Side-by-side: AILang kernel now

| Capability | OCCT | AILang CAD | Status |
|------------|------|------------|--------|
| B-Rep store + walk | full | `CAD_Store` + radial edge | **real** |
| Box / cyl / sphere | analytic | analytic kinds + poly | **real** |
| Extrude profile | general | rect/poly/circle/multi-loop | **real** (restricted multi-hole) |
| Revolve | general | rect → cyl / annulus full 360° | **partial** |
| Loft | multi-section NURBS | 2-section ruled | **partial** |
| Sweep / pipe | path + section | path Z-change, parallel transport | **partial** |
| Boolean fuse/cut | general | restricted box/cyl/plate | **restricted** |
| Hole / pocket | general cut | plate/side/rect recipes | **restricted** |
| Plane–plane fillet | general | edge-based + equal-R digon | **real** (plane supports) |
| Plane–cyl fillet | general | cyl top/bottom rim; washer hole top | **partial** (lathe poly, not torus) |
| Chamfer | general | vertical prism + horiz box | **partial** |
| Pattern / mirror | features | clone + transform multi-shell | **real** (kind-0) |
| Shell / offset | general | open-top box shell recipe | **partial** |
| Draft | faces | rect frustum | **partial** |
| STEP out | full AP | shell walk analytic where present | **real** (export) |
| STEP in | full | not built | **open** |
| DXF sketch | — | LINE/CIRCLE/ARC/LWPOLY | **real** |
| Tess + view | many | software FB → BMP | **real** (coarse OK) |
| Constraints 2D | — | not built | **open** |
| History / naming | `BRepTools_History` | Feat stubs / loud fail | **open** |
| General isect | full | limited | **open** |

---

## 3. Gaps that kill “draw and model” first

Priority for an **interactive app** (expose pain fast):

1. **Sketch UI → kernel** — create/edit LINE/CIRCLE/ARC without external DXF  
2. **Pad/pocket from live sketch** — already recipes; need tool surface  
3. **See result** — `cad_view` BMP exists; need live loop / multi-view  
4. **Select edge for fillet/chamfer** — topology pick from tess or id list  
5. **Undo / feature list** — minimal Feat tree later  

OCCT-scale bool/fillet can wait; **latency of authoring** cannot.

---

## 4. Optional deeper OCCT grep (later)

If we vendor or clone OCCT:

```bash
# Feature surface of public APIs
rg -n "class BRepAlgoAPI_|class BRepFilletAPI_|class BRepOffsetAPI_|class BRepFeat_" src/
rg -n "class BRepPrimAPI_|class BRepBuilderAPI_Make" src/
```

Use that list only to **extend our honesty table**, not to copy architecture.

---

## 5. Recommendation

| Phase | Focus |
|-------|--------|
| **Now (done this turn)** | Plane–cyl top/bottom + washer hole rim; gates green |
| **Next** | Minimal **draw app** (sketch + pad + view + export) |
| **Parallel** | Grow bool/fillet domains only when the app hits them |

The map is clear: **kernel core is strong enough to drive a thin tool UI**; OCC parity remains a long horizon, not the next commit.
