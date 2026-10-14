/* In-memory reverse complement.
 * Pair table and two-pointer swap are Mr Ledrug's Benchmarks Game
 * gcc #2. FASTA headers, the 60-column rewrap, threads, and stdin
 * are not part of this pin. The buffer is a deterministic IUPAC
 * sequence from the fasta LCG (IA 3877, IC 29573, IM 139968, seed 42).
 * An odd number of passes leaves the reverse complement.
 */
#include <stdio.h>
#include <stdint.h>

enum { LEN = 100000, PASSES = 21 };

static int to_upper(int c) {
    if (c >= 97 && c <= 122) {
        return c - 32;
    }
    return c;
}

static int to_lower(int c) {
    if (c >= 65 && c <= 90) {
        return c + 32;
    }
    return c;
}

int main(void) {
    const char *pairs = "ATCGGCTAUAMKRYWWSSYRKMVBHDDHBVNN\n\n";
    const char *alpha = "ATCGUMRWSYKVHDBN";
    unsigned char tbl[128];
    unsigned char buf[LEN];
    int i;
    const char *s;

    for (i = 0; i < 128; i++) {
        tbl[i] = 0;
    }
    for (s = pairs; *s; s += 2) {
        tbl[to_upper((unsigned char)s[0])] = (unsigned char)s[1];
        tbl[to_lower((unsigned char)s[0])] = (unsigned char)s[1];
    }

    uint32_t seed = 42;
    for (i = 0; i < LEN; i++) {
        seed = (seed * 3877u + 29573u) % 139968u;
        buf[i] = (unsigned char)alpha[seed % 16u];
    }

    int p;
    for (p = 0; p < PASSES; p++) {
        int left = 0;
        int right = LEN - 1;
        while (left <= right) {
            unsigned char c = tbl[buf[left]];
            buf[left] = tbl[buf[right]];
            buf[right] = c;
            left++;
            right--;
        }
    }

    unsigned long long sum = 0;
    unsigned long long mix = 0;
    for (i = 0; i < LEN; i++) {
        sum += buf[i];
        mix ^= buf[i];
    }
    printf("SUM %llu\n", sum);
    printf("XOR %llu\n", mix);
    return 0;
}
