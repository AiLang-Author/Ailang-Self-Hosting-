# Fillet ∩ rear curve — session handoff (2026-10-30)

Start here. Do not reconstruct from chat. Architecture lock: `docs/cad/FILLET_MULTI_SEGMENT.md` (rev 4). Screenshot `CAD/screenshots/junc5-latest.png` is the pre-fix n1b binary (purple lid spike). The shaded Front and ISO views after the ellipse install (history 7/7 Fillet, opac=100) still showed a starburst on the rear host cylinder and long diagonals on the top. The fillet side (rolling-ball `RuledLoop`) was already accepted and is unchanged. That rear/top fan is fixed in the install below: open arcs follow the coedge origin, and the host wall is an x-monotone strip. Headless gates are green. GUI was not relaunched.

## The bug

Fillet of a top LINE into an **unselected extruded 2D-arc** (`junc=5`). Even **one** edge. The arc is analytic (1 CIRCLE + kind=2 cylinder). Commercial CAD: rolling-ball cylinder, end is a notch-trim (fillet ∩ limiter).

The lid-spanning purple spike was the notched wall’s triangle fan, seen through the translucent lid. Two causes, both fixed in source and in `./cad_app.x`:

1. **Host cylinder axis.** `SweepEmitCurve` left the circle span in `fr[9]` and `a0` in `fr[10]` after `MakeCircle` (those slots are copied onto the circle; `MakeCircle` only reads 0..8). `MakeCylinderSurf` mapped `fr[9,10,11]` to the cylinder Z axis, so Z was `(span, a0, 1)`. STEP of the pre-fix 1-line solid: axis `(−0.853, 1.997, 1)`. Fix: zero `fr[9]` and `fr[10]` before `MakeCylinderSurf`. Gate prints `wall axis 0 0 1000`.
2. **Earclip fan off the cylinder.** With a true +Z axis, `MeshCylLoopUV` still earclips a fan from the notch corner Th down to non-adjacent bottom-arc samples. That fan is a valid fill of the unroll. In XYZ the diagonals are chords through the pad (the purple spike). `CAD_Tess.CylChordRefine` runs after XYZ restore, only on triangles this face just emitted. A triangle whose centroid is more than 0.2 mm off the cylinder is split on its longest edge; the midpoint is projected back onto the cylinder. Cap 2500 adds. Integer triangle indices use `LessThan`, not `CAD_Num.Le` (that is `Float_Le`).
3. **Wireframe fan on the rolling-ball end.** After (1) and (2), Wire mode still showed a spider on the fillet’s straight end wall. That wall is planar `kind=1`, `nring=5`, `|Nz|=0`, so `MeshSolid` called `MeshLoopFanTess` from the far corner across the quarter-circle. Raw XY earclip cannot take it: shoelace in XY is ~0 on a Y-normal (or X-normal) face. Fix: `MeshPlanarDrop` drops the dominant normal axis (Y: swap y/z; X: cycle xyz→yzx), runs the existing dedup/orient/earclip, then restores XYZ. `EarClipPoly` clips the ear with the smallest max edge instead of the first ear — first-ear still fans that quarter-circle (Python: 8/8 long). Smallest-ear nibbles the ~4 mm arc ears first. The non-strict test, `o==0` keep, CW reverse, strict retry, and centroid fan fallback stay. Do not strip `o==0` samples.

1-line after the fan install: `end mer=9 end fan=0`, mesh nt=575, `wall chord bad=0 worst_um=196`. 3-line: `lid_short=1 wall_nring=6`, mesh nt=2987, chord bad=0. Fillet faces stay `MeshRuledLoop`. The inward-arc lid and bottom are concave; a boundary triangulation still draws long diagonals there. That is not the rolling-ball end. Do not “fix” it by stripping arc samples or by sending those faces through `CylLoopUV` / `RuledLoop`.

