#!/usr/bin/env python3
"""Split an AILang library on Function.*/FixedPool. boundaries.

No top-level code — each part is functions + the same imports.
Fixed pools stay with the functions that own them (or in Topo.Core).

Usage (from repo root):
  python3 tools/cad_split_ailang.py           # all CAD over-1500 jobs
  python3 tools/cad_split_ailang.py fillet query tools
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def topo_imports() -> str:
    return """LibraryImport.Cad.CAD_Store
LibraryImport.Cad.CAD_Num
LibraryImport.Cad.CAD_Geom
"""


def sketch_imports() -> str:
    return """LibraryImport.Cad.CAD_Store
LibraryImport.Cad.CAD_Num
LibraryImport.Cad.CAD_Geom
"""


APP_IMPORTS_COMMON = """LibraryImport.Arena
LibraryImport.UtilArgs
LibraryImport.Cad.CAD_Sys
LibraryImport.Cad.CAD_Num
LibraryImport.Cad.CAD_Store
LibraryImport.Cad.CAD_Sketch
LibraryImport.Cad.CAD_DXF
LibraryImport.Cad.CAD_Feat
LibraryImport.Cad.CAD_IO
LibraryImport.Cad.CAD_Geom
LibraryImport.Cad.CAD_View
LibraryImport.Cad.CAD_Repo
LibraryImport.Cad.CAD_Topo
LibraryImport.Cad.CAD_Plane
LibraryImport.Cad.CAD_Bool
LibraryImport.Display.Render.Framebuffer
LibraryImport.StringUtils
"""

APP_IMPORTS_TOOLS = APP_IMPORTS_COMMON.replace(
    "LibraryImport.Cad.CAD_Bool\n",
    "LibraryImport.Cad.CAD_Bool\nLibraryImport.Cad.CAD_UI\n",
)

APP_IMPORTS_SOLID = APP_IMPORTS_COMMON.replace(
    "LibraryImport.Cad.CAD_View\n",
    "LibraryImport.Cad.CAD_View\nLibraryImport.Cad.CAD_Tess\n",
).replace(
    "LibraryImport.Cad.CAD_Bool\n",
    "LibraryImport.Cad.CAD_Bool\nLibraryImport.Cad.CAD_Blend\n",
)

APP_IMPORTS_DRAW = APP_IMPORTS_COMMON.replace(
    "LibraryImport.Cad.CAD_View\n",
    "LibraryImport.Cad.CAD_View\nLibraryImport.Cad.CAD_Tess\n",
).replace(
    "LibraryImport.Cad.CAD_Bool\n",
    "LibraryImport.Cad.CAD_Bool\nLibraryImport.Cad.CAD_UI\n",
)

APP_IMPORTS_STATE = APP_IMPORTS_TOOLS
APP_IMPORTS_DOC = APP_IMPORTS_TOOLS
APP_IMPORTS_PLANE = APP_IMPORTS_COMMON


JOBS = {
    # --- already-split facades (idempotent if src is still the monolith) ---
    "tess": {
        "mode": "facade",
        "src": ROOT / "Librarys/Cad/Library.CAD_Tess.ailang",
        "backup": ROOT / "Librarys/Cad/Library.CAD_Tess.ailang.pre_split",
        "out_dir": ROOT / "Librarys/Cad/Tess",
        "facade": ROOT / "Librarys/Cad/Library.CAD_Tess.ailang",
        "import_prefix": "Cad.Tess",
        "api": "Function.CAD_Tess.*",
        "caller": "LibraryImport.Cad.CAD_Tess",
        "part_imports": """LibraryImport.Cad.CAD_Sys
LibraryImport.Cad.CAD_Store
LibraryImport.Cad.CAD_Num
LibraryImport.Cad.CAD_Topo
LibraryImport.Cad.CAD_Geom
LibraryImport.StringUtils
""",
        "facade_extra": """LibraryImport.Cad.CAD_Sys
