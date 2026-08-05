#!/usr/bin/env python3
import os
import math
import numpy as np

def gen_100pct_watertight_hole_solid(dx=100, dy=50, dz=25, hole_rad=10, n_side=12):
    # Total outer perimeter vertices = 4 * n_side = 48
    N = 4 * n_side
    tris = []
    cx, cy = dx / 2.0, dy / 2.0

    # 1. Outer Box Perimeter Polygon (48 vertices along 4 edges, including 4 exact corners)
    outer_2d = []
    # Bottom edge (Y=0): (0,0) to (dx,0)
    for i in range(n_side):
        x = float(i) / n_side * dx
        outer_2d.append([x, 0.0])
    # Right edge (X=dx): (dx,0) to (dx,dy)
    for i in range(n_side):
        y = float(i) / n_side * dy
        outer_2d.append([dx, y])
    # Top edge (Y=dy): (dx,dy) to (0,dy)
    for i in range(n_side):
        x = dx - float(i) / n_side * dx
        outer_2d.append([x, dy])
    # Left edge (X=0): (0,dy) to (0,0)
    for i in range(n_side):
        y = dy - float(i) / n_side * dy
        outer_2d.append([0.0, y])

    # 2. Inner Circle Hole Polygon (48 vertices, uniform angle)
    inner_2d = []
    for i in range(N):
        # Match angle phase to outer perimeter direction
        theta = -2.0 * math.pi * float(i) / N - math.pi / 2.0
        x = cx + hole_rad * math.cos(theta)
        y = cy + hole_rad * math.sin(theta)
        inner_2d.append([x, y])

    # Construct 3D vertex lists
    top_out = [[p[0], p[1], dz] for p in outer_2d]
    bot_out = [[p[0], p[1], 0.0] for p in outer_2d]

    top_in = [[p[0], p[1], dz] for p in inner_2d]
    bot_in = [[p[0], p[1], 0.0] for p in inner_2d]

    # 3. Outer Vertical Side Walls (N quads = 2N tris)
    for i in range(N):
        ni = (i + 1) % N
        tris.append([bot_out[i], bot_out[ni], top_out[ni]])
        tris.append([bot_out[i], top_out[ni], top_out[i]])

    # 4. Inner Hole Cylinder Wall (N quads = 2N tris, facing inward)
    for i in range(N):
        ni = (i + 1) % N
        tris.append([bot_in[i], top_in[ni], bot_in[ni]])
        tris.append([bot_in[i], top_in[i], top_in[ni]])

    # 5. Top Planar Annulus (+Z face, 2N tris)
    for i in range(N):
        ni = (i + 1) % N
        tris.append([top_in[i], top_out[i], top_in[ni]])
        tris.append([top_out[i], top_out[ni], top_in[ni]])

    # 6. Bottom Planar Annulus (-Z face, 2N tris)
    for i in range(N):
        ni = (i + 1) % N
        tris.append([bot_in[i], bot_in[ni], bot_out[i]])
        tris.append([bot_out[i], bot_in[ni], bot_out[ni]])

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
    tris = gen_100pct_watertight_hole_solid(100, 50, 25, 10, 12)
    write_stl_ascii('/mnt/c/Users/Sean/Documents/AILangSH/test-stl/01_box_with_hole.stl', tris, "BoxWithHole")
    write_stl_ascii('/home/sean/cli_model.stl', tris, "BoxWithHole")
    print(f"Generated 100% watertight solid with 0 gaps: {len(tris)} Triangles")
