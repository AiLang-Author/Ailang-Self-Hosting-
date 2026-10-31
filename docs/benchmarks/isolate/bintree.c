/* Bottom-up binary trees. Same layout as bintree.ailang: left, right, item. */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

typedef struct Node {
    struct Node *left;
    struct Node *right;
    long long item;
} Node;

__attribute__((noinline))
static Node *build(long long d, long long item) {
    Node *p = (Node *)malloc(sizeof(Node));
    p->item = item;
    if (d <= 0) {
        p->left = 0;
        p->right = 0;
        return p;
    }
    p->left = build(d - 1, 2 * item - 1);
    p->right = build(d - 1, 2 * item);
    return p;
}

__attribute__((noinline))
static long long check(Node *p) {
    if (p == 0) return 0;
    if (p->left == 0) return p->item;
    return p->item + check(p->left) - check(p->right);
}

int main(void) {
    long long s = 0;
    long long i;
    long long t0, t1;
    t0 = nsec_now();
    for (i = 0; i < 80; i++) {
        Node *t = build(12, 1);
        s += check(t);
    }
    t1 = nsec_now();
    printf("BINTREE %lld ns %lld\n", s, t1 - t0);
    return s == 0 ? 0 : 1;
}
