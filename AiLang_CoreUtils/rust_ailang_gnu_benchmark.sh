#!/usr/bin/env bash
# Fixed AILANG vs GNU vs Rust uutils benchmark
# Handles _ailang suffix and symlinks correctly

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${PURPLE}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      AILANG vs GNU vs RUST uutils — November 17, 2025       ║"
echo "║                   PERFORMANCE BENCHMARK                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Create temp directory
BENCH_DIR=$(mktemp -d -t benchmark.XXXXXX)
trap 'rm -rf "$BENCH_DIR" 2>/dev/null || true' EXIT

# -------------------------------------------------
# Auto-detect AILANG installation
# -------------------------------------------------
echo -e "${CYAN}Detecting implementations...${NC}"

# Find AILANG binaries
AILANG_DIR="${AILANG_DIR:-}"  # Allow override via environment variable

if [[ -z "$AILANG_DIR" ]]; then
    for candidate in "$HOME/.local/bin/ailang" "$HOME/.ailang/bin" "/usr/local/bin/ailang" "./ailang_bin" "./dist"; do
        # Check if directory exists and has any _ailang binaries or *_exec files
        if [[ -d "$candidate" ]] && { ls "$candidate"/*_ailang >/dev/null 2>&1 || ls "$candidate"/*/*_exec >/dev/null 2>&1; }; then
            AILANG_DIR="$candidate"
            break
        fi
    done
fi

if [[ -z "$AILANG_DIR" ]]; then
    echo -e "${RED}✗ AILANG binaries not found${NC}"
    echo "  Searched: ~/.local/bin/ailang, ~/.ailang/bin, /usr/local/bin/ailang, ./ailang_bin, ./dist"
    echo ""
    echo "  Debug info:"
    echo "  - Does ~/.local/bin/ailang exist? $(test -d "$HOME/.local/bin/ailang" && echo "YES" || echo "NO")"
    if [[ -d "$HOME/.local/bin/ailang" ]]; then
        echo "  - Contents of ~/.local/bin/ailang:"
        ls -la "$HOME/.local/bin/ailang" | head -10
    fi
    if [[ -d "./dist" ]]; then
        echo "  - Contents of ./dist:"
        ls -la "./dist" | head -10
    fi
    echo ""
    echo "  Solutions:"
    echo "  1. Run './install_ailang_utils.sh' first"
    echo "  2. Set AILANG_DIR: export AILANG_DIR=/path/to/ailang/binaries"
    echo "  3. Make sure you're in the ailang project directory"
    exit 1
fi
echo -e "${GREEN}✓ AILANG: $AILANG_DIR${NC}"

# Find GNU binaries
GNU_DIR=""
for candidate in "/usr/bin" "/bin" "/usr/local/bin"; do
    if [[ -x "$candidate/grep" ]]; then
        # Verify it's GNU by checking for GNU-specific option
        if "$candidate/grep" --version 2>&1 | grep -q "GNU"; then
            GNU_DIR="$candidate"
            break
        fi
    fi
done

if [[ -z "$GNU_DIR" ]]; then
    echo -e "${YELLOW}⚠ GNU coreutils not found, using system default${NC}"
    GNU_DIR="/usr/bin"
else
    echo -e "${GREEN}✓ GNU: $GNU_DIR${NC}"
fi

# Find Rust uutils - check multiple possible names and multi-call binary
RUST_DIR=""
HAS_RUST=0
RUST_MULTICALL=""
RUST_COREUTILS_PATH="$HOME/.cargo/bin/coreutils"

# SIMPLIFIED: Check for the exact multi-call binary we know exists.
if [[ -x "$RUST_COREUTILS_PATH" ]]; then
    RUST_DIR=$(dirname "$RUST_COREUTILS_PATH")
    RUST_MULTICALL="$RUST_COREUTILS_PATH"
    HAS_RUST=1
    echo -e "${GREEN}✓ RUST: $RUST_MULTICALL (multi-call binary)${NC}"
fi

if [[ $HAS_RUST -eq 0 ]]; then
    echo -e "${YELLOW}⚠ Rust uutils not found - will compare AILANG vs GNU only${NC}"
    echo -e "${CYAN}  Checked for: $RUST_COREUTILS_PATH${NC}"
    echo -e "${CYAN}  Add ~/.cargo/bin to PATH or wait for cargo install to finish${NC}"
fi

# -------------------------------------------------
# Generate test data (SAFE method - same as test_grep.sh)
# -------------------------------------------------
echo -e "\n${CYAN}Generating test data...${NC}"

# Use same method as test_grep.sh (which works!)
for i in $(seq 1 1000); do
    if [ $((i % 100)) -eq 0 ]; then
        echo "INFO line $(printf "%06d" $i) data ERROR rare event"
    else
        echo "INFO line $(printf "%06d" $i) data OK normal"
    fi
done > "$BENCH_DIR/big.txt"

# Tab-delimited version
tr ' ' '\t' < "$BENCH_DIR/big.txt" > "$BENCH_DIR/big_tabs.txt"

# Files for paste
seq 1 1000 > "$BENCH_DIR/p1.txt"
seq 1001 2000 > "$BENCH_DIR/p2.txt"

