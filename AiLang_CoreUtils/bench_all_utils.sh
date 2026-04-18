#!/bin/bash
# bench_all_utils.sh - Benchmark installed AILANG utilities (FIXED)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     AILANG CoreUtils Performance Benchmark${NC}"
echo -e "${BLUE}     (Testing installed binaries in PATH)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Create a unique temporary directory for all test data
BENCH_DIR=$(mktemp -d -t ailang_bench_XXXXXX)

# Cleanup function to remove the temp directory on exit
cleanup() {
    rm -rf "$BENCH_DIR"
}
trap cleanup EXIT

echo -e "${YELLOW}Generating test data in $BENCH_DIR...${NC}"

# Main test file (100k lines)
for i in $(seq 1 100000); do
    if [ $((i % 100)) -eq 0 ]; then
        echo "INFO: Processing record $i - ERROR: A rare event occurred."
    else
        echo "INFO: Processing record $i - Status OK, data is normal."
    fi
done > "$BENCH_DIR/bench_test.txt"

# Create a tab-delimited version for cut
cat "$BENCH_DIR/bench_test.txt" | tr ' ' '\t' > "$BENCH_DIR/bench_test_tabs.txt"
seq 1 10000 | shuf > "$BENCH_DIR/bench_sort_numbers.txt"

# Create a sorted version for uniq
sort "$BENCH_DIR/bench_test.txt" > "$BENCH_DIR/bench_test_sorted.txt"

# Create slightly different files for diff
cp "$BENCH_DIR/bench_test.txt" "$BENCH_DIR/bench_diff1.txt"
cp "$BENCH_DIR/bench_test.txt" "$BENCH_DIR/bench_diff2.txt"
echo "This is an extra line for diffing" >> "$BENCH_DIR/bench_diff2.txt"

# Create smaller files for diff benchmark to avoid memory exhaustion
head -n 100 "$BENCH_DIR/bench_diff1.txt" > "$BENCH_DIR/bench_diff_small1.txt"
head -n 100 "$BENCH_DIR/bench_diff2.txt" > "$BENCH_DIR/bench_diff_small2.txt"

# Create files for paste, expand, unexpand
seq 1 1000 > "$BENCH_DIR/paste1.txt"
seq 1001 2000 > "$BENCH_DIR/paste2.txt"
echo -e "        eight spaces" > "$BENCH_DIR/bench_unexpand.txt"
echo -e "one\ttwo\tthree" > "$BENCH_DIR/bench_expand.txt"

# Create a temporary directory structure for the 'du' benchmark
mkdir -p "$BENCH_DIR/bench_du_dir/subdir"
dd if=/dev/urandom of="$BENCH_DIR/bench_du_dir/file1.dat" bs=1K count=10 >/dev/null 2>&1
dd if=/dev/urandom of="$BENCH_DIR/bench_du_dir/subdir/file2.dat" bs=1K count=20 >/dev/null 2>&1


# Check if AILANG utils are in PATH
if command -v head_ailang >/dev/null 2>&1; then
    echo -e "${GREEN}✓ AILANG utilities are available in PATH${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠ AILANG utilities not found. Run: ./install_ailang_utils.sh${NC}"
    echo ""
fi

# Function to benchmark - uses PATH versions
bench() {
    local label=$1        # Display label (can include notes like "1000x")
    local util=$2         # Actual utility name for path lookup
    local ailang_cmd=$3
    local gnu_cmd=$4
    local iterations=${5:-100}
    
    echo -e "${YELLOW}$label${NC}"
    
    # FIXED: Use actual util name for path lookup, not the label
    # Use `command -v` for a robust, PATH-based lookup.
    # This correctly finds utilities like 'which' that may not be in /bin or /usr/bin.
    local system_util_path=$(command -v "$util")
    
    if [ -z "$system_util_path" ]; then
        echo -e "  ${RED}✗ Could not find system version of '$util'. Skipping GNU benchmark.${NC}"
        echo ""
        return
    fi
    
    # Use installed version (from PATH - could be AILANG or system)
    { time for i in $(seq 1 $iterations); do eval "$ailang_cmd" > /dev/null 2>&1; done; } 2> "$BENCH_DIR/ailang_time.log"
    ailang_time=$(grep real "$BENCH_DIR/ailang_time.log" | awk '{print $2}')
    
    # Use system version (full path to avoid any AILANG version)
    # For nohup, we need to wait for the background process to finish
    if [ "$util" == "nohup" ]; then
        { time for i in $(seq 1 $iterations); do eval "$system_util_path ${gnu_cmd#* }" > /dev/null 2>&1; wait; done; } 2> "$BENCH_DIR/gnu_time.log"
    else
        { time for i in $(seq 1 $iterations); do eval "$system_util_path ${gnu_cmd#* }" > /dev/null 2>&1; done; } 2> "$BENCH_DIR/gnu_time.log"
    fi
    gnu_time=$(grep real "$BENCH_DIR/gnu_time.log" | awk '{print $2}')
    
    echo "  AILANG: $ailang_time"
    echo "  GNU:    $gnu_time"
    
    # Parse times (handle both 0m0.123s and 0.123s formats)
    ailang_ms=$(echo $ailang_time | sed 's/[ms]//g' | awk -F'[m.]' '{if (NF==3) print $1*60000+$2*1000+$3; else print $1*1000+$2}')
    gnu_ms=$(echo $gnu_time | sed 's/[ms]//g' | awk -F'[m.]' '{if (NF==3) print $1*60000+$2*1000+$3; else print $1*1000+$2}')
    
    # Handle empty/zero values
    [ -z "$ailang_ms" ] && ailang_ms=1
    [ -z "$gnu_ms" ] && gnu_ms=1
    [ "$ailang_ms" -eq 0 ] && ailang_ms=1
    [ "$gnu_ms" -eq 0 ] && gnu_ms=1
    
    if [ $ailang_ms -lt $gnu_ms ]; then
        ratio=$(awk "BEGIN {printf \"%.2f\", $gnu_ms / $ailang_ms}")
        echo -e "  ${GREEN}✓ AILANG ${ratio}x faster${NC}"
    elif [ $ailang_ms -eq $gnu_ms ]; then
        echo -e "  ${YELLOW}≈ TIE${NC}"
    else
        ratio=$(awk "BEGIN {printf \"%.2f\", $ailang_ms / $gnu_ms}")
        echo -e "  ${RED}✗ GNU ${ratio}x faster${NC}"
    fi
    echo ""
}

