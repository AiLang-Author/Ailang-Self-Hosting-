#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define MAX_CACHED_ICONS 256

// Represents a client-side cache entry for a TVG Icon Resource
typedef struct {
    uint32_t id;
    char name[64];
    uint32_t data_length;
    uint8_t* tvg_data;
    int active;
} IconCacheEntry;

IconCacheEntry icon_cache[MAX_CACHED_ICONS] = {0};

// Helper: Read LEB128 unsigned integer (varuint)
uint32_t read_varuint(const uint8_t** ptr) {
    uint32_t result = 0, shift = 0;
    while (1) {
        uint8_t byte = **ptr; (*ptr)++;
        result |= (byte & 0x7F) << shift;
        if ((byte & 0x80) == 0) break;
        shift += 7;
    }
    return result;
}

void handle_res_icon(const uint8_t** ptr) {
    uint32_t res_id = read_varuint(ptr);
    
    uint32_t name_len = read_varuint(ptr);
    char name[64] = {0};
    if (name_len < 64) {
        memcpy(name, *ptr, name_len);
        *ptr += name_len;
    }
    
    uint32_t data_len = read_varuint(ptr);
    
    if (res_id < MAX_CACHED_ICONS) {
        // Free existing data if overwriting
        if (icon_cache[res_id].active) {
            free(icon_cache[res_id].tvg_data);
        }
        
        // Store in the client-side flat cache
        icon_cache[res_id].id = res_id;
        strcpy(icon_cache[res_id].name, name);
        icon_cache[res_id].data_length = data_len;
        icon_cache[res_id].tvg_data = malloc(data_len);
        memcpy(icon_cache[res_id].tvg_data, *ptr, data_len);
        icon_cache[res_id].active = 1;
        
        printf("[Cache] Stored RES_ICON: ID=%u, Name='%s', Size=%u bytes\n", res_id, name, data_len);
    }
    *ptr += data_len;
}

void render_icon(uint32_t res_id) {
    printf("[Render] Requested to draw Icon ID %u...\n", res_id);
    if (res_id < MAX_CACHED_ICONS && icon_cache[res_id].active) {
        printf("  └─ Found in cache! Name: '%s', Data: ", icon_cache[res_id].name);
        for(uint32_t i = 0; i < icon_cache[res_id].data_length; i++) {
            printf("%02X ", icon_cache[res_id].tvg_data[i]);
        }
        printf("\n\n");
    } else {
        printf("  └─ ERROR: Icon ID %u not found in cache.\n\n", res_id);
    }
}

int main() {
    printf("--- Web 3.0 Client: RES_ICON Caching Mock ---\n\n");
    
    // Mock payload: RES_ICON (0x51), ID 42 (0x2A), Name "save" (4 bytes), Data: [0xAA 0xBB 0xCC]
    uint8_t dummy_payload[] = {
        0x51, 0x2A, 0x04, 's', 'a', 'v', 'e', 0x03, 0xAA, 0xBB, 0xCC
    };
    
    const uint8_t* ptr = dummy_payload;
    if (*ptr++ == 0x51) {
        handle_res_icon(&ptr);
    }
    printf("\n");
    
    render_icon(42); // This will succeed
    render_icon(99); // This will fail (not cached)
    
    return 0;
}