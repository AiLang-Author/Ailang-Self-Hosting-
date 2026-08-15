# Real B-Rep bool + junction fillet

**Status:** living grind list — start here, one chunk at a time  
**Date:** 2026-08-15  
**Parent:** `CAD_PROGRESS.md` · `CAD_MODELLING_HITLIST.md` D2.2 / D2.5  
**Rule:** Gtk is chrome. Kernel owns geometry. `SolidBounds` is an extent query, never a solid. No AABB pocket as the product path.

---

## 0. Why this exists

Extrude JOIN today is `CompoundAdd`: concatenate shell lists. Two bodies that *look* joined (circle boss on a box) are still **two shells**. There is no junction edge, so fillet has nothing real to blend.

Extrude CUT today is `CAD_Bool.Difference`: a handful of **recipes** (box−cyl hole, box−box top pocket, side notch). Anything else returns 0. The HUD can ask for CUT; the kernel often cannot do it.

The scene that must work:

```text
Sketch_0 rectangle → Extrude JOIN
  → On Face (top) → circle or smaller rect → Extrude JOIN
  → pick the join loop → Modify Fillet R
```

That is one manifold solid with a **real** edge (or edge chain) at the footprint, then a **real** blend on those two incident faces.

---

## 1. Current truth (do not paper over)

| What you do | What the kernel actually does |
|-------------|-------------------------------|
| On-face Extrude JOIN | `ExtrudeOnPlane` + `CompoundAdd` — **no imprint, no fuse** |
| On-face Extrude CUT | Tool along −N, then `Difference`. Succeeds only if a recipe matches |
| `CAD_Bool.Union` | Kind-0 → `CompoundAdd` again |
| `CAD_Bool.ClassifyFace` | **Stub — always INSIDE** |
| `CAD_Bool.StitchShells` | Allocates a solid handle, does not stitch |
| Fillet picked edge | Plane–plane (`FilletPlanePlaneEdge` / Digon) **or** standalone cyl rim recipes |
| Fillet “cyl on box” | Miss / wrong body — **no join edge exists** |
| Chamfer | Same family as fillet (edge set + prism-cap recipes) |

What is already real and reusable:

- Kind-0 solids are **planar-face B-Reps** (`MakePolyPrism` writes kind 0).
- `ClassifyPoint` kind-0: +Z ray vs planar faces, even-odd (not box bounds).
- `FaceGetPlane`, `FaceCentroid`, `PointInFaceUV`, `EdgeIncidentFaces`.
- `CAD_Isect.PlanePlane` — line of two planes (watch **frame layout**, §3).
- `FilletPlanePlaneEdge` + Digon corners — works **once the edge is real**.
- `SolidCollectEdges` walks **all shells** (pick can see both bodies).

---

## 2. Locked policy

1. **Recipes stay as optional fast paths**, never as the only path. A hex pad minus a circle must not become a featureless box.
2. **Join means fuse.** After JOIN, `shell.next` of the host must be 0 (one outer shell) unless the user asked **NEW**.
3. **Cut means regularized difference** on the live B-Rep, not “translate a box and hope AABB matches.”
4. **Fillet consumes topology.** If collect/pick cannot name the join, fillet is not a product feature yet.
5. **Tessellated circle walls are planes.** A sketched circle pad is an n-gon prism. First fillet is **plane–plane per wall segment + Digon at verts**. Analytic plane–cyl (torus) is a later chunk.
6. Pin all bool/imprint state in **FixedPools**. Address locals die across nested `CAD_*` calls.
7. Each chunk ships a **headless demo** that prints PASS/FAIL. App chrome last.

---

## 3. Footguns

- **`FaceGetPlane` vs `PlanePlane` frames differ.** Face plane: O at `[1..3]`, X `[4..6]`, Y `[7..9]`, N `[10..12]`. `CAD_Isect.PlanePlane` wants N at `[9..11]` and O at `[0..2]`. Convert explicitly; do not pass a face plane blob through.
- **Coplanar overlap is the join case.** Boss bottom sits on host top (or antiparallel N, same plane). General split-by-intersection-line does not apply until faces are **not** coplanar.
- **CompoundAdd is not a bool.** Tests that only check “something shaded” will lie.
- Circle Extrude is **not** kind-1 cylinder unless a primitive path made it. Interactive circle → `MakePolyPrism`.

