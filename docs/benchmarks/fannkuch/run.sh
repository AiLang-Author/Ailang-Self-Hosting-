#!/bin/bash
# Single-thread fannkuch-redux. No vectorize, no unroll, no complete peel.
# Pin core 1. AILANG_CC overrides the compiler (default: repo ./ailang.x).
set -e
cd "$(dirname "$0")"
ROOT="$(cd ../../.. && pwd)"
CC="${AILANG_CC:-$ROOT/ailang.x}"

echo "CPU $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-)"
echo "CXX $(g++ -dumpfullversion) -O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops -fno-peel-loops --param max-completely-peel-times=0 --param max-completely-peeled-insns=0"
echo "$($CC -v) $(sha256sum "$CC" | awk '{print $1}')"

g++ -O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize \
    -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops \
    -fno-peel-loops --param max-completely-peel-times=0 \
    --param max-completely-peeled-insns=0 \
    -o fannkuch_cpp fannkuch.cpp
"$CC" fannkuch.ailang -o fannkuch.x

set +e
taskset -c 1 ./fannkuch_cpp > cpp.txt
cpp_status=$?
taskset -c 1 ./fannkuch.x > ailang.txt
ail_status=$?
set -e
echo "fannkuch_cpp exit ${cpp_status}"
echo "fannkuch.x exit ${ail_status}"
python3 compare.py
