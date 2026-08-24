#!/usr/bin/env python3
"""
pack_font_vif.py — Pack TVG glyphs + metrics into a VIF font file.

Usage:
    python3 pack_font_vif.py fonts/noto-sans/ NotoSans.vif

Reads:
    fonts/noto-sans/font_meta.json
    fonts/noto-sans/metrics.json
    fonts/noto-sans/kerning.json
    fonts/noto-sans/tvg/*.tvg

Produces:
    NotoSans.vif — binary font file for AILang VIF loader

VIF Font File Format:
    [4 bytes] magic: "VIF0"
    [4 bytes] version: 1
    [4 bytes] entry_count
    [4 bytes] kern_count
    [4 bytes] em_size
    [4 bytes] ascent
    [4 bytes] descent
    [4 bytes] line_gap
    [64 bytes] font_name (null-padded)
    --- per entry (glyph) ---
    [4 bytes] codepoint
    [4 bytes] advance
    [4 bytes] bearing_x
    [4 bytes] bearing_y
    [4 bytes] tvg_length
    [N bytes] tvg_data
    --- per kerning pair ---
    [4 bytes] left_codepoint
    [4 bytes] right_codepoint
    [4 bytes] adjust_x

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import sys
import os
import json
import struct


def pack_font(input_dir, output_path):
    """Pack exported font data into a VIF file."""

    # Load metadata
    meta_path = os.path.join(input_dir, "font_meta.json")
    metrics_path = os.path.join(input_dir, "metrics.json")
    kern_path = os.path.join(input_dir, "kerning.json")
    tvg_dir = os.path.join(input_dir, "tvg")

    with open(meta_path) as f:
        meta = json.load(f)
    with open(metrics_path) as f:
        metrics = json.load(f)
    with open(kern_path) as f:
        kern_pairs = json.load(f)
    kern_pairs = [k for k in kern_pairs if int(k.get("adjust_x", 0)) != 0]

    print(f"[pack] Font: {meta['name']}")
    print(f"[pack] Glyphs in metrics: {len(metrics)}")
    print(f"[pack] Kerning pairs: {len(kern_pairs)}")

    # Match metrics to TVG files
    entries = []
    for m in metrics:
        cp = m["codepoint"]
        name = m["name"]
        fname = m["file"].replace(".svg", ".tvg")
        tvg_path = os.path.join(tvg_dir, fname)

        tvg_data = b""
        if os.path.exists(tvg_path):
            tvg_data = open(tvg_path, "rb").read()

        # Empty glyphs (space) have no TVG. Pack them anyway so the
        # loader can use their advance instead of a half-em fallback.
        entries.append({
            "codepoint": cp,
            "advance": int(m["advance"]),
            "bearing_x": int(m.get("bearing_x", 0)),
            "bearing_y": int(m.get("bearing_y", 0)),
            "tvg_data": tvg_data,
        })

    print(f"[pack] Glyphs with TVG data: {len(entries)}")

    # Sort by codepoint for binary search later
    entries.sort(key=lambda e: e["codepoint"])

    # Build output
    out = bytearray()

    # Header
    out += b"VIF0"                                          # magic
    out += struct.pack("<I", 1)                             # version
    out += struct.pack("<I", len(entries))                  # entry_count
    out += struct.pack("<I", len(kern_pairs))               # kern_count
    out += struct.pack("<I", meta.get("em", 1024))          # em_size
    out += struct.pack("<I", meta.get("ascent", 800))       # ascent
    out += struct.pack("<i", meta.get("descent", -200))     # descent (signed)
    out += struct.pack("<I", meta.get("os2_typo_linegap", 0))  # line_gap

    # Font name (64 bytes, null-padded)
    name_bytes = meta.get("name", "Unknown").encode("utf-8")[:63]
    out += name_bytes + b"\x00" * (64 - len(name_bytes))

    # Glyph entries
    for e in entries:
        tvg = e["tvg_data"]
        out += struct.pack("<I", e["codepoint"])
        out += struct.pack("<I", e["advance"])
        out += struct.pack("<i", e["bearing_x"])
        out += struct.pack("<i", e["bearing_y"])
        out += struct.pack("<I", len(tvg))
        out += tvg

    # Kerning pairs
    for k in kern_pairs:
        out += struct.pack("<I", k["left"])
        out += struct.pack("<I", k["right"])
        out += struct.pack("<i", k["adjust_x"])

    # Write
    with open(output_path, "wb") as f:
        f.write(out)

    size_kb = len(out) / 1024
    print(f"[pack] Wrote {output_path} ({size_kb:.1f} KB)")
    print(f"[pack] {len(entries)} glyphs, {len(kern_pairs)} kern pairs")


def main():
    if len(sys.argv) < 3:
        print("Usage: pack_font_vif.py <input_dir> <output.vif>")
        print("  input_dir should contain font_meta.json, metrics.json, kerning.json, tvg/")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.isdir(input_dir):
        print(f"ERROR: Not a directory: {input_dir}")
        sys.exit(1)

    pack_font(input_dir, output_path)


if __name__ == "__main__":
    main()