LibraryImport.Cad.CAD_Store
LibraryImport.Cad.CAD_Num
LibraryImport.Cad.CAD_Topo
LibraryImport.Cad.CAD_Geom
LibraryImport.StringUtils
""",
        "cuts": [
            ("FixedPool.CAD_Tess_State", "TessCore"),
            ("Function.CAD_Tess.MeshCylinderAnalytic", "TessAnalytic"),
            ("Function.CAD_Tess.EarClipPoly", "TessEarclip"),
            ("Function.CAD_Tess.CollectLoopVerts", "TessCollect"),
            ("Function.CAD_Tess.PointInIdxPoly", "TessHole"),
            ("Function.CAD_Tess.ZipperTriHole", "TessZip"),
            ("Function.CAD_Tess.ValidInnerLoop", "TessFace"),
        ],
        "banner": "CAD.Tess — mesh generation + STL (facade).",
    },
    "sketchprofile": {
        "mode": "facade",
        "src": ROOT / "Librarys/Cad/Library.CAD_SketchProfile.ailang",
        "backup": ROOT / "Librarys/Cad/Library.CAD_SketchProfile.ailang.pre_split",
        "out_dir": ROOT / "Librarys/Cad/SketchProfile",
        "facade": ROOT / "Librarys/Cad/Library.CAD_SketchProfile.ailang",
        "import_prefix": "Cad.SketchProfile",
        "api": "Function.CAD_Sketch.*",
        "caller": "LibraryImport.Cad.CAD_SketchProfile",
        "part_imports": sketch_imports(),
        "facade_extra": sketch_imports(),
        "cuts": [
            ("Function.CAD_Sketch.BuildClosedLoop", "Loop"),
            ("Function.CAD_Sketch.TessellateCircles", "Tess"),
            ("Function.CAD_Sketch.SnapNearEndpoints", "Snap"),
        ],
        "banner": "CAD.SketchProfile — loops / tess / snap (facade).",
    },
    # --- CAD kernel: sibling files, CAD_Topo facade gains imports ---
    "fillet": {
        "mode": "siblings",
        "src": ROOT / "Librarys/Cad/Topo/Library.Fillet.ailang",
        "backup": ROOT / "Librarys/Cad/Topo/Library.Fillet.ailang.pre_split",
        "out_dir": ROOT / "Librarys/Cad/Topo",
        "api": "Function.CAD_Topo.*",
        "caller": "LibraryImport.Cad.CAD_Topo",
        "part_imports": topo_imports(),
        "import_prefix": "Cad.Topo",
        "parent_facade": ROOT / "Librarys/Cad/Library.CAD_Topo.ailang",
        "facade_after": "LibraryImport.Cad.Topo.Fillet",
        "cuts": [
            ("Function.CAD_Topo.MakeMinorArcEdge", "Fillet"),
            ("Function.CAD_Topo.FilletVertNote", "FilletVertex"),
            ("Function.CAD_Topo.FilletPlanePlaneEdge_UNUSED_START", "FilletUnused"),
        ],
        "park": {"FilletUnused"},
        "banner": "CAD.Topo.Fillet",
    },
    "filletseq": {
        "mode": "siblings",
        "src": ROOT / "Librarys/Cad/Topo/Library.Digon2.ailang",
        "backup": ROOT / "Librarys/Cad/Topo/Library.Digon2.ailang.pre_split",
        "out_dir": ROOT / "Librarys/Cad/Topo",
        "api": "Function.CAD_Topo.*",
        "caller": "LibraryImport.Cad.CAD_Topo",
        "part_imports": topo_imports(),
        "import_prefix": "Cad.Topo",
        "parent_facade": ROOT / "Librarys/Cad/Library.CAD_Topo.ailang",
        "facade_after": "LibraryImport.Cad.Topo.Digon2",
        "cuts": [
            ("Function.CAD_Topo.DigonBindCoedge", "Digon2"),
            ("Function.CAD_Topo.FilletEdgesSequential", "FilletSeq"),
        ],
        "banner": "CAD.Topo.Digon2 / FilletSeq",
    },
    "query": {
        "mode": "siblings",
        "src": ROOT / "Librarys/Cad/Topo/Library.Query.ailang",
        "backup": ROOT / "Librarys/Cad/Topo/Library.Query.ailang.pre_split",
        "out_dir": ROOT / "Librarys/Cad/Topo",
        "api": "Function.CAD_Topo.*",
        "caller": "LibraryImport.Cad.CAD_Topo",
        "part_imports": topo_imports(),
        "import_prefix": "Cad.Topo",
        "parent_facade": ROOT / "Librarys/Cad/Library.CAD_Topo.ailang",
        "facade_after": "LibraryImport.Cad.Topo.Query",
        "cuts": [
            ("Function.CAD_Topo.EdgeIncidentFaces", "Query"),
            ("Function.CAD_Topo.EdgeInLoop", "QueryWalk"),
        ],
        "banner": "CAD.Topo.Query",
    },
    "makecyl": {
        "mode": "siblings",
        "src": ROOT / "Librarys/Cad/Topo/Library.MakeCyl.ailang",
        "backup": ROOT / "Librarys/Cad/Topo/Library.MakeCyl.ailang.pre_split",
        "out_dir": ROOT / "Librarys/Cad/Topo",
        "api": "Function.CAD_Topo.*",
        "caller": "LibraryImport.Cad.CAD_Topo",
        "part_imports": topo_imports(),
        "import_prefix": "Cad.Topo",
        "parent_facade": ROOT / "Librarys/Cad/Library.CAD_Topo.ailang",
        "facade_after": "LibraryImport.Cad.Topo.MakeCyl",
        "cuts": [
            ("Function.CAD_Topo.MakeCylinderSolid", "MakeCyl"),
            ("Function.CAD_Topo.MakeLatheClosed", "MakeLathe"),
        ],
        "banner": "CAD.Topo.MakeCyl",
    },
    # --- CAD_Sketch: keep pools/CRUD in the facade file, extract the rest ---
    "sketch": {
        "mode": "extract",
        "src": ROOT / "Librarys/Cad/Library.CAD_Sketch.ailang",
        "backup": ROOT / "Librarys/Cad/Library.CAD_Sketch.ailang.pre_split",
        "api": "Function.CAD_Sketch.*",
        "caller": "LibraryImport.Cad.CAD_Sketch",
        "part_imports": sketch_imports(),
        "keep": "Sketch",
        "cuts": [
            ("FixedPool.CAD_Sketch_State", "Sketch"),
            ("Function.CAD_Sketch.AddConstraint", "Cstr"),
            ("Function.CAD_Sketch.AddPoint", "Geom"),
        ],
        "extract_paths": {
            "Cstr": ROOT / "Librarys/Cad/Library.CAD_SketchCstr.ailang",
            "Geom": ROOT / "Librarys/Cad/Library.CAD_SketchGeom.ailang",
        },
        "add_imports": [
            "LibraryImport.Cad.CAD_SketchCstr",
            "LibraryImport.Cad.CAD_SketchGeom",
        ],
        "banner": "CAD.Sketch",
    },
    # --- CAD/App facades (cad_app still Import.CAD.App.Tools etc.) ---
    "tools": {
        "mode": "facade",
        "src": ROOT / "CAD/App/Tools.ailang",
        "backup": ROOT / "CAD/App/Tools.ailang.pre_split",
        "out_dir": ROOT / "CAD/App",
        "facade": ROOT / "CAD/App/Tools.ailang",
        "local_import": "CAD.App",
        "file_prefix": "Tools",
        "api": "Function.CA_*",
        "caller": "Import.CAD.App.Tools",
        "part_imports": APP_IMPORTS_TOOLS,
        "facade_extra": APP_IMPORTS_TOOLS,
        "cuts": [
            ("Function.CA_SketchClick", "Snap"),
            ("Function.CA_BeginConstraint", "Cstr"),
            ("Function.CA_OnClick", "Click"),
            ("Function.CA_HudClose", "Hud"),
            ("Function.CA_TreeSelect", "Edit"),
            ("Function.CA_HudTab", "Poly"),
        ],
        "banner": "CAD/App/Tools — facade. Parts: ToolsSnap/Cstr/Click/Hud/Edit/Poly.",
    },
    "solid": {
        "mode": "facade",
        "src": ROOT / "CAD/App/Solid.ailang",
        "backup": ROOT / "CAD/App/Solid.ailang.pre_split",
        "out_dir": ROOT / "CAD/App",
        "facade": ROOT / "CAD/App/Solid.ailang",
        "local_import": "CAD.App",
        "file_prefix": "Solid",
        "api": "Function.CA_*",
        "caller": "Import.CAD.App.Solid",
        "part_imports": APP_IMPORTS_SOLID,
        "facade_extra": APP_IMPORTS_SOLID,
        "cuts": [
            ("Function.CA_CountProfiles", "Wire"),
            ("Function.CA_PromoteOuterHoles", "Prof"),
            ("Function.CA_BlendFeatEnsure", "Blend"),
            ("Function.CA_BuildSolid", "Pad"),
        ],
        "banner": "CAD/App/Solid — facade. Parts: SolidWire/Prof/Blend/Pad.",
    },
    "draw": {
        "mode": "facade",
        "src": ROOT / "CAD/App/Draw.ailang",
        "backup": ROOT / "CAD/App/Draw.ailang.pre_split",
        "out_dir": ROOT / "CAD/App",
        "facade": ROOT / "CAD/App/Draw.ailang",
        "local_import": "CAD.App",
        "file_prefix": "Draw",
        "api": "Function.CA_*",
        "caller": "Import.CAD.App.Draw",
        "part_imports": APP_IMPORTS_DRAW,
        "facade_extra": APP_IMPORTS_DRAW,
        "cuts": [
            ("Function.CA_ProfileProjColor", "Cam"),
            ("Function.CA_DrawSketchToFB", "Sketch"),
            ("Function.CA_BuildViewFrame", "View3"),
            ("Function.CA_DrawCircPreview", "Hud"),
        ],
        "banner": "CAD/App/Draw — facade. Parts: DrawCam/Sketch/View3/Hud.",
    },
    "state": {
        "mode": "facade",
        "src": ROOT / "CAD/App/State.ailang",
        "backup": ROOT / "CAD/App/State.ailang.pre_split",
        "out_dir": ROOT / "CAD/App",
        "facade": ROOT / "CAD/App/State.ailang",
        "local_import": "CAD.App",
        "file_prefix": "State",
        "api": "Function.CA_* / FixedPool.CadApp",
        "caller": "Import.CAD.App.State",
        "part_imports": APP_IMPORTS_STATE,
        "facade_extra": APP_IMPORTS_STATE,
        "cuts": [
            ("Function.DebugLog_Push", "Pools"),
            ("Function.CA_WriteFileStr", "Hud"),
            ("Function.CA_CurrentSkIdx", "Tree"),
        ],
        "banner": "CAD/App/State — facade. Parts: StatePools (CadApp) / Hud / Tree.",
    },
    "plane": {
        "mode": "facade",
        "src": ROOT / "CAD/App/Plane.ailang",
        "backup": ROOT / "CAD/App/Plane.ailang.pre_split",
        "out_dir": ROOT / "CAD/App",
        "facade": ROOT / "CAD/App/Plane.ailang",
        "local_import": "CAD.App",
        "file_prefix": "Plane",
        "api": "Function.CA_*",
        "caller": "Import.CAD.App.Plane",
        "part_imports": APP_IMPORTS_PLANE,
        "facade_extra": APP_IMPORTS_PLANE,
        "cuts": [
            ("Function.CA_PlaneOnTop", "Reg"),
            ("Function.CA_ImportFaceRefs", "Pick"),
            ("Function.CA_PlaneByPid", "Tree"),
        ],
        "banner": "CAD/App/Plane — facade. Parts: PlaneReg/Pick/Tree.",
    },
    "doc": {
        "mode": "facade",
        "src": ROOT / "CAD/App/Doc.ailang",
        "backup": ROOT / "CAD/App/Doc.ailang.pre_split",
        "out_dir": ROOT / "CAD/App",
        "facade": ROOT / "CAD/App/Doc.ailang",
        "local_import": "CAD.App",
        "file_prefix": "Doc",
        "api": "Function.CA_*",
        "caller": "Import.CAD.App.Doc",
        "part_imports": APP_IMPORTS_DOC,
        "facade_extra": APP_IMPORTS_DOC,
        "cuts": [
            ("Function.CA_PublishToolsJson", "Hist"),
            ("Function.CA_WriteListFiles", "List"),
            ("Function.CA_FormatFeatTree", "Repo"),
        ],
        "banner": "CAD/App/Doc — facade. Parts: DocHist/List/Repo.",
    },
}

DEFAULT_JOBS = [
    "fillet",
    "filletseq",
    "query",
    "makecyl",
    "sketch",
    "tools",
    "solid",
    "draw",
    "state",
    "plane",
    "doc",
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


def bucket_items(items, cuts):
    stems = [s for _, s in cuts]
    buckets = {s: [] for s in stems}
    cut_at = {n: s for n, s in cuts}
    current = stems[0]
    for item in items:
        if item[1] in cut_at:
            current = cut_at[item[1]]
        buckets[current].append(item)
    return stems, buckets


def already_facade(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text()
    n = text.count("\n")
    return n < 80 and ("LibraryImport." in text or "Import." in text) and "Function." not in text


def backup(path: Path, dest: Path) -> None:
    if not dest.exists():
        dest.write_text(path.read_text())
        print(f"  backup {dest.relative_to(ROOT)}")


def write_part(path: Path, banner: str, imports: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(banner + imports + "\n" + body.rstrip() + "\n")
    loc = sum(1 for _ in path.open())
    print(f"    wrote {path.relative_to(ROOT)}  {loc} loc")


def insert_after(facade: Path, after: str, new_lines: list[str]) -> None:
    text = facade.read_text()
    pending = [n for n in new_lines if n not in text]
    if not pending:
        return
    needle = after + "\n"
    if needle not in text:
        raise SystemExit(f"cannot find {after!r} in {facade}")
    addition = "".join(n + "\n" for n in pending)
    facade.write_text(text.replace(needle, needle + addition, 1))
    print(f"    facade + {pending} after {after}")


def run_facade(job: dict) -> None:
    src_path: Path = job["src"]
    if already_facade(src_path) and src_path == job["facade"]:
        print("  skip (already a facade)")
        return
    backup(src_path, job["backup"])
    src = src_path.read_text()
    lines = src.splitlines(keepends=True)
    items = parse_items(src)
    if not items:
        raise SystemExit(f"no items in {src_path}")
    stems, buckets = bucket_items(items, job["cuts"])
    out_dir: Path = job["out_dir"]
    local = job.get("local_import")
    file_prefix = job.get("file_prefix", "")
    import_prefix = job.get("import_prefix")
    for stem in stems:
        nlines = sum(e - s for s, _, e in buckets[stem])
        print(f"  {stem:14s}  items={len(buckets[stem]):2d}  lines={nlines:5d}")
        body = "".join("".join(lines[s:e]) for s, _, e in buckets[stem])
        if local:
            path = out_dir / f"{file_prefix}{stem}.ailang"
            banner = f"// {job['banner']} part {file_prefix}{stem}\n// API stays {job['api']}\n\n"
        else:
            path = out_dir / f"Library.{stem}.ailang"
            banner = (
                f"// {job['banner']} part {stem}\n"
                f"// API stays {job['api']}  (facade: {job['caller']})\n\n"
            )
        write_part(path, banner, job["part_imports"], body)

    if local:
        facade = f"// {job['banner']}\n\n"
        facade += job["part_imports"] + "\n"
        for stem in stems:
            facade += f"Import.{local}.{file_prefix}{stem}\n"
    else:
        facade = f"// {job['banner']}\n// Split parts via {job['caller']}\n\n"
        facade += job.get("facade_extra", "")
        for stem in stems:
            facade += f"LibraryImport.{import_prefix}.{stem}\n"
    job["facade"].write_text(facade + "\n")
    print(f"    facade {job['facade'].relative_to(ROOT)}")


def run_siblings(job: dict) -> None:
    src_path: Path = job["src"]
    backup(src_path, job["backup"])
    src = src_path.read_text()
    if "FilletEdgesSequential" not in src and job.get("cuts", [("", "")])[-1][1] == "FilletSeq":
        if (job["out_dir"] / "Library.FilletSeq.ailang").exists():
            print("  skip (FilletSeq already extracted)")
            return
    lines = src.splitlines(keepends=True)
    items = parse_items(src)
    if not items:
        raise SystemExit(f"no items in {src_path}")
    stems, buckets = bucket_items(items, job["cuts"])
    park = set(job.get("park") or [])
    imported = []
    for stem in stems:
        nlines = sum(e - s for s, _, e in buckets[stem])
        if nlines == 0:
            print(f"  {stem:14s}  empty, skip")
            continue
        print(f"  {stem:14s}  items={len(buckets[stem]):2d}  lines={nlines:5d}")
        body = "".join("".join(lines[s:e]) for s, _, e in buckets[stem])
        path = job["out_dir"] / f"Library.{stem}.ailang"
        note = "  PARKED, not imported" if stem in park else ""
        banner = (
            f"// {job['banner']} part {stem}{note}\n"
            f"// API stays {job['api']}  (facade: {job['caller']})\n\n"
        )
        write_part(path, banner, job["part_imports"], body)
        if stem not in park:
            imported.append(stem)
    # First imported stem is the original filename; extra stems go on the facade.
    extras = [s for s in imported if s != Path(src_path).stem.replace("Library.", "")]
    # Library.Fillet.ailang stem is Fillet; Path.stem is "Library.Fillet" on some
    # systems? Path("Library.Fillet.ailang").stem == "Library.Fillet". Use cuts[0].
    first = job["cuts"][0][1]
    extras = [s for s in imported if s != first]
    if extras and job.get("parent_facade"):
        insert_after(
            job["parent_facade"],
            job["facade_after"],
            [f"LibraryImport.{job['import_prefix']}.{s}" for s in extras],
        )


def run_extract(job: dict) -> None:
    src_path: Path = job["src"]
    backup(src_path, job["backup"])
    src = src_path.read_text()
    if all(p.exists() and p.stat().st_size > 0 for p in job["extract_paths"].values()):
        if "LibraryImport.Cad.CAD_SketchCstr" in src:
            print("  skip (already extracted)")
            return
    lines = src.splitlines(keepends=True)
    items = parse_items(src)
    stems, buckets = bucket_items(items, job["cuts"])
    keep = job["keep"]
    # preamble: everything before first Function/FixedPool
    first_i = items[0][0]
    preamble = "".join(lines[:first_i])
    keep_body = "".join("".join(lines[s:e]) for s, _, e in buckets[keep])
    # Pools live in this file. Import extracted parts AFTER the pools so
    # CAD_Sketch_State exists when Cstr/Geom are inlined.
    extra = ""
    for imp in job.get("add_imports") or []:
        if imp not in preamble and imp not in keep_body:
            extra += imp + "\n"
    if extra:
        extra = "\n" + extra
    src_path.write_text(preamble + keep_body.rstrip() + extra + "\n")
    print(f"    kept {src_path.relative_to(ROOT)}  {sum(1 for _ in src_path.open())} loc")

    for stem, path in job["extract_paths"].items():
        nlines = sum(e - s for s, _, e in buckets[stem])
        print(f"  {stem:14s}  items={len(buckets[stem]):2d}  lines={nlines:5d}")
        body = "".join("".join(lines[s:e]) for s, _, e in buckets[stem])
        banner = (
            f"// {job['banner']} part {stem}\n"
            f"// API stays {job['api']}  (loaded via {job['caller']})\n\n"
        )
        write_part(path, banner, job["part_imports"], body)


def run_job(key: str) -> None:
    job = JOBS[key]
    print(f"== {key} ==")
    mode = job.get("mode", "facade")
    if mode == "facade":
        run_facade(job)
    elif mode == "siblings":
        run_siblings(job)
    elif mode == "extract":
        run_extract(job)
    else:
        raise SystemExit(f"unknown mode {mode}")


def patch_topo_banner() -> None:
    path = ROOT / "Librarys/Cad/Library.CAD_Topo.ailang"
    text = path.read_text()
    old = """//   Topo.MakeCyl      cylinder / lathe
