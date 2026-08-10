# Path to a working CAD application

**Superseded in detail by:** `CAD_APP_PLAN.md` (real-time DXF/geometry, hosted window, nav cube).  
**This file:** short jump map.

---

## Goal

See and edit **DXF + geometry in real time** for test loops.  
Headless BMP = bootstrap/CI. Hosted window = daily path.

---

## Architecture (one line)

Kernel fills an ARGB buffer; host window blits it. AOS is a later presenter.

---

## Milestones

| ID | Deliverable |
|----|-------------|
| **M-B** | Hosted window, load DXF, pad, live redraw, export STEP | **done** |
| **M-C** | In-window sketch edit → re-pad | **done** |
| **M-D** | LMB orbit, scroll zoom, **nav cube** | **done** |
| **DXF→solid** | Pad, multi-loop holes, plate+hole pair, live cut/reload | **done** |
| **M-C2** | Multi-circle/arc profile, FreeCAD-style trim, dense prism pad | **done** 2026-08-08 |
| **Repo** | Postgres SoR (orthogonal doc/rev/asset via PostgreSQL_Complete) | **v2 done** |
| **M-E** | **Revolve UI** + pad confirm + more feature tools | **next** |
| **Planes / naming** | Plane tree + persistent face map assets | later |

---

## Input (target)

| Input | Action | When |
|-------|--------|------|
| LMB drag | Orbit | M-D |
| Scroll | Zoom | M-D |
| Nav cube faces | Snap ortho/iso | M-D |
| Sketch tools | Line/rect/circle/arc/trim/pick | M-C / M-C2 |
| Scroll (sketch) | Zoom sketch plane | M-C2 |
| Hold LMB + drag (sketch) | Pan sketch | M-C2 |
| Profiles / Pad | Project closed faces; extrude selection | M-C2 |
| Keys | Height, wire, re-pad, export | M-B |

---

## Bootstrap + live viewport

```bash
# CI / agents only (no window)
./CAD/smoke_app.sh

# DAILY: real viewport window (recommended — handles DISPLAY/XWayland)
./CAD/scripts/run_cad_app.sh
./CAD/scripts/run_cad_app.sh -i test-stl/test-dxf-files/diamond.dxf -H 15

# Plate + through hole from two DXFs
./CAD/scripts/run_cad_app.sh \
  -i test-stl/test-dxf-files/escutcheon_plate.dxf \
  --hole test-stl/test-dxf-files/keyhole_flared.dxf -H 4

# Multi closed loops in one DXF → outer pad + holes
./CAD/scripts/run_cad_app.sh -i test-stl/test-dxf-files/lwpoly_plate_hole.dxf -H 5
```

`run_cad_app.sh` starts the X11 host **first** with your shell env, then `cad_app --nohost`.  
Do **not** rely on bare `./cad_app.x` for a window (it can strip `DISPLAY` on spawn).

### DXF → solid ops (in window)

| Key / flag | Action |
|------------|--------|
| `-i` / `--in` | Plate / profile DXF |
| `-k` / `--hole` | Optional hole DXF (through cut) |
| `-H` | Thickness / pad height mm |
| `r` | Rebuild pad / plate+hole |
| `u` | ExtrudeCut sketch (or hole) into solid |
| `o` | Reload DXF paths from disk |
| `s` / `b` / `x` | Export STEP / BMP / sketch DXF |

### Postgres document store (CAD_Repo)

Uses **`Library.PostgreSQL_Complete`**. Model is **orthogonal** (see `CAD_REPO.md`):

- `cad_document` / `cad_revision` / `cad_asset` (role-tagged, not fixed columns)
- Authoritative: `profile_dxf` asset (+ optional `hole_dxf`)
- Derived: `step_cache`
- New features later = new roles / JSON keys (`plane_tree`, `face_map`, …)

```bash
createdb cad_db
psql -d cad_db -f CAD/sql/cad_schema.sql

./cad_app.x --headless -i diamond.dxf -H 15 --name mypart --save
./cad_app.x --headless --load --name mypart -o out.bmp
./CAD/scripts/run_cad_app.sh -i diamond.dxf -H 15 --name mypart   # p=save g=load
```

---

## Next

1. Part list + revision browser in the host UI  
2. **Planes** (`plane_coordinate_tree_spec.md`) as `plane_tree` assets  
3. **Persistent topo naming** (`face_map` + `CAD_Feat.ResolveNaming`)  
4. M-E edge tools writing into feature_tree JSON
