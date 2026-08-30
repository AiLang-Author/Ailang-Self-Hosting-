/* display3d_vulkan.cpp — Display3D viewport over AilangVk + SSE2 fallback
 *
 * This is a *consumer* of the orthogonal Vulkan resource. CAD, the
 * compiler debugger, and any other 3D view can use the same mesh/camera
 * contract. Kernel B-Rep stays in AILang; we only take already-tessellated
 * vertices.
 *
 * Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
 * Licensed under the Sean Collins Software License (SCSL v1.0).
 */
#include "ailang_display3d.h"
#include "ailang_vk.h"

#include <emmintrin.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define D3D_MAX_MESHES 32
#define D3D_BG_R 28
#define D3D_BG_G 32
#define D3D_BG_B 40
#define D3D_TEAL 0xFFD29646u /* memory RGBA8: 70,150,210,255 */

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

struct D3D_Mesh {
    uint32_t id;
    uint32_t vertex_count;
    uint32_t index_count;
    Display3D_Vertex *verts;
    uint32_t *indices;
    AilangVk_Buffer vbo;
    AilangVk_Buffer ibo;
    int gpu_ready;
};

struct Display3D_Context {
    uint32_t width;
    uint32_t height;
    int want_vulkan;
    int vulkan_enabled;
    Display3D_Camera camera;
    D3D_Mesh meshes[D3D_MAX_MESHES];
    uint32_t mesh_count;
    AilangVk_Context *vk;
    AilangVk_PipelineId pipe;
    float *zbuf;
};

static void mat_ident(float m[16])
{
    memset(m, 0, 16 * sizeof(float));
    m[0] = m[5] = m[10] = m[15] = 1.0f;
}

static void mat_mul(float o[16], const float a[16], const float b[16])
{
    float t[16];
    for (int c = 0; c < 4; c++) {
        for (int r = 0; r < 4; r++) {
            t[c * 4 + r] =
                a[0 * 4 + r] * b[c * 4 + 0] +
                a[1 * 4 + r] * b[c * 4 + 1] +
                a[2 * 4 + r] * b[c * 4 + 2] +
                a[3 * 4 + r] * b[c * 4 + 3];
        }
    }
    memcpy(o, t, sizeof t);
}

