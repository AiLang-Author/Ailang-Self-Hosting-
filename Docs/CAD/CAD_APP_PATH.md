# Path to a working CAD application

**Goal:** you can **draw profiles, pad/cut, look, export STEP** without FreeCAD.  
**Kernel is toolable today** via demos/CLI; the app is a thin control surface.

---

## 1. Product shape (not FreeCAD clone)

```text
┌─────────────────────────────────────────────┐
│  App: sketch canvas + feature buttons + view │  ← host process (Linux first)
├─────────────────────────────────────────────┤
│  Tool API (already emerging)                 │
│    ImportDXF / ExportSTEP / Extrude / Fillet │
│    Pattern / ViewShot / Load profile         │
├─────────────────────────────────────────────┤
│  Kernel: Sketch · Feat · Topo · Bool · Blend │
└─────────────────────────────────────────────┘
```

AIMacro/script remains optional. **Mouse + keys + BMP/window** is the product.

---

## 2. MVP app (ship order)

| Slice | User can… | Kernel already has | App work |
|------:|-----------|--------------------|----------|
| **M0** | Pipe DXF → STEP → BMP | `cad_load`, `cad_view` | polish CLI only |
| **M1** | Open window, pan/orbit solid | tess + FB | host window + blit BMP |
| **M2** | 2D sketch: line, rect, circle | `CAD_Sketch` | canvas, snap, finish loop |
| **M3** | Pad height → solid + re-view | `ExtrudeProfile` | height control |
| **M4** | Pocket / hole on body | `ExtrudeCut`, `CreateHole` | tool profile + depth |
| **M5** | Pick edge → fillet/chamfer | `FilletEdge`, `ChamferEdge` | edge hit-test from tess |
| **M6** | Save STEP / open previous | IO | file dialogs |

**Do not** block M1–M3 on general bool or OCCT fillet.

---

## 3. Host choices (pragmatic)

| Option | Pros | Cons |
|--------|------|------|
| **Headless + BMP + external viewer** | already works | slow iteration |
| **SDL2/GLFW + software FB** | simple, no Vulkan required | more host code |
| **Existing Display libs in tree** | reuse | may pull AOS |

Recommend: **GLFW/SDL + software framebuffer** first (same mesh path as `CAD_View`), optional later GL lines.

---

## 4. Session loop (M2–M3)

```text
sketch entities ──BuildClosedLoop──► ExtrudeProfile(h)
        ▲                                    │
        │                              MeshSolid → FB
        │                                    │
        └──── edit / undo (later) ◄── BMP window
```

File format short-term: **DXF for sketch**, **STEP for solid**. Native project file later.

---

## 5. What the app will expose (bugs we want)

- Loop not closed / winding wrong  
- Extrude of multi-loop holes  
- Edge pick ambiguity after pattern  
- Chamfer/fillet domain refuse (must surface error text)  
- View matrix / scale confusion  

Each should map to a **kernel gate**, not an app hack.

---

## 6. Next implementation tranche (after this kernel turn)

1. Spec `cad_app` binary: args, window, keybindings  
2. M1: load STEP-less solid from demo recipe OR DXF pad, orbit BMP  
3. M2: sketch lines on plane  
4. Wire status line: last tool result / refuse reason  

Kernel work during app: only **fix-as-you-hit**.
