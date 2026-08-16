# CAD UI Plan v3 — IPC chrome + PG JSON catalog

**Status:** locked 2026-08-13 (v3)  
**Replaces:** UI plan v1 (FLTK-as-product-shell), soft-optional PG notes  
**Pairs with:** `CAD_REPO.md`, `CAD_APP_PLAN.md`, `CAD_Kernel_Design_v3.md` (engine only)  
**UI implementers (Gemini / Fable / external):** use **`CAD_HOST_UI_BUILDER.md`** — full coding brief (IPC, pixels, tools.json, acceptance).  
**Read time (this file):** ~8–10 min @ 250 wpm

---

## 0. One-page architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Host chrome (compiled Gtk3; AOS later)     DISPOSABLE      │
│  • menus / toolbars from tools.json                         │
│  • blits frame.raw                                          │
│  • writes cmd.txt                                           │
└────────────────────────────▲────────────────────────────────┘
                             │ IPC only (pixel + cmd + JSON)
┌────────────────────────────┴────────────────────────────────┐
│  cad_app.x (AILang)   PERMANENT                             │
│  sketch · pad · tess · shade · pick · docs                  │
│  never links Gtk/Qt/FLTK/X11/Wayland                        │
└────────────────────────────▲────────────────────────────────┘
                             │ always
┌────────────────────────────┴────────────────────────────────┐
│  PostgreSQL (hard dependency)                               │
│  docs/revs/assets + cad_ui_catalog (JSONB tool chrome)      │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Owns | Does not own |
|-------|------|----------------|
| **Kernel** | Geometry, FB pixels, cmd execution, PG connect, emit `tools.json` | Button layout, docking, themes |
| **Host** | Chrome layout, file dialogs, blit, input | Tess, BREP, shade math, inventing tool cmds |
| **PG** | SoR + UI catalog JSON | Pixels |

**Rules (do not break)**

1. Kernel **never** links a windowing toolkit.  
2. Host **only** blits the pixel stream and sends IPC cmds.  
3. **PostgreSQL is required** — no offline CAD product path (one code path).  
4. Tool **cmds** are owned by `Library.CAD_UI` (kernel writes `tools.json`). PG seed is optional sync.  
5. AOS later = another host on the **same contract**.  
6. Host **Quit** writes `quit`; kernel runs `CA_Shutdown`.

Aligned with kernel design v3.1: no GUI in kernel; PG system of record; UI tables free with PG. Kernel design stops at mesh+CLI — **this doc owns the pixel/IPC host split.**

---

## 1. IPC contract (frozen)

Session dir: `CAD_APP_STATE` (default `/tmp/cad_app`).

| File | Direction | Role |
|------|-----------|------|
| `meta.bin` | K→H | `w,h,pitch` LE int32 |
| `frame.raw` | K→H | BGRA pixels |
| `gen.txt` | K→H | frame generation counter |
| `cmd.txt` | H→K | one command line; kernel clears after read |
| `tool.txt` | K→H | `mode tool nclick dirty …` |
| `status.txt` / `hud.txt` | K→H | human / structured status |
| **`tools.json`** | K→H | **UI catalog projection from PG** |
| `path.txt` | H→K | import path |
| `parts.txt` / `sel.txt` | K→H | repo list overlay |

### Cmd vocabulary (host writes exact `cmd` strings from JSON)

Sketch: `tool_line|rect|rectc|rect3|circ|circ2|circ3|arc|arc2|arc3|polyN|spline|point|trim|pick|fillet2d` · `profiles` · `done`  
Feature: `repad` · `revolve` · `cut` · `height N`  
Solid: `tool_fillet3d` · `fillet R` · `tool_chamfer` · `chamfer D`  
View: `mode` · `wire` · `grid` · `orbit` · `zoom` · `pan` · `iso` · `view0|1|2`  
Doc: `import` · `newdoc` · `name <part>` · `save` · `load` · `files` · **`quit`**  
Meta: `tools` → re-publish catalog from `CAD_UI`  

Input: `click x y [shift]` · `hover x y`

**Versioning:** `tools.json` has `"schema": 1`. Host ignores unknown fields; kernel adds fields only.

---

## 2. PostgreSQL hard dep + JSON catalog

### Why hard

Dual “works without PG” paths = two products. **Refuse.**  
If PG is down → `cad_app` exits with a clear error. Launcher may print how to `createdb cad_db`.

### Catalog storage (v3)

One row of JSONB — send JSON, boom done (matches product preference):

