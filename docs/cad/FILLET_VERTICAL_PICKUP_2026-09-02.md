# Fillet pickup — 2026-09-02 21:20

**Start a new session with this file.** The previous session context was too large and started repeating failed paths. Read this before touching fillet.

Repo: `/home/bob/Ailang-Self-Hosting-/`

---

## What to tell the user you understood

They fillet a **pacman** (270° extruded ARC + two LINE walls). Standalone **n=1 ARC** rim fillet is the known-good visual. After that they want the two **full-height mouth verticals** (plane ∩ cylinder generatrices) to fillet like any other LINE — Fusion-competitive, constant-R, round, watertight.

They **throw the body away every time**. They do not save files. Do **not** tell them to “use a fresh extrude” as if the last shot was leftover topology. Every screenshot this session was a new pad.

Visual gate: newest repo-root `Screenshot_YYYY-MM-DD_HH-MM-SS.png`. Euler / `fillet OK` is not success.

---

## Locked (do not reopen)

- Commercial-grade fillet → chamfer → boolean. Not Euler-as-success.
- Analytic B-Rep only: plane=1, cyl=2, sphere=3, torus=4. Tess samples analytic edges.
- Kernel as compiler: PARSE → ANALYZE → CHAIN → SOLVE → EMIT.
- **No recipes, special cases, pattern matchers, G1-dot/IR-vote/occupancy detector rewrites.**
- No invented inner-join corner recipes. Inner 90° pad joins cope. Outer box-top rounded vertices are Digon.
- Mixed LINE+ARC chains (ovals) are valid G1. Pacman **mouths** (LINE–ARC where traces miss > R) are a geometry violation — the 3-edge rim as **one** feature should refuse; V vs ARC are two features.
- `EmitChain` takes n=1..N (open canals allowed). At an open canal end, sew the meridian into every incident face that is **not host and not this wall**.
- Do **not** reintroduce: `MixSolveMixed`, `MixJoin2Face`, `MixSolveVertSphere`, `MixCopeSeam` ellipses, 420 host-insert, mouth-sphere caps, rail-split as a named mouth recipe, P-as-T_host, coalesce-LINE-T_host-to-ARC-Th as a named recipe.
- Leave SketchProfile/ProfIR phantom alone unless it is a pacman pattern matcher.
- AILang: SysV ≤6, Address-local clobber → FixedPool, Cos/Sin smash Integer locals. ~1500 LOC/file (`FilletIR.ailang` is already **1528** — do not add there).
- Rebuild then **restart gtk**:

```
./ailang.x CAD/cad_app.ailang -o /tmp/cad_app_new.x && cp -f /tmp/cad_app_new.x cad_app.x
```

- Logs: `/tmp/cad_app/session.log` (often binary — `grep -a`), `/tmp/cad_app/fillet_math.log`, `/tmp/cad_app/notice.txt`.
- User always restarts gtk after a rebuild when asked; still say restart because a stale binary is silent.

---

## What works (do not break)

| Path | Evidence |
|---|---|
| **n=1 ARC-only** on a fresh pacman extrude | User: “it worked fine stand alone first selection” and later “i regression tested the partial circle it's fine”. Class **c8** EmitChain. Math: pair=1, `dTh=8000`, sew `ins≠0`. Shot of a clean torus canal on the 270° rim. |
| Inner hole + stadium G1 + plain cylinder | Locked regression controls when not regressing. |
| Pick/HUD: fail clears selection | `CA_ClearEdgeSel` zeros buffer + `last_bl_n`; HUD back to Pick. User had verified leftover pick before that fix. |
| Floor overlay | Samples real edges (`CA_SampleEdge`), not origin-to-next-origin chords. |
| Pair-0 LINE on plane+cyl is **pair=0** | `pair=1 && edge kind==1 → pair=0`. A generatrix is a LINE canal, not a rim torus. |
| VertOnCollar | Collar CIRCLE must be a **minor** mer (`\|span\|≤π`). Pacman top 270° 3-edge plane is **not** a collar. Reason 5 on mouth verticals was this false positive. |

---

## Live bug (why you are here)

**Plane ∩ cylinder generatrix (the two pacman mouth verticals) does not emit a round constant-R canal.**

Geometry: extruded 270° ARC (OD cylinder) + two planar pie walls. Each mouth vertical is LINE, supports = radial **plane** + **cylinder**.

### What the user sees

