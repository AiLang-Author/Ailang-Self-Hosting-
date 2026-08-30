#!/usr/bin/env python3
"""Resolve shared libraries for a foreign ELF and copy them next to it.

Used when wrapping Chrome / VS Code / Xvfb for AOS. We do not run ldd on
the guest (BusyBox has none). We parse DT_NEEDED with readelf.

Policy:
  - Do not copy glibc (libc, ld-linux, libpthread, libm, libdl, librt).
    The guest already has a libc; mixing host libc is how resize2fs died.
  - DO copy libsystemd.so / libselinux.so if NEEDED. That is a .so, not a
    daemon. The wrap still does not start systemd.
  - DT_NEEDED cannot see dlopen() plugins (libsoftokn3.so). Pass --extra
    or --also-dir for those, plus matching .chk files.

Examples:
  tools/bundle_foreign.py --elf /usr/bin/Xvfb --dest overlay/usr/lib
  tools/bundle_foreign.py --elf /opt/google/chrome/chrome \\
      --also-dir /opt/google/chrome --extra libsoftokn3.so --extra '*.chk'
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKIP_SONAME = re.compile(
    r"^(ld-linux.*|libc\.so\.|libm\.so\.|libpthread\.so\.|libdl\.so\.|"
    r"librt\.so\.|libresolv\.so\.|libnss_files\.so\.|libnss_dns\.so\.|"
    r"linux-vdso\.so)"
)

NEEDED_RE = re.compile(r"Shared library: \[(.+)\]")
RPATH_RE = re.compile(r"(?:Library rpath|Library runpath): \[(.+)\]")


def readelf_dynamic(elf: Path) -> tuple[list[str], list[str]]:
    try:
        out = subprocess.check_output(
            ["readelf", "-d", str(elf)], stderr=subprocess.DEVNULL, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise SystemExit(f"readelf failed on {elf}: {e}") from e
    needed = NEEDED_RE.findall(out)
    rpath = []
    for m in RPATH_RE.findall(out):
        rpath.extend(m.split(":"))
    return needed, rpath


def interp_origin(elf: Path) -> Path:
    return elf.resolve().parent


def search_so(soname: str, search: list[Path]) -> Path | None:
    for d in search:
        cand = d / soname
        if cand.is_file() or cand.is_symlink():
            return cand.resolve()
        # libfoo.so.1 -> libfoo.so.1.0.2 sitting beside it
        if d.is_dir():
            for p in d.glob(soname + "*"):
                if p.is_file():
                    return p.resolve()
    return None


def copy_lib(src: Path, dest_dir: Path, dry: bool) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    real = src.resolve()
    dest_real = dest_dir / real.name
    if not dry:
        if not dest_real.exists() or dest_real.stat().st_size != real.stat().st_size:
            shutil.copy2(real, dest_real)
        soname = src.name
        dest_link = dest_dir / soname
        if soname != real.name and not dest_link.exists():
            dest_link.symlink_to(real.name)
        # also link the soname if src was the real file named libfoo.so.1.2
    return dest_real


def walk(root_elf: Path, from_dirs: list[Path], extras: list[str], also_dirs: list[Path],
         dest: Path, dry: bool) -> dict[str, Path | None]:
    queue: list[Path] = [root_elf.resolve()]
    seen: set[Path] = set()
    resolved: dict[str, Path | None] = {}

    while queue:
        elf = queue.pop()
        if elf in seen:
            continue
        seen.add(elf)
        needed, rpath = readelf_dynamic(elf)
        origin = interp_origin(elf)
        search = []
        for rp in rpath:
            search.append(Path(rp.replace("$ORIGIN", str(origin))))
        search.append(origin)
        search.extend(from_dirs)
        for soname in needed:
            if SKIP_SONAME.match(soname):
                resolved[soname] = None  # guest libc
                continue
            if soname in resolved:
                continue
            found = search_so(soname, search)
            resolved[soname] = found
            if found is None:
                continue
            copy_lib(found, dest, dry)
            queue.append(found)

    # plugins next to the binary (NSS etc.)
    for d in also_dirs:
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if p.suffix in {".so", ".chk"} or ".so." in p.name:
                if SKIP_SONAME.match(p.name):
                    continue
                copy_lib(p, dest, dry)
                if p.suffix == ".so" or ".so." in p.name:
                    queue.append(p.resolve())

    for pat in extras:
        hits = []
        for d in also_dirs + from_dirs + [root_elf.parent]:
            hits.extend(d.glob(pat))
        for p in hits:
            if p.is_file():
                copy_lib(p, dest, dry)
                resolved[p.name] = p.resolve()

    return resolved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--elf", required=True, type=Path, help="root ELF (chrome, Xvfb, code)")
    ap.add_argument("--dest", required=True, type=Path, help="directory to copy .so into")
    ap.add_argument("--from", dest="from_dirs", action="append", default=[],
                    help="search dir (repeat). Default: host multiarch + /lib + /usr/lib")
    ap.add_argument("--also-dir", action="append", default=[], type=Path,
                    help="copy extra .so/.chk sitting in this dir (Chrome NSS)")
    ap.add_argument("--extra", action="append", default=[],
                    help="glob for dlopen plugins (libsoftokn3.so, *.chk)")
    ap.add_argument("--env-out", type=Path, help="write LD_LIBRARY_PATH=... here")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    elf = args.elf
    if not elf.is_file():
        print(f"not an ELF file: {elf}", file=sys.stderr)
        return 2

    from_dirs = [Path(p) for p in args.from_dirs] or [
        Path("/usr/lib/x86_64-linux-gnu"),
        Path("/lib/x86_64-linux-gnu"),
        Path("/usr/lib"),
        Path("/lib"),
    ]

    resolved = walk(elf, from_dirs, args.extra, args.also_dir, args.dest, args.dry_run)
    missing = [k for k, v in resolved.items() if v is None and not SKIP_SONAME.match(k)]
    skipped = [k for k, v in resolved.items() if v is None and SKIP_SONAME.match(k)]
    copied = {k: v for k, v in resolved.items() if v is not None}

    print(f"elf        {elf}")
    print(f"dest       {args.dest}")
    print(f"copied     {len(copied)}")
    print(f"guest libc {len(skipped)} (not copied)")
    if missing:
        print("MISSING:")
        for m in sorted(missing):
            print(f"  {m}")
    for name, path in sorted(copied.items()):
        print(f"  {name} <- {path}")

    if args.env_out and not args.dry_run:
        args.env_out.parent.mkdir(parents=True, exist_ok=True)
        lp = f"LD_LIBRARY_PATH={args.dest}:/usr/lib:/usr/lib/x86_64-linux-gnu"
        args.env_out.write_text(lp + "\n")
        print(f"wrote {args.env_out}: {lp}")

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
