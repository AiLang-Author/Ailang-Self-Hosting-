#!/usr/bin/env python3
"""Split Library.CAD_Topo.ailang on Function.*/FixedPool. boundaries.

Callers keep LibraryImport.Cad.CAD_Topo. The facade inlines Cad.Topo.* parts.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Librarys/Cad/Library.CAD_Topo.ailang"
OUT_DIR = ROOT / "Librarys/Cad/Topo"
FACADE = ROOT / "Librarys/Cad/Library.CAD_Topo.ailang"
BACKUP = ROOT / "Librarys/Cad/Library.CAD_Topo.ailang.pre_split"

# (start_name, file_stem) — item stays in that file until the next cut.
# Names are the Function.CAD_Topo.X or FixedPool.CAD_Topo_Y token.
CUTS = [
    ("FixedPool.CAD_Topo_State", "Core"),
    ("Function.CAD_Topo.MakeTriangleSolid", "MakePrism"),
    ("Function.CAD_Topo.ChamferPrismCap", "MakeCap"),
    ("Function.CAD_Topo.MakeRuledSolid", "MakeSweep"),
    ("Function.CAD_Topo.MakeCylinderSolid", "MakeCyl"),
    ("Function.CAD_Topo.MakeBoxThroughHole", "MakePlate"),
    ("Function.CAD_Topo.MakeBoxRectPocketSolid", "MakeBoxFeat"),
    ("Function.CAD_Topo.MakeBoxRectNotchXSolid", "MakeBoxFeat2"),
    ("Function.CAD_Topo.EdgeIncidentFaces", "Query"),
    ("Function.CAD_Topo.RebuildKind0Planes", "Xform"),
    ("Function.CAD_Topo.MakeMinorArcEdge", "Fillet"),
    ("Function.CAD_Topo.Solve3Planes", "Digon"),
    ("Function.CAD_Topo.DigonMakeCap", "Digon2"),
]

IMPORTS = """LibraryImport.Cad.CAD_Store
LibraryImport.Cad.CAD_Num
LibraryImport.Cad.CAD_Geom
"""

PARTS = [
    "Core",
    "MakePrism",
    "MakeCap",
    "MakeSweep",
    "MakeCyl",
    "MakePlate",
    "MakeBoxFeat",
    "MakeBoxFeat2",
    "Query",
    "Xform",
    "Fillet",
    "Digon",
    "Digon2",
]


def parse_items(text: str) -> list[tuple[int, str, int]]:
    lines = text.splitlines(keepends=True)
    starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if line.startswith("Function.") or line.startswith("FixedPool."):
            starts.append((i, line.strip().split()[0].rstrip("{")))
    items: list[tuple[int, str, int]] = []
    for n, (i, name) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        items.append((i, name, end))
    return items


def assign_file(name: str) -> str:
    current = CUTS[0][1]
    for cut_name, stem in CUTS:
        if name == cut_name:
            current = stem
            return current
        # walk: once we have passed a cut that this name comes after, stay
    # fallback: find last cut whose name is <= this in the item list by applying sequentially
    return current


def bucket_items(items: list[tuple[int, str, int]]) -> dict[str, list[tuple[int, str, int]]]:
    buckets: dict[str, list[tuple[int, str, int]]] = {p: [] for p in PARTS}
    current = CUTS[0][1]
    cut_at = {n: s for n, s in CUTS}
    for item in items:
        name = item[1]
        if name in cut_at:
            current = cut_at[name]
        buckets[current].append(item)
    return buckets


def header_block(src_lines: list[str], first_item_i: int) -> str:
    # Keep the file banner comments only (before first FixedPool).
    return "".join(src_lines[:first_item_i]).rstrip() + "\n\n"


def write_part(stem: str, body: str) -> Path:
    path = OUT_DIR / f"Library.{stem}.ailang"
    text = (
        f"// CAD.Topo.{stem} — split from Library.CAD_Topo.ailang\n"
        f"// API stays Function.CAD_Topo.*  (facade: LibraryImport.Cad.CAD_Topo)\n\n"
        f"{IMPORTS}\n"
        f"{body.rstrip()}\n"
    )
    path.write_text(text)
    return path


def main() -> None:
    src = SRC.read_text()
    if not BACKUP.exists():
        BACKUP.write_text(src)
        print(f"backup {BACKUP}")
    lines = src.splitlines(keepends=True)
    items = parse_items(src)
    if not items:
        raise SystemExit("no Function./FixedPool. items")
    buckets = bucket_items(items)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("buckets:")
    for stem in PARTS:
        nlines = sum(e - s for s, _, e in buckets[stem])
        print(f"  {stem:14s}  items={len(buckets[stem]):2d}  lines={nlines:5d}")
        body = "".join("".join(lines[s:e]) for s, _, e in buckets[stem])
        write_part(stem, body)

    facade = """// CAD.Topo — radial-edge B-Rep over CAD_Store (facade).
// Split modules live in Librarys/Cad/Topo/. One import still loads all:
//   LibraryImport.Cad.CAD_Topo
//
//   Topo.Core         MakeVertex/Edge/Face, CompoundAdd, pools
//   Topo.MakePrism    triangle / box / wedge / poly prism
//   Topo.MakeCap      chamfer/fillet prism caps, prism-with-holes
//   Topo.MakeSweep    ruled / sweep / annulus / frustum / plate-hole
//   Topo.MakeCyl      cylinder / lathe
//   Topo.MakePlate    plate hole shells / sphere
//   Topo.MakeBoxFeat  box pocket / side hole
//   Topo.MakeBoxFeat2 box notch / boss
//   Topo.Query        FaceGet* / pick / bounds
//   Topo.Xform        RebuildKind0Planes / Map / Translate
//   Topo.Fillet       plane-plane edge fillet
//   Topo.Digon        digon solve
//   Topo.Digon2       digon build / FilletPlaneEdges
//
// Tags: 1=Vertex 2=Edge 3=Coedge 4=Loop 5=Face 6=Shell 7=Solid

LibraryImport.Cad.CAD_Store
LibraryImport.Cad.CAD_Num
LibraryImport.Cad.CAD_Geom
"""
    for stem in PARTS:
        facade += f"LibraryImport.Cad.Topo.{stem}\n"
    FACADE.write_text(facade + "\n")
    print(f"wrote facade {FACADE} ({FACADE.stat().st_size} bytes)")
    for stem in PARTS:
        p = OUT_DIR / f"Library.{stem}.ailang"
        n = sum(1 for _ in p.open())
        print(f"  {p.relative_to(ROOT)}  {n} loc")


if __name__ == "__main__":
    main()
