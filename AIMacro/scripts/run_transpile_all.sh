#!/usr/bin/env bash
# Transpile every .aim under AIMacro_Tests/ via aimacro.x
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
AIMACRO="${AIMACRO:-./aimacro.x}"
TESTS_DIR="${TESTS_DIR:-AIMacro_Tests}"
if [[ ! -x "$AIMACRO" ]]; then
  echo "error: $AIMACRO not found or not executable" >&2
  exit 1
fi
ok=0
fail=0
shopt -s nullglob
for f in "$TESTS_DIR"/*.aim "$TESTS_DIR"/*/*.aim; do
  [[ -f "$f" ]] || continue
  base="${f%.aim}"
  out="${base}.ailang"
  if "$AIMACRO" "$f" "$out" 2>/dev/null; then
    echo "OK   transpile $f"
    ((ok++)) || true
  else
    echo "FAIL transpile $f" >&2
    ((fail++)) || true
  fi
done
echo "---"
echo "transpile ok=$ok fail=$fail"
[[ "$fail" -eq 0 ]]