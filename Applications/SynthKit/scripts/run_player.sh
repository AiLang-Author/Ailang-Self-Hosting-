#!/usr/bin/env bash
# Sample player. Any MIDI 3 pack plus a MIDI song. Not the synthesizer.
#
#   ./scripts/run_player.sh
#   MIDI3_PACK=/path/to/pack MIDI3_SONG=/path/to/file.mid ./scripts/run_player.sh
#
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STATE="${SAMPLE_PLAYER_STATE:-/dev/shm/sample_player}"
mkdir -p "$STATE"
pkill -f "synth_app.x ${STATE}" 2>/dev/null || true
pkill -x sample_player_gtk 2>/dev/null || true
sleep 0.2
: > "$STATE/cmd.txt"
printf '00000000\n' > "$STATE/keys.txt"
printf '0 256 0 0 0 0 80 4 80 180 2 64 0 0 0 0 0 0 0 0 2 180 0 0 0 0 0 0 0 0 0\n' > "$STATE/ctl.txt"
: > "$STATE/bank.txt"
: > "$STATE/song.txt"
: > "$STATE/song_cmd.txt"
: > "$STATE/pack.txt"
: > "$STATE/inst.txt"
rm -f "$STATE/ready.txt"
if [[ -z "${MIDI3_PACK:-}" && -f "$HOME/Downloads/midi3-packs/UprightPianoKW/pack.json" ]]; then
  MIDI3_PACK="$HOME/Downloads/midi3-packs/UprightPianoKW"
fi
cp -f "$ROOT/../../Librarys/Media/opcode16.json" "$STATE/opcode16.json" 2>/dev/null || \
  cp -f /home/bob/Ailang-Self-Hosting-/Librarys/Media/opcode16.json "$STATE/opcode16.json"
if [[ -n "${MIDI3_PACK:-}" && -f "${MIDI3_PACK}/pack.json" ]]; then
  printf '%s\n' "$MIDI3_PACK" > "$STATE/pack.txt"
fi
if [[ -n "${MIDI3_SONG:-}" && -f "$MIDI3_SONG" ]]; then
  printf '%s\n' "$MIDI3_SONG" > "$STATE/song.txt"
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
echo "sample player: building..."
make -C host sample_player_gtk
if [[ ! -x synth_app.x ]]; then
  ailang.x synth_app.ailang synth_app.x
fi
./synth_app.x "$STATE" card &
APP_PID=$!
echo "sample player: loading the pack..."
for _ in $(seq 1 120); do
  if [[ -s "$STATE/ready.txt" ]]; then
    break
  fi
  if ! kill -0 "$APP_PID" 2>/dev/null; then
    echo "ERROR: synth_app.x exited immediately"
    exit 1
  fi
  sleep 0.5
done
if [[ ! -s "$STATE/ready.txt" ]]; then
  echo "ERROR: sample player did not finish starting"
  kill "$APP_PID" 2>/dev/null || true
  exit 1
fi
./host/sample_player_gtk "$STATE"
kill "$APP_PID" 2>/dev/null || true
wait "$APP_PID" 2>/dev/null || true
