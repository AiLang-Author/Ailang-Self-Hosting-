#!/bin/bash
# Plain spectral-norm. g++ -O3 may vectorize; the source does not.
# Pin core 1. Print f64 bits and the monotonic gap around the ten iterations.
set -e
cd "$(dirname "$0")"
ROOT="$(cd ../../.. && pwd)"
CC="$ROOT/ailang.x"

echo "CPU $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-)"
echo "CXX $(g++ -dumpfullversion) -O3 -std=gnu++17 -fno-exceptions -fno-rtti"
echo "$($CC -v) $(sha256sum "$CC" | awk '{print $1}')"

g++ -O3 -std=gnu++17 -fno-exceptions -fno-rtti -o spectral_cpp spectral.cpp
"$CC" spectral.ailang -o spectral.x

set +e
taskset -c 1 ./spectral_cpp > cpp.txt
cpp_status=$?
taskset -c 1 ./spectral.x > ailang.txt
ail_status=$?
set -e
echo "spectral_cpp exit ${cpp_status}"
echo "spectral.x exit ${ail_status}"
python3 compare.py
