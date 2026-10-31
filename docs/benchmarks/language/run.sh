#!/bin/bash
# Language-feature pins. Core 1. AILANG_CC selects the compiler.
# Outputs stay in /tmp/lang-bench so the source directories stay clean.
set -u
cd "$(dirname "$0")"
ROOT="$(cd ../../.. && pwd)"
OUT=/tmp/lang-bench
mkdir -p "$OUT"
CC="${AILANG_CC:-$ROOT/ailang.x}"
LIB="$ROOT/Librarys"

echo "CPU $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-)"
echo "AILANG $($CC -v 2>&1 | head -1) $(sha256sum "$CC" | awk '{print $1}')"

ai() {
    local name="$1" src="$2"
    echo "COMPILE AI $name"
    AILANG_LIB_PATH="$LIB" "$CC" "$src" "$OUT/$name.ail.x" > "$OUT/$name.ail.log" 2>&1
    local ec=$?
    echo "  exit $ec"
    return 0
}

runp() {
    local name="$1" bin="$2"
    if [ ! -x "$bin" ]; then
        echo "SKIP $name"
        return 0
    fi
    echo "RUN $name"
    taskset -c 1 "$bin" > "$OUT/$name.out" 2> "$OUT/$name.err"
    local ec=$?
    echo "  exit $ec"
    cat "$OUT/$name.out"
    return 0
}

ai memcopy memcopy.ailang
ai strings strings.ailang
ai array array.ailang
ai hash hash.ailang
ai recursion recursion.ailang
ai nbody "$ROOT/docs/benchmarks/nbody/nbody.ailang"

echo "COMPILE C memcopy"
gcc -O3 -march=native -std=gnu11 -o "$OUT/memcopy.c.x" memcopy.c > "$OUT/memcopy.c.log" 2>&1
echo "  exit $?"
echo "COMPILE C strings"
gcc -O3 -march=native -std=gnu11 -o "$OUT/strings.c.x" strings.c > "$OUT/strings.c.log" 2>&1
echo "  exit $?"
echo "COMPILE C array"
gcc -O3 -march=native -std=gnu11 -o "$OUT/array.c.x" array.c > "$OUT/array.c.log" 2>&1
echo "  exit $?"
echo "COMPILE C hash"
gcc -O3 -march=native -msse4.2 -std=gnu11 -o "$OUT/hash.c.x" hash.c > "$OUT/hash.c.log" 2>&1
echo "  exit $?"
echo "COMPILE C recursion"
gcc -O3 -march=native -std=gnu11 -fno-optimize-sibling-calls -o "$OUT/recursion.c.x" recursion.c > "$OUT/recursion.c.log" 2>&1
echo "  exit $?"
echo "COMPILE C nbody scalar"
g++ -O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize \
    -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops \
    -fno-peel-loops --param max-completely-peel-times=0 \
    --param max-completely-peeled-insns=0 -ffp-contract=off \
    -o "$OUT/nbody.scalar.x" "$ROOT/docs/benchmarks/nbody/nbody.cpp" -lm > "$OUT/nbody.scalar.log" 2>&1
echo "  exit $?"
echo "COMPILE C nbody native"
g++ -O3 -march=native -std=gnu++17 -fno-exceptions -fno-rtti \
    -o "$OUT/nbody.native.x" "$ROOT/docs/benchmarks/nbody/nbody.cpp" -lm > "$OUT/nbody.native.log" 2>&1
echo "  exit $?"

runp memcopy.ail "$OUT/memcopy.ail.x"
runp memcopy.gcc "$OUT/memcopy.c.x"
runp strings.ail "$OUT/strings.ail.x"
runp strings.gcc "$OUT/strings.c.x"
runp array.ail "$OUT/array.ail.x"
runp array.gcc "$OUT/array.c.x"
runp hash.ail "$OUT/hash.ail.x"
runp hash.gcc "$OUT/hash.c.x"
runp recursion.ail "$OUT/recursion.ail.x"
runp recursion.gcc "$OUT/recursion.c.x"
runp nbody.ail "$OUT/nbody.ail.x"
runp nbody.scalar "$OUT/nbody.scalar.x"
runp nbody.native "$OUT/nbody.native.x"
echo DONE
