#!/bin/bash
# Realistic grep benchmark - focus on actual source code sizes

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

RUN_STRACE=false
[ "$1" == "--strace" ] && RUN_STRACE=true


echo -e "${CYAN}${BOLD}REALISTIC GREP BENCHMARK${NC}"
echo "Testing typical source code file sizes (100-5000 lines)"
echo "════════════════════════════════════════════════════════════════"
echo ""

TEST_DIR=$(mktemp -d)
SYSCALL_LOG=$(mktemp)
trap "rm -rf $TEST_DIR $SYSCALL_LOG" EXIT

AILANG_GREP="$HOME/.local/bin/ailang/grep_ailang"
GNU_GREP="/usr/bin/grep"
RUST_GREP="$HOME/.cargo/bin/coreutils"

echo -e "${YELLOW}Generating realistic test files...${NC}"

# 100 lines (small utility script)
for i in $(seq 1 100); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/100.txt"

# 500 lines (medium source file)
for i in $(seq 1 500); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/500.txt"

# 1000 lines (large source file)
for i in $(seq 1 1000); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/1000.txt"

# 2500 lines (very large source file)
for i in $(seq 1 2500); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/2500.txt"

# 5000 lines (huge source file - rare)
for i in $(seq 1 5000); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/5000.txt"

# 10k lines
for i in $(seq 1 10000); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/10000.txt"

# 15k lines
for i in $(seq 1 15000); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/15000.txt"

# 25k lines
for i in $(seq 1 25000); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/25000.txt"

# 50k lines
for i in $(seq 1 50000); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/50000.txt"

# 75k lines (approaching dictionary size)
for i in $(seq 1 75000); do
    if [ $((i % 10)) -eq 0 ]; then
        echo "    if (error) { handle_error(); }"
    else
        echo "    process_data(item[$i]);"
    fi
done > "$TEST_DIR/75000.txt"

echo -e "${GREEN}✓ Test files ready${NC}"
echo ""

bench_grep() {
    local name="$1"
    local file="$2"
    local iterations="$3"

    printf "%-25s " "$name"

    # AILANG
    start=$(/usr/bin/date +%s.%N)
    for i in $(seq 1 $iterations); do
        "$AILANG_GREP" error "$file" >/dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    ailang_time=$(awk "BEGIN {printf \"%.4f\", $end - $start}")
    printf "%10s " "$ailang_time"

    # GNU
    start=$(/usr/bin/date +%s.%N)
    for i in $(seq 1 $iterations); do
        "$GNU_GREP" error "$file" >/dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    gnu_time=$(awk "BEGIN {printf \"%.4f\", $end - $start}")
    printf "%10s " "$gnu_time"

    # Rust
    start=$(/usr/bin/date +%s.%N)
    for i in $(seq 1 $iterations); do
        "$RUST_GREP" grep error "$file" >/dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    rust_time=$(awk "BEGIN {printf \"%.4f\", $end - $start}")
    printf "%10s " "$rust_time"

    # Winner
    if (( $(echo "$ailang_time < $gnu_time && $ailang_time < $rust_time" | bc -l) )); then
        printf "  ${GREEN}🥇 AILANG WINS${NC}"
    elif (( $(echo "$gnu_time < $rust_time" | bc -l) )); then
        speedup=$(awk "BEGIN {printf \"%.2f\", $ailang_time / $gnu_time}")
        printf "  ${YELLOW}GNU wins (AILANG ${speedup}x)${NC}"
    else
        speedup=$(awk "BEGIN {printf \"%.2f\", $ailang_time / $rust_time}")
        printf "  ${YELLOW}Rust wins (AILANG ${speedup}x)${NC}"
    fi
    
    echo ""

    # Optional: Run strace for detailed syscall analysis
    if [ "$RUN_STRACE" = true ]; then
        # AWK script to count occurrences of mmap, read, and openat
        local awk_script='/mmap/ {m++} /read/ {r++} /openat/ {o++} END { printf "%d/%d/%d", m, r, o }'

        # Use timeout to prevent hangs, redirect stderr to stdout to capture strace output
        ailang_syscalls=$( { timeout 2 strace -e trace=mmap,read,openat "$AILANG_GREP" error "$file" >/dev/null; } 2>&1 | awk "$awk_script")
        gnu_syscalls=$( { timeout 2 strace -e trace=mmap,read,openat "$GNU_GREP" error "$file" >/dev/null; } 2>&1 | awk "$awk_script")
        rust_syscalls=$( { timeout 2 strace -e trace=mmap,read,openat "$RUST_GREP" grep error "$file" >/dev/null; } 2>&1 | awk "$awk_script")

        # Write data to log file, using tabs as a delimiter
        echo -e "$name\t${ailang_syscalls:-N/A}\t${gnu_syscalls:-N/A}\t${rust_syscalls:-N/A}" >> "$SYSCALL_LOG"
    fi
}

