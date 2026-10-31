/* Sliding-window 4-byte hash compressor. Same as lz4win.ailang. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static uint32_t load32(const unsigned char *p, int i) {
    return (uint32_t)p[i] | ((uint32_t)p[i + 1] << 8) |
           ((uint32_t)p[i + 2] << 16) | ((uint32_t)p[i + 3] << 24);
}

static unsigned long long compress(const unsigned char *src, int n, long long *tab) {
    int i, out = 0;
    unsigned int mix = 0;
    int lim = n - 4;
    for (i = 0; i < 4096; i++) tab[i] = 0;
    i = 0;
    while (i < lim) {
        uint32_t v = load32(src, i);
        unsigned int h = (unsigned int)((v * 2654435761u) >> 20) & 4095u;
        long long prev = tab[h];
        int hit = 0;
        tab[h] = i;
        if (prev > 0) {
            int dist = i - (int)prev;
            if (dist < 65536 && load32(src, (int)prev) == v) hit = 1;
        }
        if (hit) {
            int ml = 4;
            int pv = (int)prev;
            while (i + ml < n && src[i + ml] == src[pv + ml]) ml++;
            out += 3;
            mix ^= (unsigned int)( (i - pv) + ml * 65537 );
            i += ml;
        } else {
            out += 1;
            mix += src[i];
            i += 1;
        }
    }
    out += n - i;
    return ((unsigned long long)(mix & 0xffffffffu) << 32) | (unsigned int)out;
}

int main(void) {
    int n = 1048576;
    unsigned char *src = (unsigned char *)malloc((size_t)n);
    long long *tab = (long long *)malloc(4096 * sizeof(long long));
    unsigned int seed = 1;
    int i;
    long long t0, t1;
    unsigned long long packed;
    for (i = 0; i < n; i++) {
        seed = seed * 1664525u + 1013904223u;
        src[i] = (unsigned char)(seed >> 24);
        if ((i & 63) == 0) src[i] = src[i & 255];
    }
    t0 = nsec_now();
    packed = compress(src, n, tab);
    t1 = nsec_now();
    printf("LZ4WIN out %u mix %u ns %lld\n",
           (unsigned)(packed & 0xffffffffu),
           (unsigned)(packed >> 32),
           t1 - t0);
    free(src);
    free(tab);
    return 0;
}
