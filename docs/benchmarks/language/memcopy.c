/* glibc memcpy/memset/memcmp/memchr, plus an SSE2 copy of the same widths.
   MemCompare's contract is 0 or 1. Overlap is not tested. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <emmintrin.h>

static long long stamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static void barrier(void) {
    asm volatile("" ::: "memory");
}

__attribute__((target("sse2")))
static void sse2_copy(unsigned char *dst, const unsigned char *src, size_t n) {
    size_t i = 0;
    while (n - i >= 16) {
        __m128i v = _mm_loadu_si128((const __m128i *)(src + i));
        _mm_storeu_si128((__m128i *)(dst + i), v);
        i += 16;
    }
    while (i < n) {
        dst[i] = src[i];
        i++;
    }
}

__attribute__((target("sse2")))
static void sse2_set(unsigned char *dst, unsigned char val, size_t n) {
    __m128i v = _mm_set1_epi8((char)val);
    size_t i = 0;
    while (n - i >= 16) {
        _mm_storeu_si128((__m128i *)(dst + i), v);
        i += 16;
    }
    while (i < n) {
        dst[i] = val;
        i++;
    }
}

static int check_copy(unsigned char *src, unsigned char *dst, size_t n) {
    size_t i;
    int fails = 0;
    memset(dst, 255, n);
    for (i = 0; i < n; i++) src[i] = (unsigned char)(i & 255);
    memcpy(dst, src, n);
    for (i = 0; i < n; i++) {
        if (dst[i] != (unsigned char)(i & 255)) fails++;
    }
    return fails;
}

static int check_set(unsigned char *dst, size_t n, unsigned char val) {
    size_t i;
    int fails = 0;
    memset(dst, val, n);
    for (i = 0; i < n; i++) {
        if (dst[i] != val) fails++;
    }
    return fails;
}

int main(void) {
    static unsigned char src[1100000];
    static unsigned char dst[1100000];
    int fails = 0;
    long long t0, t1, acc;
    int rep;
    const int reps = 200;
    const size_t bytes = 1048576;
    size_t i;
    void *found;

    fails += check_copy(src, dst, 0);
    fails += check_copy(src, dst, 1);
    fails += check_copy(src, dst, 7);
    fails += check_copy(src, dst, 15);
    fails += check_copy(src, dst, 16);
    fails += check_copy(src, dst, 17);
    fails += check_copy(src, dst, 31);
    fails += check_copy(src, dst, 32);
    fails += check_copy(src, dst, 63);
    fails += check_copy(src, dst, 64);
    fails += check_copy(src, dst, 127);
    fails += check_copy(src, dst, 128);
    fails += check_copy(src, dst, 255);
    fails += check_copy(src, dst, 256);
    fails += check_copy(src, dst, 1000);
    fails += check_copy(src, dst, 4096);
    fails += check_copy(src, dst, 65536);
    fails += check_copy(src, dst, 1048576);
    fails += check_copy(src + 7, dst + 1, 100);
    fails += check_copy(src + 1, dst + 8, 4096);

    fails += check_set(dst, 0, 165);
    fails += check_set(dst, 1, 165);
    fails += check_set(dst, 17, 165);
    fails += check_set(dst, 64, 165);
    fails += check_set(dst, 1000, 90);

    for (i = 0; i < 1000; i++) src[i] = (unsigned char)(i & 255);
    memcpy(dst, src, 1000);
    if (memcmp(src, dst, 1000) != 0) fails++;
    if (memcmp(src, dst, 0) != 0) fails++;
    dst[999] = 1;
    if (memcmp(src, dst, 1000) == 0) fails++;
    dst[999] = src[999];
    dst[0] = 9;
    if (memcmp(src, dst, 1000) == 0) fails++;

    memset(src, 0, 200);
    src[0] = 90;
    src[15] = 90;
    src[16] = 90;
    src[100] = 90;
    found = memchr(src, 90, 200);
    if (found != src) fails++;
    found = memchr(src + 1, 90, 199);
    if (found != src + 15) fails++;
    found = memchr(src, 91, 200);
    if (found != NULL) fails++;

    printf("CHECK memcopy fails %d\n", fails);

    for (i = 0; i < bytes; i++) src[i] = (unsigned char)(i & 255);
    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        memcpy(dst, src, bytes);
        acc += (long long)bytes;
        barrier();
    }
    t1 = stamp();
    printf("TIME memcopy glibc_copy ns %lld acc %lld\n", t1 - t0, acc);

    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        sse2_copy(dst, src, bytes);
        acc += (long long)bytes;
        barrier();
    }
    t1 = stamp();
    printf("TIME memcopy sse2_copy ns %lld acc %lld\n", t1 - t0, acc);

    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        memset(dst, 165, bytes);
        acc += (long long)bytes;
        barrier();
    }
    t1 = stamp();
    printf("TIME memcopy glibc_set ns %lld acc %lld\n", t1 - t0, acc);

    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        sse2_set(dst, 165, bytes);
        acc += (long long)bytes;
        barrier();
    }
    t1 = stamp();
    printf("TIME memcopy sse2_set ns %lld acc %lld\n", t1 - t0, acc);

    memcpy(dst, src, bytes);
    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        acc += memcmp(src, dst, bytes) != 0;
        barrier();
    }
    t1 = stamp();
    printf("TIME memcopy glibc_cmp ns %lld acc %lld\n", t1 - t0, acc);

    src[1048575] = 90;
    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        found = memchr(src, 90, bytes);
        acc += (unsigned char *)found - src;
        barrier();
    }
    t1 = stamp();
    printf("TIME memcopy glibc_chr ns %lld acc %lld\n", t1 - t0, acc);

    return fails == 0 ? 0 : 1;
}
