#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/socket.h>
#include <stdint.h>

/*
 * Web 3.0 Frame Header (8 bytes)
 * Type 0x07 = PING
 * Type 0x08 = PONG
 * Length is 0 for keepalives.
 */

void send_ping(int sock) {
    uint8_t header[8] = { 0x01, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
    write(sock, header, 8);
    printf("[Server] Sent PING (0x07).\n");
}

void send_pong(int sock) {
    uint8_t header[8] = { 0x01, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
    write(sock, header, 8);
    printf("[Client] Sent PONG (0x08) response.\n");
}

void client_listen_loop(int sock) {
    uint8_t header[8];
    // Client blocks waiting for a frame
    if (read(sock, header, 8) == 8) {
        uint8_t type = header[1];
        if (type == 0x07) {
            printf("[Client] Received PING. Replying immediately...\n");
            send_pong(sock);
        } else {
            printf("[Client] Received unknown frame: 0x%02X\n", type);
        }
    }
}

void server_listen_loop(int sock) {
    uint8_t header[8];
    if (read(sock, header, 8) == 8) {
        uint8_t type = header[1];
        if (type == 0x08) {
            printf("[Server] Received PONG. Client is alive!\n");
        }
    }
}

int main() {
    // Create a local bi-directional pipe to simulate the IPC connection
    int socks[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, socks) == -1) {
        perror("socketpair");
        return 1;
    }
    
    int server_sock = socks[0];
    int client_sock = socks[1];
    
    printf("--- Web 3.0 Keepalive Simulation ---\n\n");
    
    send_ping(server_sock);
    client_listen_loop(client_sock);
    server_listen_loop(server_sock);
    
    close(server_sock);
    close(client_sock);
    
    return 0;
}