#!/bin/bash
# bench_compilers.sh — A/B compile-time + output-equivalence benchmark.
#
# Compares two compiler binaries by building the entire CoreUtils suite
# with each, in turn, into per-compiler output directories. Reports:
#   - per-utility wall time (best of N) for each compiler
#   - aggregate total time (sum of bests)
#   - byte-for-byte diff of every produced binary pair
#
# A new compiler that emits identical bytes within tolerance of the same
# wall time is a safe drop-in. Any size or content delta on a non-kmod
# build is a regression.
#
# Default: A=./ailang.x  B=./ailang_kmod.x  (override via env or argv).
# Usage:   bench_compilers.sh [compilerA] [compilerB] [runs_per_util]

set -u

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AILANG_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$AILANG_ROOT" || { echo "Cannot cd to AILANG_ROOT=$AILANG_ROOT"; exit 1; }

COMPILER_A="${1:-./ailang.x}"
COMPILER_B="${2:-./ailang_kmod.x}"
RUNS="${3:-3}"

DEST_DIR="AiLang_CoreUtils/dist"

UTILS=(
    "echo" "cat" "ls" "wc" "grep" "head" "tail" "seq" "true" "false" "yes"
    "basename" "dirname" "sleep" "touch" "pwd" "whoami" "env" "cut" "tee"
    "uniq" "nl" "rev" "tac" "tr" "fold" "logname" "id" "printenv" "uname"
    "date" "find" "sort" "diff" "cp" "mkdir" "rm" "ln" "file" "mv" "chmod"
    "sync" "readlink" "tty" "realpath" "which" "nohup" "chown" "df" "chgrp"
    "stat" "du" "dd" "split" "expand" "unexpand" "paste"
)

for c in "$COMPILER_A" "$COMPILER_B"; do
    if [ ! -x "$c" ]; then
        echo -e "${RED}❌ Compiler not executable: $c${NC}"
        exit 1
    fi
done
if [ ! -d "$DEST_DIR" ]; then
    echo -e "${RED}❌ $DEST_DIR/ not found.${NC}"
    exit 1
fi

OUT_A="$(mktemp -d -t ailangbench-A-XXXXXX)"
OUT_B="$(mktemp -d -t ailangbench-B-XXXXXX)"
LOG_DIR="$(mktemp -d -t ailangbench-log-XXXXXX)"

