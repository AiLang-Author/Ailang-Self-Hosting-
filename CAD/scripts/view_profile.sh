#!/usr/bin/env bash
# Load DXF → software view BMP (cad_view.x contract).
# Usage: view_profile.sh <in.dxf> <out.bmp> [height_mm] [view:0|1|2]
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
IN="${1:?usage: view_profile.sh in.dxf out.bmp [height] [view]}"
OUT="${2:?}"
H="${3:-10}"
V="${4:-0}"
if [[ ! -x ./cad_view.x ]]; then
  ./ailang.x CAD/cad_view.ailang -o cad_view.x
fi
./cad_view.x --in "$IN" --shot "$OUT" --height "$H" --view "$V" --wire 0 --defl 2
echo "OK $OUT"
