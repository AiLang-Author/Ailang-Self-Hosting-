#!/usr/bin/env bash
# Send one IPC command to cad_app and optionally wait for gen to advance.
#
# Usage:
#   ./CAD/scripts/cad_cmd.sh tool_line
#   ./CAD/scripts/cad_cmd.sh "orbit 40 -20" --wait
#   ./CAD/scripts/cad_cmd.sh import --path /path/to/file.dxf
#   CAD_APP_STATE=/tmp/cad_app ./CAD/scripts/cad_cmd.sh grid 1
#
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

set -euo pipefail
STATE="${CAD_APP_STATE:-/tmp/cad_app}"
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
  echo "usage: $0 <cmd...> [--wait] [--path file] [--state dir]" >&2
  exit 1
fi
CMD="${ARGS[*]}"
mkdir -p "$STATE"

if [[ -n "$PATH_ARG" ]]; then
  # absolutize so kernel open() works regardless of cwd
  if [[ -e "$PATH_ARG" ]]; then
    PATH_ARG="$(cd "$(dirname "$PATH_ARG")" && pwd)/$(basename "$PATH_ARG")"
  fi
  printf '%s\n' "$PATH_ARG" > "$STATE/path.txt"
fi

# wait for free cmd slot
for _ in $(seq 1 80); do
  if [[ ! -s "$STATE/cmd.txt" ]]; then break; fi
  # treat whitespace-only as free
  if ! grep -q '[^[:space:]]' "$STATE/cmd.txt" 2>/dev/null; then break; fi
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
  echo "timeout waiting for gen advance" >&2
  exit 2
fi
