# CAD Core Competitive Plan

**Status:** living plan (2026-08-07)  
**Audience:** implementers  
**Product stance:** pure-AILang **kernel + tools**, not FreeCAD glue, not a scripting-first product.  
**Pairs with:** `CAD_Kernel_Design_v3.md` (normative), `CAD_PROGRESS.md` (ticks), `CAD_CLI.md` (current host surface).

---

## 0. Thesis (what you said, made precise)

Commercial CAD (OCC/FreeCAD, SolidWorks, Fusion, Parasolid-based tools) is mostly:

```text
┌─────────────────────────────────────────────────────────┐
│  Tools / controls / workbenches / CAM / drawings        │  ← product surface
├─────────────────────────────────────────────────────────┤
│  Feature recipes (extrude, revolve, fillet, pattern…)     │  ← thin, composable
├─────────────────────────────────────────────────────────┤
│  CORE ENGINE                                            │
│    2D sketch geometry + (optional) constraints            │
│    Exact curves/surfaces                                  │
│    B-Rep topology + validation                            │
│    Intersections                                          │
│    Boolean / local ops (fillet, chamfer, offset…)         │
│    Tessellation + interchange (STEP/DXF/…)                │
└─────────────────────────────────────────────────────────┘
```

**We already have a seed of that core** (solids, restricted bools, plane–plane fillet/digon, DXF→extrude, STEP out, software view).  
**Next competitive pressure is not scripting and not AOS GUI** — it is:

1. **DXF / sketch primitives** rich enough to express real profiles  
2. **Sketch → solid** operators that produce honest B-Rep (not tess soup)  
3. **Pass-through B-Rep tools** (fillet, hole, pocket, revolve…) composed cleanly  
4. **Controls** that drive those tools (host CLI today; interactive sketch later)

Scripting engines (Python/AIMacro) are **optional consumers** of a stable tool API. They are not the product definition.

---

## 1. What “competitive” means here

We will **not** match SolidWorks feature count or OCC maturity on a short horizon. We will match the **shape of the core** and close the gap where daily work fails FreeCAD-less:

| Competitive bar | Measure |
|-----------------|----------|
| **Author real 2D profiles** | LINE/CIRCLE/ARC/LWPOLYLINE (+ ELLIPSE later); closed multi-loop (outer+holes) |
| **Solid from profile** | Extrude, revolve, (later) loft/sweep — analytic where possible |
| **Solid edit ops** | Extrude cut/pad, through/blind hole, rect/poly pocket, plane–plane fillet; expand domain honestly |
| **Exact interchange** | STEP export of true B-Rep; DXF round-trip for sketches |
| **See results** | Tess + BMP (and STEP) without FreeCAD |
| **Clean architecture** | Layer graph: Sketch → Feat recipes → Topo/Geom/Bool; no feature logic inside STEP export |

**Non-goals for this plan**

- Full general boolean of arbitrary freeform B-Rep (OCC’s decades of isect/heal) as v1 target  
- Feature parity with SolidWorks tree UI  
- Python/AIMacro as primary authoring  
- AOS-hosted CAD workbench before sketch+solid core is “toolable”

---

## 2. Where we are (honest inventory)

### Have (engine seed)

| Layer | Reality |
|-------|---------|
| Geom / Num / Store | Real |
| Topo solids | Box, poly prism, cyl, sphere, plate holes, poly-through-hole, boss/notch shells |
| Bool | Restricted domain (honest, not OCCT-general) |
| Blend | Plane–plane fillet + equal-R digon |
| Sketch | Lines, circles, arcs (store); closed loop chain; tess arcs/circles for poly path |
| DXF in | LINE, CIRCLE, ARC → sketch → extrude / plate+hole |
| Feat | ExtrudeProfile, ExtrudePlateThroughHole, hole/pocket recipes (restricted) |
| IO | STEP export walk; DXF import; path/pipe CLI |
| View | Software tess → BMP (coarse OK) |

### Missing for competitive *core* (priority order)

| Gap | Why it matters |
|-----|----------------|
| **LWPOLYLINE + bulge** | Real DXF from CAD tools is rarely pure LINE/ARC soup |
| **Multi-loop sketch as first-class** | Outer + holes in one sketch (not only two-file plate API) |
| **Analytic extrude of arcs/circles in mixed profiles** | Today arcs tessellate to lines → poly prism; competitive cores keep CIRCLE/ARC on edges when possible |
| **Revolve** | Second pillar of solid-from-sketch (shafts, disks, bottles) |
| **Extrude cut / pad on existing body** | Tooling = body + profile tool + bool, not only “create solid from empty” |
| **Sketch on plane (not only world XY)** | Prerequisite for multi-feature parts (Sketch_0 lineage in design doc) |
| **General (or broader) boolean** | Domain expansion with tests; don’t claim general until isect is real |
| **Plane–cyl fillet / chamfer** | Completes “edge tools” story after plane–plane |
| **DXF export of sketch** | Round-trip / external edit loop |
| **Sketch creator controls** | Create/edit primitives without external CAD |

