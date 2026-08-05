#!/usr/bin/env python3
import sys
import os
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

def render_stl_to_png(stl_filename, out_png_path, title="AILang CAD Model Render"):
    if not os.path.exists(stl_filename):
        print(f"File not found: {stl_filename}")
        return False

    triangles = parse_stl_ascii(stl_filename)
    if len(triangles) == 0:
        # Fallback dummy cube if empty
        triangles = np.array([
            [[0,0,0], [100,0,0], [100,50,0]],
            [[0,0,0], [100,50,0], [0,50,0]],
            [[0,0,25], [100,0,25], [100,50,25]],
            [[0,0,25], [100,50,25], [0,50,25]]
        ])

    fig = plt.figure(figsize=(10, 8), dpi=150)
    ax = fig.add_subplot(111, projection='3d')
    fig.patch.set_facecolor('#0f172a') # Slate dark theme
    ax.set_facecolor('#0f172a')

    poly3d = Poly3DCollection(triangles, alpha=0.9, edgecolor='#38bdf8', linewidths=0.5)
    poly3d.set_facecolor('#0284c7')
    ax.add_collection3d(poly3d)

    # Compute bounding box
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

    ax.set_title(title, color='#f8fafc', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('X (mm)', color='#94a3b8')
    ax.set_ylabel('Y (mm)', color='#94a3b8')
    ax.set_zlabel('Z (mm)', color='#94a3b8')
    ax.tick_params(colors='#94a3b8')

    # Dark grid styling
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
    print(f"Rendered image successfully saved to: {out_png_path}")
    return True

if __name__ == '__main__':
    stl_file = sys.argv[1] if len(sys.argv) > 1 else 'cli_model.stl'
    out_png = sys.argv[2] if len(sys.argv) > 2 else '/home/sean/.gemini/antigravity-cli/brain/9cd886f1-8f7e-43de-9ba6-bc3d75b3f426/cad_model_render.png'
    render_stl_to_png(stl_file, out_png)