static void vec3_norm(float v[3])
{
    float L = sqrtf(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    if (L < 1e-12f)
        return;
    v[0] /= L;
    v[1] /= L;
    v[2] /= L;
}

static void vec3_cross(float o[3], const float a[3], const float b[3])
{
    o[0] = a[1] * b[2] - a[2] * b[1];
    o[1] = a[2] * b[0] - a[0] * b[2];
    o[2] = a[0] * b[1] - a[1] * b[0];
}

/* Z-up orbit, matching CAD_View: yaw about Z, pitch elevation (degrees). */
static void orbit_basis(const Display3D_Camera *cam, float eye[3], float right[3], float up[3], float fwd[3])
{
    float yaw = cam->yaw * (float)M_PI / 180.0f;
    float pitch = cam->pitch * (float)M_PI / 180.0f;
    float cp = cosf(pitch), sp = sinf(pitch);
    float cy = cosf(yaw), sy = sinf(yaw);
    /* camera direction from target toward camera (CAD_View cdx,cdy,cdz) */
    fwd[0] = cp * sy;
    fwd[1] = cp * cy;
    fwd[2] = sp;
    eye[0] = cam->target[0] + cam->distance * fwd[0];
    eye[1] = cam->target[1] + cam->distance * fwd[1];
    eye[2] = cam->target[2] + cam->distance * fwd[2];
    /* right = normalize(worldZ × fwd) = (-fwd.y, fwd.x, 0) */
    right[0] = -fwd[1];
    right[1] = fwd[0];
    right[2] = 0.0f;
    float rl = sqrtf(right[0] * right[0] + right[1] * right[1]);
    if (rl < 1e-6f) {
        right[0] = 1.0f;
        right[1] = 0.0f;
        right[2] = 0.0f;
    } else {
        right[0] /= rl;
        right[1] /= rl;
    }
    vec3_cross(up, fwd, right);
    vec3_norm(up);
}

static void mat_look(float m[16], const float eye[3], const float target[3], const float up_in[3])
{
    float f[3] = { target[0] - eye[0], target[1] - eye[1], target[2] - eye[2] };
    vec3_norm(f);
    float up[3] = { up_in[0], up_in[1], up_in[2] };
    vec3_norm(up);
    float s[3];
    vec3_cross(s, f, up);
    vec3_norm(s);
    float u[3];
    vec3_cross(u, s, f);
    mat_ident(m);
    m[0] = s[0]; m[4] = s[1]; m[8]  = s[2];
    m[1] = u[0]; m[5] = u[1]; m[9]  = u[2];
    m[2] = -f[0]; m[6] = -f[1]; m[10] = -f[2];
    m[12] = -(s[0] * eye[0] + s[1] * eye[1] + s[2] * eye[2]);
    m[13] = -(u[0] * eye[0] + u[1] * eye[1] + u[2] * eye[2]);
    m[14] = f[0] * eye[0] + f[1] * eye[1] + f[2] * eye[2];
}

/* Perspective, Vulkan-friendly with Y flip so CAD Y-up lands correctly. */
static void mat_persp(float m[16], float fov_deg, float aspect, float zn, float zf)
{
    float f = 1.0f / tanf(fov_deg * 0.5f * (float)M_PI / 180.0f);
    memset(m, 0, 16 * sizeof(float));
    m[0] = f / (aspect > 1e-6f ? aspect : 1.0f);
    m[5] = -f; /* Y flip */
    m[10] = zf / (zn - zf);
    m[11] = -1.0f;
    m[14] = (zf * zn) / (zn - zf);
}

static void build_mvp(const Display3D_Context *ctx, AilangVk_MeshUBO *ubo)
{
    float eye[3], right[3], up[3], fwd[3];
    orbit_basis(&ctx->camera, eye, right, up, fwd);
    float view[16], proj[16];
    mat_look(view, eye, ctx->camera.target, up);
    float aspect = (ctx->height > 0) ? ((float)ctx->width / (float)ctx->height) : 1.0f;
    float fov = ctx->camera.fov > 1.0f ? ctx->camera.fov : 45.0f;
    float zn = ctx->camera.distance * 0.02f;
    if (zn < 0.01f)
        zn = 0.01f;
    float zf = ctx->camera.distance * 20.0f;
    if (zf < zn + 1.0f)
        zf = zn + 1.0f;
    mat_persp(proj, fov, aspect, zn, zf);
    mat_mul(ubo->mvp, proj, view);
    /* CAD_View light: normalize(1,1,1) */
    ubo->light[0] = 0.57735027f;
    ubo->light[1] = 0.57735027f;
    ubo->light[2] = 0.57735027f;
    ubo->light[3] = 0.0f;
}

static void pack_bgra(uint8_t *p, int r, int g, int b)
{
    if (r < 0) r = 0;
    if (r > 255) r = 255;
    if (g < 0) g = 0;
    if (g > 255) g = 255;
    if (b < 0) b = 0;
    if (b > 255) b = 255;
    p[0] = (uint8_t)b;
    p[1] = (uint8_t)g;
    p[2] = (uint8_t)r;
    p[3] = 255;
}

static void sse2_clear(uint8_t *fb, uint32_t pitch, uint32_t w, uint32_t h)
{
    uint32_t pixel = (uint32_t)D3D_BG_B | ((uint32_t)D3D_BG_G << 8) |
                     ((uint32_t)D3D_BG_R << 16) | 0xFF000000u;
    __m128i fill = _mm_set1_epi32((int)pixel);
    for (uint32_t y = 0; y < h; y++) {
        uint8_t *row = fb + (size_t)y * pitch;
        uint32_t x = 0;
        for (; x + 4 <= w; x += 4)
            _mm_storeu_si128((__m128i *)(row + x * 4), fill);
        for (; x < w; x++)
            memcpy(row + x * 4, &pixel, 4);
    }
}

static uint32_t shade_vertex(const Display3D_Vertex *v)
{
    float nx = v->normal[0], ny = v->normal[1], nz = v->normal[2];
    float nl = sqrtf(nx * nx + ny * ny + nz * nz);
    if (nl > 1e-8f) {
        nx /= nl; ny /= nl; nz /= nl;
    }
    float nd = nx * 0.57735027f + ny * 0.57735027f + nz * 0.57735027f;
    if (nd < 0.0f)
        nd = -nd;
    float sh = 0.35f + 0.65f * nd;
    int br = (int)(v->color & 255);
    int bg = (int)((v->color >> 8) & 255);
    int bb = (int)((v->color >> 16) & 255);
    if (v->color == 0 || v->color == D3D_TEAL) {
        float ax = nx < 0 ? -nx : nx;
        float ay = ny < 0 ? -ny : ny;
        float az = nz < 0 ? -nz : nz;
        br = 70; bg = 150; bb = 210;
        if (az >= ay && az >= ax) {
            br = 100; bg = 175; bb = 230;
        } else if (ax >= ay && ax >= az) {
            br = 55; bg = 155; bb = 175;
        } else {
            br = 110; bg = 135; bb = 190;
        }
    }
    int r = (int)(br * sh);
    int g = (int)(bg * sh);
    int b = (int)(bb * sh);
    if (r > 255) r = 255;
    if (g > 255) g = 255;
    if (b > 255) b = 255;
    return (uint32_t)r | ((uint32_t)g << 8) | ((uint32_t)b << 16) | 0xFF000000u;
}

static int project_vertex(const Display3D_Context *ctx, const AilangVk_MeshUBO *ubo,
                          const float pos[3], float *sx, float *sy, float *sz)
{
    const float *m = ubo->mvp;
    float x = pos[0], y = pos[1], z = pos[2];
    float cx = m[0] * x + m[4] * y + m[8]  * z + m[12];
    float cy = m[1] * x + m[5] * y + m[9]  * z + m[13];
    float cz = m[2] * x + m[6] * y + m[10] * z + m[14];
    float cw = m[3] * x + m[7] * y + m[11] * z + m[15];
    if (cw > -1e-8f && cw < 1e-8f)
        return 0;
    float iw = 1.0f / cw;
    *sx = (cx * iw * 0.5f + 0.5f) * (float)ctx->width;
    *sy = (cy * iw * 0.5f + 0.5f) * (float)ctx->height;
    *sz = cz * iw;
    return 1;
}

static void fill_tri(Display3D_Context *ctx, uint8_t *fb, uint32_t pitch,
                     float x0, float y0, float z0,
                     float x1, float y1, float z1,
                     float x2, float y2, float z2,
                     uint32_t color)
{
    int w = (int)ctx->width, h = (int)ctx->height;
    int minx = (int)floorf(fminf(x0, fminf(x1, x2)));
    int maxx = (int)ceilf(fmaxf(x0, fmaxf(x1, x2)));
    int miny = (int)floorf(fminf(y0, fminf(y1, y2)));
    int maxy = (int)ceilf(fmaxf(y0, fmaxf(y1, y2)));
    if (minx < 0) minx = 0;
    if (miny < 0) miny = 0;
    if (maxx >= w) maxx = w - 1;
    if (maxy >= h) maxy = h - 1;
    if (minx > maxx || miny > maxy)
        return;
    float area = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0);
    if (area > -1e-6f && area < 1e-6f)
        return;
    float inv = 1.0f / area;
    uint8_t cr = (uint8_t)(color & 255);
    uint8_t cg = (uint8_t)((color >> 8) & 255);
    uint8_t cb = (uint8_t)((color >> 16) & 255);
    for (int y = miny; y <= maxy; y++) {
        for (int x = minx; x <= maxx; x++) {
            float px = (float)x + 0.5f, py = (float)y + 0.5f;
            float w0 = ((x1 - px) * (y2 - py) - (y1 - py) * (x2 - px)) * inv;
            float w1 = ((x2 - px) * (y0 - py) - (y2 - py) * (x0 - px)) * inv;
            float w2 = 1.0f - w0 - w1;
            if (w0 < 0.0f || w1 < 0.0f || w2 < 0.0f)
                continue;
            float z = w0 * z0 + w1 * z1 + w2 * z2;
            size_t zi = (size_t)y * (size_t)w + (size_t)x;
            if (z >= ctx->zbuf[zi])
                continue;
            ctx->zbuf[zi] = z;
            pack_bgra(fb + (size_t)y * pitch + (size_t)x * 4, cr, cg, cb);
        }
    }
}

