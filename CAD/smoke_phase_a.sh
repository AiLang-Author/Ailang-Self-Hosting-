#!/usr/bin/env bash
# Phase A gates: LWPOLYLINE, multi-loop, ARC, export round-trip, view.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[phase_a] build"
./ailang.x CAD/cad_load.ailang -o cad_load.x
./ailang.x CAD/cad_view.ailang -o cad_view.x

echo "[phase_a] LWPOLYLINE rect"
./cad_load.x -i test-stl/test-dxf-files/lwpoly_rect.dxf -o test-stl/cad_dxf_lwrect.stp -H 15
test "$(grep -c ADVANCED_FACE test-stl/cad_dxf_lwrect.stp)" -eq 6

echo "[phase_a] multi-loop plate+hole (one DXF)"
./cad_load.x -i test-stl/test-dxf-files/lwpoly_plate_hole.dxf -o test-stl/cad_dxf_lwplate.stp -H 4
test "$(grep -c FACE_BOUND test-stl/cad_dxf_lwplate.stp)" -eq 2

echo "[phase_a] ARC slot"
./cad_load.x -i test-stl/test-dxf-files/slot_arc.dxf -o test-stl/cad_dxf_slot.stp -H 8
test "$(grep -c ADVANCED_FACE test-stl/cad_dxf_slot.stp)" -ge 6

echo "[phase_a] view multi-loop"
./cad_view.x -i test-stl/test-dxf-files/lwpoly_plate_hole.dxf \
  -o test-stl/cad_view_lwplate.bmp -H 4 -W 400 --imgh 300 --wire 0
test -s test-stl/cad_view_lwplate.bmp

echo "[phase_a] ALL OK"
