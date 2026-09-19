#!/usr/bin/env bash
# Launch synth kernel + GTK chrome. Same IPC split as Arcade.
#
#   ./scripts/run_synthkit.sh
#
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STATE="${SYNTH_APP_STATE:-/dev/shm/synth_app}"
mkdir -p "$STATE"
pkill -x synth_app.x 2>/dev/null || true
pkill -x synth_shell_gtk 2>/dev/null || true
sleep 0.2
: > "$STATE/cmd.txt"
printf '00000000\n' > "$STATE/keys.txt"
printf '8 256 0 0 0 0 200 4 80 180 2 64 0 0 0 0 0 0 0 0 2 180 0 0 0 0 0 0 0 0 0\n' > "$STATE/ctl.txt"
printf '%s\n' "$HOME/Downloads/PTQ.sf2" > "$STATE/bank.txt"
: > "$STATE/song.txt"
: > "$STATE/song_cmd.txt"
cp -f "$ROOT/../../Librarys/Media/opcode16.json" "$STATE/opcode16.json" 2>/dev/null || true
if [[ -d "$HOME/Downloads/midi3-packs/GeneralUser-GS" ]]; then
  printf '%s\n' "$HOME/Downloads/midi3-packs/GeneralUser-GS" > "$STATE/pack.txt"
fi
if [[ -f "$HOME/Downloads/CV_Intro.mid" ]]; then
  printf '%s\n' "$HOME/Downloads/CV_Intro.mid" > "$STATE/song.txt"
fi
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
export XMODIFIERS="${XMODIFIERS:-@im=none}"
export GTK_IM_MODULE="${GTK_IM_MODULE:-}"

echo "synthkit: building gtk host..."
make -C host
echo "synthkit: building kernel..."
ailang.x synth_app.ailang synth_app.x

./synth_app.x &
APP_PID=$!
sleep 0.3
if ! kill -0 "$APP_PID" 2>/dev/null; then
  echo "ERROR: synth_app.x exited immediately"
  exit 1
fi
./host/synth_shell_gtk "$STATE"
kill "$APP_PID" 2>/dev/null || true
wait "$APP_PID" 2>/dev/null || true
