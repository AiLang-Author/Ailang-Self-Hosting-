/* glibc strlen, strcmp, strchr. strstr is a separate row.
   AILANG StringIndexOf searches for the first byte of the needle. */
#include <stdio.h>
#include <string.h>
#include <time.h>

static void barrier(void) {
    asm volatile("" ::: "memory");
}

static long long stamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static long long to_int(const char *s) {
    long long result = 0;
    int i = 0;
    while (s[i] >= '0' && s[i] <= '9') {
        result = result * 10 + (s[i] - '0');
        i++;
    }
    return result;
}

int main(void) {
    enum { N = 262144, POS = 262139 };
    static char h[N + 1];
    static char other[N + 1];
    int fails = 0;
    int i;
    char *found;
    long long t0, t1, acc, hit;
    int rep;
    const int reps = 40;

    if (strlen("foobar") != 6) fails++;
    if (strcmp("abc", "abc") != 0) fails++;
    if (strcmp("abc", "abd") == 0) fails++;
    if (strncmp("foobar", "foo", 3) != 0) fails++;
    if (strncmp("foobar", "bar", 3) == 0) fails++;
    if (strcmp("foobar" + 3, "bar") != 0) fails++;
    if (strcmp("foobar", "foo") == 0) fails++;
    {
        const char *abra = "abracadabra";
        const char *mid = "abXabc";
        found = strchr(abra, 'c');
        if (found == NULL || found - abra != 4) fails++;
        found = strchr(abra, '\0');
        if (found == NULL || found - abra != 11) fails++;
        found = strchr(mid, 'a');
        if (found == NULL || found - mid != 0) fails++;
        if (strchr(abra, 'z') != NULL) fails++;
        found = strstr(abra, "cad");
        if (found == NULL || found - abra != 4) fails++;
        found = strstr(mid, "abc");
        if (found == NULL || found - mid != 3) fails++;
    }
    if (to_int("2048x") != 2048) fails++;

    for (i = 0; i < N; i++) {
        h[i] = 'a';
        other[i] = 'a';
    }
    h[N] = 0;
    other[N] = 0;
    memcpy(h + POS, "xyzzy", 5);

    if (strlen(h) != N) fails++;
    found = strchr(h, 'x');
    if (found == NULL || found - h != POS) fails++;
    if (strchr(h, 'q') != NULL) fails++;
    found = strstr(h, "xyzzy");
    if (found == NULL || found - h != POS) fails++;
    if (strncmp(h, "aaa", 3) != 0) fails++;
    if (strcmp(h + N - 5, "xyzzy") != 0) fails++;
    if (strcmp(other, other) != 0) fails++;
    other[N - 1] = 'b';
    if (strcmp(h, other) == 0) fails++;

    printf("CHECK strings fails %d at %d\n", fails, POS);

    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        found = strchr(h, 'x');
        hit = found - h;
        acc += hit;
        barrier();
    }
    t1 = stamp();
    printf("TIME strings glibc_chr ns %lld acc %lld\n", t1 - t0, acc);

    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        found = strstr(h, "xyzzy");
        hit = found - h;
        acc += hit;
        barrier();
    }
    t1 = stamp();
    printf("TIME strings glibc_strstr ns %lld acc %lld\n", t1 - t0, acc);

    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        acc += (long long)strlen(h);
        barrier();
    }
    t1 = stamp();
    printf("TIME strings glibc_length ns %lld acc %lld\n", t1 - t0, acc);

    other[N - 1] = 'a';
    acc = 0;
    t0 = stamp();
    for (rep = 0; rep < reps; rep++) {
        acc += strcmp(h, other);
        barrier();
    }
    t1 = stamp();
    printf("TIME strings glibc_compare ns %lld acc %lld\n", t1 - t0, acc);

    return fails == 0 ? 0 : 1;
}
