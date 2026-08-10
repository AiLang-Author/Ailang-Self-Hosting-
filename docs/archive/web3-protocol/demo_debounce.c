#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

#define DEBOUNCE_DELAY_MS 200

// Simulates a client-side text input element's local state
char input_buffer[256] = {0};
int cursor_pos = 0;

// Debounce state tracking
long long last_keypress_time = 0;
int has_pending_event = 0;

long long current_time_ms() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (tv.tv_sec * 1000LL) + (tv.tv_usec / 1000);
}

void send_input_event() {
    // In a real client, this constructs the JSON and writes to the IPC socket
    printf("\n>>> [NETWORK] Sending EVENT: {\"action\": \"input\", \"payload\": {\"value\": \"%s\", \"cursor\": %d}}\n\n", 
           input_buffer, cursor_pos);
    has_pending_event = 0; // Clear the pending flag
}

void on_user_keypress(char c) {
    // Update the local buffer immediately so the user sees their typing
    input_buffer[cursor_pos++] = c;
    input_buffer[cursor_pos] = '\0';
    
    // Update the debounce timer and flag
    last_keypress_time = current_time_ms();
    has_pending_event = 1;
    
    printf("[UI] User typed '%c' -> Local Buffer: \"%s\" (Network Event Deferred)\n", c, input_buffer);
}

void client_event_loop_tick() {
    // Called every frame (e.g., 60 FPS) to check for pending deferred events
    if (has_pending_event) {
        long long now = current_time_ms();
        if (now - last_keypress_time >= DEBOUNCE_DELAY_MS) {
            send_input_event();
        }
    }
}

int main() {
    printf("Simulating a user typing \"Web 3.0\" at 50ms per keystroke...\n\n");
    
    char* text = "Web 3.0";
    for (int i = 0; i < strlen(text); i++) {
        on_user_keypress(text[i]);
        usleep(50 * 1000); // Sleep 50ms to simulate rapid typing
        client_event_loop_tick(); // Check timers
    }
    
    printf("\n[UI] User paused typing...\n");
    
    // Keep running the event loop to allow the debounce timer to pop
    for (int i = 0; i < 5; i++) {
        usleep(50 * 1000);
        client_event_loop_tick();
    }
    
    return 0;
}