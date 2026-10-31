/* sum += a[i], 20000 passes of 1024. Same total as idxsum.ailang. */
#include <stdint.h>
#include <stdio.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

int main(void) {
    long long arr[1024];
    long long sum = 0;
    long long t0, t1;
    int i, pass;
    for (i = 0; i < 1024; i++) arr[i] = i;
    t0 = nsec_now();
    for (pass = 0; pass < 20000; pass++) {
        for (i = 0; i < 1024; i++) sum += arr[i];
    }
    t1 = nsec_now();
    printf("IDXSUM %lld ns %lld\n", sum, t1 - t0);
    return 0;
}