bench_dict() {
    local name="$1"
    local file="$2"
    local num_words="$3"
    # List of 10 common words to search for
    local all_words=("the" "of" "and" "to" "in" "is" "you" "that" "it" "for")
    # Slice the array to get the desired number of words
    local words=("${all_words[@]:0:$num_words}")

    if [ ! -f "$file" ]; then
        printf "%-25s ${RED}File not found: %s${NC}\n" "$name" "$file"
        return
    fi

    printf "%-25s " "$name"

    # AILANG
    start=$(/usr/bin/date +%s.%N)
    for word in "${words[@]}"; do
        "$AILANG_GREP" "$word" "$file" >/dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    ailang_time=$(awk "BEGIN {printf \"%.4f\", $end - $start}")
    printf "%10s " "$ailang_time"

    # GNU
    start=$(/usr/bin/date +%s.%N)
    for word in "${words[@]}"; do
        "$GNU_GREP" "$word" "$file" >/dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    gnu_time=$(awk "BEGIN {printf \"%.4f\", $end - $start}")
    printf "%10s " "$gnu_time"

    # Rust
    start=$(/usr/bin/date +%s.%N)
    for word in "${words[@]}"; do
        "$RUST_GREP" grep "$word" "$file" >/dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    rust_time=$(awk "BEGIN {printf \"%.4f\", $end - $start}")
    printf "%10s " "$rust_time"

    # Winner
    if (( $(echo "$ailang_time < $gnu_time && $ailang_time < $rust_time" | bc -l) )); then
        printf "  ${GREEN}🥇 AILANG WINS${NC}"
    elif (( $(echo "$gnu_time < $rust_time" | bc -l) )); then
        speedup=$(awk "BEGIN {printf \"%.2f\", $ailang_time / $gnu_time}")
        printf "  ${YELLOW}GNU wins (AILANG ${speedup}x)${NC}"
    else
        speedup=$(awk "BEGIN {printf \"%.2f\", $ailang_time / $rust_time}")
        printf "  ${YELLOW}Rust wins (AILANG ${speedup}x)${NC}"
    fi

    echo ""

    # Optional: Run strace for detailed syscall analysis
    if [ "$RUN_STRACE" = true ]; then
        local awk_script='/mmap/ {m++} /read/ {r++} /openat/ {o++} END { printf "%d/%d/%d", m, r, o }'

        # For the dictionary test, we trace just one word search
        ailang_syscalls=$( { timeout 2 strace -e trace=mmap,read,openat "$AILANG_GREP" "the" "$file" >/dev/null; } 2>&1 | awk "$awk_script")
        gnu_syscalls=$( { timeout 2 strace -e trace=mmap,read,openat "$GNU_GREP" "the" "$file" >/dev/null; } 2>&1 | awk "$awk_script")
        rust_syscalls=$( { timeout 2 strace -e trace=mmap,read,openat "$RUST_GREP" grep "the" "$file" >/dev/null; } 2>&1 | awk "$awk_script")

        # Write data to log file
        echo -e "$name\t${ailang_syscalls:-N/A}\t${gnu_syscalls:-N/A}\t${rust_syscalls:-N/A}" >> "$SYSCALL_LOG"
    fi
}