static void sse2_render(Display3D_Context *ctx, uint8_t *fb, uint32_t pitch)
{
    sse2_clear(fb, pitch, ctx->width, ctx->height);
    size_t npix = (size_t)ctx->width * (size_t)ctx->height;
    if (!ctx->zbuf)
        ctx->zbuf = (float *)malloc(npix * sizeof(float));
    if (!ctx->zbuf)
        return;
    for (size_t i = 0; i < npix; i++)
        ctx->zbuf[i] = 1.0f;

    AilangVk_MeshUBO ubo;
    build_mvp(ctx, &ubo);

    for (uint32_t m = 0; m < ctx->mesh_count; m++) {
        D3D_Mesh *mesh = &ctx->meshes[m];
        if (!mesh->verts || mesh->vertex_count < 3)
            continue;
        uint32_t ntri = mesh->index_count ? (mesh->index_count / 3) : (mesh->vertex_count / 3);
        for (uint32_t t = 0; t < ntri; t++) {
            uint32_t i0, i1, i2;
            if (mesh->indices) {
                i0 = mesh->indices[t * 3 + 0];
                i1 = mesh->indices[t * 3 + 1];
                i2 = mesh->indices[t * 3 + 2];
            } else {
                i0 = t * 3 + 0;
                i1 = t * 3 + 1;
                i2 = t * 3 + 2;
            }
            if (i0 >= mesh->vertex_count || i1 >= mesh->vertex_count || i2 >= mesh->vertex_count)
                continue;
            float sx0, sy0, sz0, sx1, sy1, sz1, sx2, sy2, sz2;
            if (!project_vertex(ctx, &ubo, mesh->verts[i0].position, &sx0, &sy0, &sz0))
                continue;
            if (!project_vertex(ctx, &ubo, mesh->verts[i1].position, &sx1, &sy1, &sz1))
                continue;
            if (!project_vertex(ctx, &ubo, mesh->verts[i2].position, &sx2, &sy2, &sz2))
                continue;
            uint32_t col = shade_vertex(&mesh->verts[i0]);
            fill_tri(ctx, fb, pitch, sx0, sy0, sz0, sx1, sy1, sz1, sx2, sy2, sz2, col);
        }
    }
}