# Sorted for uniq
sort "$BENCH_DIR/big.txt" > "$BENCH_DIR/big_sorted.txt"

# Numbers for sorting
seq 1 1000 > "$BENCH_DIR/numbers.txt"

echo -e "${GREEN}✓ Test data ready${NC}"

# -------------------------------------------------
# Helper function to find AILANG binary
# -------------------------------------------------
find_ailang_bin() {
    local util=$1
    
    # Check for direct _ailang binary
    if [[ -x "$AILANG_DIR/${util}_ailang" ]]; then
        echo "$AILANG_DIR/${util}_ailang"
        return 0
    fi
    
    # Check for binary in subdirectory (dist structure)
    if [[ -x "$AILANG_DIR/${util}_util/${util}_exec" ]]; then
        echo "$AILANG_DIR/${util}_util/${util}_exec"
        return 0
    fi
    
    # Check if symlink exists in PATH
    if [[ -L "$HOME/.local/bin/$util" ]]; then
        local target=$(readlink "$HOME/.local/bin/$util")
        if [[ -x "$target" ]]; then
            echo "$target"
            return 0
        fi
    fi
    
    return 1
}

# -------------------------------------------------
# Benchmark function with proper timing
# -------------------------------------------------
run_bench() {
    local impl_name=$1
    local impl_dir=$2
    local cmd=$3
    local iterations=$4
    
    # Extract utility name from command
    local util=$(echo "$cmd" | awk '{print $1}')
    
    # For AILANG, find the actual binary
    if [[ "$impl_name" == "AILANG" ]]; then
        local ailang_bin=$(find_ailang_bin "$util" 2>/dev/null || echo "")
        if [[ -z "$ailang_bin" ]]; then
            echo "N/A"
            return
        fi
        # Replace command with full path to AILANG binary
        cmd="${ailang_bin}${cmd#$util}"
    elif [[ "$impl_name" == "RUST" && -n "$RUST_MULTICALL" ]]; then
        # Rust multi-call binary: prepend "coreutils" to the command
        cmd="$RUST_MULTICALL $cmd"
    else
        if [[ ! -x "$impl_dir/$util" ]]; then
            echo "N/A"
            return
        fi
        # Use full path for GNU
        cmd="$impl_dir/$util${cmd#$util}"
    fi
    
    # Run benchmark
    local start=$(/usr/bin/date +%s.%N 2>/dev/null || /usr/bin/date +%s)
    for ((i=0; i<iterations; i++)); do
        eval "$cmd" >/dev/null 2>&1 || true
    done
    local end=$(/usr/bin/date +%s.%N 2>/dev/null || /usr/bin/date +%s)
    
    # Calculate elapsed time (using awk for portability)
    local elapsed=$(awk "BEGIN {printf \"%.3f\", $end - $start}")
    echo "$elapsed"
}

# -------------------------------------------------
# Run benchmarks
# -------------------------------------------------
echo -e "\n${PURPLE}${BOLD}PERFORMANCE RESULTS (seconds, lower is better)${NC}"
echo "================================================================"
printf "%-20s %12s %12s %12s\n" "TEST" "AILANG" "GNU" "RUST"
echo "----------------------------------------------------------------"

bench() {
    local name=$1
    local cmd=$2
    local iterations=${3:-10}
    
    printf "%-20s " "$name"
    
    # AILANG
    local ailang_time=$(run_bench "AILANG" "$AILANG_DIR" "$cmd" "$iterations")
    printf "%12s " "$ailang_time"
    
    # GNU
    local gnu_time=$(run_bench "GNU" "$GNU_DIR" "$cmd" "$iterations")
    printf "%12s " "$gnu_time"
    
    # Rust
    if [[ $HAS_RUST -eq 1 ]]; then
        local rust_time=$(run_bench "RUST" "$RUST_DIR" "$cmd" "$iterations")
        printf "%12s" "$rust_time"
    else
        printf "%12s" "N/A"
    fi
    
    echo ""
}

# Simple commands (run many times)
bench "echo" "echo test" 1000
bench "true" "true" 1000
bench "false" "false" 1000
bench "pwd" "pwd" 1000
bench "basename" "basename /usr/local/bin/test.txt" 1000
bench "dirname" "dirname /usr/local/bin/test.txt" 1000
bench "whoami" "whoami" 1000

# File processing (fewer iterations)
bench "cat" "cat $BENCH_DIR/big.txt" 10
bench "wc -l" "wc -l $BENCH_DIR/big.txt" 10
bench "head" "head $BENCH_DIR/big.txt" 100
bench "tail" "tail $BENCH_DIR/big.txt" 100
bench "grep" "grep ERROR $BENCH_DIR/big.txt" 10
# cut removed - hangs with file arguments (only works with stdin)
bench "uniq" "uniq $BENCH_DIR/big_sorted.txt" 10
bench "sort" "sort -n $BENCH_DIR/numbers.txt" 5
bench "paste" "paste $BENCH_DIR/p1.txt $BENCH_DIR/p2.txt" 10
bench "seq" "seq 1 10000" 10

