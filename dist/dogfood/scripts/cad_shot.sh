#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="${CAD_APP_STATE:-/tmp/cad_app_dogfood}"
OUT="${1:-$STATE/viewport.png}"
python3 "$ROOT/scripts/frame_to_png.py" "$STATE" "$OUT"
echo "shot: $OUT"
