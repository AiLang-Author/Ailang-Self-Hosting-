# CAD Host UI — Builder Spec (for Gemini / Fable / external UI agents)

**Audience:** UI implementers who will build a **desktop host shell** only.  
**Not your job:** CAD geometry, tessellation, shading math, PostgreSQL schema, AILang kernel.  
**Your job:** Beautiful chrome + correct **IPC** against a running `cad_app.x`.  
**Authority:** This file + live files under `$CAD_APP_STATE` (default `/tmp/cad_app`).  
**Architecture charter:** `docs/cad/CAD_UI_PLAN.md` (v3) — short product rules.  
**Do not read:** `CAD_Kernel_Design_v3.md` (kernel tome; irrelevant to chrome).

**Status:** 2026-08-13 · IPC schema 1  

---

## 0. Mental model (30 seconds)

```text
┌─────────────────────────────────────────┐
│  YOU BUILD THIS (any toolkit)           │
│  menus · toolbars · dialogs · theme     │
│  blit pixels · mouse/keyboard → cmds    │
└──────────────────┬──────────────────────┘
                   │  ONLY files / later socket
┌──────────────────▼──────────────────────┐
│  ALREADY EXISTS (do not rewrite)        │
│  cad_app.x — model + software renderer  │
│  writes frame.raw + tools.json + status │
└─────────────────────────────────────────┘
```

**Hard rules**

1. **Never** draw geometry yourself (no OpenGL mesh of the solid, no re-rasterize BREP).  
2. **Never** invent tool commands — only `cmd` strings from `tools.json`.  
3. **Never** link into or patch `cad_app.x` / AILang sources for chrome.  
4. Viewport = **texture blit** of `frame.raw` every time `gen.txt` changes.  
5. Input = **write one line** to `cmd.txt` (protocol below).  
6. Kernel owns PostgreSQL; you only **consume** `tools.json` (and optional `parts.txt`).

If you break (1)–(3), the product forks. Don’t.

---

## 1. How the product is run (integration)

Typical session (operator already has this):

```bash
# Terminal A — starts kernel + may start a placeholder host
./CAD/scripts/run_cad_app.sh
# or kernel only:
./cad_app.x --nohost .

# Terminal B — YOUR host (preferred during UI development)
export CAD_APP_STATE=/tmp/cad_app
./your_pretty_host
```

| Env | Meaning |
|-----|---------|
| `CAD_APP_STATE` | Session directory (default `/tmp/cad_app`) |
| `DISPLAY` | X11/XWayland (Linux dogfood) |

**Your binary/process** should:

1. Read `CAD_APP_STATE` (or argv).  
2. Poll / watch files in that dir.  
3. On window close send **`quit`** so the kernel can `CA_Shutdown` (do not leave cad_app.x running).

Reference hosts (ugly but correct):  
`CAD/host/cad_shell_gtk` (compiled Gtk3), `CAD/host/cad_host_x11.c`

---

## 2. IPC file contract (complete)

All paths relative to `$CAD_APP_STATE`.

### 2.1 Kernel → Host (read)

| File | Format | Purpose |
|------|--------|---------|
| `meta.bin` | 3× **little-endian int32**: `width`, `height`, `pitch` | Frame dimensions |
| `frame.raw` | `pitch * height` bytes, **BGRA** 8-bit/channel, row-major, `pitch` ≥ `width*4` | Viewport pixels |
| `gen.txt` | Decimal integer + newline | Frame generation; **increment ⇒ new image** |
| `tools.json` | UTF-8 JSON (`schema: 1`) | Toolbar / menu catalog |
| `status.txt` | One human line | Status bar text |
| `hud.txt` | `key=value` pairs, space-separated | Live params (tool, pad H, …) |
| `tool.txt` | Integers: `mode tool nclick dirty [cstr npick]` | Machine-readable mode |
| `parts.txt` | Newline-separated part names | Optional file list overlay |
| `sel.txt` | Integer index | Selected row in parts list |

### 2.2 Host → Kernel (write)

| File | Format | Purpose |
|------|--------|---------|
| `cmd.txt` | **One** command line + `\n` | Tools, clicks, orbit, … |
| `path.txt` | Absolute or relative filesystem path | Used by `import` |

### 2.3 `cmd.txt` write protocol (critical)

Kernel polls and **clears** `cmd.txt` after reading. Race-safe pattern:

```text
1. If cmd.txt non-empty (not only whitespace/newline), wait 2–5 ms and retry (max ~100–200 ms).
2. Write full command + "\n" (truncate/create).
3. Do not write a second command until cmd.txt is empty again (or wait).
```

**Never** append two commands without waiting for clear.  
**Never** leave partial writes.

### 2.4 Pixel format

