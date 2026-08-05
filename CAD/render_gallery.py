#!/usr/bin/env python3
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def parse_stl_ascii(filename):
    triangles = []
    current_tri = []
    with open(filename, 'r') as f:
        for line in f:
            tokens = line.strip().split()
            if not tokens:
                continue
            if tokens[0] == 'vertex':
                x, y, z = float(tokens[1]), float(tokens[2]), float(tokens[3])
                current_tri.append([x, y, z])
                if len(current_tri) == 3:
                    triangles.append(current_tri)
                    current_tri = []
    return np.array(triangles)

def render_model(stl_filename, out_png_path, title="CAD Model"):
    triangles = parse_stl_ascii(stl_filename)
    fig = plt.figure(figsize=(10, 8), dpi=150)
    ax = fig.add_subplot(111, projection='3d')
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')

    poly3d = Poly3DCollection(triangles, alpha=0.9, edgecolor='#38bdf8', linewidths=0.4)
    poly3d.set_facecolor('#0284c7')
    ax.add_collection3d(poly3d)

    all_pts = triangles.reshape(-1, 3)
    min_pts = all_pts.min(axis=0)
    max_pts = all_pts.max(axis=0)
    max_range = np.array([max_pts[0]-min_pts[0], max_pts[1]-min_pts[1], max_pts[2]-min_pts[2]]).max() / 2.0
    mid_x = (max_pts[0] + min_pts[0]) * 0.5
    mid_y = (max_pts[1] + min_pts[1]) * 0.5
    mid_z = (max_pts[2] + min_pts[2]) * 0.5

    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)

    ax.set_title(f"{title} ({len(triangles)} Triangles)", color='#f8fafc', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('X (mm)', color='#94a3b8')
    ax.set_ylabel('Y (mm)', color='#94a3b8')
    ax.set_zlabel('Z (mm)', color='#94a3b8')
    ax.tick_params(colors='#94a3b8')

    ax.xaxis.pane.set_edgecolor('#334155')
    ax.yaxis.pane.set_edgecolor('#334155')
    ax.zaxis.pane.set_edgecolor('#334155')
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False

    ax.view_init(elev=30, azim=45)
    plt.tight_layout()
    plt.savefig(out_png_path, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Rendered {title} to: {out_png_path}")

if __name__ == '__main__':
    art_dir = '/home/sean/.gemini/antigravity-cli/brain/9cd886f1-8f7e-43de-9ba6-bc3d75b3f426'
    stl_dir = '/mnt/c/Users/Sean/Documents/AILangSH/test-stl'

    models = [
        ('01_box_with_hole.stl', 'render_01_box_hole.png', 'Box with Drilled Hole (Phase 3/6)'),
        ('02_analytic_sphere.stl', 'render_02_sphere.png', 'Analytic Sphere (Phase 1 Geom)'),
        ('03_cylinder_solid.stl', 'render_03_cylinder.png', 'Cylinder Solid (Phase 1 Geom)'),
        ('04_nurbs_surface.stl', 'render_04_nurbs.png', 'NURBS Freeform Surface (Phase 11 BSpline)'),
        ('05_hollow_shell.stl', 'render_05_shell.png', 'Thin-Wall Solid (Phase 12 Offset)')
    ]

    for stl_file, png_file, title in models:
        stl_p = os.path.join(stl_dir, stl_file)
        png_p = os.path.join(art_dir, png_file)
        render_model(stl_p, png_p, title)
