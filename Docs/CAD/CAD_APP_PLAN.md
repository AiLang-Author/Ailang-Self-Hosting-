# CAD Working App Plan — Real-time DXF / Geometry Loops

**Status:** plan + **M-B implemented** (2026-08-07)  
**Goal:** See and edit DXF + solids in a **hosted window** for fast test loops.  
**Headless BMP** = bootstrap / CI / agents only, not the daily path.  
**Pairs with:** `CAD_APP_PATH.md`, `CAD_CLI.md`, `CAD_OCC_CAPABILITY_AUDIT.md`.

### M-B shipped

| Piece | Path |
|-------|------|
| Buffer render | `CAD_View.RenderSolidToFB` / `WriteFBRaw` |
| App | `cad_app.x` / `CAD/cad_app.ailang` |
| Host presenter | `CAD/host/cad_host_x11` (X11 blit + keys → `/tmp/cad_app/cmd.txt`) |
| Headless gate | `./CAD/smoke_app.sh` |

```bash
# CI
./CAD/smoke_app.sh

# Window (DISPLAY required)
cc -O2 -o CAD/host/cad_host_x11 CAD/host/cad_host_x11.c -lX11
./ailang.x CAD/cad_app.ailang -o cad_app.x
./cad_app.x -i test-stl/test-dxf-files/cube.dxf -H 10
# keys in host: q r w 1 2 3 [ ] s b
```

---

## 0. Product requirements (locked)

| Need | Priority |
|------|----------|
| See geometry update when you change it | **P0** |
| See / edit DXF (or equivalent sketch IR) live | **P0** |
| Hosted OS window (normal desktop) | **P0** |
| Pad (extrude) and re-view without restart | **P0** |
| Headless BMP / `cad_view` | **P0 bootstrap** only |
| Left-drag orbit, scroll zoom | **P1** (after basic live loop) |
| Nav cube (FreeCAD / Fusion style) | **P1** (same tranche as orbit or just after) |
| AOS full window manager | **P2** (later presenter, same buffer API) |
| Full FreeCAD feature tree | out of scope for v1 app |

---

## 1. Architecture (buffer-centric, one draw path)

```text
┌──────────────────────────────────────────────────────────────┐
│  cad_app  (hosted process on Linux desktop)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │ Sketch UI   │  │ 3D viewport  │  │ Status / tools bar  │  │
│  │ (DXF IR)    │  │ + nav cube   │  │ Pad H, wire, refuse │  │
│  └──────┬──────┘  └──────▲───────┘  └──────────▲──────────┘  │
│         │                │                     │               │
│         ▼                │                     │               │
│  CAD_Sketch ──Extrude──► solid ──Tess──► pixel buffer          │
│         │                │              (HeadlessFB / ARGB)    │
│         │                │                     │               │
│         └──── export DXF/STEP ◄────────────────┘               │
│                              │                                 │
│                    Presenter: blit buffer → host window        │
└──────────────────────────────────────────────────────────────┘
```

**Rules**

1. Kernel **never** opens X11/Wayland/AOS. It fills an ARGB buffer + owns model.  
2. Presenter is swappable: headless→BMP, host window, later AOS surface.  
3. Live loop = edit model → rebuild solid (if needed) → remesh → redraw buffer → blit.  
4. Coarse software raster is OK for testing; polish later.

---

## 2. Modes of the window

Two panes (or tabbed views) in one window — both P0 for “see and edit DXF and geometry”:

| Mode | Content | Edits |
|------|---------|--------|
| **2D Sketch** | Current profile (from DXF load or drawn) | Add/move line/circle/arc, close loop, delete |
| **3D Solid** | Tess of last pad/cut result | View only until orbit/zoom (P1); tools: re-pad, export |

**Session state**

```text
document {
  sketch_handle      // CAD_Sketch IR (source of truth for profile)
  solid_handle       // 0 until pad succeeds
  height_mm
  dirty_sketch       // needs re-pad for solid to match
  view { yaw, pitch, dist, pan_x, pan_y, mode }  // mode: free/iso/top/front
  wire, defl
  last_error_string  // refuse reasons from Feat/Blend
}
```

---

## 3. Implementation phases

### Phase A — Bootstrap (already mostly done)

| Item | Status | Deliverable |
|------|--------|-------------|
| DXF → solid → STEP | done | `cad_load` |
| DXF → solid → HeadlessFB → BMP | done | `cad_view` |
| Optional host image open | done | `--show` / eog |

**Exit:** CI and agents stay on this path forever.

---

