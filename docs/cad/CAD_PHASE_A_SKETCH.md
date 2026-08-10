# Phase A — Sketch Completeness (DXF + native primitives)

**Parent:** `CAD_CORE_COMPETITIVE_PLAN.md`  
**Full sketcher roadmap (working inventory + constraints + Sketch_0):** `CAD_SKETCHER_IMPL.md`  
**Architecture:** Sketch owns 2D UV entities only; Feat turns profiles into B-Rep; IO is interchange; View is derived.  
**Style:** Compiler-like layers — parse → IR (sketch) → lower (tess/loop) → codegen (Topo solid). Standardized `Add*` / `Get*` / `Build*` / `Validate*` / `Export*` verbs.

---

## A.0 Layer contracts (do not violate)

| Library | Owns | May call | Must not |
|---------|------|----------|----------|
| `CAD_DXF` | Parse/emit DXF text | Sketch, Sys, Num, StringUtils | Topo, Feat, View |
| `CAD_Sketch` | Entities, loops, validation | Store, Num, Geom | Bool, IO files, View |
| `CAD_Feat` | Pad/pocket/revolve recipes | Sketch, Topo, Bool, Num | DXF parse, pixels |
| `CAD_IO` | Path/fd load-save | DXF, Feat, Topo, Sketch | Feature policy |
| `CAD_View` | Tess → FB → BMP | Tess, Topo, FB | Authoring |

**Standard method families**

```text
Create* / Add* / Get*Count / Build* / Tessellate* / Validate* / Export*
Import* (IO/DXF only) / Load* (IO: path→solid) / Extrude* (Feat only)
```

---

## A.1 Sub-phase checklist

### A1 — LWPOLYLINE import  **[done]**

| ID | Task | Status |
|----|------|--------|
| A1.1–A1.5 | LWPOLY parse, Atan/Atan2, bulge→arc/line, fixtures | **done** |

### A2 — Native sketch API parity  **[done]**

| ID | Task | Status |
|----|------|--------|
| A2.1–A2.3 | Store layout, AddPolyline, profile getters | **done** |
| A2.4 | Pure native demo (no DXF) | optional follow-up |

### A3 — Multi-loop sketch (outer + holes)  **[done]**

| ID | Task | Status |
|----|------|--------|
| A3.1–A3.5 | BuildAllClosedLoops, ExtrudeProfile 2+ → plate hole | **done** (1 hole) |

### A4 — DXF sketch export  **[done]**

| ID | Task | Status |
|----|------|--------|
| A4.1–A4.3 | ExportSketch, round-trip, CAD_IO.ExportDXF | **done** |

### A5 — Profile validation + gates  **[done]**

| ID | Task | Status |
|----|------|--------|
| A5.1–A5.3 | ValidateProfile, error codes, smoke_phase_a.sh | **done** |

---

## A.2 Sketch store layout (Phase A + CS-0)

Tag **10**, stride **24**:

| Slot | Name | Content |
|-----:|------|---------|
| 0 | n_lines | count |
| 1 | lines_addr | x1,y1,x2,y2 × n |
| 2 | n_loop | primary loop vertex count (compat / outer) |
| 3 | loop_addr | primary xy pairs (compat pointer into pool or own) |
| 4 | workplane | id |
| 5 | cap_lines | |
| 6 | cap_loop_pts | max verts in pool |
| 7 | n_circles | |
| 8 | circles_addr | cx,cy,r |
| 9 | cap_circles | |
| 10 | n_arcs | |
| 11 | arcs_addr | cx,cy,r,a0,a1 rad |
| 12 | n_profiles | number of closed loops (≥1 after BuildAll) |
| 13 | profile_meta | [n_pts, start_idx] × n_profiles (start into pool as vert index) |
| 14 | loop_pool | all profile xy packed |
| 15 | cap_profiles | max profiles (64) |
| 16 | n_pts | anchor count |
| 17 | pts_addr | x,y anchors (ends/crossings only — not full tess) |
| 18 | cap_pts | max anchors |
| 19 | plane_id | 0 = world / Sketch_0 |
| 20 | n_constraints | constraint count |
| 21 | constraints_addr | 8 words × constraint |
| 22 | cap_constraints | max (128) |
| 23 | datum_flags | bit0 = EnsureDatum done |
| 24 | n_upts | first-class user Point count |
| 25 | upts_addr | x,y user Points (not wiped by RebuildAnchors) |
| 26 | cap_upts | max (512) |
| 27 | reserved | |

**Caps (2026-08-08):** primary loop ≤**4096** verts; profile pool enlarged; `MakePolyPrism` ≤**2048**.

**Compat:** After `BuildClosedLoop` / `BuildAllClosedLoops`, profile 0 is outer (largest |area|); slots 2–3 mirror profile 0 for old Feat paths.

**Live vs clone:** Interactive app keeps circles/arcs on the **live** sketch. Tessellation + face walk run on a **clone** (`CA_RebuildProfiles`); profile XY is copied back for overlay/Pad only.

---

## A.3 Lowering pipeline (compiler analogy)

```text
DXF text
  └─ CAD_DXF.Import*          # lexer/parser
        └─ CAD_Sketch entities   # IR
              ├─ TessellateArcs/Circles/Bulges
              ├─ BuildAllClosedLoops
              └─ ValidateProfile
                    └─ CAD_Feat.ExtrudeProfile   # codegen
                          └─ CAD_Topo solid
```

---

## A.4 Error codes (standard)

| Code | Meaning |
|-----:|---------|
| 0 | ok |
| -1 | null handle / bad arg |
| -2 | empty / too few points |
| -3 | not closed |
| -4 | zero / degenerate area |
| -16 | IO open/read/write fail |
| -17 | unsupported / not implemented |

---

## A.5 Phase A exit criteria

- [x] LWPOLYLINE rect/plate loads and extrudes  
- [x] Multi-loop single sketch → plate with through hole (2 FACE_BOUND)  
- [x] Native API: `AddPolyline` / `AddBulgeSegment` / `BuildAllClosedLoops`  
- [x] ExportDXF round-trips LINE sketch  
- [x] `smoke_phase_a.sh` green  
- [x] Layer rule: DXF only → Sketch (no Topo from DXF)

**Open follow-ups (not blocking A exit):** multi-hole (>1) in one ExtrudeProfile; LWPOLYLINE with non-zero bulge fixture from FreeCAD; pure native demo without DXF file.
---

## Phases B–E sub-phase index (layout only; implement after A)

### Phase B — Sketch → solid  (see `CAD_PHASE_B_SOLID.md` — B2–B6 core done)
- B1 Extrude pad refine (mixed profile) — interactive multi-circle pad **done** 2026-08-08  
- B2 Extrude cut on body — **done**  
- B3 Revolve pad — **kernel done**; app UI next  
- B4 Revolve cut — **kernel done**  
- B5 Analytic prefer (cyl faces) — **partial**  
- B6 Draft (optional) — **done**

### Phase C — Solid tools
- C1 Hole tool completeness  
- C2 Poly pocket  
- C3 Plane–cyl fillet  
- C4 Chamfer  
- C5 Bool domain matrix expand  
- C6 Rigid transform

### Phase D — Controls
- D1 `cad_tool` unified CLI  
- D2 `cad_sketch` builder CLI  
- D3 Host interactive sketch (optional)  
- D4 In-memory feature list / regen

### Phase E — Product substrate
- E1 Sketch_0 + plane recipes  
- E2 PG feature tree  
- E3 Persistent naming  
- E4 Constraint solve  

---

*Implement A1→A5 in order; tick this file and CAD_PROGRESS.md each grind.*
