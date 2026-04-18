#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

int main() {
    printf("=== glibc malloc Speed Test ===\n\n");

    int iterations = 10000000;
    int block_size = 64;
    void* last_ptr = NULL;

    /* Phase 1: sequential alloc, no free */
    printf("Phase 1: 10M x 64-byte alloc (no free, sequential)...\n");
    for (int i = 0; i < iterations; i++) {
        void* ptr = malloc(block_size);
        *(char*)ptr = 1;
        last_ptr = ptr;
    }
    printf("Done. Last ptr: %p\n\n", last_ptr);

    /* Phase 2: alloc + immediate free */
    printf("Phase 2: 10M x alloc/free cycles (64 bytes)...\n");
    for (int i = 0; i < iterations; i++) {
        void* ptr = malloc(block_size);
        *(char*)ptr = 1;
        free(ptr);
    }
    printf("Done.\n\n");

    /* Phase 3: mixed sizes */
    printf("Phase 3: 10M x mixed size alloc/free (64/128/256)...\n");
    for (int i = 0; i < iterations; i++) {
        int mod = i % 3;
        void* ptr;
        if (mod == 0) {
            ptr = malloc(64);
            *(char*)ptr = 1;
            free(ptr);
        } else if (mod == 1) {
            ptr = malloc(128);
            *(char*)ptr = 1;
            free(ptr);
        } else {
            ptr = malloc(256);
            *(char*)ptr = 1;
            free(ptr);
        }
    }
    printf("Done.\n\n");

    /* Phase 4: batch alloc then batch free */
    printf("Phase 4: Batch alloc 100K then batch free...\n");
    int batch_size = 100000;
    void** ptrs = malloc(batch_size * sizeof(void*));

    for (int outer = 0; outer < 100; outer++) {
        for (int i = 0; i < batch_size; i++) {
            ptrs[i] = malloc(64);
            *(char*)ptrs[i] = 1;
        }
        for (int i = 0; i < batch_size; i++) {
            free(ptrs[i]);
        }
    }
    free(ptrs);
    printf("Done.\n\n");

    printf("=== Complete ===\n");
    return 0;
}