static int gpu_upload_mesh(Display3D_Context *ctx, D3D_Mesh *mesh)
{
    if (!ctx->vulkan_enabled || !ctx->vk)
        return 0;
    AilangVk_DestroyBuffer(ctx->vk, &mesh->vbo);
    AilangVk_DestroyBuffer(ctx->vk, &mesh->ibo);
    mesh->gpu_ready = 0;
    uint64_t vbytes = (uint64_t)mesh->vertex_count * sizeof(Display3D_Vertex);
    /* Host-visible VBO: Display3D writes clip-space verts each frame.
     * Device-local staging remains available via AilangVk_StageUpload for
     * compiler / custom pipelines. */
    if (!AilangVk_CreateBuffer(ctx->vk, vbytes, AILANG_VK_BUF_VERTEX, 1, &mesh->vbo))
        return 0;
    if (!AilangVk_StageUpload(ctx->vk, &mesh->vbo, mesh->verts, vbytes))
        return 0;
    if (mesh->index_count && mesh->indices) {
        uint64_t ibytes = (uint64_t)mesh->index_count * sizeof(uint32_t);
        if (!AilangVk_CreateBuffer(ctx->vk, ibytes, AILANG_VK_BUF_INDEX, 0, &mesh->ibo))
            return 0;
        if (!AilangVk_StageUpload(ctx->vk, &mesh->ibo, mesh->indices, ibytes))
            return 0;
    }
    mesh->gpu_ready = 1;
    return 1;
}