---

## 4. Dependency order

Do not start a chunk until its `Needs` are green. Test is the gate, not a screenshot.

```text
B0 fixtures
  └─ B1 ClassifyFace (real)
       └─ B2 Face rings in UV
            ├─ B3 Coplanar imprint (2D polygon ∩)
            │     └─ B4 GlueOnFace (one shell + join loop)
            │           ├─ B6 App JOIN uses glue
            │           └─ B8 Junction fillet (plane–plane + Digon)
            │                 └─ B9 Pick the join as one set
            └─ B5 Non-coplanar split + Difference
                  └─ B7 App CUT uses B5
B10 Analytic plane–cyl fillet (after B8 is boring)
B11 Revolve CUT / more bool (after B7)
```

### B0 — Prove the lie (fixtures)

**Needs:** nothing  
**Build:** headless `CAD/demo_bool_compound.ailang`  
**Does:** box prism + circle/rect prism `CompoundAdd`. Print `n_shells`, `n_edges`, `ClassifyPoint` of a point on the would-be join. Try `FilletEdge` on the boss bottom ring.  
**Done when:** log shows **2 shells**, fillet **0**, and the comment in this file still matches.  
**Status:** green — `CAD/demo_bool_compound.ailang` prints `shells=2`

### B1 — `ClassifyFace` is not a stub

**Needs:** B0 (so we have two solids to classify against)  
**Build:** `CAD_Bool.ClassifyFace` = `FaceCentroid` + `ClassifyPoint`. Keep ON_BOUNDARY if centroid is on.  
**Test:** centroid of box top vs box → ON; vs a disjoint cube → OUT; vs an overlapping boss → IN or ON.  
**Done when:** stub `ReturnValue(1)` is gone; `CAD/demo_bool_classify.ailang` PASS.  
**Status:** green — `ClassifyFace` = centroid + `ClassifyPoint`

### B2 — Face → UV ring

**Needs:** B1 optional (B2 can start in parallel with B1)  
**Build:** `CAD_Topo.FaceOuterXY(face, out_uv, out_n)` using the **face** X/Y (same as `PointInFaceUV`). Optional inner loops later.  
**Test:** top of a 40×30×10 pad is 4 UV verts; area matches.  
**Done when:** one function, no world-XY assumption.  
**Status:** green — `CAD_Topo.FaceOuterXY`

### B3 — Coplanar footprint ∩

**Needs:** B2  
**Build:** given host face + tool face (or tool bottom loop), detect same plane (N parallel, same D, abs tol). Run **even-odd polygon intersection in UV** (we already have `PointInPoly` / earclip helpers).  
**Test:** 20×20 host top, 8-gon (circle tess) centered → one inner loop, n≈8. Miss if planes differ.  
**Done when:** intersection is a closed UV ring, not an AABB.  
**Status:** skipped for JOIN — tool bottom loop *is* the footprint (`GlueOnFace`). Keep for clip-if-overhang later.

### B4 — `GlueOnFace` (the join)

**Needs:** B3  
**Build:** `CAD_Bool.GlueOnFace(host, tool, host_face)`:

1. Imprint tool footprint as an **inner loop** on `host_face` (real hole in that face).
2. Drop the tool face that sat on the host (interior after glue).
3. Twin-stitch tool wall edges to the new inner loop.
4. Relink tool’s remaining faces into the **host shell**. Do not `CompoundAdd`.

**Test:** `CAD/demo_bool_glue.ailang` — box + n-gon boss. `n_shells==1`. Tess watertight. STEP has one CLOSED_SHELL. A point that was in both solids is still INSIDE once.  
**Done when:** `SolidCollectEdges` lists the imprint loop; those edges have **two** incident faces (host remnant + a wall).  
**Status:** green for sitting-boss JOIN — `CAD/demo_bool_glue.ailang` `shells1=1 nt=26`. App JOIN tries glue before CompoundAdd. Tess watertight check still 0 (weld/index); topology is one shell.

### B5 — Planar Difference (non-coplanar)

