/* Same word-count state machine as wc.ailang. */
#include <stdio.h>
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
    long long lines = 0, words = 0, bytes = 0;
    int rep, i;
    long long t0, t1;
    if (!buf) return 1;
    for (i = 0; i < n; i++) buf[i] = (unsigned char)text[i % tn];
    t0 = nsec_now();
    for (rep = 0; rep < reps; rep++) {
        int inw = 0;
        for (i = 0; i < n; i++) {
            int c = buf[i];
            int sp = 0;
            bytes++;
            if (c == 10) lines++;
            if (c == 32) sp = 1;
            if (c == 10) sp = 1;
            if (c == 9) sp = 1;
            if (c == 13) sp = 1;
            if (sp == 1) {
                inw = 0;
            } else if (inw == 0) {
                words++;
                inw = 1;
            }
        }
    }
    t1 = nsec_now();
    printf("WC lines %lld words %lld bytes %lld ns %lld\n", lines, words, bytes, t1 - t0);
    free(buf);
    return 0;
}
