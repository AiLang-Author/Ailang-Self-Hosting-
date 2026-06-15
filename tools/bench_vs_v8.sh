#!/usr/bin/env bash
# bench_vs_v8.sh — Compare Ailang JS engine vs V8 (node) on SunSpider
#
# Measures total wall-clock time (startup + parse + compile + execute).
# Each benchmark is run RUNS times, median reported.
#
# Usage: ./tools/bench_vs_v8.sh [sunspider|octane|all]
#
# Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HARNESS="$ROOT/test262_harness.x"
SUNSPIDER="/home/bob/quickjs-benchmarks/sunspider-1.0"
OCTANE="/home/bob/quickjs-benchmarks/octane"
RUNS=5

if [[ ! -x "$HARNESS" ]]; then
    echo "ERROR: $HARNESS not found."
    exit 1
fi

# Time a command in nanoseconds, return ms with 3 decimals
time_ms() {
    local start end
    start=$(date +%s%N)
    "$@" >/dev/null 2>&1 || true
    end=$(date +%s%N)
    echo "scale=3; ($end - $start) / 1000000" | bc
}

# Time the ailang harness (copies file to /tmp/test262_current.js first)
time_ailang_ms() {
    local file="$1"
    local start end
    cp "$file" /tmp/test262_current.js
    start=$(date +%s%N)
    "$HARNESS" >/dev/null 2>&1 || true
    end=$(date +%s%N)
    echo "scale=3; ($end - $start) / 1000000" | bc
}

# Run N times for ailang harness, return median
median_time_ailang() {
    local file="$1"
    local -a times=()
    for ((i=0; i<RUNS; i++)); do
        times+=("$(time_ailang_ms "$file")")
    done
    printf '%s\n' "${times[@]}" | sort -n | sed -n "$((RUNS/2+1))p"
}

# Run N times, return median
median_time() {
    local -a times=()
    for ((i=0; i<RUNS; i++)); do
        times+=("$(time_ms "$@")")
    done
    printf '%s\n' "${times[@]}" | sort -n | sed -n "$((RUNS/2+1))p"
}

# Totals
total_ailang=0
total_v8=0
count=0

# Print header
printf "\n"
printf "  %-38s %10s %10s %8s\n" "Benchmark" "Ailang" "Node/V8" "Ratio"
printf "  %-38s %10s %10s %8s\n" "--------------------------------------" "----------" "----------" "--------"

run_bench() {
    local file="$1"
    local name="$2"
    local ailang_ms v8_ms ratio

    ailang_ms=$(median_time_ailang "$file")
    v8_ms=$(median_time node "$file")

    if (( $(echo "$v8_ms > 0.001" | bc -l) )); then
        ratio=$(echo "scale=1; $v8_ms / $ailang_ms" | bc 2>/dev/null || echo "?")
    else
        ratio="?"
    fi

    printf "  %-38s %8s ms %8s ms %6sx\n" "$name" "$ailang_ms" "$v8_ms" "$ratio"

    total_ailang=$(echo "$total_ailang + $ailang_ms" | bc)
    total_v8=$(echo "$total_v8 + $v8_ms" | bc)
    count=$((count + 1))
}

# Run a single benchmark with a timeout; report FAIL instead of dying
run_bench_safe() {
    local file="$1"
    local name="$2"
    local timeout_s="${3:-60}"
    local ailang_ms v8_ms ratio ailang_ok

    # Test if ailang can handle it at all (single run with timeout)
    cp "$file" /tmp/test262_current.js
    ailang_ok=1
    timeout "$timeout_s" "$HARNESS" >/dev/null 2>&1 || ailang_ok=0

    if [[ "$ailang_ok" -eq 0 ]]; then
        # Capture error for diagnostics (re-run with short timeout)
        cp "$file" /tmp/test262_current.js
        local err_out
        err_out=$(timeout 15 "$HARNESS" 2>&1 | grep -E '(failed|ERROR|error|CRASH|Segfault|dump)' | head -3)
        [[ -z "$err_out" ]] && err_out="(exit code non-zero or timeout)"
        v8_ms=$(median_time node "$file")
        printf "  %-38s %10s %8s ms %6s\n" "$name" "FAIL" "$v8_ms" "-"
        printf "    => %s\n" "$err_out"
        return
    fi

    ailang_ms=$(median_time_ailang "$file")
    v8_ms=$(median_time node "$file")

    if (( $(echo "$v8_ms > 0.001" | bc -l) )); then
        ratio=$(echo "scale=1; $v8_ms / $ailang_ms" | bc 2>/dev/null || echo "?")
    else
        ratio="?"
    fi

    printf "  %-38s %8s ms %8s ms %6sx\n" "$name" "$ailang_ms" "$v8_ms" "$ratio"

    total_ailang=$(echo "$total_ailang + $ailang_ms" | bc)
    total_v8=$(echo "$total_v8 + $v8_ms" | bc)
    count=$((count + 1))
}

