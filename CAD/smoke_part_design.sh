#!/usr/bin/env bash
# Part Design parity: pattern, mirror, shell, loft, sweep, non-box pattern,
# plus edge/negative honesty gates. Regenerates fixtures under test-stl/.
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p test-stl

echo "[part_design] pattern/mirror/shell"
./ailang.x CAD/demo_part_design.ailang -o /tmp/dpd && /tmp/dpd
test "$(grep -c ADVANCED_FACE test-stl/cad_pattern_linear.stp)" -eq 24
test "$(grep -c ADVANCED_FACE test-stl/cad_mirror.stp)" -eq 12
test "$(grep -c ADVANCED_FACE test-stl/cad_pattern_circular.stp)" -eq 36
test "$(grep -c ADVANCED_FACE test-stl/cad_shell.stp)" -eq 11

echo "[part_design] loft/sweep/non-box pattern"
./ailang.x CAD/demo_loft_sweep.ailang -o /tmp/dls && /tmp/dls
# loft: 2 caps + 4 sides = 6
test "$(grep -c ADVANCED_FACE test-stl/cad_loft.stp)" -eq 6
# sweep 2-pt path: same 6 faces
test "$(grep -c ADVANCED_FACE test-stl/cad_sweep.stp)" -eq 6
# diamond linear ×4: 6 faces × 4 shells
test "$(grep -c ADVANCED_FACE test-stl/cad_pattern_diamond.stp)" -eq 24
# diamond circular ×5: 6 × 5
test "$(grep -c ADVANCED_FACE test-stl/cad_pattern_diamond_circ.stp)" -eq 30

echo "[part_design] edges + negatives"
./ailang.x CAD/demo_pd_edges.ailang -o /tmp/dpe && /tmp/dpe
# multi-seg sweep = 2 ruled segments compound → 12 faces
test "$(grep -c ADVANCED_FACE test-stl/cad_sweep_3seg.stp)" -eq 12
# mirror diamond: original + clone = 12 faces
test "$(grep -c ADVANCED_FACE test-stl/cad_mirror_diamond.stp)" -eq 12
# clone alone: 6 faces
test "$(grep -c ADVANCED_FACE test-stl/cad_clone_kind0.stp)" -eq 6
test "$(grep -c ADVANCED_FACE test-stl/cad_loft_edge.stp)" -eq 6

echo "[part_design] ALL OK"
