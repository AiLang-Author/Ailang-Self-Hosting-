#!/usr/bin/env bash
# Transpile, compile, and run every AIMacro_Tests/*.aim.
# If <test>.stdin exists, it is piped to the binary (input() tests).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
AIMACRO="${AIMACRO:-./aimacro.x}"
AILANG="${AILANG:-./ailang.x}"
ok_t=0; fail_t=0; ok_c=0; fail_c=0; ok_r=0; fail_r=0
shopt -s nullglob
for f in AIMacro_Tests/*.aim; do
  base="${f%.aim}"
  out="${base}.ailang"
  name="$(basename "$f")"
  if "$AIMACRO" "$f" "$out" >/tmp/aim_t.err 2>&1; then
    ok_t=$((ok_t+1))
  else
    echo "FAIL transpile $name"
    fail_t=$((fail_t+1))
    continue
  fi
  bin="/tmp/aimatrix_$(basename "$base")"
  if "$AILANG" "$out" "$bin" >/tmp/aim_c.err 2>&1; then
    ok_c=$((ok_c+1))
  else
    echo "FAIL compile $name"
    tail -6 /tmp/aim_c.err
    fail_c=$((fail_c+1))
    continue
  fi
  stdin="${base}.stdin"
  if [[ -f "$stdin" ]]; then
    if "$bin" <"$stdin" >/tmp/aim_r.out 2>/tmp/aim_r.err; then
      echo "OK   run       $name (stdin)"
      ok_r=$((ok_r+1))
    else
      echo "FAIL run       $name rc=$?"
      tail -8 /tmp/aim_r.out
      fail_r=$((fail_r+1))
    fi
  else
    if "$bin" >/tmp/aim_r.out 2>/tmp/aim_r.err; then
      ok_r=$((ok_r+1))
    else
      echo "FAIL run       $name rc=$?"
      tail -8 /tmp/aim_r.out
      fail_r=$((fail_r+1))
    fi
  fi
done
echo "---"
echo "transpile ok=$ok_t fail=$fail_t"
echo "compile   ok=$ok_c fail=$fail_c"
echo "run       ok=$ok_r fail=$fail_r"
[[ "$fail_t" -eq 0 && "$fail_c" -eq 0 && "$fail_r" -eq 0 ]]
