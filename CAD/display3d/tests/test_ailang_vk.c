/* test_ailang_vk.c — basic AilangVk wheels. No CAD, no B-Rep.
 *
 * Gates: create, init, info, target, clear, staging, pipeline, NDC draw,
 *        resize, multi-frame, destroy. Works on lavapipe or a real GPU.
 *
 * Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
 * Licensed under the Sean Collins Software License (SCSL v1.0).
 */
#include "ailang_vk.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_fail;

static void pass(const char *s) { fprintf(stderr, "[PASS] %s\n", s); }
static void fail(const char *s)
{
    fprintf(stderr, "[FAIL] %s\n", s);
    g_fail++;
}

static int px_rgb(const uint8_t *fb, uint32_t pitch, int x, int y,
                  int *r, int *g, int *b)
{
    const uint8_t *p = fb + (size_t)y * pitch + (size_t)x * 4u;
    *b = p[0];
    *g = p[1];
    *r = p[2];
    return p[3];
}

static int near_rgb(int r, int g, int b, int er, int eg, int eb, int slop)
{
    return abs(r - er) <= slop && abs(g - eg) <= slop && abs(b - eb) <= slop;
}

/* Display3D_Vertex layout: pos3 nrm3 uv2 rgba8 = 36 bytes. */
typedef struct MeshVert {
    float pos[3];
    float nrm[3];
    float uv[2];
    uint32_t color;
} MeshVert;

static uint32_t rgba(uint8_t r, uint8_t g, uint8_t b, uint8_t a)
{
    return (uint32_t)r | ((uint32_t)g << 8) | ((uint32_t)b << 16) | ((uint32_t)a << 24);
}

