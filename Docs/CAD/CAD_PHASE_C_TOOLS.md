# Phase C — Solid tools (B-Rep ops)

**Parent:** `CAD_CORE_COMPETITIVE_PLAN.md`  
**After:** Phase B (pad/cut/revolve)

## Sub-phases

| Sub | Name | Status |
|-----|------|--------|
| **C1** | Hole tool (existing CreateHole) | done earlier |
| **C2** | Poly pocket / through cut | B2 ExtrudeCut poly |
| **C3** | Plane–cyl fillet | open |
| **C4** | Chamfer vertical box corner | **done** `ChamferEdge` |
| **C5** | Bool domain: coaxial cyl−cyl | **done** → annulus |
| **C6** | Rigid transform | **done** Translate + `RotateSolidZ` + multi-shell walk |
| **C7** | Clone + pattern of non-box | **done** `CloneKind0`, Linear/CircularPattern, Mirror |
| **C8** | Loft / sweep | **done** `MakeRuledSolid`, `LoftProfiles`, `SweepProfile` |

## Domains

| Op | Domain |
|----|--------|
| ChamferEdge | kind-0 box, full-height vertical **corner** edge, equal setback D → 5-gon prism |
| Difference cyl−cyl | coaxial, same height/base, ra>rb → MakeAnnulusPrism |
| RotateSolidZ | kind 0 verts (all shells); kind 1/2 axis; kind 3 plate; kind 4 sphere |
| CloneKind0 | first shell only; plane faces + line edges; ≤256 verts |
| LinearPattern | kind-0 seed → Clone + Translate × (count−1) → CompoundAdd |
| CircularPattern | about AABB center; true spin (not AABB box copies) |
| Mirror | Clone + ReflectSolid about AABB mid (axis 0/1/2) |
| LoftProfiles | two sketches, same n loop pts, zpack [z0,z1] |
| SweepProfile | sketch + path [x,y,z]×npath; consecutive samples must change Z |

## Gates

```bash
./CAD/smoke_phase_c.sh
./CAD/smoke_part_design.sh   # pattern + loft + sweep + diamond pattern
```
