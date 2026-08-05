#!/usr/bin/env python3
"""
render_wallpaper.py — Render wallpaper SVG to PPM/PNG/TVG at any size.

Uses the native svg_test.x harness (SVG → BGRA surface → PPM RGB), then
converts to PNG for SysDisplay wallpaper loading. Also emits TVG for vector
pipeline reuse.

Usage:
    python3 tools/render_wallpaper.py
    python3 tools/render_wallpaper.py --size 128
    python3 tools/render_wallpaper.py --width 1920 --height 1080
    python3 tools/render_wallpaper.py --svg Media/wallpapers/workbench-grid.svg

Copyright © 2026 Sean Collins / AILANG project.
"""

from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SVG = os.path.join(ROOT, "Media", "wallpapers", "workbench-grid.svg")
SVG_TEST = os.path.join(ROOT, "svg_test.x")
SVG2TVG = os.path.join(ROOT, "tools", "svg2tvg.py")
OUT_DIR = os.path.join(ROOT, "Media", "wallpapers")


def read_ppm(path: str) -> tuple[int, int, bytes]:
    with open(path, "rb") as f:
        magic = f.readline()
        if magic.strip() != b"P6":
            raise ValueError(f"Expected P6 PPM, got {magic!r}")
        # skip comments
        line = f.readline()
        while line.startswith(b"#"):
            line = f.readline()
        dims = line.decode().strip().split()
        w, h = int(dims[0]), int(dims[1])
        maxval = int(f.readline().decode().strip())
        if maxval != 255:
            raise ValueError(f"Unsupported maxval {maxval}")
        data = f.read(w * h * 3)
        if len(data) != w * h * 3:
            raise ValueError("Truncated PPM pixel data")
        return w, h, data


def ppm_to_png(ppm_path: str, png_path: str) -> None:
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("PIL/Pillow required: pip install pillow") from None
    w, h, rgb = read_ppm(ppm_path)
    img = Image.frombytes("RGB", (w, h), rgb)
    img.save(png_path, "PNG")
    print(f"[render_wallpaper] {ppm_path} -> {png_path} ({w}x{h})")


def ppm_to_rgba(ppm_path: str, rgba_path: str) -> None:
    w, h, rgb = read_ppm(ppm_path)
    out = bytearray(w * h * 4)
    i = 0
    o = 0
    while i < len(rgb):
        out[o] = rgb[i]
        out[o + 1] = rgb[i + 1]
        out[o + 2] = rgb[i + 2]
        out[o + 3] = 255
        i += 3
        o += 4
    with open(rgba_path, "wb") as f:
        f.write(out)
    print(f"[render_wallpaper] {ppm_path} -> {rgba_path} ({w}x{h} RGBA)")


def render_svg(svg_path: str, ppm_path: str, width: int, height: int) -> None:
    if not os.path.isfile(SVG_TEST):
        raise SystemExit(
            f"svg_test.x not found at {SVG_TEST}\n"
            "Build: ./ailang.x TestCode/svg_test.ailang svg_test.x"
        )
    cmd = [SVG_TEST, svg_path, ppm_path, str(width), str(height)]
    print(f"[render_wallpaper] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        raise SystemExit(f"svg_test.x failed (exit {result.returncode})")
    if not os.path.isfile(ppm_path):
        raise SystemExit(f"PPM not created: {ppm_path}")


def convert_tvg(svg_path: str, tvg_path: str) -> None:
    cmd = [sys.executable, SVG2TVG, svg_path, tvg_path]
    print(f"[render_wallpaper] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render wallpaper SVG to PNG/TVG")
    parser.add_argument("--svg", default=DEFAULT_SVG, help="Input SVG path")
    parser.add_argument("--size", type=int, default=128,
                        help="Square tile size (default 128, for seamless tiling)")
    parser.add_argument("--width", type=int, help="Output width (overrides --size)")
    parser.add_argument("--height", type=int, help="Output height (overrides --size)")
    parser.add_argument("--name", default="workbench-grid",
                        help="Output basename (without extension)")
    parser.add_argument("--out-dir", default=OUT_DIR, help="Output directory")
    args = parser.parse_args()

    svg_path = os.path.abspath(args.svg)
    if not os.path.isfile(svg_path):
        raise SystemExit(f"SVG not found: {svg_path}")

    w = args.width if args.width else args.size
    h = args.height if args.height else args.size

    os.makedirs(args.out_dir, exist_ok=True)
    base = os.path.join(args.out_dir, args.name)
    ppm_path = base + ".ppm"
    png_path = base + ".png"
    rgba_path = base + ".rgba"
    tvg_path = base + ".tvg"

    render_svg(svg_path, ppm_path, w, h)
    ppm_to_png(ppm_path, png_path)
    ppm_to_rgba(ppm_path, rgba_path)
    convert_tvg(svg_path, tvg_path)

    # Convenience symlink-style copy for tile naming
    if w == h == 128:
        tile_png = os.path.join(args.out_dir, args.name + "-tile.png")
        if tile_png != png_path:
            with open(png_path, "rb") as src, open(tile_png, "wb") as dst:
                dst.write(src.read())
            print(f"[render_wallpaper] tile copy -> {tile_png}")

    try:
        os.remove(ppm_path)
    except OSError:
        pass

    print(f"[render_wallpaper] done: {png_path}, {tvg_path}, {rgba_path}")
    print(f"[render_wallpaper] re-render at new scale: "
          f"python3 tools/render_wallpaper.py --width W --height H")


if __name__ == "__main__":
    main()