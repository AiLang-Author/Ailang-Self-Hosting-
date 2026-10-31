/* Flat open-address map. Keys live in the slot. Hash is SSE4.2 CRC32.
   Load limit is 70 percent. Empty hash is 0, tombstone is all-bits-one. */
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

static int table_has(Table *t, const char *key) {
    return find_slot(t, hash_key(key), key) >= 0;
}

static int table_del(Table *t, const char *key) {
    uint32_t h = hash_key(key);
    int slot = find_slot(t, h, key);
    if (slot < 0) return 0;
    t->slots[slot].hash = 0xffffffffu;
    t->slots[slot].value = 0;
    t->slots[slot].key[0] = 0;
    t->size--;
    return 1;
}

int main(void) {
    const int n = 20000;
    Table t;
    char key[16];
    int i, fails = 0, gone, has, put, v;
    long long sum = 0, expect;
    long long t0, t1;

    table_init(&t, 16);
    t0 = stamp();
    for (i = 0; i < n; i++) {
        write_key(key, i);
        table_set(&t, key, i + 1);
    }
    for (i = 0; i < n; i++) {
        write_key(key, i);
        sum += table_get(&t, key);
    }
    t1 = stamp();

    if (t.size != n) fails++;
    expect = (long long)n * (n + 1) / 2;
    if (sum != expect) fails++;

    write_key(key, 3);
    gone = table_del(&t, key);
    if (gone != 1) fails++;
    if (table_has(&t, key) != 0) fails++;
    if (table_get(&t, key) != 0) fails++;
    if (t.size != n - 1) fails++;
    put = table_set(&t, key, 99);
    if (put != 1) fails++;
    v = table_get(&t, key);
    if (v != 99) fails++;
    put = table_set(&t, key, 4);
    if (put != 0) fails++;
    v = table_get(&t, key);
    if (v != 4) fails++;
    has = table_has(&t, "no-such");
    if (has != 0) fails++;

    printf("CHECK hash fails %d sum %lld\n", fails, sum);
    printf("TIME hash crc32 ns %lld\n", t1 - t0);
    table_free(&t);
    return fails == 0 ? 0 : 1;
}
