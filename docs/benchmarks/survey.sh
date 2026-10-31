#!/bin/bash
# One-core scan vs scalar g++. Existing docs benches, isolate kernels,
# and extra pairs. Core 1 only. No parallel runs.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CC="${AILANG_CC:-/tmp/linscan_s2.x}"
LIB="$ROOT/Librarys"
OUT=/tmp/bench-out/survey
mkdir -p "$OUT"
export AILANG_LIB_PATH="$LIB"
export AILANG_LINSCAN=1

NBODY_CXX=(-O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize \
    -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops \
    -fno-peel-loops --param max-completely-peel-times=0 \
    --param max-completely-peeled-insns=0 -ffp-contract=off)
ISO_CXX=("${NBODY_CXX[@]}")

ai() {
    local name="$1" src="$2"
    echo "COMPILE scan $name"
    "$CC" "$src" "$OUT/$name.ail.x" > "$OUT/$name.ail.log" 2>&1
    echo "  $?"
}

run1() {
    local tag="$1" bin="$2"
    if [ ! -x "$bin" ]; then
        echo "SKIP $tag"
        return 0
    fi
    echo "RUN $tag"
    taskset -c 1 "$bin"
}

echo "=== isolate ==="
"$ROOT/docs/benchmarks/isolate/run.sh"
# fasta, vmdispatch, lz4win, jsonarena, nbody50 are in isolate/run.sh

echo "=== docs float/int ==="
ai mandel "$ROOT/docs/benchmarks/mandelbrot/mandelbrot.ailang"
ai sieve "$ROOT/docs/benchmarks/sieve/sieve.ailang"
ai nbody "$ROOT/docs/benchmarks/nbody/nbody.ailang"
ai spectral "$ROOT/docs/benchmarks/spectral-norm/spectral.ailang"
ai matmul "$ROOT/docs/benchmarks/matmul/matmul.ailang"
g++ "${NBODY_CXX[@]}" -o "$OUT/mandel.gcc.x" "$ROOT/docs/benchmarks/mandelbrot/mandelbrot.c" -lm
g++ "${NBODY_CXX[@]}" -o "$OUT/sieve.gcc.x" "$ROOT/docs/benchmarks/sieve/sieve.c"
g++ "${NBODY_CXX[@]}" -o "$OUT/nbody.gcc.x" "$ROOT/docs/benchmarks/nbody/nbody.cpp" -lm
g++ -O3 -std=gnu++17 -fno-exceptions -fno-rtti -o "$OUT/spectral.gcc.x" "$ROOT/docs/benchmarks/spectral-norm/spectral.cpp"
g++ -O3 -std=gnu++17 -fno-exceptions -fno-rtti -fno-devirtualize \
    -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops \
    -ffp-contract=fast -o "$OUT/matmul.gcc.x" "$ROOT/docs/benchmarks/matmul/matmul.cpp"

run1 mandel.scan "$OUT/mandel.ail.x"
run1 mandel.gcc "$OUT/mandel.gcc.x"
run1 sieve.scan "$OUT/sieve.ail.x"
run1 sieve.gcc "$OUT/sieve.gcc.x"
run1 nbody.scan "$OUT/nbody.ail.x"
run1 nbody.gcc "$OUT/nbody.gcc.x"
run1 spectral.scan "$OUT/spectral.ail.x"
run1 spectral.gcc "$OUT/spectral.gcc.x"
run1 matmul.scan "$OUT/matmul.ail.x"
run1 matmul.gcc "$OUT/matmul.gcc.x"

