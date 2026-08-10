#!/usr/bin/env bash
# Capture current CAD viewport to PNG for agent/debug.
#
# Usage:
#   ./CAD/scripts/cad_shot.sh                 # /tmp/cad_app/viewport.png
#   ./CAD/scripts/cad_shot.sh out.png
#   ./CAD/scripts/cad_shot.sh --kernel out.png  # also ask kernel for shot.bmp
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE="${CAD_APP_STATE:-/tmp/cad_app}"
KERNEL=0
OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --kernel|-k) KERNEL=1; shift ;;
    --state) STATE="${2:-}"; shift 2 ;;
    *) OUT="$1"; shift ;;
  esac
done
OUT="${OUT:-$STATE/viewport.png}"

if [[ "$KERNEL" -eq 1 ]]; then
  "$ROOT/CAD/scripts/cad_cmd.sh" shot --wait --state "$STATE" || true
fi

python3 "$ROOT/CAD/scripts/frame_to_png.py" "$STATE" "$OUT"
# convenience copy for agent read_file
if [[ "$OUT" != "$STATE/viewport.png" ]]; then
  cp -f "$OUT" "$STATE/viewport.png" 2>/dev/null || true
fi
echo "shot: $OUT"
