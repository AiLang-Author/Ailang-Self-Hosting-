/* Same growth as Array.Push: start at 16, double, memcpy the old block. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long long stamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

typedef struct Vec {
    long long *data;
    long long size;
    long long cap;
} Vec;

static void vec_push(Vec *v, long long value) {
    if (v->size >= v->cap) {
        long long ncap = v->cap * 2;
        long long *nd = (long long *)malloc((size_t)ncap * sizeof(long long));
        memcpy(nd, v->data, (size_t)v->size * sizeof(long long));
        free(v->data);
        v->data = nd;
        v->cap = ncap;
    }
    v->data[v->size] = value;
    v->size++;
}

static long long vec_index(Vec *v, long long value) {
    long long i;
    for (i = 0; i < v->size; i++) {
        if (v->data[i] == value) return i;
    }
    return -1;
}

int main(void) {
    const long long n = 100000;
    Vec v;
    long long i, sum, expect, at;
    long long t0, t1, acc;
    int rep, fails = 0;

    v.cap = 16;
    v.size = 0;
    v.data = (long long *)calloc(16, sizeof(long long));

    t0 = stamp();
    for (i = 0; i < n; i++) vec_push(&v, i + 1);
    sum = 0;
    for (i = 0; i < n; i++) sum += v.data[i];
    t1 = stamp();

    if (v.size != n) fails++;
    expect = n * (n + 1) / 2;
    if (sum != expect) fails++;
    if (vec_index(&v, 1) != 0) fails++;
    if (vec_index(&v, n) != n - 1) fails++;
    if (vec_index(&v, -1) != -1) fails++;

    printf("CHECK array fails %d sum %lld\n", fails, sum);
    printf("TIME array glibc_build ns %lld\n", t1 - t0);

    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < 8; rep++) acc += vec_index(&v, n);
    t1 = stamp();
    printf("TIME array glibc_find ns %lld acc %lld\n", t1 - t0, acc);

    free(v.data);
    return fails == 0 ? 0 : 1;
}
