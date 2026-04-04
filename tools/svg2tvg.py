#!/usr/bin/env python3
"""
svg2tvg.py — Convert simple SVG path glyphs to TinyVG binary format.
Handles the subset of SVG that FontForge exports (path-only, no transforms).

Usage:
    python3 svg2tvg.py input.svg output.tvg
    python3 svg2tvg.py fonts/dejavu-sans/glyphs/ fonts/dejavu-sans/tvg/

Supports SVG path commands: M m L l H h V v C c S s Q q T t Z z A a

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import sys
import os
import re
import struct
import math
import xml.etree.ElementTree as ET


# ============================================================================
# SVG PATH PARSER
# ============================================================================

def tokenize_path(d):
    """Split SVG path d attribute into tokens."""
    # Split on command letters and numbers
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', d)
    return tokens


def parse_path(d):
    """Parse SVG path string into list of (command, points) tuples."""
    tokens = tokenize_path(d)
    commands = []
    i = 0
    current_cmd = None

    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            current_cmd = t
            i += 1
        elif current_cmd is None:
            i += 1
            continue

        cmd = current_cmd

        if cmd in ('Z', 'z'):
            commands.append((cmd, []))
            current_cmd = None  # Z doesn't repeat
            continue

        # Number of coordinate pairs per command
        param_counts = {
            'M': 2, 'm': 2, 'L': 2, 'l': 2,
            'H': 1, 'h': 1, 'V': 1, 'v': 1,
            'C': 6, 'c': 6, 'S': 4, 's': 4,
            'Q': 4, 'q': 4, 'T': 2, 't': 2,
            'A': 7, 'a': 7,
        }

        n = param_counts.get(cmd, 0)
        if n == 0:
            i += 1
            continue

        params = []
        for j in range(n):
            if i < len(tokens) and not tokens[i].isalpha():
                params.append(float(tokens[i]))
                i += 1
            else:
                break

        if len(params) == n:
            commands.append((cmd, params))

            # Implicit repeat: M becomes L, m becomes l
            if cmd == 'M':
                current_cmd = 'L'
            elif cmd == 'm':
                current_cmd = 'l'
        else:
            break

    return commands


def to_absolute(commands):
    """Convert all relative commands to absolute."""
    result = []
    cx, cy = 0, 0
    sx, sy = 0, 0  # subpath start
    last_cp = None  # last control point for S/T

    for cmd, params in commands:
        if cmd == 'M':
            cx, cy = params[0], params[1]
            sx, sy = cx, cy
            result.append(('M', [cx, cy]))
        elif cmd == 'm':
            cx += params[0]
            cy += params[1]
            sx, sy = cx, cy
            result.append(('M', [cx, cy]))
        elif cmd == 'L':
            cx, cy = params[0], params[1]
            result.append(('L', [cx, cy]))
        elif cmd == 'l':
            cx += params[0]
            cy += params[1]
            result.append(('L', [cx, cy]))
        elif cmd == 'H':
            cx = params[0]
            result.append(('L', [cx, cy]))
        elif cmd == 'h':
            cx += params[0]
            result.append(('L', [cx, cy]))
        elif cmd == 'V':
            cy = params[0]
            result.append(('L', [cx, cy]))
        elif cmd == 'v':
            cy += params[0]
            result.append(('L', [cx, cy]))
        elif cmd == 'C':
            result.append(('C', list(params)))
            last_cp = (params[2], params[3])
            cx, cy = params[4], params[5]
        elif cmd == 'c':
            abs_params = [
                cx + params[0], cy + params[1],
                cx + params[2], cy + params[3],
                cx + params[4], cy + params[5],
            ]
            result.append(('C', abs_params))
            last_cp = (abs_params[2], abs_params[3])
            cx, cy = abs_params[4], abs_params[5]
        elif cmd == 'S':
            # Smooth cubic: reflect last control point
            if last_cp:
                cp1x = 2 * cx - last_cp[0]
                cp1y = 2 * cy - last_cp[1]
            else:
                cp1x, cp1y = cx, cy
            result.append(('C', [cp1x, cp1y, params[0], params[1], params[2], params[3]]))
            last_cp = (params[0], params[1])
            cx, cy = params[2], params[3]
        elif cmd == 's':
            if last_cp:
                cp1x = 2 * cx - last_cp[0]
                cp1y = 2 * cy - last_cp[1]
            else:
                cp1x, cp1y = cx, cy
            abs_params = [
                cp1x, cp1y,
                cx + params[0], cy + params[1],
                cx + params[2], cy + params[3],
            ]
            result.append(('C', abs_params))
            last_cp = (abs_params[2], abs_params[3])
            cx, cy = abs_params[4], abs_params[5]
        elif cmd == 'Q':
            result.append(('Q', list(params)))
            last_cp = (params[0], params[1])
            cx, cy = params[2], params[3]
        elif cmd == 'q':
            abs_params = [
                cx + params[0], cy + params[1],
                cx + params[2], cy + params[3],
            ]
            result.append(('Q', abs_params))
            last_cp = (abs_params[0], abs_params[1])
            cx, cy = abs_params[2], abs_params[3]
        elif cmd == 'T':
            if last_cp:
                cpx = 2 * cx - last_cp[0]
                cpy = 2 * cy - last_cp[1]
            else:
                cpx, cpy = cx, cy
            result.append(('Q', [cpx, cpy, params[0], params[1]]))
            last_cp = (cpx, cpy)
            cx, cy = params[0], params[1]
        elif cmd == 't':
            if last_cp:
                cpx = 2 * cx - last_cp[0]
                cpy = 2 * cy - last_cp[1]
            else:
                cpx, cpy = cx, cy
            abs_params = [cpx, cpy, cx + params[0], cy + params[1]]
            result.append(('Q', abs_params))
            last_cp = (cpx, cpy)
            cx, cy = abs_params[2], abs_params[3]
        elif cmd in ('A', 'a'):
            # Arc — convert to line for now (proper arc encoding is complex)
            if cmd == 'a':
                ex, ey = cx + params[5], cy + params[6]
            else:
                ex, ey = params[5], params[6]
            result.append(('L', [ex, ey]))
            cx, cy = ex, ey
        elif cmd in ('Z', 'z'):
            result.append(('Z', []))
            cx, cy = sx, sy
            last_cp = None
            continue

        if cmd not in ('C', 'c', 'S', 's', 'Q', 'q', 'T', 't'):
            last_cp = None

    return result


# ============================================================================
# TINYVG ENCODER
# ============================================================================

class TVGWriter:
    def __init__(self):
        self.buf = bytearray()

    def write_byte(self, v):
        self.buf.append(v & 0xFF)

    def write_u16(self, v):
        self.buf += struct.pack("<h", int(v))

    def write_varuint(self, v):
        v = int(v)
        while v >= 0x80:
            self.buf.append(0x80 | (v & 0x7F))
            v >>= 7
        self.buf.append(v & 0x7F)

    def write_unit(self, v):
        """Write a Unit as i16."""
        iv = int(round(v))
        iv = max(-32768, min(32767, iv))
        self.buf += struct.pack("<h", iv)


def segments_from_commands(commands):
    """Split absolute commands into segments (subpaths)."""
    segments = []
    current = []

    for cmd, params in commands:
        if cmd == 'M':
            if current:
                segments.append(current)
            current = [('M', params)]
        elif cmd == 'Z':
            current.append(('Z', []))
            segments.append(current)
            current = []
        else:
            current.append((cmd, params))

    if current:
        segments.append(current)

    return segments


def encode_tvg(paths, width, height, scale_bits=4):
    """Encode parsed SVG paths as TinyVG binary."""
    w = TVGWriter()

    # Magic
    w.write_byte(0x72)  # 'r'
    w.write_byte(0x56)  # 'V'

    # Version
    w.write_byte(1)

    # Flags: scale(u4) | color_enc(u2) | coord_range(u2)
    # scale_bits=4, color_enc=0 (RGBA8888), coord_range=0 (i16)
    flags = (scale_bits & 0xF) | (0 << 4) | (0 << 6)
    w.write_byte(flags)

    # Width, Height (as Units with scale_bits fractional bits)
    scale = 1 << scale_bits
    w.write_unit(int(width * scale))
    w.write_unit(int(height * scale))

    # Color table: just black fill
    w.write_varuint(1)  # 1 color
    w.write_byte(0)     # R
    w.write_byte(0)     # G
    w.write_byte(0)     # B
    w.write_byte(255)   # A

    # Convert each path to segments
    all_segments = []
    for path_cmds in paths:
        segs = segments_from_commands(path_cmds)
        for seg in segs:
            all_segments.append(seg)

    if not all_segments:
        # End command
        w.write_byte(0x00)
        return bytes(w.buf)

    # Fill path command
    # cmd_byte: cmd_id(u6) | prim_style_kind(u2)
    # cmd_id=3 (fill_path), style_kind=0 (flat)
    cmd_byte = 3 | (0 << 6)
    w.write_byte(cmd_byte)

    # segment_count (VarUInt, offset by 1)
    w.write_varuint(len(all_segments) - 1)

    # Style: flat color index 0
    w.write_varuint(0)

    # Encode path segments
    # First: all segment command counts
    for seg in all_segments:
        cmds = [c for c in seg if c[0] != 'M']
        w.write_varuint(max(len(cmds) - 1, 0))

    # Then: segment data
    for seg in all_segments:
        # Start point from M command
        start = seg[0]
        if start[0] == 'M':
            sx, sy = start[1][0], start[1][1]
        else:
            sx, sy = 0, 0

        w.write_unit(int(sx * scale))
        w.write_unit(int(sy * scale))

        # Commands
        for cmd, params in seg:
            if cmd == 'M':
                continue

            if cmd == 'L':
                # Line: tag=0
                w.write_byte(0)
                w.write_unit(int(params[0] * scale))
                w.write_unit(int(params[1] * scale))

            elif cmd == 'C':
                # Cubic bezier: tag=3
                w.write_byte(3)
                w.write_unit(int(params[0] * scale))
                w.write_unit(int(params[1] * scale))
                w.write_unit(int(params[2] * scale))
                w.write_unit(int(params[3] * scale))
                w.write_unit(int(params[4] * scale))
                w.write_unit(int(params[5] * scale))

            elif cmd == 'Q':
                # Quadratic bezier: tag=7
                w.write_byte(7)
                w.write_unit(int(params[0] * scale))
                w.write_unit(int(params[1] * scale))
                w.write_unit(int(params[2] * scale))
                w.write_unit(int(params[3] * scale))

            elif cmd == 'Z':
                # Close: tag=6
                w.write_byte(6)

    # End command
    w.write_byte(0x00)

    return bytes(w.buf)


# ============================================================================
# SVG FILE PARSER
# ============================================================================

def parse_svg_file(svg_path):
    """Extract paths and viewBox from SVG file."""
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Handle namespace
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'

    # Get viewBox
    vb = root.get('viewBox', '0 0 1024 1024')
    parts = vb.split()
    vb_x, vb_y = float(parts[0]), float(parts[1])
    vb_w, vb_h = float(parts[2]), float(parts[3])

    # Find all path elements
    paths = []
    for elem in root.iter(ns + 'path'):
        d = elem.get('d', '')
        if d:
            cmds = parse_path(d)
            abs_cmds = to_absolute(cmds)
            paths.append(abs_cmds)

    return paths, vb_w, vb_h


def convert_file(svg_path, tvg_path):
    """Convert a single SVG file to TVG."""
    paths, width, height = parse_svg_file(svg_path)
    if not paths:
        return False

    tvg_data = encode_tvg(paths, width, height)
    with open(tvg_path, 'wb') as f:
        f.write(tvg_data)
    return True


def convert_directory(svg_dir, tvg_dir):
    """Batch convert all SVGs in a directory."""
    os.makedirs(tvg_dir, exist_ok=True)
    converted = 0
    failed = 0

    svg_files = sorted(f for f in os.listdir(svg_dir) if f.endswith('.svg'))
    for fname in svg_files:
        svg_path = os.path.join(svg_dir, fname)
        tvg_name = fname.replace('.svg', '.tvg')
        tvg_path = os.path.join(tvg_dir, tvg_name)

        try:
            if convert_file(svg_path, tvg_path):
                converted += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [fail] {fname}: {e}")
            failed += 1

    print(f"[svg2tvg] Converted {converted}, failed {failed}")
    return converted


# ============================================================================
# MAIN
# ============================================================================

def main():
    if len(sys.argv) < 3:
        print("Usage: svg2tvg.py <input.svg|input_dir/> <output.tvg|output_dir/>")
        sys.exit(1)

    src = sys.argv[1]
    dst = sys.argv[2]

    if os.path.isdir(src):
        convert_directory(src, dst)
    else:
        if convert_file(src, dst):
            sz = os.path.getsize(dst)
            print(f"[svg2tvg] {src} -> {dst} ({sz} bytes)")
        else:
            print(f"[svg2tvg] Failed: {src}")
            sys.exit(1)


if __name__ == "__main__":
    main()