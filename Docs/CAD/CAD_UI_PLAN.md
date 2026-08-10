# CAD UI Plan — Internal dogfood (FLTK shell + IPC viewport)

**Status:** charter locked (2026-08-09)  
**Scope:** internal development only — not a product release  
**License:** Sean Collins Software License (SCSL v1.0) — see repo root `License.md` / `LICENSE`

---

## 1. Architecture shape (do not break)

```text
┌──────────────────────────────────────────────────────────────────┐
│  FLTK presenter (window chrome only)                             │
│  ┌── ribbon / menus ──┐  ┌── HUD (upper right) ──┐               │
│  │ File · Sketch ▾    │  │ tool L / angle / R    │               │
│  │ Plane ▾ · Feature ▾│  │ pad H / plane offset  │               │
│  └────────────────────┘  └───────────────────────┘               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Viewport = blit kernel frame.raw (ARGB)                   │  │
│  │  solids + planes + sketch overlay · orbit · pick           │  │
│  │  grid toggle · RMB context for in-use tool                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│  status line: mode · active plane · tool · selection             │
└────────────────────────────▲─────────────────────────────────────┘
                             │ IPC (/tmp/cad_app/* or socket later)
┌────────────────────────────┴─────────────────────────────────────┐
│  cad_app.x (AILang kernel)                                       │
│  model · tess · planes · selection · HUD numbers as data         │
│  never opens X11/GTK/FLTK                                        │
└──────────────────────────────────────────────────────────────────┘
```

**Rules**

1. Kernel **never** owns windowing. It fills a buffer + owns model + publishes HUD fields.  
2. Presenter is swappable: X11 host today → **FLTK shell** next → AOS later. Same IPC.  
3. Viewport already shows planes + solids together — keep that; polish chrome around it.  
4. Temporary button panel is disposable; do not grow more one-off buttons as the product UI.

---

## 2. Presenter choice

| Option | Decision |
|--------|----------|
| **FLTK** | **Yes** — shell for menus, dialogs, ribbon strip, HUD panel |
| X11 host (current) | Keep as blit/reference or fold into FLTK drawable |
| GTK3 | Avoid for shell (heavy / friction); optional zenity only if needed |
| Qt | No |

FLTK draws **chrome only**. The CAD image is still `frame.raw` from the kernel (or shared mem later).

---

## 3. Viewport (already roughly right)

| Need | Plan |
|------|------|
| Solids + planes + sketch together | **Keep** current 3D construction view |
| Grid toggle | Cmd `grid` / `grid 0` / `grid 1` — plane UV grid on/off (axes may stay) |
| Orbit / zoom / nav cube | Keep; clarify click vs orbit (tool or modifier) |
| See-through plane grid | Dashed / sparse lines (done); improve later |

**Mode policy (target)**

- Prefer **one 3D scene**; sketch tools draw on **active plane** (UV mapped in place).  
- Full-screen 2D UV remains available for precision, not the only way to exist.

---

## 4. HUD (upper right — kernel-driven)

**Placement:** upper-right of viewport (kernel can paint into FB, or FLTK overlays text from IPC).

**Phase A (first):** kernel publishes HUD lines; presenter (or kernel FB) shows them UR.

| Context | Fields |
|---------|--------|
| Line / rect place | length, optional angle |
| Circle / arc | radius, angle span |
| Pad / cut | height / depth |
| Plane create | offset mm, angle deg |
| Always | active plane pid, tool name, mode |

**Phase B (later by tool type):** richer per-tool panels (line vs circle templates).  
**Phase C (after UI up):** **Measure tool** (distance / angle pick-to-pick).

IPC sketch:

```text
# /tmp/cad_app/hud.txt  (or fields in status.txt)
tool=line phase=2 L=42.5 ang=0
pad_H=10
plane_pid=2 plane_off=50
grid=1
```

Presenter **displays** numbers; kernel **owns** them.

---

## 5. Shell chrome (minimal)

### File
- Open / Save with **names** (FLTK file chooser → path into existing load/save cmds)
- New / Close / export STEP-BMP as today

### Ribbon-style groups (dropdowns, not a flat 40-button soup)

| Group | Contents |
|-------|----------|
| **Sketch** | Line, Rect, Circ, Arc ▸ Arc3, Point, Trim, Pick, Fillet |
| **Plane** | XY, XZ, YZ, Offset…, Angle…, Flip, On face (pick), SkPln |
| **Feature** | Pad, Rev, Cut, (Loft / Draft when wired) |
| **View** | Iso/Top/Front, Wire, Grid toggle, Fit |

### Context (RMB)
- Only for **in-use tool** + current selection  
- Examples: Cancel, set height, flip plane, next profile  
- No global context menu of everything

---

## 6. Build order

1. **Grid toggle** (kernel + cmd + HUD flag)  
2. **HUD channel** + upper-right display (kernel paint or FLTK text)  
3. **FLTK shell** skeleton: window, menubar/dropdowns, viewport blit widget, status  
4. **File open/save** dialogs → existing IPC/file paths  
5. **RMB context** for active tool  
6. **Measure tool** (after shell usable)  
7. Multi-sketch list for loft (selection model)  
8. AOS presenter swap (same buffer API)

---

## 7. Non-goals (now)

- Marketing polish, themes, docking like Fusion  
- Full feature tree / constraint manager UI  
- Dim-on-geometry HUD (deferred with dim system)  
- Rewriting viewport in toolkit drawing APIs  

---

## 8. IPC contract (freeze direction)

| Path / channel | Role |
|----------------|------|
| `frame.raw` + `meta.bin` | Viewport pixels |
| `cmd.txt` | Tools, orbit, click, plane, pad… |
| `status.txt` / `tool.txt` | Mode, tool, dirty |
| `hud.txt` (new) | Live params for UR HUD |
| Optional later | socket instead of `/tmp` files |

---

## 9. License

This project (and CAD work) is under **Sean Collins Software License (SCSL v1.0)**  
Copyright © Sean Collins / 2 Paws Machine and Engineering.  
See root `License.md` and `LICENSE`. Terms stay SCSL until the author revisits licensing after the stack stabilizes.

---

## 10. Success criteria (internal)

- Open a named part, draw on two offset planes, see both grids in 3D, orbit, pad/loft without memorizing raw cmds.  
- HUD shows length/H while placing without reading the terminal.  
- Presenter can be swapped without touching kernel geometry code.
