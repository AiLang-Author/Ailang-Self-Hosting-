# CAD Kernel — Development Guide

**Status:** living process doc (pairs with `CAD_Kernel_Design_v3.md` v3.1)  
**Last updated:** 2026-08-05

---

## 1. Diagnosis (where we actually are)

Gemini (and the v3.0 skeleton push) left a **correct module map** and a lot of
**API theater**. Interfaces and phase names exist; most bodies do not implement
geometry. Gallery STLs/STEPs and many “passes” were driven or backfilled by
**Python scripts in `CAD/`** — those scripts are **deleted**. The kernel is pure
AILang or it is lying.

| Reality | Notes |
|--------|--------|
| Design path | Layer graph in design doc is sound (compiler metaphor: feature tree = AST, B-rep = IR) |
| Implementation | Mostly stubs: counters, null checks, `ReturnValue(0)` |
| Closest to real | `CAD_Num` (tol, vectors, Orient*, Newton Sqrt) — still incomplete vs design |
| Critical hole | `CAD_Store.Alloc` does not store entity payloads — handles without memory |
| Dual files | `CAD_Num`/`CAD.Num`, `CAD_Store`/`CAD.Store`, `CAD_Sys`/`CAD.Sys` — pick one |
| Persistence | **v3.1:** Postgres = system of record; `.cadx` abandoned |
| Interchange | **STEP** primary (B-Rep); DXF sketches; STL optional not look-at |
| Competitive target | OpenCASCADE-class **kernel** (L0–L6), not FreeCAD UI glue |

**Rule:** if a demo “works” without a solid gate test that can fail on wrong
numbers, it is not done. Smoke paths that always print VERIFIED are not gates.

---

## 2. Persistence model (normative)

```
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL (CAD.Repo) — system of record               │
│  projects, sessions, users, revs, feature_tree, params  │
│  optional BYTEA caches: brep, mesh                      │
└───────────────────────────┬─────────────────────────────┘
                            │ open / commit
                            ▼
┌─────────────────────────────────────────────────────────┐
│  In-memory arena (CAD.Store slabs + handles)            │
│  Hot path: Geom, Topo, Isect, Bool, Tess, Sketch solve  │
└───────────────────────────┬─────────────────────────────┘
                            │ import / export only
                            ▼
┌─────────────────────────────────────────────────────────┐
│  Neutral files: STEP (primary), DXF; STL optional       │
└─────────────────────────────────────────────────────────┘
```

- **Do not** invent proprietary binary documents.
- **Do not** query Postgres per edge in boolean loops.
- **Do** use PG for sessions, ACLs, revisions, multi-user, agent jobs (free).
- **Do** store UI configuration in PG as well: workbenches, toolbars, tools,
  user prefs — avoids a second config format and registry fight later.
- **Unit tests** for L0–L6: pure memory, no server required.
- **Integration tests** for Repo: live local PG when available.

Schema sketch lives in design doc §7.3 `CAD.Repo` (v3.1).

---

## 3. Dependency ladder (ground floor first)

Sketch/Solve2D is **application layer**, not the foundation.

| Order | Layer | Module | What “real” means |
|------:|-------|--------|-------------------|
| 0 | Process | docs, fixtures, single naming | This guide + design v3.1 |
| 1 | L0 | `CAD_Store` | Real slabs: write/read fields by handle, gen free |
| 1 | L0 | `CAD_Num` + LA | Tol, V3, mat, dense LU; predicates policy |
| 1 | L0 | `CAD_Sys` | File/syscall as needed |
| 2 | L1 | `CAD_Geom` | Analytic eval + d1 (+d2), project |
| 3 | L1 | `CAD_BSpline` | Real Cox–de Boor, curve then surface |
| 4 | L2 | `CAD_Topo` | Linked radial-edge + Euler that sticks |
| 5 | L3 | `CAD_Isect` | C-C, C-S, S-S (analytic first) |
| 6 | L4 | `CAD_Bool` | Fuse/cut/common on restricted domain first |
| 7 | L5–6 | Tess, Feat, Sketch/Solve2D | After solids have a spine |
| 8 | L7 | `CAD_IO`, `CAD_Repo` | Interchange + PG product path |

**Start here next (code):** unify Store/Num/Sys → implement **real Store** →
harden **Num** → analytic **Geom**. No new Python. No CADX.

---

## 4. Tree layout

```
Docs/CAD/
  CAD_Kernel_Design_v3.md     # normative design (v3.1: no cadx)
  CAD_DEV_GUIDE.md              # this file
  plane_coordinate_tree_spec.md
  notes/                        # historical gemini notes (not authority)

Librarys/Cad/                   # ONLY engine libraries (AILang)
CAD/                            # harnesses, demos, phase gates (AILang only)
fixtures/cad/                   # (target) dxf/, stl/, step/, golden/
  # currently still: test-dxf-files/, test-stl/, root master_model.*
```

