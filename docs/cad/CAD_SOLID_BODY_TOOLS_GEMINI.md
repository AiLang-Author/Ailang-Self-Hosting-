# Solid body tools — brief for Gemini / host UI agents

**Date:** 2026-08-13  
**Audience:** UI host implementer (Gtk / FLTK / custom chrome)  
**You do:** chrome for body modify tools (fillet, chamfer, params)  
**You do not:** reimplement BREP, tess, or shade — only IPC  

**Parent specs:** `CAD_HOST_UI_BUILDER.md` (IPC contract), `CAD_UI_PLAN.md` v3  

---

## 0. Why this exists

Sketch → pad pipeline is dogfooded. Solids look good (see `CAD/screenshots/wouldyoujustlookatit.png`).  
Next stress path is **modify the body**: fillet, chamfer, later edge-pick / draft / shell.

Kernel already has blend ops (`CAD_Blend.Fillet*`, `Chamfer*`). App IPC is wired:

| Cmd | Kernel | Meaning |
|-----|--------|---------|
| `fillet` / `fillet 5` | `CA_FilletSolid(Rmm)` | Round **all** collectable edges (fallback: first edge) |
| `chamfer` / `chamfer 2` | `CA_ChamferSolid(Dmm)` | Equal setback on edges (kernel limits apply) |

**Not the same as** sketch `tool_fillet` (2-line corner fillet in 2D).

---

## 1. Mental model

```text
User has solid (mode=0 3D, CadApp.solid ≠ 0)
    ↓ host toolbar / ribbon
write_cmd("fillet 5")   or  "chamfer 2"
    ↓ kernel
collect edges → CAD_Blend → new solid → PublishFrame
    ↓ host
blit frame.raw (gen.txt bumps)
```

**v1.1 edge pick (in kernel now):**

1. Host sends `tool_fillet` while a solid is active (3D).  
2. User **LMB clicks** an edge → kernel highlights cyan/yellow.  
3. Second click **or** `fillet 5` applies `CAD_Blend.FilletEdge` on `sel_edge_id`.

Host still **never** sends edge handles. Only clicks + `fillet [R]`.

---

## 2. UI requirements (do this)

### 2.1 SOLID / Modify ribbon section

Add a **Solid** (or **Modify**) toolbar **only active when 3D has a solid** (optional: grey out when no body).

Suggested tools (ids/cmds fixed — match PG `tools.json`):

| id | Label | Default `cmd` | Variants (split button / menu) |
|----|-------|---------------|--------------------------------|
| `fillet3d` | Fillet Body | `fillet 5` | `fillet 2`, `fillet 5`, `fillet 10` |
| `chamfer3d` | Chamfer Body | `chamfer 2` | `chamfer 1`, `chamfer 2`, `chamfer 5` |

Optional spinbox / dialog:

- Fillet: integer R mm → write `fillet {R}`  
- Chamfer: integer D mm → write `chamfer {D}`  

Use **exact** cmd strings; do not invent `solid_fillet` / `body.fillet`.

### 2.2 Catalog source of truth

1. Prefer live `$CAD_APP_STATE/tools.json` from kernel (PG `cad_ui_catalog`).  
2. After SQL update: operator runs `psql -d cad_db -f CAD/sql/cad_ui_catalog.sql` then host/kernel `tools` cmd.  
3. Gtk fallback embeds the same SOLID tools (see `cad_shell_gtk.py` load_tools fallback).

### 2.3 Mode / enable rules

| State | Fillet/Chamfer buttons |
|-------|------------------------|
| Sketch mode, no solid | Disabled or no-op (kernel logs “needs active 3D solid”) |
| 3D + solid present | Enabled |
| After success | Stay in 3D; frame refreshes |

Read `tool.txt` field `mode` (0=3D, 1=sketch). Solid existence: optional parse of `status.txt` / always try cmd (kernel validates).

### 2.4 Visual chrome (nice)

- Group under ribbon tab **SOLID** next to Extrude / Revolve / Cut.  
- Icons: rounded corner (fillet), bevel (chamfer).  
- Tooltip: “Round body edges (R mm)” / “Chamfer body edges (D mm)”.  
- Status bar: leave kernel log; optional toast “Fillet R=5 applied” when gen bumps after cmd.

### 2.5 Do **not**

- Draw edges yourself or highlight mesh in OpenGL.  
- Call FreeCAD / OCC.  
- Add host-side BREP.  
- Confuse with sketch **Fillet 2D** (`tool_fillet`).

---

## 3. Acceptance checklist

- [ ] After pad of a simple box/rect, **Fillet Body R=5** produces rounded edges in `frame.raw` (or kernel log “3D solid fillet OK”).  
- [ ] **Chamfer Body D=2** on a box changes silhouette.  
- [ ] No solid: button either disabled or log “fillet needs active 3D solid” without crash.  
- [ ] Cmd only from `tools.json` / this table.  
- [ ] Sketch fillet still works via `tool_fillet` (separate tool).  
- [ ] Orbit/zoom still only blit + orbit/zoom cmds.

Golden visual refs (stress solids):  
`CAD/screenshots/wouldyoujustlookatit.png`, `clean.png`.

---

## 4. Kernel limits (set expectations)

| Capability | Status |
|------------|--------|
| Fillet plane–plane edges on kind-0 poly prisms | Yes (`FilletEdges` / `FilletPlanePlaneEdge`) |
| Fillet cylinder rims (analytic kind-1) | Yes (dedicated paths) |
| Chamfer vertical / box horizontal edges | Partial (see demos) |
| Pick single edge in UI | **Not yet** — v1 is “all edges / best effort” |
| Variable-R fillet from UI | Kernel API exists; no IPC param pack yet |
| Undo stack | Not productized — New Doc / re-pad |

If fillet fails on a Mickey-keyhole solid: kernel log `3D solid fillet FAIL` — geometry may be outside blend support; not a host bug.

---

## 5. Future (do not block v1)

1. **Edge pick in 3D:** kernel hit-test edge under `click x y` → `fillet_edge <id> <R>`. Host: highlight via kernel overlay only.  
2. **Inspector spinbox** bound to `defaults.fillet_r` from tools.json.  
3. **Draft / shell / thickness** when kernel cmds exist.  
4. Feature tree browser (PG `feature_tree`) — separate brief.

---

## 6. Operator apply (for humans, not Gemini)

```bash
# catalog
psql -d cad_db -f CAD/sql/cad_ui_catalog.sql

# rebuild kernel if Solid/Ipc changed
./ailang.x CAD/cad_app.ailang -o cad_app.x

# session
./CAD/scripts/run_cad_app.sh
# in host: tools  → reload tools.json
# pad a body, then: fillet 5
```

---

## 7. Cmd cheat sheet (host write to cmd.txt)

```text
fillet          # R=5 default
fillet 2
fillet 10
chamfer
chamfer 1
chamfer 5
tool_fillet     # SKETCH 2D only — not body
repad           # rebuild pad from profile
mode            # 2D/3D toggle
wire            # wireframe toggle
```

**End of brief.** Chrome only; kernel owns geometry.
