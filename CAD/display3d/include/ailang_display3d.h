/* ailang_display3d.h — 3D viewport consumer of the orthogonal AilangVk resource
 *
 * C ABI for mesh streaming, camera, and BGRA frame output.
 * Used by CAD, compiler debug views, and any Display client that needs a
 * shaded 3D viewport. GPU work lives in ailang_vk.h — this header does not
 * own VkInstance / pipelines.
 *
 * Pixel contract matches CAD_View / cad_host_x11: BGRA8, pitch bytes/row.
 *
 * Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
 * Licensed under the Sean Collins Software License (SCSL v1.0).
 */
#ifndef AILANG_DISPLAY3D_H
#define AILANG_DISPLAY3D_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 3D Vertex representation for B-Rep CAD geometry */
typedef struct Display3D_Vertex {
    float position[3]; // x, y, z
    float normal[3];   // nx, ny, nz
    float uv[2];       // u, v
    uint32_t color;    // RGBA
} Display3D_Vertex;

/* Mesh handle for B-Rep triangulated solids */
typedef struct Display3D_Mesh {
    uint32_t mesh_id;
    Display3D_Vertex *vertices;
    uint32_t vertex_count;
    uint32_t *indices;
    uint32_t index_count;
} Display3D_Mesh;

/* Camera viewport state */
typedef struct Display3D_Camera {
    float target[3];
    float distance;
    float yaw;
    float pitch;
    float fov;
} Display3D_Camera;

/* Display engine context handle */
typedef struct Display3D_Context Display3D_Context;

/* Core API Functions */
Display3D_Context* Display3D_Create(uint32_t width, uint32_t height, int use_vulkan);
void Display3D_Destroy(Display3D_Context *ctx);

int Display3D_InitVulkan(Display3D_Context *ctx);
void Display3D_UpdateCamera(Display3D_Context *ctx, const Display3D_Camera *cam);
int Display3D_UploadMesh(Display3D_Context *ctx, const Display3D_Mesh *mesh);
void Display3D_RenderFrame(Display3D_Context *ctx, uint8_t *frame_buffer, uint32_t pitch);

#ifdef __cplusplus
}
#endif

#endif /* AILANG_DISPLAY3D_H */
