#!/bin/bash
# ============================================
# Branch Prediction Benchmark
# Test 1: Predictable (i % 2)
# Test 2: Unpredictable ((i * 1234567) & 1)
# ============================================

# Run from AiLangSH root regardless of invocation dir. Source files are
# regenerated via heredoc each run and land in CWD (= repo root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || { echo "Cannot cd to repo root"; exit 1; }

echo "=========================================="
echo "BRANCH PREDICTION BENCHMARK"
echo "100,000,000 iterations"
echo "$(uname -a)"
echo "$(date)"
echo "=========================================="
echo ""

# --- PREDICTABLE BRANCH ---

cat > branch_pred.c << 'EOF'
#include <stdio.h>
int main() {
    long sum = 0;
    for (int i = 0; i < 100000000; i++) {
        if (i % 2 == 0)
            sum += 1;
        else
            sum -= 1;
    }
    printf("Sum: %ld\n", sum);
    return 0;
}
EOF

cat > branch_pred.ailang << 'AILANGEOF'
SubRoutine.Main {
    sum = 0
    i = 0
    WhileLoop LessThan(i, 100000000) {
        IfCondition EqualTo(Modulo(i, 2), 0) ThenBlock: {
            sum = Add(sum, 1)
        } ElseBlock: {
            sum = Subtract(sum, 1)
        }
        i = Add(i, 1)
    }
    PrintMessage("Sum: ")
    PrintNumber(sum)
    PrintMessage("\n")
}
RunTask(Main)
AILANGEOF

cat > branch_pred.zig << 'EOF'
const std = @import("std");
pub fn main() !void {
    var sum: i64 = 0;
    var i: i64 = 0;
    while (i < 100000000) : (i += 1) {
        if (@mod(i, 2) == 0)
            sum += 1
        else
            sum -= 1;
    }
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Sum: {}\n", .{sum});
}
EOF

cat > branch_pred.rs << 'EOF'
fn main() {
    let mut sum: i64 = 0;
    for i in 0..100000000_i64 {
        if i % 2 == 0 {
            sum += 1;
        } else {
            sum -= 1;
        }
    }
    println!("Sum: {}", sum);
}
EOF

cat > branch_pred.go << 'EOF'
package main
import "fmt"
func main() {
    sum := 0
    for i := 0; i < 100000000; i++ {
        if i%2 == 0 {
            sum += 1
        } else {
            sum -= 1
        }
    }
    fmt.Printf("Sum: %d\n", sum)
}
EOF

# --- UNPREDICTABLE BRANCH ---

cat > branch_unpred.c << 'EOF'
#include <stdio.h>
int main() {
    long sum = 0;
    for (int i = 0; i < 100000000; i++) {
        if ((i * 1234567) & 1)
            sum += 1;
        else
            sum -= 1;
    }
    printf("Sum: %ld\n", sum);
    return 0;
}
EOF

cat > branch_unpred.ailang << 'AILANGEOF'
SubRoutine.Main {
    sum = 0
    i = 0
    WhileLoop LessThan(i, 100000000) {
        IfCondition EqualTo(BitwiseAnd(Multiply(i, 1234567), 1), 1) ThenBlock: {
            sum = Add(sum, 1)
        } ElseBlock: {
            sum = Subtract(sum, 1)
        }
        i = Add(i, 1)
    }
    PrintMessage("Sum: ")
    PrintNumber(sum)
    PrintMessage("\n")
}
RunTask(Main)
AILANGEOF

cat > branch_unpred.zig << 'EOF'
const std = @import("std");
pub fn main() !void {
    var sum: i64 = 0;
    var i: i64 = 0;
    while (i < 100000000) : (i += 1) {
        if ((i * 1234567) & 1 == 1)
            sum += 1
        else
            sum -= 1;
    }
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Sum: {}\n", .{sum});
}
EOF

cat > branch_unpred.rs << 'EOF'
fn main() {
    let mut sum: i64 = 0;
    for i in 0..100000000_i64 {
        if (i * 1234567) & 1 == 1 {
            sum += 1;
        } else {
            sum -= 1;
        }
    }
    println!("Sum: {}", sum);
}
EOF

cat > branch_unpred.go << 'EOF'
package main
import "fmt"
func main() {
    sum := 0
    for i := 0; i < 100000000; i++ {
        if (i*1234567)&1 == 1 {
            sum += 1
        } else {
            sum -= 1
        }
    }
    fmt.Printf("Sum: %d\n", sum)
}
EOF

# --- Clean ---
rm -f branch_pred_* branch_unpred_* *.o

# --- Compile ---
echo "=========================================="
echo "COMPILING"
echo "=========================================="
echo ""

echo "--- Predictable ---"
echo "AILang:"
time ./ailang.x branch_pred.ailang branch_pred_ailang.x > /dev/null 2>&1
echo "GCC -O3:"
time gcc -O3 -o branch_pred_c branch_pred.c
echo "Zig:"
time zig build-exe branch_pred.zig -O ReleaseFast -femit-bin=branch_pred_zig 2>/dev/null
echo "Rust:"
time rustc -O -o branch_pred_rust branch_pred.rs 2>/dev/null
echo "Go:"
time go build -o branch_pred_go branch_pred.go
echo ""

echo "--- Unpredictable ---"
echo "AILang:"
time ./ailang.x branch_unpred.ailang branch_unpred_ailang.x > /dev/null 2>&1
echo "GCC -O3:"
time gcc -O3 -o branch_unpred_c branch_unpred.c
echo "GCC -O3 noinline (apples to apples):"
time gcc -O0 -o branch_unpred_c_o0 branch_unpred.c
echo "Zig:"
time zig build-exe branch_unpred.zig -O ReleaseFast -femit-bin=branch_unpred_zig 2>/dev/null
echo "Rust:"
time rustc -O -o branch_unpred_rust branch_unpred.rs 2>/dev/null
echo "Go:"
time go build -o branch_unpred_go branch_unpred.go
echo ""

# --- Runtime ---
echo "=========================================="
echo "PREDICTABLE BRANCH (i % 2)"
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

run_bench "AILang" "./branch_pred_ailang.x"
run_bench "C (gcc -O3)" "./branch_pred_c"
run_bench "Zig (ReleaseFast)" "./branch_pred_zig"
run_bench "Rust (release)" "./branch_pred_rust"
run_bench "Go" "./branch_pred_go"

echo "=========================================="
echo "UNPREDICTABLE BRANCH ((i * 1234567) & 1)"
echo "=========================================="
echo ""

run_bench "AILang" "./branch_unpred_ailang.x"
run_bench "C (gcc -O3)" "./branch_unpred_c"
run_bench "C (gcc -O0)" "./branch_unpred_c_o0"
run_bench "Zig (ReleaseFast)" "./branch_unpred_zig"
run_bench "Rust (release)" "./branch_unpred_rust"
run_bench "Go" "./branch_unpred_go"

echo "=========================================="
echo "BENCHMARK COMPLETE"
echo "=========================================="
echo ""
echo "KEY: If predictable and unpredictable times are similar"
echo "across all languages, the CPU branch predictor dominates"
echo "and compiler tricks don't matter much."
echo "=========================================="