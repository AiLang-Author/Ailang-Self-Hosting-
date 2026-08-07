#!/usr/bin/env bash
# Phase C gates: chamfer (single + multi/general), rotate, cyl-cyl tube
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p test-stl

echo "[phase_c] chamfer single corner"
./ailang.x CAD/demo_chamfer.ailang -o /tmp/dch && /tmp/dch
test -s test-stl/cad_chamfer_edge.stp
# 5-gon prism: 2 caps + 5 sides = 7
test "$(grep -c ADVANCED_FACE test-stl/cad_chamfer_edge.stp)" -eq 7

echo "[phase_c] chamfer multi / general vertical"
./ailang.x CAD/demo_chamfer_multi.ailang -o /tmp/dcm && /tmp/dcm
# 4 corners → 8-gon: 2+8 = 10 faces
test "$(grep -c ADVANCED_FACE test-stl/cad_chamfer_4corners.stp)" -eq 10
# sequential two corners → 6-gon: 2+6 = 8
test "$(grep -c ADVANCED_FACE test-stl/cad_chamfer_seq.stp)" -eq 8
# diamond one corner: 4→5 verts → 7 faces
test "$(grep -c ADVANCED_FACE test-stl/cad_chamfer_diamond.stp)" -eq 7

echo "[phase_c] chamfer horizontal box"
./ailang.x CAD/demo_chamfer_horiz.ailang -o /tmp/dchh && /tmp/dchh
# 5-gon profile extruded: 2+5 = 7 faces each
test "$(grep -c ADVANCED_FACE test-stl/cad_chamfer_horiz.stp)" -eq 7
test "$(grep -c ADVANCED_FACE test-stl/cad_chamfer_horiz_y.stp)" -eq 7
test "$(grep -c ADVANCED_FACE test-stl/cad_chamfer_horiz_bot.stp)" -eq 7

echo "[phase_c] plane-cyl fillet (cyl top rim)"
./ailang.x CAD/demo_fillet_cyl.ailang -o /tmp/dfc && /tmp/dfc
test -s test-stl/cad_fillet_cyl_top.stp
test -s test-stl/cad_fillet_cyl_direct.stp
# lathe: n_rings=8 (2+6), n_ang=24 → caps 2 + sides 7*24 = 2+168 = 170 faces
test "$(grep -c ADVANCED_FACE test-stl/cad_fillet_cyl_direct.stp)" -eq 170

echo "[phase_c] plane-cyl bottom + washer hole rim"
./ailang.x CAD/demo_fillet_cyl_more.ailang -o /tmp/dfcm && /tmp/dfcm
test -s test-stl/cad_fillet_cyl_bot.stp
test -s test-stl/cad_fillet_washer_hole.stp
# washer closed lathe: n_prof=4+6=10, faces = 10*24 = 240
test "$(grep -c ADVANCED_FACE test-stl/cad_fillet_washer_hole.stp)" -eq 240

echo "[phase_c] rotate"
./ailang.x CAD/demo_rotate.ailang -o /tmp/drot && /tmp/drot
test -s test-stl/cad_rotate_z.stp

echo "[phase_c] revolve tube (cyl−cyl bool path)"
./ailang.x CAD/demo_revolve.ailang -o /tmp/drev && /tmp/drev
test -s test-stl/cad_revolve_tube.stp

echo "[phase_c] ALL OK"