```sql
cad_ui_catalog (
  role     TEXT PRIMARY KEY,   -- e.g. 'default'
  catalog  JSONB NOT NULL,    -- full tools.json body
  updated_at TIMESTAMPTZ
)
```

Optional normalized tables (`cad_workbench` / `cad_toolbar` / `cad_tool`) can **project into** this JSON later; hosts never query SQL.

### JSON shape

```json
{
  "schema": 1,
  "app": "cad",
  "role": "default",
  "defaults": { "pad_h": 20, "shade": "solid", "wire": 0 },
  "toolbars": [
    {
      "id": "sketch",
      "label": "Sketch",
      "tools": [
        { "id": "line", "label": "Line", "cmd": "tool_line", "group": "draw" }
      ]
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `cmd` | Exact `cmd.txt` line host must write |
| `id` | Stable key (hotkeys, telemetry) |
| `label` | Display string (host may theme) |
| layout / icons / dock | **Host only** |

### Publish path

1. Kernel `ConnectLocal` (required).  
2. `InitSchema` + ensure `cad_ui_catalog` seed.  
3. `SELECT catalog::text …` → write `tools.json`.  
4. Cmd `tools` re-publishes.  

Host: parse JSON once (or on gen/tools change); build chrome; never hardcode tool lists as authority.

---

## 3. Presenter choice (v3)

| Presenter | Role | Status |
|-----------|------|--------|
| **`CAD/host/cad_shell_gtk` (C++ Gtk3)** | **Product shell** — blit, rubber-band, HUD, File menubar, Guest/login chrome | **current** |
| `cad_host_x11` + panel | Emergency blit only | `CAD_UI=x11` |
| AOS | Future host | same IPC |
| FLTK / Python Gtk | **Dropped** | do not build |

Launcher: `./CAD/scripts/run_cad_app.sh` → compiled Gtk. Close window / File→Quit / Ctrl+Q → `quit`.

File / Import-Export live on the top-left menubar (not a ribbon tab). The app starts as **Guest**; Log in is chrome-only until pgcrypto + capabilities land. Live grind: `CAD_UI_USABILITY.md`.

---

## 4. Viewport / shade (kernel side of glass)

- Kernel owns software raster (`CAD_View`: fill + Z + N·L; optional wire overlay).  
- Default product view: **shaded** (`wire=0`); `wire` cmd toggles fishnet.  
- Dense tri edges ≠ “missing mesher” — do not give host a GL path to “fix” that.  
- Tess quality / defl = kernel; host may only send cmds that change quality later.

---

## 5. Build order (v3)

| # | Item | Done when |
|---|------|-----------|
| 1 | This plan + `CAD_REPO` / app pointers | docs |
| 2 | `CAD/sql/cad_ui_catalog.sql` seed | `psql -f` ok |
| 3 | Kernel: hard PG connect, publish `tools.json`, cmd `tools` | file appears after start |
| 4 | Gtk shell reads `tools.json`, blits, sends cmds | draw/pad loop works |
| 5 | Launcher `CAD_UI=gtk` default when Gi present | one command run |
| 6 | Shade default solid; wire toggle | pads look solid |
| 7 | (Later) normalized workbench tables → catalog JSON rebuild | SQL only |

---

## 6. Non-goals

- Embedding Gtk/Qt/FLTK in `cad_app.x`  
- Offline CAD without PostgreSQL  
- Host re-rasterizing solids  
- Fusion-class docking product chrome  
- Rewriting `CAD_Kernel_Design_v3.md` into this file (use agent extracts when needed)

---

## 7. Success criteria

- Start app → PG required → `tools.json` written → Gtk toolbar matches catalog.  
- Click Line / Rect / Profiles / Pad via toolbar only (no memorized raw cmds).  
- Viewport is kernel pixels only.  
- Swap host without recompiling kernel.  
- Same contract works for agents (`cad_cmd.sh` + `cad_shot.sh`).

---

## 8. Kernel design v3.1 crosswalk (agent extract)

| Kernel design | UI plan v3 |
|---------------|------------|
| No GUI / no OpenGL in kernel | Host-only windowing |
| PG = SoR; Repo critical path | Hard dep; no `.cadx` fallback |
| UI config free with PG | `cad_ui_catalog` JSONB → `tools.json` |
| Tess = mesh cache, not pixels | Kernel raster still in `CAD_View` for app; design gap closed here |
| CLI `cadk` as product surface | Interactive path = IPC host; CLI remains |

---

## 9. License

SCSL v1.0 — Sean Collins / 2 Paws Machine and Engineering. See root `License.md`.
