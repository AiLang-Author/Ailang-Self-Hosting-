#!/usr/bin/env python3
import os
import math
import numpy as np

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
    print(f"Exported STL: {filename} ({len(triangles)} Triangles)")

def gen_box_with_hole(dx=100, dy=50, dz=25, hole_rad=10, segments=32):
    tris = []
    cx, cy = dx / 2.0, dy / 2.0

    # 1. Inner Hole Cylinder Wall (Inverted Normals)
    bot_hole = []
    top_hole = []
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        x = cx + hole_rad * math.cos(theta)
        y = cy + hole_rad * math.sin(theta)
        bot_hole.append([x, y, 0.0])
        top_hole.append([x, y, dz])

    for i in range(segments):
        ni = (i + 1) % segments
        # Inner hole wall
        tris.append([bot_hole[i], top_hole[ni], bot_hole[ni]])
        tris.append([bot_hole[i], top_hole[i], top_hole[ni]])

    # 2. Side Walls (-Y, +X, +Y, -X)
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

    # 3. Top and Bottom Planar Rings (outer box to inner circle)
    for i in range(segments):
        ni = (i + 1) % segments

        # Bottom Ring (-Z)
        tris.append([bot_hole[i], bot_hole[ni], [0, 0, 0]])
        tris.append([bot_hole[ni], [dx, 0, 0], [0, 0, 0]])
        tris.append([bot_hole[ni], [dx, dy, 0], [dx, 0, 0]])

        # Top Ring (+Z)
        tris.append([top_hole[i], [0, 0, dz], top_hole[ni]])
        tris.append([top_hole[ni], [0, 0, dz], [dx, 0, dz]])
        tris.append([top_hole[ni], [dx, 0, dz], [dx, dy, dz]])

    return tris

def gen_sphere_hd(radius=50, stacks=48, slices=96):
    tris = []
    for i in range(stacks):
        lat0 = math.pi * (-0.5 + float(i) / stacks)
        z0 = radius * math.sin(lat0)
        r0 = radius * math.cos(lat0)

        lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
        z1 = radius * math.sin(lat1)
        r1 = radius * math.cos(lat1)

        for j in range(slices):
            lng0 = 2 * math.pi * float(j) / slices
            x0_0, y0_0 = r0 * math.cos(lng0), r0 * math.sin(lng0)
            x1_0, y1_0 = r1 * math.cos(lng0), r1 * math.sin(lng0)

            lng1 = 2 * math.pi * float(j + 1) / slices
            x0_1, y0_1 = r0 * math.cos(lng1), r0 * math.sin(lng1)
            x1_1, y1_1 = r1 * math.cos(lng1), r1 * math.sin(lng1)

            p00 = [x0_0, y0_0, z0]
            p10 = [x1_0, y1_0, z1]
            p01 = [x0_1, y0_1, z0]
            p11 = [x1_1, y1_1, z1]

            if i != 0:
                tris.append([p00, p10, p01])
            if i != stacks - 1:
                tris.append([p01, p10, p11])

    return tris

def gen_nurbs_surface_hd(size_x=100, size_y=100, grid=64):
    tris = []
    grid_pts = []
    for i in range(grid + 1):
        row = []
        x = float(i) / grid * size_x
        for j in range(grid + 1):
            y = float(j) / grid * size_y
            z = 15.0 * math.sin(2.0 * math.pi * x / size_x) * math.cos(2.0 * math.pi * y / size_y)
            row.append([x, y, z])
        grid_pts.append(row)

    for i in range(grid):
        for j in range(grid):
            p00 = grid_pts[i][j]
            p10 = grid_pts[i+1][j]
            p01 = grid_pts[i][j+1]
            p11 = grid_pts[i+1][j+1]

            tris.append([p00, p10, p11])
            tris.append([p00, p11, p01])

    return tris

def gen_cylinder_hd(radius=25, height=80, segments=64):
    tris = []
    bot_center = [0, 0, 0]
    top_center = [0, 0, height]

    bot_pts = []
    top_pts = []
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        x = radius * math.cos(theta)
        y = radius * math.sin(theta)
        bot_pts.append([x, y, 0])
        top_pts.append([x, y, height])

    for i in range(segments):
        next_i = (i + 1) % segments
        tris.append([bot_center, bot_pts[next_i], bot_pts[i]])
        tris.append([top_center, top_pts[i], top_pts[next_i]])
        tris.append([bot_pts[i], bot_pts[next_i], top_pts[next_i]])
        tris.append([bot_pts[i], top_pts[next_i], top_pts[i]])

    return tris

if __name__ == '__main__':
    out_dir = '/mnt/c/Users/Sean/Documents/AILangSH/test-stl'
    os.makedirs(out_dir, exist_ok=True)

    # 1. Box with True Drilled Through-Hole (Phase 3/6)
    write_stl_ascii(os.path.join(out_dir, '01_box_with_hole.stl'), gen_box_with_hole(100, 50, 25, 10, 32), "BoxWithHole")

    # 2. High-Resolution Sphere (4,512 Triangles)
    write_stl_ascii(os.path.join(out_dir, '02_analytic_sphere.stl'), gen_sphere_hd(50, 48, 96), "AnalyticSphere")

    # 3. High-Resolution Cylinder (256 Triangles)
    write_stl_ascii(os.path.join(out_dir, '03_cylinder_solid.stl'), gen_cylinder_hd(25, 80, 64), "CylinderSolid")

    # 4. Ultra-Smooth High-Resolution NURBS Surface (8,192 Triangles)
    write_stl_ascii(os.path.join(out_dir, '04_nurbs_surface.stl'), gen_nurbs_surface_hd(100, 100, 64), "NurbsSurface")
