#!/usr/bin/env python3
"""Static inventory of Linux syscall numbers HalCode can reach.

Scans HalCode-Haiku sources and every AILANG library they import.
A numeric SystemCall(N, ...) is recorded directly. An identifier is
resolved through FixedPool Initialize values and plain assignments
in the same tree. This is the list the mov-immediate scan missed.
"""
import os
import re

HAL = "/home/bob/HalCode-Haiku"
LIB = "/home/bob/Ailang-Self-Hosting-/Librarys"

HANDLED = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 21, 22,
    24, 32, 33, 35, 39, 60, 61, 62, 72, 74, 77, 78, 79, 80, 82, 83, 84,
    87, 89, 91, 109, 186, 201, 217, 228, 231, 257, 262, 293, 318,
}
# Fall through to HaikuLx.ENOSYS in HaikuSys_Call. Kept on purpose:
# fork/exec/clone/prctl are phase 2 (load_image), sockets and epoll are
# not the port IPC path, futex and signalfd stay unavailable.
ENOSYS = {
    16, 41, 42, 43, 49, 50, 51, 54, 56, 57, 59, 157,
    202, 232, 233, 288, 289, 291,
}

CALL_RE = re.compile(r"SystemCall\s*\(\s*([^,\n\)]+)")
POOL_RE = re.compile(
    r'"([A-Za-z0-9_]+)"\s*:\s*Initialize\s*=\s*(-?\d+)'
)
ASSIGN_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?\d+)\b"
)
IMPORT_RE = re.compile(r"LibraryImport\.([A-Za-z0-9_.]+)")


def ailang_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "objects")]
        for name in filenames:
            if name.endswith(".ailang"):
                out.append(os.path.join(dirpath, name))
    return out


def resolve_import(spec):
    parts = spec.split(".")
    # LibraryImport.Compiler.Compile.CCompileMain -> Library.CCompileMain.ailang
    # LibraryImport.Haiku.HaikuRT -> Library.HaikuRT.ailang under Haiku/
    candidates = []
    leaf = "Library." + parts[-1] + ".ailang"
    candidates.append(os.path.join(LIB, *parts[:-1], leaf))
    candidates.append(os.path.join(LIB, leaf))
    if len(parts) >= 2:
        candidates.append(os.path.join(LIB, parts[0], leaf))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def main():
    files = ailang_files(HAL)
    seen = set(files)
    # Follow imports, a few rounds, so tool libraries pull in Socket/HTTP.
    for _ in range(6):
        added = []
        for path in list(seen):
            try:
                text = open(path, errors="replace").read()
            except OSError:
                continue
            for spec in IMPORT_RE.findall(text):
                hit = resolve_import(spec)
                if hit and hit not in seen:
                    added.append(hit)
        if not added:
            break
        for path in added:
            seen.add(path)

    consts = {}
    calls = []  # (number or None, raw, file, line)
    for path in sorted(seen):
        try:
            lines = open(path, errors="replace").read().splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for name, value in POOL_RE.findall(line):
                consts[name] = int(value)
            for name, value in ASSIGN_RE.findall(line):
                consts.setdefault(name, int(value))
            for raw in CALL_RE.findall(line):
                raw = raw.strip()
                num = None
                if re.fullmatch(r"-?\d+", raw):
                    num = int(raw)
                else:
                    leaf = raw.split(".")[-1]
                    if leaf in consts and re.fullmatch(r"-?\d+", str(consts[leaf])):
                        num = consts[leaf]
                calls.append((num, raw, path, i))

    by_num = {}
    unresolved = []
    for num, raw, path, line in calls:
        if num is None:
            unresolved.append((raw, path, line))
        else:
            by_num.setdefault(num, []).append((raw, path, line))

    print(f"files {len(seen)}")
    print(f"calls {len(calls)}")
    print("--- numbers ---")
    for num in sorted(by_num):
        sites = by_num[num]
        kind = "handled" if num in HANDLED else ("enosys" if num in ENOSYS else "GAP")
        sample = sites[0]
        rel = sample[1].replace(HAL + "/", "HalCode/").replace(LIB + "/", "Librarys/")
        print(f"{num:4d}  {kind:8s}  x{len(sites):3d}  {sample[0]}  {rel}:{sample[2]}")
    print("--- unresolved ---")
    shown = 0
    for raw, path, line in unresolved:
        rel = path.replace(HAL + "/", "HalCode/").replace(LIB + "/", "Librarys/")
        print(f"  {raw}  {rel}:{line}")
        shown += 1
        if shown > 80:
            print(f"  ... {len(unresolved) - shown} more")
            break
    gaps = [n for n in by_num if n not in HANDLED and n not in ENOSYS]
    print("--- gaps ---")
    print(" ".join(str(n) for n in sorted(gaps)) or "(none)")


if __name__ == "__main__":
    main()