```text
meta.bin:
  int32 width   // e.g. 800
  int32 height  // e.g. 600
  int32 pitch   // e.g. 3200 (= width * 4 for packed BGRA)

frame.raw:
  for y in 0..height-1:
    for x in 0..width-1:
      offset = y * pitch + x * 4
      B = data[offset+0]
      G = data[offset+1]
      R = data[offset+2]
      A = data[offset+3]   // often unused; treat as opaque
```

Convert to RGB/RGBA for your toolkit texture.  
**Letterbox** if window ≠ frame size: center blit; map mouse into frame coords (see §4).

### 2.5 Polling

| Signal | Action |
|--------|--------|
| `gen.txt` value changed | Reload `meta.bin` + `frame.raw`, upload texture |
| `tools.json` mtime changed | Rebuild toolbars/menus |
| `status.txt` / `hud.txt` | Refresh status / HUD labels |
| `tool.txt` | Update active tool highlight, rubber-band behavior |

60 Hz poll is fine; 20–30 Hz acceptable. File watches (inotify) optional.

---

## 3. `tools.json` schema (host chrome authority)

Kernel writes this from PostgreSQL. **You do not query SQL.**

### 3.1 Shape

```json
{
  "schema": 1,
  "app": "cad",
  "role": "default",
  "defaults": {
    "pad_h": 20,
    "shade": "solid",
    "wire": 0
  },
  "toolbars": [
    {
      "id": "sketch",
      "label": "Sketch",
      "tools": [
        {
          "id": "line",
          "label": "Line",
          "cmd": "tool_line",
          "group": "draw"
        }
      ]
    }
  ]
}
```

| Field | Required | Host behavior |
|-------|----------|----------------|
| `schema` | yes | If `>1` and unknown, show warning; still try best-effort |
| `toolbars[]` | yes | One ribbon group / toolbar / menu section each |
| `toolbars[].id` | yes | Stable key for layout prefs (your side) |
| `toolbars[].label` | yes | Section title |
| `tools[].id` | yes | Stable; icons / hotkeys map here |
| `tools[].label` | yes | Button text |
| `tools[].cmd` | yes | **Exact** string to write to `cmd.txt` |
| `tools[].group` | no | Optional visual subgroup |
| `defaults` | no | Seed UI spinboxes (pad height, etc.) |

**On tool button click:**

```text
write_cmd( tools[i].cmd )
```

Example: user clicks “Line” → write `tool_line\n` to `cmd.txt`.

**Do not** map labels to hardcoded enums. Labels may change; `cmd` is the contract.

### 3.2 Refresh

- On `tools.json` mtime change → rebuild chrome.  
- Optional menu item “Refresh tools” → write `tools\n` (kernel re-publishes from PG).

### 3.3 Fallback

If `tools.json` missing at startup: show “Waiting for kernel…” and empty toolbar; **do not** ship a second authority list except a tiny debug fallback clearly marked non-production.

---

## 4. Viewport interaction (must match kernel)

### 4.1 Coordinate spaces

```text
Widget pixel (mx, my) relative to viewport widget top-left
    ↓ subtract letterbox origin (ox, oy)
Frame pixel (fx, fy) in [0, width) × [0, height)
    ↓ written into commands
Kernel interprets frame pixels
```

```text
ox = max(0, (widget_w - frame_w) / 2)
oy = max(0, (widget_h - frame_h) / 2)
fx = mx - ox
fy = my - oy
```

Only send clicks/hovers when `0 ≤ fx < width` and `0 ≤ fy < height`.

### 4.2 Mode from `tool.txt`

```text
tool.txt fields (space-separated ints):
  mode   0 = 3D view,  1 = sketch (2D)
  tool   0=line 1=rect 2=circ 3=arc 4=pick 5=trim 6=point 7=cstr 8=fillet 9=arc3
  nclick in-progress click count for multi-click tools
  dirty  1 if sketch dirty
```

### 4.3 Mouse (match existing hosts)

| Mode | LMB drag | LMB click (no drag) | Scroll | RMB |
|------|----------|---------------------|--------|-----|
| **3D** (`mode=0`) | `orbit dx dy` (frame deltas) | `click fx fy` (nav cube / face pick) | `zoom 1` / `zoom -1` | optional `cancel` |
| **Sketch** (`mode=1`) | If hold ~0.8s then drag → `pan dx dy`; else hover `hover fx fy` for rubber-band | `click fx fy [shift]` | `zoom 1` / `zoom -1` | `cancel` |

**Sketch click rules (important):**

- One **press/release** = one `click` (do not click on drag start + release).  
- If user moved ≥3 px during press, use release position; else use press position.  
- **Shift** held at press → third arg `1` (multi-select profiles):  
  `click 400 300 1`  
