/* Same fib and the same non-tail depth chain. Build with
   -fno-optimize-sibling-calls so the depth chain stays on the stack. */
#include <stdio.h>
#include <time.h>

static long long stamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

__attribute__((noinline))
static long long fib(long long n) {
    long long a, b;
    if (n < 2) return n;
    a = fib(n - 1);
    b = fib(n - 2);
    return a + b;
}

__attribute__((noinline))
static long long depth(long long n) {
    volatile long long here = n;
    long long below;
    if (n <= 0) return here;
    below = depth(n - 1);
    return here + below;
}

int main(void) {
    int fails = 0;
    long long f, d, deep, fib35;
    long long t0, t1, t2, t3;

    if (fib(0) != 0) fails++;
    if (fib(1) != 1) fails++;
    if (fib(10) != 55) fails++;
    if (fib(20) != 6765) fails++;
    if (depth(1) != 1) fails++;
    if (depth(100) != 5050) fails++;

    t0 = stamp();
    deep = depth(8192);
    t1 = stamp();
    if (deep != 33558528LL) fails++;

    t2 = stamp();
    fib35 = fib(35);
    t3 = stamp();
    if (fib35 != 9227465LL) fails++;

    printf("CHECK recursion fails %d fib35 %lld depth %lld\n", fails, fib35, deep);
    printf("TIME recursion depth ns %lld\n", t1 - t0);
    printf("TIME recursion fib35 ns %lld\n", t3 - t2);
    (void)f;
    (void)d;
    return fails == 0 ? 0 : 1;
}
