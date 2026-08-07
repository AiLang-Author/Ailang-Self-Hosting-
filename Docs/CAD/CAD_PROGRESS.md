# CAD Kernel — Plan & Progress

**Living document.** Update every grind turn. Pair with `CAD_DEV_GUIDE.md` (process) and `CAD_Kernel_Design_v3.md` (normative).  
**Rule:** local commit after each meaningful turn so regressions are git-bisectable.

**Last updated:** 2026-08-07 (loft / sweep / non-box pattern via CloneKind0)  
**Branch:** `master` (local; push when ready)  
**Strategy:** `Docs/CAD/CAD_CORE_COMPETITIVE_PLAN.md` · Phase A: `CAD_PHASE_A_SKETCH.md`

---

## 1. Goal

Pure-AILang CAD/CAM **kernel** (not FreeCAD glue):

- Exact B-Rep in memory → **STEP** (primary interchange). STL optional / not look-at.
- Parametric product model later: **Sketch_0 root**, plane recipes, ordered tree in **Postgres**
- Capability path: analytic solids → restricted bool/holes → **edge blend (fillet digon)** → sketch-driven features → import/UI

---

## 2. Jump map

| Jump | Name | Status |
|-----:|------|--------|
| **0** | Bones (box, poly STEP) | **done** |
| **1** | Analytic B-Rep (CIRCLE/CYL/SPHERE) | **done** |
| **2** | Isect + restricted Bool/holes/pad | **done** (restricted domain) |
| **2b** | Plane–plane edge blend + equal-R digon | **done** (this tranche) |
| **3** | DXF/sketch completeness (Phase A) | **done** LWPOLY+multi-loop+export |
| **3b** | Sketch→solid Pad/Cut/Revolve (Phase B) | **B2–B4 done**; B5 partial; B6 open |
| **4** | Solid tools Phase C | **C4 chamfer, C5 cyl−cyl, C6 rotate**; C3 open |

```
[Jump 0–2 DONE]  →  [Jump 2b fillet digon DONE]
        │
        ▼  Jump 3  ← ACTIVE
  DXF LINE import → closed loop → ExtrudeProfile → STEP  ✓ rect + diamond
  next: CIRCLE/ARC, revolve, draft, hole-from-circle, Sketch_0 constraints
        │
        ▼  Jump 4
  Chamfer · plane–cyl · unequal-R ball corner · STEP body import · Vulkan
```

---

## 3. Current status snapshot

### Kernel solid / bool (earlier jumps)

| Item | Evidence |
|------|----------|
| `CAD_Store` / `CAD_Num` / `CAD_Geom` | gates `test_num`, `test_geom` |
| Box / cyl / sphere analytic + walk STEP | `demo_primitives` |
| Restricted hole/pocket/union/pad shells | demos under `test-stl/cad_plate_*`, etc. |
| STEP-first, **no export recipes** | `ExportSTEP` shell walk only |

### Fillet / digon tranche (2026-08-06) — look-at fixtures

```bash
./ailang.x CAD/demo_fillet_edge.ailang      -o /tmp/d && /tmp/d   # R=5 one vertical
./ailang.x CAD/demo_fillet_horiz.ailang     -o /tmp/d && /tmp/d   # R=5 top front
./ailang.x CAD/demo_fillet_verticals.ailang -o /tmp/d && /tmp/d   # R=4 ×4 verts
./ailang.x CAD/demo_fillet_edges.ailang     -o /tmp/d && /tmp/d   # R=4 box top digon
./ailang.x CAD/demo_fillet_wedge.ailang     -o /tmp/d && /tmp/d   # R=3 apex 31° digon
./ailang.x CAD/demo_fillet_roof.ailang      -o /tmp/d && /tmp/d   # R=2.5 planes 15° digon
```

