/* 64x64 f64 matmul, 2x2 register tile, row-major.
 * C[i][j] += A[i][k] * B[k][j], two rows by two columns per inner trip.
 * Entries are small integers, so a contracted fma and a separate mul/add
 * produce the same f64 bits. No SIMD intrinsics.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

enum { N = 64, REPS = 2000 };

static long long nsec_now(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static void fill(double *A, double *B)
{
    int i, j;
    for (i = 0; i < N; i++) {
        for (j = 0; j < N; j++) {
            A[i * N + j] = (double)(i + j + 1);
            B[i * N + j] = (double)(i * 3 - j + N);
        }
    }
}

static void tile_mul(const double *A, const double *B, double *C)
{
    int i, j, k;
    for (i = 0; i < N; i += 2) {
        for (j = 0; j < N; j += 2) {
            double s00 = 0;
            double s01 = 0;
            double s10 = 0;
            double s11 = 0;
            for (k = 0; k < N; k++) {
                double a0 = A[i * N + k];
                double a1 = A[(i + 1) * N + k];
                double b0 = B[k * N + j];
                double b1 = B[k * N + j + 1];
                s00 += a0 * b0;
                s01 += a0 * b1;
                s10 += a1 * b0;
                s11 += a1 * b1;
            }
            C[i * N + j] = s00;
            C[i * N + j + 1] = s01;
            C[(i + 1) * N + j] = s10;
            C[(i + 1) * N + j + 1] = s11;
        }
    }
}

static void digest(const double *C, uint64_t *sum_bits, uint64_t *mix_bits)
{
    double sum = 0;
    uint64_t mix = 0;
    int i;
    for (i = 0; i < N * N; i++) {
        uint64_t bits = 0;
        sum += C[i];
        memcpy(&bits, &C[i], sizeof(bits));
        mix ^= bits;
    }
    memcpy(sum_bits, &sum, sizeof(*sum_bits));
    *mix_bits = mix;
}

int main(void)
{
    double *A = (double *)malloc((size_t)N * N * sizeof(double));
    double *B = (double *)malloc((size_t)N * N * sizeof(double));
    double *C = (double *)malloc((size_t)N * N * sizeof(double));
    int rep;
    uint64_t sum_bits = 0;
    uint64_t mix_bits = 0;
    long long t0, t1;
    fill(A, B);
    t0 = nsec_now();
    for (rep = 0; rep < REPS; rep++)
        tile_mul(A, B, C);
    t1 = nsec_now();
    digest(C, &sum_bits, &mix_bits);
    printf("ROW %d bits %llu mix %llu ns %lld\n", N,
           (unsigned long long)sum_bits, (unsigned long long)mix_bits,
           (long long)(t1 - t0));
    free(A);
    free(B);
    free(C);
    return 0;
}
