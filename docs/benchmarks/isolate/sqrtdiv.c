/* n-body mag chain, no structs. Same arithmetic as sqrtdiv.ailang. */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

int main(void) {
    double dt = 1.0 / 100.0;
    double x = 1.0, y = 1.0, z = 1.0, acc = 0.0;
    long long t0, t1;
    int n;
    union { double d; long long b; } u;
    t0 = nsec_now();
    for (n = 0; n < 8000000; n++) {
        double x2 = x * x;
        double y2 = y * y;
        double z2 = z * z;
        double dist2 = x2 + y2 + z2;
        double dist = sqrt(dist2);
        double dist3 = dist2 * dist;
        double mag = dt / dist3;
        x = x + mag;
        acc = acc + mag;
    }
    t1 = nsec_now();
    u.d = acc;
    printf("SQRTDIV %lld ns %lld\n", u.b, t1 - t0);
    return 0;
}
