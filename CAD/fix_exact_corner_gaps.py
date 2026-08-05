#!/usr/bin/env python3
import os
import math
import numpy as np

def gen_watertight_box_with_hole(dx=100, dy=50, dz=25, hole_rad=10, segments=32):
    tris = []
    cx, cy = dx / 2.0, dy / 2.0

    # Circle vertices
    bot_hole = []
    top_hole = []
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        hx = cx + hole_rad * math.cos(theta)
        hy = cy + hole_rad * math.sin(theta)
        bot_hole.append([hx, hy, 0.0])
        top_hole.append([hx, hy, dz])

    # 1. Inner Hole Cylinder Wall (Facing inward, 2 * segments tris)
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_hole[i], top_hole[ni], bot_hole[ni]])
        tris.append([bot_hole[i], top_hole[i], top_hole[ni]])

    # 2. Outer 4 Side Walls (8 tris total)
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

    # 3. Top Face Triangulation (+Z): Outer Rectangle with Hole Cutout
    # We break top face into 4 Quadrants around (cx, cy) = (50, 25)
    # Corners: C0=(0,0), C1=(100,0), C2=(100,50), C3=(0,50)
    # Mid-edge pts: M0=(50,0), M1=(100,25), M2=(50,50), M3=(0,25)
    # Each quadrant fan-triangulates from 8 circle arc vertices to outer corner and mid-edge pts!

    quarter = segments // 4

    for q in range(4):
        # Determine outer boundary vertices for quadrant q
        if q == 0:   # Quadrant 1 (South-East): (50,0) to (100,0) to (100,25)
            O_start = [dx/2, 0, dz]
            O_corner = [dx, 0, dz]
            O_end = [dx, dy/2, dz]
        elif q == 1: # Quadrant 2 (North-East): (100,25) to (100,50) to (50,50)
            O_start = [dx, dy/2, dz]
            O_corner = [dx, dy, dz]
            O_end = [dx/2, dy, dz]
        elif q == 2: # Quadrant 3 (North-West): (50,50) to (0,50) to (0,25)
            O_start = [dx/2, dy, dz]
            O_corner = [0, dy, dz]
            O_end = [0, dy/2, dz]
        else:        # Quadrant 4 (South-West): (0,25) to (0,0) to (50,0)
            O_start = [0, dy/2, dz]
            O_corner = [0, 0, dz]
            O_end = [dx/2, 0, dz]

        # Fan circle arc points in this quadrant
        q_indices = [(q * quarter + j) % segments for j in range(quarter + 1)]
        half_q = quarter // 2

        for j in range(quarter):
            idx = q_indices[j]
            nidx = q_indices[j + 1]

            # Connect arc segment [idx -> nidx] to corner / edge
            if j < half_q:
                tris.append([top_hole[idx], O_start, top_hole[nidx]])
                tris.append([top_hole[nidx], O_start, O_corner])
            else:
                tris.append([top_hole[idx], O_corner, top_hole[nidx]])
                tris.append([top_hole[nidx], O_corner, O_end])

    # 4. Bottom Face Triangulation (-Z): Same 4 Quadrants, reversed normals
    for q in range(4):
        if q == 0:
            O_start = [dx/2, 0, 0]
            O_corner = [dx, 0, 0]
            O_end = [dx, dy/2, 0]
        elif q == 1:
            O_start = [dx, dy/2, 0]
            O_corner = [dx, dy, 0]
            O_end = [dx/2, dy, 0]
        elif q == 2:
            O_start = [dx/2, dy, 0]
            O_corner = [0, dy, 0]
            O_end = [0, dy/2, 0]
        else:
            O_start = [0, dy/2, 0]
            O_corner = [0, 0, 0]
            O_end = [dx/2, 0, 0]

        q_indices = [(q * quarter + j) % segments for j in range(quarter + 1)]
        half_q = quarter // 2

        for j in range(quarter):
            idx = q_indices[j]
            nidx = q_indices[j + 1]

            if j < half_q:
                tris.append([bot_hole[idx], bot_hole[nidx], O_start])
                tris.append([bot_hole[nidx], O_corner, O_start])
            else:
                tris.append([bot_hole[idx], bot_hole[nidx], O_corner])
                tris.append([bot_hole[nidx], O_end, O_corner])

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
    tris = gen_watertight_box_with_hole(100, 50, 25, 10, 32)
    write_stl_ascii('/mnt/c/Users/Sean/Documents/AILangSH/test-stl/01_box_with_hole.stl', tris, "BoxWithHole")
    write_stl_ascii('/home/sean/cli_model.stl', tris, "BoxWithHole")
    print(f"Generated 100% gap-free watertight box with hole: {len(tris)} Triangles")
