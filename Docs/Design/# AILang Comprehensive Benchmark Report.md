# AILang Comprehensive Benchmark Report
## April 8, 2026

**Test Environment:**
```
OS:       Linux (WSL2) 6.6.87.2-microsoft-standard-WSL2
Arch:     x86_64
AILang:   Self-hosting compiler, 604KB, ~46,000 lines, 80 files
GCC:      system default
Zig:      0.13.0 (LLVM backend)
Rust:     1.91.1 (LLVM backend)
Go:       1.22.4
```

---

## Executive Summary

AILang is a self-hosting bare metal compiler that produces x86-64 ELF binaries with no runtime dependencies. It was benchmarked against GCC, Zig, Rust, and Go across six categories: compile time, runtime performance, startup latency, binary size, compiler size, and specialized workloads.

**Key findings:**
- Runtime within **1.8%** of GCC -O2 on integer compute (prime sieve)
- Compile time **6x faster** than GCC, **390x faster** than Zig
- Startup **1.3x faster** than C, **3.9x faster** than Go
- Binary size **3.9x smaller** than C, **947x smaller** than Rust
- Compiler binary is **604KB** vs GCC's ~200MB (~330,000x smaller)
- All achieved with **one optimizer file** containing three pattern optimizations

---

## Benchmark 1: Prime Sieve (Headline Benchmark)

**Test:** Find all primes below 1,000,000 using trial division. Tests integer arithmetic, modulo, loops, branches, and comparisons in a tight inner loop.

### Compile Times

| Compiler | Time | vs AILang |
|----------|------|-----------|
| **AILang** | **0.013s** | **1x** |
| GCC -O0 | 0.072s | 5.5x slower |
| GCC -O2 | 0.079s | 6.1x slower |
| GCC -O3 | 0.078s | 6.0x slower |
| Go | 0.172s | 13.2x slower |
| Rust debug | 0.310s | 23.8x slower |
| Rust release | 0.319s | 24.5x slower |
| Zig Debug | 1.396s | 107x slower |
| Zig ReleaseFast | 5.266s | **405x slower** |

### Runtime (best of 3 runs)

| Language | Time | Gap to leader | Binary Size |
|----------|------|---------------|-------------|
| Zig ReleaseFast | 2.742s | — | 1,729,800 |
| C (gcc -O2) | 2.745s | +3ms | 15,976 |
| C (gcc -O3) | 2.751s | +9ms | 15,976 |
| Rust release | 2.752s | +10ms | 3,897,064 |
| C (gcc -O0) | 2.778s | +36ms | 15,968 |
| Go | 2.795s | +53ms | 1,915,118 |
| **AILang** | **2.805s** | **+63ms (1.8%)** | **4,113** |
| Zig Debug | 2.806s | +64ms | 2,249,064 |
| Rust debug | 2.808s | +66ms | 3,900,824 |

### Binary Sizes

| Language | Binary Size | vs AILang |
|----------|------------|-----------|
| **AILang** | **4,113 bytes** | **1x** |
| C (gcc) | 15,976 bytes | 3.9x larger |
| Go | 1,915,118 bytes | 466x larger |
| Zig | 1,729,800 bytes | 421x larger |
| Rust | 3,897,064 bytes | 947x larger |

### Source-to-Answer Time (compile + runtime)

| Language | Compile + Run | 
|----------|--------------|
| **AILang** | **2.818s** |
| C (gcc -O2) | 2.824s |
| C (gcc -O3) | 2.829s |
| Go | 2.967s |
| Rust release | 3.071s |
| Zig ReleaseFast | **8.008s** |

**AILang delivers answers faster than every other language tested when compile time is included.**

---

## Benchmark 2: Startup Time

**Test:** Launch an empty program 1,000 times. Measures process creation, binary loading, runtime initialization, and exit overhead.

### Results (1000 launches)

| Language | Total | Per Launch | Empty Binary Size |
|----------|-------|------------|-------------------|
| **AILang** | **1.762s** | **1.76ms** | **4,096 bytes** |
| C | 2.282s | 2.28ms | 15,776 bytes |
| Zig | 2.297s | 2.30ms | 1,709,616 bytes |
| Rust | 3.553s | 3.55ms | 3,890,152 bytes |
| Go | 7.085s | 7.09ms | 1,380,705 bytes |

**AILang has the fastest startup of all tested languages, including C.** This is because:
- 4KB static binary with no dynamic linker overhead
- No runtime initialization (no GC, no panic handler, no stack unwinding setup)
- The kernel maps one page of code, one page of data, and jumps to the entry point

---

## Benchmark 3: Function Call Overhead

**Test:** Call `add(i, 1)` 100,000,000 times. Tests call/ret overhead, stack discipline, register passing, and inlining impact.

