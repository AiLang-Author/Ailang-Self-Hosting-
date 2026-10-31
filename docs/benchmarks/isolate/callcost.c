/* Same call split as callcost.ailang. noinline, no sibling-call. */
#include <stdio.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

__attribute__((noinline))
static long long leaf_add(long long a, long long b) {
    return a + b;
}

__attribute__((noinline))
static long long stub_add(long long a, long long b) {
    long long s = a + b;
    return s;
}

__attribute__((noinline))
static long long sink(long long x) {
    return x;
}

__attribute__((noinline))
static long long call_add(long long a, long long b) {
    long long s = a + b;
    return sink(s);
}

__attribute__((noinline))
static long long sum6(long long a, long long b, long long c,
                      long long d, long long e, long long f) {
    return a + b + c + d + e + f;
}

__attribute__((noinline))
static long long depth(long long n) {
    volatile long long here = n;
    if (n <= 0) return here;
    return here + depth(n - 1);
}

int main(void) {
    long long n = 20000000;
    long long s, i, k;
    long long leaf, stub, callv, six, deep;
    long long t0, t1, t2, t3, t4, t5, t6, t7, t8, t9;
    int fails = 0;

    t0 = nsec_now();
    s = 0;
    for (i = 0; i < n; i++) s += leaf_add(i, 1);
    t1 = nsec_now();
    leaf = s;
    if (s != 200000010000000LL) fails++;

    t2 = nsec_now();
    s = 0;
    for (i = 0; i < n; i++) s += stub_add(i, 1);
    t3 = nsec_now();
    stub = s;
    if (s != 200000010000000LL) fails++;

    t4 = nsec_now();
    s = 0;
    for (i = 0; i < n; i++) s += call_add(i, 1);
    t5 = nsec_now();
    callv = s;
    if (s != 200000010000000LL) fails++;

    t6 = nsec_now();
    s = 0;
    for (i = 0; i < 10000000LL; i++) s += sum6(i, 1, 2, 3, 4, 5);
    t7 = nsec_now();
    six = s;
    if (s != 50000145000000LL) fails++;

    t8 = nsec_now();
    s = 0;
    for (k = 0; k < 2000; k++) s += depth(512);
    t9 = nsec_now();
    deep = s;
    if (s != 262656000LL) fails++;

    printf("CHECK callcost fails %d leaf %lld stub %lld call %lld six %lld deep %lld\n",
           fails, leaf, stub, callv, six, deep);
    printf("TIME LEAFADD ns %lld\n", t1 - t0);
    printf("TIME STUBADD ns %lld\n", t3 - t2);
    printf("TIME CALLADD ns %lld\n", t5 - t4);
    printf("TIME SIXARG ns %lld\n", t7 - t6);
    printf("TIME DEEPWALK ns %lld\n", t9 - t8);
    return fails == 0 ? 0 : 1;
}
