/* Phase timer matching hash-phases.ailang. Not the official bench.
   The table is the inline-key C map from hash.c. n = 20000. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <nmmintrin.h>

static long long stamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static void write_key(char *buf, int i) {
    int p;
    buf[0] = 'k';
    for (p = 7; p > 0; p--) {
        buf[p] = (char)('0' + (i % 10));
        i /= 10;
    }
    buf[8] = 0;
}

static uint32_t hash_key(const char *s) {
    uint32_t crc = 0;
    int i;
    for (i = 0; s[i]; i++) crc = _mm_crc32_u8(crc, (unsigned char)s[i]);
    if (crc == 0) crc = 1;
    return crc;
}

typedef struct Slot {
    uint32_t hash;
    int value;
    char key[12];
} Slot;

typedef struct Table {
    Slot *slots;
    int cap;
    int size;
} Table;

static void table_init(Table *t, int cap) {
    t->cap = cap;
    t->size = 0;
    t->slots = (Slot *)calloc((size_t)cap, sizeof(Slot));
}

static void table_free(Table *t) { free(t->slots); }

static int find_slot(Table *t, uint32_t h, const char *key) {
    int mask = t->cap - 1;
    int slot = (int)(h & (uint32_t)mask);
    int i;
    for (i = 0; i < t->cap; i++) {
        uint32_t sh = t->slots[slot].hash;
        if (sh == 0) return -1;
        if (sh != 0xffffffffu && sh == h && strcmp(t->slots[slot].key, key) == 0) return slot;
        slot = (slot + 1) & mask;
    }
    return -1;
}

static void rehash(Table *t) {
    int old_cap = t->cap;
    Slot *old = t->slots;
    int i;
    t->cap = old_cap * 2;
    t->slots = (Slot *)calloc((size_t)t->cap, sizeof(Slot));
    t->size = 0;
    for (i = 0; i < old_cap; i++) {
        if (old[i].hash != 0 && old[i].hash != 0xffffffffu) {
            int mask = t->cap - 1;
            int slot = (int)(old[i].hash & (uint32_t)mask);
            while (t->slots[slot].hash != 0) slot = (slot + 1) & mask;
            t->slots[slot] = old[i];
            t->size++;
        }
    }
    free(old);
}

static int table_set(Table *t, const char *key, int value) {
    uint32_t h;
    int mask, slot, tomb, i;
    if (t->size > (t->cap * 7) / 10) rehash(t);
    h = hash_key(key);
    mask = t->cap - 1;
    slot = (int)(h & (uint32_t)mask);
    tomb = -1;
    for (i = 0; i < t->cap; i++) {
        uint32_t sh = t->slots[slot].hash;
        if (sh == 0) {
            int ins = tomb >= 0 ? tomb : slot;
            t->slots[ins].hash = h;
            t->slots[ins].value = value;
            memcpy(t->slots[ins].key, key, 9);
            t->size++;
            return 1;
        }
        if (sh == 0xffffffffu && tomb < 0) tomb = slot;
        if (sh == h && strcmp(t->slots[slot].key, key) == 0) {
            t->slots[slot].value = value;
            return 0;
        }
        slot = (slot + 1) & mask;
    }
    return 0;
}

static int table_get(Table *t, const char *key) {
    uint32_t h = hash_key(key);
    int slot = find_slot(t, h, key);
    if (slot < 0) return 0;
    return t->slots[slot].value;
}

int main(void) {
    const int n = 20000;
    char *keys = (char *)calloc((size_t)n, 16);
    char *keys2 = (char *)calloc((size_t)n, 16);
    char one[16];
    Table table, table2;
    int i, fails = 0;
    long long crc_sum = 0, len_sum = 0, cmp_sum = 0;
    long long set_sum = 0, get_sum = 0, upd_sum = 0, upd_get = 0, off_sum = 0;
    long long expect;
    long long t0, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15;

    t0 = stamp();
    for (i = 0; i < n; i++) write_key(keys + i * 16, i);
    for (i = 0; i < n; i++) write_key(keys + i * 16, i);
    t1 = stamp();

    for (i = 0; i < n; i++) write_key(keys2 + i * 16, i);

    t2 = stamp();
    for (i = 0; i < n; i++) crc_sum += hash_key(keys + i * 16);
    for (i = 0; i < n; i++) crc_sum += hash_key(keys + i * 16);
    t3 = stamp();

    t4 = stamp();
    for (i = 0; i < n; i++) len_sum += (long long)strlen(keys + i * 16);
    for (i = 0; i < n; i++) len_sum += (long long)strlen(keys + i * 16);
    t5 = stamp();

    t6 = stamp();
    for (i = 0; i < n; i++) cmp_sum += strcmp(keys + i * 16, keys2 + i * 16);
    for (i = 0; i < n; i++) cmp_sum += strcmp(keys + i * 16, keys2 + i * 16);
    t7 = stamp();

    char *copies = (char *)calloc((size_t)n, 16);
    long long copy_sum = 0;
    long long t16, t17, t18, t19, t20, t21;
    char *bump;
    char *bp;
    void **ord;
    int ord_cap, ord_n;
    long long kb_sum = 0;

    t16 = stamp();
    for (i = 0; i < n; i++) {
        char *src = keys + i * 16;
        char *dst = copies + i * 16;
        memcpy(dst, src, 8);
        copy_sum += (unsigned char)dst[0];
    }
    t17 = stamp();

    bump = (char *)malloc((size_t)n * 32);
    bp = bump;
    t18 = stamp();
    for (i = 0; i < n; i++) {
        char *cell = bp + 8;
        memcpy(cell, keys + i * 16, 8);
        cell[8] = 0;
        bp += 24;
        kb_sum += (unsigned char)cell[0];
    }
    t19 = stamp();

    ord = (void **)malloc(8 * sizeof(void *));
    ord_cap = 8;
    ord_n = 0;
    t20 = stamp();
    for (i = 0; i < n; i++) {
        if (ord_n >= ord_cap) {
            int nc = ord_cap * 2;
            void **nd = (void **)malloc((size_t)nc * sizeof(void *));
            memcpy(nd, ord, (size_t)ord_n * sizeof(void *));
            free(ord);
            ord = nd;
            ord_cap = nc;
        }
        ord[ord_n] = keys + i * 16;
        ord_n++;
    }
    t21 = stamp();

    table_init(&table, 16);
    t8 = stamp();
    for (i = 0; i < n; i++) set_sum += table_set(&table, keys + i * 16, i + 1);
    t9 = stamp();

    t10 = stamp();
    for (i = 0; i < n; i++) get_sum += table_get(&table, keys + i * 16);
    t11 = stamp();

    t12 = stamp();
    for (i = 0; i < n; i++) upd_sum += table_set(&table, keys + i * 16, i + 2);
    t13 = stamp();

    for (i = 0; i < n; i++) upd_get += table_get(&table, keys + i * 16);

    table_init(&table2, 16);
    t14 = stamp();
    for (i = 0; i < n; i++) {
        write_key(one, i);
        table_set(&table2, one, i + 1);
    }
    for (i = 0; i < n; i++) {
        write_key(one, i);
        off_sum += table_get(&table2, one);
    }
    t15 = stamp();

    expect = (long long)n * (n + 1) / 2;
    if (len_sum != 320000) fails++;
    if (cmp_sum != 0) fails++;
    if (set_sum != n) fails++;
    if (get_sum != expect) fails++;
    if (upd_sum != 0) fails++;
    if (upd_get != expect + n) fails++;
    if (off_sum != expect) fails++;
    if (table.size != n) fails++;
    if (copy_sum != 2140000) fails++;
    if (kb_sum != 2140000) fails++;
    if (ord_n != n) fails++;

    printf("CHECK phases fails %d crc %lld len %lld cmp %lld set %lld get %lld upd %lld official %lld\n",
           fails, crc_sum, len_sum, cmp_sum, set_sum, get_sum, upd_sum, off_sum);
    printf("TIME write2 ns %lld\n", t1 - t0);
    printf("TIME crc2 ns %lld\n", t3 - t2);
    printf("TIME len2 ns %lld\n", t5 - t4);
    printf("TIME cmp2 ns %lld\n", t7 - t6);
    printf("TIME copy8 ns %lld\n", t17 - t16);
    printf("TIME keybytes ns %lld\n", t19 - t18);
    printf("TIME order ns %lld\n", t21 - t20);
    printf("TIME set ns %lld\n", t9 - t8);
    printf("TIME get ns %lld\n", t11 - t10);
    printf("TIME update ns %lld\n", t13 - t12);
    printf("TIME official ns %lld\n", t15 - t14);

    table_free(&table);
    table_free(&table2);
    free(keys);
    free(keys2);
    free(copies);
    free(bump);
    free(ord);
    return fails == 0 ? 0 : 1;
}
