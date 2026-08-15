# CAD modelling hitlist — drive it first

**Status:** living focus list (2026-08-14)  
**Rule:** if you cannot *aim* the verb at a face/edge/profile, the kernel entry does not count as a product feature.  
**Related:** `CAD_PROGRESS.md` (grind log) · `CAD_SKETCHER_IMPL.md` (IR) · `CAD_PLANE_ON_FACE.md` (lineage) · `CAD_PHASE_C_TOOLS.md` (kernel already built)

---

## 0. Call (locked)

**Sketcher conveniences and in-context display first. Solid/B-Rep second. Feature recipes (hole/pattern/thread/emboss) third.**

The kernel already has more verbs than the Gtk app can point: pad/cut/revolve, fillet/chamfer, pattern/mirror, loft/sweep, restricted bool. Those stay **off the ribbon** until a human can pick the face, see the solid, and trust the plane.

Bidirectional / midplane extrude and “circle on face → hole” are **one flip of N away** (`ExtrudeSymmetric` / `ExtrudeCut` exist). Do **not** turn them on until Sketch-on-Face + outward pad is boringly correct. Wrong-direction pad through the body is the current proof.

---

## 1. Why this order

Without a way to drive it, a Class A kernel is almost worthless. The last week of bugs were all *aiming*:

| Symptom | Real failure |
|---------|----------------|
| 3rd sketch floating | centroid pick / click-through |
| Top of 2nd solid unselectable | stale face plane after Translate |
| Side pad detached | `MapSolidByFrame` clobber |
| Polygon on the wrong face | EvalFrame rebound + no cycle-pick |
| Cylinder through the box | N pointed into the solid |

Those are display + plane-tree + pick problems, not missing hole tools.

---

## 2. What we will not do

| Temptation | Why not (now) |
|------------|----------------|
| Ship FreeCAD Python tools against our bodies | Different B-Rep, different names, OCC topology. Our policy is live sketch entities + real rings, not OCC shapes. Format mismatch is not a weekend shim. |
| AIMacro as the product CAD | Fine as a *lab* to try a verb. The shipping tool is an AILang recipe (`CAD_Feat` / `CAD_Topo`) the Gtk host can call. Python stays a prototype, not the runtime. |
| Boolean-first UI | Union/cut stay off the ribbon until the tool body is a sketch **on a named face** with outward N. |
| Midplane / both-directions / hole-from-face | Kernel-adjacent. Unlock after D0–D1. |
| Vulkan viewport, loft/sweep chrome, thread/emboss | After the part can be drawn. |

**Later option (honest):** use FreeCAD / AIMacro as a *reference implementation* of a recipe (what inputs, what result), then port the recipe to AILang. Never call their `.so` on our `CAD_Store` handles.

---

## 3. Phases

### D0 — See what you are drawing (display + plane)

The current “Sketch on Face → blank 2D” is the #1 driveability hole. You lose the solid, so you cannot tell if the circle is on the lid.

| # | Item | Done when |
|---|------|-----------|
| D0.1 | **In-context sketch** | Sketch-on-face keeps the shaded solid; UV overlay on the real face; no full-screen blank pad |
| D0.2 | Orbit / pan / zoom while sketching | Same `CAD.View` camera; host only sends `orbit`/`pan`/`zoom` |
| D0.3 | Face highlight stays honest | Light-red available, bright-red hover; Shift+click cycles along the ray |
| D0.4 | Locked face frame | Pick-time X/Y/N + Sketch_0 origin; pad uses that, not signature rebound |
| D0.5 | Outward pad | +N away from solid center; boss sits on the face (no through-collision) |
| D0.6 | Face-plane overlay | Outline the **B-Rep face**, not an 80 mm square about a projected origin |

### D1 — Sketcher conveniences (drive the profile)

Kernel already has most entities. This is *using* them on a face without fighting the UI.

