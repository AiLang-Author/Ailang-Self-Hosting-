#!/usr/bin/env python3
import os
import math
import numpy as np

def project_to_box_boundary(cx, cy, x, y, dx=100, dy=50):
    # Ray from (cx, cy) through (x, y) to box boundary [0, dx] x [0, dy]
    vx = x - cx
    vy = y - cy

    scale_x = float('inf')
    scale_y = float('inf')

    if vx > 1e-9:
        scale_x = (dx - cx) / vx
    elif vx < -1e-9:
        scale_x = (0.0 - cx) / vx

    if vy > 1e-9:
        scale_y = (dy - cy) / vy
    elif vy < -1e-9:
        scale_y = (0.0 - cy) / vy

    scale = min(scale_x, scale_y)
    bx = cx + scale * vx
    by = cy + scale * vy
    return bx, by

def gen_box_with_exact_hole(dx=100, dy=50, dz=25, hole_rad=10, segments=32):
    tris = []
    cx, cy = dx / 2.0, dy / 2.0

    # Vertices of inner circle and projected outer boundary
    bot_hole = []
    top_hole = []
    bot_out = []
    top_out = []

    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        hx = cx + hole_rad * math.cos(theta)
        hy = cy + hole_rad * math.sin(theta)

        bx, by = project_to_box_boundary(cx, cy, hx, hy, dx, dy)

        bot_hole.append([hx, hy, 0.0])
        top_hole.append([hx, hy, dz])

        bot_out.append([bx, by, 0.0])
        top_out.append([bx, by, dz])

    # 1. Inner Hole Cylinder Wall (Normal facing center)
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_hole[i], top_hole[ni], bot_hole[ni]])
        tris.append([bot_hole[i], top_hole[i], top_hole[ni]])

    # 2. Outer 4 Vertical Side Walls
    p = np.array([
        [0,0,0], [dx,0,0], [dx,dy,0], [0,dy,0],
        [0,0,dz], [dx,0,dz], [dx,dy,dz], [0,dy,dz]
    ])
    # Front (-Y)
    tris.append([p[0], p[1], p[5]]); tris.append([p[0], p[5], p[4]])
    # Right (+X)
    tris.append([p[1], p[2], p[6]]); tris.append([p[1], p[6], p[5]])
    # Back (+Y)
    tris.append([p[2], p[3], p[7]]); tris.append([p[2], p[7], p[6]])
    # Left (-X)
    tris.append([p[3], p[0], p[4]]); tris.append([p[3], p[4], p[7]])

    # 3. Top Planar Face with True Hole Cutout (+Z)
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([top_hole[i], top_out[i], top_hole[ni]])
        tris.append([top_out[i], top_out[ni], top_hole[ni]])

    # 4. Bottom Planar Face with True Hole Cutout (-Z)
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_hole[i], bot_hole[ni], bot_out[i]])
        tris.append([bot_out[i], bot_hole[ni], bot_out[ni]])

    return tris

def write_stl_ascii(filename, triangles, name="CAD_Model"):
    with open(filename, 'w') as f:
        f.write(f"solid {name}\n")
        for tri in triangles:
            p0, p1, p2 = np.array(tri[0]), np.array(tri[1]), np.array(tri[2])
            v1 = p1 - p0
            v2 = p2 - p0
            normal = np.cross(v1, v2)
            norm_len = np.linalg.norm(normal)
            if norm_len > 1e-9:
                normal = normal / norm_len
            else:
                normal = np.array([0.0, 0.0, 1.0])

            f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {p0[0]:.6f} {p0[1]:.6f} {p0[2]:.6f}\n")
            f.write(f"      vertex {p1[0]:.6f} {p1[1]:.6f} {p1[2]:.6f}\n")
            f.write(f"      vertex {p2[0]:.6f} {p2[1]:.6f} {p2[2]:.6f}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write(f"endsolid {name}\n")

if __name__ == '__main__':
    tris = gen_box_with_exact_hole(100, 50, 25, 10, 32)
    write_stl_ascii('/mnt/c/Users/Sean/Documents/AILangSH/test-stl/01_box_with_hole.stl', tris, "BoxWithHole")
    write_stl_ascii('/home/sean/cli_model.stl', tris, "BoxWithHole")
    print(f"Generated exact box with drilled hole: {len(tris)} Triangles")