**Forbidden in `CAD/` and `Librarys/Cad/`:** `.py`, `.js`, shell generators that
emit “kernel” goldens. External oracles (OCCT/FreeCAD) may live under
`tools/cad-oracle/` later, clearly labeled non-kernel.

---

## 5. Coding and gate rules

From design doc §3–§5, abbreviated:

1. Interfaces freeze; may-call violations are design escalations (§13).
2. Max 6 args; points/vectors as `Address`; flat SSA; no deep nesting.
3. Errors are status codes; no exceptions.
4. One tolerance authority (`CAD_Num` / §6).
5. **Gate tests assert numeric/topological goldens**, not `handle != 0`.
6. Exit non-zero on failure. `cadk test` must be scriptable.
7. Dual library files: **canonical underscore form** `Library.CAD_*.ailang`;
   dotted duplicates to be merged/removed after import audit.

---

## 6. What Gemini got wrong (so we do not repeat it)

- Claiming phase 0–13 “verified” with empty Newton/boolean/NURBS bodies.
- Shipping **Python** that wrote STLs/STEPs so renders looked real.
- Prioritizing snap/gallery UX before Store/Geom/Topo.
- Specifying **`.cadx`** while the stack already has a full Postgres driver.
- ~1/10 implementation density vs claims — treat every stub as untrusted.

---

## 7. Immediate backlog (P0 housekeeping → P1 substrate)

**Done**

- [x] Design doc in `Docs/CAD/`, bumped to **v3.1** (`.cadx` out, PG SoR)
- [x] Gemini CAD notes under `Docs/CAD/notes/`
- [x] All `CAD/*.py` removed
- [x] **Tranche 1 substrate (2026-08):** real `CAD_Store` slabs (StoreValue/Dereference;
      not ArrayGet — those assume +8 header and corrupt bulk slabs), free list + gen,
      `CAD_Num` dense LU/LinSolve + V3Add/Sub/Scale, dotted dual modules removed,
      `CAD/test_num.ailang` hard gate **18/18 PASS**
- [x] Analytic `CAD_Geom` eval (line/circle/plane/cyl/sphere + project) + trig poly
- [x] `CAD_BSpline` Cox–de Boor curve/surface eval (arity-packed)
- [x] Linked `CAD_Topo` half-edge + `MakeBoxSolid` / triangle; Euler checks
- [x] STL path for box + FreeCAD-visible STEP box-from-AABB (`CAD_IO.ExportSTEP`)
- [x] **§1.4 product model frozen:** Sketch_0 = part root/origin; later sketches use
      relative plane recipes; ordered feature tree in Postgres; B-Rep/STEP derived

**Coding note — raw memory**

- `ArrayGet`/`ArraySet` use offset `index*8+8` (array object header).
- Kernel slabs and bulk tables must use `StoreValue(addr, v)` / `Dereference(addr)`
  with `addr = base + word_index*8`.

**Product model (normative — design §1.4)**

- Sketch_0 is the part origin. Reordering the root breaks models (industry-wide).
- Construction planes = recipes (offset/angle/distance/on-face) from parents.
- Sketch data is UV-only; world comes from evaluated plane frames.
- Postgres owns ordered `feature_tree` / `feat_index` + params; arena regenerates.
- Prefer feature provenance over “face index after boolean” (TNP).

**Capability target (full CAD kernel — not a mesher)**

Design v3 already scopes OpenCASCADE-class L0–L6. Terminology we use:

| User word | Kernel meaning | Module |
|-----------|----------------|--------|
| Hole | Subtractive **boolean cut** (tool solid, usually cylinder) | `CAD_Bool.Difference` + Feat |
| Pocket / cut | Same family: difference | Bool + Feat |
| Fuse / join | Union | `CAD_Bool.Union` |
| Fillet / round | Edge blend (constant/variable radius) | `CAD_Blend` (needs offset/isect) |
| Chamfer | Edge blend (plane strip) | `CAD_Blend` |
| Pad / extrude | Sketch profile → solid | Feat + Topo |
| STEP | Exact B-Rep interchange (**look-at truth**) | `CAD_IO` |

`CreateHole` (not “drill” as the primary name) is the high-level cut API.
`DrillHole` is an alias only. Do not green-light hole tests until Difference is real.

**Policy: STEP-first.** Do not dual-export STL for FreeCAD look-at. Industry
interchange is STEP; STL is a faceted dump for printers — not kernel proof.

**Policy: no STEP recipes / kind matchers.** `ExportSTEP` only walks
`solid.shell` (B-Rep). Hole/counterbore/sphere “pretty” writers are deleted.
If a solid has no shell, export fails — build topology in Topo/Bool, don’t add
export special cases.

