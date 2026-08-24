#!/usr/bin/env python3
"""
svg2tvg.py — Convert SVG to TinyVG binary format.

Handles two SVG subsets:
  1. Font glyphs: path-only, single black fill (FontForge exports)
  2. Widget atoms: rect + path elements, linearGradient fills, stroke, opacity

Usage:
    python3 svg2tvg.py input.svg output.tvg
    python3 svg2tvg.py input_dir/ output_dir/

Supports SVG path commands: M m L l H h V v C c S s Q q T t Z z A a
Supports SVG elements: <path>, <rect> (with rx/ry), <line>
Supports fills: flat color (#hex, named), url(#gradient), opacity
Supports strokes: flat color with stroke-width
Supports linearGradient with 2+ stops (first/last used for TVG)

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
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
            current_cmd = None
            continue

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
    sx, sy = 0, 0
    last_cp = None

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
# COLOR PARSING
# ============================================================================

def parse_hex_color(s):
    """Parse #RGB, #RRGGBB, or #RRGGBBAA to (r, g, b, a)."""
    s = s.strip().lstrip('#')
    if len(s) == 3:
        r = int(s[0] * 2, 16)
        g = int(s[1] * 2, 16)
        b = int(s[2] * 2, 16)
        return (r, g, b, 255)
    elif len(s) == 6:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        return (r, g, b, 255)
    elif len(s) == 8:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = int(s[6:8], 16)
        return (r, g, b, a)
    return (0, 0, 0, 255)


NAMED_COLORS = {
    'white': (255, 255, 255, 255),
    'black': (0, 0, 0, 255),
    'red': (255, 0, 0, 255),
    'green': (0, 128, 0, 255),
    'blue': (0, 0, 255, 255),
    'none': None,
}


def parse_color(s):
    """Parse a color string. Returns (r,g,b,a) or None for 'none'."""
    if s is None:
        return None
    s = s.strip().lower()
    if s == 'none':
        return None
    if s in NAMED_COLORS:
        return NAMED_COLORS[s]
    if s.startswith('#'):
        return parse_hex_color(s)
    return None


def apply_opacity(color, opacity):
    """Apply opacity (0.0-1.0) to color's alpha channel."""
    if color is None:
        return None
    r, g, b, a = color
    a = int(a * opacity)
    return (r, g, b, a)


# ============================================================================
# TINYVG ENCODER
# ============================================================================

class TVGWriter:
    def __init__(self, coord_range=0):
        self.buf = bytearray()
        self.coord_range = coord_range  # 0=i16(default), 3=i32

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
        """Write a coordinate unit as i16 or i32 depending on coord_range."""
        iv = int(round(v))
        if self.coord_range == 3:  # i32
            iv = max(-2147483648, min(2147483647, iv))
            self.buf += struct.pack("<i", iv)
        else:  # i16 (default)
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


def rect_to_path(x, y, w, h, rx=0, ry=0):
    """Convert a <rect> to a list of path commands (absolute)."""
    rx = min(rx, w / 2)
    ry = min(ry, h / 2)
    if ry == 0:
        ry = rx  # SVG spec: if ry missing, ry = rx

    cmds = []
    if rx > 0 and ry > 0:
        # Rounded rect as 4 lines + 4 quarter-circle arcs (approximated with cubics)
        # kappa for 90-degree arc
        k = 0.5522847498
        kx = rx * k
        ky = ry * k

        cmds.append(('M', [x + rx, y]))
        cmds.append(('L', [x + w - rx, y]))
        cmds.append(('C', [x + w - rx + kx, y, x + w, y + ry - ky, x + w, y + ry]))
        cmds.append(('L', [x + w, y + h - ry]))
        cmds.append(('C', [x + w, y + h - ry + ky, x + w - rx + kx, y + h, x + w - rx, y + h]))
        cmds.append(('L', [x + rx, y + h]))
        cmds.append(('C', [x + rx - kx, y + h, x, y + h - ry + ky, x, y + h - ry]))
        cmds.append(('L', [x, y + ry]))
        cmds.append(('C', [x, y + ry - ky, x + rx - kx, y, x + rx, y]))
        cmds.append(('Z', []))
    else:
        cmds.append(('M', [x, y]))
        cmds.append(('L', [x + w, y]))
        cmds.append(('L', [x + w, y + h]))
        cmds.append(('L', [x, y + h]))
        cmds.append(('Z', []))

    return cmds


