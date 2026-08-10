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

// Helper: Read 16-bit big-endian unsigned integer
uint16_t read_u16(const uint8_t** ptr) {
    uint16_t bits = ((*ptr)[0] << 8) | (*ptr)[1];
    (*ptr) += 2;
    return bits;
}

// Helper: Read 32-bit big-endian float (IEEE 754)
float read_f32(const uint8_t** ptr) {
    uint32_t bits = ((*ptr)[0] << 24) | ((*ptr)[1] << 16) | ((*ptr)[2] << 8) | (*ptr)[3];
    (*ptr) += 4;
    float f;
    memcpy(&f, &bits, 4); 
    return f;
}

void parse_layout_constraints(const uint8_t* payload) {
    const uint8_t* ptr = payload;
    uint8_t opcode = *ptr++;
    
    if (opcode == 0x43) { // LAYOUT_CONSTRAINTS
        uint32_t node_id = read_varuint(&ptr);
        uint16_t min_w   = read_u16(&ptr);
        uint16_t min_h   = read_u16(&ptr);
        uint16_t max_w   = read_u16(&ptr);
        uint16_t max_h   = read_u16(&ptr);
        uint16_t pref_w  = read_u16(&ptr);
        uint16_t pref_h  = read_u16(&ptr);
        float weight_x   = read_f32(&ptr);
        float weight_y   = read_f32(&ptr);
        
        printf("[TVG] Parsed LAYOUT_CONSTRAINTS (0x43) for Node %u\n", node_id);
        printf("  ├─ Min Size:  %u x %u\n", min_w, min_h);
        printf("  ├─ Max Size:  %u x %u\n", max_w, max_h);
        printf("  ├─ Pref Size: %u x %u\n", pref_w, pref_h);
        printf("  └─ Weights:   X=%.2f, Y=%.2f\n\n", weight_x, weight_y);
    }
}

int main() {
    printf("--- Web 3.0 Client: Auckland Layout Constraint Parser ---\n\n");
    // Opcode 0x43, NodeID 0x0A (10), Min: 50x50, Max: 500x0(none), Pref: 200x50, Wgt: 1.0x0.0
    uint8_t dummy_payload[] = {
        0x43, 0x0A, 0x00, 0x32, 0x00, 0x32, 0x01, 0xF4, 0x00, 0x00, 0x00, 0xC8, 0x00, 0x32, 0x3F, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    };
    parse_layout_constraints(dummy_payload);
    return 0;
}