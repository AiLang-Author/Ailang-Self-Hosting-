# CAD kernel and app — deficiency register

**Date:** 2026-11-13 · **Tree:** `db345f75` (plus uncommitted work outside CAD)
**Scope:** `Librarys/Cad/**` (kernel, ~74k lines), `CAD/App/**` + `CAD/cad_app.ailang` (app, ~25k lines), `CAD/demo_*.ailang` + `CAD/test_*.ailang` (150 programs)
**Supersedes the status columns of:** `CAD_OCC_CAPABILITY_AUDIT.md` (2026-08-07), `CAD_BREP_BOOL_FILLET.md` §1 (2026-08-15). Both predate the 2026-08-30 solid-generation rewrite and are wrong in places (e.g. the audit lists 2D constraints as "not built"; they are built, see §5.4).

Every item below is tied to code or to a test run. Items marked **(untested)** are read from code and have no reproducer yet.

---

## 0. How this was produced

| Check | Method |
|---|---|
| Test status | Compiled and ran every `CAD/demo_*.ailang` and `CAD/test_*.ailang`, each in its own scratch dir (`test-stl/` + link to `test-dxf-files`), 60 s run timeout |
| Self-reported limits | Grep for `not implemented`, `TODO`, `stub`, `returns 0`, `refuse`, etc. across kernel and app |
| Fake success | Functions that take inputs, call nothing, and return OK |
| Unreachable code | Statements after an unconditional `ReturnValue` / `BreakLoop` at the same block level |
| Silent caps | `GreaterThan(guard, N) ThenBlock: { cursor = 0 }` loop guards over topology walks |
| Reachability | Every `Function.` in kernel/app counted for references in kernel, app, and demos/tests separately |

Re-run the test sweep before closing any item in §1–§2.

---

## 1. Test suite status

150 programs: **122 exit clean, 23 report FAIL, 4 do not compile, 1 segfaults.**

"Exit clean" means exit 0 and no `FAIL` line. 20 of the 122 print no `PASS`/`FAIL`/`OK` at all, so they only prove the program did not crash.

### 1.1 Do not compile (test rot)

`test_bool`, `test_feat`, `test_repo`, `test_sketch` — `[IMPORT ERROR] Cannot read: CAD_Sys`. They use `LibraryImport.CAD_Sys` / `LibraryImport.CAD_Num`; the libraries moved to `LibraryImport.Cad.*`. The boolean, feature, repo and sketch unit tests have not been running since the move.

### 1.2 Crash

| Program | Signal | Last output |
|---|---|---|
| `demo_arch_notch_tess` | SIGSEGV | `mesh nt=400 nv=606` (tessellation of a ruled arch notch) |

### 1.3 Reported FAIL

| Program | Failing check | Likely cause |
|---|---|---|
| `demo_extrude_cut` | `FAIL cut` | `CAD_Feat.ExtrudeCut` → `Difference` recipe path retired 2026-08-30 (§2.4) |
| `demo_rect_pocket` | `FAIL rect pocket cut` | same — `CreateRectPocket` |
| `demo_counterbore` | `FAIL c'bore cut` | same — `CreateHole` |
| `demo_revolve_cut` | `FAIL revolve cut` | same — `RevolveCut` needs box − kind-1 cylinder |
| `demo_rect_oct_hole` | `FAIL rect+oct hole` | `ExtrudeProfile` with mixed holes (the 08-30 commit message: "rectangle and mixed holes do not") |
| `demo_part_design` | `FAIL shell` | `CAD_Feat.Shell` |
| `demo_pad_boss` | `FAIL hole center not outside` | `CreateHole` / `ClassifyPoint` |
| `demo_bool_ops` | `FAIL Intersection` | `Intersection` always returns 0 (§3.1) |
| `demo_bool_glue` | `B4 GLUE FAIL` | `GlueOnFace` |
| `demo_glue_cyl` | `GLUE CYL FAIL` | `GlueOnFace` with cylinder tool |
| `demo_circle_analytic` | `ANALYTIC CYL FAIL` | analytic circle pad |
| `demo_dxf_circle` | `FAIL expected 1 circle` | DXF circle import |
| `demo_revolve_caps` | `REVOLVE CAPS FAIL` | lathe caps |
| `demo_fillet_1line_arc` | `FAIL fillet nose flat` | fillet on line–arc |
| `demo_fillet_cyl_join` | `FAIL class not 6` | fillet classifier |
| `demo_fillet_hole_id` | `FAIL class not 6` | fillet classifier |
| `demo_fillet_join_cove` | `FAIL class not 3` | fillet classifier |
| `demo_fillet_pacman_hole` | `FAIL fillet` | fillet on hole with notch |
| `demo_fillet_pacman_solid` | `FAIL fillet` | fillet on notched solid |
| `demo_fillet_prism_box` | `FILLET PRISM BOX FAIL` | |
| `demo_fillet_washer_bottom` | `FAIL bottom OD mode` (×2) | washer bottom rim |
| `test_blend` | `ComputeRollingBall`, `AddFillet`, `AddVariableFillet`, `AddChamfer` failed | legacy `CAD_Blend` API; app uses `CAD_Topo.Fillet*` instead |
| `test_offset` | `Surface offset mismatch` | `CAD_Offset.Surface`; likely the plane-frame layout mismatch documented in `CAD_BREP_BOOL_FILLET.md` §3 |

