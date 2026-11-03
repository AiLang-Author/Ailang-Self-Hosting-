/* Same independent range tests as classify.ailang. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

int main(void) {
    const char *text = "The quick brown fox jumps over the lazy dog. 12345\n";
    int tn = (int)strlen(text);
    int n = 2000000;
    int reps = 8;
    unsigned char *buf = (unsigned char *)malloc((size_t)n);
    long long ctrl = 0, digit = 0, upper = 0, lower = 0, other = 0, sum = 0;
    int i, rep;
    long long t0, t1;
    if (!buf) return 1;
    for (i = 0; i < n; i++) buf[i] = (unsigned char)text[i % tn];
    t0 = nsec_now();
    for (rep = 0; rep < reps; rep++) {
        for (i = 0; i < n; i++) {
            int c = buf[i];
            int kind = 5;
            if (c < 33) kind = 1;
            if (c >= 48 && c < 58) kind = 2;
            if (c >= 65 && c < 91) kind = 3;
            if (c >= 97 && c < 123) kind = 4;
            if (kind == 1) ctrl++;
            if (kind == 2) digit++;
            if (kind == 3) upper++;
            if (kind == 4) lower++;
            if (kind == 5) other++;
            sum += c;
        }
    }
    t1 = nsec_now();
    printf("CLASS ctrl %lld digit %lld upper %lld lower %lld other %lld sum %lld ns %lld\n",
           ctrl, digit, upper, lower, other, sum, t1 - t0);
    free(buf);
    return 0;
}
