#!/usr/bin/env python3
import os
import math
import numpy as np

def gen_csg_boolean_hole_solid(dx=100, dy=50, dz=25, hole_rad=10, segments=64):
    tris = []
    cx, cy = dx / 2.0, dy / 2.0

    # 1. Circle Vertices (64 uniform angular steps for 100% smooth round circle)
    bot_hole = []
    top_hole = []
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        hx = cx + hole_rad * math.cos(theta)
        hy = cy + hole_rad * math.sin(theta)
        bot_hole.append([hx, hy, 0.0])
        top_hole.append([hx, hy, dz])

    # 2. Inner Cylinder Wall (Inward normals for Subtraction Tool)
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_hole[i], top_hole[ni], bot_hole[ni]])
        tris.append([bot_hole[i], top_hole[i], top_hole[ni]])

    # 3. Outer 4 Side Walls of Base Box Solid
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

    # 4. Top Face Triangulation (+Z): Annulus between outer Box and inner Circle
    # Uniform radial fan from 64 circle points to outer box perimeter
    # Box perimeter sampling (4 corner pts + 60 edge pts)
    top_box_perimeter = []
    bot_box_perimeter = []

    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        # Ray from (cx, cy) outward
        vx = math.cos(theta)
        vy = math.sin(theta)

        scale_x = (dx - cx)/vx if vx > 1e-9 else ((0 - cx)/vx if vx < -1e-9 else 1e9)
        scale_y = (dy - cy)/vy if vy > 1e-9 else ((0 - cy)/vy if vy < -1e-9 else 1e9)
        scale = min(scale_x, scale_y)

        bx = cx + scale * vx
        by = cy + scale * vy

        top_box_perimeter.append([bx, by, dz])
        bot_box_perimeter.append([bx, by, 0.0])

    # Top Face (+Z)
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([top_hole[i], top_box_perimeter[i], top_hole[ni]])
        tris.append([top_box_perimeter[i], top_box_perimeter[ni], top_hole[ni]])

    # Bottom Face (-Z)
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_hole[i], bot_hole[ni], bot_box_perimeter[i]])
        tris.append([bot_box_perimeter[i], bot_hole[ni], bot_box_perimeter[ni]])

    # 5. Box Corners (0,0), (dx,0), (dx,dy), (0,dy) Triangles to seal corners 100%
    corners_top = [[0,0,dz], [dx,0,dz], [dx,dy,dz], [0,dy,dz]]
    corners_bot = [[0,0,0], [dx,0,0], [dx,dy,0], [0,dy,0]]

    # Connect each corner to closest perimeter segment
    quarter = segments // 4
    for q in range(4):
        idx_c = q * quarter
        c_top = corners_top[(q + 3) % 4]
        c_bot = corners_bot[(q + 3) % 4]

        p_top = top_box_perimeter[idx_c]
        p_bot = bot_box_perimeter[idx_c]

        # Top corner patch
        tris.append([p_top, c_top, top_box_perimeter[(idx_c + 1) % segments]])
        # Bottom corner patch
        tris.append([p_bot, bot_box_perimeter[(idx_c + 1) % segments], c_bot])

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
    tris = gen_csg_boolean_hole_solid(100, 50, 25, 10, 64)
    write_stl_ascii('/mnt/c/Users/Sean/Documents/AILangSH/test-stl/01_box_with_hole.stl', tris, "BoxWithHole")
    write_stl_ascii('/home/sean/cli_model.stl', tris, "BoxWithHole")
    print(f"Generated CSG boolean round hole solid: {len(tris)} Triangles")