- Without shift: `click 400 300` or `click 400 300 0`

**Orbit:** sum mouse deltas in frame space while LMB down in 3D; send e.g. `orbit 3 -2` each motion chunk.

### 4.4 Keyboard (optional but nice)

| Key | Suggested cmd |
|-----|----------------|
| Esc | `cancel` |
| M | `mode` |
| Delete / Backspace | (only if kernel supports; prefer toolbar) |
| Space | (avoid unless documented) |

Do not steal keys while typing in dialogs.

---

## 5. Command vocabulary (host may send)

Only send commands that either appear as `tools[].cmd` or are **input/navigation** below.

### 5.1 From `tools.json` (examples; catalog is authoritative)

```text
tool_line
tool_rect
tool_circ
tool_arc
tool_3pt
tool_point
tool_trim
tool_fillet          # sketch 2D corner fillet — NOT body
tool_pick
profiles
repad
revolve
cut
fillet [Rmm]         # solid body fillet (default R=5)
chamfer [Dmm]        # solid body chamfer (default D=2)
mode
wire
grid
newdoc
f                    # doc list (not fillet)
```

**Solid body tools brief:** `docs/cad/CAD_SOLID_BODY_TOOLS_GEMINI.md`

### 5.2 Navigation / input (host-generated)

```text
click <fx> <fy> [shift]
hover <fx> <fy>
orbit <dx> <dy>
zoom <steps>          # positive in, negative out
pan <dx> <dy>
cancel
```

### 5.3 Optional extras (if you build dialogs)

```text
height <mm>
h <mm>
import                 # after writing path.txt
tools                  # re-publish tools.json
plane_xy | plane_xz | plane_yz | plane_top
plane_off <mm>
wire
grid
grid 0
grid 1
shot
```

**File open flow:**

```text
1. Native open dialog → absolute path
2. Write path to path.txt (full string, no newline issues)
3. write_cmd("import")
```

---

## 6. Status / HUD display

### 6.1 `status.txt`

Single line. Put in a status bar at bottom. Examples:

```text
DOC untitled r0 brightRED Shift+multi
SKETCH empty
```

### 6.2 `hud.txt`

Space-separated `key=value`. Parse leniently.

Example:

```text
mode=sketch tool=line phase=0 pad_H=20 plane_pid=0 plane_n=0 grid=1 dirty=0
```

| Key | Use |
|-----|-----|
| `mode` | sketch / 3d badge |
| `tool` | highlight active tool |
| `phase` / `nclick` | “click 2 of 3” hints |
| `pad_H` | pad height spinbox sync |
| `grid` | toggle state |
| `dirty` | unsaved/dirty indicator |

Render as monospace overlay (upper-right of viewport) or side inspector. Kernel may also paint some HUD into the framebuffer — overlay text is still fine.

---

## 7. UX requirements (make it pretty — your strength)

These are **product** expectations; toolkit is your choice (Qt, Flutter, Electron, Dear ImGui, polished Gtk, etc.).

### 7.1 Layout (recommended)

```text
┌─ Menu bar ──────────────────────────────────────────┐
│ File  Edit  View  Help                              │
├─ Ribbon / toolbars (from tools.json groups) ────────┤
│ [Sketch tools…] [Feature…] [View…]                  │
├────────────────────────────┬────────────────────────┤
│                            │ Inspector (optional)   │
│     VIEWPORT               │  pad H spinner         │
│     (frame.raw blit)       │  HUD mirror            │
│     + optional HUD overlay │  selection tips        │
│                            │                        │
├────────────────────────────┴────────────────────────┤
│ status.txt                                          │
└─────────────────────────────────────────────────────┘
```

### 7.2 Visual polish checklist

- Dark modern theme (CAD-like: dark gray canvas, accent blue/teal).  
- Clear **active tool** state (match `tool.txt` / `hud tool=`).  
- Tooltips = `label` + optional `cmd` in small type for power users.  
- Icons optional; if used, key by `tools[].id` (not label).  
- Viewport focus: click viewport to focus; don’t let toolbars steal scroll.  
- HiDPI: scale chrome with DPI; **frame pixels stay 1:1 kernel resolution** (letterbox, don’t stretch-smear if possible — or stretch with nearest/linear, document choice).  
- Empty state: “Start kernel / waiting for frame…” when no `meta.bin`.  
- Error toast if `cmd.txt` stuck busy >500 ms.

### 7.3 Out of scope (do not implement in host)

- Feature tree graph editor tied to B-rep  
- Constraint solver UI beyond sending cmds  
- Reimplementing pad/extrude  
- Direct PostgreSQL UI tables (kernel owns that)  
- Wayland/X11 compositor logic inside kernel  