static int gpu_render(Display3D_Context *ctx, uint8_t *fb, uint32_t pitch)
{
    if (!ctx->vulkan_enabled || !ctx->vk || !ctx->pipe)
        return 0;
    AilangVk_MeshUBO ubo;
    build_mvp(ctx, &ubo);
    for (uint32_t i = 0; i < ctx->mesh_count; i++) {
        D3D_Mesh *m = &ctx->meshes[i];
        if (!m->gpu_ready || !m->vbo.mapped || !m->verts)
            continue;
        Display3D_Vertex *dst = (Display3D_Vertex *)m->vbo.mapped;
        for (uint32_t v = 0; v < m->vertex_count; v++) {
            const Display3D_Vertex *in = &m->verts[v];
            Display3D_Vertex out = *in;
            const float *mat = ubo.mvp;
            float x = in->position[0], y = in->position[1], z = in->position[2];
            float cx = mat[0] * x + mat[4] * y + mat[8]  * z + mat[12];
            float cy = mat[1] * x + mat[5] * y + mat[9]  * z + mat[13];
            float cz = mat[2] * x + mat[6] * y + mat[10] * z + mat[14];
            float cw = mat[3] * x + mat[7] * y + mat[11] * z + mat[15];
            if (cw > -1e-8f && cw < 1e-8f)
                cw = 1e-8f;
            float iw = 1.0f / cw;
            out.position[0] = cx * iw;
            out.position[1] = cy * iw;
            out.position[2] = cz * iw;
            out.color = shade_vertex(in);
            dst[v] = out;
        }
    }
    if (!AilangVk_BeginFrame(ctx->vk, D3D_BG_R / 255.0f, D3D_BG_G / 255.0f, D3D_BG_B / 255.0f))
        return 0;
    if (!AilangVk_BindPipeline(ctx->vk, ctx->pipe)) {
        AilangVk_EndFrame(ctx->vk);
        return 0;
    }
    for (uint32_t i = 0; i < ctx->mesh_count; i++) {
        D3D_Mesh *m = &ctx->meshes[i];
        if (!m->gpu_ready)
            continue;
        AilangVk_Draw(ctx->vk, &m->vbo, m->index_count ? &m->ibo : NULL,
                      m->vertex_count, m->index_count);
    }
    if (!AilangVk_EndFrame(ctx->vk))
        return 0;
    return AilangVk_ReadbackBGRA(ctx->vk, fb, pitch);
}

extern "C" Display3D_Context *Display3D_Create(uint32_t width, uint32_t height, int use_vulkan)
{
    if (width < 1 || height < 1)
        return NULL;
    Display3D_Context *ctx = (Display3D_Context *)calloc(1, sizeof(Display3D_Context));
    if (!ctx)
        return NULL;
    ctx->width = width;
    ctx->height = height;
    ctx->want_vulkan = use_vulkan;
    ctx->camera.target[0] = 0.0f;
    ctx->camera.target[1] = 0.0f;
    ctx->camera.target[2] = 0.0f;
    ctx->camera.distance = 50.0f;
    ctx->camera.yaw = 45.0f;
    ctx->camera.pitch = 30.0f;
    ctx->camera.fov = 45.0f;
    if (use_vulkan)
        Display3D_InitVulkan(ctx);
    return ctx;
}

extern "C" void Display3D_Destroy(Display3D_Context *ctx)
{
    if (!ctx)
        return;
    for (uint32_t i = 0; i < ctx->mesh_count; i++) {
        if (ctx->vk) {
            AilangVk_DestroyBuffer(ctx->vk, &ctx->meshes[i].vbo);
            AilangVk_DestroyBuffer(ctx->vk, &ctx->meshes[i].ibo);
        }
        free(ctx->meshes[i].verts);
        free(ctx->meshes[i].indices);
    }
    if (ctx->vk)
        AilangVk_Destroy(ctx->vk);
    free(ctx->zbuf);
    free(ctx);
}

