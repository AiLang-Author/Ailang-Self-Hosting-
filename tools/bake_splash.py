#!/usr/bin/env python3
# bake_splash.py — convert an MP4 to a .bgra frame blob for ANSICanvas.
#
# Usage:
#   python3 bake_splash.py <input.mp4> <output.bgra> [options]
#
# Options:
#   --width  W    target pixel width  (default: 80, = 80 terminal columns)
#   --height H    target pixel height (default: 48, = 24 terminal rows at half-block)
#   --fps    N    output frame rate   (default: 12)
#   --reverse     reverse frame order (for videos that were generated backwards)
#   --trim   T    only take the first T seconds of the video
#
# Blob format (.bgra):
#   [0..3]   magic "BGRV"
#   [4]      version = 1
#   [5..6]   width  (uint16 LE)
#   [7..8]   height (uint16 LE)
#   [9]      fps    (uint8)
#   [10..13] frame_count (uint32 LE)
#   [14..15] reserved (0x00 0x00)
#   [16..]   frame_count * width * height * 4 bytes of raw BGRA
#
# Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

import sys
import os
import struct
import subprocess
import argparse


def bake(input_mp4, output_bgra, width=80, height=48, fps=24, reverse=False, trim=None):
    vf_parts = []
    if reverse:
        # Reverse before any filtering so temporal denoise runs in correct output direction.
        vf_parts.append("reverse")
    # Temporal + spatial denoise before downscale — kills frame-to-frame flicker ("static").
    # hqdn3d luma_spatial:chroma_spatial:luma_temporal:chroma_temporal
    vf_parts.append("hqdn3d=luma_spatial=6:chroma_spatial=6:luma_tmp=5:chroma_tmp=5")
    # Scale to fit within width×height preserving aspect ratio, then pad with black.
    vf_parts.append(
        f"scale={width}:{height}:flags=lanczos:force_original_aspect_ratio=decrease"
    )
    vf_parts.append(
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    )
    # Boost contrast + saturation so half-block colors read as distinct shapes instead of mud.
    vf_parts.append("eq=contrast=1.3:saturation=1.6:brightness=0.05")
    vf_parts.append("format=bgra")

    vf = ",".join(vf_parts)

    cmd = ["ffmpeg", "-y"]
    if trim:
        cmd += ["-t", str(trim)]
    cmd += [
        "-i", input_mp4,
        "-vf", vf,
        "-r", str(fps),
        "-f", "rawvideo",
        "-pix_fmt", "bgra",
        "pipe:1"
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print("ffmpeg error:", result.stderr.decode(errors="replace")[-500:])
        sys.exit(1)

    raw = result.stdout
    frame_size = width * height * 4
    frame_count = len(raw) // frame_size
    if frame_count == 0:
        print("ERROR: no frames extracted")
        sys.exit(1)

    # Trim any partial trailing frame
    raw = raw[:frame_count * frame_size]

    with open(output_bgra, "wb") as f:
        f.write(b"BGRV")                          # magic
        f.write(bytes([1]))                        # version
        f.write(struct.pack("<H", width))          # width
        f.write(struct.pack("<H", height))         # height
        f.write(bytes([fps]))                      # fps
        f.write(struct.pack("<I", frame_count))    # frame_count
        f.write(bytes([0, 0]))                     # reserved
        f.write(raw)

    out_size = os.path.getsize(output_bgra)
    print(f"OK: {frame_count} frames  {width}x{height}  @{fps}fps  ->  {output_bgra}")
    print(f"    Blob size: {out_size/1024:.0f} KB  ({out_size/1024/1024:.2f} MB)")


def main():
    ap = argparse.ArgumentParser(description="Bake MP4 to BGRA blob for ANSICanvas")
    ap.add_argument("input",          help="Input MP4 file")
    ap.add_argument("output",         help="Output .bgra blob file")
    ap.add_argument("--width",  type=int,   default=80,   help="Pixel width  (default 80)")
    ap.add_argument("--height", type=int,   default=48,   help="Pixel height (default 48 = 24 rows)")
    ap.add_argument("--fps",    type=int,   default=24,   help="Output fps   (default 24)")
    ap.add_argument("--reverse",            action="store_true", help="Reverse frame order")
    ap.add_argument("--trim",   type=float, default=None, help="Only take first N seconds")
    args = ap.parse_args()

    if args.height % 2 != 0:
        print("ERROR: height must be even (half-block encoding pairs rows)")
        sys.exit(1)

    bake(args.input, args.output,
         width=args.width, height=args.height,
         fps=args.fps, reverse=args.reverse, trim=args.trim)


if __name__ == "__main__":
    main()
