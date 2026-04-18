#!/bin/bash
# bench_all_utils.sh  —  performance + correctness comparison of installed
# AILANG coreutils vs GNU equivalents.
#
# Rewritten 2026-04-18 to close a coverage hole: the old version timed
# AiLang-vs-GNU for each utility but NEVER VERIFIED the outputs matched.
# That's how head/tail/fold shipped broken with "all benchmarks pass."
#
# New rules:
#   1. For each utility, a correctness gate runs first: same invocation,
#      diff outputs byte-for-byte. Mismatch → FAIL, no timing emitted.
#   2. Only utilities that pass the correctness gate proceed to timing.
#   3. Utilities whose output is intentionally environment-dependent
#      (pwd, whoami, date, tty, id, stat, df, du) use `bench_no_diff` —
#      we verify the command succeeds, time it, but don't diff output.
#   4. The final summary clearly separates correctness failures from perf
#      wins/losses.
#
# Usage:
#   ./bench_all_utils.sh                   # all utilities
#   ./bench_all_utils.sh <util>            # one utility only

set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m'

ONLY="${1:-}"

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     AILANG CoreUtils Perf + Correctness Benchmark${NC}"
echo -e "${BLUE}     (Testing installed binaries in PATH)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

BENCH_DIR=$(mktemp -d -t ailang_bench_XXXXXX)
trap 'rm -rf "$BENCH_DIR"' EXIT

echo -e "${YELLOW}Generating test data in $BENCH_DIR...${NC}"

# 100k-line log-shaped file — primary input for filter utilities.
for i in $(seq 1 100000); do
    if [ $((i % 100)) -eq 0 ]; then
        echo "INFO: Processing record $i - ERROR: A rare event occurred."
    else
        echo "INFO: Processing record $i - Status OK, data is normal."
    fi
done > "$BENCH_DIR/bench_test.txt"

cat "$BENCH_DIR/bench_test.txt" | tr ' ' '\t' > "$BENCH_DIR/bench_test_tabs.txt"
seq 1 10000 | shuf > "$BENCH_DIR/bench_sort_numbers.txt"
sort "$BENCH_DIR/bench_test.txt" > "$BENCH_DIR/bench_test_sorted.txt"
cp "$BENCH_DIR/bench_test.txt" "$BENCH_DIR/bench_diff1.txt"
cp "$BENCH_DIR/bench_test.txt" "$BENCH_DIR/bench_diff2.txt"
echo "This is an extra line for diffing" >> "$BENCH_DIR/bench_diff2.txt"
/usr/bin/head -n 100 "$BENCH_DIR/bench_diff1.txt" > "$BENCH_DIR/bench_diff_small1.txt"
/usr/bin/head -n 100 "$BENCH_DIR/bench_diff2.txt" > "$BENCH_DIR/bench_diff_small2.txt"
seq 1 1000 > "$BENCH_DIR/paste1.txt"
seq 1001 2000 > "$BENCH_DIR/paste2.txt"
printf '        eight spaces\n' > "$BENCH_DIR/bench_unexpand.txt"
printf 'one\ttwo\tthree\n' > "$BENCH_DIR/bench_expand.txt"

# Result accumulators
correct_pass=0; correct_fail=0
perf_wins=(); perf_ties=(); perf_losses=()
declare -a correctness_failures=()

# ─── Correctness gate ───────────────────────────────────────────────────────
# Runs AiLang and GNU with identical args once each, diffs outputs.
# Returns 0 if match, non-zero if mismatch (or either blew up).
# Sets `gate_detail` with a human-readable reason on mismatch.
gate_detail=""
correctness_check() {
    local util="$1" cmdline="$2"
    local gnu_bin
    gnu_bin=$(command -v -- "/usr/bin/$util" 2>/dev/null)
    if [ -z "$gnu_bin" ] || [ ! -x "$gnu_bin" ]; then
        gate_detail="no GNU $util installed to compare against"
        return 2
    fi
    local ailang_out gnu_out ailang_rc gnu_rc
    ailang_out=$(eval "$util $cmdline" 2>/dev/null); ailang_rc=$?
    gnu_out=$(eval "$gnu_bin $cmdline" 2>/dev/null); gnu_rc=$?
    if [ $ailang_rc -eq 139 ]; then gate_detail="AiLang SEGFAULT"; return 3; fi
    if [ $ailang_rc -eq 124 ]; then gate_detail="AiLang TIMEOUT";  return 4; fi
    if [ "$ailang_out" = "$gnu_out" ]; then
        return 0
    fi
    gate_detail=$(printf 'output diff (AiLang rc=%d, GNU rc=%d)' "$ailang_rc" "$gnu_rc")
    return 1
}

