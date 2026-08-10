#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

void mock_zstd_decompress(const uint8_t* compressed, uint32_t comp_len, uint8_t** decompressed, uint32_t* decomp_len) {
    printf("  [ZSTD] Decompressing %u bytes of payload...\n", comp_len);
    
    // In a real client, ZSTD_decompress() would be called here using the pre-trained TVG dictionary.
    // For this mock, we simulate an average 3x expansion ratio.
    *decomp_len = comp_len * 3;
    *decompressed = malloc(*decomp_len + 1);
    
    snprintf((char*)*decompressed, *decomp_len + 1, "{\"mock\":\"decompressed_data\"}");
    printf("  [ZSTD] Successfully decompressed to %u bytes.\n", *decomp_len);
}

void process_frame(const uint8_t* header, const uint8_t* payload) {
    uint16_t flags = (header[2] << 8) | header[3];
    uint32_t length = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
    
    printf("Received Frame (Type: 0x%02X, Flags: 0x%04X, Length: %u bytes)\n", header[1], flags, length);
    
    uint8_t* final_payload = (uint8_t*)payload;
    uint32_t final_length = length;
    int needs_free = 0;
    
    // Check Bit 0 of the flags (0x0001 = COMPRESSED)
    if (flags & 0x0001) { 
        printf("  └─ Status: COMPRESSED flag detected.\n");
        mock_zstd_decompress(payload, length, &final_payload, &final_length);
        needs_free = 1;
    } else {
        printf("  └─ Status: UNCOMPRESSED plaintext payload.\n");
    }
    
    printf("  └─ Proceeding to parser with %u bytes of data.\n\n", final_length);
    
    if (needs_free) {
        free(final_payload);
    }
}

int main() {
    printf("--- Web 3.0 Client: Compression Flag Handling ---\n\n");
    
    const char* mock_data = "raw_binary_stream";
    uint32_t len = strlen(mock_data);
    
    // Test 1: Uncompressed Frame
    uint8_t header_uncompressed[8] = { 0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, len };
    printf("Test 1: Uncompressed Frame\n");
    process_frame(header_uncompressed, (const uint8_t*)mock_data);
    
    // Test 2: Compressed Frame (Flags = 0x0001)
    uint8_t header_compressed[8] = { 0x01, 0x04, 0x00, 0x01, 0x00, 0x00, 0x00, len };
    printf("Test 2: Compressed (ZSTD) Frame\n");
    process_frame(header_compressed, (const uint8_t*)mock_data);
    
    return 0;
}