| File | What it proves |
|------|----------------|
| `test-stl/cad_fillet_edge.stp` | Single plane–plane `FilletEdge` (vertical) |
| `test-stl/cad_fillet_horiz.stp` | Single plane–plane horizontal |
| `test-stl/cad_fillet_verticals.stp` | Sequential multi-edge (disjoint verts) |
| `test-stl/cad_fillet_edges.stp` | **Equal-R digon** top cycle box 90° (4 CYL + 4 ELLIPSE, 0 sphere) |
| `test-stl/cad_fillet_wedge.stp` | Digon on **31°** wedge prism (3 CYL + 3 ELLIPSE) |
| `test-stl/cad_fillet_roof.stp` | Digon **shallow 15°** plane angle / 165° solid apex, R=2.5 |

### Gates (must stay green)

```bash
./ailang.x CAD/test_geom.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_topo.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_cylinder.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_io.ailang -o /tmp/t && /tmp/t
./ailang.x CAD/test_tess.ailang -o /tmp/t && /tmp/t
```

### Known limitations (honest)

- `CreateHole` / plate shells = **restricted** bool domain, not general B-Rep cut.
- Fillet = **plane–plane** only; no plane–cyl / cone / cyl–cyl yet.
- Equal-R **digon** at shared vertices (cylinders + Steinmetz ellipses). **No sphere face** on that path.
- Unequal-R “ball corner”, chamfer, variable-R: **not built**.
- Sketch constraints / Solve2D / PG product path: **not implemented**.
- DXF: **LINE only** (z≈0); no LWPOLYLINE/ARC/CIRCLE yet; no revolve/draft.
- AILang stack: Address locals clobber across nested calls — digon pins state on `digon_S` heap.

---

## 3b. Implemented vs not — DXF → extrude tranche (2026-08-06)

### Implemented ✓

| Capability | Locus | Notes |
|------------|--------|--------|
| ASCII DXF **LINE** parse | `CAD_DXF.ImportFile` | ENTITIES section; 2D (z≈0) only |
| ASCII DXF **CIRCLE** | `CAD_DXF.ImportFile` | Pure-circle sketch → analytic cylinder extrude |
| ASCII DXF **ARC** | `CAD_Sketch.AddArc` / `TessellateArcs` | Slot/capsule profiles; tess → LINEs |
| Sketch line/circle storage + **closed loop chain** | `CAD_Sketch.*` / `BuildClosedLoop` / `TessellateCircles` | Real Store-backed profile |
| **Extrude** closed loop +Z | `CAD_Feat.ExtrudeProfile` | AABB rect → box; poly → `MakePolyPrism` (≤64); pure CIRCLE → cyl |
| Poly prism solid | `CAD_Topo.MakePolyPrism` | Non-rect profiles (diamond, keyhole) |
| **Plate + through poly hole** | `MakePlateThroughPolyHole` / `ExtrudePlateThroughHole` | Outer rect + inner poly (escutcheon) |
| **Path → solid (no fixtures)** | `CAD_IO.LoadDXFExtrude` / `LoadDXFPlateHole` | Arbitrary DXF path → solid |
| **CLI loader + pipe** | `CAD/cad_load.ailang` → `cad_load.x` | files or `stdin DXF → stdout STEP` (`-` default) |
| DXF from fd/buffer | `CAD_DXF.ImportFd` / `ImportBuffer` | pipe-safe ReadAllFd |
| STEP to fd | `CAD_IO.ExportSTEPFd` | stdout without closing |
| **Software viewport** | `CAD_View` + `cad_view.x` | Tess → headless FB → BMP; optional host `eog` |
| Screenshots for agents | `CAD_View.SaveFBToBMP` / `--shot` | no FreeCAD required |
| Multi-loop face tess | `MeshFaceLoopsXY` (bridge + ear-clip) | plate holes visible in view |
| Edge overlay + face tint | `CAD_View.DrawMesh` | axis-tinted shade + wire edges |
| Smoke | `CAD/smoke_view.sh` | square / keyhole / diamond / escutcheon / slot / top |
| View presets | `--view 0\|1\|2` iso/top/front; `--wire`; `--defl` | daily look-ats without FreeCAD |
| **CLI contract v1** | `Docs/CAD/CAD_CLI.md` | frozen `cad_load` / `cad_view` + scripts |
| DXF demos | cube / diamond / keyhole / circle / **escutcheon** | `cad_dxf_*.stp` under `test-stl/` |
| Format choice | DXF bootstrap | STEP = solid interchange; SVG available later for 2D UI |

