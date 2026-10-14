/* FNV-1a 64, RFC 9923.
 * offset basis 0xCBF29CE484222325, prime 0x100000001B3.
 * hash = (hash xor byte) * prime, wrapping mod 2^64.
 * FOOBAR is the published "foobar" vector.
 * HASH is one running hash of the buffer repeated PASSES times,
 * so each pass depends on the previous hash.
 */
#include <stdio.h>
#include <stdint.h>

enum { N = 65536, PASSES = 80 };

int main(void) {
    unsigned char buf[N];
    unsigned char foo[6];
    int i;
    int p;
    const uint64_t basis = 0xCBF29CE484222325ULL;
    const uint64_t prime = 0x100000001B3ULL;
    uint64_t h;
    uint64_t fooh;

    foo[0] = 102;
    foo[1] = 111;
    foo[2] = 111;
    foo[3] = 98;
    foo[4] = 97;
    foo[5] = 114;

    fooh = basis;
    for (i = 0; i < 6; i++) {
        fooh ^= foo[i];
        fooh *= prime;
    }

    for (i = 0; i < N; i++) {
        buf[i] = (unsigned char)(i * 131 + 17);
    }

    h = basis;
    for (p = 0; p < PASSES; p++) {
        for (i = 0; i < N; i++) {
            h ^= buf[i];
            h *= prime;
        }
    }

    printf("FOOBAR %ld\n", (long)fooh);
    printf("HASH %ld\n", (long)h);
    return 0;
}
