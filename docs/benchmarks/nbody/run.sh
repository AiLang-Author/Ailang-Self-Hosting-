#!/bin/bash
# Scalar n-body. No vectorize, no unroll, no complete peel.
# -ffp-contract=off keeps mul and add separate. AILANG's one-use fold
# still fuses dx*dx into dx2+dy2, so e1 bits differ. compare.py reports that.
# Pin core 1. AILANG_CC overrides the compiler (default: repo ./ailang.x).
set -e
cd "$(dirname "$0")"
ROOT="$(cd ../../.. && pwd)"
CC="${AILANG_CC:-$ROOT/ailang.x}"

echo "CPU $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-)"
echo "CXX $(g++ -dumpfullversion) -O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops -fno-peel-loops --param max-completely-peel-times=0 --param max-completely-peeled-insns=0 -ffp-contract=off"
echo "$($CC -v) $(sha256sum "$CC" | awk '{print $1}')"

g++ -O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize \
    -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops \
    -fno-peel-loops --param max-completely-peel-times=0 \
    --param max-completely-peeled-insns=0 \
    -ffp-contract=off \
    -o nbody_cpp nbody.cpp -lm
"$CC" nbody.ailang -o nbody.x

set +e
taskset -c 1 ./nbody_cpp > cpp.txt
cpp_status=$?
taskset -c 1 ./nbody.x > ailang.txt
ail_status=$?
set -e
echo "nbody_cpp exit ${cpp_status}"
echo "nbody.x exit ${ail_status}"
python3 compare.py