### Phase B — Hosted window + live solid view (first real app)

**Binary:** `cad_app.x` (or `cad_app` host launcher + AILang core).

| Step | What | Notes |
|------|------|--------|
| B1 | Presenter: SDL2 or GLFW window, blit ARGB from HeadlessFB each frame | Prefer SDL2 for input later |
| B2 | Load DXF on launch (`-i`) or empty sketch | Reuse `CAD_DXF` / `LoadDXFExtrude` path |
| B3 | Pad with `-H` / key `[` `]` height, redraw solid | No orbit yet: fixed iso (current `CAD_View`) |
| B4 | Keys: `R` re-pad, `W` wire, `1/2/3` view presets, `S` STEP, `B` BMP, `Q` quit | Status line: face count / error |
| B5 | Auto-reload DXF file if mtime changes (optional, great for FreeCAD-side edit loops) | External edit → live solid |

**Exit criteria**

- Open window, see solid from DXF, change height, re-pad, still seeing updates **without restart**.  
- Export STEP from the running app.  
- Headless `cad_view` still green.

**Out of B:** sketch drawing, orbit, nav cube.

---

### Phase C — Live DXF / sketch edit (core testing loop)

| Step | What | Notes |
|------|------|--------|
| C1 | 2D canvas overlay (or split): project sketch XY to screen | Ortho top for sketch mode |
| C2 | Tools: line, rect, circle (click-click or drag) | Write into `CAD_Sketch` |
| C3 | Select + delete entity; snap to endpoint (grid later) | |
| C4 | **Apply pad** on Enter / button → rebuild solid → 3D pane | `dirty_sketch` clear |
| C5 | Export sketch DXF + import replace | Round-trip for external tools |
| C6 | Overlay sketch edges on 3D when solid exists (optional) | |

**Exit criteria**

- Draw a rectangle, pad, see solid; add a pocket profile path later.  
- Edit a line, re-pad, solid updates.  
- This is the **primary internal test harness** for sketch/extrude bugs.

---

### Phase D — Navigation (P1, after C works)

| Step | What | Behavior |
|------|------|----------|
| D1 | View state: yaw/pitch/distance/pan | Replace fixed `view_mode` matrix in `CAD_View` |
| D2 | **LMB drag** → orbit (rotate about model center) | FreeCAD-like |
| D3 | **Scroll** → zoom (change dist / ortho scale) | |
| D4 | **MMB drag** or Shift+LMB → pan | Optional same tranche |
| D5 | **Nav cube** (corner widget) | See §4 |
| D6 | Double-click cube face → snap iso/top/front/right | Animation optional |

**Exit criteria**

- Can orbit/zoom without re-running CLI.  
- Cube sets standard views; free orbit still works.

---

### Phase E — Modeling tools in-app (grow with kernel)

| Step | Tool | Kernel |
|------|------|--------|
| E1 | Pocket / hole | `ExtrudeCut`, `CreateHole` |
| E2 | Edge pick → fillet / chamfer | hit-test mesh edge → `FilletEdge` / `ChamferEdge` |
| E3 | Pattern / mirror | existing Feat APIs |
| E4 | Feature list / undo | later; not required for test loops |

Kernel expands **only when the app hits a wall**.

---

## 4. Nav cube (spec)

**Placement:** top-right of 3D viewport, ~80–100 px, always screen-aligned after camera.

**Look**

```text
        [Top]
   [L] [Front] [R]
        [Bot]
   + small iso corners (optional v2)
```

**Hit regions**

| Region | Action |
|--------|--------|
| Face: Top / Bottom / Front / Back / Left / Right | Set view to that ortho |
| Corner tri (optional) | Set nearest iso |
| Drag on cube | Same as orbit (optional) |

**Implementation**

- Pure 2D UI in screen space (not part of B-Rep).  
- Drawn **after** solid into same ARGB buffer (or second overlay buffer composite).  
- Cube orientation: rotate face labels with camera yaw/pitch so it matches FreeCAD “which way is up”.

**Data**

```text
nav_cube {
  size_px, margin_px
  faces[6] { label, view_yaw, view_pitch }
  hover_face  // for highlight
}
```

---

## 5. Camera / input map (Phase D)

| Input | Action |
|-------|--------|
| LMB drag | Orbit (yaw/pitch) |
| Scroll | Zoom |
| MMB drag or Shift+LMB | Pan |
| Click nav cube face | Snap view |
| Keys `1` `2` `3` | Iso / top / front (keep forever) |
| `F` | Fit all (AABB of solid or sketch) |

