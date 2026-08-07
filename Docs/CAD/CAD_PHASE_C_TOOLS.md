# Phase C — Solid tools (B-Rep ops)

**Parent:** `CAD_CORE_COMPETITIVE_PLAN.md`  
**After:** Phase B (pad/cut/revolve)

## Sub-phases

| Sub | Name | Status |
|-----|------|--------|
| **C1** | Hole tool (existing CreateHole) | done earlier |
| **C2** | Poly pocket / through cut | B2 ExtrudeCut poly |
| **C3** | Plane–cyl fillet | open |
| **C4** | Chamfer vertical (general prism) | **done** `ChamferEdge` / `ChamferEdges` |
| **C5** | Bool domain: coaxial cyl−cyl | **done** → annulus |
| **C6** | Rigid transform | **done** Translate + `RotateSolidZ` + multi-shell walk |
| **C7** | Clone + pattern of non-box | **done** `CloneKind0`, Linear/CircularPattern, Mirror |
| **C8** | Loft / sweep | **done** `MakeRuledSolid`, `LoftProfiles`, `SweepProfile` |

## Domains

| Op | Domain |
|----|--------|
| ChamferEdge / ChamferEdges | kind-0 **prism** (box/poly/prior chamfer); full-height vertical edges; equal setback D along base edges; rebuild `MakePolyPrism` |
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
./CAD/smoke_part_design.sh   # pattern + loft + sweep + diamond + edges/negatives
```

### Edge / negative honesty (`demo_pd_edges`)

| Case | Expected |
|------|----------|
| Loft unequal n / equal Z / null sketch | 0 |
| Sweep npath&lt;2 / flat Z / null | 0 |
| Pattern count&lt;1 / null / kind-1 cyl | 0 |
| Mirror null / kind-1 | 0 |
| CloneKind0 null / kind-1 | 0 |
| Pattern count=1 | identity handle |
| Sweep 3-segment path | solid, 12 faces (2 shells) |
| Mirror diamond | solid, 12 faces |
