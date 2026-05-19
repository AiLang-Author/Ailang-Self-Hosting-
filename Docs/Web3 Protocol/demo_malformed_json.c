#include <stdio.h>
#include <stdint.h>
#include <string.h>

// A highly simplified, fast JSON structural validator
// In a real client, this would be a single-pass tokenizer (like jsmn)
int validate_json_structure(const char* payload, uint32_t len) {
    int depth = 0;
    int in_string = 0;
    
    for (uint32_t i = 0; i < len; i++) {
        char c = payload[i];
        
        if (c == '"' && (i == 0 || payload[i-1] != '\\')) {
            in_string = !in_string;
        }
        
        if (!in_string) {
            if (c == '{' || c == '[') depth++;
            if (c == '}' || c == ']') depth--;
        }
        
        if (depth < 0) return 0; // Unmatched closing brace/bracket
    }
    
    return (depth == 0 && !in_string) ? 1 : 0;
}

void process_update_frame(const uint8_t* header, const char* payload) {
    uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
    
    printf("[Client] Receiving UPDATE frame (%u bytes)...\n", payload_len);
    
    if (!validate_json_structure(payload, payload_len)) {
        // Gracefully drop the frame and emit the Web 3.0 error code
        printf("  └─ [REJECTED] ERROR 105: BAD_JSON. Dropping malformed frame.\n\n");
        return;
    }
    
    printf("  └─ [ACCEPTED] JSON is structurally sound. Proceeding to update scene graph.\n\n");
}

int main() {
    printf("--- Web 3.0 Client: Malformed Frame Handling ---\n\n");
    
    // Simulated Frame Header (Type 0x04 = UPDATE)
    uint8_t header[8] = { 0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
    
    // Test 1: Perfectly valid JSON UPDATE
    const char* valid_payload = "{\"version\":\"1.0\",\"type\":\"update\",\"seq\":10}";
    header[7] = strlen(valid_payload); // Set length byte
    printf("Test 1: Valid JSON Payload\n");
    process_update_frame(header, valid_payload);
    
    // Test 2: Malformed JSON (Missing closing brace)
    // This simulates a truncated socket read or a server-side crash during generation
    const char* malformed_payload = "{\"version\":\"1.0\",\"type\":\"update\",\"seq\":11";
    header[7] = strlen(malformed_payload);
    printf("Test 2: Malformed JSON Payload (Truncated)\n");
    process_update_frame(header, malformed_payload);
    
    return 0;
}