bench_recursive() {
    local name="$1"
    # The second argument is a space-separated string of words
    local words_str="$2"
    # Convert the string to an array
    local words=($words_str)
    local search_dir="." # Search the current directory

    # Add a header for the match count
    local header_name="${name/Recursive/Matches for}"
    printf "%-25s %10s %10s %10s\n" "$header_name" "AILANG" "GNU" "RUST"

    printf "%-25s " "$name"

    # AILANG
    start=$(/usr/bin/date +%s.%N)
    for word in "${words[@]}"; do
        "$AILANG_GREP" -r --include='*.ailang' "$word" "$search_dir" >/dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    ailang_time=$(awk "BEGIN {printf \"%.4f\", $end - $start}")
    printf "%10s " "$ailang_time"
    # Correctly count matches by iterating, same as the timing loop
    local ailang_matches=0
    for word in "${words[@]}"; do
        ailang_matches=$((ailang_matches + $("$AILANG_GREP" -r --include='*.ailang' "$word" "$search_dir" 2>/dev/null | wc -l)))
    done

    # GNU
    start=$(/usr/bin/date +%s.%N)
    for word in "${words[@]}"; do
        "$GNU_GREP" -r --include='*.ailang' "$word" "$search_dir" >/dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    gnu_time=$(awk "BEGIN {printf \"%.4f\", $end - $start}")
    printf "%10s " "$gnu_time"
    local gnu_matches=0
    for word in "${words[@]}"; do
        gnu_matches=$((gnu_matches + $("$GNU_GREP" -r --include='*.ailang' "$word" "$search_dir" 2>/dev/null | wc -l)))
    done

    # Rust
    start=$(/usr/bin/date +%s.%N)
    for word in "${words[@]}"; do
        "$RUST_GREP" grep -r --include='*.ailang' "$word" "$search_dir" >/dev/null 2>&1
    done
    end=$(/usr/bin/date +%s.%N)
    rust_time=$(awk "BEGIN {printf \"%.4f\", $end - $start}")
    printf "%10s " "$rust_time"
    local rust_matches=0
    for word in "${words[@]}"; do
        rust_matches=$((rust_matches + $("$RUST_GREP" grep -r --include='*.ailang' "$word" "$search_dir" 2>/dev/null | wc -l)))
    done

    # Winner
    if (( $(echo "$ailang_time < $gnu_time && $ailang_time < $rust_time" | bc -l) )); then
        printf "  ${GREEN}🥇 AILANG WINS${NC}"
    elif (( $(echo "$gnu_time < $rust_time" | bc -l) )); then
        speedup=$(awk "BEGIN {printf \"%.2f\", $ailang_time / $gnu_time}")
        printf "  ${YELLOW}GNU wins (AILANG ${speedup}x)${NC}"
    else
        speedup=$(awk "BEGIN {printf \"%.2f\", $ailang_time / $rust_time}")
        printf "  ${YELLOW}Rust wins (AILANG ${speedup}x)${NC}"
    fi

    echo ""
    # Print the match counts on a new line
    printf "%-25s %10s %10s %10s\n" "" "($ailang_matches)" "($gnu_matches)" "($rust_matches)"

}

analyze_recursive_scope() {
    echo ""
    echo "────────────────────────────────────────────────────────────────"
    echo -e "${CYAN}${BOLD}Recursive Search Scope Analysis${NC}"
    echo "════════════════════════════════════════════════════════════════"
    echo "Counting unique files each utility finds a match in."
    echo "A common word ('the') is used to maximize file hits."
    echo "────────────────────────────────────────────────────────────────"
    printf "%-25s %10s\n" "UTILITY" "FILES SEARCHED"
    echo "────────────────────────────────────────────────────────────────"

    # AILANG
    local ailang_files=$("$AILANG_GREP" -rl "the" "." 2>/dev/null | wc -l | tr -d ' ')
    printf "%-25s %10s\n" "AILANG" "$ailang_files"

    # GNU
    local gnu_files=$("$GNU_GREP" -rl "the" "." 2>/dev/null | wc -l | tr -d ' ')
    printf "%-25s %10s\n" "GNU" "$gnu_files"

    # Rust
    local rust_files=$("$RUST_GREP" grep -rl "the" "." 2>/dev/null | wc -l | tr -d ' ')
    printf "%-25s %10s\n" "RUST" "$rust_files"

    echo "════════════════════════════════════════════════════════════════"
}

print_syscall_summary() {
    if [ "$RUN_STRACE" = true ] && [ -s "$SYSCALL_LOG" ]; then
        echo ""
        echo "────────────────────────────────────────────────────────────────"
        echo -e "${CYAN}${BOLD}SYSCALL SUMMARY (mmap/read/openat calls)${NC}"
        echo "════════════════════════════════════════════════════════════════"
        
        # Create a header and pipe it along with the log file to column
        # This ensures the header and body are formatted together for perfect alignment.
        (
            echo -e "TEST\tAILANG\tGNU\tRUST"
            echo -e "───────────────────────────────\t──────────\t───\t────"
            cat "$SYSCALL_LOG"
        ) | column -t -s $'\t'
        
        echo "════════════════════════════════════════════════════════════════"
    fi
}

