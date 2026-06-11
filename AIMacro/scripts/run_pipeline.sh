#!/usr/bin/env bash
# Transpile one .aim → .ailang → compile/run with ailang.x (if available)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
AIMACRO="${AIMACRO:-./aimacro.x}"
AILANG="${AILANG:-./ailang.x}"
if [[ $# -lt 1 ]]; then
  echo "usage: $0 <path/to/test.aim>" >&2
  exit 1
fi
src="$1"
[[ -f "$src" ]] || { echo "error: not found: $src" >&2; exit 1; }
out="${src%.aim}.ailang"
echo "== transpile =="
"$AIMACRO" "$src" "$out"
echo "== output: $out =="
if [[ -x "$AILANG" ]]; then
  echo "== run =="
  "$AILANG" "$out"
else
  echo "skip run: $AILANG not executable"
fi