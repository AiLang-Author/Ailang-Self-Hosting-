#!/bin/bash
# One pattern per program. Scalar g++ -O3 matches the n-body flags:
# no vectorize, no unroll, no contracted multiply-add.
# Pin core 1. One bench at a time.
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CC="${AILANG_CC:-/tmp/linscan_s2.x}"
LIB="$ROOT/Librarys"
OUT=/tmp/bench-out/isolate
mkdir -p "$OUT"
export AILANG_LIB_PATH="$LIB"
export AILANG_LINSCAN=1

CXXFLAGS=(-O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize \
    -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops \
    -fno-peel-loops --param max-completely-peel-times=0 \
    --param max-completely-peeled-insns=0 -ffp-contract=off)

for name in regchain fieldop idxsum swaploop sqrtdiv triad liveint callcost bintree fasta vmdispatch lz4win jsonarena nbody50; do
    echo "COMPILE $name"
    "$CC" "$ROOT/docs/benchmarks/isolate/$name.ailang" "$OUT/$name.ail.x" > "$OUT/$name.ail.log" 2>&1
    echo "  ailang $?"
    extra=()
    if [ "$name" = callcost ] || [ "$name" = bintree ]; then
        extra=(-fno-optimize-sibling-calls)
    fi
    if [ "$name" = nbody50 ]; then
        extra+=(-lm)
    fi
    g++ "${CXXFLAGS[@]}" "${extra[@]}" -o "$OUT/$name.gcc.x" "$ROOT/docs/benchmarks/isolate/$name.c" -lm
    echo "  gcc $?"
done

for name in regchain fieldop idxsum swaploop sqrtdiv triad liveint callcost bintree fasta vmdispatch lz4win jsonarena nbody50; do
    echo "RUN $name scan"
    if [ -x "$OUT/$name.ail.x" ]; then
        taskset -c 1 "$OUT/$name.ail.x"
    else
        echo "  SKIP"
    fi
    echo "RUN $name gcc"
    taskset -c 1 "$OUT/$name.gcc.x"
done
echo DONE
