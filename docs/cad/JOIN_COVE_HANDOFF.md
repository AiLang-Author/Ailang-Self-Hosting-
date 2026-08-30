# Join-cove handoff — 2026-08-24 18:40

**Read this before touching fillet/cove.** The previous session passed Euler gates while the picture was never a cove. The user is correctly angry. Do not declare success from `2E=Σ nce`.

---

## What the user sees (this is the gate)

Latest shot: `Screenshot_2026-08-24_18-38-33.png`

- 100×100 plate, 50×50 pad, both H=20, fillet R=8, **4 inner join edges**, class 3, faces=19, log `3D solid fillet OK`.
- **Four spherical lumps at the pad corners on the plate.**
- **No quarter-pipe gutter along the four joins.** Pad bottom edges still look sharp.
- That is **not a fillet cove.** User: “are you just punking me… that is not a fillet cove.”

A real join cove (pad glued on a plate, fillet the imprint):

- Continuous **quarter-cylinder of radius R** along each join (host top ∩ pad wall).
- At each corner, a **1/8-sphere** that *connects the two pipes*, not a blob sitting by itself.
- Host hole becomes a **rounded rectangle** offset by R. Pad walls trimmed up by R.
- Looks like a concave weld bead all the way around the pad.

Visual gate: if you cannot see four pipes + four corner balls that meet them, it is not done. Euler is necessary, not sufficient.

---

## Locked product rules (do not reopen)

- Kernel owns geometry/camera. Gtk is chrome (`CAD/host/cad_shell_gtk.cxx`).
- Closed sketches pad from live geometry (`GlueOnFace`). That B-Rep is the contract.
- **No AABB as the solid. No kind recipes for tess.** Tess samples analytic edges (`PATH=PARAM`).
- Analytic surfaces only: plane=1, cyl=2, sphere=3, torus=4. No n-gon geometry.
- **Do not restore Digon-on-hole.** Friday 12:11 “continuous gutter” was Digon on the imprint (diamond trench). Wrong solid. User forbade rollback.
- **Do not sequential `FaceRetargetVert` on holed host** (17:47 frustum).
- Box 4-edge **outer** Digon (class 1) must keep working. Simple cylinder/box outer fillet is fine.
- Case-pattern handling is expected (classifier + `Branch`). Not a mega-function, not “eliminate cases.”
- Notifications: `CA_Notify` → `/tmp/cad_app/notice.txt`. No HUD spam.
- AILang: SysV ≤6, Address-local clobber → `FixedPool`, `IfCondition`/`Fork`/`Branch` (integer `Case` = CMP/JE). ~1500 LOC/file.
- Rebuild: `./ailang.x CAD/cad_app.ailang -o /tmp/cad_app_new.x && cp -f /tmp/cad_app_new.x cad_app.x` then **restart the gtk shell**. User must restart or they are looking at a stale binary.

---

## Classifier (this part is OK — leave it)

Path is **one integer then `Branch`**, not a try-chain.

`CA_FilletSolid` (`CAD/App/SolidBlend.ailang`):

1. `EdgeIsCove` on first selected edge → `fillet_concave`.
2. `nsel>1` → `CAD_Blend.FilletEdges` → `ClassifyFilletBatch`.
3. `nsel==1` → `CAD_Blend.FilletEdge` → same classifier, n=1.

`ClassifyFilletBatch` (`Librarys/Cad/Topo/Library.FilletSeq.ailang`) first match:

| Class | When | Runs |
|------:|------|------|
| **3** | Any selected edge is **inner-loop LINE** (pad imprint). Walks hole, requires a live upright at each corner | `FilletJoinCoveCycle` |
| 6 | Inner CIRCLE (boss-base) | lathe ring (`CompoundAdd`, not a B-Rep weld) |
| 4/5 | Lone solid, outer CIRCLE, z=top/bot | analytic torus rebuild |
| 2 | One outer plane–plane LINE | `FilletEdgeLocal` |
| 1 | ≥3 outer horizontal LINEs sharing verts, one shell, **not** inner | Digon |
| 7 | Verticals only | sequential local |
| 0 | else | refuse + notice |

