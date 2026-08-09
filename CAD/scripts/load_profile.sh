#!/usr/bin/env bash
# Load arbitrary DXF profile → STEP (uses cad_load.x contract).
# Usage: load_profile.sh <in.dxf> <out.stp> [height_mm]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
IN="${1:?usage: load_profile.sh in.dxf out.stp [height]}"
OUT="${2:?}"
H="${3:-10}"
if [[ ! -x ./cad_load.x ]]; then
  ./ailang.x CAD/cad_load.ailang -o cad_load.x
fi
./cad_load.x --in "$IN" --out "$OUT" --height "$H"
echo "OK $OUT"
