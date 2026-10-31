/* Six live integer accumulators. Same as liveint.ailang. */
#include <stdint.h>
#include <stdio.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

int main(void) {
    long long a = 0, b = 0, c = 0, d = 0, e = 0, f = 0;
    long long t0, t1;
    int n;
    t0 = nsec_now();
    for (n = 0; n < 8000000; n++) {
        a += 1;
        b += 2;
        c += 3;
        d += 4;
        e += 5;
        f += 6;
    }
    t1 = nsec_now();
    printf("LIVEINT %lld ns %lld\n", a + b + c + d + e + f, t1 - t0);
    return 0;
}
