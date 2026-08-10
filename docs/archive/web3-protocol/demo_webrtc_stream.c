#include <stdio.h>
#include <stdint.h>
#include <string.h>

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

void parse_media_commands(const uint8_t* payload, uint32_t len) {
    const uint8_t* ptr = payload;
    const uint8_t* end = payload + len;
    
    while (ptr < end) {
        uint8_t opcode = *ptr++;
        
        if (opcode == 0x54) { // RES_STREAM
            uint32_t res_id = read_varuint(&ptr);
            uint8_t type = *ptr++;
            uint32_t str_len = read_varuint(&ptr);
            
            char config[128] = {0};
            if (str_len < sizeof(config)) {
                memcpy(config, ptr, str_len);
            }
            ptr += str_len;
            
            printf("[TVG] Parsed RES_STREAM (0x54)\n");
            printf("  ├─ Resource ID: %u\n", res_id);
            printf("  ├─ Stream Type: 0x%02X (%s)\n", type, type == 2 ? "WebRTC" : "Other");
            printf("  └─ Config/URI:  '%s'\n\n", config);
        } 
        else if (opcode == 0x10) { // SG_NODE_CREATE
            uint32_t node_id = read_varuint(&ptr);
            uint8_t type = *ptr++;
            uint32_t parent_id = read_varuint(&ptr);
            
            printf("[TVG] Parsed SG_NODE_CREATE (0x10)\n");
            printf("  ├─ Node ID:   %u\n", node_id);
            printf("  ├─ Parent ID: %u\n", parent_id);
            
            if (type == 0x07) { // MEDIA_SURFACE (Requires an extra stream_id parameter)
                uint32_t stream_id = read_varuint(&ptr);
                printf("  ├─ Node Type: 0x07 (MEDIA_SURFACE)\n");
                printf("  └─ Stream ID: %u (Linked to Resource %u)\n\n", stream_id, stream_id);
            } else {
                printf("  └─ Node Type: 0x%02X\n\n", type);
            }
        }
    }
}

int main() {
    printf("--- Web 3.0 Client: WebRTC RES_STREAM Mapping ---\n\n");
    
    // Mock payload based on 08_MEDIA_RTC.md:
    // 1. RES_STREAM (0x54), res_id=10 (0x0A), type=2 (WebRTC), config="rtc-1" (5 bytes)
    // 2. SG_NODE_CREATE (0x10), node_id=50 (0x32), type=7 (MEDIA_SURFACE), parent=1 (0x01), stream_id=10 (0x0A)
    uint8_t dummy_payload[] = {
        0x54, 0x0A, 0x02, 0x05, 'r', 't', 'c', '-', '1',
        0x10, 0x32, 0x07, 0x01, 0x0A
    };
    
    parse_media_commands(dummy_payload, sizeof(dummy_payload));
    return 0;
}