//   Topo.MakePlate    plate hole shells / sphere
//   Topo.MakeBoxFeat  box pocket / side hole
//   Topo.MakeBoxFeat2 box notch / boss
//   Topo.Query        FaceGet* / pick / bounds
//   Topo.Xform        RebuildKind0Planes / Map / Translate
//   Topo.Fillet       plane-plane edge fillet
//   Topo.Digon        digon solve
//   Topo.Digon2       digon build / FilletPlaneEdges
"""
    new = """//   Topo.MakeCyl      cylinder / top-bottom fillet
//   Topo.MakeLathe    closed lathe / revolution / prism cyl
//   Topo.MakePlate    plate hole shells / sphere
//   Topo.MakeBoxFeat  box pocket / side hole
//   Topo.MakeBoxFeat2 box notch / boss
//   Topo.Query        FaceGet* / pick / bounds
//   Topo.QueryWalk    edge sig / coedge surgery
//   Topo.Xform        RebuildKind0Planes / Map / Translate
//   Topo.Fillet       plane-plane edge fillet
//   Topo.FilletVertex rolling-ball vertex sphere
//   Topo.Digon        digon solve
//   Topo.Digon2       digon build / Digon cap fillet
//   Topo.FilletSeq    sequential + FilletPlaneEdges dispatch
"""
    if old in text:
        path.write_text(text.replace(old, new))
        print("patched CAD_Topo banner")


def main() -> None:
    args = sys.argv[1:] or DEFAULT_JOBS
    for a in args:
        if a not in JOBS:
            raise SystemExit(f"unknown job {a}; want {sorted(JOBS)}")
        run_job(a)
    if any(a in {"fillet", "filletseq", "query", "makecyl"} for a in args):
        patch_topo_banner()


if __name__ == "__main__":
    main()
