#!/usr/bin/env bash
# AILang HDL × Yosys regression harness
#
# Usage:
#   ./dev/hdl_test_yosys.sh              # all smokes under dev/
#   ./dev/hdl_test_yosys.sh --strict     # fail if yosys check reports any problems
#   ./dev/hdl_test_yosys.sh hello prims  # subset by name substring
#
# Requires: ./ailang_hdl.x  (or rebuilds if AILANG_HDL_REBUILD=1)
#           yosys on PATH or OSS_CAD_SUITE
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

STRICT=0
FILTERS=()
for a in "$@"; do
  case "$a" in
    --strict) STRICT=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) FILTERS+=("$a") ;;
  esac
done

# Yosys
if [[ -z "${YOSYS:-}" ]]; then
  if command -v yosys >/dev/null 2>&1; then
    YOSYS=yosys
  elif [[ -x "$HOME/tools/oss-cad-suite/bin/yosys" ]]; then
    export PATH="$HOME/tools/oss-cad-suite/bin:$PATH"
    YOSYS=yosys
  else
    echo "FAIL: yosys not found (install oss-cad-suite or put yosys on PATH)"
    exit 2
  fi
fi

HDL_BIN="${HDL_BIN:-$ROOT/ailang_hdl.x}"
if [[ "${AILANG_HDL_REBUILD:-0}" == "1" ]]; then
  echo "== rebuild ailang_hdl.x =="
  ./ailang.x ailang_cli.ailang ailang_hdl.x
fi
if [[ ! -x "$HDL_BIN" ]]; then
  echo "FAIL: missing $HDL_BIN (build with: ./ailang.x ailang_cli.ailang ailang_hdl.x)"
  exit 2
fi

OUT_DIR="${HDL_TEST_OUT:-$ROOT/dev/hdl_test_out}"
mkdir -p "$OUT_DIR"
rm -rf "$OUT_DIR"/*
LOG="$OUT_DIR/summary.log"
: >"$LOG"

# Smoke programs (source → short name)
declare -a SMOKES=(
  "dev/hdl_hello.ailang:hello"
  "dev/hdl_prims_smoke.ailang:prims"
  "dev/hdl_constructs_smoke.ailang:constructs"
  "dev/hdl_foreach_smoke.ailang:foreach"
  "dev/hdl_all_smoke.ailang:all"
  "dev/hdl_smoke.ailang:stream"
  "dev/hdl_logic_only.ailang:logic"
  "dev/hdl_core_syntax.ailang:core"
  "dev/hdl_stress_nested.ailang:stress_nested"
  "dev/hdl_stress_bits.ailang:stress_bits"
  "dev/hdl_stress_array.ailang:stress_array"
  "dev/hdl_stress_branch.ailang:stress_branch"
  "dev/hdl_stress_chain.ailang:stress_chain"
)

pass=0
fail=0
warn=0
skip=0

match_filter() {
  local name="$1"
  if [[ ${#FILTERS[@]} -eq 0 ]]; then
    return 0
  fi
  local f
  for f in "${FILTERS[@]}"; do
    [[ "$name" == *"$f"* ]] && return 0
  done
  return 1
}

run_one() {
  local src="$1"
  local name="$2"
  local base="$OUT_DIR/$name"
  local tlog="$OUT_DIR/$name.log"

  if [[ ! -f "$src" ]]; then
    echo "SKIP  $name (missing $src)"
    echo "SKIP $name" >>"$LOG"
    skip=$((skip + 1))
    return 0
  fi

  echo "== $name =="
  {
    echo "### compile $src"
    if ! "$HDL_BIN" -hdl -period 10 "$src" "$base" 2>&1; then
      echo "COMPILE_FAIL"
      return 1
    fi
    if [[ ! -f "$base.v" ]]; then
      echo "MISSING_V"
      return 1
    fi
    echo "### yosys"
    # Prefer generated .ys; fall back to inline check
    if [[ -f "$base.ys" ]]; then
      if ! "$YOSYS" -s "$base.ys" 2>&1; then
        echo "YOSYS_FAIL"
        return 1
      fi
    else
      if ! "$YOSYS" -q -p "read_verilog $base.v; hierarchy -check -top ailang_top; proc; opt; memory; opt; stat; check" 2>&1; then
        echo "YOSYS_FAIL"
        return 1
      fi
    fi
  } >"$tlog" 2>&1

  local problems
  problems=$(grep -E 'Found and reported [0-9]+ problems' "$tlog" | tail -1 | grep -oE '[0-9]+' | head -1 || true)
  problems=${problems:-0}

  # Hard errors
  if grep -qE 'COMPILE_FAIL|YOSYS_FAIL|MISSING_V|ERROR:|Compilation Failed' "$tlog"; then
    echo "FAIL  $name  (see $tlog)"
    echo "FAIL $name" >>"$LOG"
    fail=$((fail + 1))
    return 1
  fi

  # Artifact checks
  local arts_ok=1
  for ext in v nl.json ys; do
    if [[ ! -f "$base.$ext" ]]; then
      arts_ok=0
    fi
  done
  if [[ "$arts_ok" -ne 1 ]]; then
    echo "FAIL  $name  missing artifacts"
    echo "FAIL $name missing_artifacts" >>"$LOG"
    fail=$((fail + 1))
    return 1
  fi

  # Print channel case-ROM/itoa can trip Yosys check (proc_rom undriven bits).
  # Core logic suites should stay at 0; print suites are soft-warn by default.
  local soft=0
  case "$name" in
    hello|all) soft=1 ;;
  esac

  if [[ "$problems" -eq 0 ]]; then
    echo "PASS  $name  (yosys problems=0)"
    echo "PASS $name problems=0" >>"$LOG"
    pass=$((pass + 1))
  else
    if [[ "$STRICT" -eq 1 && "$soft" -eq 0 ]]; then
      echo "FAIL  $name  (yosys problems=$problems, --strict)"
      echo "FAIL $name problems=$problems strict" >>"$LOG"
      fail=$((fail + 1))
      return 1
    fi
    if [[ "$STRICT" -eq 1 && "$soft" -eq 1 ]]; then
      echo "WARN  $name  (yosys problems=$problems — print-channel soft under --strict)"
      echo "WARN $name problems=$problems print_soft" >>"$LOG"
      warn=$((warn + 1))
    else
      echo "WARN  $name  (yosys problems=$problems — undriven/proc_rom noise often OK)"
      echo "WARN $name problems=$problems" >>"$LOG"
      warn=$((warn + 1))
    fi
  fi
  return 0
}

echo "AILang HDL × Yosys harness"
echo "  root=$ROOT"
echo "  hdl=$HDL_BIN"
echo "  yosys=$("$YOSYS" -V 2>&1 | head -1)"
echo "  out=$OUT_DIR"
echo "  strict=$STRICT"
echo

for entry in "${SMOKES[@]}"; do
  src="${entry%%:*}"
  name="${entry##*:}"
  if ! match_filter "$name"; then
    continue
  fi
  run_one "$src" "$name" || true
done

echo
echo "======== SUMMARY ========"
echo "pass=$pass  warn=$warn  fail=$fail  skip=$skip"
echo "log: $LOG"
cat "$LOG"
echo "========================="

if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
exit 0