# Benchmark - use commands as they would be used normally
bench "echo" "echo" \
    "echo test" \
    "echo test"

bench "cat" "cat" \
    "cat $BENCH_DIR/bench_test.txt" \
    "cat $BENCH_DIR/bench_test.txt"

bench "wc" "wc" \
    "wc $BENCH_DIR/bench_test.txt" \
    "wc $BENCH_DIR/bench_test.txt"

bench "head" "head" \
    "head $BENCH_DIR/bench_test.txt" \
    "head $BENCH_DIR/bench_test.txt"

bench "tail" "tail" \
    "tail $BENCH_DIR/bench_test.txt" \
    "tail $BENCH_DIR/bench_test.txt"

bench "grep" "grep" \
    "grep 'ERROR' $BENCH_DIR/bench_test.txt" \
    "grep -F 'ERROR' $BENCH_DIR/bench_test.txt"

bench "seq" "seq" \
    "seq 1 10000" \
    "seq 1 10000"

bench "true (1000x)" "true" \
    "true" \
    "true" \
    1000

bench "false (1000x)" "false" \
    "false" \
    "false" \
    1000

bench "basename (1000x)" "basename" \
    "basename /usr/local/very/long/path/to/a/file.txt" \
    "basename /usr/local/very/long/path/to/a/file.txt" \
    1000

bench "dirname (1000x)" "dirname" \
    "dirname /usr/local/very/long/path/to/a/file.txt" \
    "dirname /usr/local/very/long/path/to/a/file.txt" \
    1000

bench "sleep" "sleep" \
    "sleep 0.01" \
    "sleep 0.01" \
    100

bench "touch (1000x)" "touch" \
    "touch $BENCH_DIR/bench_touch_test.txt" \
    "touch $BENCH_DIR/bench_touch_test.txt" \
    1000

bench "pwd (1000x)" "pwd" \
    "pwd" \
    "pwd" \
    1000

bench "whoami (1000x)" "whoami" \
    "whoami" \
    "whoami" \
    1000

bench "env (1000x)" "env" \
    "env" \
    "env" \
    1000

bench "cut" "cut" \
    "cut -f 5 $BENCH_DIR/bench_test_tabs.txt" \
    "cut -f 5 $BENCH_DIR/bench_test_tabs.txt"

#bench "tee" "tee" \
#    "cat $BENCH_DIR/bench_test.txt | tee $BENCH_DIR/tee_test_output.txt" \
#    "cat $BENCH_DIR/bench_test.txt | tee $BENCH_DIR/tee_test_output.txt" \
#    10

bench "uniq" "uniq" \
    "uniq $BENCH_DIR/bench_test_sorted.txt" \
    "uniq $BENCH_DIR/bench_test_sorted.txt"

bench "logname (1000x)" "logname" \
    "logname" \
    "logname" \
    1000

bench "id (1000x)" "id" \
    "id" \
    "id" \
    1000

bench "printenv (1000x)" "printenv" \
    "printenv" \
    "printenv" \
    1000

bench "uname (1000x)" "uname" \
    "uname" \
    "uname" \
    1000

bench "find" "find" \
    "find . -name '*.py'" \
    "find . -name '*.py'" \
    10

bench "sort" "sort" \
    "sort -n $BENCH_DIR/bench_sort_numbers.txt" \
    "sort -n $BENCH_DIR/bench_sort_numbers.txt"

