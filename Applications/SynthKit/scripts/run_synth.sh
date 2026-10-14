#!/usr/bin/env bash
# Standalone synth. Loads Surge XT .fxp patches. No sample pack.
#
#   ./scripts/run_synth.sh
#
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STATE="${SURGE_APP_STATE:-/dev/shm/surge_app}"
mkdir -p "$STATE"
pkill -f "synth_app.x ${STATE}" 2>/dev/null || true
pkill -x synth_shell_gtk 2>/dev/null || true
sleep 0.2
: > "$STATE/cmd.txt"
printf '00000000\n' > "$STATE/keys.txt"
printf '0 256 0 0 0 0 80 4 200 200 2 128 0 0 0 0 0 0 0 0 2 180 0 0 0 0 0 0 0 0 0\n' > "$STATE/ctl.txt"
: > "$STATE/bank.txt"
: > "$STATE/song.txt"
: > "$STATE/song_cmd.txt"
: > "$STATE/pack.txt"
: > "$STATE/inst.txt"
dd if=/dev/zero of="$STATE/pcm.bin" bs=32832 count=1 status=none 2>/dev/null || \
  truncate -s 32832 "$STATE/pcm.bin"
if [[ -z "${DISPLAY:-}" ]]; then
  if [[ -S /tmp/.X11-unix/X0 ]]; then export DISPLAY=:0
  elif [[ -S /tmp/.X11-unix/X1 ]]; then export DISPLAY=:1
  else echo "ERROR: no DISPLAY"; exit 1
  fi
fi
if [[ -z "${XAUTHORITY:-}" && -f "$HOME/.Xauthority" ]]; then
  export XAUTHORITY="$HOME/.Xauthority"
fi
echo "synth: building..."
make -C host synth_shell_gtk
if [[ ! -x synth_app.x ]]; then
  ailang.x synth_app.ailang synth_app.x
fi
./synth_app.x "$STATE" card &
APP_PID=$!
sleep 1
if ! kill -0 "$APP_PID" 2>/dev/null; then
  echo "ERROR: synth_app.x exited immediately"
  exit 1
fi
./host/synth_shell_gtk "$STATE"
kill "$APP_PID" 2>/dev/null || true
wait "$APP_PID" 2>/dev/null || true