### Not implemented ✗ (DXF / sketch spine)

| Capability | Notes |
|------------|--------|
| DXF **LWPOLYLINE** | ARC done; polyline still open |
| **Revolve** profile | Still stub |
| **Revolve** profile | Feature stub only |
| **Draft** (taper) | Not started |
| General pocket/cut from DXF tool solid | Restricted Difference only; plate-through-poly is explicit topology |
| Multi-hole nested loops in one ExtrudeProfile | Two-sketch plate+hole path exists |
| Sketch constraints / DOF solve | `CAD_Solve2D` theater |
| Sketch_0 plane recipes + Feat tree | Product model |
| DXF units / layers / blocks | Minimal path only |

```bash
./ailang.x CAD/demo_dxf_extrude.ailang -o /tmp/d && /tmp/d       # rect 40×30 → h=15
./ailang.x CAD/demo_dxf_diamond.ailang -o /tmp/d && /tmp/d      # diamond poly prism
./ailang.x CAD/demo_dxf_keyhole.ailang -o /tmp/d && /tmp/d      # solid keyhole pad
./ailang.x CAD/demo_dxf_circle.ailang -o /tmp/d && /tmp/d       # analytic cylinder
./ailang.x CAD/demo_dxf_escutcheon.ailang -o /tmp/d && /tmp/d   # plate + flared keyhole through
./ailang.x CAD/cad_load.ailang -o cad_load.x
./cad_load.x --in any.dxf --out out.stp --height 10
./cad_load.x --in plate.dxf --hole hole.dxf --out esc.stp -H 4
cat any.dxf | ./cad_load.x -H 10 > out.stp   # full pipe
```

---

## 4. Implemented vs not — fillet / digon tranche

Tracking for this grind arc only (edge blend + corners). Update ticks when status changes.

### Implemented ✓

| Capability | API / locus | Notes |
|------------|-------------|--------|
| Plane–plane constant-R edge fillet | `CAD_Blend.FilletEdge` → `FilletPlanePlaneEdge` | Cylinder strip + minor end arcs; rebuild planar faces |
| Multi-edge sequential (no shared verts) | `FilletPlaneEdges` | e.g. four verticals |
| Equal-R **digon** multi-edge cycle | `FilletPlaneEdges` → `FilletPlaneEdgesDigon` | Shared verts refused for sequential; digon path |
| Digon cylinders + **ellipse** corners | `DigonCyl*`, `MakeEqualRDigonEdge` | OCC-style: **no globe** when R equal |
| General dihedral equal-R corner points | `DigonEqualRSolve` / `DigonSolve3` | Any angle (31°, 15° plane, 90°, …) via 3 offset planes |
| Digon ellipse from actual points | `Cs`, `P_ww`, `P_cap` axes | Not horizontal false Steinmetz |
| Manifold wall/cap rebuild | `DigonMapVert` + edge registry | Shared verts/edges across faces |
| Minor-arc end circles on single fillet | `MakeMinorArcEdge` | Avoids folded-in FreeCAD arcs |
| Wedge / roof test solids | `MakeWedgePrism` | Non-ortho digon demos |
| STEP walk export of ELLIPSE + CYL | `CAD_IO` | Look-at FreeCAD |

### Not implemented ✗ (this tranche / next)

