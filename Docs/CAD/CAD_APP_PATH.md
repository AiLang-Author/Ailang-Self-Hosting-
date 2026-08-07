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
| **M-D** | LMB orbit, scroll zoom, **nav cube** | next |
| **M-E** | Pocket / edge fillet-chamfer pick | later |

---

## Input (target)

| Input | Action | When |
|-------|--------|------|
| LMB drag | Orbit | M-D |
| Scroll | Zoom | M-D |
| Nav cube faces | Snap ortho/iso | M-D |
| Sketch tools | Line/rect/circle | M-C |
| Keys | Height, wire, re-pad, export | M-B |

---

## Bootstrap + M-B

```bash
./cad_load.x --in profile.dxf --out out.stp -H 10
./cad_view.x --in profile.dxf --shot out.bmp -H 10 --show

# live app (headless CI)
./CAD/smoke_app.sh

# live app (window)
cc -O2 -o CAD/host/cad_host_x11 CAD/host/cad_host_x11.c -lX11
./ailang.x CAD/cad_app.ailang -o cad_app.x
./cad_app.x -i test-stl/test-dxf-files/cube.dxf -H 10
```

---

## Next

**M-D** orbit + scroll zoom + nav cube (see `CAD_APP_PLAN.md`).