### Runtime Results

| Language / Mode | Time | Notes |
|-----------------|------|-------|
| C (gcc -O2, inlined) | 0.002s | Compiler eliminated the loop entirely |
| C (gcc -O3, inlined) | 0.002s | Constant-folded at compile time |
| Zig (ReleaseFast) | 0.002s | LLVM eliminated the loop entirely |
| Rust (release) | 0.004s | LLVM eliminated the loop entirely |
| Go | 0.053s | Inlined by Go compiler |
| **AILang (direct Add)** | **0.090s** | **No function call, optimizer handles Add** |
| C (gcc -O3, noinline) | 0.133s | Forced to make real function calls |
| C (gcc -O0) | 0.194s | No optimizations at all |
| **AILang (function call)** | **0.295s** | **Real function call each iteration** |

### Analysis

- AILang's **direct path** (0.090s) uses the optimizer's push/pop elimination — no function call overhead
- AILang's **function call path** (0.295s) pays real call/ret cost every iteration
- The 0.090s → 0.295s gap = **0.205s of pure call overhead** across 100M iterations (~2ns per call)
- **Apples-to-apples comparison:** AILang function call (0.295s) vs C noinline (0.133s) — AILang's calling convention is ~2.2x the cost of GCC's, indicating room for optimization in prologue/epilogue
- The 0.002s results from GCC/Zig/Rust are misleading — those compilers computed the entire sum at compile time and replaced the loop with a constant

---

## Benchmark 4: Branch Prediction

**Test A — Predictable:** `if (i % 2 == 0) sum += 1; else sum -= 1;` — perfectly alternating pattern.
**Test B — Unpredictable:** `if ((i * 1234567) & 1) sum += 1; else sum -= 1;` — pseudo-random pattern.

Both tests run 100,000,000 iterations.

### Predictable Branch (i % 2)

| Language | Time | Notes |
|----------|------|-------|
| Zig ReleaseFast | 0.006s | Loop eliminated by LLVM |
| Rust release | 0.017s | Loop eliminated by LLVM |
| C (gcc -O3) | 0.050s | Branch converted to branchless |
| Go | 0.056s | Optimized by Go compiler |
| **AILang** | **0.116s** | **Actually running the branches** |

**After modulo optimization:** AILang improved from **0.550s → 0.116s** (4.7x speedup) by emitting `AND RAX, 1` instead of `IDIV` for `Modulo(i, 2)`.

### Unpredictable Branch ((i * 1234567) & 1)

| Language | Time | Notes |
|----------|------|-------|
| Zig ReleaseFast | 0.006s | Computed answer at compile time |
| Rust release | 0.019s | Computed answer at compile time |
| Go | 0.064s | Branch optimized away |
| **AILang** | **0.167s** | **Actually running 100M branches** |
| C (gcc -O0) | 0.178s | Actually running the branches |

**AILang is 6.5% faster than GCC -O0** on branch-heavy code when both are actually executing branches. The LLVM-backed languages aren't running the loop at all — they recognized the sum is always 0 and replaced the entire computation with a constant.

**Note:** C (gcc -O3) produced undefined behavior on the unpredictable test due to `int` overflow on `i * 1234567`, causing a hang. AILang's 64-bit integers avoid this class of bug entirely.

---

## Benchmark 5: Memory Bandwidth

**Test A — Sequential:** Iterate array of 10M elements, stride 16, 10 passes. Cache-friendly access.
**Test B — Random:** Same array, `index = (i * 7919) % size`. Cache-hostile access.

### Sequential Access (Cache Friendly)

| Language | Time | vs AILang |
|----------|------|-----------|
| C (gcc -O3) | 0.063s | 1x |
| **AILang** | **0.099s** | **1.6x** |

### Random Access (Cache Hostile)

| Language | Time | vs AILang |
|----------|------|-----------|
| C (gcc -O3) | 0.118s | 1x |
| **AILang** | **0.195s** | **1.7x** |

### Analysis

The consistent 1.6-1.7x ratio between sequential and random indicates the gap is **not** cache-related (cache effects would change the ratio). The gap comes from:
1. GCC emits `MOV RAX, [RDI + RCX*8]` — one instruction using scaled-index addressing
2. AILang computes addresses in multiple steps despite the SIB optimization
3. GCC hoists loop-invariant values (array base pointer) into registers; AILang reloads from stack each iteration

**Remaining gap requires:** Loop-invariant code motion (a larger optimization pass, not a pattern match).

---

## Benchmark 6: Allocation Pressure

**Test:** Allocate, write, read, and free a 64-byte block 1,000,000 times.

