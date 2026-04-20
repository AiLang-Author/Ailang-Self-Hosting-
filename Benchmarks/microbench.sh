#!/bin/bash
# ============================================
# Micro-benchmarks — probe specific performance axes
# not covered by the other Benchmarks/*.sh scripts.
#
# Existing coverage:
#   benchmark.sh   — prime sieve (mixed arithmetic + memory)
#   benchinline.sh — function call overhead (100M add(i,1))
#   benchbranch.sh — predictable vs unpredictable branches
#   membench.sh    — sequential/random memory + alloc pressure
#
# This script adds:
#   1. ALU loop    — register allocation + arithmetic throughput
#                    (3 live vars, zero memory traffic)
#   2. Recursion   — stack frame setup + return propagation
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || { echo "Cannot cd to repo root"; exit 1; }

echo "=========================================="
echo "MICROBENCHMARKS"
echo "$(uname -a) — $(date)"
echo "=========================================="
echo ""

# ==========================================
# TEST 1: PURE ALU LOOP
# ==========================================
# No memory access, no allocation, no calls. Just a tight loop
# with 3 live integers. If AiLang is slow here it's purely a
# register-allocation issue — nothing else can explain it.
cat > alu_loop.c << 'EOF'
#include <stdio.h>
int main() {
    long a = 1, b = 2, c = 3;
    for (long i = 0; i < 500000000L; i++) {
        a = a + b;
        b = b + c;
        c = c + a;
    }
    printf("Result: %ld\n", a ^ b ^ c);
    return 0;
}
EOF

cat > alu_loop.ailang << 'AILANGEOF'
SubRoutine.Main {
    a = 1
    b = 2
    c = 3
    i = 0
    WhileLoop LessThan(i, 500000000) {
        a = Add(a, b)
        b = Add(b, c)
        c = Add(c, a)
        i = Add(i, 1)
    }
    r = BitwiseXor(a, BitwiseXor(b, c))
    PrintMessage("Result: ")
    PrintNumber(r)
    PrintMessage("\n")
}
RunTask(Main)
AILANGEOF

# (Call-overhead test moved to benchinline.sh — skipped here.)

# ==========================================
# TEST 2: RECURSION (Fibonacci)
# ==========================================
# Classic tree recursion — fib(35) = ~29M calls. Each call
# has no inlinable shortcut (branches on n). Measures stack
# frame allocation + return propagation.
cat > fib.c << 'EOF'
#include <stdio.h>
long fib(long n) {
    if (n < 2) return n;
    return fib(n-1) + fib(n-2);
}
int main() {
    printf("fib(35) = %ld\n", fib(35));
    return 0;
}
EOF

cat > fib.ailang << 'AILANGEOF'
Function.Fib {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessThan(n, 2) ThenBlock: { ReturnValue(n) }
        ReturnValue(Add(Fib(Subtract(n, 1)), Fib(Subtract(n, 2))))
    }
}

SubRoutine.Main {
    r = Fib(35)
    PrintMessage("fib(35) = ")
    PrintNumber(r)
    PrintMessage("\n")
}
RunTask(Main)
AILANGEOF

# Cleanup + compile
rm -f alu_loop_c alu_loop_ai.x fib_c fib_ai.x

echo "=========================================="
echo "COMPILING"
echo "=========================================="
echo ""

echo "=== ALU Loop ==="
echo "AILang:"
time ./ailang.x alu_loop.ailang alu_loop_ai.x > /dev/null 2>&1
echo "GCC -O3:"
time gcc -O3 -o alu_loop_c alu_loop.c
echo ""

echo "=== Fibonacci ==="
echo "AILang:"
time ./ailang.x fib.ailang fib_ai.x > /dev/null 2>&1
echo "GCC -O3:"
time gcc -O3 -o fib_c fib.c
echo ""

run_bench() {
    name=$1
    binary=$2
    echo "--- $name ---"
    for run in 1 2 3; do
        result=$( { time $binary; } 2>&1 )
        real_time=$(echo "$result" | grep real | awk '{print $2}')
        echo "  Run $run: $real_time"
    done
    echo ""
}

chmod +x alu_loop_ai.x fib_ai.x

echo "=========================================="
echo "ALU LOOP (500M iterations, 3 live vars, pure register work)"
echo "=========================================="
echo ""
run_bench "AILang"       "./alu_loop_ai.x"
run_bench "C (gcc -O3)"  "./alu_loop_c"

echo "=========================================="
echo "FIBONACCI (fib(35) — ~29M recursive calls)"
echo "=========================================="
echo ""
run_bench "AILang"       "./fib_ai.x"
run_bench "C (gcc -O3)"  "./fib_c"

echo "=========================================="
echo "INTERPRETATION GUIDE"
echo "=========================================="
echo "  ALU / C ratio ≈ 1.0 → register allocator is healthy"
echo "  Fib  / C ratio ≈ 1.0 → stack frame + return path is clean"
echo "  Any ratio ≫ 1.5 → that axis is leaving performance on the floor"
echo "=========================================="
