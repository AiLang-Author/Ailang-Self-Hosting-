#!/bin/bash
# ============================================
# Function Call Overhead Benchmark
# Tests: call/ret overhead, inlining advantage
# ============================================

# Run from AiLangSH root regardless of invocation dir. Source files are
# regenerated via heredoc each run and land in CWD (= repo root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || { echo "Cannot cd to repo root"; exit 1; }


echo "=========================================="
echo "FUNCTION CALL OVERHEAD BENCHMARK"
echo "100,000,000 iterations of add(i, 1)"
echo "$(uname -a)"
echo "$(date)"
echo "=========================================="
echo ""

# --- Source files ---

# C version - function in separate translation would prevent inlining
# but same file lets compiler inline freely (realistic comparison)
cat > calltest.c << 'EOF'
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main() {
    long sum = 0;
    for (int i = 0; i < 100000000; i++) {
        sum += add(i, 1);
    }
    printf("Sum: %ld\n", sum);
    return 0;
}
EOF

# C version with noinline to show what happens WITHOUT inlining
cat > calltest_noinline.c << 'EOF'
#include <stdio.h>

__attribute__((noinline)) int add(int a, int b) {
    return a + b;
}

int main() {
    long sum = 0;
    for (int i = 0; i < 100000000; i++) {
        sum += add(i, 1);
    }
    printf("Sum: %ld\n", sum);
    return 0;
}
EOF

cat > calltest.zig << 'EOF'
const std = @import("std");

fn add(a: i64, b: i64) i64 {
    return a + b;
}

pub fn main() !void {
    var sum: i64 = 0;
    var i: i64 = 0;
    while (i < 100000000) : (i += 1) {
        sum += add(i, 1);
    }
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Sum: {}\n", .{sum});
}
EOF

cat > calltest.rs << 'EOF'
fn add(a: i64, b: i64) -> i64 {
    a + b
}

fn main() {
    let mut sum: i64 = 0;
    for i in 0..100000000_i64 {
        sum += add(i, 1);
    }
    println!("Sum: {}", sum);
}
EOF

cat > calltest.go << 'EOF'
package main

import "fmt"

func add(a, b int) int {
    return a + b
}

func main() {
    sum := 0
    for i := 0; i < 100000000; i++ {
        sum += add(i, 1)
    }
    fmt.Printf("Sum: %d\n", sum)
}
EOF

# AILang version - uses a real function call
cat > calltest.ailang << 'AILANGEOF'
Function.AddTwo {
    Input: a: Integer
    Input: b: Integer
    Output: Integer
    Body: {
        ReturnValue(Add(a, b))
    }
}

SubRoutine.Main {
    sum = 0
    i = 0
    WhileLoop LessThan(i, 100000000) {
        sum = Add(sum, AddTwo(i, 1))
        i = Add(i, 1)
    }
    PrintMessage("Sum: ")
    PrintNumber(sum)
    PrintMessage("\n")
}
RunTask(Main)
AILANGEOF

# AILang version WITHOUT the function call - direct Add only
cat > calltest_direct.ailang << 'AILANGEOF2'
SubRoutine.Main {
    sum = 0
    i = 0
    WhileLoop LessThan(i, 100000000) {
        sum = Add(sum, Add(i, 1))
        i = Add(i, 1)
    }
    PrintMessage("Sum: ")
    PrintNumber(sum)
    PrintMessage("\n")
}
RunTask(Main)
AILANGEOF2

# --- Clean ---
echo "--- Cleaning ---"
rm -f calltest_c_o0 calltest_c_o2 calltest_c_o3 calltest_c_noinline
rm -f calltest_zig calltest_rust calltest_go
rm -f calltest_ailang.x calltest_direct.x
rm -f calltest.o calltest_zig.o
echo ""

# --- Compile ---
echo "=========================================="
echo "COMPILE"
echo "=========================================="
echo ""

echo "--- AILang (with function call) ---"
time ./ailang.x calltest.ailang calltest_ailang.x > /dev/null 2>&1
echo ""

echo "--- AILang (direct Add, no function) ---"
time ./ailang.x calltest_direct.ailang calltest_direct.x > /dev/null 2>&1
echo ""

echo "--- C (gcc -O0) ---"
time gcc -O0 -o calltest_c_o0 calltest.c
echo ""

echo "--- C (gcc -O2) ---"
time gcc -O2 -o calltest_c_o2 calltest.c
echo ""

echo "--- C (gcc -O3) ---"
time gcc -O3 -o calltest_c_o3 calltest.c
echo ""

echo "--- C (gcc -O3, noinline) ---"
time gcc -O3 -o calltest_c_noinline calltest_noinline.c
echo ""

echo "--- Zig (ReleaseFast) ---"
time zig build-exe calltest.zig -O ReleaseFast -femit-bin=calltest_zig 2>/dev/null
echo ""

echo "--- Rust (release) ---"
time rustc -O -o calltest_rust calltest.rs 2>/dev/null
echo ""

echo "--- Go ---"
time go build -o calltest_go calltest.go
echo ""

# --- Runtime ---
echo "=========================================="
echo "RUNTIME (3 runs each)"
echo "=========================================="
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

run_bench "AILang (with function call)" "./calltest_ailang.x"
run_bench "AILang (direct Add, no function)" "./calltest_direct.x"
run_bench "C (gcc -O0, no inlining)" "./calltest_c_o0"
run_bench "C (gcc -O2, inlined)" "./calltest_c_o2"
run_bench "C (gcc -O3, inlined)" "./calltest_c_o3"
run_bench "C (gcc -O3, forced noinline)" "./calltest_c_noinline"
run_bench "Zig (ReleaseFast, inlined)" "./calltest_zig"
run_bench "Rust (release, inlined)" "./calltest_rust"
run_bench "Go" "./calltest_go"

echo "=========================================="
echo "BENCHMARK COMPLETE"
echo "=========================================="
echo ""
echo "KEY COMPARISONS:"
echo "  AILang function vs AILang direct = your call overhead"
echo "  AILang function vs C noinline = apples-to-apples (no inlining either side)"
echo "  C noinline vs C O3 = what inlining is actually worth"
echo "=========================================="