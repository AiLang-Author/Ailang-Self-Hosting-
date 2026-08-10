#!/usr/bin/env bash
# Minimal launcher for the Telegram dogfood kit (X11 hosts, no monorepo required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STATE="${CAD_APP_STATE:-/tmp/cad_app_dogfood}"
export CAD_APP_STATE="$STATE"

if [[ -z "${DISPLAY:-}" ]]; then
  if [[ -S /tmp/.X11-unix/X0 ]]; then export DISPLAY=:0
  elif [[ -S /tmp/.X11-unix/X1 ]]; then export DISPLAY=:1
  else
    echo "No DISPLAY. Need X11 or XWayland."
    exit 1
  fi
fi

mkdir -p "$STATE"
rm -f "$STATE"/* 2>/dev/null || true
: > "$STATE/cmd.txt"
printf '0\n' > "$STATE/gen.txt"
printf 'SKETCH empty\n' > "$STATE/status.txt"
printf '1 0 0 0\n' > "$STATE/tool.txt"

HOST="$ROOT/bin/cad_host_x11"
PANEL="$ROOT/bin/cad_panel_x11"
APP="$ROOT/bin/cad_app.x"
for b in "$HOST" "$PANEL" "$APP"; do
  if [[ ! -x "$b" ]]; then
    echo "Missing $b — rebuild package from monorepo: ./dist/build_dogfood_package.sh"
    exit 1
  fi
done

"$HOST" "$STATE" &
HP=$!
"$PANEL" "$STATE" &
PP=$!
cleanup() { kill "$HP" "$PP" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
sleep 0.3
echo "Dogfood CAD: viewport + tools panel"
echo "  GitHub: https://github.com/AiLang-Author/Ailang-Self-Hosting-"
echo "  Feedback: design notes welcome (see README.md)"
exec "$APP" --nohost -H 15 "$@"