**Inner LINE can only be 3 or 0.** Never Digon (1) or sequential (2/7). That is the Sunday break, locked out.

`CA_LogInt("cad_app: fillet class=", …)` **drops the number** (known quirk). Infer class from faces / `fillet join-cove` print / `fillet class=` in stdout of headless demos.

18:38 apply: `path=edges n=4`, `COVE`, `faces=19` → class 3, **sphere-at-P** `FilletJoinCoveCycle` (no gutter).

**2026-08-24 18:50 restore:** `Library.FilletCove.ailang` checked out from `f07f628b` (F' 6-cycle true cyl + 3-plane sphere + collar). Demo 11→23, 4 CYL+4 SPH, 2E=96. Tess 6-cycle Ruled + Steiner still in Tess*. This is **08:27**: pipes exist; corners overshoot. Restored because 18:38 was not a cove at all. Do not put sphere-P arcs on cylinder faces again.

---

## Why every construction this session failed visually

Geometry fact you cannot wish away:

For orthogonal host `Nh=+Z` and walls `Nw=±X,±Y`:

- **2-plane rolling ball** (one join): `C = P + R(Nh+Nw)`, contacts `T_h = P+R Nw` (on plate, outboard by R, **same span as the join**), `T_w = P+R Nh` (up the wall by R). Cylinder on original span `2a`. This is the gutter pipe.
- **3-plane rolling ball** (corner tangent to host + two walls): `C = P + R(Nh+Nw1+Nw2) = (a+R, a+R, H+R)`. Host contact `T_h = (a+R, a+R, H)` — **R past the pad in both X and Y**. Wall contacts sit at `y=a+R` / `x=a+R` — **off the bounded wall faces**. Cylinder ∩ that sphere is only at `y=a+R`. **You cannot stitch a 3-plane equal-R sphere to cylinders that stop at y=±a. They do not touch.**

So:

| Want | Forces |
|------|--------|
| True rolling-ball corner | Cylinders **extend** to `a+R`; host hole is larger rounded-rect; 1/8-sphere sits **on the plate in front of the pad**. That *is* a cove. User called it overshoot. |
| Stop at pad verticals | 3-plane sphere **cannot** meet the pipes. Corner closer is then planar pies / sphere-at-P / something else. Pipes can exist along the sides. Corners will not be the 3-plane ball. |

The session ping-ponged between those two and shipped neither as a picture.

### Timeline (shots in repo root)

| Shot | What it actually was |
|------|----------------------|
| Fri 12:11 `Screenshot_2026-08-23_12-11-37` | Last “continuous gutter”. **Digon-on-hole** (diamond). Do not restore. |
| 17:47 | `FaceRetargetVert` on holed host → frustum |
| 17:59 / 18:03 | Sequential cyl on original span + unstitched 3-plane spheres (fins, no pipes) |
| Sun sequential | Inner-join diverted off Digon onto per-edge local. Broke the join. |
| 07:52 | F' Euler-OK, nring=6 fanned → fins |
| 08:02 | 6-cycle zip → pipes, still wrecked corners |
| **08:27** | F': outboard 1/8-spheres **on the plate in front of the pad** + wings past verticals. User: “cove overshoots the end of the upper cube line… EXACT same bug every time.” |
| 15:00 | Stop-at-end + **planar pie** end-caps. Huge triangular fans at corners. No round join. User unsure better/worse. |
| **18:38** | Stop-at-end + **sphere-at-P** + rounded-rect hole. **Four corner blobs, no gutter.** User: not a cove. |

### What the code does right now (18:38 / `cad_app.x` 15:41)

File: `Librarys/Cad/Topo/Library.FilletCove.ailang` — `FilletJoinCoveCycle`.

- 2-plane contacts at both original endpoints (`FCoveSolveCorner`). T_w shared per corner (`276[i] = 252[next]`).
- 4-cycle cylinders, original span 2a (host gen `312`, wall gen `324`).
- **End-arcs `360`/`372` are sphere-at-P sections** (center = pad corner P, not the 2-plane cyl centre). Those arcs **do not lie on the cylinder.**
- Host inner: 8-cycle, offset gens + host-plane quarter-circles at P (`348`).
- One sphere per corner at P, r=R, 3-cycle: host qarc + two end-arcs (`FCoveMakeSphereFace`). `FCoveMakeCollarFace` is a no-op.
- Pad top stays 4-gon. Shortened verticals to P'.
- Headless `CAD/demo_fillet_join_cove.ailang`: faces 11→19, 4 CYL+4 SPH, 2E=80, open=0, **JOIN COVE OK**. That demo is a topology gate, **not a visual gate**.

Why 18:38 has blobs and no pipes: B-Rep has 4 cylinder faces, but tess (`MeshRuledLoop`) zips the two **sphere-P** end-arcs. Those are not the cylinder’s circular sections, so the “pipe” mesh is a pinched/degenerate ruled patch that does not read as a gutter. Spheres at P tessellate as isolated corner balls on the plate. Exact failure the user photographed.

---

## What to build (recommended)

**Ask the user one question before another construction**, because the last two days were this disagreement:

> Do you want a **true rolling-ball cove** (gutter lives on the plate, rounded-rect hole, 1/8-spheres outboard of the pad — that *will* occupy ~R past the pad silhouette), or a **hold-line cove** (pipes stop flush at the verticals, corners stay sharp / get a different cap)?

Until they answer, the honest rolling-ball (what every kernel draws for “fillet these 4 joins”) is:

1. **Pipes = 2-plane cylinders with TRUE planar end-arcs** (centre `C = P+R(Nh+Nw)`, from `T_h` to `T_w`). Zip those two circles. That is the gutter. Do not put sphere-P arcs on a cylinder face.
2. **Corners = 3-plane spheres** at `C=P+R(Nh+Nw1+Nw2)`, stitched to the cylinders by **extending the cylinders to the sphere** (host gen to `T_h` of the 3-plane, i.e. span `2a+2R` on the offset lines). Sphere ∩ host quarter-circles make the rounded-rect hole.
3. **Host inner = rounded rect**: 4 offset gens + 4 `sphere∩host` quarter-circles. Not a plus-shape, not a bigger sharp rectangle with a sphere dumped on the corner.
4. **No planar pies. No collars unless a wall-wall section is actually needed.** No Digon-on-hole. No sequential inner.
5. **Walls**: 4-gons, bottom = wall gen at z=H+R. If 3-plane `T_w` is off the bounded wall, that is the “wing” — either a small collar in the wall plane or a different wall embedding. Do not leave unstitched fins.

If they insist “stop at the cube line”: keep (1) with original span `2a` and **true** cyl end-arcs; skip (2); corners are the pipe’s circular end in the vertical plane (a **quarter-disk around C_cyl**, not a triangle to P). That looks like four independent gutters dying at the verticals — not a wrapped corner, but it *is* a cove along each join. The 15:00 pies failed because they were triangles to P (and likely long-arc fan), not quarter-disks around the cylinder axis.

**Do not** put sphere-at-P end-arcs on cylinder faces again. That was 18:38.

---

## Files that matter

| File | Role |
|------|------|
| `Librarys/Cad/Topo/Library.FilletCove.ailang` | **The class-3 construction.** Rewrite here. |
| `Librarys/Cad/Topo/Library.FilletSeq.ailang` | Classifier + `Branch`. Case 3 calls `FilletJoinCoveCycle`. Leave dispatch. |
| `Librarys/Cad/Topo/Library.Fillet.ailang` | `MakeMinorArcEdge` (span slot 12, `(−π,π]`). `FilletEdgeLocal` 4-cycle (the working pipe for a *single* plane–plane). |
| `Librarys/Cad/Topo/Library.FilletVertex.ailang` | 3-plane sphere + convex stitch. Cove stitch still skipped (`sh=0`). Class 3 must not rely on it. |
| `Librarys/Cad/Library.CAD_Blend.ailang` | `FilletEdge` Branch on class. |
| `Librarys/Cad/Tess/Library.TessCollect.ailang` | `MeshRuledLoop` zips **two CIRCLE** rails. `SampleCircleEdge` uses slot 12 span. |
| `Librarys/Cad/Tess/Library.TessCore.ailang` | `MeshLoopFanTess`. nring=3 & 3 circles → Steiner on sphere. **Do not clobber `nn` with ArcSegCount.** |
| `Librarys/Cad/Tess/Library.TessFace.ailang` | nring 4 or 6 → Ruled; inner/planar XY; else fan. |
| `CAD/App/SolidBlend.ailang` | Apply, concave probe, batch vs single. |
| `CAD/demo_fillet_join_cove.ailang` | Topology gate. Update face/SPH counts if Euler changes. **Not the visual gate.** |
| `CAD/demo_fillet_pad_verts.ailang` | Collect shortened verts after class 3; skip step 2. |
| `docs/cad/AILANG_FILLET_COVE_DESIGN.md` | Signed F' design (collar, 11→23). **Superseded visually.** Classifier section still accurate. |
| `docs/cad/CAD_SPLIT_NOTE.md` | File size / append-only pool fields. |

Rebuild + restart gtk. `cad_app.x` at handoff is 15:41 2026-08-24 (sphere-at-P, faces 19).

`FCove.buf` slots (current, n≤12, stride 12 unless noted):

```
0 edge  12 v0  24 v1  36 host  48 wall  60 upright
84–108 Nh  120–144 Nw  156–180 dir  192 ab
204–228 C0 (2-plane at v0)
240 T_h0  252 T_w0=P'  264 T_h1  276 T_w1 (= next P')
288 shortened vert  300 cyl surf
312 host gen  324 wall gen
348 host-plane qarc at v0
360 end-arc v0  372 end-arc v1
408 sphere surf at P
456 n  457 inner loop
```

`RegisterCe` **clobbers `FCove.ce`**. Pin loop coedges in `hd`/`nxt` before calling it (`SwapHost` already does).

---

## Working controls (do not break)

- Box / prism **outer** rim: class 1 Digon.
- Lone cylinder top rim: class 4 torus rebuild (`MakeCylinderTopFillet`).
- GlueOnFace rec-on-rec: 11 faces, inner LINE cycle, live uprights → class 3.
- Sketch occlude in 3D+solid (`DrawView3` `SetOcclude(1)`) so cyan sketch is not a ghost through the hole.

`demo_fillet_prism_box` may FAIL a tess-quality dump (`top_tris` / `cap_mid`) even when class=1 Digon ran. Interactive box Digon is the control.

---

## Non-goals until the picture is a cove

- Convex-fillet of shortened verticals after cove (`incident-collar` fail-closed).
- Class-6 true B-Rep torus weld (still `CompoundAdd`).
- Gregory / n-sided patches, variable-R.
- Gtk/camera/pick.
- Resurrect `Library.FilletUnused.ailang`.
- Treating `JOIN COVE OK` as done.

---

## Session hygiene

- Log: `/tmp/cad_app/session.log` (null bytes; use `strings | grep fillet`).
- Notice: `/tmp/cad_app/notice.txt`.
- Tree: `/tmp/cad_app/tree.txt`.
- Screenshots land in repo root as `Screenshot_YYYY-MM-DD_HH-MM-SS.png`. **Always open the newest one.**
- Git: CAD-only local commits; leave display/fonts alone unless asked. Branch was `master` ahead of `github/master`.

If you are the next agent: open `Screenshot_2026-08-24_18-38-33.png` first, agree it is not a cove, then ask the one question above. Do not invent a fifth corner recipe that only satisfies the demo.
