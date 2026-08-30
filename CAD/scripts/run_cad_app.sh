#!/usr/bin/env bash
# Live CAD viewport launcher.
# Product chrome is Gtk3 (tools.json). FLTK is dropped.
# PostgreSQL cad_db is required (docs). See docs/cad/CAD_UI_PLAN.md v3.
#
# Usage:
#   ./CAD/scripts/run_cad_app.sh
#   ./CAD/scripts/run_cad_app.sh -i test-stl/test-dxf-files/diamond.dxf -H 15
#   CAD_UI=x11  ./CAD/scripts/run_cad_app.sh   # emergency X11 blit+panel only
#
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

STATE="${CAD_APP_STATE:-/tmp/cad_app}"
HOST_BIN="./CAD/host/cad_host_x11"
PANEL_BIN="./CAD/host/cad_panel_x11"
GTK_SHELL="./CAD/host/cad_shell_gtk"
APP_BIN="./cad_app.x"
APP_SRC="CAD/cad_app.ailang"
UI="${CAD_UI:-gtk}"

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

export XMODIFIERS="${XMODIFIERS:-@im=none}"
export GTK_IM_MODULE="${GTK_IM_MODULE:-}"
export QT_IM_MODULE="${QT_IM_MODULE:-}"

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

have_gtk() {
  # compiled Gtk3 host (Python shell is gone)
  [[ -x "$GTK_SHELL" ]] || [[ -f CAD/host/cad_shell_gtk.cxx ]]
}

UI_KIND=""  # gtk | x11
case "$UI" in
  x11)
    build_x11
    UI_KIND=x11
    ;;
  fltk)
    echo "ERROR: FLTK host is dropped. Use Gtk (default) or CAD_UI=x11." >&2
    exit 1
    ;;
  gtk|auto|*)
    if ! have_gtk; then
      echo "ERROR: compiled Gtk host missing (make -C CAD/host gtk)." >&2
      exit 1
    fi
    UI_KIND=gtk
    ;;
esac

# --- PostgreSQL: UI catalog seed (hard dep) ---
if ! psql -d cad_db -c 'SELECT 1' >/dev/null 2>&1; then
  echo "ERROR: PostgreSQL cad_db not reachable (product hard dep)." >&2
  echo "  createdb cad_db && psql -d cad_db -f CAD/sql/cad_schema.sql" >&2
  echo "  psql -d cad_db -f CAD/sql/cad_ui_catalog.sql" >&2
  exit 1
fi
echo "run_cad_app: seeding UI catalog into cad_db..."
psql -d cad_db -v ON_ERROR_STOP=1 -f "$ROOT/CAD/sql/cad_ui_catalog.sql" >/dev/null

need_rebuild=0
if [[ ! -x "$APP_BIN" ]]; then
  need_rebuild=1
fi
for src in "$APP_SRC" \
           CAD/App/Doc.ailang CAD/App/Ipc.ailang CAD/App/Tools.ailang \
           CAD/App/Draw.ailang CAD/App/State.ailang CAD/App/Solid.ailang \
           CAD/App/Plane.ailang \
           Librarys/Cad/Library.CAD_UI.ailang \
           Librarys/Cad/Library.CAD_Repo.ailang; do
  if [[ -f "$src" && "$APP_BIN" -ot "$src" ]]; then
    need_rebuild=1
  fi
done
if [[ "$need_rebuild" -eq 1 ]]; then
  echo "run_cad_app: building cad_app..."
  ./ailang.x "$APP_SRC" -o "$APP_BIN"
fi

mkdir -p "$STATE" test-stl
# keep last session log for cat after a crash; rotate to .prev
if [[ -f "$STATE/session.log" ]]; then
  mv -f "$STATE/session.log" "$STATE/session.prev.log"
fi
echo "run_cad_app: session log $STATE/session.log  (previous → session.prev.log)"
# wipe IPC state so startup never shows previous session frame/solid/status
rm -f "$STATE"/cmd.txt "$STATE"/frame.raw "$STATE"/meta.bin \
      "$STATE"/gen.txt "$STATE"/status.txt "$STATE"/tool.txt \
      "$STATE"/parts.txt "$STATE"/sel.txt "$STATE"/hud.txt \
      "$STATE"/path.txt "$STATE"/shot.bmp "$STATE"/viewport.png \
      "$STATE"/tools.json
: > "$STATE/cmd.txt"
printf '0\n' > "$STATE/gen.txt"
printf 'SKETCH empty\n' > "$STATE/status.txt"
printf '1 0 0 0\n' > "$STATE/tool.txt"
printf 'mode=sketch tool=line phase=0 pad_H=20 plane_pid=0 plane_n=0 grid=1 dirty=0\n' > "$STATE/hud.txt"

HOST_PID=""
PANEL_PID=""
export CAD_APP_STATE="$STATE"
case "$UI_KIND" in
  gtk)
    if [[ ! -x "$GTK_SHELL" ]] || [[ "$GTK_SHELL" -ot CAD/host/cad_shell_gtk.cxx ]]; then
      echo "run_cad_app: building compiled Gtk shell..."
      make -C CAD/host gtk
    fi
    echo "run_cad_app: starting compiled Gtk shell..."
    "$GTK_SHELL" "$STATE" &
    HOST_PID=$!
    ;;
  x11)
    echo "run_cad_app: starting viewport host..."
    "$HOST_BIN" "$STATE" &
    HOST_PID=$!
    echo "run_cad_app: starting tools panel..."
    "$PANEL_BIN" "$STATE" &
    PANEL_PID=$!
    ;;
esac

cleanup() {
  echo "run_cad_app: shutting down (clear state + hosts)"
  rm -f "$STATE"/cmd.txt "$STATE"/frame.raw "$STATE"/meta.bin \
        "$STATE"/gen.txt "$STATE"/status.txt "$STATE"/tool.txt \
        "$STATE"/parts.txt "$STATE"/sel.txt "$STATE"/hud.txt \
        "$STATE"/path.txt 2>/dev/null || true
  # leave session.log / session.prev.log — cat after a crash instead of pasting
  if [[ -n "$HOST_PID" ]]; then
    kill -15 "$HOST_PID" 2>/dev/null || true
    sleep 0.2
    kill -9 "$HOST_PID" 2>/dev/null || true
  fi
  if [[ -n "$PANEL_PID" ]]; then
    kill -15 "$PANEL_PID" 2>/dev/null || true
    sleep 0.05
    kill -9 "$PANEL_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

sleep 0.3
if ! kill -0 "$HOST_PID" 2>/dev/null; then
  echo "ERROR: UI host exited immediately — no window."
  exit 1
fi
echo "run_cad_app: UI pid=$HOST_PID  kind=$UI_KIND"

if [[ $# -eq 0 ]]; then
  set -- -H 20
fi

echo "run_cad_app: starting model loop: $APP_BIN --nohost $*"
echo "  VIEWPORT: LMB orbit | scroll zoom | sketch click | RMB cancel"
echo "  CHROME: Gtk from CAD_UI tools.json (cmd: tools to refresh)"
echo "  Agent:  ./CAD/scripts/cad_cmd.sh <cmd> --wait"
echo "          ./CAD/scripts/cad_shot.sh [out.png]"
"$APP_BIN" --nohost "$@"