**Orbit math (simple)**

- Trackball or yaw/pitch about solid AABB center.  
- Rebuild projection each frame; re-raster mesh (software).  
- Performance: ok for ~10k tris; if slow, lower defl or dirty-flag mesh only when model changes, reproject verts when only camera moves.

**Optimization split**

| Event | Remesh solid? | Reproject? | Redraw? |
|-------|---------------|------------|---------|
| Orbit / zoom / pan | no | yes | yes |
| Pad / sketch apply | yes | yes | yes |
| Wire toggle | no | no | yes |

---

## 6. Process / packaging

### Preferred layout

```text
CAD/
  cad_app.ailang          # model + tools + raster (AILang)
  host/
    cad_host_sdl.c        # OR thin SDL main: create window, poll events,
                          # call into shared buffer / IPC
```

**Two viable packaging options**

| Option | How | When |
|--------|-----|------|
| **A. Single AILang binary + SDL via syscalls/FFI later** | Harder if no SDL bindings | If/when AILang has easy C lib link |
| **B. Thin C host + AILang as library/subprocess** | Host owns window; AILang renders buffer to shm/file | **Default for M1** if linking is painful |
| **C. AILang renders; host only displays BMP sequence** | Too slow | Reject for live edit |

**Recommendation:** start **B** if SDL can’t link cleanly into AILang tomorrow; target **A** when linker story is easy. Same buffer contract either way.

### Headless flag

```bash
./cad_app --headless --in x.dxf --shot out.bmp -H 10   # CI
./cad_app --in x.dxf -H 10                             # window
```

---

## 7. File formats in the app

| Asset | Format | Notes |
|-------|--------|--------|
| Profile | DXF (LINE/CIRCLE/ARC/LWPOLY) | Load/save sketch |
| Solid | STEP out | Primary interchange |
| Screenshot | BMP | Debug / agent |
| Project | deferred | Later: sketch + height + view JSON |

---

## 8. Testing strategy

| Layer | Gate |
|-------|------|
| Kernel | existing `smoke_*.sh` unchanged |
| App headless | `cad_app --headless ...` same face counts as demos |
| App interactive | manual checklist (below) + optional screenshot diff |

**Manual checklist (Phase B)**

1. Launch with `test-dxf-files` square → see solid  
2. Change height → solid updates  
3. Export STEP → opens in FreeCAD  
4. Quit clean  

**Manual checklist (Phase C)**

1. Draw rect → pad → solid  
2. Move corner → re-pad → solid matches  
3. Save DXF → reload  

**Manual checklist (Phase D)**

1. Orbit LMB, zoom scroll  
2. Cube Top / Front snaps  
3. Fit `F`

---

## 9. Milestone schedule (effort order, not calendar)

| Milestone | Delivers | Depends |
|-----------|----------|---------|
| **M-B** Hosted window + live pad from DXF | Daily “see solid” loop | Phase B |
| **M-C** Sketch edit in window | Daily “edit DXF IR” loop | M-B |
| **M-D** Orbit + zoom + nav cube | Comfortable navigation | M-B (can parallel after B3) |
| **M-E** Pocket / fillet pick | Real modeling stress | M-C + kernel |

**Suggested build order inside first sprint**

1. Buffer API extract from `CAD_View` (`RenderSolidToBuffer`)  
2. Host window blit loop  
3. DXF load + pad + keys  
4. Sketch draw (C) **before** investing heavy nav polish  
5. Orbit + nav cube (D)

Reason: **edit loop > fancy camera**. Nav without edit still needs CLI re-runs for geometry changes.

---

## 10. Explicit non-goals (v1 app)

- AOS desktop integration  
- Constraint solver / fully constrained sketches  
- General OCCT-class boolean  
- Multi-body assembly UI  
- Photoreal materials  

---

## 11. Open decisions (resolve at implement start)

| Decision | Options | Lean |
|----------|---------|------|
| Host toolkit | SDL2 vs GLFW vs raw X11 | **SDL2** (input + window) |
| Process model | mono vs host+core | **host+buffer** until link is easy |
| Sketch UI | split pane vs mode toggle | **mode toggle** (simpler layout) |
| Nav cube | Phase D1 with orbit vs after orbit | **with orbit** same PR if small |

---

## 12. Success definition

You can sit at a normal Linux desktop, **draw or load a profile, pad it, see it update, orbit it, hit a cube face for top view, export STEP**, and use that loop to find kernel bugs—without FreeCAD and without AOS.

Headless remains the gate for agents and CI.
