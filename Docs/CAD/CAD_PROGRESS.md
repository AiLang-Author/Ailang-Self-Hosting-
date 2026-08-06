# CAD Kernel — Plan & Progress

**Living document.** Update every grind turn. Pair with `CAD_DEV_GUIDE.md` (process) and `CAD_Kernel_Design_v3.md` (normative).  
**Rule:** local commit after each meaningful turn so regressions are git-bisectable.

**Last updated:** 2026-08-05  
**Branch:** `master` (local; push when ready)

---

## 1. Goal

Pure-AILang CAD/CAM **kernel** (not FreeCAD glue):

- Exact B-Rep in memory → **STEP** (primary interchange). STL optional/not look-at.
- Parametric product model: **Sketch_0 root**, plane recipes, ordered tree in **Postgres**
- Capability target: box/cyl/sphere → **holes (boolean cut)** → pad/pocket → fillet → import

Proof that this class of work is doable: JS JVM track. CAD should move faster with clearer geometry milestones.

---

## 2. Jump map (here → real CAD)

| Jump | Name | Exit criteria (look-at / gate) |
|-----:|------|--------------------------------|
| **0** | Bones | Box + faceted cyl open in FreeCAD (**STEP**); measures work |
| **1** | Analytic B-Rep | Cylinder = CIRCLE edges + CYL surface; STEP continuous |
| **2** | Isect + Bool | `CreateHole` cuts a real hole; box-with-hole **STEP** |
| **3** | Features + Sketch_0 | Pad from sketch; height edit regenerates; tree order in memory then PG |
| **4** | Blend + import + UI | Fillet/chamfer; STEP import subset; viewport later |

```
[Jump 0 — DONE]
  Store · Num · eval · box · n-gon cyl · poly STEP · FreeCAD open/measure
        │
        ▼  Jump 1  ← ACTIVE
  Analytic cylinder/sphere · tess from surfaces · STEP CIRCLE/CYL
        │
        ▼  Jump 2
  Isect → Bool.Difference → hole
        │
        ▼  Jump 3
  Sketch_0 · planes · pad · PG feature_tree
        │
        ▼  Jump 4
  Fillet · import · Vulkan
```

---

## 3. Current status (Jump 0 complete)

### Done

