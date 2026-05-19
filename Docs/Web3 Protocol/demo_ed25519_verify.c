#include <stdio.h>
#include <stdint.h>
#include <string.h>

// Mock Ed25519 Signature Verification
// In a real client, this uses a crypto library (e.g. libsodium, Monocypher)
int mock_ed25519_verify(const uint8_t* signature, const uint8_t* message, uint32_t message_len, const uint8_t* pubkey) {
    // For this mock, we just check if the signature is all 0xED
    for (int i = 0; i < 64; i++) {
        if (signature[i] != 0xED) return 0;
    }
    return 1;
}

void process_signed_update(const uint8_t* header, const uint8_t* payload, const uint8_t* signature, const uint8_t* pubkey) {
    uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
    
    printf("Incoming Signed UPDATE Frame (%u bytes payload)\n", payload_len);
    
    // The message to verify includes the header and the payload
    uint32_t msg_len = 8 + payload_len;
    uint8_t message[msg_len];
    memcpy(message, header, 8);
    memcpy(message + 8, payload, payload_len);
    
    printf("  └─ Verifying Ed25519 Signature (64 bytes)...\n");
    if (mock_ed25519_verify(signature, message, msg_len, pubkey)) {
        printf("  └─ [ACCEPTED] Signature is valid. Trusted server verified.\n\n");
    } else {
        printf("  └─ [REJECTED] Invalid signature! Potential MITM attack. Dropping frame.\n\n");
    }
}

int main() {
    printf("--- Web 3.0 Client: Mode 3 Ed25519 Signature Verification ---\n\n");
    
    uint8_t mock_pubkey[32] = {0}; 
    
    uint8_t header[8] = { 0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10 };
    uint8_t payload[16] = "mock_tvg_payload";
    
    uint8_t valid_signature[64];
    memset(valid_signature, 0xED, 64);
    
    uint8_t invalid_signature[64];
    memset(invalid_signature, 0xBA, 64);
    
    printf("Test 1: Valid Signature\n");
    process_signed_update(header, payload, valid_signature, mock_pubkey);
    
    printf("Test 2: Invalid Signature (Tampered Payload)\n");
    process_signed_update(header, payload, invalid_signature, mock_pubkey);
    
    return 0;
}