# CAD Sketcher — Implementation Document

**Status:** living — sketch→profile→pad/hole **dogfoodable**; revolve UI + sketch-on-face next  
**Date:** 2026-08-09 (rev: pow-wow priority lock — defer pattern/dim UI)  
**Owner path:** interactive `cad_app` + `CAD_Sketch` + multipass `SolveConstraints`  
**Related:**

| Doc | Role |
|-----|------|
| `CAD_PHASE_A_SKETCH.md` | Store layout, Phase A exit, layer contracts |
| `CAD_PHASE_B_SOLID.md` | Pad / cut / revolve from profiles |
| `CAD_PLANE_ON_FACE.md` | Sketch-on-face attachment strategy |
| `CAD_DESIGN_EVOLUTION.md` | Theory → current design (what changed) |
| `plane_coordinate_tree_spec.md` | PlaneFeature transform tree |
| `CAD_PROGRESS.md` | Living grind status |
| `CAD_APP_PLAN.md` | Hosted app UX (temporary panel) |

**Goal:** A full sketching system that does not suck — freehand + trim + profiles + pad; **origin-rooted constraints**; construction tools (fillet/arc/shapes/patterns/splines) that emit clean entities + constraints so rebuilds stay parametric.

---

## 0. Philosophy (locked)

| Principle | Meaning |
|-----------|---------|
| **Live geometry stays clean** | Circles/arcs/splines are real entities, not permanent polylines. Tessellation is for projection/pad only. |
| **Projection is a lower step** | Face walk / split / prune run on a **clone**. |
| **Datum from sketch zero** | Absolute constraints hang off immutable `O`, `+X`, `+Y`. Relational secondary. |
| **Tools construct + constrain** | Fillet/pattern/N-gon **emit** geometry + constraints; solver **holds**. |
| **Patterns are recipes** | count/spacing/center are params; rebuild instances on edit (not only anonymous baked copies). |
| **Shapes are macros** | N-gon = N lines (+ optional equal constraints), not a new solid type. |
| **Loud failure over silent wrong** | Refuse inventing joins, faces, or topology. |

### Hybrid constraints

```text
PRIMARY   Absolute: FixOrigin/X/Y, H/V, DistToOrigin, OnAxis
SECONDARY Relational: Coincident, PointOnLine/Circle, Tangent, EqualR, DistPoints, …
OPTIONAL  Construction geom (never pads)
```

### Rebuild chain (sketch-on-face)

```text
Sketch_0 O/+X/+Y → feature params → solid → face frame (PlaneFeature) → child UV → constraints → pad
```

---

## 1. Known working (honest inventory — 2026-08-09)

### 1.1 Geometry IR (`CAD_Sketch`, tag 10, stride **28**)

| Feature | Status | Notes |
|---------|--------|-------|
| Lines | **done** | Cap 4096 |
| Circles | **done** | Cap 64; live entities |
| Arcs | **done** | Cap 128; `cx,cy,r,a0,a1` |
| User **Points** | **done** | Cap 512; **not** wiped by RebuildAnchors |
| Anchors | **done** | Derived ends/crosses (display) |
| Rect helper | **done** | Four lines |
| Polyline / bulge | **done** | DXF + API |
| Multi-profile pool | **done** | 64 faces |
| `plane_id` | **done** | Slot 19; 0 = world Sketch_0 |
| Constraint buffer | **done** | Slots 20–22; 128 × 8 words |

### 1.2 Projection (clone only)

Live → copy → Tess arcs/circles (forced isect verts) → Split → Snap → Prune → `BuildAllClosedLoops` → profile pool for overlay/Pad.  
**Never** permanent live tess for trim/pad.

### 1.3 Trim

Line split at hits; circle → arcs; no live tess explode. **No undo.**

### 1.4 Interactive `cad_app` + panel

| Tool | Status |
|------|--------|
| Line / Rect / Circ / Arc / Point / Trim / Pick | **done** |
| Profiles / Next / Pad / zoom-pan | **done** |
| Datum draw + snap O/axes | **done** |
| Status `u=`/`v=` | **done** |
| Constraints: Coin H V FixO DistO Rad Tang OnLn EqR Dist | **done** (pick + auto-solve) |
| Solve button | **done** |
| Active constraint highlight (single button) | **done** |
| Sketch **fillet** (2 lines + R) | **done** | `FilletLines` + panel; default R=5 (user R later) |
| **3-point arc** | **done** | `Arc3Pend`+`Arc3Point` + panel **Arc3** |
| Multi-select pad holes | **done** | mask bits; `MakePolyPrismHoles` |
| N-gon / patterns / spline / dim HUD | **deferred** | temp UI — not long-term panel |

### 1.5 Constraint types (multipass projection solver)