4. **Arc-end wedge (the shaded screenshot).** `FilletPlexNotchEllipse` used to cut the host cylinder with the plane through the host axis and Th/Tw. On the R=54 GUI pad that ellipse spans ~0.22 rad and sags 0.17 mm, while the rolling-ball nose sags 2.4 mm. `MeshRuledLoop` then ruled the R=8 quarter-circle onto that chord, so the fillet face was a chamfer. The straight-end fan fix did not touch this rail. Fix: plane through Th, Tw, and the fillet bisector shot along the axis onto the host; the ellipse is that plane ∩ the fillet cylinder (`rmin` = fillet R, `rmaj` = R/|N·axis|). Both one-Th and two-Th go through this function. Unequal-radius cylinder intersection is degree-4; this section is within 0.06 mm of that curve and of the host, and the eccentric angle is the fillet angle, so the existing index zip stays on the cylinder (probe `mid df_um=0`). Do not start a degree-4 solver. Do not flip the hidx reversal. Do not send the fillet face through `CylLoopUV`.

After this ellipse (2026-10-30): probe R=54 `notch ell rmaj_um=8554`, ellipse `sp=1587 r=8`, `rail sag_um=2400`, `nose d_um=0`, `mid n=433 df_um=0`, mesh nt=1474. 1-line on that binary: `nose n=7 host=0`, `end mer=9 end fan=0`, chord bad=0 worst_um=197, nt=561, `rmaj_um=8433`. 3-line: `lid_short=1 wall_nring=6` both ends, chord bad=0 worst_um=193, nt=2799, north topo ok. That binary is `cad_app_ell` (`d142147c…`). It still fanned the rear wall.

5. **Rear-wall starburst and top diagonals (the Front/ISO screenshots).** Same bug on two faces. The notch arc’s sense bit does not match its coedge origin (slot 5). `CollectLoopVerts` used to reverse from sense, so the wall coedge (sense 0, origin = Th = edge v0) walked far→Th, and the lid twin (sense 1, origin = far = edge v1) did not reverse. Both rings jumped ~43 mm from Th to the far end, then stepped back along the arc. `MonoStrip` rejected that ring (`mono mono ch=2 drop=-1954`). Earclip then fanned the cylinder from the fillet corner, and the lid drew the same long diagonals. The fillet face (`nring=4` kind=2 `RuledLoop`) was not this bug.

Fix, tessellation only: `CAD_Tess.CoedgeRev`. An open arc (edge v0≠v1) reverses iff the coedge origin equals edge v1, so the first sample is the origin. If the origin matches neither end, fall back to sense==0. A closed circle (v0==v1) still reverses iff sense==0. Called from the CIRCLE and ELLIPSE branches of `CollectLoopVerts` after sampling. Do not change the sense bit in `FilletPlex`; the origin is already the walk start. Do not change `MeshLoopFanTess` (it still uses sense).

With the ring in order, the one-Th host wall (`nring=5` kind=2) is x-monotone. `CAD_Tess.MonoStrip` (de Berg) emits a strip: one θ-step by the face height. `CylChordRefine` then adds 0. If `MonoStrip` returns &lt;0, `MeshCylLoopUV` still falls back to `EarClipPoly` plus `FlipDelaunay`. Do not run `MonoStrip` on the lid. `PlanarLongRefine` was deleted; do not put a longest-edge split back on the lid. `EarClipPoly` itself is unchanged. The lid goes through ordinary XY earclip on a loop that no longer doubles back (keyhole nt 51→50).

1-line after CoedgeRev: `lid_one=1 wall_nring=5`, `mono nt=94 dx=1982`, `cyl refine n=0`, mesh nt=334, `end mer=9 end fan=0`, `wall chord bad=0 worst_um=38`. 3-line: `mono nt=137 dx=2027`, `cyl refine n=0`, mesh nt=2684, chord bad=0 worst_um=38, north topo ok. `dx` is one ~2 mm sample, not a face-length diagonal.

## Live binary

