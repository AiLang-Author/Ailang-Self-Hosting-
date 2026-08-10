#include <stdio.h>
#include <stdint.h>

// The client's local tracker for the NEXT expected server frame
uint64_t expected_seq = 100; // Arbitrary start based on handshake

void process_update_frame(uint64_t incoming_seq) {
    printf("Incoming UPDATE Frame [Seq: %llu]\n", (unsigned long long)incoming_seq);
    
    if (incoming_seq == expected_seq) {
        printf("  └─ [ACCEPTED] Sequence matches exactly. Processing payload...\n\n");
        expected_seq++; // Increment after successful processing
    } 
    else if (incoming_seq < expected_seq) {
        printf("  └─ [REJECTED] Replay Attack Detected!\n");
        printf("     Expected seq >= %llu, but got %llu. Dropping frame.\n\n", 
               (unsigned long long)expected_seq, (unsigned long long)incoming_seq);
    } 
    else {
        printf("  └─ [FATAL] Sequence Gap Detected!\n");
        printf("     Expected seq %llu, but got %llu. ERROR 109: SEQUENCE_GAP.\n", 
               (unsigned long long)expected_seq, (unsigned long long)incoming_seq);
        printf("     Client must tear down socket and attempt resume/reconnect.\n\n");
        
        // For the sake of continuing the demo, we sync it up
        expected_seq = incoming_seq + 1; 
    }
}

int main() {
    printf("--- Web 3.0 Client: Sequence Tracking & Anti-Replay ---\n\n");
    
    // 1. Normal expected operation
    process_update_frame(100);
    process_update_frame(101);
    
    // 2. An attacker tries to replay an old frame
    printf(">> Network Attacker injects a captured older frame...\n");
    process_update_frame(100);
    
    // 3. A frame is dropped/lost over the network (e.g. UDP/WebSocket desync)
    printf(">> Frame 102 is lost in transit...\n");
    process_update_frame(103);
    
    process_update_frame(104);
    
    return 0;
}