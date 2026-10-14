#!/bin/bash
# 64x64 tiled matmul. Scalar g++ only: no vectorize, no unroll.
# -ffp-contract=fast leaves scalar fma selection on. The matrix entries
# are small integers, so fma and mul/add print the same bits.
# Pin core 1. AILANG_CC overrides the compiler (default: repo ./ailang.x).
set -e
cd "$(dirname "$0")"
ROOT="$(cd ../../.. && pwd)"
CC="${AILANG_CC:-$ROOT/ailang.x}"

echo "CPU $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-)"
echo "CXX $(g++ -dumpfullversion) -O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops -ffp-contract=fast"
echo "$($CC -v) $(sha256sum "$CC" | awk '{print $1}')"

g++ -O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize \
    -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops \
    -ffp-contract=fast \
    -o matmul_cpp matmul.cpp
"$CC" matmul.ailang -o matmul.x

set +e
taskset -c 1 ./matmul_cpp > cpp.txt
cpp_status=$?
taskset -c 1 ./matmul.x > ailang.txt
ail_status=$?
set -e
echo "matmul_cpp exit ${cpp_status}"
echo "matmul.x exit ${ail_status}"
python3 compare.py
