#!/usr/bin/env python3
"""
Deep cache/barrier diagnostic for the first-write-reads-0xFFFFFFFF bug.
Tests whether mfence, clflush, double-write, or read-first workarounds help.
Also checks the actual page table cache type via /proc/self/smaps.

Run as: sudo python3 gpu_cache_diag.py
"""
import mmap, os, struct, ctypes, ctypes.util

PCI = "/sys/bus/pci/devices"
BUS2 = "0000:02:00.0"
BUS1 = "0000:01:00.0"

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def wr32(mm, off, v):
    struct.pack_into('<I', mm, off, v & 0xFFFFFFFF)

# Load libc for mfence/clflush via inline asm
libc = ctypes.CDLL(ctypes.util.find_library('c'))

# We'll use ctypes to call mfence and clflush via small C snippets
# Actually, let's just compile a tiny helper
import tempfile, subprocess

helper_c = r"""
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <x86intrin.h>
#include <immintrin.h>

/* Write with sfence after */
void write32_sfence(volatile uint32_t *addr, uint32_t val) {
    *addr = val;
    _mm_sfence();
}

/* Write with mfence after */
void write32_mfence(volatile uint32_t *addr, uint32_t val) {
    *addr = val;
    _mm_mfence();
}

/* Read with lfence before */
uint32_t read32_lfence(volatile uint32_t *addr) {
    _mm_lfence();
    return *addr;
}

/* Read with mfence before */
uint32_t read32_mfence(volatile uint32_t *addr) {
    _mm_mfence();
    return *addr;
}

/* Write with clflush after */
void write32_clflush(volatile uint32_t *addr, uint32_t val) {
    *addr = val;
    _mm_clflush((void*)addr);
    _mm_mfence();
}

/* Non-temporal write (movnti) + sfence */
void write32_nt(volatile uint32_t *addr, uint32_t val) {
    _mm_stream_si32((int*)addr, (int)val);
    _mm_sfence();
}

/* Full barrier write-read test at a given offset in a mapped region */
int test_offset(void *base, size_t off, uint32_t pattern) {
    volatile uint32_t *addr = (volatile uint32_t*)((char*)base + off);

    /* Test 1: Normal write, mfence, read */
    *addr = pattern;
    _mm_mfence();
    uint32_t v1 = *addr;

    /* Test 2: movnti write, sfence, read */
    _mm_stream_si32((int*)addr, (int)(pattern ^ 0xFFFFFFFF));
    _mm_sfence();
    _mm_mfence();
    uint32_t v2 = *addr;

    /* Test 3: clflush after write */
    *addr = pattern;
    _mm_clflush((void*)addr);
    _mm_mfence();
    uint32_t v3 = *addr;

    /* Test 4: Double write */
    *addr = 0;
    _mm_mfence();
    *addr = pattern;
    _mm_mfence();
    uint32_t v4 = *addr;

    /* Test 5: Read first (prime the page), then write, then read */
    volatile uint32_t dummy = *addr;
    (void)dummy;
    _mm_mfence();
    *addr = pattern ^ 0x12345678;
    _mm_mfence();
    uint32_t v5 = *addr;

    uint32_t exp1 = pattern;
    uint32_t exp2 = pattern ^ 0xFFFFFFFF;
    uint32_t exp3 = pattern;
    uint32_t exp4 = pattern;
    uint32_t exp5 = pattern ^ 0x12345678;

    printf("  [0x%06zX] normal+mfence: 0x%08X %s\n", off, v1, v1==exp1?"OK":"FAIL");
    printf("  [0x%06zX] movnti+sfence: 0x%08X %s\n", off, v2, v2==exp2?"OK":"FAIL");
    printf("  [0x%06zX] write+clflush: 0x%08X %s\n", off, v3, v3==exp3?"OK":"FAIL");
    printf("  [0x%06zX] double-write:  0x%08X %s\n", off, v4, v4==exp4?"OK":"FAIL");
    printf("  [0x%06zX] read-first:    0x%08X %s\n", off, v5, v5==exp5?"OK":"FAIL");

    return (v1==exp1) + (v2==exp2) + (v3==exp3) + (v4==exp4) + (v5==exp5);
}

/* Pattern sweep: write N dwords, mfence, read them back */
int pattern_sweep(void *base, size_t start, int count) {
    volatile uint32_t *p = (volatile uint32_t*)((char*)base + start);
    int i;
    for (i = 0; i < count; i++)
        p[i] = 0xA5A50000 + i;
    _mm_mfence();
    int errors = 0;
    for (i = 0; i < count; i++) {
        if (p[i] != (uint32_t)(0xA5A50000 + i)) {
            if (errors < 3)
                printf("    [%d] exp=0x%08X got=0x%08X\n", i, 0xA5A50000+i, p[i]);
            errors++;
        }
    }
    return errors;
}

/* Double-write pattern sweep: write each twice */
int pattern_sweep_double(void *base, size_t start, int count) {
    volatile uint32_t *p = (volatile uint32_t*)((char*)base + start);
    int i;
    /* First pass: write zeros to prime */
    for (i = 0; i < count; i++)
        p[i] = 0;
    _mm_mfence();
    /* Second pass: write actual pattern */
    for (i = 0; i < count; i++)
        p[i] = 0xB00B0000 + i;
    _mm_mfence();
    int errors = 0;
    for (i = 0; i < count; i++) {
        if (p[i] != (uint32_t)(0xB00B0000 + i)) {
            if (errors < 3)
                printf("    [%d] exp=0x%08X got=0x%08X\n", i, 0xB00B0000+i, p[i]);
            errors++;
        }
    }
    return errors;
}

int main(int argc, char **argv) {
    const char *dev = argc > 1 ? argv[1] : "0000:02:00.0";
    char path[256];
    snprintf(path, sizeof(path), "/sys/bus/pci/devices/%s/resource0", dev);

    int fd = open(path, O_RDWR | O_SYNC);
    if (fd < 0) { perror("open resource0"); return 1; }

    size_t map_size = 2 * 1024 * 1024; /* 2MB */
    void *mm = mmap(NULL, map_size, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    if (mm == MAP_FAILED) { perror("mmap"); return 1; }

    printf("=== Cache/Barrier test on %s ===\n", dev);
    printf("  Mapped %s at VA %p, size 0x%zX\n\n", path, mm, map_size);

    /* Check smaps for this mapping */
    printf("=== /proc/self/smaps for this mapping ===\n");
    char smaps_line[512];
    FILE *sf = fopen("/proc/self/smaps", "r");
    if (sf) {
        int found = 0;
        while (fgets(smaps_line, sizeof(smaps_line), sf)) {
            if (strstr(smaps_line, "resource0")) found = 1;
            if (found) {
                printf("  %s", smaps_line);
                if (smaps_line[0] == 'V' && strstr(smaps_line, "VmFlags"))
                    { found = 0; printf("\n"); }
            }
        }
        fclose(sf);
    }

    printf("=== Per-offset barrier tests (fresh offsets) ===\n");
    int total_ok = 0;
    int total_tests = 0;
    size_t offsets[] = {0x1000, 0x2000, 0x4000, 0x8000, 0x10000, 0x80000, 0x100000};
    for (int i = 0; i < 7; i++) {
        if (offsets[i] + 4 <= map_size) {
            int ok = test_offset(mm, offsets[i], 0xDEADBEEF);
            total_ok += ok;
            total_tests += 5;
        }
    }
    printf("\n  Total: %d/%d passed\n", total_ok, total_tests);

    printf("\n=== Pattern sweep (256 DWORDs at 0x100000) ===\n");
    int e1 = pattern_sweep(mm, 0x100000, 256);
    printf("  Single-write sweep: %d/256 correct, %d errors\n", 256-e1, e1);

    printf("\n=== Double-write pattern sweep (256 DWORDs at 0x110000) ===\n");
    int e2 = pattern_sweep_double(mm, 0x110000, 256);
    printf("  Double-write sweep: %d/256 correct, %d errors\n", 256-e2, e2);

    printf("\n=== Large sweep: 4096 DWORDs (16KB) at 0x120000 ===\n");
    int e3 = pattern_sweep(mm, 0x120000, 4096);
    printf("  Single-write: %d/4096 correct, %d errors\n", 4096-e3, e3);
    int e4 = pattern_sweep_double(mm, 0x140000, 4096);
    printf("  Double-write: %d/4096 correct, %d errors\n", 4096-e4, e4);

    munmap(mm, map_size);
    close(fd);
    return 0;
}
"""