Several of these may be stale tests of deliberately retired paths rather than regressions. Each needs a decision: fix the code, or delete or rewrite the demo. A suite that is always partly red stops catching new breaks.

### 1.4 Tests that pass against fake code

`test_solve2d` (5/5 pass) and `test_featdag` (5/5 pass) test functions that do no work (§2.1). Their green results are meaningless.

---

## 2. Correctness defects (wrong result, or success reported without work)

These come first because they break the codebase's own rule: "no silent success".

### 2.1 Functions that return OK without doing their job

| Function | File:line | What it actually does |
|---|---|---|
| `CAD_Solve2D.AssembleJacobian` | `Library.CAD_Solve2D.ailang:86` | Stores `n*m` in a counter. Writes no matrix. Header claims "Full Constraint Jacobian Matrix & LU Decomposition Solver". |
| `CAD_Solve2D.SolveNewtonRaphson` | `Library.CAD_Solve2D.ailang:107` | Increments `solves_run` and `converged_solves`, returns 0 "Converged". No iteration. Called by `CAD/cadk.ailang:77`. |
| `CAD_Bool.StitchShells` | `Library.CAD_Bool.ailang:362` | Allocates an empty solid handle and returns OK. Faces are ignored. |
| `CAD_Offset.ShellSolid` | `Library.CAD_Offset.ailang:60` | Allocates an empty solid and returns OK. Comment says "Generate inner offset shell and perform Boolean Difference". |
| `CAD_FeatDAG.AddDependency` | `Library.CAD_FeatDAG.ailang:38` | Increments a counter. No edge is stored. |
| `CAD_FeatDAG.InvalidateNode` | `Library.CAD_FeatDAG.ailang:59` | Increments a counter. No node is marked. |
| `CAD_FeatDAG.RebuildDirty` | `Library.CAD_FeatDAG.ailang:73` | Zeroes the counter. Nothing is rebuilt. |
| `CAD_BSPTree.AttachSketchToPlane` | `Library.CAD_BSPTree.ailang:66` | Null-checks and returns OK. Binds nothing. |

All eight share one style (`// CAD_OK`, "Layer N … §11 Phase N" headers), from the `CAD_Kernel_Design_v3.md` phase scaffold. **Fix:** make each return `-17` (not implemented) like `ImportSTEP` and `ResolveNaming` do, then implement or delete. `LUDecompose`/`LUSolve` (2×2) are real.

### 2.2 STEP export writes compounds as one manifold solid

`CAD_IO` collects "verts/edges/faces from all shells (compound solids)" (`Library.CAD_IO.ailang:130`) and writes them into a single `CLOSED_SHELL #120` inside a single `MANIFOLD_SOLID_BREP #110` (lines 229, 801). Join is often `CompoundAdd` (§3.1), so a two-body part exports as one "closed shell" whose faces overlap or touch. Receiving CAD may reject it or report a bad solid. **(untested against an importer)**

Fix: one `MANIFOLD_SOLID_BREP` per shell (or `BREP_WITH_VOIDS` for inner shells), grouped under a `SHAPE_REPRESENTATION`.

Smaller STEP issues: fixed `FILE_NAME('ailang_solid.stp','2026-08-05T00:00:00',…)` header (line 215); no colours/styles; no assemblies; no B-spline or conical entities (none exist in the kernel).

### 2.3 Topology walks cap silently

Loop guards over the B-rep stop walking when a counter passes a fixed N, then carry on with partial data. No error is raised. 182 such guards; the caps differ by function, so two operations on the same solid can see different face sets.

