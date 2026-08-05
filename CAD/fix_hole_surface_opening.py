#!/usr/bin/env python3
import os
import math
import numpy as np

def project_ray_to_box(cx, cy, x, y, dx=100, dy=50):
    vx = x - cx
    vy = y - cy

    scale_x = (dx - cx)/vx if vx > 1e-9 else ((0 - cx)/vx if vx < -1e-9 else 1e9)
    scale_y = (dy - cy)/vy if vy > 1e-9 else ((0 - cy)/vy if vy < -1e-9 else 1e9)
    scale = min(scale_x, scale_y)

    bx = cx + scale * vx
    by = cy + scale * vy
    return bx, by

def gen_open_hole_watertight_solid(dx=100, dy=50, dz=25, hole_rad=10, segments=64):
    tris = []
    cx, cy = dx / 2.0, dy / 2.0

    # 1. Circle Vertices (64 uniform angular points)
    bot_hole = []
    top_hole = []
    bot_out = []
    top_out = []

    for i in range(segments):
        theta = 2.0 * math.pi * float(i) / segments
        hx = cx + hole_rad * math.cos(theta)
        hy = cy + hole_rad * math.sin(theta)

        bx, by = project_ray_to_box(cx, cy, hx, hy, dx, dy)

        bot_hole.append([hx, hy, 0.0])
        top_hole.append([hx, hy, dz])

        bot_out.append([bx, by, 0.0])
        top_out.append([bx, by, dz])

    # 2. Inner Cylinder Wall (Inward normals, 2 * segments tris)
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_hole[i], top_hole[ni], bot_hole[ni]])
        tris.append([bot_hole[i], top_hole[i], top_hole[ni]])

    # 3. Top Face Triangulation (+Z): Annulus between outer boundary and inner circle
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([top_hole[i], top_out[i], top_hole[ni]])
        tris.append([top_out[i], top_out[ni], top_hole[ni]])

    # 4. Bottom Face Triangulation (-Z): Annulus
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_hole[i], bot_hole[ni], bot_out[i]])
        tris.append([bot_out[i], bot_hole[ni], bot_out[ni]])

    # 5. Outer 4 Side Walls of the Box
    # Construct side wall quads between adjacent top_out and bot_out points
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_out[i], bot_out[ni], top_out[ni]])
        tris.append([bot_out[i], top_out[ni], top_out[i]])

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
    tris = gen_open_hole_watertight_solid(100, 50, 25, 10, 64)
    write_stl_ascii('/mnt/c/Users/Sean/Documents/AILangSH/test-stl/01_box_with_hole.stl', tris, "BoxWithHole")
    write_stl_ascii('/home/sean/cli_model.stl', tris, "BoxWithHole")
    print(f"Generated open circular hole solid: {len(tris)} Triangles")
