#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

// Helper: Read LEB128 unsigned integer
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

// Helper: Read 32-bit big-endian float
float read_f32(const uint8_t** ptr) {
    uint32_t bits = ((*ptr)[0] << 24) | ((*ptr)[1] << 16) | ((*ptr)[2] << 8) | (*ptr)[3];
    (*ptr) += 4;
    float f;
    memcpy(&f, &bits, 4); 
    return f;
}

// Simulates the client's local font engine calculating bounding boxes
void measure_and_reply(uint32_t query_id, uint32_t font_res, float font_size, const char* text, uint32_t text_len) {
    // Fake measurement logic (e.g. assuming a fixed monospace for demonstration)
    // A real client would ask FreeType / CoreText / DirectWrite here
    float avg_char_width = font_size * 0.6f;
    
    float computed_width = avg_char_width * text_len;
    float computed_height = font_size * 1.2f;
    float computed_baseline = font_size * 0.9f;
    
    printf("Client measured text: \"%s\"\n", text);
    printf("  └─ Font Size: %.1fpx (Resource %u)\n", font_size, font_res);
    printf("  └─ Bounds: Width=%.2f, Height=%.2f, Baseline=%.2f\n\n", 
           computed_width, computed_height, computed_baseline);
           
    // Generate the JSON EVENT response to send back to the server
    char json_buf[512];
    snprintf(json_buf, sizeof(json_buf),
        "{\n"
        "  \"version\": \"1.0\",\n"
        "  \"type\": \"event\",\n"
        "  \"action\": \"text:measured\",\n"
        "  \"payload\": {\n"
        "    \"query_id\": %u,\n"
        "    \"width\": %.2f,\n"
        "    \"height\": %.2f,\n"
        "    \"baseline\": %.2f\n"
        "  },\n"
        "  \"seq\": 44\n"
        "}", query_id, computed_width, computed_height, computed_baseline);
        
    printf("Sending Response EVENT to Server over IPC:\n%s\n", json_buf);
}

void parse_tvg_command(const uint8_t* ptr) {
    uint8_t opcode = *ptr++;
    
    if (opcode == 0x32) { // TEXT_MEASURE
        uint32_t query_id = read_varuint(&ptr);
        uint32_t font_res = read_varuint(&ptr);
        float font_size = read_f32(&ptr);
        uint32_t str_len = read_varuint(&ptr);
        
        char* text = malloc(str_len + 1);
        memcpy(text, ptr, str_len);
        text[str_len] = '\0';
        
        measure_and_reply(query_id, font_res, font_size, text, str_len);
        free(text);
    }
}

int main() {
    // Mock binary buffer representing a TEXT_MEASURE command
    // Opcode (0x32), QueryID (1), FontRes (0), FontSize (16.0 = 0x41800000), StrLen (13)
    uint8_t dummy_payload[] = {
        0x32, 
        0x01, 0x00, 
        0x41, 0x80, 0x00, 0x00, 
        0x0D, 'H', 'e', 'l', 'l', 'o', ' ', 'W', 'e', 'b', ' ', '3', '.', '0'
    };
    
    parse_tvg_command(dummy_payload);
    return 0;
}