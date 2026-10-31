/* Stream triad. a[i] = b[i] + c[i]*d[i]. Same layout as triad.ailang. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static double run(double *a, double *b, double *c, double *d, int n) {
    double s = 0.0;
    int i;
    for (i = 0; i < n; i++) {
        double t = b[i] + c[i] * d[i];
        a[i] = t;
        s += t;
    }
    return s;
}

int main(void) {
    int n = 2000000;
    int i;
    double *a = (double *)malloc((size_t)n * 8);
    double *b = (double *)malloc((size_t)n * 8);
    double *c = (double *)malloc((size_t)n * 8);
    double *d = (double *)malloc((size_t)n * 8);
    long long t0, t1;
    union { double d; long long b; } u;
    for (i = 0; i < n; i++) {
        b[i] = (double)i;
        c[i] = 1.0;
        d[i] = 2.0;
    }
    t0 = nsec_now();
    u.d = run(a, b, c, d, n);
    t1 = nsec_now();
    printf("TRIAD %lld ns %lld\n", u.b, t1 - t0);
    free(a);
    free(b);
    free(c);
    free(d);
    return 0;
}
