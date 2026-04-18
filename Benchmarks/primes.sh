#!/usr/bin/env bash
# bench_primes_silent.sh - Silent benchmark (summary only, no warnings)

# Run from AiLangSH root regardless of invocation dir.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || { echo "Cannot cd to repo root"; exit 1; }

# Explicit paths for all system utilities
GREP=/usr/bin/grep
AWK=/usr/bin/awk
BC=/usr/bin/bc
TIME=/usr/bin/time
DATE=/usr/bin/date
SED=/usr/bin/sed

# CONFIG
QUIET=1                             # 1 = summary only, no per-run spam
AILANG_EXE="./primetest.x"
GCC_EXE="./primes_c_o3"
RUNS=20
EXPECTED_PRIMES=78498               # We keep it for reference but don't check/print
TMP_OUT="/tmp/bench_out_$$.txt"
TMP_TIME="/tmp/bench_time_$$.txt"

echo "Benchmark: Trial division primes up to 1,000,000"
echo "AiLang binary:   $AILANG_EXE"
echo "GCC -O3 binary:  $GCC_EXE"
echo "Runs per exe:    $RUNS"
echo "Date:            $($DATE)"
echo ""

for exe in "$AILANG_EXE" "$GCC_EXE"; do
    if [ ! -x "$exe" ]; then
        echo "ERROR: $exe not found or not executable"
        exit 1
    fi
done

run_test() {
    local exe="$1"
    local name="$2"
    local total_real=0
    local times=()  # for min/median/max

    for ((i=1; i<=RUNS; i++)); do
        rm -f "$TMP_OUT" "$TMP_TIME"

        $TIME -p "$exe" > "$TMP_OUT" 2> "$TMP_TIME"

        real_time=$($GREP '^real' "$TMP_TIME" | $AWK '{print $2}' | head -n1)

        if [ -z "$real_time" ]; then
            echo "ERROR: No real time captured for $name run $i"
            continue
        fi

        # Convert m:ss.sss → seconds
        if [[ $real_time =~ ^([0-9]+):([0-9]+\.[0-9]+)$ ]]; then
            seconds=$($BC -l <<< "${BASH_REMATCH[1]} * 60 + ${BASH_REMATCH[2]}")
        else
            seconds=$real_time
        fi

        total_real=$($BC -l <<< "$total_real + $seconds")
        times+=("$seconds")
    done

    rm -f "$TMP_OUT" "$TMP_TIME"

    if [ ${#times[@]} -eq 0 ]; then
        echo "No successful runs for $name"
        return
    fi

    # Stats
    avg=$($BC -l <<< "scale=3; $total_real / ${#times[@]}")
    sorted=($(printf '%s\n' "${times[@]}" | sort -n))
    median=${sorted[$((RUNS/2))]}
    min=${sorted[0]}
    max=${sorted[-1]}

    printf "%-20s  Avg: %s s   Min: %s s   Max: %s s   Median: %s s   (%d runs)\n" \
        "$name" "$avg" "$min" "$max" "$median" "${#times[@]}"
    echo ""
}

run_test "$AILANG_EXE" "AiLang self-hosted"
run_test "$GCC_EXE"    "GCC -O3"

echo "Benchmark complete."