/* Single-thread fannkuch-redux. Permute 0..n-1, flip until the
 * first slot is 0, and alternate the flip counts into a checksum.
 * No SIMD intrinsics. The clock wraps only that search.
 */

#include <stdint.h>
#include <stdio.h>
#include <time.h>

static long long nsec_now(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static void fannkuch(int n, int64_t *checksum, int64_t *maxflips)
{
    int64_t perm[16];
    int64_t perm1[16];
    int64_t count[16];
    int64_t maxf = 0;
    int64_t sum = 0;
    int64_t perm_count = 0;
    int i;
    int r = n;
    for (i = 0; i < n; i++)
        perm1[i] = i;
    for (;;) {
        while (r != 1) {
            count[r - 1] = r;
            r--;
        }
        for (i = 0; i < n; i++)
            perm[i] = perm1[i];
        int64_t flips = 0;
        int64_t k = perm[0];
        while (k != 0) {
            int64_t k2 = (k + 1) >> 1;
            for (i = 0; i < k2; i++) {
                int64_t tmp = perm[i];
                perm[i] = perm[k - i];
                perm[k - i] = tmp;
            }
            flips++;
            k = perm[0];
        }
        if (flips > maxf)
            maxf = flips;
        if ((perm_count & 1) == 0)
            sum += flips;
        else
            sum -= flips;
        for (;;) {
            int64_t perm0;
            if (r == n) {
                *checksum = sum;
                *maxflips = maxf;
                return;
            }
            perm0 = perm1[0];
            i = 0;
            while (i < r) {
                int j = i + 1;
                perm1[i] = perm1[j];
                i = j;
            }
            perm1[r] = perm0;
            count[r] = count[r] - 1;
            if (count[r] > 0)
                break;
            r++;
        }
        perm_count++;
    }
}

static void run(int n)
{
    int64_t checksum = 0;
    int64_t maxflips = 0;
    long long t0, t1;
    t0 = nsec_now();
    fannkuch(n, &checksum, &maxflips);
    t1 = nsec_now();
    printf("FANNKUCH %d checksum %lld max %lld ns %lld\n", n,
           (long long)checksum, (long long)maxflips, (long long)(t1 - t0));
}

int main(void)
{
    run(7);
    run(10);
    run(12);
    return 0;
}