---

## 3. Design principles (clean implementation)

1. **Recipes over monoliths**  
   `Pad` / `Pocket` / `Revolve` / `Hole` = sketch + parameters + call Topo/Bool. No second kernel inside Feat.

2. **Sketch is UV geometry; solid is B-Rep**  
   Sketch never owns facets. Tess is display/CAM sampling of B-Rep (or of sketch for 2D preview only).

3. **Prefer analytic curves on solid edges**  
   When profile is pure CIRCLE → cylinder solid (already).  
   Long-term: extrude of ARC/LINE loops should keep cylindrical faces where the generator is circular — not only LINE tessellation.  
   Short-term honesty: tessellated poly prism is OK if labeled and gated; competitive track upgrades to analytic.

4. **Restricted ops stay restricted until isect/bool expand**  
   Loud failure > silent wrong solid. Domain tables in docs and demos.

5. **Tools compose**  
   Example: plate + hole = outer rect extrude + inner profile cut (or dual-loop shell). One implementation path, multiple UIs.

6. **Controls call tools; tools call kernel**  
   ```text
   Control (CLI / later sketch UI)
        → Tool API (Pad, Pocket, Revolve, Fillet, ImportDXF, ExportSTEP, ViewShot)
             → CAD_Sketch / CAD_Feat / CAD_Topo / CAD_Bool / CAD_IO / CAD_View
   ```
   No control code builds STEP strings or fakes shells.

7. **Interchange is STEP (solids) + DXF (sketches)**  
   Postgres feature tree later; not blocking core geometry.

8. **No scripting requirement**  
   Host tools (`cad_load`, `cad_view`, future `cad_sketch`) are enough. Scripts may shell them; kernel does not depend on a language runtime.

---

## 4. Competitive core map (target architecture)

```text
                    ┌──────────────┐
                    │  CAD_IO      │  DXF ↔ Sketch, STEP ↔ Solid
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  ┌────────────┐   ┌─────────────┐   ┌─────────────┐
  │ CAD_Sketch │──▶│  CAD_Feat   │──▶│  CAD_Topo   │
  │ primitives │   │ Pad/Pocket  │   │ B-Rep build │
  │ loops      │   │ Revolve     │   │ shells      │
  │ (solve later)  │ Hole/Fillet │   └──────┬──────┘
  └────────────┘   └──────┬──────┘          │
                          │          ┌──────┴──────┐
                          │          ▼             ▼
                          │    CAD_Bool        CAD_Blend
                          │    CAD_Isect       CAD_Geom
                          └──────────┬─────────────┘
                                     ▼
                              CAD_Tess / CAD_View
                              (look-at only)
```

**Sketch creator** = UI/controls that only mutate `CAD_Sketch` + call Feat tools.  
**Solid model output** = always B-Rep handle → STEP (and optional BMP).

---

## 5. Phased roadmap

### Phase A — Sketch completeness  **✓ DONE (2026-08-07)**

**Detail:** `Docs/CAD/CAD_PHASE_A_SKETCH.md` · gate: `./CAD/smoke_phase_a.sh`

| Sub | Name | Status |
|-----|------|--------|
| **A1** | LWPOLYLINE + bulge | done |
| **A2** | Native sketch API | done |
| **A3** | Multi-loop sketch | done (1 hole) |
| **A4** | DXF sketch export | done |
| **A5** | Validate + smoke | done |

### Phase B — Sketch → solid  **✓ B2+B3 done (2026-08-07)**

**Detail:** `Docs/CAD/CAD_PHASE_B_SOLID.md` · `./CAD/smoke_phase_b.sh`

| Sub | Name | Status |
|-----|------|--------|
| **B1** | Extrude pad refine | done (Phase A) |
| **B2** | Extrude cut on body | **done** rect/circle/poly |
| **B3** | Revolve pad | **done** cyl + tube |
| **B4** | Revolve cut | **done** `RevolveCut` |
| **B5** | Analytic prefer | partial (pure circle pad) |
| **B6** | Draft + midplane | **done** `ExtrudeDraft` / `ExtrudeSymmetric` |

**Rule:** Feat recipes only; no tess as solid truth when Geom can hold the face.

### Phase C — next focus after B4 optional

### Phase C — Solid tools  **C4–C6 + cyl−cyl in progress**

**Detail:** `Docs/CAD/CAD_PHASE_C_TOOLS.md` · `./CAD/smoke_phase_c.sh`