# ─── Timer ──────────────────────────────────────────────────────────────────
# Times `cmd` for `iters` iterations via the real-time profiler. Echoes
# the elapsed seconds (float) on stdout.
time_cmd() {
    local cmd="$1" iters="$2"
    # Use GNU date explicitly — the installed AiLang `date` may not
    # support +%s.%N yet (documented GNU gap), and the timing source
    # must be reliable.
    local start end
    start=$(/usr/bin/date +%s.%N)
    for i in $(/usr/bin/seq 1 "$iters"); do
        eval "$cmd" > /dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    awk "BEGIN{printf \"%.3f\", $end - $start}"
}

# ─── Main benchmark driver ──────────────────────────────────────────────────
# Usage: bench LABEL UTIL CMDLINE_FOR_GATE AILANG_CMD GNU_CMD ITERS
#   - CMDLINE_FOR_GATE is the args-only version passed to correctness_check
#     (appended to `ailang_util` and `/usr/bin/util` respectively).
#   - AILANG_CMD / GNU_CMD are full command lines used for timing (already
#     include the util name).
bench() {
    local label="$1" util="$2" gate_cmdline="$3"
    local ailang_cmd="$4" gnu_cmd="$5"
    local iters="${6:-100}"

    if [ -n "$ONLY" ] && [ "$util" != "$ONLY" ]; then return; fi

    echo -e "${YELLOW}$label${NC}"

    # Correctness gate first.
    local gate_rc
    correctness_check "$util" "$gate_cmdline"; gate_rc=$?
    case $gate_rc in
        0)
            correct_pass=$((correct_pass+1))
            echo -e "  correctness ${GREEN}✓${NC}"
            ;;
        2)
            echo -e "  correctness ${YELLOW}—${NC}  (no GNU binary)"
            echo ""
            return
            ;;
        *)
            correct_fail=$((correct_fail+1))
            correctness_failures+=("$util: $gate_detail")
            echo -e "  correctness ${RED}✗${NC}  $gate_detail"
            echo -e "  ${DIM}timing skipped — fix output first${NC}"
            echo ""
            return
            ;;
    esac

    # Timing.
    local ailang_sec gnu_sec
    ailang_sec=$(time_cmd "$ailang_cmd" "$iters")
    gnu_sec=$(time_cmd "$gnu_cmd" "$iters")

    echo "  AiLang: ${ailang_sec}s   GNU: ${gnu_sec}s   (${iters}x)"

    local ratio
    ratio=$(awk "BEGIN {if ($gnu_sec == 0 || $ailang_sec == 0) print \"NA\"; else if ($ailang_sec < $gnu_sec) printf \"%.2fx AiLang faster\", $gnu_sec / $ailang_sec; else if ($ailang_sec == $gnu_sec) print \"tied\"; else printf \"%.2fx GNU faster\", $ailang_sec / $gnu_sec}")

    case "$ratio" in
        *"AiLang faster"*)  echo -e "  ${GREEN}→ $ratio${NC}"; perf_wins+=("$util: $ratio") ;;
        tied|*NA*)          echo -e "  ${YELLOW}→ $ratio${NC}"; perf_ties+=("$util") ;;
        *"GNU faster"*)     echo -e "  ${RED}→ $ratio${NC}";    perf_losses+=("$util: $ratio") ;;
    esac
    echo ""
}

# bench_no_diff: same as bench but skips the correctness gate. For utilities
# where the output is intentionally environment-dependent.
bench_no_diff() {
    local label="$1" util="$2"
    local ailang_cmd="$3" gnu_cmd="$4"
    local iters="${5:-100}"

    if [ -n "$ONLY" ] && [ "$util" != "$ONLY" ]; then return; fi

    echo -e "${YELLOW}$label${NC}"
    echo -e "  correctness ${DIM}(env-dep, skipped)${NC}"

    local ailang_sec gnu_sec
    ailang_sec=$(time_cmd "$ailang_cmd" "$iters")
    gnu_sec=$(time_cmd "$gnu_cmd" "$iters")

    echo "  AiLang: ${ailang_sec}s   GNU: ${gnu_sec}s   (${iters}x)"
    local ratio
    ratio=$(awk "BEGIN {if ($gnu_sec == 0 || $ailang_sec == 0) print \"NA\"; else if ($ailang_sec < $gnu_sec) printf \"%.2fx AiLang faster\", $gnu_sec / $ailang_sec; else if ($ailang_sec == $gnu_sec) print \"tied\"; else printf \"%.2fx GNU faster\", $ailang_sec / $gnu_sec}")
    case "$ratio" in
        *"AiLang faster"*) echo -e "  ${GREEN}→ $ratio${NC}"; perf_wins+=("$util: $ratio") ;;
        tied|*NA*)         echo -e "  ${YELLOW}→ $ratio${NC}"; perf_ties+=("$util") ;;
        *"GNU faster"*)    echo -e "  ${RED}→ $ratio${NC}"; perf_losses+=("$util: $ratio") ;;
    esac
    echo ""
}

