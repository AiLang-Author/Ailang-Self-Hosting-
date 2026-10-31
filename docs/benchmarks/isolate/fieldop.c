/* Two pairs of doubles in memory. Same update as fieldop.ailang. */
#include <stdint.h>
#include <stdio.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

int main(void) {
    double p[2], q[2];
    double half = 1.0;
    long long hits = 0;
    long long t0, t1;
    int n;
    p[0] = 1.0;
    p[1] = 2.0;
    q[0] = 0.5;
    q[1] = 3.0;
    t0 = nsec_now();
    for (n = 0; n < 8000000; n++) {
        double ix = p[0], iy = p[1], jx = q[0], jy = q[1];
        double dx = ix - jx;
        double dy = iy - jy;
        double s = dx * dx + dy * dy;
        ix = ix + dx * half;
        iy = iy + dy * half;
        p[0] = ix;
        p[1] = iy;
        if (s < ix) hits++;
    }
    t1 = nsec_now();
    printf("FIELDOP %lld ns %lld\n", hits, t1 - t0);
    return 0;
}
