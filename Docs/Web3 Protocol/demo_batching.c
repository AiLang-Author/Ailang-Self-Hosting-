#include <stdio.h>
#include <stdint.h>

int defer_render = 0;

void trigger_render() {
    if (defer_render) {
        printf("  └─ [Render Engine] Skipped paint. Framebuffer is currently LOCKED.\n");
    } else {
        printf("  └─ [Render Engine] Pushing updated scene graph to display -> (FLUSH!)\n");
    }
}

void parse_tvg_commands(const uint8_t* ptr, int len) {
    const uint8_t* end = ptr + len;
    
    while (ptr < end) {
        uint8_t opcode = *ptr++;
        
        if (opcode == 0x00) { // BATCH_BEGIN
            uint8_t flags = *ptr++;
            printf("[TVG] BATCH_BEGIN (flags=0x%02X) - Locking display...\n", flags);
            defer_render = 1;
        } 
        else if (opcode == 0x01) { // BATCH_END
            printf("[TVG] BATCH_END - Unlocking display...\n");
            defer_render = 0;
            trigger_render();
        } 
        else if (opcode == 0x10) { // SG_NODE_CREATE (Mocked simplified args)
            uint8_t id = *ptr++;
            printf("[TVG] SG_NODE_CREATE (node=%d)\n", id);
            trigger_render(); // Implicitly triggers a render if not batched
        }
    }
}

int main() {
    printf("--- Web 3.0 Client: Batch Rendering ---\n\n");
    
    printf("Scenario 1: Unbatched Commands (Causes flickering)\n");
    uint8_t unbatched_cmds[] = { 0x10, 11, 0x10, 12, 0x10, 13 }; 
    parse_tvg_commands(unbatched_cmds, sizeof(unbatched_cmds));
    
    printf("\nScenario 2: Batched Commands (Atomic, flawless update)\n");
    uint8_t batched_cmds[] = { 
        0x00, 0x02, // BATCH_BEGIN (High priority)
        0x10, 21,   // SG_NODE_CREATE
        0x10, 22,   // SG_NODE_CREATE
        0x10, 23,   // SG_NODE_CREATE
        0x01        // BATCH_END
    };
    parse_tvg_commands(batched_cmds, sizeof(batched_cmds));
    
    return 0;
}