---

## 8. Acceptance tests (ship when these pass)

### A. Blit loop

1. Kernel running (`cad_app.x --nohost` or launcher).  
2. Host shows updating image when you orbit (gen changes).  
3. Resize window → letterbox or scale without crash.

### B. tools.json chrome

1. Host builds buttons from `tools.json` only.  
2. Click **Line** → kernel log / `tool.txt` shows tool=0 / hud `tool=line`.  
3. Change PG catalog + `tools` cmd → host rebuilds toolbar without restart (mtime).

### C. Sketch draw

1. `tool_rect` → two clicks on viewport → rectangle appears in frame.  
2. Rubber-band: with nclick>0, hover updates preview (if kernel paints it).

### D. Profile pick

1. Closed shape → `profiles` → light red faces.  
2. `tool_pick` → click face → bright red fill.  
3. Shift+click multi-select.

### E. Pad

1. Profile selected → `repad` / Pad tool → 3D solid in viewport.  
2. LMB-drag orbit works in 3D.

### F. File import (if you build File→Open)

1. Choose DXF → `path.txt` + `import` → geometry appears.

### G. Isolation

1. Host process kill → kernel keeps running.  
2. Host restart → reconnects via same `CAD_APP_STATE` files.

---

## 9. Suggested implementation skeleton (pseudo)

```text
main:
  state = env CAD_APP_STATE or "/tmp/cad_app"
  window = create_dark_main_window()
  toolbar_host = empty
  viewport = gpu_or_cpu_image_widget()
  status = label()
  last_gen = -1
  last_tools_mtime = 0

  on_frame(60hz):
    if mtime(tools.json) != last_tools_mtime:
      catalog = json.load(tools.json)
      rebuild_toolbars(toolbar_host, catalog)  // each button -> write_cmd(cmd)
      last_tools_mtime = mtime

    g = int(read(gen.txt) or -1)
    if g != last_gen:
      w,h,pitch = read_meta(meta.bin)
      pixels = read(frame.raw, pitch*h)
      viewport.set_image(bgra_to_rgba(w,h,pitch,pixels))
      last_gen = g

    status.set_text(read(status.txt))
    update_hud(parse_kv(hud.txt))

  viewport.on_mouse → map to frame coords → orbit/click/hover/pan as §4
  file_open → write path.txt; write_cmd("import")
```

Language/toolkit free: Qt6 QML, Flutter desktop, Electron+canvas, Dear ImGui+SDL, polished Gtk4, etc.

---

## 10. Reference samples (live)

After kernel start, you should see approximately:

**`meta.bin`:** `width=800 height=600 pitch=3200`  
**`tool.txt`:** `1 0 0 0 …` (sketch, line)  
**`hud.txt`:** `mode=sketch tool=line phase=0 pad_H=20 …`  
**`tools.json`:** `schema=1`, multiple `toolbars` (sketch / feature / view / file)

Seed catalog SQL (operators only): `CAD/sql/cad_ui_catalog.sql`  
You still only read **`tools.json`**.

---

## 11. Deliverables checklist (for the UI agent)

Ship a host that:

- [ ] Runs as separate process against `$CAD_APP_STATE`  
- [ ] Blits BGRA `frame.raw` on `gen` change  
- [ ] Builds chrome from `tools.json` (`cmd` exact)  
- [ ] Implements sketch click + 3D orbit + zoom + shift-click  
- [ ] Status bar + basic HUD  
- [ ] File→Open → `path.txt` + `import` (nice-to-have)  
- [ ] Dark modern CAD-like visuals  
- [ ] README: how to launch beside `./cad_app.x --nohost .`  
- [ ] **No** kernel source changes required  

Optional stretch:

- [ ] Parts list from `parts.txt`  
- [ ] Pad height spinner → `height N`  
- [ ] Preferences store toolbar layout by `tools[].id` locally  

---

## 12. What to tell the human if blocked

| Symptom | Likely cause |
|---------|----------------|
| Black viewport | Kernel not running / wrong `CAD_APP_STATE` |
| `tools.json` missing | Kernel failed PG connect or catalog not seeded |
| Clicks do nothing | Wrong letterbox math; or `cmd.txt` not clearing |
| Double geometry draws | You are drawing mesh — stop; blit only |
| Tools don’t match | Hardcoded buttons — use JSON only |

---

## 13. License / ownership

Host chrome is disposable. IPC contract is owned by the CAD product (SCSL).  
Pretty UI is welcome; contract breakage is not.

---

**End of builder spec.**  
Primary product rules: `docs/cad/CAD_UI_PLAN.md`.  
This file is the **implementation brief** for external UI builders (Gemini, Fable, humans).