| # | Item | Done when |
|---|------|-----------|
| D1.1 | Rubber-band + HUD on every tool | N=/R=/L=/angle visible; no Cos/Sin-in-arg clobber |
| D1.2 | Undo that actually restores sketch + plane + solid | One-step is ok; must not drop the first body |
| D1.3 | Constraints on the face sketch | Same ribbon; origin = that sketch’s O (lineage), not world |
| D1.4 | Trim / pick / coincident while the solid is visible | |
| D1.5 | Numeric dims / type-in L and R | Status + commit |
| D1.6 | Sketch rotate in UV (and later 3-point align to an edge) | Not world X/Y orbit of the sketch — rotate **on the plane** |
| D1.7 | Exit sketch without losing the solid or the plane pid | `m` / Done |

### D2 — Solid aiming (verbs you can point)

Only after D0–D1. Kernel entries already exist; this is **chrome + pick**.

| # | Item | Kernel already | App |
|---|------|----------------|-----|
| D2.1 | Pad from on-face profile | `ExtrudeOnPlane` + CompoundAdd | outward N, keep body |
| D2.2 | Cut / hole from on-face circle or profile | recipes only — **see `CAD_BREP_BOOL_FILLET.md`** | HUD CUT exists; general B-Rep cut does not |
| D2.3 | Midplane / both-directions | `ExtrudeSymmetric` | one extra pad option |
| D2.4 | Revolve on a face sketch | kind 6 SoR | already in 3D; keep axis pick |
| D2.5 | Edge fillet / chamfer | Digon / ChamferEdges on **existing** edges | JOIN leaves no junction edge — B4 then B8 |
| D2.6 | Named face identity | `plane_tree` + `face_map` | dogfood save/load after two on-face pads |

### D3 — Recipes (tools people name)

Do **not** start until a hole can be aimed (D2.2). Prefer native AILang recipes. FreeCAD/AIMacro only as a spec.

| # | Item | Notes |
|---|------|--------|
| D3.1 | Hole (simple / countersink / thru) | Sketch circle + cut recipe; not a third kernel |
| D3.2 | Linear / circular **feature** pattern | Kernel `LinearPattern` / `CircularPattern` exist; need a seed pick |
| D3.3 | Mirror feature | Kernel Mirror exists |
| D3.4 | Pocket | Cut with a face profile, not a primitive box |
| D3.5 | Emboss / wrap | Defer — needs a stable face param |
| D3.6 | Thread | Cosmetic first (mesh/HUD); true helix later |
| D3.7 | Loft / sweep chrome | Kernel demo-gated; last |

---

## 4. Current dogfood path (must stay green)

```text
Sketch_0 → pad solid
  → Sketch on Face (see the solid) → profile → pad boss (outward)
  → Sketch on Face (side or next cap) → profile → pad or cut
  → save / load → same pids, same attachments
```

If any step needs an AABB, a blank screen, or a rebound to the hex top, it is a **P0 bug**, not a new tool.

---

## 5. AIMacro / FreeCAD — allowed use

```text
Python / FreeCAD / AIMacro     = try the verb, write down inputs → result
        ↓  (human port)
CAD_Feat / CAD_Topo recipe     = native .x, Gtk calls it
        ↓
cad_app ribbon / tools.json    = only after D2 pick exists
```

Do not load FreeCAD bodies. Do not call OCCT on our shells. If a Python prototype is useful, keep it in a `dev/` folder and throw it away once the AILang recipe matches the demo.

---

## 6. This week (only)

**Navigator (2026-08-14):** left PART list = Origin / Sketch_0 / Body / Sketch_N. Click switches current sketch or 3D body. Not a Fusion timeline, not a FreeCAD object dump.

1. **D0.1** in-context sketch (solid + dashed lower projection).  
2. Face-vertex refs + typed UV (`pt U V`, Fix U/V). Polygon any N (3–64).  
3. Do **not** add hole/pattern/thread chrome.

When D0.1 works, pull D1.1–D1.5 in order. Everything else waits.