Latest vertical attempts (all **new pads**):

| Shot | What happened |
|---|---|
| `Screenshot_2026-09-02_20-36-24.png` | **n=2 sequential Local (c7)**. One mouth looked round (the “right-hand” one). The other was a flat strip. User later: left “is not a fillet lol”. |
| `Screenshot_2026-09-02_20-47-46.png` | Same: left planar, right looked rounder from ISO. |
| `Screenshot_2026-09-02_20-55-35.png` | Sequential **EmitChain** recipe: **right totally destroyed**, left still a strip. |
| `Screenshot_2026-09-02_21-03-31.png` | Two **n=1 EmitChain c8**: both mouths flat chops. `sew ins=0`, `span=0 rad=0`. |
| `Screenshot_2026-09-02_21-09-36.png` | **n=1 Local c2** with FilletFaceN reading the **true ARC center**: Steiner `1+N·N` near 0, **planar slice through the pie**. User: “awful worse than before”. |
| `Screenshot_2026-09-02_21-16-25.png` + `_21-16-43.png` | **n=1 Local c2** after reverting the center lookup. Mouth at ~`(44, -23)` mm. Planar vertical strip + hanging triangle on the top of the wall. Bottom view: cut through. **Not a round canal.** |

### Math for the 21:16 mouth (the one in the last two shots)

`/tmp/cad_app/fillet_math.log`:

```
n=1  R=8mm  kind=1  pair=0
P  = 44.423, -22.945, 10
Nh = 0.122, 0.992, 0     (radial wall)
Nw = 0.888, -0.458, 0    (≈ P_xy hat — cylinder N from surf O≈0)
dTh = 11.483 mm          (should be ~R=8 for a 90° 2-face)
```

`Nh·Nw ≈ -0.35` → 2-plane Steiner `ab = R/(1+dot)` ≈ 12.4 mm. Local still returns OK and emits a **plane-like** 4-corner ruled patch (tess of two generators + two mer endpoints with no arc samples, or a huge offset). Top loop: wall LINE pulled to `Th` while the 270° ARC still ends at the old vertex → **triangle ear**.

The **other** mouth (20:36 “right-hand”) was ~`P=(-8.6, 49.3)`, `dTh≈7.8–8.5` ≈ R, `Nh·Nw≈0`. That is the only vertical that ever looked round, and only via **Local**, never via EmitChain.

### Why 2-plane Steiner is the wrong SOLVE here

The wall is **not radial to the ARC**. True cylinder N is `(P − C_arc)`. Using `C_arc` made `1+dot` worse and sliced the pad (21:09). Using surf O≈0 made one mouth accidentally ~90° (20:36 right) and the other 11.5 mm (21:16). Neither is a plane+cylinder rolling-ball.

**Correct 2-face SOLVE** (not a recipe — use the actual surfaces):

- Plane: offset by ±R along `N_plane`.
- Cylinder: offset radius `R_cyl ± R` (sign from convex/cove / occupancy).
- Generatrix is parallel to the cylinder axis. Ball center is the XY intersection of offset plane ∩ offset cylinder, extruded along the edge.
- `T_plane` on the offset plane; `T_cyl` **on the cylinder** (`C_cyl + R_cyl · radial`).
- Blend surface: cylinder of radius R whose axis is that ball-center line.
- Host rail: LINE on the plane. Wall rail: LINE (generatrix) **on the cylinder**.
- End mers: minor arcs in planes ⟂ edge, sewn into top and bottom (not host, not wall).

Do **not** approximate the cylinder as its tangent plane except as a last-ditch, and never report OK for `dTh` far from R.

---

## Dispatch (current code, after this session)

`FilletPlaneEdges` (`Librarys/Cad/Topo/Library.FilletSeq.ailang`):

1. `FilletCompile`.
2. If IR has both pair-0 and pair-1 → `FilletEmitChain` (mixed oval). **Keep.**
3. If `n<3` **and** `nV>0` (pair-1 CIRCLE present) → `FilletEmitChain`. **This is the good n=1 ARC path. Keep.**
4. Else Classify:
   - n=1 LINE → **class 2** `FilletEdgeLocal` (both-planes FaceGetPlane check **removed** so plane+cyl LINEs reach Local).
   - n=2 both vertical (dz≠0) → **class 7** Sequential Local.
   - n=1 CIRCLE → `ClassifyCylRim` (only if step 3 did not already EmitChain).