| Item | Evidence |
|------|----------|
| `CAD_Store` slabs + handles | `test_num` / topo gates |
| `CAD_Num` tol, V3, LU, Orient* | hard gates |
| `CAD_Geom` eval + MakeLine/Plane/Circle/CylSurf | `test_geom` |
| `CAD_Topo` half-edge, MakeBoxSolid (line+plane) | `test_topo` |
| `MakeCylinderSolid` n-gon prism + analytic handles (decorative) | `test_cylinder` |
| Walk STEP polyhedra; high entity IDs (no #100 collision) | FreeCAD opens box + cyl STEP |
| **Policy: STEP = look-at truth** (STL not dual-export / not ground) | demos STEP-only |
| Design §1.4 Sketch_0 / plane recipes / PG order | design doc |
| Hole terminology = boolean cut (`CreateHole`) | Script + DEV_GUIDE |

### Look-at fixtures (STEP only — regenerate)

```bash
./ailang.x CAD/demo_primitives.ailang -o /tmp/demo_prim && /tmp/demo_prim
./ailang.x CAD/demo_hole_intent.ailang -o /tmp/demo_hole && /tmp/demo_hole
./ailang.x CAD/demo_blind_hole.ailang -o /tmp/demo_blind && /tmp/demo_blind
./ailang.x CAD/demo_multi_hole.ailang -o /tmp/demo_mh && /tmp/demo_mh
./ailang.x CAD/demo_counterbore.ailang -o /tmp/demo_cb && /tmp/demo_cb
```

| File | Notes |
|------|--------|
| `test-stl/cad_box_10x20x30.stp` | box mm |
| `test-stl/cad_box_unit.stp` | 1 mm cube |
| `test-stl/cad_cylinder_r10_h30.stp` | analytic CIRCLE + CYL |
| `test-stl/cad_sphere_r10.stp` | analytic SPHERICAL_SURFACE + equator (walk) |
| `test-stl/cad_plate_hole_offset.stp` | single through hole (walk) |
| `test-stl/cad_plate_blind_pocket.stp` | blind floor disk (walk) |
| `test-stl/cad_plate_multi_hole.stp` | through + blind independent (walk) |
| `test-stl/cad_counterbore.stp` | nested annular floor (walk) |
| `test-stl/cad_plate_rect_pocket.stp` | blind rect pocket (box−box) |
| `test-stl/cad_plate_rect_through.stp` | through rect pocket |
| `test-stl/cad_union_boxes.stp` | face-adjacent box fuse |
| `test-stl/cad_side_hole_through.stp` | hole axis +X through |
| `test-stl/cad_side_hole_blind.stp` | hole axis +X blind |
| `test-stl/cad_side_hole_y_through.stp` | hole axis +Y through |
| `test-stl/cad_side_hole_y_blind.stp` | hole axis +Y blind |
| `test-stl/cad_intersect_boxes.stp` | AABB box ∩ box |
| `test-stl/cad_rect_notch_x.stp` | rectangular notch on −X face |
| `test-stl/cad_pad_boss.stp` | plate + rectangular boss (step) |
| `test-stl/cad_fillet_edge.stp` | general FilletEdge plane–plane |

### Gates (must stay green)

```bash
./ailang.x CAD/test_geom.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_topo.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_cylinder.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_io.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_tess.ailang -o /tmp/t && /tmp/t
```

### Known limitations (honest)

- Exact-cyl B-Rep is CIRCLE/CYL; prism path still n-gon.
- `CreateHole` = restricted Bool (box−cyl → kind-3 plate; append ≤5 holes), not general B-Rep.
- Plate shells cover Z-axis holes; side-axis / freeform cuts still TODO.
- Sphere solid = two hemispheres + equator CIRCLE on SPHERICAL_SURFACE (walk).
- Sketch_0 / Feat regen / PG product path not implemented.

---

## 4. Active plan — Jump 1 (Analytic B-Rep)

### 4.1 Intent

Make **exact** geometry the solid truth; **STEP derives** from it (mesh optional).

### 4.2 Tasks

| ID | Task | Status |
|----|------|--------|
| J1.1 | Progress/plan doc + commit discipline | **done** |
| J1.2 | Exact topo: 2V + CIRCLE×2 + LINE + 3 faces | **done** |
| J1.3 | Tess: `MeshCylinderAnalytic` samples by deflection | **done** |
| J1.4 | STEP: CIRCLE + CYLINDRICAL_SURFACE | **done** |
| J1.5 | Sphere solid (analytic) + look-at STL/STEP | **done** |
| J1.6 | `MakeCylinderPrismSolid` n-gon debug path | **done** |

### 4.3 Exit criteria Jump 1

- [x] FreeCAD STEP cylinder uses **CIRCLE + CYLINDRICAL_SURFACE**  
- [x] STL faceted from **surface sampling** (kind=1), not n-gon topo walk  
- [x] Exact solid Euler **2−3+3=2**, F=3  
- [x] `test_cylinder` + `demo_primitives` green  
- [x] Progress doc updated; local commit per task

### 4.4 Non-goals Jump 1

- Holes, fillets, sketch solver, PG open/save, Vulkan

---

## 5. Mission target — Fusion-shaped features (normative intent)

Kernel geometry is not the product UI; **features** are how users build parts.
Target mental model matches Fusion 360 / mainstream parametric CAD:

### 5.1 How solids grow

| Feature | User action | Kernel meaning |
|---------|-------------|----------------|
| **Pad / Extrude (join)** | Sketch closed profile on a plane → extrude | Profile → solid; **Union** with body (or new body) |
| **Pocket / Extrude (cut)** | Sketch on face/plane → extrude **into** solid | Profile → tool solid; **Difference**(body, tool) |
| **Revolve (join/cut)** | Sketch profile + axis → revolve | Sweep profile about axis; union or difference |
| **Hole / Drill** | Place **circle on a face** → depth/through | Convenience cut: circle → tool **cylinder** → **Difference** |

All of these are the **same two engines**:
1. **Profile → solid** (extrude or revolve of sketch geometry)  
2. **Boolean** (union / difference / intersect)

“Drill” is not a third geometry kernel — it is **circle on plane + extrude cut** with hole UI defaults (through, countersink later).

### 5.2 Coordinate story (already frozen §1.4 design)

```
Sketch_0  (part root / origin plane)
   └── Pad  → body
         └── plane-on-face / offset plane
               └── Sketch_N  (circle for hole)
                     └── Pocket/Hole  → Difference(body, tool_cyl)
```

- Sketches live in **plane UV**  
- Planes are **recipes** from Sketch_0 / faces  
- B-Rep / **STEP** are **derived** after regen (STL not required)  

### 5.3 Priority order (locked 2026-08-05, reaffirmed for blend)

**Core solid-modelling B-Rep first. Sketch-driven authoring waits.**

Fillet/chamfer/shell need offset + isect + topology edits — that is the next
kernel spine. Sketch → extrude/revolve is the Fusion *control panel*; cart-before-horse
until rounds and richer solids are real.

| Order | Work | Why |
|------:|------|-----|
| 1 | Analytic solids (box, cyl, sphere) | Exact B-Rep truth ✓ |
| 2 | Transforms + restricted Bool/Isect | Holes, pockets, pad boss ✓ |
| 3 | **Offset surfaces** | Thin-wall / blend substrate |
| 4 | **Fillet / chamfer** (constant-R edge first) | Standard solid modelling |
| 5 | Then Sketch_0 + pad/pocket/revolve | Authoring on working solids |

### 5.4 Jump map

| Jump | Delivers |
|-----:|----------|
| **1** | Exact cyl ✓ · sphere · transforms |
| **2** | Restricted hole ✓ · richer bool/isect |
| **3** | Sketch_0 + Pad/Hole **(deferred until kernel solid)** |
| **4** | Fillet, import, viewport |

### 5.5 Jump 1b / 2 remaining (active)

| ID | Task | Status |
|----|------|--------|
| J1.5 | Sphere solid + tess + STEP | **done** |
| J1.7 | `TranslateSolid` + hole (cx,cy) placement | **done** |
| J2.2 | Analytic isect + LineCylinder + PlaneCylinder (horiz) | **done** |
| J2.3–J2.4 | Plate hole: offset + **partial depth** blind pocket | **done** |
| J2.5 | Multi-hole: Difference(kind3,cyl) append; analytic STEP | **done** |
| J2.6 | PlaneCylinder general (circle/gens/ellipse) + LineSphere | **done** |
| J2.7 | `RotateSolidZ` (kernel) | **done** |
| J2.8 | **Kill STEP recipes**; Export = `WritePolySolidSTEP` only | **done** |
| J2.9 | Multi / blind / nested hole **shells** (Topo, not export) | **done** |
| J2.10 | Rect pocket (box−box) + PlaneSphere | **done** |
| J2.11 | Side-hole +X; AABB box Union fuse | **done** |
| J2.12 | Side-hole +Y; demo_regen_all fixtures | **done** |
| J2.13 | Intersection boxes; ClassifyPoint; side rect notch | **done** |
| J2.14 | Pad boss shell; kind-3 hole ClassifyPoint | **done** |
| J2.15 | Shape-specific box fillets | **deleted** |
| J2.16 | **General `FilletEdge` plane–plane** (edge-based) | **done** |
| J2.17 | Multi-edge verticals + horizontal top edge | **done** |
| J2.18 | Top-rim loop (4 horiz + vertex spheres); chamfer | **next** |
| J2.19 | Plane–cyl edge blend | **next** |
| J3.* | Sketch_0 / extrude / revolve | **deferred until blend spine** |

### 5.6 Fillet / chamfer architecture (locked — no shape recipes)

**Do not** write `MakeBoxTopRimFillets` / cone-bottom specials / triangle specials.
Those do not scale to “any edge on any solid.”

**Target API (feature-level):**
```
CAD_Blend.FilletEdge(solid, edge_handle, radius) → new solid | 0
CAD_Blend.ChamferEdge(solid, edge_handle, dist [, angle]) → new solid | 0
```

**Kernel sequence for one constant-R edge fillet:**
1. Resolve edge → two support faces + shared curve  
2. **Offset** each support surface by ±R (analytic when plane/cyl/cone/sphere)  
3. **Isect** offset surfaces → spine (rail) curve  
4. Build blend surface (rolling-ball envelope / pipe)  
5. Trim supports; insert blend face; fix coedges  
6. At vertices where N edges meet: vertex blend (equal-R → sphere sector on planes)

**Order of support-surface pairs (honest domain growth):**
| # | Face pair | Why |
|--:|-----------|-----|
| 1 | **Plane–plane** | Any polyhedron edge (box, triangle prism, free faceted body) |
| 2 | Plane–cylinder | Fillet onto holes / side walls |
| 3 | Plane–cone | Cone base / draft |
| 4 | Cylinder–cylinder / sphere… | Later |

Chamfer reuses the same topology edit path with a **planar** blend strip instead of a cylinder/sphere.

Shape-specific fillet builders **removed**. Use `CAD_Blend.FilletEdge(solid, edge, R)`.
| J3.* | Sketch_0 / extrude / revolve | **deferred** |

**Honesty rule:** do not mark hole/pad green until boolean or extrude produces wrong-on-fail geometry.

---

## 6. Backlog (after solid engine)

1. Sketch_0 + pad + circle hole (thin feature spine)  
2. Repo `feature_tree` JSONB  
3. Fillet / blend, STEP import, viewport  

---

## 7. Turn log

| Date | Commit / turn | What | Gates |
|------|---------------|------|-------|
| 2026-08-05 | prior commits | Store, Num, Topo box, tess STL | green |
| 2026-08-05 | `15d7f053` | `CAD_PROGRESS.md` + Sketch_0 §1.4 | — |
| 2026-08-05 | `7282e993` | Jump 0: n-gon cyl, poly STEP, fixtures | green |
| 2026-08-05 | `35c73cb4` | J1.4 analytic cyl STEP | green |
| 2026-08-05 | `8bc64a77` | J1.2+J1.3 exact cyl B-Rep + surface mesh | green |
| 2026-08-05 | `3c5e7b1b` | Fusion map; cut tool path | green |
| 2026-08-05 | `c11d2960`/`9dd4e73b` | Plate with hole mesh+STEP | green |
| 2026-08-05 | `d0cc8981`/`942bf429` | Analytic 8-octant sphere STEP | green |
| 2026-08-05 | `e97d29b0` | Placement + base Isect | green |
| 2026-08-05 | prior | LineCyl/PlaneCyl; blind pocket mesh depth; offset hole | green |
| 2026-08-05 | `ced6d052` | Blind STEP: z_floor cyl + solid bottom + floor disk | green |
| 2026-08-05 | prior | Multi-hole append (max 5) — grid mesh was wrong | red |
| 2026-08-05 | prior | Multi-hole earclip STL broken (missing pocket / face distortion) | red |
| 2026-08-05 | prior | Multi-hole STL grind abandoned (inferior format) | — |
| 2026-08-05 | `b6a59f52` | **STEP-first policy**: demos export STEP only | green |
| 2026-08-05 | prior | PlaneCyl + LineSphere; RotateSolidZ; bad rot45 demo | mixed |
| 2026-08-05 | prior | Counterbore STEP recipe (temporary) | mixed |
| 2026-08-05 | `5fbf4901` | **Delete all STEP recipes**; ExportSTEP = B-Rep walk only | green |
| 2026-08-05 | `392e786e` | **J2.9** `BuildPlateHoleShell`: multi/blind/nested counterbore | green |
| 2026-08-05 | `49323305` | Exact sphere B-Rep: SPHERICAL_SURFACE + two hemispheres | green |
| 2026-08-05 | `af55187e` | Counterbore wall coedge senses (no vanishing cyl) | green |
| 2026-08-05 | `02721f84` | Rect pocket box−box Bool + PlaneSphere | green |
| 2026-08-05 | `c2fb33df` | Side-hole +X + box Union fuse | green |
| 2026-08-05 | `9d778a11` | Side-hole +Y; `demo_regen_all` | green |
| 2026-08-05 | `00f5af08` | Box Intersection; ClassifyPoint; rect notch +X | green |
| 2026-08-05 | `2ec3ef81` | Pad boss; kind-3 ClassifyPoint holes | green |
| 2026-08-05 | `dd389f76` | Policy: general edge blend, not shape recipes | — |
| 2026-08-05 | *(this)* | Delete shape fillets; `FilletEdge` plane–plane edge-based | green |
| | | *next: multi-edge robustness; chamfer; plane–cyl* | |

---

## 8. Process (every turn)

1. Update **§6 Turn log** + task status in §4.2  
2. Implement smallest vertical slice with **look-at or gate**  
3. Run relevant gates  
4. **`git commit`** only CAD-related paths (do not mix unrelated tree wipes)  
5. If red: fix or revert before next feature  

### Commit scope hygiene

- Include: `Librarys/Cad/`, `CAD/`, `Docs/CAD/`, `test-stl/cad_*`  
- Exclude unless intentional: mass `TestCode/` deletes, binaries, screenshots, JS JVM paths  

---

## 8. Related

| Doc | Role |
|-----|------|
| `CAD_Kernel_Design_v3.md` | Normative (incl. §1.4 product model) |
| `CAD_DEV_GUIDE.md` | Day-to-day process + look-at commands |
| `plane_coordinate_tree_spec.md` | Plane feature tree |
| `CAD_PROGRESS.md` | **This file** — plan + progress |
