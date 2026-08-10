#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <stdint.h>

#define SOCKET_PATH "/tmp/web3.sock"

void send_hello(int sock) {
    const char* hello_json = 
        "{"
        "\"version\":\"1.0\","
        "\"encryption\":[\"none\"],"
        "\"compression\":[\"none\"],"
        "\"client_nonce\":\"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\""
        "}";
        
    uint32_t payload_len = strlen(hello_json);
    uint8_t header[8] = { 0x01, 0x01, 0x00, 0x00, 
                          (payload_len >> 24) & 0xFF, (payload_len >> 16) & 0xFF, 
                          (payload_len >> 8) & 0xFF, payload_len & 0xFF };
                          
    write(sock, header, 8);
    write(sock, hello_json, payload_len);
    printf("Sent HELLO frame.\n");
}

int read_welcome(int sock) {
    uint8_t header[8];
    if (read(sock, header, 8) != 8) return 0;
    if (header[0] != 0x01 || header[1] != 0x02) return 0; // 0x02 = WELCOME
    
    uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
    char* payload = malloc(payload_len + 1);
    
    int total_read = 0;
    while (total_read < payload_len) {
        int n = read(sock, payload + total_read, payload_len - total_read);
        if (n <= 0) break;
        total_read += n;
    }
    payload[payload_len] = '\0';
    
    printf("Received WELCOME: %s\n\n", payload);
    free(payload);
    return 1;
}

void listen_for_updates(int sock) {
    printf("Listening for streaming updates (press Ctrl+C to stop)...\n");
    while (1) {
        uint8_t header[8];
        if (read(sock, header, 8) <= 0) {
            printf("Server disconnected.\n");
            break;
        }
        
        uint8_t type = header[1];
        uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
        
        char* payload = malloc(payload_len + 1);
        int total_read = 0;
        while (total_read < payload_len) {
            int n = read(sock, payload + total_read, payload_len - total_read);
            if (n <= 0) break;
            total_read += n;
        }
        payload[payload_len] = '\0';
        
        if (type == 0x04) { // 0x04 = UPDATE
            printf("[Stream] Received UPDATE (%u bytes):\n%s\n\n", payload_len, payload);
        } else {
            printf("Received unknown frame type 0x%02X\n", type);
        }
        
        free(payload);
    }
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
        if (read_welcome(sock)) {
            listen_for_updates(sock);
        }
    } else {
        perror("Connection failed");
    }
    
    close(sock);
    return 0;
}