#!/usr/bin/env python3
"""
pack_widget_vif.py — Pack SVG/TVG icons into a named-entry VIF icon pack.

Usage:
    python3 tools/pack_widget_vif.py <tvg_dir> <output.vif> [--map name_map.json]

If --map is provided, filenames are mapped to standard names via the JSON file.
Otherwise, the filename (minus extension) becomes the standard name.

VIF Icon Pack Format:
    [4 bytes]  magic: "VIF\x02" (version 2 = icon pack)
    [4 bytes]  entry_count
    [4 bytes]  manifest_len (JSON string length including null)
    [manifest_len bytes]  JSON manifest: {"name": entry_index, ...}
    For each entry:
        [4 bytes]  tvg_len
        [4 bytes]  design_w (from TVG header)
        [4 bytes]  design_h (from TVG header)
        [tvg_len bytes]  raw TVG data

The manifest maps standard icon names to 0-based entry indices.
Runtime does: parse JSON → lookup name → get index → offset into TVG data.

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import os
import sys
import json
import struct
import glob


def read_tvg_dimensions(tvg_data):
    """Extract width and height from TVG header."""
    if len(tvg_data) < 4:
        return 15, 15  # default for icon sets
    # TinyVG v1 header: magic(2), scale_and_color(1), coord_range(derived)
    # Width and height follow based on coord_range
    # For simplicity with icon packs, we'll read from the header
    # but fall back to 15x15 (standard icon size) if parsing fails
    try:
        # TinyVG v1 layout:
        #   Byte 0-1: magic 0x72 0x56
        #   Byte 2:   version (1)
        #   Byte 3:   flags: scale(4) | color_enc(2) | coord_range(2)
        #   Then: width, height (size depends on coord_range)
        #   Then: color_count (varuint)
        if tvg_data[0] != 0x72 or tvg_data[1] != 0x56:
            return 15, 15
        flags = tvg_data[3]
        coord_range = (flags >> 6) & 0x03
        pos = 4
        # Read width and height based on coord_range
        if coord_range == 0:  # i16
            w = struct.unpack_from('<h', tvg_data, pos)[0]
            h = struct.unpack_from('<h', tvg_data, pos + 2)[0]
        elif coord_range == 1:  # i32
            w = struct.unpack_from('<i', tvg_data, pos)[0]
            h = struct.unpack_from('<i', tvg_data, pos + 4)[0]
        else:
            w = 15
            h = 15
        return abs(w), abs(h)
    except (IndexError, struct.error):
        return 15, 15


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <tvg_dir> <output.vif> [--map name_map.json]")
        sys.exit(1)

    tvg_dir = sys.argv[1]
    output_path = sys.argv[2]
    name_map = {}

    # Optional name map
    if '--map' in sys.argv:
        map_idx = sys.argv.index('--map')
        if map_idx + 1 < len(sys.argv):
            with open(sys.argv[map_idx + 1], 'r') as f:
                name_map = json.load(f)

    # Collect TVG files
    tvg_files = sorted(glob.glob(os.path.join(tvg_dir, '*.tvg')))
    if not tvg_files:
        print(f"No .tvg files found in {tvg_dir}")
        sys.exit(1)

    # Build entries and manifest
    entries = []  # (standard_name, tvg_data, width, height)
    manifest = {}

    for tvg_path in tvg_files:
        filename = os.path.basename(tvg_path)
        stem = os.path.splitext(filename)[0]

        # Map filename to standard name
        if filename in name_map:
            std_name = name_map[filename]
        elif stem in name_map:
            std_name = name_map[stem]
        else:
            # Default: use filename stem, lowercase, hyphens preserved
            std_name = stem.lower()

        # Skip duplicates (first wins)
        if std_name in manifest:
            print(f"  SKIP {filename} → {std_name} (duplicate)")
            continue

        with open(tvg_path, 'rb') as f:
            tvg_data = f.read()

        w, h = read_tvg_dimensions(tvg_data)
        idx = len(entries)
        entries.append((std_name, tvg_data, w, h))
        manifest[std_name] = idx
        print(f"  [{idx:3d}] {filename} → {std_name} ({w}x{h}, {len(tvg_data)} bytes)")

    # Serialize manifest to JSON
    manifest_json = json.dumps(manifest, separators=(',', ':'))
    manifest_bytes = manifest_json.encode('utf-8') + b'\x00'

    # Write VIF
    with open(output_path, 'wb') as f:
        # Header
        f.write(b'VIF\x02')                          # magic + version 2
        f.write(struct.pack('<I', len(entries)))       # entry count
        f.write(struct.pack('<I', len(manifest_bytes)))# manifest length

        # Manifest
        f.write(manifest_bytes)

        # Entries
        for std_name, tvg_data, w, h in entries:
            f.write(struct.pack('<I', len(tvg_data)))  # tvg_len
            f.write(struct.pack('<I', w))              # design_w
            f.write(struct.pack('<I', h))              # design_h
            f.write(tvg_data)                          # raw TVG

    total_size = os.path.getsize(output_path)
    print(f"\nPacked {len(entries)} icons into {output_path} ({total_size:,} bytes)")
    print(f"Manifest: {len(manifest_json)} bytes JSON")


if __name__ == '__main__':
    main()