| Structure | Caps found |
|---|---|
| shells per solid | 8 (`FilletIRInward`), 64 (39 sites) |
| faces per shell | 16 (`PunchObCyl`), 40, 48, 64 (11 sites incl. `PunchPrism` tool walk, `FilletPlaneEdgesDigon`), 80 (`ClipWalls`, `DropHost`, `OpenLoops`, `Steal`), 256, 512, 4096 |
| loops per face | 8 (`FindCoedgeOnFace`, `FaceRetargetVert`, `ChamferRingRetarget`), 16 (`TranslateSolid`), 64 |
| coedges per loop | 40 (`BoolClip.CutLoop`), 64, 256 |

Example: `TranslateSolid` (`Topo/Library.Xform.ailang:147`) walks ≤64 shells, ≤256 faces per shell and ≤16 loops per face, so a face with 16+ holes would be partly left behind on a move. **(untested)**

Fix: one shared limit constant, and on overflow raise `CAD_Err` and return failure instead of truncating.

### 2.4 Retired `Difference` recipes still exposed through the API

On 2026-08-30 (`638a9b58`) the recipe paths in `CAD_Bool.Difference` were deliberately turned off with an early `ReturnValue(0)`: "Kind recipes (plate+cyl, box AABB pocket, coaxial tube, notch) are gone. A hole is an inner loop on the swept solid." (`Library.CAD_Bool.ailang:489`; `PunchPrism` was added in front later).

The decision is sound, but the cleanup was not finished:
- 251 unreachable lines remain after the return.
- `CAD_Feat.CreateRectPocket`, `CreateHole`, `DrillHole`, `RevolveCut`, `ExtrudeCut` (non-face tools), `CreateSideHoleX/Y`, `CreateRectNotchX` still exist and can no longer succeed. Their demos fail (§1.3).

Fix: delete the dead block. Either re-implement each feature on top of `PunchPrism`/profile holes, or make it return `-17`, and update the demos to match.

### 2.5 Edge references by midpoint

Fillet/chamfer edges are persisted as edge midpoints in micrometres (`cad_cmd_edge`, `Library.CAD_Repo.ailang:8`) and rebound on replay. `CAD_Feat.ResolveNaming` returns `-17` (`Library.CAD_Feat.ailang:1375`). Any upstream edit that moves the edge's midpoint (pad height, sketch dimension) makes a fillet bind to a different edge or none. **(untested)** This is the topological-naming problem; every parametric CAD system has to solve it.

### 2.6 Other correctness risks (untested)

- `CAD_Bool.ClassifyPoint` for kind-0 casts one +Z ray and counts hits on **planar** faces only (`Library.CAD_Bool.ailang:119`). Curved faces on kind-0 solids (analytic circle pads) are not counted, and rays through edges/vertices are not perturbed.
- `CAD_Bool.ClassifyFace` uses the face centroid, which can lie outside a non-convex face.

---

## 3. Kernel capability gaps

### 3.1 Booleans

| Operation | Today | Missing |
|---|---|---|
| Union | `GlueOnFace`: tool face coplanar with a host planar face → one shell. Otherwise `CompoundAdd` (two shells, no merge). | Fuse of intersecting/overlapping solids; fuse onto non-planar faces; any orientation other than face-on-face |
| Difference | `PunchPrism`: profile prism swept from a planar host face, cut by the BoolClip engine (arcs, holes, seams, walls; ~5k lines). `BoolObliq`: single-cylinder tool whose caps miss the host. | Arbitrary tool solids; tools that are not one prism/cylinder; sphere/torus/revolved tools; tools entering through curved faces |
| Intersection | Always returns 0 (`Library.CAD_Bool.ailang:781`) | All of it |
| General surface–surface intersection | `CAD_Isect` has line/plane/cylinder/sphere/circle pairs, used only by tests | Plane–torus, cyl–cyl, cyl–sphere, anything–NURBS; a boolean driven by these curves |

### 3.2 Fillet and chamfer

The fillet system (`Topo/Fillet*` + `Topo/Digon*`, ~20k lines) is the most developed part. It does multi-edge chains, digon corners, coves, and plane–cylinder rims. Its own refusal codes (`Library.CAD_Err.ailang`) mark the boundary:

| Code | Message | Gap it marks |
|---|---|---|
| 1 | pick the whole join loop | partial loops |
| 2 | join must be Z-up | join fillets in any other orientation |
| 3 | vertex needs a wall upright | non-vertical walls at a vertex |
| 4 | glue the pad first | fillet across a compound (no fused edge) |
| 5 | cannot fillet those verticals yet | some vertical-edge sets |
| 6 | R must be smaller than the 2D corner radius | |
| 11 | canal traces miss at the vertex | vertex blends where three fillets meet with non-constant setback |
| 12 | sharp arc-line corner | non-G1 line/arc chains in one pass |
| 22 | edges are not one chain | disjoint selections in one operation |
| 28 / 29 | hole fillet meets cap edge / crosses a hole | fillets interacting with other features |

