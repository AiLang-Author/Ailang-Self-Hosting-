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

def gen_watertight_sharp_hole_solid(dx, dy, dz, hole_rad, segments=32):
    tris = []
    cx, cy = dx / 2.0, dy / 2.0
    half_s = segments // 4
    eighth_s = segments // 8

    bot_hole, top_hole = [], []
    for i in range(segments):
        theta = 2.0 * math.pi * float(i) / segments
        hx = cx + hole_rad * math.cos(theta)
        hy = cy + hole_rad * math.sin(theta)
        bot_hole.append([hx, hy, 0.0])
        top_hole.append([hx, hy, dz])

    # Inner Hole Cylinder Wall
    for i in range(segments):
        ni = (i + 1) % segments
        tris.append([bot_hole[i], top_hole[ni], bot_hole[ni]])
        tris.append([bot_hole[i], top_hole[i], top_hole[ni]])

    # 4 Sharp Corners + 4 Mid-edges
    C0_b, C1_b, C2_b, C3_b = [0,0,0], [dx,0,0], [dx,dy,0], [0,dy,0]
    M0_b, M1_b, M2_b, M3_b = [dx/2,0,0], [dx,dy/2,0], [dx/2,dy,0], [0,dy/2,0]

    C0_t, C1_t, C2_t, C3_t = [0,0,dz], [dx,0,dz], [dx,dy,dz], [0,dy,dz]
    M0_t, M1_t, M2_t, M3_t = [dx/2,0,dz], [dx,dy/2,dz], [dx/2,dy,dz], [0,dy/2,dz]

    # Outer 4 Side Walls (16 Triangles)
    tris.append([C0_b, M0_b, M0_t]); tris.append([C0_b, M0_t, C0_t])
    tris.append([M0_b, C1_b, C1_t]); tris.append([M0_b, C1_t, M0_t])
    tris.append([C1_b, M1_b, M1_t]); tris.append([C1_b, M1_t, C1_t])
    tris.append([M1_b, C2_b, C2_t]); tris.append([M1_b, C2_t, M1_t])
    tris.append([C2_b, M2_b, M2_t]); tris.append([C2_b, M2_t, C2_t])
    tris.append([M2_b, C3_b, C3_t]); tris.append([M2_b, C3_t, M2_t])
    tris.append([C3_b, M3_b, M3_t]); tris.append([C3_b, M3_t, C3_t])
    tris.append([M3_b, C0_b, C0_t]); tris.append([M3_b, C0_t, M3_t])

    # Top (+Z) & Bottom (-Z) Annulus (Zero Overlap Fan)
    for i in range(segments):
        ni = (i + 1) % segments
        q = i // half_s
        local_i = i % half_s

        if q == 0:
            P_start_t, P_corner_t, P_end_t = M0_t, C1_t, M1_t
            P_start_b, P_corner_b, P_end_b = M0_b, C1_b, M1_b
        elif q == 1:
            P_start_t, P_corner_t, P_end_t = M1_t, C2_t, M2_t
            P_start_b, P_corner_b, P_end_b = M1_b, C2_b, M2_b
        elif q == 2:
            P_start_t, P_corner_t, P_end_t = M2_t, C3_t, M3_t
            P_start_b, P_corner_b, P_end_b = M2_b, C3_b, M3_b
        else:
            P_start_t, P_corner_t, P_end_t = M3_t, C0_t, M0_t
            P_start_b, P_corner_b, P_end_b = M3_b, C0_b, M0_b

        # Top Face (+Z)
        if local_i < eighth_s:
            tris.append([top_hole[i], P_start_t, top_hole[ni]])
            if local_i == eighth_s - 1:
                tris.append([top_hole[ni], P_start_t, P_corner_t])
        else:
            tris.append([top_hole[i], P_corner_t, top_hole[ni]])
            if local_i == half_s - 1:
                tris.append([top_hole[ni], P_corner_t, P_end_t])

        # Bottom Face (-Z)
        if local_i < eighth_s:
            tris.append([bot_hole[i], bot_hole[ni], P_start_b])
            if local_i == eighth_s - 1:
                tris.append([bot_hole[ni], P_corner_b, P_start_b])
        else:
            tris.append([bot_hole[i], bot_hole[ni], P_corner_b])
            if local_i == half_s - 1:
                tris.append([bot_hole[ni], P_end_b, P_corner_b])

    return tris

def gen_path1_sketch_extrude():
    return gen_watertight_sharp_hole_solid(100, 50, 25, 10, 32)

def gen_path2_csg_drill_hole():
    return gen_watertight_sharp_hole_solid(120, 60, 30, 12, 32)

def gen_path3_subtractive_pocket(dx=100, dy=50, dz=25, pw=60, ph=30, pd=15):
    tris = []
    px0, py0 = (dx - pw) / 2.0, (dy - ph) / 2.0
    px1, py1 = px0 + pw, py0 + ph
    pz_floor = dz - pd

    p = np.array([
        [0,0,0], [dx,0,0], [dx,dy,0], [0,dy,0],
        [0,0,dz], [dx,0,dz], [dx,dy,dz], [0,dy,dz],
        [px0, py0, pz_floor], [px1, py0, pz_floor], [px1, py1, pz_floor], [px0, py1, pz_floor],
        [px0, py0, dz], [px1, py0, dz], [px1, py1, dz], [px0, py1, dz]
    ])

    tris.append([p[0], p[2], p[1]]); tris.append([p[0], p[3], p[2]])
    tris.append([p[0], p[1], p[5]]); tris.append([p[0], p[5], p[4]])
    tris.append([p[1], p[2], p[6]]); tris.append([p[1], p[6], p[5]])
    tris.append([p[2], p[3], p[7]]); tris.append([p[2], p[7], p[6]])
    tris.append([p[3], p[0], p[4]]); tris.append([p[3], p[4], p[7]])

    tris.append([p[8], p[9], p[10]]); tris.append([p[8], p[10], p[11]])
    tris.append([p[8], p[12], p[13]]); tris.append([p[8], p[13], p[9]])
    tris.append([p[9], p[13], p[14]]); tris.append([p[9], p[14], p[10]])
    tris.append([p[10], p[14], p[15]]); tris.append([p[10], p[15], p[11]])
    tris.append([p[11], p[15], p[12]]); tris.append([p[11], p[12], p[8]])

    tris.append([p[4], p[5], p[13]]); tris.append([p[4], p[13], p[12]])
    tris.append([p[5], p[6], p[14]]); tris.append([p[5], p[14], p[13]])
    tris.append([p[6], p[7], p[15]]); tris.append([p[6], p[15], p[14]])
    tris.append([p[7], p[4], p[12]]); tris.append([p[7], p[12], p[15]])

    return tris

if __name__ == '__main__':
    out_dirs = ['/mnt/c/Users/Sean/Documents/AILangSH/test-stl', '/home/sean']

    t1 = gen_path1_sketch_extrude()
    t2 = gen_path2_csg_drill_hole()
    t3 = gen_path3_subtractive_pocket()

    for d in out_dirs:
        write_stl_ascii(os.path.join(d, 'path1_extrude_sketch.stl'), t1, "Path1_SketchExtrude")
        write_stl_ascii(os.path.join(d, 'path2_csg_drill_hole.stl'), t2, "Path2_CSGDrillHole")
        write_stl_ascii(os.path.join(d, 'path3_subtractive_pocket.stl'), t3, "Path3_SubtractivePocket")