- `./cad_app.x` from `/tmp/cad_app_sew.x`, 2576210 bytes, sha256 `0c2a5e8120546887a4517c75b30338d06b6cd9b44240eceb93ca0ae8d2137144` (Oct 30 22:07). Same tess and the same `CA_WriteHist` locals as `cad_app_hist` (`6aa7393b…`), plus the profile collapse below. Previous ellipse (`d142147c…`) still fanned the rear wall.
- `./ailang.x` **untouched** (sha256 `67e25f5b47f77bb461f7b7aad5f719aaa2ea7ddc403a569fe9d3a7962cf65c37`, Oct 24). Do not overwrite it. Do not launch the GUI unless asked. Restart: `CAD/scripts/run_cad_app.sh`.
- Log: `/tmp/cad_app/fillet_math.log`. Session: `/tmp/cad_app/session.log`.

## Prune stacked a second pad (the diagonal and the dark arc wall)

Not a fillet recipe. The session after the strip install: one `ipc repad` built the pad (`shells=1`), the side fillet notched (`nTh=2`, history 7/7), then Prune deleted a fillet and `CA_RepoReplayFeats` swept the same extrude twice (`sweep plex` twice, then `fillet shells=2 faces=15`). The 3-edge apply logged `junc=0 nsel=0`, no shorten, Steinmetz `meet ok` only at the square corners `(±25,-25,20)`, and `notch nTh=0`. The dark vertical band is the second shell's arc wall. The long crease is the untrimmed fillet on that compound. `replay pads=4` was a lie: `CA_WriteHist` stored the history kind in `CadAppRepo.n`, and 4 is Fillet.

Cause: `CA_WriteHist` used `CadAppRepo.feat_i` as its line index. Replay's cursor is that same field. `CA_HistPush` after the extrude reset the cursor, the loop stepped back onto the extrude, and `CompoundAdd` stacked the copy (`GlueOnFace` misses on two coincident pads). History then showed Extrude Extrude Fillet Fillet because the extrude was pushed twice.

Fix: `CA_WriteHist` walks with locals `hi` and `hk`. It does not touch `feat_i` or `CadAppRepo.n`. Fillet math and tess are unchanged. Remake the pad, or Prune once so replay builds a single shell, then fillet. A single-pad 3-edge apply must log `notch nTh=2` and `shells=1`. The headless 3-line gate already does that and was not re-run for this app-only change. Do not rename `hi`. Disassembly of the hist binary showed it is `[rbp-0x8]`, not `CAD_SPlex.hi`.

## Caps not sewn, projected fill empty (history 5/5 Extrude)

Not tess and not the fill painter. The pad in that session was `sweep plex n=12`, `sol: ncurve=12`, `sol: pick nn=72` (4 arc pieces × 16 samples + 8 line pieces). The last good pad on the same sources was `n=4` / `nn=19`. Twelve short curves do not sew the top and bottom to one arc. The 72-gon strokes a red outline and even-odd fills nothing when the pieces overlap. `CA_WriteHist`'s `hi` is not the cause.

Fix: `SketchPlexCollapse` in `Library.SketchPlex.ailang`, called from `SketchPlexWalkOne` after the dup filter and before `SketchPlexSample`. Consecutive collinear line pieces and cocircular same-direction arc pieces become one new plex node (travel order, `crev=0`, not inserted in the segment ring). A same-curve reversal is dropped. A 90° corner stays. If a pass would leave fewer than 3 edges and nothing valid was kept, that walk is rejected. A clean 4-corner path is unchanged.

Gates after the edit: RECT PLEX OK (centered and corner `nseg=4`). ARC PROFILE OK: clean 3-LINE+arc `nprof=1 nn=19 nseg=4`; the same keyhole with each line and the arc split in half collapses `8→4`, `nn=19`, one arc whose span is the full arc. GUI was not launched. Restart `CAD/scripts/run_cad_app.sh` (binary is newer than the sources). Remake the pad. The sweep log must show `sweep plex n=4` and `pick nn=19`. The projected fill is that 19-gon. Top and bottom are the one arc.

## What already works (do not regress)

