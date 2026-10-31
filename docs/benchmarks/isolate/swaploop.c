/* Reverse perm[0..15] four million times. Even count restores 0..15. */
#include <stdint.h>
#include <stdio.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

int main(void) {
    long long perm[16];
    long long sum = 0;
    long long t0, t1;
    int i, rep;
    for (i = 0; i < 16; i++) perm[i] = i;
    t0 = nsec_now();
    for (rep = 0; rep < 4000000; rep++) {
        for (i = 0; i < 8; i++) {
            long long a = perm[i];
            int idx = 15 - i;
            long long b = perm[idx];
            perm[i] = b;
            perm[idx] = a;
        }
    }
    t1 = nsec_now();
    for (i = 0; i < 16; i++) sum += perm[i];
    printf("SWAPLOOP %lld ns %lld\n", sum, t1 - t0);
    return 0;
}