`FilletEdgeLocal` (`Library.Fillet.ailang`): 2-plane Steiner, `MakeCylinderSurf` along the edge, 4-cycle blend, `CoedgeSwapEdge` on both supports, mer into end faces via `FindFaceWithVert`, `FaceRetargetVert` on f1/f2 (skips inner-loop faces; **skips non-plane** in spirit of cylinder retarget).

`FilletIR.ailang` `FilletIRVert2Face` pair-0 is the same 2-plane Steiner. File is **over 1500 LOC** — do not add. Put new SOLVE in FilletEmit / Fillet.ailang.

---

## Failed paths this session — do not repeat

1. **Sequential EmitChain of two disconnected verticals** (plane-vs-cylinder `FaceGetPlane` dispatch). Second canal ran on a body the first had RimSwapped. Right mouth destroyed (`20-55-35`). User: no special casing, no recipes.
2. **Forcing n=1 LINE through EmitChain** (`n<3` always EmitChain). `class=c8`, `sew ins=0`, `span=0`, both mouths flat (`21-03-31`).
3. **FilletFaceN walking the face for a CIRCLE to get C_arc.** True cylinder N + 2-plane Steiner sliced the pie (`21-09-36`). Reverted. FilletFaceN is again `(P − surf O)` minus edge-dir axis.
4. **Rewriting extrude cylinder frame** to pin O=`(cx0,cy0)` and Z=`(0,0,1)`. Interacts with (3). Reverted to `fr[2]=0`, `fr[11]=1` only.
5. Telling the user to throw away the solid / not reuse a mutated body. **They never save. Stop.**

User allowed: if **both verticals at once** cannot be one chain, **refuse** (`reason 22`: `those edges are not one chain — apply separately`). That refuse is in place for EmitChain RimOrder fail. Class 7 Sequential Local still exists for n=2 verticals — 20:36 path (one round, one strip). Do not re-add sequential EmitChain to “make both work.”

---

## Files you will touch

| File | Role |
|---|---|
| `Librarys/Cad/Topo/Library.Fillet.ailang` | `FilletEdgeLocal`, `FilletVertOnCollar`, `RimMakeSeg` kind=1. ~1479 LOC. |
| `Librarys/Cad/Topo/Library.FilletEmit.ailang` | `FilletFaceN`, `RimOrder`, `FilletSewOpenEnd`, `FilletEmitChain`, `FilletMerThrough`. ~1021 LOC. |
| `Librarys/Cad/Topo/Library.FilletSeq.ailang` | Classify, Sequential, `FilletPlaneEdges`. |
| `Librarys/Cad/Topo/Library.FilletIR.ailang` | PARSE/ANALYZE/SOLVE. **1528 LOC — do not grow.** |
| `Librarys/Cad/Topo/Library.FilletCove.ailang` | `FCoveMakeJoinFace` (use `FCove.i` after trig — Cos smashes Input `i`). |
| `Librarys/Cad/Topo/Library.Extrude.ailang` | Cylinder side surf; do not re-pin frame unless you have a failing ARC. |
| `CAD/App/SolidBlend.ailang` | `CA_FilletSolid`, `CA_ClearEdgeSel`. |
| `CAD/App/ToolsHud.ailang` | HUD kind 10 fail → field Pick. |
| `Librarys/Cad/Library.CAD_Err.ailang` | Reason 22 message. |

---

## Suggested next kernel step (not a recipe)

Fix **SOLVE** for pair-0 when one support `FilletIRFaceKind` is 2 (cylinder): offset plane ∩ offset cylinder in the plane ⟂ generatrix. Write `T_host` on the plane, `T_wall` **on the cylinder**. Then Local/EmitChain rails lie on their faces, mers are minor, tess of the blend cylinder is round.

Refuse (`reason 11` or a new SOLVE reason) if `|T−V|` is not a constant-R contact — do not emit a planar strip and print OK.

Keep n=1 ARC EmitChain as the visual control. After any change, user will re-pad (they always do) and shot the newest PNG.

---

## Session quote (leave-off)

User: “i throw the bodys away EVERY time i am not saving the files”

Last vertical shots: `Screenshot_2026-09-02_21-16-25.png` and `Screenshot_2026-09-02_21-16-43.png` — Local c2, not a fillet.

ARC still good. Do not “fix” the vertical by touching ProfIR, Mix*, or n=1 ARC emit.
