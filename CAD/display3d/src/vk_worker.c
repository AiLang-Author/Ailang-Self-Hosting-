/* vk_worker — stdin/stdout AilangVk backend for Library.VulkanClient
 *
 * Binary frames (LE):
 *   req:  magic u32='VKC1'  op u32  nbytes u32  payload[nbytes]
 *   rep:  magic u32='VKC1'  status u32  nbytes u32  payload[nbytes]
 * status 0 = ok.
 *
 * Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
 * Licensed under the Sean Collins Software License (SCSL v1.0).
 */
#include "ailang_vk.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAGIC 0x31434B56u /* 'VKC1' little-endian */
#define MAX_BUFS 16

enum {
    OP_INIT = 1,
    OP_TARGET = 2,
    OP_PIPE = 3,
    OP_BUF = 4,
    OP_UPLOAD = 5,
    OP_BEGIN = 6,
    OP_BIND = 7,
    OP_DRAW = 8,
    OP_END = 9,
    OP_READBACK = 10,
    OP_READY = 11,
    OP_INFO = 12,
    OP_QUIT = 13
};

static AilangVk_Context *g_vk;
static AilangVk_Buffer g_bufs[MAX_BUFS];
static int g_buf_used[MAX_BUFS];
static AilangVk_PipelineId g_pipe;

static int read_full(void *dst, size_t n)
{
    uint8_t *p = (uint8_t *)dst;
    size_t got = 0;
    while (got < n) {
        ssize_t r = read(0, p + got, n - got);
        if (r <= 0)
            return 0;
        got += (size_t)r;
    }
    return 1;
}

static int write_full(const void *src, size_t n)
{
    const uint8_t *p = (const uint8_t *)src;
    size_t put = 0;
    while (put < n) {
        ssize_t w = write(1, p + put, n - put);
        if (w <= 0)
            return 0;
        put += (size_t)w;
    }
    return 1;
}

static int reply(uint32_t status, const void *payload, uint32_t n)
{
    uint32_t hdr[3];
    hdr[0] = MAGIC;
    hdr[1] = status;
    hdr[2] = n;
    if (!write_full(hdr, 12))
        return 0;
    if (n && payload && !write_full(payload, n))
        return 0;
    return 1;
}

static uint32_t ru32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
    ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }

static uint64_t ru64(const uint8_t *p)
{
    return (uint64_t)ru32(p) | ((uint64_t)ru32(p + 4) << 32);
}

static void wu32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