| Capability | Why it matters | Notes |
|------------|----------------|--------|
| **Unequal-R corner (sphere / rolling-ball “globe”)** | Only place globe is *correct* by default | Digon dies when radii differ |
| **Chamfer** (planar blend strip) | Same topology edit, flat face | Not started |
| **Plane–cylinder** edge blend | Fillet into hole walls | Needs offset/isect on cyl |
| **Plane–cone / cyl–cyl** blends | Draft, pipes | Later |
| **3-edge vertex full network** beyond top cycle digon | Freeform polyhedron corners | Digon cycle covers coplanar-cap loops |
| Variable-R / G2 blend | Styling | Far |
| General B-Rep shell edit after blend on non-plane supports | Robustness | Walls currently plane rebuild |
| Feature-level history (fillet as Feat node) | Parametric edit | Kernel ops only today |
| Chamfer + digon mix | Production modelling | — |

### Policy (locked)

1. **No shape recipes** (`MakeBoxTopRimFillets` etc. deleted). API is edge-based.
2. **Equal R on meeting edges → digon (ellipse), not sphere.**
3. **Sphere / globe corner only** when radii differ or explicit ball-corner is requested (future).
4. Unsupported support pair → **return 0**, never silent wrong geometry.

### Architecture (what we actually ship)

```
FilletEdge(solid, edge, R)
  → plane–plane supports only
  → cylinder blend + minor arcs + face rebuild

FilletEdges(solid, edges[], n, R)
  → if edges share vertices and n≥3 (or shared): FilletPlaneEdgesDigon
  → else sequential FilletPlanePlaneEdge

Digon (equal R):
  orient outward normals → EqualR corner (P_ww, P_cap, Cs)
  → ellipse digon edges → cylinder faces per cycle edge
  → new cap + rebuild other plane faces (shared vert map)
```

Historic design note “equal-R → sphere sector” is **superseded** for the equal-R multi-edge path: digon matches look-at (no glob) and OCC-style edge network.

---

## 5. Mission target — Fusion-shaped features (unchanged intent)

| Feature | Kernel meaning | Status |
|---------|----------------|--------|
| Pad / extrude join | Profile → solid ∪ body | **partial** (pad boss shell only) |
| Pocket / cut | Profile → tool → Difference | **restricted** rect/hole |
| Hole | Circle → cyl → Difference | **restricted** plate/side |
| Revolve | Profile about axis | **done** full 360° rect → cyl/annulus |
| Fillet | Edge blend | **plane–plane + equal-R digon ✓** |
| Chamfer | Planar strip | **box corner vertical ✓** |
| Loft | Two profiles → ruled solid | **done** `LoftProfiles` / `MakeRuledSolid` |
| Sweep | Profile + path | **done** `SweepProfile` / `MakePathSweepSolid` (Z-changing path) |
| Pattern / mirror | Clone + transform | **done** kind-0 any poly (not only AABB box) |

### Part Design deeper parity (2026-08-07)

| API | Domain |
|-----|--------|
| `CAD_Topo.CloneKind0` | First shell, plane faces + line edges; seed-safe after CompoundAdd |
| `CAD_Topo.MakeRuledSolid` | Two XY n-gons at z_bot/z_top, n 3..64 |
| `CAD_Topo.MakePathSweepSolid` | XY profile + path XYZ; Z must change between samples |
| `CAD_Feat.LoftProfiles` | Two sketches, same loop count, zpack |
| `CAD_Feat.SweepProfile` | Sketch + path array |
| `CAD_Feat.LinearPattern` | CloneKind0 + Translate, compound multi-shell |
| `CAD_Feat.CircularPattern` | Clone + rotate about AABB center |
| `CAD_Feat.Mirror` | Clone + ReflectSolid about AABB mid plane |

```bash
./CAD/smoke_part_design.sh
# fixtures: cad_loft.stp, cad_sweep.stp, cad_pattern_diamond*.stp, cad_pattern_linear.stp, …
```

**Priority reaffirm (2026-08-07):**

| Order | Work | Status |
|------:|------|--------|
| 1 | Analytic solids | ✓ |
| 2 | Transforms + restricted Bool | ✓ |
| 3 | Plane–plane fillet + equal-R digon | ✓ |
| 4 | **DXF → extrude** (LINE/CIRCLE/ARC/LWPOLY) | ✓ |
| 5 | Revolve, draft, pad/cut, Part Design pattern | ✓ |
| 6 | Loft / sweep / non-box pattern | ✓ |
| 7 | Chamfer general, plane–cyl, unequal-R globe, general cut | open |

