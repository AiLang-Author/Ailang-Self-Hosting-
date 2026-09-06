#!/usr/bin/env bash
# Launch paint_app.x + thin Gtk blit host.
# Same contract as CAD/dash: kernel owns pixels, host blits + cmds.
#
#   ./Paint/scripts/run_paint_app.sh
#
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
STATE="${PAINT_APP_STATE:-/tmp/paint_app}"
mkdir -p "$STATE"
pkill -x paint_app.x 2>/dev/null || true
pkill -x paint_shell_gtk 2>/dev/null || true
sleep 0.2
: > "$STATE/cmd.txt"
: > "$STATE/ptr.txt"

if [[ -z "${DISPLAY:-}" ]]; then
  if [[ -S /tmp/.X11-unix/X0 ]]; then export DISPLAY=:0
  elif [[ -S /tmp/.X11-unix/X1 ]]; then export DISPLAY=:1
  else echo "ERROR: no DISPLAY"; exit 1
  fi
fi

if [[ -z "${XAUTHORITY:-}" && -f "$HOME/.Xauthority" ]]; then
  export XAUTHORITY="$HOME/.Xauthority"
fi
export XMODIFIERS="${XMODIFIERS:-@im=none}"
export GTK_IM_MODULE="${GTK_IM_MODULE:-}"

echo "run_paint_app: building gtk host..."
make -C Paint/host
echo "run_paint_app: building paint_app..."
./ailang.x Paint/paint_app.ailang -o "$ROOT/paint_app.x"

./paint_app.x &
APP_PID=$!
sleep 0.4
./Paint/host/paint_shell_gtk "$STATE"
kill "$APP_PID" 2>/dev/null || true
wait "$APP_PID" 2>/dev/null || true