def ellipse_to_path(cx, cy, rx, ry):
    """Convert a circle/ellipse to path commands using 4 cubic Bezier arcs."""
    k = 0.5522847498
    kx = rx * k
    ky = ry * k

    cmds = [
        ('M', [cx, cy - ry]),
        ('C', [cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy]),
        ('C', [cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry]),
        ('C', [cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy]),
        ('C', [cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry]),
        ('Z', []),
    ]
    return cmds


def reverse_closed_path(commands):
    """Reverse a closed path (M, L/C, ..., Z) preserving curve types.

    For cubic beziers, swap the control points and reverse order.
    Input must be a single closed subpath (M...Z).
    """
    # Collect commands (skip M and Z)
    cmds = []
    start_pt = None
    for cmd, params in commands:
        if cmd == 'M':
            start_pt = params[:2]
        elif cmd == 'Z':
            continue
        else:
            cmds.append((cmd, params))

    if not cmds or start_pt is None:
        return commands

    # Build a list of (endpoint, command_type, full_params)
    # For reversal, we need to know the start point of each segment
    points = [start_pt]  # points[i] = start of cmd[i]
    for cmd, params in cmds:
        if cmd == 'L':
            points.append(params[:2])
        elif cmd == 'C':
            points.append([params[4], params[5]])  # end point
        elif cmd == 'Q':
            points.append([params[2], params[3]])  # end point

    # The last point before Z should connect back to start_pt
    # Reversed path starts at points[-1], ends at points[0]
    rev = [('M', list(points[-1]))]
    for i in range(len(cmds) - 1, -1, -1):
        cmd, params = cmds[i]
        if cmd == 'L':
            rev.append(('L', list(points[i])))
        elif cmd == 'C':
            # Reverse cubic: swap control points, end = previous start
            # Original: start=points[i], cp1=params[0:2], cp2=params[2:4], end=params[4:6]
            # Reversed: start=params[4:6], cp1=params[2:4], cp2=params[0:2], end=points[i]
            rev.append(('C', [params[2], params[3], params[0], params[1],
                              points[i][0], points[i][1]]))
        elif cmd == 'Q':
            # Reverse quad: control stays, end = previous start
            rev.append(('Q', [params[0], params[1],
                              points[i][0], points[i][1]]))
    rev.append(('Z', []))
    return rev


def stroke_path_to_fill(commands, stroke_width):
    """Expand a stroked open path into a filled outline (thick line).

    For each line segment, offsets perpendicular by half stroke_width
    to create a filled quad. For simplicity, uses miter joins.
    """
    # Collect points from the path
    points = []
    for cmd, params in commands:
        if cmd == 'M':
            points.append((params[0], params[1]))
        elif cmd == 'L':
            points.append((params[0], params[1]))

    if len(points) < 2:
        return commands  # can't expand

    hw = stroke_width / 2.0
    left_side = []
    right_side = []

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dx = x1 - x0
        dy = y1 - y0
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.001:
            continue
        nx = -dy / length * hw
        ny = dx / length * hw
        left_side.append((x0 + nx, y0 + ny))
        left_side.append((x1 + nx, y1 + ny))
        right_side.append((x0 - nx, y0 - ny))
        right_side.append((x1 - nx, y1 - ny))

    if not left_side:
        return commands

    # Build closed path: left forward, right backward
    result = [('M', [left_side[0][0], left_side[0][1]])]
    for p in left_side[1:]:
        result.append(('L', [p[0], p[1]]))
    for p in reversed(right_side):
        result.append(('L', [p[0], p[1]]))
    result.append(('Z', []))
    return result


# ============================================================================
# WIDGET-AWARE TVG ENCODER
# ============================================================================

