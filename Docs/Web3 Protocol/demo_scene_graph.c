#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define MAX_NODES 1024
#define MAX_CHILDREN 16

// The structure of a retained TVG node on the client
typedef struct TVGNode {
    uint32_t id;
    uint8_t type;
    uint32_t parent_id;
    
    // Pointers to construct the hierarchical tree
    struct TVGNode* children[MAX_CHILDREN];
    int child_count;
} TVGNode;

// The global scene graph container
typedef struct {
    TVGNode* nodes[MAX_NODES]; // Fast flat lookup array
    TVGNode* root;             // Pointer to root grouping node
} SceneGraph;

SceneGraph* sg_init() {
    SceneGraph* sg = calloc(1, sizeof(SceneGraph));
    
    // Initialize the root Desktop node (ID 0)
    TVGNode* root = calloc(1, sizeof(TVGNode));
    root->id = 0;
    root->type = 0; // 0 = GROUP
    
    sg->nodes[0] = root;
    sg->root = root;
    return sg;
}

// Simulates executing a parsed SG_NODE_CREATE (0x10) command
void sg_node_create(SceneGraph* sg, uint32_t id, uint8_t type, uint32_t parent_id) {
    if (id >= MAX_NODES || sg->nodes[id] != NULL) return; // Prevent overflows/duplicates
    
    TVGNode* node = calloc(1, sizeof(TVGNode));
    node->id = id;
    node->type = type;
    node->parent_id = parent_id;
    
    // Add to flat lookup
    sg->nodes[id] = node;
    
    // Link to parent in the tree hierarchy
    if (parent_id < MAX_NODES && sg->nodes[parent_id] != NULL) {
        TVGNode* parent = sg->nodes[parent_id];
        if (parent->child_count < MAX_CHILDREN) {
            parent->children[parent->child_count++] = node;
        }
    }
}

// Recursive visualization of the tree
void sg_print_tree(TVGNode* node, int depth) {
    if (!node) return;
    
    for (int i = 0; i < depth; i++) printf("  ");
    
    const char* type_str = "UNKNOWN";
    switch(node->type) {
        case 0: type_str = "GROUP"; break;
        case 1: type_str = "RECT"; break;
        case 2: type_str = "PATH"; break;
        case 3: type_str = "TEXT"; break;
        case 7: type_str = "MEDIA_SURFACE"; break;
    }
    
    printf("└─ Node %u [%s]\n", node->id, type_str);
    
    // Recurse down to children
    for (int i = 0; i < node->child_count; i++) {
        sg_print_tree(node->children[i], depth + 1);
    }
}

int main() {
    SceneGraph* sg = sg_init();
    
    printf("Simulating TVG Command Parsing...\n\n");
    
    // Simulating: {"op": "node_create", "node": 10, "type": 0, "parent": 0}
    sg_node_create(sg, 10, 0, 0);  // Widget Group under root
    
    // Simulating: {"op": "node_create", "node": 11, "type": 1, "parent": 10}
    sg_node_create(sg, 11, 1, 10); // Background Rect inside Widget Group
    
    // Simulating: {"op": "node_create", "node": 12, "type": 3, "parent": 10}
    sg_node_create(sg, 12, 3, 10); // Text label inside Widget Group
    
    // Simulating: {"op": "node_create", "node": 50, "type": 7, "parent": 0}
    sg_node_create(sg, 50, 7, 0);  // Media Surface under root
    
    printf("--- Resulting Retained Scene Graph ---\n");
    sg_print_tree(sg->root, 0);
    
    return 0;
}