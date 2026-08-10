#include <stdio.h>
#include <stdint.h>

#define MAX_PAYLOAD_SIZE (4 * 1024 * 1024) // 4 MB limit for UPDATE frames

void process_frame_header(const uint8_t* header) {
    uint8_t type = header[1];
    uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
    
    printf("Incoming Frame Header (Type: 0x%02X, Advertised Length: %u bytes)\n", type, payload_len);
    
    if (payload_len > MAX_PAYLOAD_SIZE) {
        printf("  └─ [REJECTED] ERROR 201: PAYLOAD_TOO_LARGE.\n");
        printf("     Length %u exceeds maximum allowed size of %u bytes.\n", payload_len, MAX_PAYLOAD_SIZE);
        printf("     Dropping frame securely (no memory allocated).\n\n");
        return;
    }
    
    printf("  └─ [ACCEPTED] Payload size is within limits. Proceeding to allocate and read.\n\n");
}

int main() {
    printf("--- Web 3.0 Client: Oversized Payload Security Check ---\n\n");
    
    // Test 1: Valid 1 KB Payload
    uint32_t safe_len = 1024;
    uint8_t safe_header[8] = { 0x01, 0x04, 0x00, 0x00, 
                              (safe_len >> 24) & 0xFF, (safe_len >> 16) & 0xFF, 
                              (safe_len >> 8) & 0xFF, safe_len & 0xFF };
    printf("Test 1: Safe Payload Size (1 KB)\n");
    process_frame_header(safe_header);
    
    // Test 2: Malicious/Oversized 10 MB Payload
    uint32_t malicious_len = 10 * 1024 * 1024;
    uint8_t malicious_header[8] = { 0x01, 0x04, 0x00, 0x00, 
                                   (malicious_len >> 24) & 0xFF, (malicious_len >> 16) & 0xFF, 
                                   (malicious_len >> 8) & 0xFF, malicious_len & 0xFF };
    printf("Test 2: Malicious Payload Size (10 MB)\n");
    process_frame_header(malicious_header);
    
    return 0;
}