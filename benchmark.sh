#!/bin/bash
# ============================================
# Prime Sieve Benchmark v3
# Compile Time + Runtime + Startup Time
# ============================================

echo "=========================================="
echo "PRIME SIEVE BENCHMARK - 1,000,000"
echo "$(uname -a)"
echo "$(date)"
echo "=========================================="
echo ""

# --- Create source files ---
cat > primetest.zig << 'ZIGEOF'
const std = @import("std");

pub fn main() !void {
    const limit: i64 = 1000000;
    var count: i64 = 0;
    var n: i64 = 2;

    while (n < limit) : (n += 1) {
        var is_prime: bool = true;
        var i: i64 = 2;
        while (i * i <= n) : (i += 1) {
            if (@mod(n, i) == 0) {
                is_prime = false;
            }
        }
        if (is_prime) count += 1;
    }

    const stdout = std.io.getStdOut().writer();
    try stdout.print("Primes found: {}\n", .{count});
}
ZIGEOF

cat > primetest.rs << 'RUSTEOF'
fn main() {
    let limit = 1000000;
    let mut count = 0;

    for n in 2..limit {
        let mut is_prime = true;
        let mut i = 2;
        while i * i <= n {
            if n % i == 0 {
                is_prime = false;
            }
            i += 1;
        }
        if is_prime {
            count += 1;
        }
    }

    println!("Primes found: {}", count);
}
RUSTEOF

cat > primetest.go << 'GOEOF'
package main

import "fmt"

func main() {
    limit := 1000000
    count := 0

    for n := 2; n < limit; n++ {
        isPrime := true
        for i := 2; i*i <= n; i++ {
            if n%i == 0 {
                isPrime = false
            }
        }
        if isPrime {
            count++
        }
    }

    fmt.Printf("Primes found: %d\n", count)
}
GOEOF

# --- Empty programs for startup timing ---
echo 'int main() { return 0; }' > empty.c

cat > empty.zig << 'ZIGEOF2'
pub fn main() void {}
ZIGEOF2

echo 'fn main() {}' > empty.rs

cat > empty.go << 'GOEOF2'
package main
func main() {}
GOEOF2

# --- Clean old binaries ---
echo "--- Cleaning old binaries ---"
rm -f primes_ailang.x primes_c_o0 primes_c_o2 primes_c_o3
rm -f primes_zig primes_zig_debug primes_rust primes_rust_debug primes_go
rm -f primetest.o primes_zig.o primes_zig_debug.o
rm -f empty_c empty_zig empty_rust empty_go empty_ailang.x
echo ""

# ==========================================
# COMPILE TIMES
# ==========================================
echo "=========================================="
echo "COMPILE TIMES"
echo "=========================================="
echo ""

echo "--- AILang ---"
time ./ailang.x primetest.ailang primes_ailang.x > /dev/null 2>&1
echo ""

echo "--- C (gcc -O0) ---"
time gcc -O0 -o primes_c_o0 primetestC.c
echo ""

echo "--- C (gcc -O2) ---"
time gcc -O2 -o primes_c_o2 primetestC.c
echo ""

echo "--- C (gcc -O3) ---"
time gcc -O3 -o primes_c_o3 primetestC.c
echo ""

echo "--- Zig (ReleaseFast) ---"
time zig build-exe primetest.zig -O ReleaseFast -femit-bin=primes_zig 2>/dev/null
echo ""

echo "--- Zig (Debug) ---"
time zig build-exe primetest.zig -O Debug -femit-bin=primes_zig_debug 2>/dev/null
echo ""

echo "--- Rust (release) ---"
time rustc -O -o primes_rust primetest.rs 2>/dev/null
echo ""

echo "--- Rust (debug) ---"
time rustc -o primes_rust_debug primetest.rs 2>/dev/null
echo ""

echo "--- Go ---"
time go build -o primes_go primetest.go
echo ""

# ==========================================
# BINARY SIZES
# ==========================================
echo "=========================================="
echo "BINARY SIZES"
echo "=========================================="
echo ""
ls -la primes_ailang.x primes_c_o0 primes_c_o2 primes_c_o3 primes_zig primes_zig_debug primes_rust primes_rust_debug primes_go 2>/dev/null | awk '{printf "  %-25s %10s bytes\n", $NF, $5}'

# ==========================================
# RUNTIME
# ==========================================
echo ""
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

run_bench "AILang (604KB compiler)" "./primes_ailang.x"
run_bench "C (gcc -O0)" "./primes_c_o0"
run_bench "C (gcc -O2)" "./primes_c_o2"
run_bench "C (gcc -O3)" "./primes_c_o3"
run_bench "Zig (ReleaseFast / LLVM)" "./primes_zig"
run_bench "Zig (Debug)" "./primes_zig_debug"
run_bench "Rust (release / LLVM)" "./primes_rust"
run_bench "Rust (debug)" "./primes_rust_debug"
run_bench "Go" "./primes_go"

# ==========================================
# STARTUP TIME (1000 iterations)
# ==========================================
echo "=========================================="
echo "STARTUP TIME (1000 empty runs)"
echo "=========================================="
echo ""

# Compile empty programs
gcc -O2 -o empty_c empty.c
zig build-exe empty.zig -O ReleaseFast -femit-bin=empty_zig 2>/dev/null
rustc -O -o empty_rust empty.rs 2>/dev/null
go build -o empty_go empty.go

# Create empty AILang program
cat > empty.ailang << 'AILANGEOF'
SubRoutine.Main {
}
RunTask(Main)
AILANGEOF
./ailang.x empty.ailang empty_ailang.x > /dev/null 2>&1

echo "--- Empty binary sizes ---"
ls -la empty_ailang.x empty_c empty_zig empty_rust empty_go 2>/dev/null | awk '{printf "  %-25s %10s bytes\n", $NF, $5}'
echo ""

echo "--- AILang (1000 runs) ---"
time for i in $(seq 1000); do ./empty_ailang.x; done
echo ""

echo "--- C (1000 runs) ---"
time for i in $(seq 1000); do ./empty_c; done
echo ""

echo "--- Zig (1000 runs) ---"
time for i in $(seq 1000); do ./empty_zig; done
echo ""

echo "--- Rust (1000 runs) ---"
time for i in $(seq 1000); do ./empty_rust; done
echo ""

echo "--- Go (1000 runs) ---"
time for i in $(seq 1000); do ./empty_go; done
echo ""

echo "=========================================="
echo "BENCHMARK COMPLETE"
echo "=========================================="