print_file_size_summary() {
    echo ""
    echo "────────────────────────────────────────────────────────────────"
    echo -e "${CYAN}${BOLD}TEST FILE METADATA${NC}"
    echo "════════════════════════════════════════════════════════════════"
    printf "%-25s %10s\n" "FILE" "SIZE"
    echo "────────────────────────────────────────────────────────────────"

    local test_files=("$TEST_DIR"/*.txt "dictionary.txt")
    for file in "${test_files[@]}"; do
        if [ -f "$file" ]; then
            local size_bytes=$(wc -c < "$file")
            local size_human=$(numfmt --to=iec-i --suffix=B --format="%.1f" "$size_bytes")
            printf "%-25s %10s\n" "$(basename "$file")" "$size_human"
        fi
    done
    echo "════════════════════════════════════════════════════════════════"
}


echo -e "${CYAN}${BOLD}RESULTS (seconds, lower is better)${NC}"
echo "════════════════════════════════════════════════════════════════"
printf "%-25s %10s %10s %10s\n" "TEST" "AILANG" "GNU" "RUST"
echo "────────────────────────────────────────────────────────────────"

# Small files - LOTS of iterations (simulates grepping through many small files)
bench_grep "100 lines × 1000" "$TEST_DIR/100.txt" 1000
bench_grep "100 lines × 500" "$TEST_DIR/100.txt" 500
bench_grep "500 lines × 500" "$TEST_DIR/500.txt" 500
bench_grep "500 lines × 200" "$TEST_DIR/500.txt" 200

# Medium files - moderate iterations (typical development workflow)
bench_grep "1000 lines × 200" "$TEST_DIR/1000.txt" 200
bench_grep "1000 lines × 100" "$TEST_DIR/1000.txt" 100
bench_grep "2500 lines × 100" "$TEST_DIR/2500.txt" 100
bench_grep "2500 lines × 50" "$TEST_DIR/2500.txt" 50

# Large files - fewer iterations (edge case)
bench_grep "5000 lines × 50" "$TEST_DIR/5000.txt" 50
bench_grep "5000 lines × 20" "$TEST_DIR/5000.txt" 20

echo "────────────────────────────────────────────────────────────────"
echo -e "${CYAN}${BOLD}Larger Files (approaching log file sizes)${NC}"
echo "────────────────────────────────────────────────────────────────"

bench_grep "10k lines × 10" "$TEST_DIR/10000.txt" 10
bench_grep "15k lines × 8" "$TEST_DIR/15000.txt" 8
bench_grep "25k lines × 5" "$TEST_DIR/25000.txt" 5

echo "────────────────────────────────────────────────────────────────"
echo -e "${CYAN}${BOLD}Very Large Files (outlier territory)${NC}"
echo "────────────────────────────────────────────────────────────────"

bench_grep "50k lines × 2" "$TEST_DIR/50000.txt" 2
bench_grep "75k lines × 2" "$TEST_DIR/75000.txt" 2

echo "────────────────────────────────────────────────────────────────"
echo -e "${CYAN}${BOLD}Dictionary Search${NC}"
echo "────────────────────────────────────────────────────────────────"

bench_dict "Dict Search (1 word)" "dictionary.txt" 1
bench_dict "Dict Search (2 words)" "dictionary.txt" 2
bench_dict "Dict Search (5 words)" "dictionary.txt" 5
bench_dict "Dict Search (10 words)" "dictionary.txt" 10

echo "────────────────────────────────────────────────────────────────"
echo -e "${CYAN}${BOLD}Recursive Search (Unscripted Project Dir)${NC}"
echo "────────────────────────────────────────────────────────────────"

bench_recursive "Recursive (1 word)" "error"
bench_recursive "Recursive (5 words)" "error function static void int"


echo "════════════════════════════════════════════════════════════════"
echo ""

# Print the file size summary
print_file_size_summary

# Print the summary table at the end
print_syscall_summary

# Run the recursive scope analysis
analyze_recursive_scope

echo -e "${CYAN}${BOLD}TYPICAL USE CASES:${NC}"
echo "  • Grepping small scripts (100-500 lines): ITERATIONS × 500-1000"
echo "  • Searching source files (1000-2500 lines): ITERATIONS × 50-200"  
echo "  • Large files (5000+ lines): ITERATIONS × 20-50"
echo ""
echo -e "${GREEN}This simulates real development workflows!${NC}"
