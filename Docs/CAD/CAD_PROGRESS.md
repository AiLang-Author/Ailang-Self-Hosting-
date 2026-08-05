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
| J1.2 | Exact topo: 2 verts + CIRCLE×2 + LINE + 3 faces | pending |
| J1.3 | Tess: sample CIRCLE / CYL by deflection | pending |
| J1.4 | STEP: CIRCLE + CYLINDRICAL_SURFACE (+ solid kind=1 r,h) | **done** (export path; topo still n-gon for mesh) |
| J1.5 | Sphere solid (analytic) + look-at STL/STEP | pending |
| J1.6 | Keep n-gon path as fallback / debug | partial (n-gon still builds mesh) |

### 4.3 Exit criteria Jump 1

- [x] FreeCAD STEP cylinder uses **CIRCLE + CYLINDRICAL_SURFACE** (re-open `cad_cylinder_r10_h30.stp`)  
- [ ] STL still faceted but generated from surface sampling (not only n-gon walk)  
- [x] `test_cylinder` + `demo_primitives` green  
- [x] Progress doc updated; local commit per task

### 4.4 Non-goals Jump 1

- Holes, fillets, sketch solver, PG open/save, Vulkan

---

## 5. Backlog (ordered after Jump 1)

1. Jump 2: analytic isect subset → `Bool.Difference` → box-with-hole fixture  
2. Jump 3: plane feature + Sketch_0 + CreatePad → memory feature list  
3. Repo: `feature_tree` JSONB commit/open  
4. Jump 4: blend, STEP import, viewport  

---

## 6. Turn log

| Date | Commit / turn | What | Gates |
|------|---------------|------|-------|
| 2026-08-05 | prior commits | Store, Num, Topo box, tess STL | green |
| 2026-08-05 | *(this session)* | Geom records, n-gon cyl, poly STEP, ID fix, Sketch_0 §1.4 | green |
| 2026-08-05 | `15d7f053` | `CAD_PROGRESS.md` + Sketch_0 §1.4 | — |
| 2026-08-05 | `7282e993` | Jump 0: n-gon cyl, poly STEP, fixtures | green |
| 2026-08-05 | *(this)* | J1.4 analytic cyl STEP (`WriteCylinderAnalyticSTEP`, solid kind=1) | green |
| | | *next: J1.2/J1.3 exact topo + surface tess; or hole jump* | |

---

## 7. Process (every turn)

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
