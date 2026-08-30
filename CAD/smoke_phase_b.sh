#!/usr/bin/env bash
# Phase B gates: ExtrudeCut (rect/circle/poly) + Revolve pad/cut
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[phase_b] extrude cut rect"
./ailang.x CAD/demo_extrude_cut.ailang -o /tmp/dec && /tmp/dec
test -s test-stl/cad_extrude_cut.stp

echo "[phase_b] extrude cut circle"
./ailang.x CAD/demo_extrude_cut_circle.ailang -o /tmp/dcc && /tmp/dcc
test "$(grep -c FACE_BOUND test-stl/cad_extrude_cut_circle.stp)" -eq 2

echo "[phase_b] extrude cut poly through"
./ailang.x CAD/demo_extrude_cut_poly.ailang -o /tmp/dcp && /tmp/dcp
test "$(grep -c FACE_BOUND test-stl/cad_extrude_cut_poly.stp)" -eq 2

echo "[phase_b] revolve pad"
./ailang.x CAD/demo_revolve.ailang -o /tmp/drev && /tmp/drev
test -s test-stl/cad_revolve_cyl.stp
test -s test-stl/cad_revolve_tube.stp

echo "[phase_b] revolve cut"
./ailang.x CAD/demo_revolve_cut.ailang -o /tmp/drc && /tmp/drc
test "$(grep -c FACE_BOUND test-stl/cad_revolve_cut.stp)" -eq 2

echo "[phase_b] draft + symmetric"
./ailang.x CAD/demo_extrude_draft.ailang -o /tmp/ddr && /tmp/ddr
test -s test-stl/cad_extrude_draft.stp
test -s test-stl/cad_extrude_sym.stp

echo "[phase_b] ALL OK"