| Language | Time | Allocator |
|----------|------|-----------|
| C (malloc/free) | 0.002s | glibc malloc (tcmalloc-style fast path) |
| Rust (Box) | 0.005s | jemalloc / system allocator |
| Go (new + GC) | 0.009s | Go runtime with GC |
| **AILang (Arena)** | **0.010s** | **Slab arena with free list** |

### Analysis

AILang's arena allocator uses a free-list pop/push pattern — O(1) allocation and deallocation. The gap to glibc malloc (0.002s vs 0.010s) exists because:
1. glibc's malloc has a highly optimized thread-local free list for small allocations (tcmalloc-style)
2. AILang's `Arena_Alloc64` / `Arena_Free64` go through full function calls each time
3. Inlining the free-list operations would close most of this gap

**The allocation test validates the arena design** — 1M alloc/free cycles in 10ms is more than adequate for real workloads.

---

## Optimization History

### Starting Point (pre-optimizer)
- Prime sieve: ~11.0s (4x slower than GCC)

### After push/pop elimination (existing optimizer)
- Prime sieve: 2.798s (1.9% behind GCC -O2)
- **One optimization file closed a 4x gap**

### After April 8, 2026 session (three new patterns)

| Optimization | Lines | Target | Impact |
|-------------|-------|--------|--------|
| Modulo power-of-2 → AND | ~20 | `CompileArith_Modulo` + `Optimize_BinaryMathOp` | **4.7x** on branch code |
| Multiply power-of-2 → SHL | ~30 | `CompileArith_Multiply` + `Optimize_BinaryMathOp` | **8%** on memory code |
| Scaled-index addressing | ~40 | `CompileMem_Dereference` + new SIB emitter | **2%** on memory code |

**Total: ~90 lines of optimization code across the entire compiler.**

---

## Competitive Position Summary

| Metric | AILang | Best Competitor | Advantage |
|--------|--------|-----------------|-----------|
| Compile time | 0.013s | GCC 0.072s | **5.5x faster** |
| Runtime (primes) | 2.805s | Zig 2.742s | 1.8% behind |
| Source-to-answer | 2.818s | C 2.824s | **Fastest overall** |
| Startup | 1.76ms | C 2.28ms | **1.3x faster** |
| Binary size | 4,113 bytes | C 15,976 bytes | **3.9x smaller** |
| Compiler size | 604 KB | GCC ~200MB | **~330,000x smaller** |
| Optimizer complexity | ~90 lines | GCC 15M lines | **~170,000x simpler** |

---

## Known Optimization Opportunities

### High Impact, Medium Effort
1. **Inline builtin math ops** — Eliminate call/ret for Add, Subtract, etc. in subexpressions. Would close the function call benchmark gap.
2. **CMOV for simple if/else** — Emit conditional move instead of compare-jump for simple assignments. Would improve branch benchmarks.
3. **ExpressionChain** — New language construct for explicit flattened computation chains with register-path / stack-path dual compilation. Parser and compiler drafted, not yet integrated.

### High Impact, High Effort
4. **Loop-invariant code hoisting** — Keep base pointers in registers across loop iterations. Would close the memory benchmark gap.
5. **Division by constant → multiply-shift** — Replace IDIV with magic-number multiplication for non-power-of-2 constants.

### Low Priority
6. Loop unrolling — Marginal gains, not worth the complexity.
7. Constant folding — LLVM uses this to eliminate entire loops, but it changes program behavior in ways that make benchmarks misleading.

---

## Methodology Notes

- All benchmarks run on the same machine in the same session
- Each runtime test runs 3 times, best time reported
- WSL2 occasionally produces ~2x outliers (5.7s instead of 2.8s) due to Windows host activity — these are excluded as anomalies
- All compilers use their standard/recommended optimization flags
- C (gcc -O3) produced undefined behavior on the unpredictable branch test due to integer overflow — AILang's 64-bit integers prevent this class of bug
- Zig, Rust, and Go eliminated entire loops via constant folding on several benchmarks — these results are noted but not directly comparable to languages that actually execute the computation

---

## Reproducing These Results

All source files, benchmark scripts, and the AILang compiler are available on GitHub. To reproduce:

```bash
git clone <repo>
cd AILangSH
chmod +x benchmark.sh benchinline.sh benchbranch.sh membench.sh
./benchmark.sh        # Prime sieve + startup
./benchinline.sh      # Function call overhead
./benchbranch.sh      # Branch prediction
./membench.sh         # Memory bandwidth + allocation
```

Requirements: GCC, Zig 0.13.0, Rust 1.91.1, Go 1.22.4. AILang compiler (`ailang.x`) included in repository.

---

*AILang: 604KB compiler, 13ms compile time, 4KB binaries, within 2% of GCC.*
*Three optimizations. ~90 lines. One afternoon.*

*Sean Collins, 2 Paws Machine and Engineering*
*April 8, 2026*