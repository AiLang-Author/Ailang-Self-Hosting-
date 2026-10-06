#!/bin/bash
# Rebuild both programs, pin one core, and check that paired f64 bits match.
# FX-8320 TSC is invariant. Pinning avoids a migration bump in the timed rows.
# -TS stays off. The comparison is the whole Arena library, not the functions
# a tree-shake could prove this benchmark never calls.
set -e
cd "$(dirname "$0")"
ROOT="$(cd ../../.. && pwd)"
CC="$ROOT/ailang.x"

echo "CPU $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-)"
echo "CXX $(g++ -dumpfullversion) -O3 -std=c++17 -fno-exceptions -fno-rtti -fno-devirtualize -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops"
echo "$($CC -v) $(sha256sum "$CC" | awk '{print $1}')"

g++ -O3 -std=c++17 -fno-exceptions -fno-rtti -fno-devirtualize \
    -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops \
    -o shapes_cpp shapes.cpp
"$CC" shapes.ailang -o shapes.x

python3 oracle.py > oracle.txt
set +e
taskset -c 1 ./shapes_cpp > cpp.txt
cpp_status=$?
taskset -c 1 ./shapes.x > ailang.txt
ail_status=$?
set -e
echo "shapes_cpp exit ${cpp_status} (low byte of the sink, not a pass/fail)"
echo "shapes.x exit ${ail_status}"
python3 compare.py
