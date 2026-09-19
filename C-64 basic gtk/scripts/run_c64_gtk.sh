#!/usr/bin/env bash
# C64 BASIC: Ailang kernel + Gtk blit host (CAD/HalCode/ECU pattern).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
STATE="${C64_APP_STATE:-/tmp/c64_basic}"
mkdir -p "$STATE"
: > "$STATE/keys.txt"
: > "$STATE/gen.txt"
if [[ -z "${DISPLAY:-}" ]]; then
  if [[ -S /tmp/.X11-unix/X0 ]]; then export DISPLAY=:0
  elif [[ -S /tmp/.X11-unix/X1 ]]; then export DISPLAY=:1
  else echo "ERROR: no DISPLAY"; exit 1
  fi
fi
make -C "C-64 basic gtk/host"
./ailang.x "C-64 basic gtk/c64_basic_gtk.ailang" "$ROOT/C-64 basic gtk/c64_basic_gtk.x"
pkill -x c64_basic_gtk.x 2>/dev/null || true
pkill -x c64_shell_gtk 2>/dev/null || true
sleep 0.2
"$ROOT/C-64 basic gtk/c64_basic_gtk.x" &
APP_PID=$!
sleep 0.3
"$ROOT/C-64 basic gtk/host/c64_shell_gtk" "$STATE"
kill "$APP_PID" 2>/dev/null || true
wait "$APP_PID" 2>/dev/null || true