cleanup() { :; }  # leave OUT_A/OUT_B/LOG_DIR around for inspection
trap cleanup EXIT

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     AILANG Compiler A/B Benchmark${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "  A: ${CYAN}${COMPILER_A}${NC}   ($(wc -c < "$COMPILER_A") bytes)"
echo -e "  B: ${CYAN}${COMPILER_B}${NC}   ($(wc -c < "$COMPILER_B") bytes)"
echo -e "  runs per util: ${RUNS} (best wall-clock kept)"
echo -e "  outputs: A=$OUT_A   B=$OUT_B"
echo -e "  logs:    $LOG_DIR"
echo ""

# Returns wall-clock seconds (float) for one compile.
time_compile() {
    local compiler="$1" src="$2" out="$3" log="$4"
    local t0 t1
    t0=$(/usr/bin/date +%s.%N)
    "$compiler" "$src" "$out" > "$log" 2>&1
    local rc=$?
    t1=$(/usr/bin/date +%s.%N)
    if [ $rc -ne 0 ]; then
        echo "FAIL"
        return 1
    fi
    awk -v a="$t0" -v b="$t1" 'BEGIN { printf "%.4f\n", b - a }'
}

best_of_n() {
    local compiler="$1" src="$2" out="$3" log="$4" runs="$5"
    local i best="" t
    for ((i=1; i<=runs; i++)); do
        t=$(time_compile "$compiler" "$src" "$out" "$log") || { echo "FAIL"; return 1; }
        if [ -z "$best" ] || awk -v a="$t" -v b="$best" 'BEGIN { exit !(a < b) }'; then
            best="$t"
        fi
    done
    echo "$best"
}

printf "  %-12s %12s %12s %10s %10s %10s\n" "util" "A_best(s)" "B_best(s)" "delta%" "A_size" "diff?"
echo "  ------------------------------------------------------------------------"

a_total=0; b_total=0
ok_count=0; size_diff_count=0; bytes_diff_count=0; fail_count=0

for util in "${UTILS[@]}"; do
    src="${DEST_DIR}/${util}_util/${util}.ailang"
    [ -f "$src" ] || continue

    out_a="${OUT_A}/${util}_exec"
    out_b="${OUT_B}/${util}_exec"
    log_a="${LOG_DIR}/${util}.A.log"
    log_b="${LOG_DIR}/${util}.B.log"

    bestA=$(best_of_n "$COMPILER_A" "$src" "$out_a" "$log_a" "$RUNS")
    bestB=$(best_of_n "$COMPILER_B" "$src" "$out_b" "$log_b" "$RUNS")

    if [ "$bestA" = "FAIL" ] || [ "$bestB" = "FAIL" ]; then
        printf "  ${YELLOW}%-12s${NC} %12s %12s %10s %10s %10s\n" "$util" "$bestA" "$bestB" "-" "-" "-"
        fail_count=$((fail_count + 1))
        continue
    fi

    a_total=$(awk -v a="$a_total" -v b="$bestA" 'BEGIN { printf "%.4f", a + b }')
    b_total=$(awk -v a="$b_total" -v b="$bestB" 'BEGIN { printf "%.4f", a + b }')

    delta=$(awk -v a="$bestA" -v b="$bestB" 'BEGIN {
        if (a == 0) { print "n/a"; exit }
        printf "%+.1f%%", (b - a) / a * 100
    }')

    sizeA=$(wc -c < "$out_a")
    sizeB=$(wc -c < "$out_b")

    if [ "$sizeA" -ne "$sizeB" ]; then
        diff_label="${RED}SIZE${NC}"
        size_diff_count=$((size_diff_count + 1))
    elif ! cmp -s "$out_a" "$out_b"; then
        diff_label="${YELLOW}BYTES${NC}"
        bytes_diff_count=$((bytes_diff_count + 1))
    else
        diff_label="${GREEN}same${NC}"
        ok_count=$((ok_count + 1))
    fi

    printf "  %-12s %12s %12s %10s %10s %b\n" \
        "$util" "$bestA" "$bestB" "$delta" "$sizeA" "$diff_label"
done

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

agg_delta=$(awk -v a="$a_total" -v b="$b_total" 'BEGIN {
    if (a == 0) { print "n/a"; exit }
    printf "%+.1f%%", (b - a) / a * 100
}')

printf "  Total wall (sum of bests):  A=${CYAN}%s${NC}s   B=${CYAN}%s${NC}s   Δ=%s\n" "$a_total" "$b_total" "$agg_delta"
printf "  Output equivalence:         ${GREEN}%d same${NC}   ${YELLOW}%d byte-diff${NC}   ${RED}%d size-diff${NC}   ${RED}%d compile-fail${NC}\n" \
    "$ok_count" "$bytes_diff_count" "$size_diff_count" "$fail_count"

if [ "$size_diff_count" -gt 0 ] || [ "$bytes_diff_count" -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Inspect divergence with:${NC}"
    echo "  diff <(xxd $OUT_A/<util>_exec) <(xxd $OUT_B/<util>_exec) | head"
fi

# Exit non-zero if there were compile failures OR (when comparing two
# compilers expected to be equivalent) any byte/size diffs. Caller can
# disable the equivalence check with EXPECT_EQUIV=0 in env.
EXPECT_EQUIV="${EXPECT_EQUIV:-1}"
fail_total=$fail_count
if [ "$EXPECT_EQUIV" = "1" ]; then
    fail_total=$((fail_total + size_diff_count + bytes_diff_count))
fi
exit "$fail_total"