# Write, compile, and run the C helper
with open('/tmp/gpu_cache_test.c', 'w') as f:
    f.write(helper_c)

print("=== Compiling C cache/barrier test ===")
r = subprocess.run(
    ['gcc', '-O2', '-msse2', '-o', '/tmp/gpu_cache_test', '/tmp/gpu_cache_test.c'],
    capture_output=True, text=True
)
if r.returncode != 0:
    print(f"Compile failed: {r.stderr}")
    # Try with -march=native
    r = subprocess.run(
        ['gcc', '-O0', '-msse2', '-o', '/tmp/gpu_cache_test', '/tmp/gpu_cache_test.c'],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"Compile still failed: {r.stderr}")
        exit(1)

print("=== Ensuring MTRR fix is in place ===")
with open('/proc/mtrr', 'r') as f:
    mtrr = f.read()
    print(mtrr.strip())
if 'base=0x0b0000000' not in mtrr:
    print("  Adding UC MTRR for 0xB0000000...")
    with open('/proc/mtrr', 'w') as f:
        f.write("base=0xB0000000 size=0x10000000 type=uncachable")

print("\n=== Running on Bus 2 (compute — broken) ===")
r = subprocess.run(['/tmp/gpu_cache_test', BUS2], capture_output=True, text=True)
print(r.stdout)
if r.stderr:
    print(f"STDERR: {r.stderr}")

print("\n=== Running on Bus 1 (display — reference) ===")
r = subprocess.run(['/tmp/gpu_cache_test', BUS1], capture_output=True, text=True)
print(r.stdout)
if r.stderr:
    print(f"STDERR: {r.stderr}")