echo "=== language ==="
ai array "$ROOT/docs/benchmarks/language/array.ailang"
ai hash "$ROOT/docs/benchmarks/language/hash.ailang"
ai strings "$ROOT/docs/benchmarks/language/strings.ailang"
ai memcopy "$ROOT/docs/benchmarks/language/memcopy.ailang"
ai recursion "$ROOT/docs/benchmarks/language/recursion.ailang"
gcc -O3 -std=gnu11 -o "$OUT/array.gcc.x" "$ROOT/docs/benchmarks/language/array.c"
gcc -O3 -msse4.2 -std=gnu11 -o "$OUT/hash.gcc.x" "$ROOT/docs/benchmarks/language/hash.c"
gcc -O3 -std=gnu11 -o "$OUT/strings.gcc.x" "$ROOT/docs/benchmarks/language/strings.c"
gcc -O3 -std=gnu11 -o "$OUT/memcopy.gcc.x" "$ROOT/docs/benchmarks/language/memcopy.c"
gcc -O3 -std=gnu11 -fno-optimize-sibling-calls -o "$OUT/recursion.gcc.x" "$ROOT/docs/benchmarks/language/recursion.c"
run1 array.scan "$OUT/array.ail.x"
run1 array.gcc "$OUT/array.gcc.x"
run1 hash.scan "$OUT/hash.ail.x"
run1 hash.gcc "$OUT/hash.gcc.x"
run1 strings.scan "$OUT/strings.ail.x"
run1 strings.gcc "$OUT/strings.gcc.x"
run1 memcopy.scan "$OUT/memcopy.ail.x"
run1 memcopy.gcc "$OUT/memcopy.gcc.x"
run1 recursion.scan "$OUT/recursion.ail.x"
run1 recursion.gcc "$OUT/recursion.gcc.x"

echo "=== extras ==="
ai mem_rand "$ROOT/Benchmarks/AiLang/mem_rand.ailang"
ai fnv1a "$ROOT/Benchmarks/AiLang/fnv1a.ailang"
ai branch_pred "$ROOT/Benchmarks/AiLang/branch_pred.ailang"
ai primetest "$ROOT/Benchmarks/AiLang/primetest.ailang"
ai revcomp "$ROOT/Benchmarks/AiLang/revcomp.ailang"
gcc -O3 -std=gnu11 -o "$OUT/mem_rand.gcc.x" "$ROOT/Benchmarks/C/mem_rand.c"
gcc -O3 -std=gnu11 -o "$OUT/fnv1a.gcc.x" "$ROOT/Benchmarks/C/fnv1a.c"
gcc -O3 -std=gnu11 -o "$OUT/branch_pred.gcc.x" "$ROOT/Benchmarks/C/branch_pred.c"
gcc -O3 -std=gnu11 -o "$OUT/primetest.gcc.x" "$ROOT/Benchmarks/C/primetestC.c"
gcc -O3 -std=gnu11 -o "$OUT/revcomp.gcc.x" "$ROOT/Benchmarks/C/revcomp.c"
run1 mem_rand.scan "$OUT/mem_rand.ail.x"
run1 mem_rand.gcc "$OUT/mem_rand.gcc.x"
run1 fnv1a.scan "$OUT/fnv1a.ail.x"
run1 fnv1a.gcc "$OUT/fnv1a.gcc.x"
run1 branch_pred.scan "$OUT/branch_pred.ail.x"
run1 branch_pred.gcc "$OUT/branch_pred.gcc.x"
run1 primetest.scan "$OUT/primetest.ail.x"
run1 primetest.gcc "$OUT/primetest.gcc.x"
run1 revcomp.scan "$OUT/revcomp.ail.x"
run1 revcomp.gcc "$OUT/revcomp.gcc.x"

echo "=== fannkuch n=7/10/12 ==="
ai fannkuch "$ROOT/docs/benchmarks/fannkuch/fannkuch.ailang"
g++ "${NBODY_CXX[@]}" -o "$OUT/fannkuch.gcc.x" "$ROOT/docs/benchmarks/fannkuch/fannkuch.cpp"
run1 fannkuch.scan "$OUT/fannkuch.ail.x"
run1 fannkuch.gcc "$OUT/fannkuch.gcc.x"

echo SURVEY_DONE