bench "diff (small)" "diff" \
    "diff $BENCH_DIR/bench_diff_small1.txt $BENCH_DIR/bench_diff_small2.txt" \
    "diff $BENCH_DIR/bench_diff_small1.txt $BENCH_DIR/bench_diff_small2.txt"

bench "cp" "cp" \
    "cp $BENCH_DIR/bench_test.txt $BENCH_DIR/cp_test_dest.txt" \
    "cp $BENCH_DIR/bench_test.txt $BENCH_DIR/cp_test_dest.txt" \
    10

bench "mkdir (1000x)" "mkdir" \
    "mkdir -p $BENCH_DIR/bench_mkdir_test_\$i" \
    "mkdir -p $BENCH_DIR/bench_mkdir_test_\$i" \
    1000

bench "rm (1000x)" "rm" \
    "rm -f $BENCH_DIR/bench_rm_test_\$i" \
    "rm -f $BENCH_DIR/bench_rm_test_\$i" \
    1000

bench "ln (1000x)" "ln" \
    "ln -sf $BENCH_DIR/bench_test.txt $BENCH_DIR/bench_ln_test_\$i" \
    "ln -sf $BENCH_DIR/bench_test.txt $BENCH_DIR/bench_ln_test_\$i" \
    1000

bench "file (1000x)" "file" \
    "file $BENCH_DIR/bench_test.txt" \
    "file $BENCH_DIR/bench_test.txt" \
    1000

bench "chmod (1000x)" "chmod" \
    "chmod 755 $BENCH_DIR/bench_test.txt" \
    "chmod 755 $BENCH_DIR/bench_test.txt" \
    1000

bench "mv (1000x)" "mv" \
    "mv -f $BENCH_DIR/bench_mv_test_\$i $BENCH_DIR/bench_mv_test_renamed_\$i 2>/dev/null || true" \
    "mv -f $BENCH_DIR/bench_mv_test_\$i $BENCH_DIR/bench_mv_test_renamed_\$i 2>/dev/null || true" \
    1000

bench "sync (1000x)" "sync" \
    "sync" \
    "sync" \
    1000

bench "readlink (1000x)" "readlink" \
    "readlink $BENCH_DIR/bench_test.txt || true" \
    "readlink $BENCH_DIR/bench_test.txt || true" \
    1000

bench "tty (1000x)" "tty" \
    "tty" \
    "tty" \
    1000

bench "realpath (1000x)" "realpath" \
    "realpath $BENCH_DIR/bench_test.txt" \
    "realpath $BENCH_DIR/bench_test.txt" \
    1000

bench "which (1000x)" "which" \
    "which ls" \
    "which ls" \
    1000

bench "nohup (1000x)" "nohup" \
    "nohup true >/dev/null 2>&1; wait" \
    "nohup true >/dev/null 2>&1; wait" \
    1000

bench "chown (1000x)" "chown" \
    "chown \$(id -u):\$(id -g) $BENCH_DIR/bench_test.txt 2>/dev/null || true" \
    "chown \$(id -u):\$(id -g) $BENCH_DIR/bench_test.txt 2>/dev/null || true" \
    1000

bench "df (1000x)" "df" \
    "df -h" \
    "df -h" \
    1000

bench "chgrp (1000x)" "chgrp" \
    "chgrp \$(id -g) $BENCH_DIR/bench_test.txt 2>/dev/null || true" \
    "chgrp \$(id -g) $BENCH_DIR/bench_test.txt 2>/dev/null || true" \
    1000

bench "stat (1000x)" "stat" \
    "stat $BENCH_DIR/bench_test.txt" \
    "stat $BENCH_DIR/bench_test.txt" \
    1000

bench "du" "du" \
    "du -sh $BENCH_DIR/bench_du_dir" \
    "du -sh $BENCH_DIR/bench_du_dir" \
    10

bench "dd" "dd" \
    "dd if=/dev/zero of=$BENCH_DIR/bench_dd_test bs=1M count=10" \
    "dd if=/dev/zero of=$BENCH_DIR/bench_dd_test bs=1M count=10" \
    10

bench "split" "split" \
    "split -l 10000 $BENCH_DIR/bench_test.txt $BENCH_DIR/split_out_" \
    "split -l 10000 $BENCH_DIR/bench_test.txt $BENCH_DIR/split_out_" \
    10

bench "expand" "expand" \
    "expand $BENCH_DIR/bench_expand.txt" \
    "expand $BENCH_DIR/bench_expand.txt"

bench "unexpand" "unexpand" \
    "unexpand $BENCH_DIR/bench_unexpand.txt" \
    "unexpand $BENCH_DIR/bench_unexpand.txt"

bench "paste" "paste" \
    "paste $BENCH_DIR/paste1.txt $BENCH_DIR/paste2.txt" \
    "paste $BENCH_DIR/paste1.txt $BENCH_DIR/paste2.txt"

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Benchmark complete!${NC}"
echo ""
echo "These are real-world performance numbers using installed binaries."