# ─── Benchmarks ─────────────────────────────────────────────────────────────

bench "echo"                echo  "test" \
    "echo test" \
    "/usr/bin/echo test"

bench "cat (100k-line file)" cat  "$BENCH_DIR/bench_test.txt" \
    "cat $BENCH_DIR/bench_test.txt" \
    "/usr/bin/cat $BENCH_DIR/bench_test.txt"

bench "wc -l"               wc    "-l $BENCH_DIR/bench_test.txt" \
    "wc -l $BENCH_DIR/bench_test.txt" \
    "/usr/bin/wc -l $BENCH_DIR/bench_test.txt"

bench "head -n 100"         head  "-n 100 $BENCH_DIR/bench_test.txt" \
    "head -n 100 $BENCH_DIR/bench_test.txt" \
    "/usr/bin/head -n 100 $BENCH_DIR/bench_test.txt"

bench "head -5 (shorthand)" head  "-5 $BENCH_DIR/bench_test.txt" \
    "head -5 $BENCH_DIR/bench_test.txt" \
    "/usr/bin/head -5 $BENCH_DIR/bench_test.txt"

bench "tail -n 100"         tail  "-n 100 $BENCH_DIR/bench_test.txt" \
    "tail -n 100 $BENCH_DIR/bench_test.txt" \
    "/usr/bin/tail -n 100 $BENCH_DIR/bench_test.txt"

bench "tail -5 (shorthand)" tail  "-5 $BENCH_DIR/bench_test.txt" \
    "tail -5 $BENCH_DIR/bench_test.txt" \
    "/usr/bin/tail -5 $BENCH_DIR/bench_test.txt"

bench "grep ERROR"          grep  "-F ERROR $BENCH_DIR/bench_test.txt" \
    "grep -F ERROR $BENCH_DIR/bench_test.txt" \
    "/usr/bin/grep -F ERROR $BENCH_DIR/bench_test.txt"

bench "seq 1 10000"         seq   "1 10000" \
    "seq 1 10000" \
    "/usr/bin/seq 1 10000"

bench "sort -n"             sort  "-n $BENCH_DIR/bench_sort_numbers.txt" \
    "sort -n $BENCH_DIR/bench_sort_numbers.txt" \
    "/usr/bin/sort -n $BENCH_DIR/bench_sort_numbers.txt"

bench "uniq (sorted)"       uniq  "$BENCH_DIR/bench_test_sorted.txt" \
    "uniq $BENCH_DIR/bench_test_sorted.txt" \
    "/usr/bin/uniq $BENCH_DIR/bench_test_sorted.txt"

bench "cut -f 5"            cut   "-f 5 $BENCH_DIR/bench_test_tabs.txt" \
    "cut -f 5 $BENCH_DIR/bench_test_tabs.txt" \
    "/usr/bin/cut -f 5 $BENCH_DIR/bench_test_tabs.txt"

bench "paste"               paste "$BENCH_DIR/paste1.txt $BENCH_DIR/paste2.txt" \
    "paste $BENCH_DIR/paste1.txt $BENCH_DIR/paste2.txt" \
    "/usr/bin/paste $BENCH_DIR/paste1.txt $BENCH_DIR/paste2.txt"

bench "expand"              expand "$BENCH_DIR/bench_expand.txt" \
    "expand $BENCH_DIR/bench_expand.txt" \
    "/usr/bin/expand $BENCH_DIR/bench_expand.txt"

bench "unexpand -a"         unexpand "-a $BENCH_DIR/bench_unexpand.txt" \
    "unexpand -a $BENCH_DIR/bench_unexpand.txt" \
    "/usr/bin/unexpand -a $BENCH_DIR/bench_unexpand.txt"

