#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// =============================================================================
// RDTSC cycle counter
// =============================================================================
static inline uint64_t rdtsc() {
    uint32_t lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

static void perf_report(const char* label, uint64_t cycles) {
    printf("[PERF] %s: %llu cycles\n", label, (unsigned long long)cycles);
}

// =============================================================================
// TEST 1: Prime Sieve
// =============================================================================
static int bench_primes() {
    uint64_t t0 = rdtsc();
    int limit = 1000000;
    int count = 0;
    int n = 2;
    while (n < limit) {
        int is_prime = 1;
        int i = 2;
        while (i * i <= n) {
            if (n % i == 0) {
                is_prime = 0;
            }
            i++;
        }
        if (is_prime) count++;
        n++;
    }
    perf_report("primes_total", rdtsc() - t0);
    return count;
}

// =============================================================================
// TEST 2: Integer Arithmetic Stress
// =============================================================================
static int bench_arithmetic() {
    uint64_t t0 = rdtsc();
    long long result = 0;
    for (int i = 1; i < 10000000; i++) {
        long long a = (long long)i * 31337;
        long long b = a % 99991;
        long long c = b ^ (i << 3);
        long long d = c & 0xFFFF;
        result ^= (d + i);
    }
    perf_report("arithmetic", rdtsc() - t0);
    return (int)result;
}

// =============================================================================
// TEST 3: Memory Sequential
// =============================================================================
static long long bench_mem_sequential() {
    int size = 10000000;
    long long* buf = (long long*)malloc(size * sizeof(long long));

    uint64_t t0 = rdtsc();

    uint64_t tw = rdtsc();
    for (int i = 0; i < size; i++) {
        buf[i] = (long long)i * 7;
    }
    perf_report("mem_seq_write", rdtsc() - tw);

    uint64_t tr = rdtsc();
    long long sum = 0;
    for (int i = 0; i < size; i++) {
        sum += buf[i];
    }
    perf_report("mem_seq_read", rdtsc() - tr);

    free(buf);
    perf_report("mem_seq_total", rdtsc() - t0);
    return sum;
}

// =============================================================================
// TEST 4: Memory Random
// =============================================================================
static long long bench_mem_random() {
    int size = 1000000;
    long long* buf = (long long*)malloc(size * sizeof(long long));

    uint64_t t0 = rdtsc();

    uint64_t tf = rdtsc();
    for (int i = 0; i < size; i++) {
        buf[i] = i;
    }
    perf_report("mem_random_fill", rdtsc() - tf);

    uint64_t tr = rdtsc();
    long long sum = 0;
    for (int i = 0; i < size; i++) {
        int idx = ((long long)i * 1000003) % size;
        sum += buf[idx];
    }
    perf_report("mem_random_read", rdtsc() - tr);

    free(buf);
    perf_report("mem_random_total", rdtsc() - t0);
    return sum;
}

// =============================================================================
// TEST 5: Recursive Fibonacci
// =============================================================================
static long long fib(int n) {
    if (n < 2) return n;
    return fib(n-1) + fib(n-2);
}

static long long bench_fibonacci() {
    uint64_t t0 = rdtsc();
    long long result = 0;
    for (int i = 0; i < 10; i++) {
        result += fib(35);
    }
    perf_report("fibonacci", rdtsc() - t0);
    return result;
}

// =============================================================================
// TEST 6: String Operations
// =============================================================================
static int bench_strings() {
    uint64_t t0 = rdtsc();
    int count = 0;
    char buf[32];
    for (int i = 0; i < 100000; i++) {
        // concat
        strcpy(buf, "Hello");
        strcat(buf, " World");
        // toupper
        for (int j = 0; buf[j]; j++) {
            if (buf[j] >= 'a' && buf[j] <= 'z')
                buf[j] -= 32;
        }
        // length check
        if (strlen(buf) == 11) count++;
    }
    perf_report("strings_total", rdtsc() - t0);
    return count;
}

// =============================================================================
// TEST 7: Bubble Sort
// =============================================================================
static long long bench_bubblesort() {
    int size = 10000;
    long long* buf = (long long*)malloc(size * sizeof(long long));

    uint64_t t0 = rdtsc();

    uint64_t tf = rdtsc();
    for (int i = 0; i < size; i++) {
        buf[i] = size - i;
    }
    perf_report("bubblesort_fill", rdtsc() - tf);

    uint64_t ts = rdtsc();
    for (int i = 0; i < size; i++) {
        for (int j = 0; j < size - i - 1; j++) {
            if (buf[j] > buf[j+1]) {
                long long tmp = buf[j];
                buf[j] = buf[j+1];
                buf[j+1] = tmp;
            }
        }
    }
    perf_report("bubblesort_sort", rdtsc() - ts);

    uint64_t tv = rdtsc();
    long long sum = 0;
    for (int i = 0; i < size; i++) {
        sum += buf[i];
    }
    perf_report("bubblesort_verify", rdtsc() - tv);

    free(buf);
    perf_report("bubblesort_total", rdtsc() - t0);
    return sum;
}

// =============================================================================
// TEST 8: Matrix Multiply 64x64
// =============================================================================
static long long bench_matmul() {
    int N = 64;
    int sz = N * N;
    long long* a = (long long*)malloc(sz * sizeof(long long));
    long long* b = (long long*)malloc(sz * sizeof(long long));
    long long* c = (long long*)malloc(sz * sizeof(long long));

    uint64_t t0 = rdtsc();

    uint64_t tf = rdtsc();
    for (int i = 0; i < sz; i++) {
        a[i] = i + 1;
        b[i] = sz - i;
        c[i] = 0;
    }
    perf_report("matmul_fill", rdtsc() - tf);

    uint64_t tc = rdtsc();
    for (int row = 0; row < N; row++) {
        for (int col = 0; col < N; col++) {
            long long sum = 0;
            for (int k = 0; k < N; k++) {
                sum += a[row * N + k] * b[k * N + col];
            }
            c[row * N + col] = sum;
        }
    }
    perf_report("matmul_compute", rdtsc() - tc);

    uint64_t tv = rdtsc();
    long long total = 0;
    for (int i = 0; i < sz; i++) {
        total += c[i];
    }
    perf_report("matmul_verify", rdtsc() - tv);

    free(a); free(b); free(c);
    perf_report("matmul_total", rdtsc() - t0);
    return total;
}

// =============================================================================
// TEST 9: Allocation Speed
// =============================================================================
static void bench_allocation() {
    int iterations = 10000000;

    // Sequential alloc no free
    uint64_t t0 = rdtsc();
    void* last = NULL;
    for (int i = 0; i < iterations; i++) {
        void* ptr = malloc(64);
        *(char*)ptr = 1;
        last = ptr;
    }
    perf_report("alloc_sequential", rdtsc() - t0);
    (void)last;

    // Alloc/free cycle
    uint64_t t1 = rdtsc();
    for (int i = 0; i < iterations; i++) {
        void* ptr = malloc(64);
        *(char*)ptr = 1;
        free(ptr);
    }
    perf_report("alloc_free_cycle", rdtsc() - t1);

    // Mixed sizes
    uint64_t t2 = rdtsc();
    for (int i = 0; i < iterations; i++) {
        int mod = i % 3;
        void* ptr;
        if (mod == 0) {
            ptr = malloc(64);
            *(char*)ptr = 1;
            free(ptr);
        } else if (mod == 1) {
            ptr = malloc(128);
            *(char*)ptr = 1;
            free(ptr);
        } else {
            ptr = malloc(256);
            *(char*)ptr = 1;
            free(ptr);
        }
    }
    perf_report("alloc_mixed_sizes", rdtsc() - t2);

    // Batch alloc then free
    uint64_t t3 = rdtsc();
    int batch_size = 100000;
    void** ptrs = (void**)malloc(batch_size * sizeof(void*));
    for (int outer = 0; outer < 100; outer++) {
        for (int i = 0; i < batch_size; i++) {
            ptrs[i] = malloc(64);
            *(char*)ptrs[i] = 1;
        }
        for (int i = 0; i < batch_size; i++) {
            free(ptrs[i]);
        }
    }
    free(ptrs);
    perf_report("alloc_batch", rdtsc() - t3);
}

// =============================================================================
// MAIN
// =============================================================================
int main() {
    printf("=== C Benchmark Suite (RDTSC) ===\n\n");

    printf("1. Prime Sieve (1M)... ");
    int r1 = bench_primes();
    printf("Primes: %d\n", r1);

    printf("2. Integer Arithmetic (10M)... ");
    int r2 = bench_arithmetic();
    printf("Result: %d\n", r2);

    printf("3. Memory Sequential (10M)... ");
    long long r3 = bench_mem_sequential();
    printf("Sum: %lld\n", r3);

    printf("4. Memory Random (1M)... ");
    long long r4 = bench_mem_random();
    printf("Sum: %lld\n", r4);

    printf("5. Fibonacci Fib(35)x10... ");
    long long r5 = bench_fibonacci();
    printf("Result: %lld\n", r5);

    printf("6. String Ops (100K)... ");
    int r6 = bench_strings();
    printf("Count: %d\n", r6);

    printf("7. Bubble Sort (10K)... ");
    long long r7 = bench_bubblesort();
    printf("Sum: %lld\n", r7);

    printf("8. Matrix Multiply (64x64)... ");
    long long r8 = bench_matmul();
    printf("Checksum: %lld\n", r8);

    printf("9. Allocation Speed (10M each)...\n");
    bench_allocation();

    printf("\n=== Complete ===\n");
    return 0;
}