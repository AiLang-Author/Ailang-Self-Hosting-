/* FASTA-style ALU repeat + LCG random IUB. Same as fasta.ailang. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static const char *ALU =
    "GGCCGGGCGCGGTGGCTCACGCCTGTAATCCCAGCACTTTGGGAGGCCGAGGCGGGCGGATCACCTGAGGTCAGGAGTTCGAGACCAGCCTGGCCAACATGGTGAAACCCCGTCTCTACTAAAAATACAAAAATTAGCCGGGCGTGGTGGCGCGCGCCTGTAATCCCAGCTACTCGGGAGGCTGAGGCAGGAGAATCGCTTGAACCCGGGAGGCGGAGGTTGCAGTGAGCCGAGATCGCGCCACTGCACTCCAGCCTGGGCGACAGAGCGAGACTCCGTCTCAAAAA";

static int repeat_alu(unsigned char *dst, int n) {
    int alun = (int)strlen(ALU);
    int pos = 0, col = 0, i = 0, k = 0;
    for (i = 0; i < n; i++) {
        dst[pos++] = (unsigned char)ALU[k];
        if (++col == 60) { dst[pos++] = 10; col = 0; }
        if (++k == alun) k = 0;
    }
    if (col) dst[pos++] = 10;
    return pos;
}

static int random_iub(unsigned char *dst, int n, int seed0, int *seed_out) {
    int pos = 0, col = 0, i;
    int seed = seed0;
    for (i = 0; i < n; i++) {
        int ch;
        seed = (seed * 3877 + 29573) % 139968;
        ch = 66;
        if (seed < 37672) ch = 97;
        else if (seed < 54375) ch = 99;
        else if (seed < 71078) ch = 103;
        else if (seed < 108750) ch = 116;
        dst[pos++] = (unsigned char)ch;
        if (++col == 60) { dst[pos++] = 10; col = 0; }
    }
    if (col) dst[pos++] = 10;
    *seed_out = seed;
    return pos;
}

int main(void) {
    int n = 250000;
    unsigned char *dst = (unsigned char *)malloc(1200000);
    int p1, p2, seed, i;
    long long t0, t1, sm = 0;
    int total;
    t0 = nsec_now();
    p1 = repeat_alu(dst, n * 2);
    p2 = random_iub(dst + p1, n, 42, &seed);
    t1 = nsec_now();
    total = p1 + p2;
    for (i = 0; i < total; i++) sm += dst[i];
    printf("FASTA n %d len %d sum %lld ns %lld\n", n, total, sm, t1 - t0);
    free(dst);
    return 0;
}
