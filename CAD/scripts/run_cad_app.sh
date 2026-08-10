#!/usr/bin/env bash
# Live CAD viewport launcher (FLTK shell preferred; X11 host+panel fallback).
# Does NOT use headless BMP as the daily path.
#
# Usage:
#   ./CAD/scripts/run_cad_app.sh
#   ./CAD/scripts/run_cad_app.sh -i test-stl/test-dxf-files/diamond.dxf -H 15
#   CAD_UI=x11 ./CAD/scripts/run_cad_app.sh    # force legacy X11 hosts
#   CAD_UI=fltk ./CAD/scripts/run_cad_app.sh   # force FLTK (default if built)
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

STATE="${CAD_APP_STATE:-/tmp/cad_app}"
HOST_BIN="./CAD/host/cad_host_x11"
PANEL_BIN="./CAD/host/cad_panel_x11"
SHELL_BIN="./CAD/host/cad_shell_fltk"
FLTK_CFG="${FLTK_CONFIG:-$ROOT/third_party/fltk/bin/fltk-config}"
APP_BIN="./cad_app.x"
APP_SRC="CAD/cad_app.ailang"
UI="${CAD_UI:-auto}"

# --- display check (X11 or XWayland under Wayland) ---
if [[ -z "${DISPLAY:-}" ]]; then
  if [[ -S /tmp/.X11-unix/X0 ]]; then
    export DISPLAY=:0
  elif [[ -S /tmp/.X11-unix/X1 ]]; then
    export DISPLAY=:1
  else
    echo "ERROR: No DISPLAY and no /tmp/.X11-unix/X* socket."
    exit 1
  fi
  echo "run_cad_app: DISPLAY was unset → using $DISPLAY"
fi

if [[ -z "${XAUTHORITY:-}" && -f "$HOME/.Xauthority" ]]; then
  export XAUTHORITY="$HOME/.Xauthority"
fi

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  echo "ERROR: cannot talk to X display '$DISPLAY' (xdpyinfo failed)."
  exit 1
fi
echo "run_cad_app: X OK on $DISPLAY (session=${XDG_SESSION_TYPE:-?})"

# --- build presenters ---
build_x11() {
  if [[ ! -x "$HOST_BIN" ]] || [[ "$HOST_BIN" -ot CAD/host/cad_host_x11.c ]]; then
    echo "run_cad_app: building cad_host_x11..."
    cc -O2 -o "$HOST_BIN" CAD/host/cad_host_x11.c -lX11 -lm
  fi
  if [[ ! -x "$PANEL_BIN" ]] || [[ "$PANEL_BIN" -ot CAD/host/cad_panel_x11.c ]]; then
    echo "run_cad_app: building cad_panel_x11..."
    cc -O2 -o "$PANEL_BIN" CAD/host/cad_panel_x11.c -lX11
  fi
}

build_fltk() {
  if [[ ! -x "$FLTK_CFG" ]]; then
    return 1
  fi
  if [[ ! -x "$SHELL_BIN" ]] || [[ "$SHELL_BIN" -ot CAD/host/cad_shell_fltk.cxx ]]; then
    echo "run_cad_app: building cad_shell_fltk..."
    g++ -O2 -o "$SHELL_BIN" CAD/host/cad_shell_fltk.cxx \
      $($FLTK_CFG --cxxflags) $($FLTK_CFG --ldflags --use-images)
  fi
  return 0
}

USE_FLTK=0
case "$UI" in
  fltk)
    if ! build_fltk; then
      echo "ERROR: CAD_UI=fltk but FLTK not at $FLTK_CFG" >&2
      exit 1
    fi
    USE_FLTK=1
    ;;
  x11)
    build_x11
    USE_FLTK=0
    ;;
  auto|*)
    if build_fltk; then
      USE_FLTK=1
    else
      echo "run_cad_app: FLTK not found — falling back to X11 host+panel"
      build_x11
      USE_FLTK=0
    fi
    ;;
esac

if [[ ! -x "$APP_BIN" ]] || [[ "$APP_BIN" -ot "$APP_SRC" ]]; then
  echo "run_cad_app: building cad_app..."
  ./ailang.x "$APP_SRC" -o "$APP_BIN"
fi

mkdir -p "$STATE" test-stl
# wipe IPC state so startup never shows previous session frame/solid/status
rm -f "$STATE"/cmd.txt "$STATE"/frame.raw "$STATE"/meta.bin \
      "$STATE"/gen.txt "$STATE"/status.txt "$STATE"/tool.txt \
      "$STATE"/parts.txt "$STATE"/sel.txt "$STATE"/hud.txt \
      "$STATE"/path.txt "$STATE"/shot.bmp "$STATE"/viewport.png
: > "$STATE/cmd.txt"
printf '0\n' > "$STATE/gen.txt"
printf 'SKETCH empty\n' > "$STATE/status.txt"
printf '1 0 0 0\n' > "$STATE/tool.txt"
printf 'mode=sketch tool=line phase=0 pad_H=20 plane_pid=0 plane_n=0 grid=1 dirty=0\n' > "$STATE/hud.txt"

HOST_PID=""
PANEL_PID=""
if [[ "$USE_FLTK" -eq 1 ]]; then
  echo "run_cad_app: starting FLTK shell..."
  "$SHELL_BIN" "$STATE" &
  HOST_PID=$!
else
  echo "run_cad_app: starting viewport host..."
  "$HOST_BIN" "$STATE" &
  HOST_PID=$!
  echo "run_cad_app: starting tools panel..."
  "$PANEL_BIN" "$STATE" &
  PANEL_PID=$!
fi

cleanup() {
  echo "run_cad_app: shutting down (clear state + hosts)"
  rm -f "$STATE"/cmd.txt "$STATE"/frame.raw "$STATE"/meta.bin \
        "$STATE"/gen.txt "$STATE"/status.txt "$STATE"/tool.txt \
        "$STATE"/parts.txt "$STATE"/sel.txt "$STATE"/hud.txt \
        "$STATE"/path.txt 2>/dev/null || true
  [[ -n "$HOST_PID" ]] && kill "$HOST_PID" 2>/dev/null || true
  [[ -n "$PANEL_PID" ]] && kill "$PANEL_PID" 2>/dev/null || true
  wait "$HOST_PID" 2>/dev/null || true
  [[ -n "$PANEL_PID" ]] && wait "$PANEL_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 0.3
if ! kill -0 "$HOST_PID" 2>/dev/null; then
  echo "ERROR: UI host exited immediately — no window."
  exit 1
fi
echo "run_cad_app: UI pid=$HOST_PID  fltk=$USE_FLTK"

if [[ $# -eq 0 ]]; then
  set -- -H 20
fi

echo "run_cad_app: starting model loop: $APP_BIN --nohost $*"
echo "  VIEWPORT: LMB orbit | scroll zoom | sketch click | RMB cancel"
if [[ "$USE_FLTK" -eq 1 ]]; then
  echo "  MENUS: File · Sketch · Plane · Feature · View (grid, open DXF, shot)"
else
  echo "  PANEL: tools / file buttons (IPC)"
fi
echo "  Agent:  ./CAD/scripts/cad_cmd.sh <cmd> --wait"
echo "          ./CAD/scripts/cad_shot.sh [out.png]"
exec "$APP_BIN" --nohost "$@"
