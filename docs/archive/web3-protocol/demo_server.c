#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <stdint.h>

#define SOCKET_PATH "/tmp/web3.sock"

void send_welcome(int client_sock) {
    // Minimum required fields per 03_WIRE_PROTOCOL.md WELCOME schema
    const char* welcome_json = 
        "{"
        "\"version\":\"1.0\","
        "\"session_id\":\"12345678-1234-1234-1234-123456789abc\","
        "\"encryption\":\"none\","
        "\"compression\":\"none\","
        "\"server_nonce\":\"BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=\","
        "\"server_pubkey\":\"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\""
        "}";
        
    uint32_t payload_len = strlen(welcome_json);
    
    uint8_t header[8];
    header[0] = 0x01; // Version
    header[1] = 0x02; // Type: WELCOME (0x02)
    header[2] = 0x00; // Flags (High)
    header[3] = 0x00; // Flags (Low)
    
    // Length (Big Endian)
    header[4] = (payload_len >> 24) & 0xFF;
    header[5] = (payload_len >> 16) & 0xFF;
    header[6] = (payload_len >> 8) & 0xFF;
    header[7] = payload_len & 0xFF;
    
    write(client_sock, header, 8);
    write(client_sock, welcome_json, payload_len);
    printf("Sent WELCOME frame (%u bytes).\n", payload_len);
}

void read_hello(int client_sock) {
    uint8_t header[8];
    if (read(client_sock, header, 8) != 8) {
        perror("Failed to read frame header");
        return;
    }
    
    if (header[0] != 0x01 || header[1] != 0x01) {
        printf("Protocol error: Expected HELLO (0x01), got 0x%02X\n", header[1]);
        return;
    }
    
    uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
    printf("Receiving HELLO frame (%u bytes)...\n", payload_len);
    
    char* payload = malloc(payload_len + 1);
    int total_read = 0;
    while (total_read < payload_len) {
        int n = read(client_sock, payload + total_read, payload_len - total_read);
        if (n <= 0) break;
        total_read += n;
    }
    payload[total_read] = '\0';
    
    printf("Client sent: %s\n", payload);
    free(payload);
}

int mock_aead_decrypt(const uint8_t* ciphertext, uint32_t ct_len, const uint8_t* tag, uint8_t* plaintext) {
    // Verify dummy Poly1305 tag
    for (int i = 0; i < 16; i++) {
        if (tag[i] != 0xAA) return 0; // Authentication failed
    }
    
    // Dummy ChaCha20-Poly1305 Decrypt (Simple XOR)
    uint8_t dummy_key = 0x5A;
    for (uint32_t i = 0; i < ct_len; i++) {
        plaintext[i] = ciphertext[i] ^ dummy_key;
    }
    return 1; // Success
}

void web3_dispatch(int client_sock, const char* event_json) {
    // Minimal JSON substring extraction for the C demo
    char action[64] = {0};
    const char* act_ptr = strstr(event_json, "\"action\":\"");
    if (act_ptr) {
        act_ptr += 10;
        int i = 0;
        while (*act_ptr && *act_ptr != '"' && i < 63) {
            action[i++] = *act_ptr++;
        }
    }
    
    printf("\n[Server Router] Dispatching Action: '%s'\n", action[0] ? action : "UNKNOWN");
    
    if (strcmp(action, "click") == 0) {
        printf("  └─ Logic: Handling click event...\n");
        printf("  └─ Out: Generating TVG UPDATE delta for the target region.\n");
    } else if (strcmp(action, "input") == 0) {
        printf("  └─ Logic: Handling text input keystroke...\n");
    } else {
        printf("  └─ Logic: Action not mapped in dispatch table.\n");
    }
}

int read_encrypted_event(int client_sock) {
    uint8_t header[8];
    int bytes_read = read(client_sock, header, 8);
    if (bytes_read <= 0) return 0; // Client disconnected
    
    if (header[1] != 0x03) { // 0x03 = EVENT
        printf("Protocol error: Expected EVENT, got 0x%02X\n", header[1]);
        return 0;
    }
    
    if ((header[3] & 0x02) == 0) {
        printf("Protocol error: EVENT frame must be ENCRYPTED!\n");
        return 0;
    }
    
    uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
    printf("Receiving Encrypted EVENT frame (%u bytes)...\n", payload_len);
    
    uint8_t* payload = malloc(payload_len);
    read(client_sock, payload, payload_len); // Simplifying read loop for demo
    
    uint32_t ct_len = payload_len - 16;
    uint8_t* plaintext = malloc(ct_len + 1);
    
    if (mock_aead_decrypt(payload, ct_len, payload + ct_len, plaintext)) {
        plaintext[ct_len] = '\0';
        printf("Successfully Decrypted Event: %s\n", plaintext);
        web3_dispatch(client_sock, (const char*)plaintext);
    } else {
        printf("AEAD Tag Authentication Failed!\n");
    }
    
    free(payload);
    free(plaintext);
    return 1;
}

void web3_session_loop(int client_sock) {
    read_hello(client_sock);
    send_welcome(client_sock);
    
    // Run the session until the client disconnects or fails
    while (read_encrypted_event(client_sock)) {
        // Waiting for the next frame...
    }
    printf("--- Client Disconnected ---\n");
}

int main() {
    int server_sock = socket(AF_UNIX, SOCK_STREAM, 0);
    
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);
    
    unlink(SOCKET_PATH); // Ensure previous runs don't block binding
    
    if (bind(server_sock, (struct sockaddr*)&addr, sizeof(addr)) == -1) {
        perror("Bind failed"); return 1;
    }
    
    if (listen(server_sock, 5) == -1) {
        perror("Listen failed"); return 1;
    }
    
    printf("Web3 Mock Server listening on %s\n", SOCKET_PATH);
    
    while (1) {
        int client_sock = accept(server_sock, NULL, NULL);
        if (client_sock == -1) continue;
        
        printf("\n--- Client Connected ---\n");
        web3_session_loop(client_sock);
        close(client_sock);
    }
    
    close(server_sock);
    unlink(SOCKET_PATH);
    return 0;
}