extern "C" int Display3D_InitVulkan(Display3D_Context *ctx)
{
    if (!ctx)
        return 0;
    ctx->vulkan_enabled = 0;
    if (!ctx->vk)
        ctx->vk = AilangVk_Create();
    if (!ctx->vk)
        return 0;
    if (!AilangVk_InitInstance(ctx->vk, "AILang Display3D")) {
        fprintf(stderr, "[Display3D] Vulkan init failed — SSE2 rasterizer active\n");
        return 0;
    }
    if (!AilangVk_CreateTarget(ctx->vk, ctx->width, ctx->height)) {
        fprintf(stderr, "[Display3D] offscreen target failed — SSE2 rasterizer active\n");
        return 0;
    }
    if (!AilangVk_CreateDefaultMeshPipeline(ctx->vk, &ctx->pipe)) {
        fprintf(stderr, "[Display3D] pipeline creation failed — SSE2 rasterizer active\n");
        return 0;
    }
    ctx->vulkan_enabled = 1;
    fprintf(stderr, "[Display3D] Vulkan path ready (%ux%u)\n", ctx->width, ctx->height);
    return 1;
}

extern "C" void Display3D_UpdateCamera(Display3D_Context *ctx, const Display3D_Camera *cam)
{
    if (!ctx || !cam)
        return;
    ctx->camera = *cam;
}

extern "C" int Display3D_UploadMesh(Display3D_Context *ctx, const Display3D_Mesh *mesh)
{
    if (!ctx || !mesh || !mesh->vertices || mesh->vertex_count < 3)
        return 0;

    D3D_Mesh *slot = NULL;
    for (uint32_t i = 0; i < ctx->mesh_count; i++) {
        if (ctx->meshes[i].id == mesh->mesh_id) {
            slot = &ctx->meshes[i];
            break;
        }
    }
    if (!slot) {
        if (ctx->mesh_count >= D3D_MAX_MESHES)
            return 0;
        slot = &ctx->meshes[ctx->mesh_count++];
        memset(slot, 0, sizeof *slot);
        slot->id = mesh->mesh_id;
    }

    free(slot->verts);
    free(slot->indices);
    slot->verts = NULL;
    slot->indices = NULL;
    slot->vertex_count = mesh->vertex_count;
    slot->index_count = mesh->index_count;
    slot->verts = (Display3D_Vertex *)malloc(sizeof(Display3D_Vertex) * mesh->vertex_count);
    if (!slot->verts)
        return 0;
    memcpy(slot->verts, mesh->vertices, sizeof(Display3D_Vertex) * mesh->vertex_count);
    for (uint32_t i = 0; i < slot->vertex_count; i++) {
        if (slot->verts[i].color == 0)
            slot->verts[i].color = D3D_TEAL;
    }
    if (mesh->index_count && mesh->indices) {
        slot->indices = (uint32_t *)malloc(sizeof(uint32_t) * mesh->index_count);
        if (!slot->indices)
            return 0;
        memcpy(slot->indices, mesh->indices, sizeof(uint32_t) * mesh->index_count);
    }

    if (ctx->vulkan_enabled)
        gpu_upload_mesh(ctx, slot);

    fprintf(stderr, "[Display3D] mesh %u staged (%u verts, %u indices, gpu=%d)\n",
            mesh->mesh_id, mesh->vertex_count, mesh->index_count, slot->gpu_ready);
    return 1;
}

extern "C" void Display3D_RenderFrame(Display3D_Context *ctx, uint8_t *frame_buffer, uint32_t pitch)
{
    if (!ctx || !frame_buffer)
        return;
    if (pitch < ctx->width * 4)
        return;
    if (ctx->vulkan_enabled && gpu_render(ctx, frame_buffer, pitch))
        return;
    sse2_render(ctx, frame_buffer, pitch);
}
