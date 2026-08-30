#!/usr/bin/env bash
# Overnight / CI smoke: DXF → solid → software view BMPs (no FreeCAD, no AOS).
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[smoke_view] build cad_view.x"
./ailang.x CAD/cad_view.ailang -o cad_view.x

OUT=test-stl
mkdir -p "$OUT"

echo "[smoke_view] square"
./cad_view.x --in test-stl/test-dxf-files/square_10.dxf \
  --shot "$OUT/cad_view_square.bmp" -H 10 --width 400 --imgh 300

echo "[smoke_view] keyhole"
./cad_view.x --in test-stl/test-dxf-files/keyhole.dxf \
  --shot "$OUT/cad_view_keyhole.bmp" -H 8 --width 500 --imgh 400

echo "[smoke_view] diamond (pipe)"
cat test-stl/test-dxf-files/diamond_2d.dxf | ./cad_view.x \
  --shot "$OUT/cad_view_diamond.bmp" -H 25 --width 400 --imgh 300

echo "[smoke_view] escutcheon plate+hole"
./cad_view.x --in test-stl/test-dxf-files/escutcheon_plate.dxf \
  --hole test-stl/test-dxf-files/keyhole_flared.dxf \
  --shot "$OUT/cad_view_escutcheon.bmp" -H 4 --width 600 --imgh 500 --wire 0

echo "[smoke_view] ARC slot"
./cad_view.x --in test-stl/test-dxf-files/slot_arc.dxf \
  --shot "$OUT/cad_view_slot.bmp" -H 8 --width 500 --imgh 350 --wire 0

echo "[smoke_view] keyhole top preset"
./cad_view.x --in test-stl/test-dxf-files/keyhole.dxf \
  --shot "$OUT/cad_view_kh_top.bmp" -H 8 --width 400 --imgh 300 --view 1 --wire 0

for f in square keyhole diamond escutcheon slot kh_top; do
  p="$OUT/cad_view_${f}.bmp"
  sz=$(wc -c <"$p")
  if [[ "$sz" -lt 1000 ]]; then
    echo "FAIL: $p too small ($sz)"
    exit 1
  fi
  magic=$(head -c 2 "$p")
  if [[ "$magic" != "BM" ]]; then
    echo "FAIL: $p not BMP"
    exit 1
  fi
  echo "  OK $p ($sz bytes)"
done

echo "[smoke_view] ALL OK"