def encode_tvg_widget(draw_ops, width, height, scale_bits=0):
    """Encode a list of draw operations as TinyVG binary.

    Each draw_op is a dict:
      - 'type': 'fill_path' or 'fill_rect'
      - 'segments': list of command lists (for fill_path)
      - 'style': 'flat' or 'linear_gradient'
      - 'color': (r,g,b,a) for flat
      - 'gradient': {x1,y1,x2,y2,color0,color1} for linear_gradient
    """
    # Collect all unique colors and gradients
    colors = []
    color_map = {}
    gradient_list = []

    def add_color(c):
        key = c
        if key not in color_map:
            color_map[key] = len(colors)
            colors.append(c)
        return color_map[key]

    # Pre-scan to build color table
    for op in draw_ops:
        if op['style'] == 'flat':
            add_color(op['color'])
        elif op['style'] == 'linear_gradient':
            g = op['gradient']
            add_color(g['color0'])
            add_color(g['color1'])

    w = TVGWriter()

    # Magic
    w.write_byte(0x72)
    w.write_byte(0x56)

    # Version
    w.write_byte(1)

    # Flags: scale(u4) | color_enc(u2) | coord_range(u2)
    # scale_bits for fractional coords, color_enc=0 (RGBA8888), coord_range=0 (i16)
    flags = (scale_bits & 0xF) | (0 << 4) | (0 << 6)
    w.write_byte(flags)

    scale = 1 << scale_bits
    w.write_unit(int(width * scale))
    w.write_unit(int(height * scale))

    # Color table
    w.write_varuint(len(colors))
    for (r, g_c, b, a) in colors:
        w.write_byte(r)
        w.write_byte(g_c)
        w.write_byte(b)
        w.write_byte(a)

    # Encode draw commands
    for op in draw_ops:
        segments = op.get('segments', [])
        if not segments:
            continue

        # Determine style kind: 0=flat, 1=linear_gradient
        if op['style'] == 'flat':
            style_kind = 0
        elif op['style'] == 'linear_gradient':
            style_kind = 1
        else:
            style_kind = 0

        # TinyVG fill_path command: cmd_id=3
        cmd_byte = 3 | (style_kind << 6)
        w.write_byte(cmd_byte)

        # segment_count - 1
        w.write_varuint(len(segments) - 1)

        # Style data
        if style_kind == 0:
            # Flat: color index
            w.write_varuint(add_color(op['color']))
        elif style_kind == 1:
            # Linear gradient: point0, point1, color_idx0, color_idx1
            g = op['gradient']
            w.write_unit(int(g['x1'] * scale))
            w.write_unit(int(g['y1'] * scale))
            w.write_unit(int(g['x2'] * scale))
            w.write_unit(int(g['y2'] * scale))
            w.write_varuint(add_color(g['color0']))
            w.write_varuint(add_color(g['color1']))

        # Segment command counts
        for seg in segments:
            cmds = [c for c in seg if c[0] != 'M']
            w.write_varuint(max(len(cmds) - 1, 0))

        # Segment data
        for seg in segments:
            start = seg[0]
            if start[0] == 'M':
                sx, sy = start[1][0], start[1][1]
            else:
                sx, sy = 0, 0
            w.write_unit(int(sx * scale))
            w.write_unit(int(sy * scale))

            for cmd, params in seg:
                if cmd == 'M':
                    continue
                if cmd == 'L':
                    w.write_byte(0)
                    w.write_unit(int(params[0] * scale))
                    w.write_unit(int(params[1] * scale))
                elif cmd == 'C':
                    w.write_byte(3)
                    for p in params:
                        w.write_unit(int(p * scale))
                elif cmd == 'Q':
                    w.write_byte(7)
                    for p in params:
                        w.write_unit(int(p * scale))
                elif cmd == 'Z':
                    w.write_byte(6)

    # End command
    w.write_byte(0x00)
    return bytes(w.buf)


# ============================================================================
# LEGACY GLYPH ENCODER (unchanged behavior for font glyphs)
# ============================================================================

