/* ailang_vk.h — Orthogonal Vulkan GPU resource for AILang
 *
 * Shared by the compiler (SPIR-V / debug viz), the Display compositor,
 * and the CAD viewport. This layer does not know about B-Rep, solids,
 * or workbenches. Consumers bring their own shaders and vertex layouts.
 *
 * C ABI. No Vulkan types leak through the header.
 *
 *   Compiler  ─┐
 *   Display   ─┼─►  AilangVk  ─►  VkInstance / device / buffers / pipelines
 *   CAD View  ─┘
 *
 * Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
 * Licensed under the Sean Collins Software License (SCSL v1.0).
 */
#ifndef AILANG_VK_H
#define AILANG_VK_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct AilangVk_Context AilangVk_Context;
typedef uint32_t AilangVk_PipelineId;

#define AILANG_VK_PIPE_NONE 0u

/* Buffer usage bits (orthogonal to VkBufferUsageFlagBits). */
enum {
    AILANG_VK_BUF_VERTEX   = 1u,
    AILANG_VK_BUF_INDEX    = 2u,
    AILANG_VK_BUF_UNIFORM  = 4u,
    AILANG_VK_BUF_STAGING  = 8u,
    AILANG_VK_BUF_STORAGE  = 16u
};

/* Vertex attribute formats. */
enum {
    AILANG_VK_FMT_F32X2      = 1,
    AILANG_VK_FMT_F32X3      = 2,
    AILANG_VK_FMT_F32X4      = 3,
    AILANG_VK_FMT_U8X4_UNORM = 4
};

enum {
    AILANG_VK_TOPO_TRIANGLES = 0,
    AILANG_VK_TOPO_LINES     = 1
};

typedef struct AilangVk_Buffer {
    uint64_t  size;
    uint32_t  usage_bits;
    uint32_t  host_visible;
    uintptr_t handle;   /* VkBuffer */
    uintptr_t memory;   /* VkDeviceMemory */
    void     *mapped;   /* host-visible mapping, else NULL */
} AilangVk_Buffer;

typedef struct AilangVk_VertexAttr {
    uint32_t location;
    uint32_t format;    /* AILANG_VK_FMT_* */
    uint32_t offset;
} AilangVk_VertexAttr;

typedef struct AilangVk_PipelineDesc {
    const uint32_t         *vert_spv;
    uint32_t                vert_spv_words;
    const uint32_t         *frag_spv;
    uint32_t                frag_spv_words;
    uint32_t                vertex_stride;
    uint32_t                attr_count;
    const AilangVk_VertexAttr *attrs;
    uint32_t                ubo_size;     /* 0 = no UBO */
    int                     depth_test;
    int                     topology;     /* AILANG_VK_TOPO_* */
    int                     cull_back;    /* 0 = two-sided (CAD default) */
} AilangVk_PipelineDesc;

typedef struct AilangVk_Info {
    char     device_name[256];
    uint32_t api_version;
    uint32_t vendor_id;
    uint32_t device_id;
    uint32_t device_type;     /* 0=other 1=integrated 2=discrete 3=virtual 4=cpu */
    uint32_t graphics_queue_family;
    uint32_t target_w;
    uint32_t target_h;
    int      ready;
} AilangVk_Info;

/* std140 UBO used by the default mesh pipeline (compiler/CAD may use their own). */
typedef struct AilangVk_MeshUBO {
    float mvp[16];
    float light[4];
} AilangVk_MeshUBO;

AilangVk_Context *AilangVk_Create(void);
void              AilangVk_Destroy(AilangVk_Context *vk);

/* Instance + physical device + logical device + command pool.
 * app_name may be NULL. Returns 1 on success.
 * Env: AILANG_VK_VALIDATE=1 enables Khronos validation if present.
 *      AILANG_VK_DEVICE=cpu|gpu|<index> pins device selection.
 */
int  AilangVk_InitInstance(AilangVk_Context *vk, const char *app_name);
int  AilangVk_Ready(const AilangVk_Context *vk);
void AilangVk_GetInfo(const AilangVk_Context *vk, AilangVk_Info *out);

/* Offscreen color+depth target. Recreate-safe. */
int  AilangVk_CreateTarget(AilangVk_Context *vk, uint32_t width, uint32_t height);

/* Device-local or host-visible buffer. Staging upload for DEVICE_LOCAL. */
int  AilangVk_CreateBuffer(AilangVk_Context *vk, uint64_t size, uint32_t usage_bits,
                           int host_visible, AilangVk_Buffer *out);
int  AilangVk_StageUpload(AilangVk_Context *vk, AilangVk_Buffer *dst,
                          const void *src, uint64_t size);
void AilangVk_DestroyBuffer(AilangVk_Context *vk, AilangVk_Buffer *buf);

/* Graphics pipeline from caller SPIR-V. Default mesh helper uses embedded shaders. */
int  AilangVk_CreatePipeline(AilangVk_Context *vk, const AilangVk_PipelineDesc *desc,
                             AilangVk_PipelineId *out);
int  AilangVk_CreateDefaultMeshPipeline(AilangVk_Context *vk, AilangVk_PipelineId *out);
int  AilangVk_UpdateUBO(AilangVk_Context *vk, const void *data, uint32_t size);

int  AilangVk_BeginFrame(AilangVk_Context *vk, float clear_r, float clear_g, float clear_b);
int  AilangVk_BindPipeline(AilangVk_Context *vk, AilangVk_PipelineId pipe);
int  AilangVk_Draw(AilangVk_Context *vk, const AilangVk_Buffer *vbo,
                   const AilangVk_Buffer *ibo, uint32_t vertex_count, uint32_t index_count);
int  AilangVk_EndFrame(AilangVk_Context *vk);

/* Copy last frame into a CPU BGRA8 buffer (X11 / CAD host / Display FB). */
int  AilangVk_ReadbackBGRA(AilangVk_Context *vk, uint8_t *dst, uint32_t pitch);

#ifdef __cplusplus
}
#endif

#endif /* AILANG_VK_H */
