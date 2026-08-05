#!/usr/bin/env python3
import os
import math
import numpy as np

def gen_sharp_corners_box_with_hole(dx=100, dy=50, dz=25, hole_rad=10, segments=32):
    tris = []
    cx, cy = dx / 2.0, dy / 2.0

    # 1. Outer Box 8 Vertices (100% Sharp 90-degree Corners)
    p = np.array([
        [0,0,0], [dx,0,0], [dx,dy,0], [0,dy,0],
        [0,0,dz], [dx,0,dz], [dx,dy,dz], [0,dy,dz]
    ])

    # 2. Outer 4 Side Walls (8 tris total)
    # Front (-Y)
    tris.append([p[0], p[1], p[5]]); tris.append([p[0], p[5], p[4]])
    # Right (+X)
    tris.append([p[1], p[2], p[6]]); tris.append([p[1], p[6], p[5]])
    # Back (+Y)
    tris.append([p[2], p[3], p[7]]); tris.append([p[2], p[7], p[6]])
    # Left (-X)
    tris.append([p[3], p[0], p[4]]); tris.append([p[3], p[4], p[7]])

    # 3. Circle Vertices
    bot_hole = []
    top_hole = []
    for i in range(segments):
        theta = 2.0 * math.pi * float(i) / segments
        hx = cx + hole_rad * math.cos(theta)
        hy = cy + hole_rad * math.sin(theta)
        bot_hole.append([hx, hy, 0.0])
        top_hole.append([hx, hy, dz])

    # 4. Inner Hole Cylinder Wall (Inward normals)
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_hole[i], top_hole[ni], bot_hole[ni]])
        tris.append([bot_hole[i], top_hole[i], top_hole[ni]])

    # 5. Top & Bottom Planar Triangulation with Sharp Corners & Open Hole
    # We partition top/bottom faces using 4 sharp corner anchors:
    # Corner 0: (0,0), Corner 1: (dx,0), Corner 2: (dx,dy), Corner 3: (0,dy)
    # Midpoints: M0=(dx/2, 0), M1=(dx, dy/2), M2=(dx/2, dy), M3=(0, dy/2)

    # For Top Face (+Z):
    for i in range(segments):
        ni = (i + 1) % segments
        quad = (i * 4) // segments

        # Anchor to outer box boundary based on circle quadrant
        if quad == 0:   # [0 to pi/2] -> South-East (dx/2,0) -> (dx,0) -> (dx, dy/2)
            o1 = [dx, 0, dz]
            o2 = [dx, dy/2, dz]
        elif quad == 1: # [pi/2 to pi] -> North-East (dx, dy/2) -> (dx, dy) -> (dx/2, dy)
            o1 = [dx, dy, dz]
            o2 = [dx/2, dy, dz]
        elif quad == 2: # [pi to 3pi/2] -> North-West (dx/2, dy) -> (0, dy) -> (0, dy/2)
            o1 = [0, dy, dz]
            o2 = [0, dy/2, dz]
        else:           # [3pi/2 to 2pi] -> South-West (0, dy/2) -> (0, 0) -> (dx/2, 0)
            o1 = [0, 0, dz]
            o2 = [dx/2, 0, dz]

        tris.append([top_hole[i], o1, top_hole[ni]])
        tris.append([top_hole[ni], o1, o2])

    # For Bottom Face (-Z):
    for i in range(segments):
        ni = (i + 1) % segments
        quad = (i * 4) // segments

        if quad == 0:
            o1 = [dx, 0, 0]
            o2 = [dx, dy/2, 0]
        elif quad == 1:
            o1 = [dx, dy, 0]
            o2 = [dx/2, dy, 0]
        elif quad == 2:
            o1 = [0, dy, 0]
            o2 = [0, dy/2, 0]
        else:
            o1 = [0, 0, 0]
            o2 = [dx/2, 0, 0]

        tris.append([bot_hole[i], bot_hole[ni], o1])
        tris.append([bot_hole[ni], o2, o1])

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
    tris = gen_sharp_corners_box_with_hole(100, 50, 25, 10, 32)
    write_stl_ascii('/mnt/c/Users/Sean/Documents/AILangSH/test-stl/01_box_with_hole.stl', tris, "BoxWithHole")
    write_stl_ascii('/home/sean/cli_model.stl', tris, "BoxWithHole")
    print(f"Generated sharp corners box with open hole solid: {len(tris)} Triangles")