**Look-at outputs (regenerate anytime)**

```bash
./ailang.x CAD/demo_primitives.ailang -o /tmp/demo_prim && /tmp/demo_prim
./ailang.x CAD/demo_hole_intent.ailang -o /tmp/demo_hole && /tmp/demo_hole
./ailang.x CAD/demo_blind_hole.ailang -o /tmp/demo_blind && /tmp/demo_blind
./ailang.x CAD/demo_multi_hole.ailang -o /tmp/demo_mh && /tmp/demo_mh
./ailang.x CAD/demo_counterbore.ailang -o /tmp/demo_cb && /tmp/demo_cb
./ailang.x CAD/demo_rect_pocket.ailang -o /tmp/demo_rp && /tmp/demo_rp
./ailang.x CAD/demo_union_boxes.ailang -o /tmp/demo_u && /tmp/demo_u
./ailang.x CAD/demo_side_hole.ailang -o /tmp/demo_sh && /tmp/demo_sh
# after deleting old models — regenerate everything:
./ailang.x CAD/demo_regen_all.ailang -o /tmp/regen && /tmp/regen
./ailang.x CAD/demo_bool_ops.ailang -o /tmp/dbo && /tmp/dbo
./ailang.x CAD/demo_pad_boss.ailang -o /tmp/dpad && /tmp/dpad
# FreeCAD: test-stl/cad_*.stp only
# Note: side holes/notches open on vertical faces — look from the side, not top.
# Pad boss = stepped solid on top of plate (not a Union of two floating boxes).
```

**Plate-hole shells (Topo, not STEP recipes)**

- `BuildPlateHoleShell` attaches walkable B-Rep for kind-3 plates.
- Independent holes (through/blind) share top openings; through open bottom.
- Nested coaxial counterbore (large shallow + small deeper): annular floor,
  pilot wall only below floor — no thin septum wall.
- `AppendBoxHole` / first cut rebuild shell after param write.

**Rect pocket (box − box)**

- `MakeBoxRectPocketSolid` + `CAD_Feat.CreateRectPocket` / `Difference` kind0−kind0
  when tool cuts from body top (axis-aligned). Blind or through. Kind 0 shell walk.

**Next (geometry spine for real STEP + features)**

1. [x] Store-backed `CAD_Geom` records (`MakeLine` / `MakePlane*`) + wire into topo
2. [x] `MakeBoxSolid` edges/faces carry real curve/surface handles (not null)
3. [x] `MakeCylinderSolid` (n-gon + circle/cyl analytic handles) + tess n-gon fan
3b. [x] Tess segments from chordal deflection `CircleSegCount(r,δ)` — not fixed n
4. [x] Walk-based poly STEP (`WritePolySolidSTEP`); no kind recipes
5. [x] Hole shells: through / blind / multi / nested counterbore (Topo)
6. [x] Rect pocket box−box; PlaneSphere isect
7. [x] Side-hole +X; AABB box Union fuse (adjacent/overlap/contain)
8. [x] Side-hole +Y; demo_regen_all for fresh fixtures
9. [x] Box Intersection; ClassifyPoint (AABB/cyl/sphere); rect notch +X
10. [x] Pad boss stepped shell; kind-3 ClassifyPoint subtracts Z-holes
11. [~] Vertical box fillets = **demo debt only** (shape-specific; not product API)
12. [ ] **General `FilletEdge`:** plane–plane edge first (any faceted solid)
13. [ ] Plane–cyl / plane–cone edge blend; vertex sphere; then chamfer strip
14. [ ] General B-Rep cut / shell hollow
15. [ ] Sketch_0 / extrude / revolve (**after** blend spine)
16. [ ] Viewport/Vulkan **after** tess emits real buffers

**Priority (2026-08):** solid modelling geometry before sketch.

**Fillet policy — no shape recipes.** Do not add top-rim-of-box / cone-bottom /
triangle-only builders. Implement **edge-based** blend: offset supports → isect
spine → blend face → topology edit. Domain grows by **surface pair type**
(plane–plane → plane–cyl → plane–cone → …), not by solid kind. Unsupported
edge returns **0**, never an empty solid.

---

## 8. Related docs

| Doc | Role |
|-----|------|
| `Docs/CAD/CAD_PROGRESS.md` | **Living plan + turn log** (update every grind turn) |
| `Docs/CAD/CAD_Kernel_Design_v3.md` | Normative architecture & contracts |
| `Docs/CAD/plane_coordinate_tree_spec.md` | Workplane / plane feature tree |
| `Docs/CAD/notes/*` | Historical; not binding |
| `Librarys/Cad/*` | Implementation |
| `CAD/test_*.ailang` | Phase gates (to be made real) |

**Grind rule:** update `CAD_PROGRESS.md`, run gates, **local commit** each turn (CAD paths only).