int main(void)
{
    g_vk = AilangVk_Create();
    if (!g_vk)
        return 1;

    for (;;) {
        uint32_t hdr[3];
        if (!read_full(hdr, 12))
            break;
        if (hdr[0] != MAGIC)
            return 2;
        uint32_t op = hdr[1];
        uint32_t n = hdr[2];
        uint8_t *pay = NULL;
        if (n) {
            pay = (uint8_t *)malloc(n);
            if (!pay || !read_full(pay, n)) {
                free(pay);
                return 3;
            }
        }

        if (op == OP_QUIT) {
            reply(0, NULL, 0);
            free(pay);
            break;
        }

        int ok = 0;
        if (op == OP_INIT) {
            char name[256];
            uint32_t ln = n < 255 ? n : 255;
            memcpy(name, pay ? (void *)pay : (void *)"", ln);
            name[ln] = 0;
            ok = AilangVk_InitInstance(g_vk, name);
            reply(ok ? 0 : 1, NULL, 0);
        } else if (op == OP_TARGET) {
            if (n >= 8) {
                uint32_t w = ru32(pay), h = ru32(pay + 4);
                ok = AilangVk_CreateTarget(g_vk, w, h);
            }
            reply(ok ? 0 : 1, NULL, 0);
        } else if (op == OP_PIPE) {
            g_pipe = 0;
            ok = AilangVk_CreateDefaultMeshPipeline(g_vk, &g_pipe);
            uint8_t out[4];
            wu32(out, g_pipe);
            reply(ok ? 0 : 1, out, 4);
        } else if (op == OP_BUF) {
            int slot = -1;
            int i;
            for (i = 0; i < MAX_BUFS; i++) {
                if (!g_buf_used[i]) {
                    slot = i;
                    break;
                }
            }
            if (slot >= 0 && n >= 16) {
                uint64_t sz = ru64(pay);
                uint32_t usage = ru32(pay + 8);
                uint32_t hostv = ru32(pay + 12);
                memset(&g_bufs[slot], 0, sizeof g_bufs[slot]);
                ok = AilangVk_CreateBuffer(g_vk, sz, usage, (int)hostv, &g_bufs[slot]);
                if (ok)
                    g_buf_used[slot] = 1;
            }
            uint8_t out[4];
            wu32(out, ok ? (uint32_t)(slot + 1) : 0);
            reply(ok ? 0 : 1, out, 4);
        } else if (op == OP_UPLOAD) {
            if (n >= 4) {
                uint32_t id = ru32(pay);
                if (id >= 1 && id <= MAX_BUFS && g_buf_used[id - 1])
                    ok = AilangVk_StageUpload(g_vk, &g_bufs[id - 1], pay + 4, n - 4);
            }
            reply(ok ? 0 : 1, NULL, 0);
        } else if (op == OP_BEGIN) {
            if (n >= 3) {
                float r = (float)pay[0] / 255.0f;
                float g = (float)pay[1] / 255.0f;
                float b = (float)pay[2] / 255.0f;
                ok = AilangVk_BeginFrame(g_vk, r, g, b);
            }
            reply(ok ? 0 : 1, NULL, 0);
        } else if (op == OP_BIND) {
            if (n >= 4)
                ok = AilangVk_BindPipeline(g_vk, ru32(pay));
            reply(ok ? 0 : 1, NULL, 0);
        } else if (op == OP_DRAW) {
            if (n >= 16) {
                uint32_t vbo = ru32(pay);
                uint32_t ibo = ru32(pay + 4);
                uint32_t vc = ru32(pay + 8);
                uint32_t ic = ru32(pay + 12);
                const AilangVk_Buffer *vb = NULL;
                const AilangVk_Buffer *ib = NULL;
                if (vbo >= 1 && vbo <= MAX_BUFS && g_buf_used[vbo - 1])
                    vb = &g_bufs[vbo - 1];
                if (ibo >= 1 && ibo <= MAX_BUFS && g_buf_used[ibo - 1])
                    ib = &g_bufs[ibo - 1];
                ok = vb && AilangVk_Draw(g_vk, vb, ib, vc, ic);
            }
            reply(ok ? 0 : 1, NULL, 0);
        } else if (op == OP_END) {
            ok = AilangVk_EndFrame(g_vk);
            reply(ok ? 0 : 1, NULL, 0);
        } else if (op == OP_READBACK) {
            AilangVk_Info info;
            memset(&info, 0, sizeof info);
            AilangVk_GetInfo(g_vk, &info);
            uint32_t w = info.target_w, h = info.target_h, pitch = w * 4;
            size_t sz = (size_t)pitch * (size_t)h;
            uint8_t *fb = (uint8_t *)calloc(sz + 12, 1);
            if (fb && w && h && AilangVk_ReadbackBGRA(g_vk, fb + 12, pitch)) {
                wu32(fb, w);
                wu32(fb + 4, h);
                wu32(fb + 8, pitch);
                reply(0, fb, (uint32_t)(sz + 12));
                ok = 1;
            } else {
                reply(1, NULL, 0);
            }
            free(fb);
        } else if (op == OP_READY) {
            uint8_t out[4];
            wu32(out, AilangVk_Ready(g_vk) ? 1 : 0);
            reply(0, out, 4);
        } else if (op == OP_INFO) {
            AilangVk_Info info;
            memset(&info, 0, sizeof info);
            AilangVk_GetInfo(g_vk, &info);
            uint8_t out[8 + 256];
            memset(out, 0, sizeof out);
            wu32(out, info.device_type);
            wu32(out + 4, info.ready);
            memcpy(out + 8, info.device_name, 256);
            reply(0, out, 8 + 256);
        } else {
            reply(2, NULL, 0);
        }
        free(pay);
    }

    {
        int i;
        for (i = 0; i < MAX_BUFS; i++) {
            if (g_buf_used[i])
                AilangVk_DestroyBuffer(g_vk, &g_bufs[i]);
        }
    }
    AilangVk_Destroy(g_vk);
    return 0;
}
