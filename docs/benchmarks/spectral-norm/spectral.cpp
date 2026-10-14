/* The Computer Language Benchmarks Game
 * https://salsa.debian.org/benchmarksgame-team/benchmarksgame/
 *
 * Contributed by Sebastien Loisel
 *
 * Kernel text is the gcc #8 entry. The driver only adds a monotonic
 * clock around the ten iterations and prints the f64 bits.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

double eval_A(int i, int j) { return 1.0 / ((i + j) * (i + j + 1) / 2 + i + 1); }

void eval_A_times_u(int N, const double u[], double Au[])
{
    int i, j;
    for (i = 0; i < N; i++) {
        Au[i] = 0;
        for (j = 0; j < N; j++)
            Au[i] += eval_A(i, j) * u[j];
    }
}

void eval_At_times_u(int N, const double u[], double Au[])
{
    int i, j;
    for (i = 0; i < N; i++) {
        Au[i] = 0;
        for (j = 0; j < N; j++)
            Au[i] += eval_A(j, i) * u[j];
    }
}

void eval_AtA_times_u(int N, const double u[], double AtAu[])
{
    double v[N];
    eval_A_times_u(N, u, v);
    eval_At_times_u(N, v, AtAu);
}

static long long nsec_now(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static void run_n(int N)
{
    double *u = (double *)malloc((size_t)N * sizeof(double));
    double *v = (double *)malloc((size_t)N * sizeof(double));
    int i;
    for (i = 0; i < N; i++)
        u[i] = 1;
    long long t0 = nsec_now();
    for (i = 0; i < 10; i++) {
        eval_AtA_times_u(N, u, v);
        eval_AtA_times_u(N, v, u);
    }
    double vBv = 0;
    double vv = 0;
    for (i = 0; i < N; i++) {
        vBv += u[i] * v[i];
        vv += v[i] * v[i];
    }
    double result = sqrt(vBv / vv);
    long long t1 = nsec_now();
    uint64_t bits = 0;
    memcpy(&bits, &result, sizeof(bits));
    printf("ROW %d bits %llu ns %lld\n", N,
           (unsigned long long)bits, (long long)(t1 - t0));
    printf("%0.9f\n", result);
    free(u);
    free(v);
}

int main(void)
{
    run_n(100);
    run_n(5500);
    return 0;
}
