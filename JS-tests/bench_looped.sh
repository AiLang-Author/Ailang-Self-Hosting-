#!/usr/bin/env bash
# bench_looped.sh — Steady-state benchmark: Ailang JS vs V8
#
# Wraps each benchmark in an outer iteration loop so both engines
# measure pure compute time (not startup/JIT warmup amortized away).
#
# Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HARNESS="$ROOT/test262_harness.x"
SUNSPIDER="/home/bob/quickjs-benchmarks/sunspider-1.0"
LOOPS=100  # inner iterations
RUNS=3     # outer measurement runs (median)

if [[ ! -x "$HARNESS" ]]; then
    echo "ERROR: $HARNESS not found."
    exit 1
fi

# Wrap a benchmark in an iteration loop
wrap_loop() {
    local src="$1"
    local out="$2"
    local iters="$3"
    # Extract the benchmark body (everything), wrap in a function, call N times
    cat > "$out" <<WRAPPER
function __bench__() {
$(cat "$src")
}
for (var __i__ = 0; __i__ < $iters; __i__++) {
    __bench__();
}
WRAPPER
}

time_ms() {
    local start end
    start=$(date +%s%N)
    "$@" >/dev/null 2>&1 || true
    end=$(date +%s%N)
    echo "scale=3; ($end - $start) / 1000000" | bc
}

median_time() {
    local -a times=()
    for ((i=0; i<RUNS; i++)); do
        times+=("$(time_ms "$@")")
    done
    printf '%s\n' "${times[@]}" | sort -n | sed -n "$((RUNS/2+1))p"
}

# Select representative benchmarks (compute-heavy, no float dependency)
BENCHMARKS=(
    "controlflow-recursive.js"
    "bitops-3bit-bits-in-byte.js"
    "bitops-bitwise-and.js"
    "access-binary-trees.js"
    "access-fannkuch.js"
    "crypto-md5.js"
    "crypto-sha1.js"
    "string-validate-input.js"
)

total_ailang=0
total_v8=0

printf "\n"
printf "  Steady-State Benchmark: %d iterations per run, %d runs (median)\n" "$LOOPS" "$RUNS"
printf "\n"
printf "  %-35s %10s %10s %8s\n" "Benchmark" "Ailang" "Node/V8" "Ratio"
printf "  %-35s %10s %10s %8s\n" "-----------------------------------" "----------" "----------" "--------"

for bench in "${BENCHMARKS[@]}"; do
    src="$SUNSPIDER/$bench"
    tmp="/tmp/bench_looped_${bench}"

    wrap_loop "$src" "$tmp" "$LOOPS"

    ailang_ms=$(median_time "$HARNESS" "$tmp")
    v8_ms=$(median_time node "$tmp")

    if (( $(echo "$ailang_ms > 0.001" | bc -l) )); then
        ratio=$(echo "scale=2; $v8_ms / $ailang_ms" | bc 2>/dev/null || echo "?")
    else
        ratio="?"
    fi

    printf "  %-35s %8s ms %8s ms %6sx\n" "$bench" "$ailang_ms" "$v8_ms" "$ratio"

    total_ailang=$(echo "$total_ailang + $ailang_ms" | bc)
    total_v8=$(echo "$total_v8 + $v8_ms" | bc)
done

printf "\n"
printf "  %-35s %8s ms %8s ms" "TOTAL" "$total_ailang" "$total_v8"
if (( $(echo "$total_ailang > 0.001" | bc -l) )); then
    overall=$(echo "scale=2; $total_v8 / $total_ailang" | bc)
    printf " %6sx\n" "$overall"
else
    printf "\n"
fi
printf "\n"
echo "  Each benchmark body runs $LOOPS times inside a loop."
echo "  This measures raw compute throughput, not startup."
echo "  Ratio >1 = Ailang faster, <1 = V8 faster."
echo ""
