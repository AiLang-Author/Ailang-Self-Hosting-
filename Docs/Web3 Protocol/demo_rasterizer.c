#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#define MAX(a, b) (((a) > (b)) ? (a) : (b))

#define BUFFER_WIDTH 80
#define BUFFER_HEIGHT 30

void clear_buffer(uint8_t* buffer, int width, int height) {
    for (int i = 0; i < width * height; i++) {
        buffer[i] = 0; // 0 = empty pixel
    }
}

void print_buffer(uint8_t* buffer, int width, int height) {
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            printf("%c", buffer[y * width + x] ? '#' : '.');
        }
        printf("\n");
    }
}

// Simulates rendering a PATH_RRECT (0x29) command to a pixel buffer
void rasterize_rrect(uint8_t* buffer, int buf_w, int buf_h, 
                     float rect_x, float rect_y, float rect_w, float rect_h, 
                     float rx, float ry) {
    
    // Find rendering bounds (clamped to the screen/buffer)
    int start_x = (int)MAX(0.0f, rect_x);
    int start_y = (int)MAX(0.0f, rect_y);
    int end_x   = (int)MIN((float)buf_w, rect_x + rect_w);
    int end_y   = (int)MIN((float)buf_h, rect_y + rect_h);

    // Compute the inner bounding box (the part without curved corners)
    float inner_left   = rect_x + rx;
    float inner_right  = rect_x + rect_w - rx;
    float inner_top    = rect_y + ry;
    float inner_bottom = rect_y + rect_h - ry;

    for (int y = start_y; y < end_y; y++) {
        for (int x = start_x; x < end_x; x++) {
            float px = (float)x + 0.5f; // Sample at pixel center
            float py = (float)y + 0.5f;
            
            int inside = 1;
            
            // Check intersection with the 4 corner ellipses
            if (px < inner_left && py < inner_top) {
                float dx = (inner_left - px) / rx;
                float dy = (inner_top - py) / ry;
                if (dx*dx + dy*dy > 1.0f) inside = 0;
            } 
            else if (px > inner_right && py < inner_top) {
                float dx = (px - inner_right) / rx;
                float dy = (inner_top - py) / ry;
                if (dx*dx + dy*dy > 1.0f) inside = 0;
            } 
            else if (px < inner_left && py > inner_bottom) {
                float dx = (inner_left - px) / rx;
                float dy = (py - inner_bottom) / ry;
                if (dx*dx + dy*dy > 1.0f) inside = 0;
            } 
            else if (px > inner_right && py > inner_bottom) {
                float dx = (px - inner_right) / rx;
                float dy = (py - inner_bottom) / ry;
                if (dx*dx + dy*dy > 1.0f) inside = 0;
            }
            
            if (inside) {
                buffer[y * buf_w + x] = 1;
            }
        }
    }
}

int main() {
    uint8_t buffer[BUFFER_WIDTH * BUFFER_HEIGHT];
    clear_buffer(buffer, BUFFER_WIDTH, BUFFER_HEIGHT);
    printf("Rasterizing PATH_RRECT (x: 5, y: 3, w: 60, h: 20, rx: 6, ry: 6)\n\n");
    rasterize_rrect(buffer, BUFFER_WIDTH, BUFFER_HEIGHT, 5.0f, 3.0f, 60.0f, 20.0f, 6.0f, 6.0f);
    print_buffer(buffer, BUFFER_WIDTH, BUFFER_HEIGHT);
    return 0;
}