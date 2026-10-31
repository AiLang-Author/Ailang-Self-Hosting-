/* Scalar float chain. Same squares and adds as regchain.ailang. */
#include <stdint.h>
#include <stdio.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

int main(void) {
    double cr = 1.0, ci = 1.0, two = 2.0, four = 4.0;
    double x = 0.0, y = 0.0;
    long long hits = 0;
    long long t0, t1;
    int n;
    t0 = nsec_now();
    for (n = 0; n < 8000000; n++) {
        double x2 = x * x;
        double y2 = y * y;
        double mag = x2 + y2;
        y = two * x * y + ci;
        x = x2 - y2 + cr;
        if (mag < four) hits++;
    }
    t1 = nsec_now();
    printf("REGCHAIN %lld ns %lld\n", hits, t1 - t0);
    return 0;
}
