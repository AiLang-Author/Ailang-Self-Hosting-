/* Count primes below 1000000. Same byte sieve as sieve.ailang. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long long stamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static int count_primes(int n) {
    unsigned char *mark = (unsigned char *)malloc((size_t)n);
    int i, j, count;
    memset(mark, 1, (size_t)n);
    if (n > 0) mark[0] = 0;
    if (n > 1) mark[1] = 0;
    for (i = 2; i < n; i++) {
        if (mark[i]) {
            for (j = i + i; j < n; j += i) mark[j] = 0;
        }
    }
    count = 0;
    for (i = 0; i < n; i++) count += mark[i];
    free(mark);
    return count;
}

int main(void) {
    long long t0 = stamp();
    int primes = count_primes(1000000);
    long long t1 = stamp();
    printf("SIEVE primes %d ns %lld\n", primes, t1 - t0);
    return primes == 78498 ? 0 : 1;
}