echo "================================================================"

# -------------------------------------------------
# Correctness validation
# -------------------------------------------------
echo -e "\n${PURPLE}${BOLD}CORRECTNESS VALIDATION${NC}"
echo "================================================================"

validate() {
    local impl_name=$1
    local impl_dir=$2
    
    echo -e "\n${CYAN}Testing $impl_name:${NC}"
    
    # Test grep
    local grep_bin=""
    if [[ "$impl_name" == "AILANG" ]]; then
        grep_bin=$(find_ailang_bin "grep" 2>/dev/null || echo "")
    else
        grep_bin="$impl_dir/grep"
    fi
    
    if [[ -n "$grep_bin" && -x "$grep_bin" ]]; then
        local grep_count=$("$grep_bin" ERROR "$BENCH_DIR/big.txt" 2>/dev/null | wc -l)
        if [[ "$grep_count" -eq 10 ]]; then
            echo -e "  grep:    ${GREEN}✓ correct ($grep_count lines)${NC}"
        else
            echo -e "  grep:    ${RED}✗ WRONG ($grep_count lines, expected 10)${NC}"
        fi
    else
        echo -e "  grep:    ${YELLOW}⚠ not found${NC}"
    fi
    
    # Test wc
    local wc_bin=""
    if [[ "$impl_name" == "AILANG" ]]; then
        wc_bin=$(find_ailang_bin "wc" 2>/dev/null || echo "")
    else
        wc_bin="$impl_dir/wc"
    fi
    
    if [[ -n "$wc_bin" && -x "$wc_bin" ]]; then
        local wc_count=$("$wc_bin" -l < "$BENCH_DIR/big.txt" 2>/dev/null | tr -d ' ')
        if [[ "$wc_count" -eq 1000 ]]; then
            echo -e "  wc:      ${GREEN}✓ correct ($wc_count lines)${NC}"
        else
            echo -e "  wc:      ${RED}✗ WRONG ($wc_count lines, expected 1000)${NC}"
        fi
    else
        echo -e "  wc:      ${YELLOW}⚠ not found${NC}"
    fi
    
    # Test cat
    local cat_bin=""
    if [[ "$impl_name" == "AILANG" ]]; then
        cat_bin=$(find_ailang_bin "cat" 2>/dev/null || echo "")
    else
        cat_bin="$impl_dir/cat"
    fi
    
    if [[ -n "$cat_bin" && -x "$cat_bin" ]]; then
        local cat_lines=$("$cat_bin" "$BENCH_DIR/big.txt" 2>/dev/null | wc -l)
        if [[ "$cat_lines" -eq 1000 ]]; then
            echo -e "  cat:     ${GREEN}✓ correct ($cat_lines lines)${NC}"
        else
            echo -e "  cat:     ${RED}✗ WRONG ($cat_lines lines)${NC}"
        fi
    else
        echo -e "  cat:     ${YELLOW}⚠ not found${NC}"
    fi
}

validate "AILANG" "$AILANG_DIR"
validate "GNU" "$GNU_DIR"
if [[ $HAS_RUST -eq 1 ]]; then
    if [[ -n "$RUST_MULTICALL" ]]; then
        # Special validation for multi-call binary
        echo -e "\n${CYAN}Testing RUST:${NC}"
        
        # Test grep
        grep_count=$("$RUST_MULTICALL" grep ERROR "$BENCH_DIR/big.txt" 2>/dev/null | wc -l)
        if [[ "$grep_count" -eq 10 ]]; then
            echo -e "  grep:    ${GREEN}✓ correct ($grep_count lines)${NC}"
        else
            echo -e "  grep:    ${RED}✗ WRONG ($grep_count lines, expected 10)${NC}"
        fi
        
        # Test wc
        wc_count=$("$RUST_MULTICALL" wc -l < "$BENCH_DIR/big.txt" 2>/dev/null | tr -d ' ')
        if [[ "$wc_count" -eq 1000 ]]; then
            echo -e "  wc:      ${GREEN}✓ correct ($wc_count lines)${NC}"
        else
            echo -e "  wc:      ${RED}✗ WRONG ($wc_count lines, expected 1000)${NC}"
        fi
        
        # Test cat
        cat_lines=$("$RUST_MULTICALL" cat "$BENCH_DIR/big.txt" 2>/dev/null | wc -l)
        if [[ "$cat_lines" -eq 1000 ]]; then
            echo -e "  cat:     ${GREEN}✓ correct ($cat_lines lines)${NC}"
        else
            echo -e "  cat:     ${RED}✗ WRONG ($cat_lines lines)${NC}"
        fi
    else
        validate "RUST" "$RUST_DIR"
    fi
fi

echo -e "\n${PURPLE}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}${BOLD}║                   BENCHMARK COMPLETE                         ║${NC}"
echo -e "${PURPLE}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "${CYAN}Temp files cleaned up: $BENCH_DIR${NC}"
echo ""
echo -e "${YELLOW}Tips:${NC}"
echo "  - Lower numbers are better"
echo "  - Run 'ailang-utils status' to see what's installed"
echo "  - Set AILANG_DIR=/custom/path to benchmark different installation"