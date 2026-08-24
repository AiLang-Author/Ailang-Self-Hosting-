# File-size prune (do tomorrow — careful)

Target: **keep `.ailang` files under ~1500 LOC.**  
AILang imports just inline the file. No headers, no Python circular-import tax. Moving a `Function.*` to a sibling module is a cut/paste + `LibraryImport` if needed.

## Rules for the pass

- **Do not insert fields in the middle of `FixedPool.CadApp`.** That shifted `hover_face` / `pick_*` and broke Sketch-on-Face on the cylinder cap (2026-08-15). New save/load counters live in `FixedPool.CadAppRepo` (append-only, own pool).
- Append new CadApp fields only at the **end**, or add a **new tiny pool**.
- One concern per file. Compile `cad_app.x` after each move. Retest: box pad → circle pad → Sketch on Face on the **cylinder top**.

## App files over 1500 (CAD/App)

Split 2026-08-23 via `python3 tools/cad_split_ailang.py`. Callers still
`Import.CAD.App.Tools` etc. Revert: `CAD/App/*.ailang.pre_split`.

| Facade | Parts (all <1000) |
|--------|-------------------|
| Tools.ailang | Snap / Cstr / Click / Hud / Edit / Poly |
| Draw.ailang | Cam / Sketch / View3 / Hud |
| Solid.ailang | Wire / Prof / Blend / Pad |
| State.ailang | Pools (`CadApp`) / Hud / Tree |
| Plane.ailang | Reg / Pick / Tree |
| Doc.ailang | Hist / List / Repo |

`CA_PollCmd` split 2026-08-23: `Branch` on first byte → `CA_IpcCmd*` helpers
(`IpcNav` / `IpcP` / `IpcT` / `IpcS` / `IpcC` / `IpcF` / `IpcMisc` / `IpcDispatch`).
`click` stays in dispatch (would collide with `cstr`/`clear`). `Fork` used for orbit/hover log skip.

`CadApp` pool itself is ~220 lines / 161 fields — **do not prune the field list.**
Do not insert fields in the middle of `FixedPool.CadApp`.

## Library files over 1500 (Librarys/Cad) — 2026-08-16

| File | LOC | Suggested cut |
|------|----:|---------------|
| Library.CAD_Topo.ailang | **facade** | Split 2026-08-16, then 2026-08-23: FilletVertex / FilletSeq / QueryWalk / MakeLathe. `FilletUnused` parked, not imported. Callers still `LibraryImport.Cad.CAD_Topo`. |
| Library.CAD_Tess.ailang | **facade** | Split into `Librarys/Cad/Tess/` (7 files). |
| Library.CAD_SketchProfile.ailang | **facade** | Loop / Tess / Snap. |
| Library.CAD_Sketch.ailang | **facade** (~482) | Pools+CRUD here; `CAD_SketchCstr` + `CAD_SketchGeom` imported after the pools. |

**Do not split Topo as a drive-by.** 13k is a dedicated session: named helpers + pinned pool fields, compile after each move. Tess next (4.5k). Issue #1 (rect+octagon → broken plate) was **not** Topo — it was pad “inside = hole” in `CAD/App/Solid.ailang` (2181) + `CAD_Feat.ExtrudeProfile`. Killed 2026-08-16: each selected ring is a planar prism; extras compound. `MakePolyPrismHoles` unused on pad.

Topo is still the dangerous one: `RebuildKind0Planes` already smashed analytic caps when a local `skipf` died.

## Capacity (2026-08-15)

Document lists were 16 sketches / 16 planes / 32 feats. Raised to **64 / 64 / 128**.  
`CAD_Store.Init` is **1M slots (~288 MB)**, zeroed with **`MemorySet` (SSE2 memset)** — not `MemoryCopy` and not a per-word WStore loop. Init failure falls back to 256k. Walk guards (512 faces, 64 shells) stay as infinite-loop brakes.

## Parked (unrelated)

B5 real Difference; fused join fillet; glue kind-1 cyl sitting-face; x-ray pick; assemblies; Measure/Surface; kernel Move.
