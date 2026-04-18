#!/bin/bash
# ============================================
# Memory Bandwidth + Allocation Pressure
# Benchmarks 3 & 5 from ChatGPT's challenge
# ============================================

# Run from AiLangSH root regardless of invocation dir. Source files are
# regenerated via heredoc each run and land in CWD (= repo root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || { echo "Cannot cd to repo root"; exit 1; }


echo "=========================================="
echo "MEMORY & ALLOCATION BENCHMARKS"
echo "$(uname -a)"
echo "$(date)"
echo "=========================================="
echo ""

# ==========================================
# BENCHMARK 3: MEMORY BANDWIDTH / CACHE
# ==========================================

# --- Sequential access (cache friendly) ---
cat > mem_seq.c << 'EOF'
#include <stdio.h>
#include <stdlib.h>
int main() {
    int size = 10000000;
    long *arr = malloc(size * sizeof(long));
    for (int i = 0; i < size; i++) arr[i] = i;
    long sum = 0;
    for (int pass = 0; pass < 10; pass++) {
        for (int i = 0; i < size; i += 16)
            sum += arr[i];
    }
    printf("Sum: %ld\n", sum);
    free(arr);
    return 0;
}
EOF

cat > mem_seq.ailang << 'AILANGEOF'
LibraryImport.Arena

SubRoutine.Main {
    Arena_Init()
    size = 10000000

    arr = Arena_AllocGeneral(Multiply(size, 8))

    i = 0
    WhileLoop LessThan(i, size) {
        StoreValue(Add(arr, Multiply(i, 8)), i)
        i = Add(i, 1)
    }

    sum = 0
    pass = 0
    WhileLoop LessThan(pass, 10) {
        i = 0
        WhileLoop LessThan(i, size) {
            sum = Add(sum, Dereference(Add(arr, Multiply(i, 8))))
            i = Add(i, 16)
        }
        pass = Add(pass, 1)
    }

    PrintMessage("Sum: ")
    PrintNumber(sum)
    PrintMessage("\n")
}
RunTask(Main)
AILANGEOF

# --- Random access (cache hostile) ---
cat > mem_rand.c << 'EOF'
#include <stdio.h>
#include <stdlib.h>
int main() {
    int size = 10000000;
    long *arr = malloc(size * sizeof(long));
    for (int i = 0; i < size; i++) arr[i] = i;
    long sum = 0;
    for (int pass = 0; pass < 10; pass++) {
        for (int i = 0; i < size; i += 16) {
            int idx = (int)(((long)i * 7919) % size);
            sum += arr[idx];
        }
    }
    printf("Sum: %ld\n", sum);
    free(arr);
    return 0;
}
EOF

cat > mem_rand.ailang << 'AILANGEOF'
LibraryImport.Arena

SubRoutine.Main {
    Arena_Init()
    size = 10000000

    arr = Arena_AllocGeneral(Multiply(size, 8))

    i = 0
    WhileLoop LessThan(i, size) {
        StoreValue(Add(arr, Multiply(i, 8)), i)
        i = Add(i, 1)
    }

    sum = 0
    pass = 0
    WhileLoop LessThan(pass, 10) {
        i = 0
        WhileLoop LessThan(i, size) {
            idx = Modulo(Multiply(i, 7919), size)
            sum = Add(sum, Dereference(Add(arr, Multiply(idx, 8))))
            i = Add(i, 16)
        }
        pass = Add(pass, 1)
    }

    PrintMessage("Sum: ")
    PrintNumber(sum)
    PrintMessage("\n")
}
RunTask(Main)
AILANGEOF

# ==========================================
# BENCHMARK 5: ALLOCATION PRESSURE
# ==========================================

cat > alloc_pressure.c << 'EOF'
#include <stdio.h>
#include <stdlib.h>
int main() {
    long sum = 0;
    for (int i = 0; i < 1000000; i++) {
        long *p = malloc(64);
        *p = i;
        sum += *p;
        free(p);
    }
    printf("Sum: %ld\n", sum);
    return 0;
}
EOF

cat > alloc_pressure.ailang << 'AILANGEOF'
LibraryImport.Arena

SubRoutine.Main {
    Arena_Init()

    sum = 0
    i = 0
    WhileLoop LessThan(i, 1000000) {
        p = Arena_Alloc64()
        StoreValue(p, i)
        sum = Add(sum, Dereference(p))
        Arena_Free64(p)
        i = Add(i, 1)
    }

    PrintMessage("Sum: ")
    PrintNumber(sum)
    PrintMessage("\n")
}
RunTask(Main)
AILANGEOF

cat > alloc_pressure.go << 'EOF'
package main
import "fmt"
func main() {
    sum := 0
    for i := 0; i < 1000000; i++ {
        p := new(int)
        *p = i
        sum += *p
    }
    fmt.Printf("Sum: %d\n", sum)
}
EOF

cat > alloc_pressure.rs << 'EOF'
fn main() {
    let mut sum: i64 = 0;
    for i in 0..1000000_i64 {
        let p = Box::new(i);
        sum += *p;
    }
    println!("Sum: {}", sum);
}
EOF

# --- Clean ---
rm -f mem_seq_c mem_seq_ailang.x mem_rand_c mem_rand_ailang.x
rm -f alloc_c alloc_ailang.x alloc_go alloc_rust
rm -f *.o

# --- Compile ---
echo "=========================================="
echo "COMPILING"
echo "=========================================="
echo ""

echo "=== Memory Sequential ==="
echo "AILang:"
time ./ailang.x mem_seq.ailang mem_seq_ailang.x > /dev/null 2>&1
echo "GCC -O3:"
time gcc -O3 -o mem_seq_c mem_seq.c
echo ""

echo "=== Memory Random ==="
echo "AILang:"
time ./ailang.x mem_rand.ailang mem_rand_ailang.x > /dev/null 2>&1
echo "GCC -O3:"
time gcc -O3 -o mem_rand_c mem_rand.c
echo ""

echo "=== Allocation Pressure ==="
echo "AILang:"
time ./ailang.x alloc_pressure.ailang alloc_ailang.x > /dev/null 2>&1
echo "GCC -O3:"
time gcc -O3 -o alloc_c alloc_pressure.c
echo "Rust release:"
time rustc -O -o alloc_rust alloc_pressure.rs 2>/dev/null
echo "Go:"
time go build -o alloc_go alloc_pressure.go
echo ""

# --- Runtime ---
echo "=========================================="
echo "MEMORY SEQUENTIAL (cache friendly)"
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

run_bench "AILang" "./mem_seq_ailang.x"
run_bench "C (gcc -O3)" "./mem_seq_c"

echo "=========================================="
echo "MEMORY RANDOM (cache hostile)"
echo "=========================================="
echo ""

run_bench "AILang" "./mem_rand_ailang.x"
run_bench "C (gcc -O3)" "./mem_rand_c"

echo "=========================================="
echo "ALLOCATION PRESSURE (1M alloc/free cycles)"
echo "=========================================="
echo ""

run_bench "AILang (Arena slab)" "./alloc_ailang.x"
run_bench "C (malloc/free)" "./alloc_c"
run_bench "Rust (Box)" "./alloc_rust"
run_bench "Go (new + GC)" "./alloc_go"

echo "=========================================="
echo "BENCHMARK COMPLETE"
echo "=========================================="
echo ""
echo "KEY INSIGHTS:"
echo "  Sequential vs Random = cache miss cost"
echo "  AILang Arena vs malloc = allocator efficiency"
echo "  Arena_Alloc64/Free64 = free list pop/push vs syscall"
echo "=========================================="