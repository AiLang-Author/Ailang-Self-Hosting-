# CAD design evolution — theory → current

**Living.** Records *what changed* from early paper design to the dogfoodable interactive app.  
**Pair with:** `CAD_Kernel_Design_v3.md` (normative kernel), `CAD_PROGRESS.md` (grind status), `CAD_SKETCHER_IMPL.md`, `CAD_PLANE_ON_FACE.md`.

**Last updated:** 2026-08-09

---

## 1. Early theory (design docs)

| Idea | Intent |
|------|--------|
| Pure-AILang B-Rep kernel | No FreeCAD glue; STEP out |
| Feat = recipes only | Topo/Bool build geometry; features store params |
| Sketch IR then extrude | DXF/LWPOLY bootstrap → closed loop → pad |
| Restricted Bool domain | Honest subset, not silent wrong solids |
| Sketch_0 + plane tree | Origin-rooted sketches; planes as recipes, not face indices |
| Constraints | Absolute datum first, relational second |
| Product tree in Postgres | Parts/revisions/assets |

Early Phase A/B assumed: **import path / demos first**, interactive app later; pad was rect/poly prism; holes often **AABB plate + hole** (kind-3).

---

## 2. What we learned (and changed)

### 2.1 Live sketch vs projection clone

| Theory | Current |
|--------|---------|
| Tessellate when needed | **Live** keeps CIRCLE/ARC entities |
| — | **Clone** only: tess → split → prune → face walk |
| Trim can explode curves | Trim **must not** permanently polyline live circles |

### 2.2 Profiles and pad

| Theory | Current |
|--------|---------|
| One closed loop → pad | **Multi-face** pool; outer envelope + nested faces |
| Auto “largest densest” pad | Still pick largest, but **holes only if multi-selected** |
| Through hole = plate AABB + hole | **Wrong** for notched outers → box, notch gone |
| — | **Now:** `MakePolyPrismHoles` — outer walls + **inner hole loops** on caps |
| Keyhole bridge for holes | Tried; side slit / wrong look → **abandoned** for pad |

### 2.3 ABI / clobber (AILang reality)

| Theory | Current |
|--------|---------|
| Multi-arg APIs like C | **6–7 float args clobber** (Arc3, AddProfileXY n_pts) |
| — | **FixedPool pins**, Pend+Point, pin before nested `CreateSketch` |
| Locals survive nested calls | **Do not trust** — re-read pool after every builder |

### 2.4 Constraints

| Theory | Full Jacobian sketcher |
|--------|-------------------------|
| Current | **Multipass projection** solver + panel apply; good enough for hub freehand |
| Deferred | Drag-while-constrained, dim HUD, full `CAD_Solve2D` |

### 2.5 UI investment

| Theory | Rich sketcher UI (dims, patterns, mirror) |
|--------|------------------------------------------|
| Current panel | Thin IPC tools — **disposable** |
| Policy | Wire **kernel verbs**; defer pattern/mirror/dim HUD |

---

## 3. Current design (locked principles)

```text
1. Live curves stay entities.
2. Projection is clone-only.
3. User selection drives pad holes (no silent auto-void rules).
4. Notched outer + holes = multi-loop prism, never AABB rebuild of outer.
5. Sketch_0 O/+X/+Y is the absolute root for constraints and (soon) planes.
6. Sketch-on-face attaches via PlaneFeature recipe — not raw face index.
7. Temporary panel: minimum tools to dogfood; no long-term UI debt.
```

---

## 4. Capability map (honest)

| Capability | Kernel | App / dogfood |
|------------|--------|----------------|
| Sketch line/rect/circ/arc/Arc3/fillet/point/trim | yes | yes |
| Profiles multi-select + pad + through holes | yes | yes |
| Cut (through / restricted) | yes | yes (Cut) |
| Revolve pad/cut | yes | **done** (profile lathe) |
| Draft / symmetric pad | yes (rect draft) | not wired |
| Loft / sweep | yes | not wired |
| Linear/circular pattern, mirror | yes | not wired (defer UI) |
| Sketch-on-face | PlaneFeature + OnTop | **v1 done** (side-face pick next) |
| Dim HUD / undo | no | defer |

---

## 5. Roadmap after this doc

1. ~~**Revolve UI**~~ **done** — true profile lathe  
2. **Sketch-on-face** — PlaneFeature + origin (see `CAD_PLANE_ON_FACE.md`) — **now**  
3. Draft / loft / sweep expose  
4. Real-part edge-case grind  

Pattern/mirror/N-gon **UI** stay deferred until a UI we intend to keep.
