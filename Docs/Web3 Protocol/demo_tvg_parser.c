#include <stdio.h>
#include <stdint.h>
#include <string.h>

// Helper: Read LEB128 unsigned integer (varuint)
uint32_t read_varuint(const uint8_t** ptr) {
    uint32_t result = 0;
    uint32_t shift = 0;
    while (1) {
        uint8_t byte = **ptr;
        (*ptr)++;
        result |= (byte & 0x7F) << shift;
        if ((byte & 0x80) == 0) break;
        shift += 7;
    }
    return result;
}

// Helper: Read 32-bit big-endian float (IEEE 754)
float read_f32(const uint8_t** ptr) {
    uint32_t bits = ((*ptr)[0] << 24) | ((*ptr)[1] << 16) | ((*ptr)[2] << 8) | (*ptr)[3];
    (*ptr) += 4;
    float f;
    memcpy(&f, &bits, 4); // Safe type-punning
    return f;
}

// Helper: Read 16-bit big-endian signed integer
int16_t read_i16(const uint8_t** ptr) {
    uint16_t bits = ((*ptr)[0] << 8) | (*ptr)[1];
    (*ptr) += 2;
    return (int16_t)bits;
}

// Helper: Read 16-bit big-endian unsigned integer
uint16_t read_u16(const uint8_t** ptr) {
    uint16_t bits = ((*ptr)[0] << 8) | (*ptr)[1];
    (*ptr) += 2;
    return bits;
}

void parse_tvg_commands(const uint8_t* buffer, uint32_t length) {
    const uint8_t* ptr = buffer;
    const uint8_t* end = buffer + length;
    
    if (ptr + 4 > end) return;
    
    // The TVG_CMDS frame starts with a 32-bit big-endian command count
    uint32_t count = (ptr[0] << 24) | (ptr[1] << 16) | (ptr[2] << 8) | ptr[3];
    ptr += 4;
    
    printf("Parsing TVG frame with %u commands...\n", count);
    
    for (uint32_t i = 0; i < count && ptr < end; i++) {
        uint8_t opcode = *ptr++;
        
        switch (opcode) {
            case 0x00: { // BATCH_BEGIN
                uint8_t flags = *ptr++;
                printf("[%d] BATCH_BEGIN (flags: 0x%02X)\n", i, flags);
                break;
            }
            case 0x10: { // SG_NODE_CREATE
                uint32_t node_id = read_varuint(&ptr);
                uint8_t type = *ptr++;
                uint32_t parent_id = read_varuint(&ptr);
                printf("[%d] SG_NODE_CREATE (id: %u, type: %u, parent: %u)\n", i, node_id, type, parent_id);
                break;
            }
            case 0x30: { // TEXT_SET
                uint32_t node_id = read_varuint(&ptr);
                uint32_t str_len = read_varuint(&ptr);
                printf("[%d] TEXT_SET (node: %u, length: %u, string: \"%.*s\")\n", 
                       i, node_id, str_len, str_len, ptr);
                ptr += str_len;
                break;
            }
            case 0x41: { // LAYOUT_SET
                uint32_t node_id = read_varuint(&ptr);
                int16_t x = read_i16(&ptr);
                int16_t y = read_i16(&ptr);
                uint16_t w = read_u16(&ptr);
                uint16_t h = read_u16(&ptr);
                printf("[%d] LAYOUT_SET (node: %u, bounds: x:%d, y:%d, w:%u, h:%u)\n", 
                       i, node_id, x, y, w, h);
                break;
            }
            default:
                printf("[%d] UNKNOWN OPCODE: 0x%02X\n", i, opcode);
                return; // Stop parsing on unknown to prevent desync
        }
    }
}

int main() {
    // A mock binary TVG_CMDS payload matching the specs
    uint8_t dummy_payload[] = {
        // Command Count = 3
        0x00, 0x00, 0x00, 0x03, 
        
        // Cmd 0: BATCH_BEGIN (flags=0x02 high priority)
        0x00, 0x02,
        
        // Cmd 1: SG_NODE_CREATE (id=10, type=0 GROUP, parent=0) -> Note LEB128 encodes 10 as 0x0A
        0x10, 0x0A, 0x00, 0x00,
        
        // Cmd 2: LAYOUT_SET (id=10, x=100, y=50, w=200, h=30) -> opcode 0x41
        0x41, 0x0A, 0x00, 0x64, 0x00, 0x32, 0x00, 0xC8, 0x00, 0x1E
    };
    
    parse_tvg_commands(dummy_payload, sizeof(dummy_payload));
    return 0;
}