- 2D profile fill/pick: Pick/Profiles stay `mode=1`. `IpcT` tid=4 stays mode=1. `avail_fill` RGB(176,64,70). `CA_HitProfilePx` world even-odd. On-face gold points only. Do not git-checkout `CAD/App/{Profile,IpcT,IpcP,DrawSketch}.ailang` or the rest of `Librarys/Cad/SketchProfile/`. `SketchPlexCollapse` stays.
- Extrude of 3-LINE+inward-arc pad.
- `n=1` box LINE method 9 (planar walls). `n=1` CIRCLE method 6 torus.
- Gates (2026-10-30, after CoedgeRev + MonoStrip): RECT PLEX OK, ARC PROFILE OK, ALL SIMPLE PADS OK, FILLET EDGE/HORIZ/CYL OK, FILLET 1LINE ARC OK (`lid_one=1 wall_nring=5`, `mono nt=94 dx=1982`, `cyl refine n=0`, `end mer=9 end fan=0`, chord bad=0 worst_um=38, nt=334), FILLET 3LINE ARC OK (`lid_short=1 wall_nring=6`, `mono nt=137 dx=2027`, `cyl refine n=0`, chord bad=0 worst_um=38, nt=2684, north topo ok).

## Topology that landed (headless)

- Sequential `n≥2` + two Th: `FilletPlexNotchHost` + `NotchSew`. Lid CIRCLE → Th–Th. Wall `nring=6`. Kind=2 mer skip stays. Gate south/north `lid_short=1 wall_nring=6`.
- Method 9 `n=1` + one Th: Case 9 calls `FilletPlexResolveNotch` after EdgeLocal. `n_th==1` → `FilletPlexNotchHostOne` + `NotchSewOne`. Lid CIRCLE → **far–Th**. One fillet-cylinder ellipse at Th (plane through Th, Tw, and the bisector on the host). Wall `nring=5`. Gate: `notch nTh=1 nHost=1` Th=17,-22 far=-24,-24 sew n=1 `wall_nring=5` `end fan=0` `nose n>=1 host=0` mesh nt=334 (`mono nt=94 dx=1982`, refine n=0). `CAD/demo_fillet_1line_arc.ailang`.
- Kind=2 mer is **not** sewn into the cylinder (`mer skip cyl seq`). Ellipse is the terminator. `FilletPlexNotchRetargetMer` Z-guard: skip same-Z lid rails (`retarget mer skip lid`).
- ShortenRailEnd at junc=5 before MakeVertex. Mer sew into planar end wall uses `FilletMerCloser`.

Headless topology, the host-cylinder chord gate, the arc-end nose, and the rear-wall strip pass on this install. The starburst in the pre-restart Front/ISO screenshots is the sense/origin reversal. The rolling-ball side was already accepted.

## Tess rules (broken twice — do not repeat)

`Librarys/Cad/Tess/Library.TessFace.ailang` MeshSolid:

- `nring==4`: HEAD. torus if kind=4; else plane+|Nz|≥0.5+LoopHasCircle → XY; else `MeshRuledLoop`.
- `nring==6` kind=2: exclusive `pack[7]=2 MeshCylLoopUV`, RuledLoop only if pack[7]==0. CylLoopUV clobbers `use_zip`; a second If on use_zip==0 starred the lid (full bottom CIRCLE zipped onto short top).
- `nring==5` **horizontal** (`|Nz|≥0.5`) → XY. `nring==5` kind=2 → CylLoopUV in that same path. `nring==5` vertical planar → `MeshPlanarDrop` (`pack[7]=4`), not raw XY and not `MeshLoopFanTess`. Do **not** send all nring=5 through RuledLoop (that broke pad/profile tess, n1 withdrawn).
- `CollectLoopVerts` LINE path is **one origin vertex**. Dense 2 mm LINE samples broke 3-LINE+arc XY earclip (nstar withdrawn).
- Do not send `nring==4` kind=2 through CylLoopUV.
- `CAD_Tess.CylChordRefine` (TessCollect, end of `MeshCylLoopUV` after XYZ restore) splits off-cylinder chords. After a successful `MonoStrip` the 1-line wall adds 0. Do not “fix” a remaining spike by routing nring=5 through RuledLoop, by dense LINE sampling, or by sending nring=4 through CylLoopUV.
- `CAD_Tess.CoedgeRev`: open circle and ellipse samples start at the coedge origin. Closed circles still use sense. `CAD_Tess.MonoStrip` runs only inside `MeshCylLoopUV`, before the earclip fallback. Success prints `mono nt=` and `dx=` (µm). A fan cannot be turned into a strip by longest-edge refine.
- `EarClipPoly` clips the smallest max-edge ear. Keep the non-strict occupancy test, `o==0` samples, CW reverse, strict retry, and the centroid fan fallback. Do not strip `o==0` (that chords circles). The concave lid/bottom still diagonals; that is the reflex arc, not a stalled earclip.