**Needs:** B1, B2  
**Build:** for each host face vs each tool face, if planes **meet in a line**, clip that line to both UV polygons, split faces, classify pieces, keep A\B (host outside tool + tool-inside reversed).  
**Test 1:** rect pocket from the **top** of a rect pad — must match today’s recipe visually but keep the **outer ring** (notched/hex pad must stay hex).  
**Test 2:** circle (n-gon) pocket, same.  
**Done when:** `Difference` no longer returns 0 on two kind-0 prisms whose AABBs overlap; hex−circle does not become a box.  
**Status:** not started  
**Note:** side-face cut is the same code if the tool is already mapped onto that plane. Do not special-case +Z.

### B6 — App JOIN = glue

**Needs:** B4  
**Build:** `CA_BuildSolid` JOIN on-face: `GlueOnFace` instead of `CompoundAdd`. If glue fails, **log loud** and do not silently compound (or compound only behind a debug flag).  
**Test:** interactive On Face circle Extrude JOIN — tree Extrude, one body, pickable join.  
**Status:** in — `CA_BuildSolid` JOIN calls `GlueOnFace` first

### B7 — App CUT = B5

**Needs:** B5  
**Build:** `CA_BuildSolid` CUT: `Difference(host, tool)` after `ExtrudeOnPlane(−H)`. Keep recipes as a **fallback** only if B5 returns 0 *and* the pair matches a documented recipe; log which path ran.  
**Test:** On Face rect, Extrude Tab CUT. Hex host must remain hex.  
**Status:** not started

### B8 — Fillet the join

**Needs:** B4 (real edges)  
**Build:** do **not** write a new “boss fillet recipe.” Call `FilletEdges` / Digon on the imprint loop. Tessellated circle = N plane–plane edges + Digon at the N verts.  
**Test:** `CAD/demo_fillet_glue.ailang` — box + hex boss, fillet all join edges, R small vs min edge. STEP + BMP.  
**Done when:** the join is rounded; mesh still watertight.  
**Status:** not started

### B9 — Pick UX

**Needs:** B8  
**Build:** clicking one join segment may expand to the **full imprint cycle** (we already expand multi-sel in places). HUD R= unchanged.  
**Test:** one click on the join, Enter, whole loop fillets.  
**Status:** not started

### B10 — Analytic plane–cyl (later)

**Needs:** B8 boring on n-gon bosses  
**Build:** rolling-ball / torus face between a planar host and a kind-1 cylinder wall. Today `FilletCylTopRim` rebuilds a **standalone** cylinder, not a boss.  
**Status:** parked

### B11 — Revolve CUT / union more cases

**Needs:** B7  
**Build:** revolve-as-cut is the same Difference after a lathe tool exists.  
**Status:** parked

---

## 5. Suggested first week

| Day | Chunk | Gate |
|-----|-------|------|
| 1 | B0 demo | 2 shells, fillet 0, printed |
| 1–2 | B1 + B2 | classify + UV ring demos PASS |
| 3–4 | B3 | footprint ring for rect and n-gon |
| 4–6 | B4 | one shell, watertight |
| then | B6 then B8 | dogfood in Gtk: join then fillet |
| after | B5 / B7 | CUT is real |

Do **not** start B10/B11 or general OCCT-style bool while B4 is red.

---

## 6. Out of scope until B4+B8 are green

- OCC / FreeCAD `.so` as the engine
- AABB `MakeBoxRectPocketSolid` as the product CUT
- “Fillet all edges” recipes that rebuild the whole primitive
- Variable-R, hold-line, setback chamfer 3-edge vertex
- Boolean on NURBS / kind-6 SoR

---

## 7. Grind log

| Date | Chunk | Result |
|------|-------|--------|
| 2026-08-15 | — | Doc opened. JOIN=CompoundAdd, CUT=recipes, ClassifyFace stub. |
| 2026-08-15 | B0 | `demo_bool_compound` PASS `shells=2` |
| 2026-08-15 | B1 | `ClassifyFace` real |
| 2026-08-15 | B2 | `FaceOuterXY` |
| 2026-08-15 | B4/B6 | `GlueOnFace` + app JOIN. Plate/hole recipes kept until B5 (CUT). |

Update this table when a chunk’s demo is green (or when a chunk is blocked — say why).
