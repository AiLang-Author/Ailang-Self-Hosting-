# CAD Kernel — Development Guide

**Status:** living process doc (pairs with `CAD_Kernel_Design_v3.md` v3.1)  
**Last updated:** 2026-08-04

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
| Interchange | STEP / STL / DXF only |
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
│  Neutral files: STEP, STL, DXF                          │
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

**Coding note — raw memory**

- `ArrayGet`/`ArraySet` use offset `index*8+8` (array object header).
- Kernel slabs and bulk tables must use `StoreValue(addr, v)` / `Dereference(addr)`
  with `addr = base + word_index*8`.

**Next**

1. [ ] Analytic `CAD_Geom` (eval + d1 + project) on Store-backed records
2. [ ] Real NURBS curve eval (Cox–de Boor)
3. [ ] Linked `CAD_Topo` + Euler
4. [ ] Fixtures dir layout
5. [ ] Viewport/Vulkan **after** tess emits real buffers

---

## 8. Related docs

| Doc | Role |
|-----|------|
| `Docs/CAD/CAD_Kernel_Design_v3.md` | Normative architecture & contracts |
| `Docs/CAD/plane_coordinate_tree_spec.md` | Workplane / plane feature tree |
| `Docs/CAD/notes/*` | Historical; not binding |
| `Librarys/Cad/*` | Implementation |
| `CAD/test_*.ailang` | Phase gates (to be made real) |