run_sunspider() {
    echo ""
    echo "  === SunSpider 1.0 ==="
    echo ""
    for f in "$SUNSPIDER"/*.js; do
        run_bench "$f" "$(basename "$f")"
    done
}

run_octane() {
    echo ""
    echo "  === Octane — Light (parse+execute) ==="
    echo ""
    for f in richards.js deltablue.js crypto.js raytrace.js earley-boyer.js navier-stokes.js splay.js code-load.js; do
        local tmp="/tmp/octane_bench_$f"
        cat "$OCTANE/base.js" "$OCTANE/$f" > "$tmp"
        run_bench "$tmp" "octane/$f"
    done

    echo ""
    echo "  === Octane — Heavy (parse+execute, 120s timeout) ==="
    echo ""

    # regexp (126 KB)
    local tmp="/tmp/octane_bench_regexp.js"
    cat "$OCTANE/base.js" "$OCTANE/regexp.js" > "$tmp"
    run_bench_safe "$tmp" "octane/regexp.js" 120

    # box2d (228 KB)
    tmp="/tmp/octane_bench_box2d.js"
    cat "$OCTANE/base.js" "$OCTANE/box2d.js" > "$tmp"
    run_bench_safe "$tmp" "octane/box2d.js" 120

    # gbemu (part1 + part2 = 516 KB)
    tmp="/tmp/octane_bench_gbemu.js"
    cat "$OCTANE/base.js" "$OCTANE/gbemu-part1.js" "$OCTANE/gbemu-part2.js" > "$tmp"
    run_bench_safe "$tmp" "octane/gbemu.js" 120

    # zlib + zlib-data (196 KB)
    tmp="/tmp/octane_bench_zlib.js"
    cat "$OCTANE/base.js" "$OCTANE/zlib.js" "$OCTANE/zlib-data.js" > "$tmp"
    run_bench_safe "$tmp" "octane/zlib.js" 120

    # pdfjs (1.5 MB)
    tmp="/tmp/octane_bench_pdfjs.js"
    cat "$OCTANE/base.js" "$OCTANE/pdfjs.js" > "$tmp"
    run_bench_safe "$tmp" "octane/pdfjs.js" 120

    # mandreel (5 MB)
    tmp="/tmp/octane_bench_mandreel.js"
    cat "$OCTANE/base.js" "$OCTANE/mandreel.js" > "$tmp"
    run_bench_safe "$tmp" "octane/mandreel.js" 120

    # typescript (compiler + input + harness = 2.5 MB)
    tmp="/tmp/octane_bench_typescript.js"
    cat "$OCTANE/base.js" "$OCTANE/typescript.js" "$OCTANE/typescript-input.js" "$OCTANE/typescript-compiler.js" > "$tmp"
    run_bench_safe "$tmp" "octane/typescript.js" 120
}

MODE="${1:-all}"
case "$MODE" in
    sunspider) run_sunspider ;;
    octane)    run_octane ;;
    all)       run_sunspider; run_octane ;;
    *)         echo "Usage: $0 [sunspider|octane|all]"; exit 1 ;;
esac

echo ""
printf "  %-38s %8s ms %8s ms" "TOTAL" "$total_ailang" "$total_v8"
if (( $(echo "$total_ailang > 0.001" | bc -l) )); then
    overall=$(echo "scale=1; $total_v8 / $total_ailang" | bc)
    printf " %6sx\n" "$overall"
else
    printf "\n"
fi
echo ""
echo "  Ailang: bytecode VM (no JIT). Node: V8 with TurboFan JIT."
echo "  Ratio = V8_time / Ailang_time (>1 means Ailang is faster)."
echo "  Measured: total wall-clock (startup + parse + compile + execute)."
echo "  Runs: $RUNS iterations, median reported."
echo ""