def flip_y_paths(paths, height):
    """Flip Y coordinates in all paths: y → height - y.

    FontForge exports SVG glyphs with Y-up (font convention) where
    y=0 is the baseline and y=ascent is the top. The TVG rasterizer
    uses Y-down (screen convention). This function corrects the
    coordinate system mismatch.
    """
    flipped = []
    for path_cmds in paths:
        new_cmds = []
        for cmd, params in path_cmds:
            if cmd == 'M' or cmd == 'L':
                new_cmds.append((cmd, [params[0], height - params[1]]))
            elif cmd == 'C':
                new_cmds.append((cmd, [
                    params[0], height - params[1],
                    params[2], height - params[3],
                    params[4], height - params[5],
                ]))
            elif cmd == 'Q':
                new_cmds.append((cmd, [
                    params[0], height - params[1],
                    params[2], height - params[3],
                ]))
            elif cmd == 'Z':
                new_cmds.append((cmd, []))
            else:
                new_cmds.append((cmd, params))
        flipped.append(new_cmds)
    return flipped


def encode_tvg(paths, width, height, scale_bits=0, coord_range=0):
    """Encode parsed SVG paths as TinyVG binary (single black fill).
    coord_range: 0=i16(default), 3=i32.  scale_bits: fractional precision."""
    w = TVGWriter(coord_range=coord_range)
    w.write_byte(0x72)
    w.write_byte(0x56)
    w.write_byte(1)

    flags = (scale_bits & 0xF) | (0 << 4) | ((coord_range & 3) << 6)
    w.write_byte(flags)

    scale = 1 << scale_bits
    # Width and height in the header are UNSCALED design units.
    # Coordinates in the body are scaled by (1 << scale_bits).
    w.write_unit(int(round(width)))
    w.write_unit(int(round(height)))

    w.write_varuint(1)
    w.write_byte(0)
    w.write_byte(0)
    w.write_byte(0)
    w.write_byte(255)

    all_segments = []
    for path_cmds in paths:
        segs = segments_from_commands(path_cmds)
        for seg in segs:
            all_segments.append(seg)

    if not all_segments:
        w.write_byte(0x00)
        return bytes(w.buf)

    cmd_byte = 3 | (0 << 6)
    w.write_byte(cmd_byte)
    w.write_varuint(len(all_segments) - 1)
    w.write_varuint(0)

    for seg in all_segments:
        cmds = [c for c in seg if c[0] != 'M']
        w.write_varuint(max(len(cmds) - 1, 0))

    for seg in all_segments:
        start = seg[0]
        if start[0] == 'M':
            sx, sy = start[1][0], start[1][1]
        else:
            sx, sy = 0, 0
        w.write_unit(round(sx * scale))
        w.write_unit(round(sy * scale))

        for cmd, params in seg:
            if cmd == 'M':
                continue
            if cmd == 'L':
                w.write_byte(0)
                w.write_unit(round(params[0] * scale))
                w.write_unit(round(params[1] * scale))
            elif cmd == 'C':
                w.write_byte(3)
                for p in params:
                    w.write_unit(round(p * scale))
            elif cmd == 'Q':
                w.write_byte(7)
                for p in params:
                    w.write_unit(round(p * scale))
            elif cmd == 'Z':
                w.write_byte(6)

    w.write_byte(0x00)
    return bytes(w.buf)


# ============================================================================
# SVG FILE PARSER — WIDGET MODE
# ============================================================================

def parse_gradients(root, ns):
    """Parse all <linearGradient> definitions from <defs>."""
    gradients = {}
    for defs in root.iter(ns + 'defs'):
        for lg in defs.iter(ns + 'linearGradient'):
            gid = lg.get('id', '')
            x1 = float(lg.get('x1', '0'))
            y1 = float(lg.get('y1', '0'))
            x2 = float(lg.get('x2', '0'))
            y2 = float(lg.get('y2', '1'))
            stops = []
            for stop in lg.iter(ns + 'stop'):
                offset_s = stop.get('offset', '0')
                offset_s = offset_s.replace('%', '')
                offset = float(offset_s)
                if offset > 1.0 and offset <= 100.0:
                    offset /= 100.0
                color_s = stop.get('stop-color', '#000000')
                color = parse_hex_color(color_s)
                stops.append((offset, color))
            gradients[gid] = {
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'stops': sorted(stops, key=lambda s: s[0]),
            }
    return gradients


