#!/bin/bash
# Desk skeleton. The window is a blit. Closing it stops the desk process.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
mkdir -p /dev/shm/daw
if [[ ! -x "$ROOT/daw_desk.x" ]]; then
  "$REPO/ailang.x" "$ROOT/daw_desk.ailang" "$ROOT/daw_desk.x"
fi
gcc -O2 -o "$ROOT/alsa_names" "$ROOT/alsa_names.c"
if [[ ! -x "$ROOT/view_gtk" ]]; then
  g++ -O2 -std=c++17 -o "$ROOT/view_gtk" "$ROOT/view_gtk.cxx" $(pkg-config --cflags --libs gtk+-3.0)
fi
"$ROOT/daw_desk.x" &
APP=$!
cleanup() { kill "$APP" 2>/dev/null || true; }
trap cleanup EXIT
export DISPLAY="${DISPLAY:-:0}"
"$ROOT/view_gtk"
