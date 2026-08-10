#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <stdint.h>

#define SOCKET_PATH "/tmp/web3.sock"

/* 
 * Web 3.0 Frame Header (8 bytes)
 * Byte 0:     Version (0x01)
 * Byte 1:     Frame Type
 * Byte 2-3:   Flags (16-bit, big-endian)
 * Byte 4-7:   Payload Length (32-bit, big-endian)
 */

void send_hello(int sock) {
    // Minimum required fields per 03_WIRE_PROTOCOL.md HELLO schema
    const char* hello_json = 
        "{"
        "\"version\":\"1.0\","
        "\"encryption\":[\"none\"],"
        "\"compression\":[\"none\"],"
        "\"client_nonce\":\"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\""
        "}";
        
    uint32_t payload_len = strlen(hello_json);
    
    uint8_t header[8];
    header[0] = 0x01; // Version
    header[1] = 0x01; // Type: HELLO (0x01)
    header[2] = 0x00; // Flags (High)
    header[3] = 0x00; // Flags (Low)
    
    // Length (Big Endian)
    header[4] = (payload_len >> 24) & 0xFF;
    header[5] = (payload_len >> 16) & 0xFF;
    header[6] = (payload_len >> 8) & 0xFF;
    header[7] = payload_len & 0xFF;
    
    write(sock, header, 8);
    write(sock, hello_json, payload_len);
    printf("Sent HELLO frame (%u bytes).\n", payload_len);
}

void read_welcome(int sock) {
    uint8_t header[8];
    if (read(sock, header, 8) != 8) {
        perror("Failed to read frame header");
        return;
    }
    
    if (header[0] != 0x01) {
        printf("Protocol error: Unknown version 0x%02X\n", header[0]);
        return;
    }
    
    if (header[1] != 0x02) { // 0x02 = WELCOME
        printf("Protocol error: Expected WELCOME (0x02), got type 0x%02X\n", header[1]);
        return;
    }
    
    uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
    printf("Receiving WELCOME frame (%u bytes)...\n", payload_len);
    
    char* payload = malloc(payload_len + 1);
    int total_read = 0;
    while (total_read < payload_len) {
        int n = read(sock, payload + total_read, payload_len - total_read);
        if (n <= 0) break;
        total_read += n;
    }
    payload[total_read] = '\0';
    
    printf("Server replied: %s\n", payload);
    free(payload);
}

void mock_aead_encrypt(const uint8_t* plaintext, uint32_t pt_len, uint8_t* ciphertext, uint8_t* tag) {
    // Dummy ChaCha20-Poly1305 Encrypt (Simple XOR for demonstration)
    uint8_t dummy_key = 0x5A;
    for (uint32_t i = 0; i < pt_len; i++) {
        ciphertext[i] = plaintext[i] ^ dummy_key;
    }
    // Dummy 16-byte authentication tag
    memset(tag, 0xAA, 16);
}

void send_encrypted_event(int sock) {
    const char* event_json = "{\"version\":\"1.0\",\"type\":\"event\",\"action\":\"click\",\"target\":\"btn\",\"seq\":1}";
    uint32_t pt_len = strlen(event_json);
    
    uint8_t ciphertext[256];
    uint8_t tag[16];
    mock_aead_encrypt((const uint8_t*)event_json, pt_len, ciphertext, tag);
    
    uint32_t payload_len = pt_len + 16; // Ciphertext + Tag
    
    uint8_t header[8];
    header[0] = 0x01; // Version
    header[1] = 0x03; // Type: EVENT (0x03)
    header[2] = 0x00; // Flags (High)
    header[3] = 0x02; // Flags (Low) -> Bit 1 set: ENCRYPTED
    
    // Length (Big Endian)
    header[4] = (payload_len >> 24) & 0xFF;
    header[5] = (payload_len >> 16) & 0xFF;
    header[6] = (payload_len >> 8) & 0xFF;
    header[7] = payload_len & 0xFF;
    
    write(sock, header, 8);
    write(sock, ciphertext, pt_len);
    write(sock, tag, 16);
    printf("Sent Encrypted EVENT frame (%u bytes total).\n", payload_len);
}

int main() {
    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);
    
    printf("Connecting to %s...\n", SOCKET_PATH);
    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) == 0) {
        printf("Connected!\n");
        send_hello(sock);
        read_welcome(sock);
        send_encrypted_event(sock);
    } else {
        perror("Connection failed");
    }
    
    close(sock);
    return 0;
}