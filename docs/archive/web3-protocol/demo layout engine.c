#include <stdio.h>

// Represents a node's constraints in a single dimension (e.g., Width)
typedef struct {
    int id;
    int min_size;
    int max_size;
    int pref_size;
    float weight;
    
    // Output from the layout engine
    int computed_size;
    int computed_pos;
} AucklandNode1D;

// Resolves sizes and positions for a group of nodes along one axis
void resolve_auckland_group(
    AucklandNode1D* nodes, 
    int count, 
    int available_size, 
    int spacing
) {
    int total_pref = 0;
    float total_weight = 0.0f;
    int total_spacing = (count > 0) ? spacing * (count - 1) : 0;
    
    // Step 1: Accumulate baseline metrics
    for (int i = 0; i < count; i++) {
        total_pref += nodes[i].pref_size;
        total_weight += nodes[i].weight;
        // Start by assigning the preferred size
        nodes[i].computed_size = nodes[i].pref_size;
    }
    
    // Step 2: Determine how much extra or deficit space we have
    int free_space = available_size - (total_pref + total_spacing);
    
    // Step 3: Distribute space proportionally based on weight
    if (free_space != 0 && total_weight > 0.0f) {
        int distributed_space = 0;
        
        for (int i = 0; i < count; i++) {
            if (nodes[i].weight > 0.0f) {
                // Calculate this node's share of the free space
                float share = nodes[i].weight / total_weight;
                int delta = (int)(free_space * share);
                
                nodes[i].computed_size += delta;
                
                // Enforce Min/Max constraints
                if (nodes[i].computed_size < nodes[i].min_size) {
                    nodes[i].computed_size = nodes[i].min_size;
                } else if (nodes[i].max_size > 0 && nodes[i].computed_size > nodes[i].max_size) {
                    nodes[i].computed_size = nodes[i].max_size;
                }
            }
        }
    }
    
    // Step 4: Finalize positions by stacking the elements
    int current_pos = 0;
    for (int i = 0; i < count; i++) {
        nodes[i].computed_pos = current_pos;
        current_pos += nodes[i].computed_size + spacing;
    }
}

int main() {
    // Example: A toolbar with a fixed button, a flexible search bar, and another fixed button
    AucklandNode1D toolbar[] = {
        { .id = 1, .min_size = 50, .max_size = 50, .pref_size = 50, .weight = 0.0f },   // Back Btn (Fixed)
        { .id = 2, .min_size = 100, .max_size = 0,  .pref_size = 200, .weight = 1.0f }, // Search Bar (Flexible)
        { .id = 3, .min_size = 80, .max_size = 80, .pref_size = 80, .weight = 0.0f }    // Submit Btn (Fixed)
    };
    
    int container_width = 800; // Available screen width
    int gap = 10;              // 10px spacing between elements
    
    resolve_auckland_group(toolbar, 3, container_width, gap);
    
    printf("Container Width: %dpx\n\n", container_width);
    for (int i = 0; i < 3; i++) {
        printf("Node %d: Pos X: %dpx | Width: %dpx\n", 
               toolbar[i].id, toolbar[i].computed_pos, toolbar[i].computed_size);
    }
    
    return 0;
}