DXF chosen as profile bootstrap (not STEP — STEP is solid interchange). SVG remains available for 2D image work outside the solid kernel.

---

## 6. Jump task board (condensed)

| ID | Task | Status |
|----|------|--------|
| J1.* | Analytic cyl/sphere/tess/STEP | **done** |
| J2.1–J2.14 | Bool/hole/pad/isect spine | **done** (restricted) |
| J2.15 | Shape-specific fillets | **deleted** (policy) |
| J2.16 | General plane–plane `FilletEdge` | **done** |
| J2.17 | Multi-edge verticals + horizontal | **done** |
| J2.18 | Equal-R digon cycle + non-ortho (31° / 15°) | **done** |
| J2.19 | Chamfer strip | **next** |
| J2.20 | Plane–cyl edge blend | **next** |
| J2.21 | Unequal-R ball corner (globe when needed) | **next** |
| J3.1 | DXF LINE import + closed loop | **done** |
| J3.2 | ExtrudeProfile → solid (rect + poly ≤8) | **done** |
| J3.3 | DXF CIRCLE/ARC/LWPOLYLINE | **next** |
| J3.4 | Revolve profile | **next** |
| J3.5 | Draft / pocket-from-DXF | **next** |
| J3.6 | Sketch_0 constraints + plane recipes | open |

---

## 7. Other look-at fixtures (earlier jumps)

Regenerate via individual demos or `CAD/demo_regen_all.ailang` where listed.

| File | Notes |
|------|--------|
| `cad_box_*`, `cad_cylinder_*`, `cad_sphere_*` | primitives |
| `cad_plate_hole_*`, `cad_counterbore.stp` | holes |
| `cad_plate_rect_*`, `cad_union_boxes.stp` | pocket / union |
| `cad_side_hole_*`, `cad_rect_notch_x.stp` | side cuts |
| `cad_intersect_boxes.stp`, `cad_pad_boss.stp` | bool / pad |

---

## 8. Turn log

| Date | What | Gates / look-at |
|------|------|-----------------|
| 2026-08-05 | Jumps 0–2: analytic solids, restricted bool, STEP walk | green |
| 2026-08-05 | Policy: general edge blend, kill shape recipes | — |
| 2026-08-05 | FilletEdge vertical + horizontal + multi-vertical | green |
| 2026-08-06 | Minor-arc fix (no folded fillets); digon equal-R top cycle | green FreeCAD |
| 2026-08-06 | digon_S sizing, manifold rebuild, ellipse from Cs/P_ww/P_cap | green |
| 2026-08-06 | General-angle EqualR (`DigonSolve3`); wedge 31° + roof 15° demos | green |
| 2026-08-06 | Docs: implemented vs not for blend tranche; sketch next | — |
| 2026-08-06 | Real DXF LINE parser; sketch loop; ExtrudeProfile; poly prism; demos | green |
| 2026-08-07 | Phase A/B/C + Part Design pattern/mirror/shell | smoke green |
| 2026-08-07 | CloneKind0; Loft/Sweep; pattern of diamond (non-box) | `smoke_part_design` green |

---

## 9. Process (every turn)

1. Update this file (status + turn log + implemented table)  
2. Smallest vertical slice with look-at or gate  
3. Run gates  
4. `git commit` CAD paths only (`Librarys/Cad/`, `CAD/`, `Docs/CAD/`, `test-stl/cad_*`)  

---

## 10. Related

| Doc | Role |
|-----|------|
| `CAD_Kernel_Design_v3.md` | Normative architecture |
| `CAD_DEV_GUIDE.md` | Day-to-day process + look-at commands |
| `plane_coordinate_tree_spec.md` | Plane feature tree |
| `CAD_PROGRESS.md` | **This file** |
