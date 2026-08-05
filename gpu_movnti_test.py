#!/usr/bin/env python3
"""
Full VRAM test using movnti (non-temporal stores) on bus 2.
Proves that VRAM itself is fine — only the CPU cache path is broken.

Run as: sudo python3 gpu_movnti_test.py
"""
import subprocess, os, tempfile

BUS2 = "0000:02:00.0"
PCI = "/sys/bus/pci/devices"

helper_c = r"""
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <immintrin.h>
#include <time.h>

static inline void nt_wr32(volatile void *base, size_t off, uint32_t val) {
    _mm_stream_si32((int*)((char*)base + off), (int)val);
}

static inline uint32_t rd32(volatile void *base, size_t off) {
    _mm_mfence();
    return *(volatile uint32_t*)((char*)base + off);
}

int main(int argc, char **argv) {
    const char *dev = argc > 1 ? argv[1] : "0000:02:00.0";
    size_t map_size = argc > 2 ? (size_t)atol(argv[2]) : 16*1024*1024;
    char path[256];
    snprintf(path, sizeof(path), "/sys/bus/pci/devices/%s/resource0", dev);

    int fd = open(path, O_RDWR | O_SYNC);
    if (fd < 0) { perror("open"); return 1; }

    void *mm = mmap(NULL, map_size, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    if (mm == MAP_FAILED) { perror("mmap"); return 1; }

    printf("=== movnti VRAM test on %s (%zu MB mapped) ===\n\n", dev, map_size/(1024*1024));

    /* Test 1: Single write/read at various offsets */
    printf("--- Test 1: Single movnti write/read at offsets ---\n");
    int t1_ok = 0, t1_total = 0;
    size_t offsets[] = {0x1000, 0x2000, 0x4000, 0x10000, 0x100000,
                        0x200000, 0x400000, 0x800000};
    for (int i = 0; i < 8; i++) {
        if (offsets[i] + 4 > map_size) break;
        nt_wr32(mm, offsets[i], 0xDEADBEEF);
        _mm_sfence();
        uint32_t v1 = rd32(mm, offsets[i]);

        nt_wr32(mm, offsets[i], 0xCAFEBABE);
        _mm_sfence();
        uint32_t v2 = rd32(mm, offsets[i]);

        nt_wr32(mm, offsets[i], 0x12345678);
        _mm_sfence();
        uint32_t v3 = rd32(mm, offsets[i]);

        int ok = v1 == 0xDEADBEEF && v2 == 0xCAFEBABE && v3 == 0x12345678;
        t1_total++;
        if (ok) t1_ok++;
        printf("  [0x%07zX] 0x%08X 0x%08X 0x%08X %s\n",
               offsets[i], v1, v2, v3, ok ? "OK" : "FAIL");
    }
    printf("  Result: %d/%d passed\n\n", t1_ok, t1_total);

    /* Test 2: Pattern sweep — write 4096 DWORDs with movnti, read back */
    printf("--- Test 2: Pattern sweep (4096 DWORDs = 16KB) at 0x100000 ---\n");
    int count = 4096;
    for (int i = 0; i < count; i++) {
        nt_wr32(mm, 0x100000 + i*4, 0xA5A50000 + i);
    }
    _mm_sfence();

    int errs = 0;
    for (int i = 0; i < count; i++) {
        uint32_t got = rd32(mm, 0x100000 + i*4);
        uint32_t exp = 0xA5A50000 + i;
        if (got != exp) {
            if (errs < 3)
                printf("  [%d] exp=0x%08X got=0x%08X\n", i, exp, got);
            errs++;
        }
    }
    printf("  Result: %d/%d correct, %d errors\n\n", count-errs, count, errs);

    /* Test 3: Large sweep — 1MB */
    printf("--- Test 3: Large sweep (256K DWORDs = 1MB) at 0x200000 ---\n");
    if (0x200000 + 1024*1024 <= map_size) {
        count = 256 * 1024;
        for (int i = 0; i < count; i++) {
            nt_wr32(mm, 0x200000 + i*4, 0xBEEF0000 + (i & 0xFFFF));
        }
        _mm_sfence();

        errs = 0;
        for (int i = 0; i < count; i++) {
            uint32_t got = rd32(mm, 0x200000 + i*4);
            uint32_t exp = 0xBEEF0000 + (i & 0xFFFF);
            if (got != exp) {
                if (errs < 5)
                    printf("  [%d] off=0x%zX exp=0x%08X got=0x%08X\n",
                           i, (size_t)(0x200000 + i*4), exp, got);
                errs++;
            }
        }
        printf("  Result: %d/%d correct, %d errors\n\n", count-errs, count, errs);
    }

    /* Test 4: Cross-page coherency — write to many pages, read back */
    printf("--- Test 4: Cross-page (512 pages, 1 DWORD each) ---\n");
    int pages = 512;
    if ((size_t)pages * 4096 + 0x1000 <= map_size) {
        for (int p = 0; p < pages; p++) {
            nt_wr32(mm, 0x1000 + p * 4096, 0xFACE0000 + p);
        }
        _mm_sfence();

        errs = 0;
        for (int p = 0; p < pages; p++) {
            uint32_t got = rd32(mm, 0x1000 + p * 4096);
            uint32_t exp = 0xFACE0000 + p;
            if (got != exp) {
                if (errs < 5)
                    printf("  page %d off=0x%zX exp=0x%08X got=0x%08X\n",
                           p, (size_t)(0x1000 + p*4096), exp, got);
                errs++;
            }
        }
        printf("  Result: %d/%d pages correct, %d errors\n\n", pages-errs, pages, errs);
    }

    /* Test 5: Timing comparison */
    printf("--- Test 5: Timing (10000 iterations) ---\n");
    {
        struct timespec t0, t1;
        int iters = 10000;

        /* movnti write + sfence */
        clock_gettime(CLOCK_MONOTONIC, &t0);
        for (int i = 0; i < iters; i++) {
            nt_wr32(mm, 0x100000, i);
            _mm_sfence();
        }
        clock_gettime(CLOCK_MONOTONIC, &t1);
        long wr_ns = ((t1.tv_sec - t0.tv_sec)*1000000000L + (t1.tv_nsec - t0.tv_nsec)) / iters;

        /* read */
        clock_gettime(CLOCK_MONOTONIC, &t0);
        for (int i = 0; i < iters; i++) {
            volatile uint32_t v = rd32(mm, 0x100000);
            (void)v;
        }
        clock_gettime(CLOCK_MONOTONIC, &t1);
        long rd_ns = ((t1.tv_sec - t0.tv_sec)*1000000000L + (t1.tv_nsec - t0.tv_nsec)) / iters;

        /* write + read */
        clock_gettime(CLOCK_MONOTONIC, &t0);
        for (int i = 0; i < iters; i++) {
            nt_wr32(mm, 0x100000, i);
            _mm_sfence();
            volatile uint32_t v = rd32(mm, 0x100000);
            (void)v;
        }
        clock_gettime(CLOCK_MONOTONIC, &t1);
        long wr_rd_ns = ((t1.tv_sec - t0.tv_sec)*1000000000L + (t1.tv_nsec - t0.tv_nsec)) / iters;

        printf("  movnti+sfence: %ld ns/op\n", wr_ns);
        printf("  read:          %ld ns/op\n", rd_ns);
        printf("  write+read:    %ld ns/op\n\n", wr_rd_ns);
    }

    printf("=== SUMMARY ===\n");
    printf("  If all tests pass: VRAM hardware is FINE.\n");
    printf("  The bug is CPU write-caching (MTRR WB + PAT UC- = WC on AMD).\n");
    printf("  Fix: use movnti in the driver, or boot with 'nopat' kernel param.\n");

    munmap(mm, map_size);
    close(fd);
    return 0;
}
"""

with open('/tmp/gpu_movnti_test.c', 'w') as f:
    f.write(helper_c)

print("Compiling...")
r = subprocess.run(
    ['gcc', '-O2', '-msse2', '-o', '/tmp/gpu_movnti_test', '/tmp/gpu_movnti_test.c'],
    capture_output=True, text=True
)
if r.returncode != 0:
    print(f"Compile failed: {r.stderr}")
    exit(1)

print("Running on bus 2 (16MB)...")
r = subprocess.run(['/tmp/gpu_movnti_test', BUS2, str(16*1024*1024)],
                   capture_output=True, text=True)
print(r.stdout)
if r.stderr:
    print(f"STDERR: {r.stderr}")
