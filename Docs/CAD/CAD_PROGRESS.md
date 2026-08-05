# CAD Kernel — Plan & Progress

**Living document.** Update every grind turn. Pair with `CAD_DEV_GUIDE.md` (process) and `CAD_Kernel_Design_v3.md` (normative).  
**Rule:** local commit after each meaningful turn so regressions are git-bisectable.

**Last updated:** 2026-08-05  
**Branch:** `master` (local; push when ready)

---

## 1. Goal

Pure-AILang CAD/CAM **kernel** (not FreeCAD glue):

- Exact B-Rep in memory → **STEP** (interchange) + **STL** (mesh)
- Parametric product model: **Sketch_0 root**, plane recipes, ordered tree in **Postgres**
- Capability target: box/cyl/sphere → **holes (boolean cut)** → pad/pocket → fillet → import

Proof that this class of work is doable: JS JVM track. CAD should move faster with clearer geometry milestones.

---

## 2. Jump map (here → real CAD)

| Jump | Name | Exit criteria (look-at / gate) |
|-----:|------|--------------------------------|
| **0** | Bones | Box + faceted cyl open in FreeCAD (STL/STEP); measures work |
| **1** | Analytic B-Rep | Cylinder = CIRCLE edges + CYL surface; STEP continuous; tess samples surfaces |
| **2** | Isect + Bool | `CreateHole` cuts a real hole; box-with-hole STL/STEP |
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
| Tess n-gon fan, 3-decimal STL, CircleSegCount(r,δ) + visual floor | STL look-at |
| Walk STEP polyhedra; high entity IDs (no #100 collision) | FreeCAD opens box + cyl STEP |
| Design §1.4 Sketch_0 / plane recipes / PG order | design doc |
| Hole terminology = boolean cut (`CreateHole`) | Script + DEV_GUIDE |

### Look-at fixtures (regenerate)

```bash
./ailang.x CAD/demo_primitives.ailang -o /tmp/demo_prim && /tmp/demo_prim
```

| File | Notes |
|------|--------|
| `test-stl/cad_box_10x20x30.stl/.stp` | box mm |
| `test-stl/cad_box_unit.stl/.stp` | 1 mm cube |
| `test-stl/cad_cylinder_r10_h30.stl/.stp` | **faceted** cylinder (n-gon truth) |

### Gates (must stay green)

```bash
./ailang.x CAD/test_geom.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_topo.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_cylinder.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_io.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_tess.ailang -o /tmp/t && /tmp/t
```

### Known limitations (honest)

- Cylinder B-Rep is **chords**, not CIRCLE/CYLINDER as topology truth → looks segmented (correct).
- `CreateHole` / Bool / Isect not real.
- STEP walk is polyhedral only (planes + lines).
- Sketch_0 / Feat regen / PG product path not implemented.

---

## 4. Active plan — Jump 1 (Analytic B-Rep)

### 4.1 Intent

Make **exact** geometry the solid truth; mesh and STEP **derive** from it.

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
- B-Rep / STEP / STL are **derived** after regen  

### 5.3 Priority order (locked 2026-08-05)

**Kernel geometry engine first. Sketch-driven solids wait.**

Sketch → pad/revolve is the Fusion *control panel*; cart-before-horse if the solid
engine is incomplete. Ailang function layers make features easy to hang on later.

| Order | Work | Why |
|------:|------|-----|
| 1 | Analytic solids (box, cyl, **sphere**) | Exact B-Rep truth |
| 2 | **Transforms** (translate, later rotate) | Place tools / holes not only at origin |
| 3 | **Bool** expand + **Isect** | Real cuts beyond plate−cyl special case |
| 4 | Then Sketch_0 + pad/pocket/revolve | Authoring on top of working solids |

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
| J2.5 | Multi-hole: Difference(kind3,cyl) append; mesh+STEP | **done** |
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
| 2026-08-05 | *(this)* | Multi-hole: bridge+earclip circular rims; analytic multi STEP | green |
| | | *next: general plane–cyl isect / richer bool; sketch deferred* | |

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
