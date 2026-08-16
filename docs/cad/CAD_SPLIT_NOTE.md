# File-size prune (do tomorrow — careful)

Target: **keep `.ailang` files under ~1500 LOC.**  
AILang imports just inline the file. No headers, no Python circular-import tax. Moving a `Function.*` to a sibling module is a cut/paste + `LibraryImport` if needed.

## Rules for the pass

- **Do not insert fields in the middle of `FixedPool.CadApp`.** That shifted `hover_face` / `pick_*` and broke Sketch-on-Face on the cylinder cap (2026-08-15). New save/load counters live in `FixedPool.CadAppRepo` (append-only, own pool).
- Append new CadApp fields only at the **end**, or add a **new tiny pool**.
- One concern per file. Compile `cad_app.x` after each move. Retest: box pad → circle pad → Sketch on Face on the **cylinder top**.

## App files over 1500 (CAD/App)

| File | LOC | Suggested cut |
|------|----:|---------------|
| Tools.ailang | 3671 | click/hover vs HUD vs rect/circ/poly edit |
| Draw.ailang | 2592 | 2D sketch vs 3D/publish |
| Solid.ailang | 2168 | edge-sel/blend vs pad/revolve |
| State.ailang | 1968 | keep pools; move WriteHud/Tree/Status |
| Ipc.ailang | 1961 | parse vs command table |
| Plane.ailang | 1934 | pick vs plane-tree |
| Doc.ailang | 1681 | hist vs repo save/load |

`CadApp` pool itself is ~220 lines / 161 fields — **do not prune the field list.**

## Library files over 1500 (Librarys/Cad) — 2026-08-16

| File | LOC | Suggested cut |
|------|----:|---------------|
| Library.CAD_Topo.ailang | **12971** | Make* vs bool-support vs Rebuild/map vs FaceGet* |
| Library.CAD_Tess.ailang | **4519** | earclip vs cyl/annulus vs collect |
| Library.CAD_SketchProfile.ailang | 2185 | tessellate vs BuildAllClosedLoops vs weld |
| Library.CAD_Sketch.ailang | 1666 | create/add vs query vs constraints |

**Do not split Topo as a drive-by.** 13k is a dedicated session: named helpers + pinned pool fields, compile after each move. Tess next (4.5k). Issue #1 (rect+octagon → broken plate) was **not** Topo — it was pad “inside = hole” in `CAD/App/Solid.ailang` (2181) + `CAD_Feat.ExtrudeProfile`. Killed 2026-08-16: each selected ring is a planar prism; extras compound. `MakePolyPrismHoles` unused on pad.

Topo is still the dangerous one: `RebuildKind0Planes` already smashed analytic caps when a local `skipf` died.

## Capacity (2026-08-15)

Document lists were 16 sketches / 16 planes / 32 feats. Raised to **64 / 64 / 128**.  
`CAD_Store.Init` is **1M slots (~288 MB)**, zeroed with **`MemorySet` (SSE2 memset)** — not `MemoryCopy` and not a per-word WStore loop. Init failure falls back to 256k. Walk guards (512 faces, 64 shells) stay as infinite-loop brakes.

## Parked (unrelated)

B5 real Difference; fused join fillet; glue kind-1 cyl sitting-face; x-ray pick; assemblies; Measure/Surface; kernel Move.
