#!/usr/bin/env bash
# Dogfood kit: send IPC command (same protocol as monorepo).
set -euo pipefail
STATE="${CAD_APP_STATE:-/tmp/cad_app_dogfood}"
WAIT=0
PATH_ARG=""
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --wait|-w) WAIT=1; shift ;;
    --path) PATH_ARG="${2:-}"; shift 2 ;;
    --state) STATE="${2:-}"; shift 2 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
if [[ ${#ARGS[@]} -eq 0 ]]; then
  echo "usage: $0 <cmd...> [--wait] [--path file]" >&2
  exit 1
fi
CMD="${ARGS[*]}"
mkdir -p "$STATE"
if [[ -n "$PATH_ARG" ]]; then
  if [[ -e "$PATH_ARG" ]]; then
    PATH_ARG="$(cd "$(dirname "$PATH_ARG")" && pwd)/$(basename "$PATH_ARG")"
  fi
  printf '%s\n' "$PATH_ARG" > "$STATE/path.txt"
fi
for _ in $(seq 1 80); do
  if [[ ! -s "$STATE/cmd.txt" ]] || ! grep -q '[^[:space:]]' "$STATE/cmd.txt" 2>/dev/null; then break; fi
  sleep 0.02
done
GEN0=$(cat "$STATE/gen.txt" 2>/dev/null || echo 0)
printf '%s\n' "$CMD" > "$STATE/cmd.txt"
echo "cmd: $CMD  (gen was $GEN0)"
if [[ "$WAIT" -eq 1 ]]; then
  for _ in $(seq 1 200); do
    GEN1=$(cat "$STATE/gen.txt" 2>/dev/null || echo 0)
    if [[ "$GEN1" != "$GEN0" ]]; then
      echo "gen: $GEN1"
      cat "$STATE/status.txt" 2>/dev/null || true
      cat "$STATE/hud.txt" 2>/dev/null || true
      exit 0
    fi
    sleep 0.05
  done
  echo "timeout waiting for gen" >&2
  exit 2
fi