def resolve_fill(fill_attr, gradients, vb_w, vb_h, elem_x, elem_y, elem_w, elem_h):
    """Resolve a fill attribute to a style dict.

    Returns: ('flat', color) or ('linear_gradient', gradient_dict) or None
    """
    if fill_attr is None or fill_attr.lower() == 'none':
        return None

    m = re.match(r'url\(#([^)]+)\)', fill_attr)
    if m:
        gid = m.group(1)
        if gid in gradients:
            g = gradients[gid]
            stops = g['stops']
            if len(stops) < 2:
                return ('flat', stops[0][1] if stops else (0, 0, 0, 255))
            c0 = stops[0][1]
            c1 = stops[-1][1]
            # Gradient coords are in objectBoundingBox (0-1 range)
            # Map to element coordinates
            gx1 = elem_x + g['x1'] * elem_w
            gy1 = elem_y + g['y1'] * elem_h
            gx2 = elem_x + g['x2'] * elem_w
            gy2 = elem_y + g['y2'] * elem_h
            return ('linear_gradient', {
                'x1': gx1, 'y1': gy1,
                'x2': gx2, 'y2': gy2,
                'color0': c0, 'color1': c1,
            })
        return None

    color = parse_color(fill_attr)
    if color:
        return ('flat', color)
    return None