static int write_bmp(const char *path, const uint8_t *bgra, int w, int h, int pitch)
{
    int rowb = w * 3;
    int pad = (4 - (rowb & 3)) & 3;
    int img = (rowb + pad) * h;
    int sz = 54 + img;
    uint8_t hdr[54];
    FILE *f;
    uint8_t *row;
    int y, x;
    memset(hdr, 0, 54);
    hdr[0] = 'B'; hdr[1] = 'M';
    hdr[2] = (uint8_t)sz; hdr[3] = (uint8_t)(sz >> 8);
    hdr[4] = (uint8_t)(sz >> 16); hdr[5] = (uint8_t)(sz >> 24);
    hdr[10] = 54; hdr[14] = 40;
    hdr[18] = (uint8_t)w; hdr[19] = (uint8_t)(w >> 8);
    hdr[22] = (uint8_t)h; hdr[23] = (uint8_t)(h >> 8);
    hdr[26] = 1; hdr[28] = 24;
    f = fopen(path, "wb");
    if (!f)
        return 0;
    fwrite(hdr, 1, 54, f);
    row = (uint8_t *)calloc((size_t)rowb + (size_t)pad, 1);
    if (!row) {
        fclose(f);
        return 0;
    }
    for (y = h - 1; y >= 0; y--) {
        const uint8_t *s = bgra + (size_t)y * (size_t)pitch;
        for (x = 0; x < w; x++) {
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
    AilangVk_Context *vk;
    AilangVk_Info info;
    AilangVk_Buffer buf, vbo;
    AilangVk_PipelineId pipe = 0;
    uint8_t *fb;
    uint32_t pitch;
    int r, g, b;
    uint8_t pattern[256];
    MeshVert tri[3];
    int i;

    memset(&buf, 0, sizeof buf);
    memset(&vbo, 0, sizeof vbo);

    /* --- invalid args --- */
    if (AilangVk_InitInstance(NULL, "x") != 0)
        fail("InitInstance(NULL) should fail");
    else
        pass("InitInstance(NULL) rejected");
    AilangVk_Destroy(NULL);
    pass("Destroy(NULL) is a no-op");

    vk = AilangVk_Create();
    if (!vk) {
        fail("AilangVk_Create");
        return 1;
    }
    if (AilangVk_Ready(vk))
        fail("Ready before Init");
    else
        pass("not ready before Init");

    if (!AilangVk_CreateTarget(vk, 64, 64))
        pass("CreateTarget before Init rejected");
    else
        fail("CreateTarget before Init should fail");

    if (!AilangVk_InitInstance(vk, "AilangVk basic gate")) {
        fail("InitInstance (need libvulkan + an ICD, lavapipe is enough)");
        AilangVk_Destroy(vk);
        return 1;
    }
    pass("InitInstance");

    if (!AilangVk_Ready(vk))
        fail("Ready after Init");
    else
        pass("Ready after Init");

    memset(&info, 0, sizeof info);
    AilangVk_GetInfo(vk, &info);
    if (!info.ready || info.device_name[0] == 0)
        fail("GetInfo empty");
    else {
        fprintf(stderr, "[info] device='%s' type=%u vendor=0x%x id=0x%x qfam=%u\n",
                info.device_name, info.device_type, info.vendor_id,
                info.device_id, info.graphics_queue_family);
        pass("GetInfo");
    }

    /* second init is idempotent */
    if (!AilangVk_InitInstance(vk, "again"))
        fail("InitInstance idempotent");
    else
        pass("InitInstance idempotent");

    if (!AilangVk_CreateTarget(vk, 0, 0))
        pass("CreateTarget(0,0) rejected");
    else
        fail("CreateTarget(0,0) should fail");

    if (!AilangVk_CreateTarget(vk, 64, 48))
        fail("CreateTarget 64x48");
    else
        pass("CreateTarget 64x48");

    pitch = 64 * 4;
    fb = (uint8_t *)calloc((size_t)pitch * 48, 1);
    if (!fb) {
        AilangVk_Destroy(vk);
        return 1;
    }

    /* clear-only frame — no pipeline. magenta-ish. */
    if (!AilangVk_BeginFrame(vk, 1.0f, 0.0f, 0.5f))
        fail("BeginFrame clear");
    else if (!AilangVk_EndFrame(vk))
        fail("EndFrame clear");
    else if (!AilangVk_ReadbackBGRA(vk, fb, pitch))
        fail("Readback clear");
    else {
        px_rgb(fb, pitch, 8, 8, &r, &g, &b);
        fprintf(stderr, "[info] clear pixel (8,8) = %d,%d,%d\n", r, g, b);
        if (near_rgb(r, g, b, 255, 0, 128, 8))
            pass("clear color readback (red/magenta)");
        else
            fail("clear color mismatch");
    }

    /* host-visible staging round-trip */
    for (i = 0; i < 256; i++)
        pattern[i] = (uint8_t)(255 - i);
    if (!AilangVk_CreateBuffer(vk, 256, AILANG_VK_BUF_STAGING, 1, &buf) || !buf.mapped)
        fail("CreateBuffer host-visible");
    else if (!AilangVk_StageUpload(vk, &buf, pattern, 256))
        fail("StageUpload host-visible");
    else if (memcmp(buf.mapped, pattern, 256) != 0)
        fail("host-visible map contents");
    else
        pass("host-visible buffer round-trip");

    if (AilangVk_StageUpload(vk, &buf, pattern, 512))
        fail("StageUpload overflow should fail");
    else
        pass("StageUpload overflow rejected");
    AilangVk_DestroyBuffer(vk, &buf);

    /* device-local vertex buffer via staging copy */
    if (!AilangVk_CreateBuffer(vk, 256, AILANG_VK_BUF_VERTEX, 0, &buf))
        fail("CreateBuffer device-local");
    else if (!AilangVk_StageUpload(vk, &buf, pattern, 256))
        fail("StageUpload device-local");
    else
        pass("device-local vertex staging");
    AilangVk_DestroyBuffer(vk, &buf);

    /* pipeline + NDC triangle (pass-through default mesh shader) */
    if (!AilangVk_CreateDefaultMeshPipeline(vk, &pipe) || pipe == 0)
        fail("CreateDefaultMeshPipeline");
    else
        pass("CreateDefaultMeshPipeline");

    memset(tri, 0, sizeof tri);
    /* covering the centre of NDC */
    tri[0].pos[0] = -0.9f; tri[0].pos[1] = -0.9f; tri[0].pos[2] = 0.0f;
    tri[1].pos[0] =  0.9f; tri[1].pos[1] = -0.9f; tri[1].pos[2] = 0.0f;
    tri[2].pos[0] =  0.0f; tri[2].pos[1] =  0.9f; tri[2].pos[2] = 0.0f;
    tri[0].nrm[2] = tri[1].nrm[2] = tri[2].nrm[2] = 1.0f;
    tri[0].color = tri[1].color = tri[2].color = rgba(240, 32, 16, 255);

    if (!AilangVk_CreateBuffer(vk, sizeof tri, AILANG_VK_BUF_VERTEX, 1, &vbo) ||
        !AilangVk_StageUpload(vk, &vbo, tri, sizeof tri))
        fail("triangle VBO");
    else
        pass("triangle VBO staged");

    if (!AilangVk_BeginFrame(vk, 0.05f, 0.05f, 0.08f) ||
        !AilangVk_BindPipeline(vk, pipe) ||
        !AilangVk_Draw(vk, &vbo, NULL, 3, 0) ||
        !AilangVk_EndFrame(vk) ||
        !AilangVk_ReadbackBGRA(vk, fb, pitch))
        fail("NDC triangle draw");
    else {
        int cx = 32, cy = 24;
        px_rgb(fb, pitch, cx, cy, &r, &g, &b);
        fprintf(stderr, "[info] center pixel (%d,%d) = %d,%d,%d\n", cx, cy, r, g, b);
        if (r > 180 && g < 80 && b < 80)
            pass("NDC triangle centre is red");
        else
            fail("NDC triangle centre not red");
        /* corner should stay near clear colour */
        px_rgb(fb, pitch, 0, 0, &r, &g, &b);
        fprintf(stderr, "[info] corner pixel (0,0) = %d,%d,%d\n", r, g, b);
        if (r < 40 && g < 40 && b < 40)
            pass("NDC triangle leaves corner as clear");
        else
            fail("corner was painted (scissor/draw overflow?)");
    }

    /* second frame, same cmd path */
    if (!AilangVk_BeginFrame(vk, 0.0f, 0.0f, 0.0f) ||
        !AilangVk_BindPipeline(vk, pipe) ||
        !AilangVk_Draw(vk, &vbo, NULL, 3, 0) ||
        !AilangVk_EndFrame(vk) ||
        !AilangVk_ReadbackBGRA(vk, fb, pitch))
        fail("second frame");
    else {
        px_rgb(fb, pitch, 32, 24, &r, &g, &b);
        if (r > 180)
            pass("second frame still red at centre");
        else
            fail("second frame lost the triangle");
    }

    /* resize target, recreate pipeline (render pass changed) */
    AilangVk_DestroyBuffer(vk, &vbo);
    if (!AilangVk_CreateTarget(vk, 128, 96))
        fail("resize target 128x96");
    else
        pass("resize target 128x96");

    pipe = 0;
    if (!AilangVk_CreateDefaultMeshPipeline(vk, &pipe))
        fail("pipeline after resize");
    else
        pass("pipeline after resize");

    if (!AilangVk_CreateBuffer(vk, sizeof tri, AILANG_VK_BUF_VERTEX, 1, &vbo) ||
        !AilangVk_StageUpload(vk, &vbo, tri, sizeof tri))
        fail("VBO after resize");
    else {
        uint8_t *fb2 = (uint8_t *)calloc(128 * 4 * 96, 1);
        if (fb2 &&
            AilangVk_BeginFrame(vk, 0.0f, 0.0f, 0.0f) &&
            AilangVk_BindPipeline(vk, pipe) &&
            AilangVk_Draw(vk, &vbo, NULL, 3, 0) &&
            AilangVk_EndFrame(vk) &&
            AilangVk_ReadbackBGRA(vk, fb2, 128 * 4)) {
            px_rgb(fb2, 128 * 4, 64, 48, &r, &g, &b);
            fprintf(stderr, "[info] resized centre = %d,%d,%d\n", r, g, b);
            if (r > 180)
                pass("draw after resize");
            else
                fail("draw after resize not red");
        } else {
            fail("draw after resize");
        }
        free(fb2);
    }

    /* bind garbage pipeline id */
    if (AilangVk_BeginFrame(vk, 0, 0, 0)) {
        if (AilangVk_BindPipeline(vk, 99))
            fail("BindPipeline(99) should fail");
        else
            pass("BindPipeline(99) rejected");
        AilangVk_EndFrame(vk);
    }

    /* indexed draw + a few frames (command-buffer reset) */
    {
        uint32_t idx[3] = { 0, 1, 2 };
        AilangVk_Buffer ibo;
        int f;
        memset(&ibo, 0, sizeof ibo);
        if (!AilangVk_CreateBuffer(vk, sizeof idx, AILANG_VK_BUF_INDEX, 1, &ibo) ||
            !AilangVk_StageUpload(vk, &ibo, idx, sizeof idx))
            fail("index buffer");
        else
            pass("index buffer staged");
        for (f = 0; f < 32; f++) {
            if (!AilangVk_BeginFrame(vk, 0.0f, 0.0f, 0.0f) ||
                !AilangVk_BindPipeline(vk, pipe) ||
                !AilangVk_Draw(vk, &vbo, &ibo, 3, 3) ||
                !AilangVk_EndFrame(vk)) {
                fail("indexed multi-frame");
                break;
            }
        }
        if (f == 32) {
            uint8_t *fb3 = (uint8_t *)calloc(128 * 4 * 96, 1);
            if (fb3 && AilangVk_ReadbackBGRA(vk, fb3, 128 * 4)) {
                px_rgb(fb3, 128 * 4, 64, 48, &r, &g, &b);
                if (r > 180)
                    pass("32 indexed frames");
                else
                    fail("indexed frames lost colour");
            } else {
                fail("indexed readback");
            }
            free(fb3);
        }
        AilangVk_DestroyBuffer(vk, &ibo);
    }

    /* look-at shot: 640x480 NDC triangle */
    AilangVk_DestroyBuffer(vk, &vbo);
    if (AilangVk_CreateTarget(vk, 640, 480) &&
        AilangVk_CreateDefaultMeshPipeline(vk, &pipe) &&
        AilangVk_CreateBuffer(vk, sizeof tri, AILANG_VK_BUF_VERTEX, 1, &vbo) &&
        AilangVk_StageUpload(vk, &vbo, tri, sizeof tri)) {
        uint8_t *shot = (uint8_t *)calloc(640 * 4 * 480, 1);
        if (shot &&
            AilangVk_BeginFrame(vk, 0.08f, 0.09f, 0.12f) &&
            AilangVk_BindPipeline(vk, pipe) &&
            AilangVk_Draw(vk, &vbo, NULL, 3, 0) &&
            AilangVk_EndFrame(vk) &&
            AilangVk_ReadbackBGRA(vk, shot, 640 * 4) &&
            write_bmp("tests/ailang_vk_triangle.bmp", shot, 640, 480, 640 * 4))
            pass("wrote tests/ailang_vk_triangle.bmp");
        else
            fail("gallery triangle bmp");
        free(shot);
    } else {
        fail("gallery triangle setup");
    }

    AilangVk_DestroyBuffer(vk, &vbo);
    free(fb);
    AilangVk_Destroy(vk);
    pass("Destroy after full session");

    /* fresh context after destroy */
    vk = AilangVk_Create();
    if (!vk || !AilangVk_InitInstance(vk, "second life"))
        fail("recreate context");
    else
        pass("recreate context");
    AilangVk_Destroy(vk);

    if (g_fail) {
        fprintf(stderr, "AILANG_VK FAILED (%d)\n", g_fail);
        return 1;
    }
    fprintf(stderr, "AILANG_VK PASSED\n");
    return 0;
}
