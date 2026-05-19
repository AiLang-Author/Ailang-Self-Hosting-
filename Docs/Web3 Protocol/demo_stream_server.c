#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <stdint.h>
#include <time.h>

#define SOCKET_PATH "/tmp/web3.sock"

void send_welcome(int client_sock) {
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
    uint8_t header[8] = { 0x01, 0x02, 0x00, 0x00, 
                          (payload_len >> 24) & 0xFF, (payload_len >> 16) & 0xFF, 
                          (payload_len >> 8) & 0xFF, payload_len & 0xFF };
    
    write(client_sock, header, 8);
    write(client_sock, welcome_json, payload_len);
    printf("Sent WELCOME frame.\n");
}

int read_hello(int client_sock) {
    uint8_t header[8];
    if (read(client_sock, header, 8) != 8) return 0;
    if (header[0] != 0x01 || header[1] != 0x01) return 0;
    
    uint32_t payload_len = (header[4] << 24) | (header[5] << 16) | (header[6] << 8) | header[7];
    char* payload = malloc(payload_len + 1);
    read(client_sock, payload, payload_len);
    payload[payload_len] = '\0';
    printf("Client Connected. Received HELLO.\n");
    free(payload);
    return 1;
}

void push_stream_update(int client_sock, uint64_t seq) {
    char json_buf[512];
    
    // Simulate fluctuating data, like a server-side CPU gauge
    int cpu_load = rand() % 100;
    
    snprintf(json_buf, sizeof(json_buf),
        "{"
        "\"version\":\"1.0\","
        "\"type\":\"update\","
        "\"seq\":%llu,"
        "\"region\":\"dashboard\","
        "\"commands\":["
        "  {\"op\":\"text\",\"node\":\"cpu-gauge-text\",\"content\":\"CPU: %d%%\"},"
        "  {\"op\":\"style\",\"node\":\"cpu-gauge-bar\",\"fill\":\"%s\"}"
        "]"
        "}", 
        (unsigned long long)seq, 
        cpu_load,
        cpu_load > 85 ? "#FF0000" : "#228B22" // Red if high, Green if normal
    );
        
    uint32_t payload_len = strlen(json_buf);
    
    // Frame Type 0x04 = UPDATE
    uint8_t header[8] = { 0x01, 0x04, 0x00, 0x00, 
                          (payload_len >> 24) & 0xFF, (payload_len >> 16) & 0xFF, 
                          (payload_len >> 8) & 0xFF, payload_len & 0xFF };
                          
    if (write(client_sock, header, 8) <= 0) return;
    if (write(client_sock, json_buf, payload_len) <= 0) return;
    
    printf("[Stream] Pushed UPDATE (seq=%llu): CPU Load = %d%%\n", (unsigned long long)seq, cpu_load);
}

int main() {
    int server_sock = socket(AF_UNIX, SOCK_STREAM, 0);
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);
    
    unlink(SOCKET_PATH);
    if (bind(server_sock, (struct sockaddr*)&addr, sizeof(addr)) == -1) return 1;
    if (listen(server_sock, 5) == -1) return 1;
    
    printf("Web3 Streaming Mock Server listening on %s\n", SOCKET_PATH);
    srand(time(NULL));
    
    while (1) {
        int client_sock = accept(server_sock, NULL, NULL);
        if (client_sock == -1) continue;
        
        if (read_hello(client_sock)) {
            send_welcome(client_sock);
            
            uint64_t seq = 100; // Start sequence arbitrarily at 100
            while (1) {
                sleep(1); // Wait 1 second between updates
                push_stream_update(client_sock, seq++);
            }
        }
    }
    
    close(server_sock);
    return 0;
}