def parse_svg_widget(svg_path):
    """Parse an SVG file with rect+path elements, gradients, strokes.

    Returns: (draw_ops, width, height) where draw_ops is a list of
    dicts ready for encode_tvg_widget().
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'

    vb = root.get('viewBox', '0 0 32 32')
    parts = vb.split()
    vb_w = float(parts[2])
    vb_h = float(parts[3])

    gradients = parse_gradients(root, ns)
    draw_ops = []

    # Process elements in document order (direct children of root)
    for elem in root:
        tag = elem.tag.replace(ns, '')
        if tag == 'defs':
            continue

        opacity = float(elem.get('opacity', '1.0'))

        if tag == 'rect':
            x = float(elem.get('x', '0'))
            y = float(elem.get('y', '0'))
            w = float(elem.get('width', '0'))
            h = float(elem.get('height', '0'))
            rx = float(elem.get('rx', '0'))
            ry = float(elem.get('ry', str(rx)))

            # Fill
            fill_attr = elem.get('fill', 'black')
            fill_style = resolve_fill(fill_attr, gradients, vb_w, vb_h, x, y, w, h)

            if fill_style:
                path_cmds = rect_to_path(x, y, w, h, rx, ry)
                segs = segments_from_commands(path_cmds)
                op = {'segments': segs}
                if fill_style[0] == 'flat':
                    color = fill_style[1]
                    if opacity < 1.0:
                        color = apply_opacity(color, opacity)
                    op['style'] = 'flat'
                    op['color'] = color
                else:
                    gd = fill_style[1]
                    if opacity < 1.0:
                        gd = dict(gd)
                        gd['color0'] = apply_opacity(gd['color0'], opacity)
                        gd['color1'] = apply_opacity(gd['color1'], opacity)
                    op['style'] = 'linear_gradient'
                    op['gradient'] = gd
                draw_ops.append(op)

            # Stroke
            stroke_attr = elem.get('stroke')
            stroke_width = float(elem.get('stroke-width', '1'))
            if stroke_attr and stroke_attr.lower() != 'none' and stroke_width > 0:
                stroke_color = parse_color(stroke_attr)
                if stroke_color:
                    if opacity < 1.0:
                        stroke_color = apply_opacity(stroke_color, opacity)
                    # Create stroke as outline path
                    path_cmds = rect_to_path(x, y, w, h, rx, ry)
                    inner = rect_to_path(
                        x + stroke_width / 2, y + stroke_width / 2,
                        w - stroke_width, h - stroke_width,
                        max(0, rx - stroke_width / 2), max(0, ry - stroke_width / 2)
                    )
                    outer = rect_to_path(
                        x - stroke_width / 2, y - stroke_width / 2,
                        w + stroke_width, h + stroke_width,
                        rx + stroke_width / 2, ry + stroke_width / 2
                    )
                    # Stroke as outer minus inner (even-odd fill)
                    outer_segs = segments_from_commands(outer)
                    inner_rev = reverse_closed_path(inner)
                    inner_segs = segments_from_commands(inner_rev)
                    all_segs = outer_segs + inner_segs

                    draw_ops.append({
                        'style': 'flat',
                        'color': stroke_color,
                        'segments': all_segs,
                    })

        elif tag == 'path':
            d = elem.get('d', '')
            if not d:
                continue
            cmds = parse_path(d)
            abs_cmds = to_absolute(cmds)

            fill_attr = elem.get('fill', 'black')
            stroke_attr = elem.get('stroke')
            stroke_width = float(elem.get('stroke-width', '1'))

            # If fill is not none, emit fill
            if fill_attr and fill_attr.lower() != 'none':
                fill_style = resolve_fill(fill_attr, gradients, vb_w, vb_h, 0, 0, vb_w, vb_h)
                if fill_style:
                    segs = segments_from_commands(abs_cmds)
                    op = {'segments': segs}
                    if fill_style[0] == 'flat':
                        color = fill_style[1]
                        if opacity < 1.0:
                            color = apply_opacity(color, opacity)
                        op['style'] = 'flat'
                        op['color'] = color
                    else:
                        gd = fill_style[1]
                        if opacity < 1.0:
                            gd = dict(gd)
                            gd['color0'] = apply_opacity(gd['color0'], opacity)
                            gd['color1'] = apply_opacity(gd['color1'], opacity)
                        op['style'] = 'linear_gradient'
                        op['gradient'] = gd
                    draw_ops.append(op)

            # If stroke, expand to fill
            if stroke_attr and stroke_attr.lower() != 'none' and stroke_width > 0:
                stroke_color = parse_color(stroke_attr)
                if stroke_color:
                    if opacity < 1.0:
                        stroke_color = apply_opacity(stroke_color, opacity)
                    expanded = stroke_path_to_fill(abs_cmds, stroke_width)
                    segs = segments_from_commands(expanded)
                    draw_ops.append({
                        'style': 'flat',
                        'color': stroke_color,
                        'segments': segs,
                    })

        elif tag == 'line':
            x1 = float(elem.get('x1', '0'))
            y1 = float(elem.get('y1', '0'))
            x2 = float(elem.get('x2', '0'))
            y2 = float(elem.get('y2', '0'))
            stroke_attr = elem.get('stroke', 'black')
            stroke_width = float(elem.get('stroke-width', '1'))
            stroke_color = parse_color(stroke_attr)
            if stroke_color:
                if opacity < 1.0:
                    stroke_color = apply_opacity(stroke_color, opacity)
                line_cmds = [('M', [x1, y1]), ('L', [x2, y2])]
                expanded = stroke_path_to_fill(line_cmds, stroke_width)
                segs = segments_from_commands(expanded)
                draw_ops.append({
                    'style': 'flat',
                    'color': stroke_color,
                    'segments': segs,
                })

        elif tag in ('circle', 'ellipse'):
            if tag == 'circle':
                cx = float(elem.get('cx', '0'))
                cy = float(elem.get('cy', '0'))
                r = float(elem.get('r', '0'))
                rx_e, ry_e = r, r
            else:
                cx = float(elem.get('cx', '0'))
                cy = float(elem.get('cy', '0'))
                rx_e = float(elem.get('rx', '0'))
                ry_e = float(elem.get('ry', '0'))

            if rx_e <= 0 or ry_e <= 0:
                continue

            path_cmds = ellipse_to_path(cx, cy, rx_e, ry_e)

            # Fill
            fill_attr = elem.get('fill', 'black')
            if fill_attr and fill_attr.lower() != 'none':
                # Bounding box for gradient mapping
                bb_x = cx - rx_e
                bb_y = cy - ry_e
                bb_w = rx_e * 2
                bb_h = ry_e * 2
                fill_style = resolve_fill(fill_attr, gradients, vb_w, vb_h,
                                          bb_x, bb_y, bb_w, bb_h)
                if fill_style:
                    segs = segments_from_commands(path_cmds)
                    op = {'segments': segs}
                    if fill_style[0] == 'flat':
                        color = fill_style[1]
                        if opacity < 1.0:
                            color = apply_opacity(color, opacity)
                        op['style'] = 'flat'
                        op['color'] = color
                    else:
                        gd = fill_style[1]
                        if opacity < 1.0:
                            gd = dict(gd)
                            gd['color0'] = apply_opacity(gd['color0'], opacity)
                            gd['color1'] = apply_opacity(gd['color1'], opacity)
                        op['style'] = 'linear_gradient'
                        op['gradient'] = gd
                    draw_ops.append(op)

            # Stroke
            stroke_attr = elem.get('stroke')
            stroke_width = float(elem.get('stroke-width', '1'))
            if stroke_attr and stroke_attr.lower() != 'none' and stroke_width > 0:
                stroke_color = parse_color(stroke_attr)
                if stroke_color:
                    if opacity < 1.0:
                        stroke_color = apply_opacity(stroke_color, opacity)
                    # Outer and inner ellipses for stroke ring
                    outer_cmds = ellipse_to_path(cx, cy,
                                                 rx_e + stroke_width / 2,
                                                 ry_e + stroke_width / 2)
                    inner_cmds = ellipse_to_path(cx, cy,
                                                 max(0, rx_e - stroke_width / 2),
                                                 max(0, ry_e - stroke_width / 2))
                    outer_segs = segments_from_commands(outer_cmds)
                    inner_rev = reverse_closed_path(inner_cmds)
                    inner_segs = segments_from_commands(inner_rev)
                    all_segs = outer_segs + inner_segs
                    draw_ops.append({
                        'style': 'flat',
                        'color': stroke_color,
                        'segments': all_segs,
                    })

    return draw_ops, vb_w, vb_h


# ============================================================================
# SVG FILE PARSER — LEGACY GLYPH MODE
# ============================================================================

def parse_svg_file(svg_path):
    """Extract paths and viewBox from SVG file (glyph mode)."""
    tree = ET.parse(svg_path)
    root = tree.getroot()

    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'

    vb = root.get('viewBox', '0 0 1024 1024')
    parts = vb.split()
    vb_w, vb_h = float(parts[2]), float(parts[3])

    paths = []
    for elem in root.iter(ns + 'path'):
        d = elem.get('d', '')
        if d:
            cmds = parse_path(d)
            abs_cmds = to_absolute(cmds)
            paths.append(abs_cmds)

    return paths, vb_w, vb_h


# ============================================================================
# DETECTION AND CONVERSION
# ============================================================================

def is_widget_svg(svg_path):
    """Detect if an SVG uses widget features (gradients, rects, strokes)."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'

    # Check for <defs> with gradients
    for defs in root.iter(ns + 'defs'):
        for lg in defs.iter(ns + 'linearGradient'):
            return True

    # Check for <rect> elements
    for rect in root.iter(ns + 'rect'):
        return True

    # Check for <circle> or <ellipse> elements
    for _ in root.iter(ns + 'circle'):
        return True
    for _ in root.iter(ns + 'ellipse'):
        return True

    # Check for stroke attributes on paths
    for path in root.iter(ns + 'path'):
        if path.get('stroke') and path.get('stroke', 'none').lower() != 'none':
            return True

    return False


def convert_file(svg_path, tvg_path):
    """Convert a single SVG file to TVG, auto-detecting mode."""
    if is_widget_svg(svg_path):
        draw_ops, width, height = parse_svg_widget(svg_path)
        if not draw_ops:
            return False
        tvg_data = encode_tvg_widget(draw_ops, width, height)
    else:
        paths, width, height = parse_svg_file(svg_path)
        if not paths:
            return False
        # FontForge SVG is already Y-down (viewBox y=0 at the top of the
        # em square). Do not call flip_y_paths — that double-flips glyphs
        # and they render upside-down / backwards on screen.
        # i32 coords + 8 fractional bits keep curve precision.
        tvg_data = encode_tvg(paths, width, height, scale_bits=8, coord_range=3)

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
                sz = os.path.getsize(tvg_path)
                mode = "widget" if is_widget_svg(svg_path) else "glyph"
                print(f"  [{mode:6s}] {fname} -> {tvg_name} ({sz} bytes)")
            else:
                print(f"  [empty] {fname}")
                failed += 1
        except Exception as e:
            print(f"  [fail]  {fname}: {e}")
            failed += 1

    print(f"\n[svg2tvg] Converted {converted}, failed {failed}")
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
