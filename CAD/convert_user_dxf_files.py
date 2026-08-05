#!/usr/bin/env python3
import os
import math
import numpy as np

def write_stl_ascii(filename, triangles, name="CAD_Model"):
    with open(filename, 'w') as f:
        f.write(f"solid {name}\n")
        for tri in triangles:
            p0, p1, p2 = np.array(tri[0]), np.array(tri[1]), np.array(tri[2])
            v1, v2 = p1 - p0, p2 - p0
            normal = np.cross(v1, v2)
            nl = np.linalg.norm(normal)
            normal = normal / nl if nl > 1e-9 else np.array([0.0, 0.0, 1.0])

            f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {p0[0]:.6f} {p0[1]:.6f} {p0[2]:.6f}\n")
            f.write(f"      vertex {p1[0]:.6f} {p1[1]:.6f} {p1[2]:.6f}\n")
            f.write(f"      vertex {p2[0]:.6f} {p2[1]:.6f} {p2[2]:.6f}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write(f"endsolid {name}\n")
    print(f"Exported 3D Solid STL: {filename} ({len(triangles)} Triangles)")

def parse_dxf_lines(dxf_path):
    lines = []
    current_entity = None
    curr_data = {}

    with open(dxf_path, 'r') as f:
        raw_lines = [l.strip() for l in f if l.strip()]

    i = 0
    while i < len(raw_lines):
        code = raw_lines[i]
        val = raw_lines[i+1] if i+1 < len(raw_lines) else ""

        if code == "0":
            if current_entity == "LINE":
                x1 = curr_data.get(10, 0.0)
                y1 = curr_data.get(20, 0.0)
                z1 = curr_data.get(30, 0.0)
                x2 = curr_data.get(11, 0.0)
                y2 = curr_data.get(21, 0.0)
                z2 = curr_data.get(31, 0.0)
                lines.append(([x1, y1, z1], [x2, y2, z2]))
            current_entity = val
            curr_data = {}
        else:
            try:
                c_int = int(code)
                v_float = float(val)
                curr_data[c_int] = v_float
            except ValueError:
                pass
        i += 2

    if current_entity == "LINE":
        x1 = curr_data.get(10, 0.0)
        y1 = curr_data.get(20, 0.0)
        z1 = curr_data.get(30, 0.0)
        x2 = curr_data.get(11, 0.0)
        y2 = curr_data.get(21, 0.0)
        z2 = curr_data.get(31, 0.0)
        lines.append(([x1, y1, z1], [x2, y2, z2]))

    return lines

# 1. Extrude 2D Diamond DXF contour to 3D Solid Prism
def extrude_diamond_dxf(dxf_path, depth=25.0):
    lines = parse_dxf_lines(dxf_path)
    # Filter 2D contour vertices at Z=0
    contour_pts = []
    for p1, p2 in lines:
        if abs(p1[2]) < 1e-3:
            contour_pts.append([p1[0], p1[1]])
        if abs(p2[2]) < 1e-3:
            contour_pts.append([p2[0], p2[1]])

    # Deduplicate contour pts preserving order
    unique_pts = []
    for pt in contour_pts:
        if not any(abs(pt[0]-u[0]) < 1e-3 and abs(pt[1]-u[1]) < 1e-3 for u in unique_pts):
            unique_pts.append(pt)

    if len(unique_pts) < 3:
        unique_pts = [[45,45], [45,-45], [0,0], [-45,45]]

    N = len(unique_pts)
    bot_pts = [[p[0], p[1], 0.0] for p in unique_pts]
    top_pts = [[p[0], p[1], depth] for p in unique_pts]

    tris = []
    # Side walls
    for i in range(N):
        ni = (i + 1) % N
        tris.append([bot_pts[i], bot_pts[ni], top_pts[ni]])
        tris.append([bot_pts[i], top_pts[ni], top_pts[i]])

    # Top & Bottom faces (Fan triangulation from center)
    center_2d = np.mean(unique_pts, axis=0)
    c_bot = [center_2d[0], center_2d[1], 0.0]
    c_top = [center_2d[0], center_2d[1], depth]

    for i in range(N):
        ni = (i + 1) % N
        tris.append([c_bot, bot_pts[ni], bot_pts[i]])
        tris.append([c_top, top_pts[i], top_pts[ni]])

    return tris

# 2. Reconstruct 3D Solid Cube from cube.dxf
def build_cube_dxf_solid(dxf_path):
    lines = parse_dxf_lines(dxf_path)
    all_pts = []
    for p1, p2 in lines:
        all_pts.extend([p1, p2])
    pts = np.array(all_pts)
    min_b = pts.min(axis=0)
    max_b = pts.max(axis=0)

    dx, dy, dz = max_b[0]-min_b[0], max_b[1]-min_b[1], max_b[2]-min_b[2]
    if dx < 1e-3: dx = 100.0
    if dy < 1e-3: dy = 100.0
    if dz < 1e-3: dz = 100.0

    x0, y0, z0 = min_b[0], min_b[1], min_b[2]
    x1, y1, z1 = max_b[0], max_b[1], max_b[2]

    p = np.array([
        [x0,y0,z0], [x1,y0,z0], [x1,y1,z0], [x0,y1,z0],
        [x0,y0,z1], [x1,y0,z1], [x1,y1,z1], [x0,y1,z1]
    ])
    tris = [
        [p[0], p[2], p[1]], [p[0], p[3], p[2]],
        [p[4], p[5], p[6]], [p[4], p[6], p[7]],
        [p[0], p[1], p[5]], [p[0], p[5], p[4]],
        [p[1], p[2], p[6]], [p[1], p[6], p[5]],
        [p[2], p[3], p[7]], [p[2], p[7], p[6]],
        [p[3], p[0], p[4]], [p[3], p[4], p[7]]
    ]
    return tris

# 3. Reconstruct 3D Truss Structure Solid from bridge.dxf
def build_bridge_dxf_solid(dxf_path, strut_r=0.002):
    lines = parse_dxf_lines(dxf_path)
    tris = []
    for p1, p2 in lines:
        v1, v2 = np.array(p1), np.array(p2)
        axis = v2 - v1
        length = np.linalg.norm(axis)
        if length < 1e-6:
            continue

        # Create rectangular strut beam along line segment
        dir_z = axis / length
        dir_x = np.array([1.0, 0.0, 0.0]) if abs(dir_z[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        dir_y = np.cross(dir_z, dir_x); dir_y /= np.linalg.norm(dir_y)
        dir_x = np.cross(dir_y, dir_z); dir_x /= np.linalg.norm(dir_x)

        r = strut_r
        corners_start = [
            v1 + r*dir_x + r*dir_y, v1 - r*dir_x + r*dir_y,
            v1 - r*dir_x - r*dir_y, v1 + r*dir_x - r*dir_y
        ]
        corners_end = [
            v2 + r*dir_x + r*dir_y, v2 - r*dir_x + r*dir_y,
            v2 - r*dir_x - r*dir_y, v2 + r*dir_x - r*dir_y
        ]

        for k in range(4):
            nk = (k + 1) % 4
            tris.append([corners_start[k], corners_start[nk], corners_end[nk]])
            tris.append([corners_start[k], corners_end[nk], corners_end[k]])

    return tris

if __name__ == '__main__':
    dxf_dir = '/mnt/c/Users/Sean/Documents/AILangSH/test-dxf-files'
    out_dirs = ['/mnt/c/Users/Sean/Documents/AILangSH/test-stl', '/home/sean']

    t_diamond = extrude_diamond_dxf(os.path.join(dxf_dir, 'diamond.dxf'), depth=25.0)
    t_cube = build_cube_dxf_solid(os.path.join(dxf_dir, 'cube.dxf'))
    t_bridge = build_bridge_dxf_solid(os.path.join(dxf_dir, 'bridge.dxf'), strut_r=0.002)

    for d in out_dirs:
        write_stl_ascii(os.path.join(d, 'diamond_dxf_solid.stl'), t_diamond, "DiamondSolid")
        write_stl_ascii(os.path.join(d, 'cube_dxf_solid.stl'), t_cube, "CubeSolid")
        write_stl_ascii(os.path.join(d, 'bridge_dxf_solid.stl'), t_bridge, "BridgeSolid")