Also: no variable-radius fillet (`AddVariableFillet` returns 0, `Library.CAD_Blend.ailang:296`); rolling-ball construction is plane–plane (`ComputeRollingBall`, line 28); cylinder blends are per-case builders (top/bottom rim, washer hole, boss join); no plane–sphere/torus/cone blends; chamfer is equal-setback only (no distance–distance or distance–angle).

### 3.3 Geometry

| Have | Missing |
|---|---|
| Line, circle, ellipse curves; plane, cylinder, sphere, torus surfaces; B-spline evaluation (de Boor) | Cone surface (no kind at all); B-spline/NURBS curves or surfaces as B-rep geometry (sketch splines are sampled to polylines, `CAD_UI.SampleSplineXY`); offset surfaces other than a plane (`CAD_Offset.Surface` is plane-only and its test fails) |

### 3.4 Features (kernel)

| Feature | Domain today |
|---|---|
| Extrude / pad | Profiles incl. arcs, islands; symmetric (`ExtrudeSymmetric`, test-only) |
| Revolve | Full 360° only, axis +Z of the sketch frame (`RevolveProfile`, `Library.CAD_Feat.ailang:630`) |
| Revolve cut | Fails (§2.4) |
| Draft | Rectangular sketch only (`ExtrudeDraft`) |
| Shell | Open-top box only (`CAD_Feat.Shell`, line 968); `demo_part_design` shell check fails; `CAD_Offset.ShellSolid` is fake |
| Loft | Two sections, equal vertex count, ruled |
| Sweep | Polyline path, 2–32 points, Z must change every step (`SweepProfile`, line 1070) |
| Pattern / mirror | `CloneKind0` + transform → extra shells (compound, not fused) |
| Transforms | `TranslateSolid`, `RotateSolidZ` (Z axis only), `ReflectSolid`, `MapSolidByFrame` |
| Missing entirely | Thicken, split body/face, offset face / press-pull, replace face, rib/web, thread, emboss, coil, hole wizard, scale |

### 3.5 Sketch

Entities: line, rectangle (2/3-point, centre), circle (centre, 2/3-point, diameter), arc (2/3-point), n-gon, slot, point, spline (sampled), plus trim, sketch fillet/chamfer. No ellipse tool, no construction-geometry toggle found, no offset/project/intersect-curve tools.

Constraints (`CAD_Sketch.SolveDatum`, `Library.CAD_SketchCstr.ailang:557`), types 1–16: at origin, x=v, y=v, on X axis, on Y axis, distance from origin, horizontal, vertical, coincident, point on line, radius, equal radius, tangent line–circle, tangent circle–circle (external), point distance, point on circle.

| Missing constraints | Missing solver behaviour |
|---|---|
| parallel, perpendicular, collinear, concentric, midpoint, symmetric, equal length, angle, point-to-line distance, internal tangency, fix-in-place, G2 smooth | Simultaneous solve (the solver is multi-pass direct projection that moves one entity per constraint, so coupled systems can depend on order or fail to converge); DOF count / fully-constrained colouring; over-/conflicting-constraint detection; 128 constraints per sketch |

### 3.6 Data exchange

| Format | Status |
|---|---|
| STEP export | Real (AP214); issues in §2.2 |
| STEP import | Stub, returns `-17` (`Library.CAD_IO.ailang:1038`) |
| DXF | Import (2D, z≈0, LINE/CIRCLE/ARC/LWPOLYLINE) and export (LINE/CIRCLE/ARC); `demo_dxf_circle` fails |
| STL | Export (`CAD_Tess.ExportSTL`) |
| IGES, OBJ, 3MF, Parasolid x_t | None |
| Native file | None — documents persist only through PostgreSQL (`CAD_Repo`). No server, no save. |

### 3.7 History and regeneration

The app has a real timeline (`CAD/App/DocHist.ailang`): undo/redo, edit a past feature, replay. Gaps:
- No dependency graph; replay is the full command list (`CAD_FeatDAG` is fake, §2.1).
- No stable entity naming (§2.5).
- History holds 128 steps; older steps are dropped.

---

## 4. App reachability — kernel work the user cannot reach

