#include <stdio.h>
#include <stdint.h>

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

// Helper: Read 16-bit big-endian signed integer
int16_t read_i16(const uint8_t** ptr) {
    int16_t val = ((*ptr)[0] << 8) | (*ptr)[1];
    *ptr += 2;
    return val;
}

// Helper: Read 16-bit big-endian unsigned integer
uint16_t read_u16(const uint8_t** ptr) {
    uint16_t val = ((*ptr)[0] << 8) | (*ptr)[1];
    *ptr += 2;
    return val;
}

void parse_layout_set(const uint8_t* payload, uint32_t len) {
    const uint8_t* ptr = payload;
    if (*ptr++ == 0x41) { // 0x41 = LAYOUT_SET
        uint32_t node_id = read_varuint(&ptr);
        int16_t x = read_i16(&ptr);
        int16_t y = read_i16(&ptr);
        uint16_t w = read_u16(&ptr);
        uint16_t h = read_u16(&ptr);
        
        printf("[TVG Parser] Node %u bounds updated -> X:%d Y:%d W:%u H:%u\n", node_id, x, y, w, h);
        printf("  └─ [Native OS] Instructing hardware compositor to scale video overlay to %ux%u.\n\n", w, h);
    }
}

int main() {
    printf("--- Web 3.0 Client: Dynamic WebRTC Media Resizing ---\n\n");
    
    printf("Event 1: Initial Video Layout (1280x720 at origin 0,0)\n");
    uint8_t payload_initial[] = { 0x41, 0x32, 0x00, 0x00, 0x00, 0x00, 0x05, 0x00, 0x02, 0xD0 };
    parse_layout_set(payload_initial, sizeof(payload_initial));
    
    printf("Event 2: Window Maximized! Server sends updated layout (1920x1080 at offset 10,25)\n");
    uint8_t payload_resized[] = { 0x41, 0x32, 0x00, 0x0A, 0x00, 0x19, 0x07, 0x80, 0x04, 0x38 };
    parse_layout_set(payload_resized, sizeof(payload_resized));
    
    return 0;
}