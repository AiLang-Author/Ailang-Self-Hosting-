/* 256-byte bytecode, 100 million fetches, switch dispatch. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static long long run(const unsigned char *code, long long n) {
    long long a = 1, b = 1, c = 0;
    long long pc = 0, i;
    for (i = 0; i < n; i++) {
        int op = code[pc & 255];
        switch (op) {
        case 0: a = a + 1; break;
        case 1: a = a + b; break;
        case 2: b = b + 1; break;
        case 3: c = c + a; break;
        case 4: a = a ^ b; break;
        case 5: b = b & 65535; break;
        case 6: a = a * 1664525 + 1013904223; break;
        case 7: c = c ^ pc; break;
        case 8: a = a - b; break;
        case 9: b = b + c; break;
        case 10: c = c + 1; break;
        case 11: a = a | 1; break;
        case 12: b = b ^ a; break;
        case 13: a = a + pc; break;
        case 14: c = c - 1; break;
        case 15: b = b + 3; break;
        default: a = a + 1; break;
        }
        pc = pc + 1;
    }
    return a ^ b ^ c;
}

int main(void) {
    unsigned char *code = (unsigned char *)malloc(256);
    int i;
    long long t0, t1, h;
    for (i = 0; i < 256; i++) code[i] = (unsigned char)(i & 15);
    t0 = nsec_now();
    h = run(code, 100000000LL);
    t1 = nsec_now();
    printf("VMDISPATCH %lld ns %lld\n", h, t1 - t0);
    free(code);
    return 0;
}