| Code | Type | Status |
|-----:|------|--------|
| 1–8 | FixOrigin/X/Y, OnAxis, DistToO, H, V | **done** |
| 9 | Coincident | **done** |
| 10 | PointOnLine | **done** |
| 11 | Radius | **done** |
| 12 | EqualRadius | **done** |
| 13 | Tangent line–circle | **done** |
| 14 | Tangent circle–circle | **done** |
| 15 | DistPoints | **done** |
| 16 | PointOnCircle | **done** |

**API:** `AddConstraint` / `AddConstraint2` + `SetConstraintValue` / `SolveConstraints` / `SnapToDatum` / `AddUserPoint`  
**Not yet:** full Jacobian `CAD_Solve2D` (still theater); drag-while-constrained; constraint glyphs on geometry.

### 1.6 Solid / DXF

Pad prism ≤2048, circle→cyl, plate+hole, cut; DXF LINE/CIRCLE/ARC/LWPOLY. Revolve kernel done, app UI open.

### 1.7 Caps

| Cap | Value |
|-----|------:|
| Lines | 4096 |
| Circles / arcs | 64 / 128 |
| User points | 512 |
| Constraints | 128 |
| Profiles / verts | 64 / 2048 |

### 1.8 Regression gates

```bash
./ailang.x CAD/demo_sketch_datum.ailang -o /tmp/d && /tmp/d
./ailang.x CAD/demo_sketch_constraints.ailang -o /tmp/d && /tmp/d
./ailang.x CAD/demo_trim_circle.ailang -o /tmp/d && /tmp/d
./ailang.x CAD/demo_peanut_pad.ailang -o /tmp/d && /tmp/d
./ailang.x CAD/demo_no_phantom_snap.ailang -o /tmp/d && /tmp/d
# + demo_sketch_fillet when landed
```

---

## 2. Architecture

```text
cad_app (tools, hit-test, panel IPC)
    → CAD_Sketch (entities, Points, constraints, construction ops)
        → SolveConstraints (multipass projection; later real Solve2D)
        → clone BuildAllClosedLoops → CAD_Feat Extrude/Cut/Revolve → Topo
```

**Store slots (stride 28):** see `CAD_PHASE_A_SKETCH.md` §A.2 (includes plane_id, constraints, user Points).

---

## 3. Coordinate system — **CS-0 done**

Immutable Sketch_0 `O`/`+X`/`+Y`; draw; snap priority; `plane_id`; cursor UV; direct absolute solver.  
Sketch-on-face still **spec** (`CAD_PLANE_ON_FACE.md`) — child UV + plane recipe, not face index alone.

---

## 4. Constraints — **kernel + panel done; polish open**

Interactive pick tools with **lock current** for DistO/Rad/Dist (no HUD yet).  
`tool.txt`: `mode tool nclick dirty cstr_type npick` for single-button highlight.

**Open:** glyphs, drag, numeric dim HUD (SQL later), Jacobian when multipass fails, retarget constraints on trim/delete.

---

## 5. Construction tools roadmap (bulk of “real sketcher”)

### 5.1 Principles

1. Emit **live arcs/circles**, not tess.  
2. Emit **constraints** where cheap (Radius, Tangent, Coincident).  
3. Patterns store **recipe** (source + params) when possible.  
4. Shapes = **macros** over lines/arcs.

### 5.2 Grind order (locked)

```text
S1  Sketch fillet (two lines + R)          ← DONE
S2  3-point arc (start / through / end)    ← DONE
--- solid product path (priority over construction UI) ---
R1  Revolve UI in cad_app                  ← DONE (picked axis, Class A SoR)
R2  Sketch-on-face (inherit Sketch_0)      ← NEXT (parent slot wired)
R3  Draft / loft / sweep expose
--- construction UI (kernel+Gtk shipped; polish later) ---
S3  N-gon builders                         ← DONE (tool_polyN)
S4  Linear / circular pattern UI           ← deferred
S5  Slot + rounded rect                    ← slot = poly2
S6  Spline poles                           ← DONE (tool_spline + done)
S7  Mirror pattern UI                      ← deferred
S8  Pattern of features (product tree)
S9  Undo / dim HUD polish                  ← deferred
S10 Constraints ribbon (origin vs relational) ← DONE (cstr_* + Solve)
```

### 5.3 S1 — Sketch fillet (radius)

**UX:** pick line A, pick line B, radius R (default mm or `fillet_r` / HUD later).

**Algorithm (kernel `CAD_Sketch.FilletLines`):**