| Sub | Name | Status |
|-----|------|--------|
| **C1** | Hole tool | done (earlier) |
| **C2** | Poly through cut | done (B2 ExtrudeCut) |
| **C3** | Plane–cyl fillet | open |
| **C4** | Chamfer box vertical corner | **done** |
| **C5** | Bool cyl−cyl coaxial | **done** |
| **C6** | Translate + RotateSolidZ | **done** |
| **C7** | Pattern / Mirror / Shell (box) | **done** compound multi-shell |

### Phase D — Controls (host tools, not AOS)

| Sub | Name | Gate |
|-----|------|------|
| **D1** | `cad_tool` CLI | pad/cut/revolve/hole/fillet/import/export/view |
| **D2** | `cad_sketch` CLI | create primitives, DXF, extrude |
| **D3** | Host interactive sketch | optional |
| **D4** | In-memory feature list | regen precursor |

### Phase E — Product substrate

| Sub | Name |
|-----|------|
| **E1** | Sketch_0 + plane recipes |
| **E2** | PG feature tree |
| **E3** | Persistent naming |
| **E4** | Constraint solve |

---

## 6. Recommended near-term sequence (actionable)

**Now → next 4–6 grinds (Phase A+B spine):**

```text
1. LWPOLYLINE (+ bulge → arcs)
2. Multi-loop sketch (outer + holes) unified Extrude/Pad/Cut
3. Extrude cut on existing body (even if domain-restricted)
4. Revolve pad (profile + Z or line axis)
5. cad_tool / cad_sketch CLI wrappers (controls → tools)
6. Only then: analytic mixed-profile extrude, fillet expand, constraints
```

**View quality** stays maintenance (defl, views) — already good enough to gate solids without FreeCAD.

**Scripting / AIMacro:** optional; if used, only shell `cad_*` tools. Do not design the kernel around a language.

---

## 7. Competitor “core engine” cheat sheet (what to steal conceptually)

| System | Core idea to emulate | What not to copy yet |
|--------|----------------------|----------------------|
| **OpenCASCADE** | Exact B-Rep + isect + bool as library; tools = algorithms | Full API surface, heal soup |
| **FreeCAD** | Part/PartDesign as feature recipes on OCC | Python dependency, GUI |
| **SolidWorks / Parasolid** | Sketch → Boss/Cut Extrude/Revolve as primary UX | Full PDM/UI |
| **OpenCascade “modeling algorithms”** | Extrusion, revolution, boolean, fillet as *ops* | |

Our equivalent:

| Their concept | Ours |
|---------------|------|
| TopoDS_Shape | `CAD_Topo` solid handle + shell walk |
| BRepPrimAPI_MakePrism | `ExtrudeProfile` / prism builders |
| BRepPrimAPI_MakeRevol | **todo** Revolve |
| BRepAlgoAPI_Cut | `CAD_Bool.Difference` (expand domain) |
| BRepFilletAPI | `CAD_Blend` |
| Sketch geometry | `CAD_Sketch` + DXF |
| STEP control | `CAD_IO.ExportSTEP` |

---

## 8. Success criteria (“looks like a core”)

You can say the core is competitive **for mechanical prismatic work** when:

1. Load or draw a multi-loop DXF/sketch with arcs (slot, plate+holes).  
2. Pad and cut extrude (and at least one revolve) produce STEP that FreeCAD opens as solid.  
3. Fillet a plane–plane edge on that solid.  
4. View BMP + STEP without FreeCAD for authoring feedback.  
5. All of the above via **tool APIs/CLI**, not ad-hoc demos.  
6. Docs list **supported domains** for bool/fillet (honest matrix).

That is “engine + tools,” not “another FreeCAD.”

---

## 9. Anti-patterns (reject in review)

- STEP recipe exporters that invent geometry without shells  
- Tessellating for solid truth when analytic is possible  
- Growing AIMacro/Python as the only way to build parts  
- Building AOS GUI before Pad/Cut/Revolve + multi-loop sketch  
- Claiming “general boolean” without isect gates  
- Mixing sketch UV and world XYZ in one unstructured soup  

---

## 10. Doc maintenance

| When | Update |
|------|--------|
| Each grind | `CAD_PROGRESS.md` ticks |
| Phase complete | This file phase status + gates |
| Tool CLI freeze | `CAD_CLI.md` |
| Contract change | `CAD_Kernel_Design_v3.md` may-call lists |

---

## 11. Immediate next grind (proposal)

**A1 + A3 partial:** LWPOLYLINE import + multi-loop sketch extrude path (one sketch, outer+hole → plate solid), gates with existing escutcheon geometry and a FreeCAD-exported LWPOLYLINE fixture.

Revolve follows immediately after multi-loop pad/cut is clean.

---

*End of plan. Implementation proceeds only by phase gates; no silent domain expansion.*
