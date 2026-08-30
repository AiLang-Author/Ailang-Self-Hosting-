/* test_display3d.c — gate for AilangVk instance/staging/pipeline + Display3D
 *
 * Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
 * Licensed under the Sean Collins Software License (SCSL v1.0).
 */
#include "ailang_display3d.h"
#include "ailang_vk.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void add_quad(Display3D_Vertex *v, uint32_t *idx, uint32_t *nv, uint32_t *ni,
                     float ax, float ay, float az,
                     float bx, float by, float bz,
                     float cx, float cy, float cz,
                     float dx, float dy, float dz,
                     float nx, float ny, float nz)
{
    uint32_t b = *nv;
    Display3D_Vertex q[4];
    memset(q, 0, sizeof q);
    q[0].position[0] = ax; q[0].position[1] = ay; q[0].position[2] = az;
    q[1].position[0] = bx; q[1].position[1] = by; q[1].position[2] = bz;
    q[2].position[0] = cx; q[2].position[1] = cy; q[2].position[2] = cz;
    q[3].position[0] = dx; q[3].position[1] = dy; q[3].position[2] = dz;
    for (int i = 0; i < 4; i++) {
        q[i].normal[0] = nx; q[i].normal[1] = ny; q[i].normal[2] = nz;
        q[i].color = 0;
        v[b + i] = q[i];
    }
    idx[*ni + 0] = b + 0; idx[*ni + 1] = b + 1; idx[*ni + 2] = b + 2;
    idx[*ni + 3] = b + 0; idx[*ni + 4] = b + 2; idx[*ni + 5] = b + 3;
    *nv += 4;
    *ni += 6;
}

static int write_bmp(const char *path, const uint8_t *bgra, int w, int h, int pitch)
{
    int rowb = w * 3;
    int pad = (4 - (rowb & 3)) & 3;
    int img = (rowb + pad) * h;
    int sz = 54 + img;
    uint8_t hdr[54];
    memset(hdr, 0, 54);
    hdr[0] = 'B'; hdr[1] = 'M';
    hdr[2] = (uint8_t)sz; hdr[3] = (uint8_t)(sz >> 8);
    hdr[4] = (uint8_t)(sz >> 16); hdr[5] = (uint8_t)(sz >> 24);
    hdr[10] = 54;
    hdr[14] = 40;
    hdr[18] = (uint8_t)w; hdr[19] = (uint8_t)(w >> 8);
    hdr[22] = (uint8_t)h; hdr[23] = (uint8_t)(h >> 8);
    hdr[26] = 1; hdr[28] = 24;
    FILE *f = fopen(path, "wb");
    if (!f)
        return 0;
    fwrite(hdr, 1, 54, f);
    uint8_t *row = (uint8_t *)calloc((size_t)rowb + (size_t)pad, 1);
    if (!row) {
        fclose(f);
        return 0;
    }
    for (int y = h - 1; y >= 0; y--) {
        const uint8_t *s = bgra + (size_t)y * (size_t)pitch;
        for (int x = 0; x < w; x++) {
            row[x * 3 + 0] = s[x * 4 + 0];
            row[x * 3 + 1] = s[x * 4 + 1];
            row[x * 3 + 2] = s[x * 4 + 2];
        }
        fwrite(row, 1, (size_t)rowb + (size_t)pad, f);
    }
    free(row);
    fclose(f);
    return 1;
}