1. Intersect infinite supports (or shared vertex) → corner `I`.  
2. Unit directions `u1,u2` from `I` along **kept** legs.  
3. Inward unit normals `n1,n2` into the filleted wedge.  
4. Arc center `C` = intersection of offset lines at distance R.  
5. Tangent points `T1 = C - R n1`, `T2 = C - R n2`.  
6. Truncate each line to far-end → `Ti`.  
7. `AddArc(C, R, a0, a1)` with CCW span of the interior fillet.  
8. Optional: Radius + Tangent constraints (geometry-first OK for v1).

**Fail loud:** parallel lines, R too large for segment length, degenerate angle.

**Exit:** demo L-corner → fillet → closed profile pad; panel **Fillet** tool.

### 5.4 S2 — 3-point arc

Clicks: P0, P1 (through), P2. Fit circle; store arc P0→P2 through side of P1. Snap ends to existing geometry when near. Optional coincident to ends.

### 5.5 S3 — Regular shapes

| Shape | Params | Emits |
|-------|--------|-------|
| Triangle / square / pent / hex / oct / N-gon | center, radius or flat-flat, rotation, N | N lines |
| Optional | — | Equal length constraints later |

Center defaults to user **Point** or Sketch_0 `O`. Shapes **seed patterns**.

### 5.6 S4 — Patterns

| Pattern | Params | Behavior |
|---------|--------|----------|
| Linear | count, Δu/Δv or Point A→B spacing | Copy selected entities |
| Circular | center Point, count, total angle or full 360 | Rotate copies |

**v1:** bake instance geometry (+ optional EqualR on circles).  
**v2:** recipe node for edit count/spacing.  
Polygons + circular pattern = bolt circles / hex packs.

### 5.7 S5 — Slot / rounded rect

Slot = line + two semicircle arcs. Rounded rect = rect + four fillets (reuse S1).

### 5.8 S6 — Splines

| Tier | Content |
|------|---------|
| P0 | Polyline through Points (already almost freehand) |
| P1 | Cubic Bezier / B-spline poles in UV; tess on clone only |
| P2 | G1 to lines/arcs; pole drag |

Same live-vs-clone rule as circles.

### 5.9 S7+ 

Mirror, undo, drag, dim HUD, plane-on-face — product completeness, not blocking mechanical sketch bulk.

---

## 6. Profiles / pad (do not regress)

Clone projection; auto-select only if one face; fill all selected; pad mask; outer envelope multi-circle.

---

## 7. API surface (current + target)

```text
# datum / points / constraints (done)
CAD_Sketch.EnsureDatum / SnapToDatum / AddUserPoint
CAD_Sketch.AddConstraint / AddConstraint2 / SetConstraintValue / SolveConstraints

# construction (S1+)
CAD_Sketch.FilletLines(sk, li, lj, r) -> ok
CAD_Sketch.Arc3Pend(x0,y0, x1,y1, x2,y2)  // 6 floats only (no handle)
CAD_Sketch.Arc3Point(sk)                  // Fit+Commit from pool
// UI: Arc3Fit(6) then Arc3CommitLast(sk) — never handle+6 in one call
CAD_Sketch.AddNGon(sk, cx, cy, radius, n, rot) -> ok
CAD_Sketch.PatternLinear(...) / PatternCircular(...)
```

---

## 8. Anti-patterns

1. Permanent live tess of circles/arcs/splines.  
2. World XYZ baked into child sketches.  
3. Face index alone as attachment.  
4. Relative-only constraint soup as default.  
5. Solver theater.  
6. Silent wrong profile / silent fillet invent.  
7. Pattern that only bakes with no path to recipe later.  
8. Opaque auto-constraints user cannot delete.

---

## 9. Success criteria

### Done

- [x] Sketch_0 datum visible + snap  
- [x] Absolute + relational multipass solve  
- [x] User Points; interactive constraint panel  
- [x] Trim keeps circles as entities  
- [x] Multi-circle pad / dogbone  

### Near (S1–S4)

- [x] Fillet two lines with R  
- [x] 3-pt arc  
- [ ] N-gon builders  
- [ ] Linear + circular pattern  

### Mid

- [ ] Slot / rounded rect  
- [ ] Spline poles + clone tess  
- [ ] Undo; drag free DOF  
- [ ] Constraint glyphs  

### Long

- [ ] Sketch-on-face clean rebuild on height/angle  
- [ ] Feature patterns (holes)  
- [ ] Real Jacobian Solve2D  

---

## 10. One-page summary

```text
DONE     freehand · trim · pad · Sketch_0 · Points · constraints · fillet · **arc3**
GRIND    S3 N-gon → S4 patterns
LATER    spline · user fillet R · mirror · undo/drag · plane-on-face

ROOT     Constraints hang from zero first.
         Tools emit geometry + constraints.
         Height/angle / pattern count → re-eval frame/recipe → clean solid.
```

**Next action:** **S3 `AddNGon`** + panel tool.
