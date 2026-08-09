#!/usr/bin/env bash
# Live CAD viewport launcher (always opens a real X11/XWayland window).
# Does NOT use headless BMP as the daily path.
#
# Usage:
#   ./CAD/scripts/run_cad_app.sh
#   ./CAD/scripts/run_cad_app.sh -i test-stl/test-dxf-files/diamond.dxf -H 15
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

STATE="${CAD_APP_STATE:-/tmp/cad_app}"
HOST_BIN="./CAD/host/cad_host_x11"
APP_BIN="./cad_app.x"
APP_SRC="CAD/cad_app.ailang"

# --- display check (X11 or XWayland under Wayland) ---
if [[ -z "${DISPLAY:-}" ]]; then
  # common Pop/GNOME defaults
  if [[ -S /tmp/.X11-unix/X0 ]]; then
    export DISPLAY=:0
  elif [[ -S /tmp/.X11-unix/X1 ]]; then
    export DISPLAY=:1
  else
    echo "ERROR: No DISPLAY and no /tmp/.X11-unix/X* socket."
    echo "  You need a graphical session with X11 or XWayland."
    echo "  Pop!_OS: at login gear, try 'Pop on Xorg' if pure Wayland fails."
    echo "  Check:  echo \$XDG_SESSION_TYPE  echo \$DISPLAY"
    exit 1
  fi
  echo "run_cad_app: DISPLAY was unset → using $DISPLAY"
fi

if [[ -z "${XAUTHORITY:-}" && -f "$HOME/.Xauthority" ]]; then
  export XAUTHORITY="$HOME/.Xauthority"
fi

# Prove X works before starting the loop
if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  echo "ERROR: cannot talk to X display '$DISPLAY' (xdpyinfo failed)."
  echo "  session: ${XDG_SESSION_TYPE:-unknown}"
  echo "  Try:  export DISPLAY=:0"
  echo "  Or log into an Xorg session (not pure Wayland without XWayland)."
  exit 1
fi
echo "run_cad_app: X OK on $DISPLAY (session=${XDG_SESSION_TYPE:-?})"

# --- build if needed ---
if [[ ! -x "$HOST_BIN" ]] || [[ "$HOST_BIN" -ot CAD/host/cad_host_x11.c ]]; then
  echo "run_cad_app: building host..."
  cc -O2 -o "$HOST_BIN" CAD/host/cad_host_x11.c -lX11
fi
if [[ ! -x "$APP_BIN" ]] || [[ "$APP_BIN" -ot "$APP_SRC" ]]; then
  echo "run_cad_app: building cad_app..."
  ./ailang.x "$APP_SRC" -o "$APP_BIN"
fi

mkdir -p "$STATE" test-stl
# wipe IPC state so startup never shows previous session frame/solid/status
rm -f "$STATE"/cmd.txt "$STATE"/frame.raw "$STATE"/meta.bin \
      "$STATE"/gen.txt "$STATE"/status.txt "$STATE"/tool.txt \
      "$STATE"/parts.txt "$STATE"/sel.txt
# empty frame placeholder so host does not blit stale pixels
: > "$STATE/cmd.txt"
printf '0\n' > "$STATE/gen.txt"
printf 'SKETCH empty\n' > "$STATE/status.txt"
printf '1 0 0 0\n' > "$STATE/tool.txt"

# --- hosts first (full shell env for DISPLAY) ---
PANEL_BIN="./CAD/host/cad_panel_x11"
if [[ ! -x "$PANEL_BIN" ]] || [[ "$PANEL_BIN" -ot CAD/host/cad_panel_x11.c ]]; then
  echo "run_cad_app: building tools panel..."
  cc -O2 -o "$PANEL_BIN" CAD/host/cad_panel_x11.c -lX11
fi

echo "run_cad_app: starting viewport host..."
"$HOST_BIN" "$STATE" &
HOST_PID=$!
echo "run_cad_app: starting tools panel..."
"$PANEL_BIN" "$STATE" &
PANEL_PID=$!
cleanup() {
  echo "run_cad_app: shutting down (clear state + hosts)"
  # drop IPC so next launch cannot show this session
  rm -f "$STATE"/cmd.txt "$STATE"/frame.raw "$STATE"/meta.bin \
        "$STATE"/gen.txt "$STATE"/status.txt "$STATE"/tool.txt \
        "$STATE"/parts.txt "$STATE"/sel.txt 2>/dev/null || true
  kill "$HOST_PID" "$PANEL_PID" 2>/dev/null || true
  wait "$HOST_PID" 2>/dev/null || true
  wait "$PANEL_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 0.3
if ! kill -0 "$HOST_PID" 2>/dev/null; then
  echo "ERROR: viewport host exited immediately — no window."
  exit 1
fi
echo "run_cad_app: viewport pid=$HOST_PID  panel pid=$PANEL_PID"

# --- app with --nohost so it never re-execs with empty env ---
# Default: EMPTY sketch (no diamond auto-load — that looked like "stale save")
# Optional DXF:  ./CAD/scripts/run_cad_app.sh -i path/to/file.dxf -H 20
if [[ $# -eq 0 ]]; then
  set -- -H 20
fi

echo "run_cad_app: starting model loop: $APP_BIN --nohost $*"
echo "  VIEWPORT: LMB orbit | scroll zoom | sketch click-click | RMB cancel"
echo "  PANEL:    tools / file buttons (IPC) — primary UI for draw & docs"
echo "  Default: empty sketch (pass -i file.dxf to load a DXF)"
echo "  keys still work on either window"
exec "$APP_BIN" --nohost "$@"