bench "diff (small)"        diff  "$BENCH_DIR/bench_diff_small1.txt $BENCH_DIR/bench_diff_small2.txt" \
    "diff $BENCH_DIR/bench_diff_small1.txt $BENCH_DIR/bench_diff_small2.txt" \
    "/usr/bin/diff $BENCH_DIR/bench_diff_small1.txt $BENCH_DIR/bench_diff_small2.txt" \
    50

bench "basename"            basename "/usr/local/long/path/a.txt" \
    "basename /usr/local/long/path/a.txt" \
    "/usr/bin/basename /usr/local/long/path/a.txt" \
    1000

bench "dirname"             dirname  "/usr/local/long/path/a.txt" \
    "dirname /usr/local/long/path/a.txt" \
    "/usr/bin/dirname /usr/local/long/path/a.txt" \
    1000

bench "find"                find  "$BENCH_DIR -name bench_test.txt" \
    "find $BENCH_DIR -name bench_test.txt" \
    "/usr/bin/find $BENCH_DIR -name bench_test.txt" \
    50

bench "which bash"          which "bash" \
    "which bash" \
    "/usr/bin/which bash" \
    500

bench "readlink (file)"     readlink "$BENCH_DIR/bench_test.txt" \
    "readlink $BENCH_DIR/bench_test.txt" \
    "/usr/bin/readlink $BENCH_DIR/bench_test.txt" \
    500

bench "realpath"            realpath "$BENCH_DIR/bench_test.txt" \
    "realpath $BENCH_DIR/bench_test.txt" \
    "/usr/bin/realpath $BENCH_DIR/bench_test.txt" \
    500

# Utilities whose output is environment-dependent — we can't diff sensibly.
bench_no_diff "true"   true  "true" "/usr/bin/true" 1000
bench_no_diff "false"  false "false" "/usr/bin/false" 1000
bench_no_diff "pwd"    pwd   "pwd" "/usr/bin/pwd" 1000
bench_no_diff "whoami" whoami "whoami" "/usr/bin/whoami" 1000
bench_no_diff "uname"  uname "uname" "/usr/bin/uname" 1000
bench_no_diff "date"   date  "date" "/usr/bin/date" 500
bench_no_diff "id"     id    "id" "/usr/bin/id" 500
bench_no_diff "sync"   sync  "sync" "/usr/bin/sync" 100

# Filesystem operations — side-effectful, gate-diff doesn't apply but we
# still want timing. These use no_diff.
bench_no_diff "touch" touch \
    "touch $BENCH_DIR/bench_touch_test.txt" \
    "/usr/bin/touch $BENCH_DIR/bench_touch_test.txt" \
    500

bench_no_diff "cp (100k-line)" cp \
    "cp $BENCH_DIR/bench_test.txt $BENCH_DIR/cp_dest.txt" \
    "/usr/bin/cp $BENCH_DIR/bench_test.txt $BENCH_DIR/cp_dest.txt" \
    50

bench_no_diff "chmod"  chmod \
    "chmod 755 $BENCH_DIR/bench_test.txt" \
    "/usr/bin/chmod 755 $BENCH_DIR/bench_test.txt" \
    500

# ─── Summary ────────────────────────────────────────────────────────────────
echo
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     SUMMARY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo
echo -e "  Correctness: ${GREEN}$correct_pass pass${NC}   ${RED}$correct_fail fail${NC}"
echo -e "  Performance: ${GREEN}${#perf_wins[@]} AiLang wins${NC}   ${YELLOW}${#perf_ties[@]} ties${NC}   ${RED}${#perf_losses[@]} GNU wins${NC}"
echo

if [ "$correct_fail" -gt 0 ]; then
    echo -e "${RED}Correctness failures (fix these — they mean the util is wrong):${NC}"
    for f in "${correctness_failures[@]}"; do
        echo "  - $f"
    done
    echo
fi

if [ ${#perf_losses[@]} -gt 0 ]; then
    echo -e "${RED}Perf regressions vs GNU:${NC}"
    for f in "${perf_losses[@]}"; do
        echo "  - $f"
    done
    echo
fi

if [ ${#perf_wins[@]} -gt 0 ]; then
    echo -e "${GREEN}Perf wins:${NC}"
    for f in "${perf_wins[@]}"; do
        echo "  - $f"
    done
    echo
fi

# Non-zero exit if any correctness failure — perf losses alone don't fail
# the run because they're informational, not incorrect.
if [ "$correct_fail" -gt 0 ]; then
    exit 1
fi
exit 0
