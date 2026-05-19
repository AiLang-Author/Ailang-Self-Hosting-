#include <stdio.h>
#include <stdint.h>
#include <string.h>

typedef struct TvgBuilder TvgBuilder;

// The Fluent API struct
struct TvgBuilder {
    uint8_t* buffer;
    size_t length;
    size_t capacity;
    
    TvgBuilder* (*text)(TvgBuilder* self, uint32_t node_id, const char* content);
    TvgBuilder* (*style_fill)(TvgBuilder* self, uint32_t node_id, uint32_t rgba);
    TvgBuilder* (*visible)(TvgBuilder* self, uint32_t node_id, uint8_t is_visible);
};

// --- Implementation Details ---

void write_varuint(TvgBuilder* b, uint32_t value) {
    while (value >= 0x80) {
        b->buffer[b->length++] = (value & 0x7F) | 0x80;
        value >>= 7;
    }
    b->buffer[b->length++] = value & 0x7F;
}

TvgBuilder* tvg_text(TvgBuilder* self, uint32_t node_id, const char* content) {
    self->buffer[self->length++] = 0x30; // TEXT_SET
    write_varuint(self, node_id);
    
    uint32_t len = strlen(content);
    write_varuint(self, len);
    memcpy(&self->buffer[self->length], content, len);
    self->length += len;
    return self;
}

TvgBuilder* tvg_style_fill(TvgBuilder* self, uint32_t node_id, uint32_t rgba) {
    self->buffer[self->length++] = 0x16; // SG_STYLE
    write_varuint(self, node_id);
    self->buffer[self->length++] = 0x01; // Flag: FILL
    
    self->buffer[self->length++] = (rgba >> 24) & 0xFF; // R
    self->buffer[self->length++] = (rgba >> 16) & 0xFF; // G
    self->buffer[self->length++] = (rgba >> 8) & 0xFF;  // B
    self->buffer[self->length++] = rgba & 0xFF;         // A
    return self;
}

TvgBuilder* tvg_visible(TvgBuilder* self, uint32_t node_id, uint8_t is_visible) {
    self->buffer[self->length++] = 0x14; // SG_VISIBLE
    write_varuint(self, node_id);
    self->buffer[self->length++] = is_visible ? 1 : 0;
    return self;
}

// Constructor
void tvg_init(TvgBuilder* b, uint8_t* buffer, size_t capacity) {
    b->buffer = buffer;
    b->length = 0;
    b->capacity = capacity;
    
    b->text = tvg_text;
    b->style_fill = tvg_style_fill;
    b->visible = tvg_visible;
}

// --- Demonstration ---

int main() {
    printf("--- Web 3.0 Server: C Fluent TVG Builder ---\n\n");
    
    uint8_t payload[256];
    TvgBuilder tvg;
    tvg_init(&tvg, payload, sizeof(payload));
    
    // Look how ergonomic this is in pure C! 
    // It perfectly mimics the Rust chaining API.
    tvg.text(&tvg, 10, "Task Saved!")
       ->style_fill(&tvg, 10, 0x00FF00FF)
       ->visible(&tvg, 10, 1);
       
    printf("Generated %zu bytes of binary TVG commands.\nHex Dump: ", tvg.length);
    for (size_t i = 0; i < tvg.length; i++) {
        printf("%02X ", payload[i]);
    }
    printf("\n\n");
    
    return 0;
}