Kernel calls made by the app: `ExtrudeOnPlane`, `ExtrudeProfile`, `ExtrudeContours`, `Difference` (→ `PunchPrism`), `GlueOnFace`, `CompoundAdd`, `MakeLatheRevolution`, `FilletCompile`/`FilletPlaneEdges`/`FilletEdges`, `ChamferEmitChain`, `ExportSTEP`, `CAD_DXF.ImportFile`/`ExportSketch`, transforms.

Kernel features with **no app path** (called only from demos/tests):

| Area | Functions |
|---|---|
| Features | `LinearPattern`, `CircularPattern`, `Mirror`, `Shell`, `ExtrudeDraft`, `ExtrudeSymmetric`, `LoftProfiles`, `SweepProfile`, `RevolveCut`, `CreateHole`, `DrillHole`, `CreatePocket`, `CreatePad` |
| Booleans | `Union`, `Intersection`, `ClassifyFace` |
| Intersection | all of `CAD_Isect` |
| Other | `CAD_Offset`, `CAD_FeatDAG`, `CAD_Script`, STL export, `CAD_Repo` revision listing |

`CAD_MODELLING_HITLIST.md` keeps these off the ribbon on purpose until face picking is solid. They are recorded here because a feature the user cannot reach should not count as shipped.

---

## 5. Product gaps against Fusion 360

Absent entirely: assemblies and joints (a document "kind" label exists, nothing else); drawings; CAM; sheet metal; surface modelling; user parameters and expressions; measure, mass properties, section analysis; appearance/materials; multi-body management (bodies are shells in a compound).

---

## 6. Capacity limits (guarded — adds past the limit are refused)

| Item | Limit | Where |
|---|---|---|
| Sketches / registered planes per document | 16 | `CAD/App/StatePools.ailang:99`, `PlaneReg.ailang:43` |
| Lines per sketch | 4096 | `Library.CAD_Sketch.ailang` |
| Circles per sketch | ~85 (2048 bytes) | same |
| Arcs per sketch | 512 | same |
| Constraints per sketch | 128 | same |
| User points per sketch | 512 | same |
| Closed profiles per sketch | 64 | same |
| Edges per fillet feature | 12 | `StatePools.ailang:164` |
| History steps | 128 (oldest dropped) | `DocHist.ailang` |
| Sweep path points | 32 | `CAD_Feat.SweepProfile` |

16 sketches per document is low for real parts.

---

## 7. Code hygiene

| Item | Count | Detail |
|---|---|---|
| Unreachable code | 4 sites, ~830 lines | `CAD_Bool.Difference` (251), `CAD_Sketch.TrimAt` after `TrimCircleAt` (273, `Library.CAD_SketchTrim.ailang:433`), `CAD_Topo.MakeLatheClosed` (245, `Topo/Library.MakeLathe.ailang:20`), `CAD_View.ShadeColor` (65, `Library.CAD_View.ailang:1064`) |
| Functions never called | 126 of 1569 | e.g. all of `CAD_OrbitCube` input handlers, `Digon.Solve3Planes`, `FilletPlexJunc5*`, `ClassifyFilletEdge`, `TessZip.*`, `CAD_SketchGeom.AddBSpline`, `CA_WeldSketch`, `FCoveMakeCollarFace` (returns 1, no body) |
| Functions only reached by tests | 113 | see §4 |
| Backup files in tree | 17 | `*.pre_split`, `*.pre_poll`, `*.bu` under `CAD/` and `Librarys/Cad/` |
| Misleading headers | — | `CAD_Solve2D`, `CAD_Offset`, `CAD_FeatDAG`, `CAD_BSPTree` headers describe engines that are not there |
| Stale docs | — | `CAD_OCC_CAPABILITY_AUDIT.md`, `CAD_BREP_BOOL_FILLET.md` §1, `CAD_MODELLING_HITLIST.md` §6 ("this week" = 2026-08-14) |

---

## 8. Suggested order

1. **Honesty pass (small).** §2.1 fakes → `-17`; delete dead code (§7); fix the 4 rotted test imports; decide fix-or-delete for each failing demo (§1.3). Goal: a suite that is all green and means it.
2. **STEP multi-solid export (§2.2).** Small, and it affects every exported part with a join.
3. **Cap policy (§2.3).** One constant, error on overflow.
4. **Simultaneous sketch solver + missing constraints (§3.5).** Highest user-visible gap; replaces the fake `Solve2D`.
5. **Real union (§3.1).** Fuse coplanar-contact and overlapping kind-0 solids into one shell. This unblocks fillet code 4, patterns that fuse, and valid STEP.
6. **Stable naming (§2.5).** Before anything else makes history editing more common.
7. Then the general boolean on analytic surfaces, general plane–cyl/cyl–cyl blends, STEP import, NURBS.
