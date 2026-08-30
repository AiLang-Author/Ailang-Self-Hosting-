#!/usr/bin/env python3
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

"""Convert CAD IPC frame.raw + meta.bin to PNG.

Usage:
  ./CAD/scripts/frame_to_png.py [state_dir] [out.png]
  state_dir default: /tmp/cad_app
  out.png  default: <state_dir>/viewport.png
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path


def png_chunk(ctype: bytes, data: bytes) -> bytes:
    c = ctype + data
    return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)


def main() -> int:
    state = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/cad_app")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else state / "viewport.png")
    meta = state / "meta.bin"
    frame = state / "frame.raw"
    if not meta.is_file() or not frame.is_file():
        print(f"missing {meta} or {frame}", file=sys.stderr)
        return 1
    hdr = meta.read_bytes()
    if len(hdr) < 12:
        print("meta.bin too short", file=sys.stderr)
        return 1
    w, h, pitch = struct.unpack_from("<iii", hdr, 0)
    if w < 16 or h < 16 or pitch < w * 4:
        print(f"bad meta {w}x{h} pitch={pitch}", file=sys.stderr)
        return 1
    raw = frame.read_bytes()
    need = pitch * h
    if len(raw) < need:
        print(f"frame.raw short: {len(raw)} < {need}", file=sys.stderr)
        return 1

    rows = []
    for y in range(h):
        row = bytearray([0])  # filter None
        off = y * pitch
        for x in range(w):
            p = off + x * 4
            b, g, r = raw[p], raw[p + 1], raw[p + 2]
            row.extend([r, g, b, 255])
        rows.append(bytes(row))
    idat = zlib.compress(b"".join(rows), 6)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(png_chunk(b"IHDR", ihdr))
        f.write(png_chunk(b"IDAT", idat))
        f.write(png_chunk(b"IEND", b""))
    print(f"{out}  ({w}x{h})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