int main(void)
{
    int failed = 0;
    AilangVk_Context *vk = AilangVk_Create();
    if (!vk) {
        fprintf(stderr, "[FAIL] AilangVk_Create\n");
        return 1;
    }
    int vk_ok = AilangVk_InitInstance(vk, "AilangVk gate");
    if (vk_ok) {
        AilangVk_Info info;
        AilangVk_GetInfo(vk, &info);
        fprintf(stderr, "[PASS] instance+device: %s type=%u\n",
                info.device_name, info.device_type);
        if (!AilangVk_CreateTarget(vk, 64, 64)) {
            fprintf(stderr, "[FAIL] CreateTarget\n");
            failed++;
        } else {
            fprintf(stderr, "[PASS] offscreen target 64x64\n");
        }
        /* staging: upload 256 bytes through a DEVICE_LOCAL vertex buffer */
        uint8_t src[256];
        for (int i = 0; i < 256; i++)
            src[i] = (uint8_t)i;
        AilangVk_Buffer buf;
        memset(&buf, 0, sizeof buf);
        if (!AilangVk_CreateBuffer(vk, 256, AILANG_VK_BUF_VERTEX, 0, &buf) ||
            !AilangVk_StageUpload(vk, &buf, src, 256)) {
            fprintf(stderr, "[FAIL] buffer staging\n");
            failed++;
        } else {
            fprintf(stderr, "[PASS] vertex buffer staged 256 bytes\n");
        }
        AilangVk_DestroyBuffer(vk, &buf);

        AilangVk_PipelineId pipe = 0;
        if (!AilangVk_CreateDefaultMeshPipeline(vk, &pipe) || pipe == 0) {
            fprintf(stderr, "[FAIL] default mesh pipeline\n");
            failed++;
        } else {
            fprintf(stderr, "[PASS] default mesh pipeline id=%u\n", pipe);
        }
    } else {
        fprintf(stderr, "[PASS] Vulkan unavailable — resource still constructible\n");
    }
    AilangVk_Destroy(vk);

    const int W = 320, H = 240;
    Display3D_Context *ctx = Display3D_Create((uint32_t)W, (uint32_t)H, 1);
    if (!ctx) {
        fprintf(stderr, "[FAIL] Display3D_Create\n");
        return 1;
    }

    Display3D_Vertex verts[24];
    uint32_t idx[36];
    uint32_t nv = 0, ni = 0;
    const float a = -12.0f, b = 12.0f;
    add_quad(verts, idx, &nv, &ni, a,a,b, b,a,b, b,b,b, a,b,b,  0,0,1);
    add_quad(verts, idx, &nv, &ni, b,a,a, a,a,a, a,b,a, b,b,a,  0,0,-1);
    add_quad(verts, idx, &nv, &ni, a,a,a, b,a,a, b,a,b, a,a,b,  0,-1,0);
    add_quad(verts, idx, &nv, &ni, a,b,b, b,b,b, b,b,a, a,b,a,  0,1,0);
    add_quad(verts, idx, &nv, &ni, b,a,b, b,a,a, b,b,a, b,b,b,  1,0,0);
    add_quad(verts, idx, &nv, &ni, a,a,a, a,a,b, a,b,b, a,b,a, -1,0,0);

    Display3D_Mesh mesh;
    memset(&mesh, 0, sizeof mesh);
    mesh.mesh_id = 1;
    mesh.vertices = verts;
    mesh.vertex_count = nv;
    mesh.indices = idx;
    mesh.index_count = ni;
    if (!Display3D_UploadMesh(ctx, &mesh)) {
        fprintf(stderr, "[FAIL] UploadMesh\n");
        failed++;
    } else {
        fprintf(stderr, "[PASS] UploadMesh %u verts %u idx\n", nv, ni);
    }

    uint32_t pitch = (uint32_t)W * 4u;
    uint8_t *fb = (uint8_t *)calloc((size_t)pitch * (size_t)H, 1);
    if (!fb) {
        Display3D_Destroy(ctx);
        return 1;
    }
    Display3D_RenderFrame(ctx, fb, pitch);

    int lit = 0;
    for (int i = 0; i < W * H; i++) {
        uint8_t bch = fb[i * 4 + 0], g = fb[i * 4 + 1], r = fb[i * 4 + 2];
        if (r > 40 || g > 45 || bch > 55)
            lit++;
    }
    fprintf(stderr, "[info] shaded pixels=%d / %d\n", lit, W * H);
    if (lit < 200) {
        fprintf(stderr, "[FAIL] frame is empty (no shaded geometry)\n");
        failed++;
    } else {
        fprintf(stderr, "[PASS] shaded geometry present\n");
    }
    write_bmp("tests/display3d_cube.bmp", fb, W, H, (int)pitch);
    fprintf(stderr, "[info] wrote tests/display3d_cube.bmp\n");
    free(fb);
    Display3D_Destroy(ctx);

    Display3D_Context *cpu = Display3D_Create((uint32_t)W, (uint32_t)H, 0);
    if (!cpu) {
        fprintf(stderr, "[FAIL] Display3D_Create SSE2\n");
        failed++;
    } else {
        if (!Display3D_UploadMesh(cpu, &mesh)) {
            fprintf(stderr, "[FAIL] SSE2 UploadMesh\n");
            failed++;
        }
        fb = (uint8_t *)calloc((size_t)pitch * (size_t)H, 1);
        Display3D_RenderFrame(cpu, fb, pitch);
        lit = 0;
        for (int i = 0; i < W * H; i++) {
            uint8_t bch = fb[i * 4 + 0], g = fb[i * 4 + 1], r = fb[i * 4 + 2];
            if (r > 40 || g > 45 || bch > 55)
                lit++;
        }
        if (lit < 200) {
            fprintf(stderr, "[FAIL] SSE2 frame empty (%d)\n", lit);
            failed++;
        } else {
            fprintf(stderr, "[PASS] SSE2 rasterizer (%d shaded)\n", lit);
        }
        write_bmp("tests/display3d_cube_sse2.bmp", fb, W, H, (int)pitch);
        free(fb);
        Display3D_Destroy(cpu);
    }

    if (failed) {
        fprintf(stderr, "DISPLAY3D FAILED (%d)\n", failed);
        return 1;
    }
    fprintf(stderr, "DISPLAY3D PASSED\n");
    return 0;
}
