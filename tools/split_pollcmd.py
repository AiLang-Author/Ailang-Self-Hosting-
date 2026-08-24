#!/usr/bin/env python3
"""Split CA_PollCmd into per-letter helpers + Branch dispatch.

Preserves original IfCondition order inside each letter. PollCmd becomes
read/log/click then Branch c0 { Case N: ReturnValue(CA_IpcX()) }.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "CAD/App/Ipc.ailang"
BACKUP = ROOT / "CAD/App/Ipc.ailang.pre_poll"
OUT = ROOT / "CAD/App"

IMPORTS = """LibraryImport.Arena
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
LibraryImport.Cad.CAD_UI
LibraryImport.Display.Render.Framebuffer
LibraryImport.StringUtils
"""

# 1-based inclusive line ranges from Ipc.ailang (current PollCmd body).
# Order inside a letter = original "must beat" order.
LETTERS = {
    "O": [(351, 377), (1569, 1600)],
    "Z": [(378, 392)],
    "P": [(394, 413), (848, 1029), (1627, 1635)],
    "H": [(415, 430), (1793, 1900)],
    "Q": [(437, 440)],
    "M": [(442, 492)],
    "T": [(494, 762)],
    "F": [(764, 847), (1437, 1468), (1495, 1507)],
    "S": [
        (1030, 1131),
        (1636, 1653),
        (1679, 1702),
        (1741, 1772),
        (1901, 1919),
    ],
    "C": [
        (1134, 1243),
        (1385, 1394),
        (1469, 1494),
        (1609, 1626),
    ],
    "N": [(1244, 1328)],
    "R": [(1330, 1371)],
    "U": [(1373, 1384)],
    "Y": [(1396, 1434)],
    "I": [(1508, 1520), (1528, 1568)],
    "J": [(1521, 1527)],
    "G": [(1654, 1678), (1703, 1723)],
    "K": [(1601, 1608)],
    "L": [(1724, 1733)],
    "W": [(1734, 1740)],
    "V": [(1773, 1792)],
    "B": [(1920, 1927)],
    "D": [(1928, 1962)],
}

# Group helpers into files (keep each < ~1000).
FILES = {
    "IpcNav": ["O", "Z", "H", "W", "V", "Q", "M"],
    "IpcP": ["P"],
    "IpcT": ["T"],
    "IpcS": ["S"],
    "IpcC": ["C"],
    "IpcF": ["F"],
    "IpcMisc": ["N", "R", "U", "Y", "I", "J", "G", "K", "L", "B", "D"],
}

# ASCII first-byte → helper. Only letters that appear as cmd prefixes.
BRANCH = [
    (98, "B"),
    (99, "C"),
    (100, "D"),
    (102, "F"),
    (103, "G"),
    (104, "H"),
    (105, "I"),
    (106, "J"),
    (107, "K"),
    (108, "L"),
    (109, "M"),
    (110, "N"),
    (111, "O"),
    (112, "P"),
    (113, "Q"),
    (114, "R"),
    (115, "S"),
    (116, "T"),
    (117, "U"),
    (118, "V"),
    (119, "W"),
    (121, "Y"),
    (122, "Z"),
]


def slice_lines(lines: list[str], start: int, end: int) -> str:
    chunk = lines[start - 1 : end]
    # PollCmd body is indented 8 spaces; helper body uses 8 as well.
    return "".join(chunk)


def wrap_helper(letter: str, body: str) -> str:
    return (
        f"// CA_PollCmd first-byte '{letter.lower()}' ({ord(letter.lower())}).\n"
        f"// Return 0 = not handled (fall through unused); else PollCmd result.\n"
        f"Function.CA_Ipc{letter} {{\n"
        f"    Output: Integer\n"
        f"    Body: {{\n"
        f"        buf = CadAppIpc.cmd\n"
        f"        IfCondition EqualTo(buf, 0) ThenBlock: {{ ReturnValue(0) }}\n"
        f"        c0 = GetByte(buf, 0)\n"
        f"{body}"
        f"        ReturnValue(0)\n"
        f"    }}\n"
        f"}}\n\n"
    )


def main() -> None:
    text = SRC.read_text()
    if not BACKUP.exists():
        BACKUP.write_text(text)
        print(f"backup {BACKUP}")
    lines = text.splitlines(keepends=True)

    # Keep parse + BuildSchema from original; drop PollCmd body.
    # Find function bounds.
    poll_i = None
    schema_i = None
    for i, line in enumerate(lines):
        if line.startswith("Function.CA_PollCmd"):
            poll_i = i
        if line.startswith("Function.CA_BuildSchema"):
            schema_i = i
    if poll_i is None or schema_i is None:
        raise SystemExit("cannot find CA_PollCmd / CA_BuildSchema")

    head = "".join(lines[:poll_i])  # parse helpers
    tail = "".join(lines[schema_i:])  # BuildSchema

    for fname, letters in FILES.items():
        parts = []
        nlines = 0
        for L in letters:
            body = ""
            for a, b in LETTERS[L]:
                body += slice_lines(lines, a, b)
                if not body.endswith("\n"):
                    body += "\n"
            parts.append(wrap_helper(L, body))
            nlines += body.count("\n")
        banner = (
            f"// CAD/App/{fname} — CA_PollCmd helpers (Branch first-byte).\n"
            f"// API: Function.CA_Ipc*  loaded via Import.CAD.App.Ipc\n\n"
        )
        path = OUT / f"{fname}.ailang"
        path.write_text(banner + IMPORTS + "\n" + "".join(parts))
        loc = sum(1 for _ in path.open())
        print(f"  {fname:12s}  {loc:4d} loc  letters={''.join(letters)}")

    cases = []
    for code, L in BRANCH:
        cases.append(
            f"            Case {code}: {{ ReturnValue(CA_Ipc{L}()) }}"
        )
    case_block = "\n".join(cases)

    poll = f"""Function.CA_PollCmd {{
    Output: Integer
    Body: {{
        fd = SystemCall(2, "/tmp/cad_app/cmd.txt", 0, 0)
        IfCondition LessThan(fd, 0) ThenBlock: {{ ReturnValue(0) }}
        IfCondition EqualTo(CadAppIpc.cmd, 0) ThenBlock: {{ CadAppIpc.cmd = Allocate(80) }}
        buf = CadAppIpc.cmd
        IfCondition EqualTo(buf, 0) ThenBlock: {{
            SystemCall(3, fd, 0, 0)
            ReturnValue(0)
        }}
        n = SystemCall(0, fd, buf, 79)
        SystemCall(3, fd, 0, 0)
        fd2 = SystemCall(2, "/tmp/cad_app/cmd.txt", 577, 420)
        IfCondition GreaterEqual(fd2, 0) ThenBlock: {{ SystemCall(3, fd2, 0, 0) }}
        IfCondition LessThan(n, 1) ThenBlock: {{
            ReturnValue(0)
        }}
        SetByte(buf, n, 0)
        c00 = GetByte(buf, 0)
        skip_log = 0
        IfCondition EqualTo(c00, 111) ThenBlock: {{ skip_log = 1 }}
        IfCondition EqualTo(c00, 104) ThenBlock: {{ skip_log = 1 }}
        IfCondition EqualTo(skip_log, 0) ThenBlock: {{
            CA_Log("cad_app: ipc ", 13)
            nn = n
            IfCondition GreaterThan(nn, 48) ThenBlock: {{ nn = 48 }}
            CA_Log(buf, nn)
            IfCondition NotEqual(GetByte(buf, Subtract(n, 1)), 10) ThenBlock: {{
                CA_Log("\\n", 1)
            }}
        }}
        // click before Branch — "click" is c… and would collide with cstr/clear.
        IfCondition EqualTo(CA_ParseClick(buf), 1) ThenBlock: {{
            ReturnValue(2)
        }}
        c0 = GetByte(buf, 0)
        Branch c0 {{
{case_block}
            Default: {{ ReturnValue(0) }}
        }}
        ReturnValue(0)
    }}
}}

"""

    facade_imports = "".join(
        f"Import.CAD.App.{name}\n" for name in FILES
    )
    # Head already has LibraryImports. Append helper imports before PollCmd.
    # Strip trailing extra newlines from head, add facade imports.
    head = head.rstrip() + "\n\n" + facade_imports + "\n"
    SRC.write_text(head + poll + tail)
    loc = sum(1 for _ in SRC.open())
    print(f"  Ipc.ailang     {loc:4d} loc  (parse + Branch + schema)")


if __name__ == "__main__":
    main()
