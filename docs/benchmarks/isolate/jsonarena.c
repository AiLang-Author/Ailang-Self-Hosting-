/* Arena JSON array-of-objects parse. Same shape as jsonarena.ailang. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

static long long nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

typedef struct Node {
    long long kind;
    long long ival;
    struct Node *next;
    struct Node *child;
} Node;

static int put_int(unsigned char *dst, int pos, int n) {
    char tmp[16];
    int d = 0, i;
    if (n == 0) { dst[pos++] = '0'; return pos; }
    while (n > 0) { tmp[d++] = (char)('0' + (n % 10)); n /= 10; }
    for (i = d - 1; i >= 0; i--) dst[pos++] = (unsigned char)tmp[i];
    return pos;
}

static int generate(unsigned char *dst, int nobj) {
    int pos = 0, i;
    dst[pos++] = '[';
    for (i = 0; i < nobj; i++) {
        if (i) dst[pos++] = ',';
        dst[pos++] = '{';
        dst[pos++] = '"'; dst[pos++] = 'x'; dst[pos++] = '"'; dst[pos++] = ':';
        pos = put_int(dst, pos, i);
        dst[pos++] = ',';
        dst[pos++] = '"'; dst[pos++] = 'y'; dst[pos++] = '"'; dst[pos++] = ':';
        pos = put_int(dst, pos, i * 3);
        dst[pos++] = '}';
    }
    dst[pos++] = ']';
    return pos;
}

static int skip(const unsigned char *src, int i, int n) {
    while (i < n) {
        unsigned char ch = src[i];
        if (ch != 32 && ch != 10 && ch != 9) return i;
        i++;
    }
    return i;
}

static int parse_num(const unsigned char *src, int i, int n, Node *node) {
    long long v = 0;
    while (i < n) {
        unsigned char ch = src[i];
        if (ch < '0' || ch > '9') break;
        v = v * 10 + (ch - '0');
        i++;
    }
    node->kind = 2;
    node->ival = v;
    node->next = 0;
    node->child = 0;
    return i;
}

static int parse_obj(const unsigned char *src, int i, int n, Node **used, Node *obj);

static int parse_arr(const unsigned char *src, int i, int n, Node **used) {
    Node *arr = *used;
    Node *head = 0, *tail = 0;
    int count = 0;
    *used = arr + 1;
    arr->kind = 4;
    arr->ival = 0;
    arr->next = 0;
    arr->child = 0;
    i++;
    while (i < n) {
        unsigned char ch;
        Node *nd;
        i = skip(src, i, n);
        ch = src[i];
        if (ch == ']') { i++; break; }
        if (ch == ',') { i++; continue; }
        nd = *used;
        *used = nd + 1;
        if (ch == '{') i = parse_obj(src, i, n, used, nd);
        else i = parse_num(src, i, n, nd);
        if (!head) { head = nd; arr->child = nd; }
        else tail->next = nd;
        tail = nd;
        count++;
    }
    arr->ival = count;
    return i;
}

static int parse_obj(const unsigned char *src, int i, int n, Node **used, Node *obj) {
    Node *last = 0;
    int fields = 0;
    obj->kind = 5;
    obj->ival = 0;
    obj->next = 0;
    obj->child = 0;
    i++;
    while (i < n) {
        unsigned char ch;
        i = skip(src, i, n);
        ch = src[i];
        if (ch == '}') { i++; break; }
        if (ch == ',') { i++; continue; }
        if (ch == '"') {
            Node *val;
            i++;
            while (i < n && src[i] != '"') i++;
            i++;
            i = skip(src, i, n);
            if (src[i] == ':') i++;
            i = skip(src, i, n);
            val = *used;
            *used = val + 1;
            i = parse_num(src, i, n, val);
            if (!last) obj->child = val;
            else last->next = val;
            last = val;
            fields++;
        } else i++;
    }
    obj->ival = fields;
    return i;
}

static long long walk_sum(Node *node) {
    long long s = 0;
    Node *obj;
    if (!node) return 0;
    for (obj = node->child; obj; obj = obj->next) {
        Node *field;
        for (field = obj->child; field; field = field->next) {
            if (field->kind == 2) s += field->ival;
        }
    }
    return s;
}

int main(void) {
    int nobj = 200000;
    unsigned char *text = (unsigned char *)malloc(8000000);
    Node *arena = (Node *)malloc(32000000);
    Node *used;
    int tlen;
    long long t0, t1, sm;
    tlen = generate(text, nobj);
    used = arena;
    t0 = nsec_now();
    parse_arr(text, 0, tlen, &used);
    t1 = nsec_now();
    sm = walk_sum(arena);
    printf("JSONARENA bytes %d nodesb %lld sum %lld ns %lld\n",
           tlen, (long long)((char *)used - (char *)arena), sm, t1 - t0);
    free(text);
    free(arena);
    return 0;
}