## Locked constraints

Plex exclusive. All-LINE `n≥2` method 1. Left/right same function. Method 10 unassigned. MixFixSharp reason 12 stays. No special MIXED classify. Emit-time terminator, not a post-pass.

**Do not restore:** CloseBot, CylClipVert, SampleEllipseByEnds-as-stitch, line-stitch, θ-zip, N2 PointInSolid flip, inner=0→mode=2, CircleEnd of host, ClipHostArc, CylMer+sew, RailArcShift, Junc5*.

Nested `CAD_Store.Read` in If / nested call-args can GPF. Flatten to locals. Nested FixedPool field-read clobbers. Do not MeshSolid two solids in one process (`CAD_Tess_State.samp` sticks → SampleCurve SEGV).

## Files

| Path | Role |
|------|------|
| `Librarys/Cad/Topo/Library.FilletPlex.ailang` | NotchHost / NotchHostOne / NotchSew / NotchSewOne / ResolveNotch / Case 9 |
| `Librarys/Cad/Topo/Library.Fillet.ailang` | EdgeLocal, kind=2 skip, ShortenRailEnd call, FilletMerCloser |
| `Librarys/Cad/Topo/Library.FilletSeq.ailang` | Sequential then ResolveNotch |
| `Librarys/Cad/Tess/Library.TessFace.ailang` | MeshSolid dispatch |
| `Librarys/Cad/Topo/Library.Extrude.ailang` | `SweepEmitCurve` zeros `fr[9]`/`fr[10]` before `MakeCylinderSurf` |
| `Librarys/Cad/Tess/Library.TessCollect.ailang` | CoedgeRev, CollectLoopVerts, MonoStrip, MeshCylLoopUV, CylChordRefine |
| `CAD/demo_fillet_1line_arc.ailang` | n=1 east LINE + south inward arc |
| `CAD/demo_fillet_3line_arc.ailang` | 4-LINE leftover, south 3-LINE+arc, north topo |
| `CAD/screenshots/junc5-latest.png` | this GUI |

Uncommitted fill-restore (keep): `CAD/App/{DrawSketch,IpcP,IpcT,Profile}.ailang`, `Librarys/Cad/SketchProfile/Library.SketchPlex.ailang`.

## Next session

1. Read this file and `FILLET_MULTI_SEGMENT.md`. The arc-end rail is the fillet-cylinder section in `FilletPlexNotchEllipse`. The rear host wall is `CoedgeRev` plus `MonoStrip` (`mono nt=94 dx=1982`, refine n=0 on the 1-line). The straight-end fan is `MeshPlanarDrop` plus smallest-ear. Do not relaunch a tess rewrite of LINE sampling, nring==4 / nring==6 dispatch, or the hidx reversal. Do not run `MonoStrip` on the lid.
2. Restart `CAD/scripts/run_cad_app.sh`. The installed binary is `cad_app_hist` (sha256 `6aa7393b…`). It is newer than the sources, so the script will not rebuild. Remake the pad (or Prune once). The next 3-edge fillet must be one shell. `notch nTh=0` with `shells=2` means the replay cursor bug is back. The starburst in the pre-strip Front/ISO screenshots stays the sense/origin reversal.
3. The fillet side stays the rolling ball. The rear wall should be a short-edge strip (max step ~2 mm, chord worst 38 µm). The top should no longer draw the Th-to-far diagonals. The straight end stays `end fan=0`. Host-wall chord gate stays `bad=0`.
4. Do not start a degree-4 bicylinder solver. Th, Tw, and the fillet bisector already determine a plane whose section of the fillet cylinder is within 0.06 mm of the true curve, and `mid df_um=0` says the ruled zip stays on that cylinder. Do not change the notch sense bit in `FilletPlex`.
