/* ailang_vk.cpp — Orthogonal Vulkan resource (compiler / Display / CAD)
 *
 * Instance, device, offscreen target, buffer staging, graphics pipelines,
 * and BGRA readback. No CAD types. No window surface.
 *
 * Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
 * Licensed under the Sean Collins Software License (SCSL v1.0).
 */
#include "ailang_vk.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef HAS_VULKAN
#include <vulkan/vulkan.h>
#include "shaders/mesh_vert.spv.h"
#include "shaders/mesh_frag.spv.h"
#endif

#define AILANG_VK_MAX_PIPES 8
#define AILANG_VK_MAX_ATTRS 8

static void vk_log(const char *msg)
{
    fprintf(stderr, "[AilangVk] %s\n", msg);
}

#ifdef HAS_VULKAN

struct AilangVk_Pipe {
    int used;
    VkShaderModule vs;
    VkShaderModule fs;
    VkDescriptorSetLayout set_layout;
    VkPipelineLayout layout;
    VkDescriptorPool pool;
    VkDescriptorSet set;
    VkPipeline pipeline;
    uint32_t ubo_size;
};

struct AilangVk_Context {
    int ready;
    VkInstance instance;
    VkPhysicalDevice phys;
    VkDevice device;
    VkQueue queue;
    uint32_t qfamily;
    VkCommandPool cmd_pool;
    VkCommandBuffer cmd;
    VkFence fence;

    VkPhysicalDeviceProperties props;

    uint32_t tw, th;
    VkFormat color_fmt;
    VkFormat depth_fmt;
    VkImage color_img;
    VkDeviceMemory color_mem;
    VkImageView color_view;
    VkImage depth_img;
    VkDeviceMemory depth_mem;
    VkImageView depth_view;
    VkRenderPass render_pass;
    VkFramebuffer framebuffer;

    VkBuffer readback;
    VkDeviceMemory readback_mem;
    void *readback_map;
    uint64_t readback_size;

    VkBuffer ubo;
    VkDeviceMemory ubo_mem;
    void *ubo_map;
    uint32_t ubo_size;

    AilangVk_Pipe pipes[AILANG_VK_MAX_PIPES];
    AilangVk_PipelineId bound;
    int in_frame;
};

static uint32_t find_memory_type(AilangVk_Context *vk, uint32_t bits, VkMemoryPropertyFlags flags)
{
    VkPhysicalDeviceMemoryProperties mp;
    vkGetPhysicalDeviceMemoryProperties(vk->phys, &mp);
    for (uint32_t i = 0; i < mp.memoryTypeCount; i++) {
        if ((bits & (1u << i)) == 0)
            continue;
        if ((mp.memoryTypes[i].propertyFlags & flags) == flags)
            return i;
    }
    return UINT32_MAX;
}

static int create_raw_buffer(AilangVk_Context *vk, VkDeviceSize size, VkBufferUsageFlags usage,
                             VkMemoryPropertyFlags memf, VkBuffer *out_buf, VkDeviceMemory *out_mem)
{
    VkBufferCreateInfo bi;
    memset(&bi, 0, sizeof bi);
    bi.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    bi.size = size;
    bi.usage = usage;
    bi.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    if (vkCreateBuffer(vk->device, &bi, NULL, out_buf) != VK_SUCCESS)
        return 0;

    VkMemoryRequirements req;
    vkGetBufferMemoryRequirements(vk->device, *out_buf, &req);
    uint32_t mt = find_memory_type(vk, req.memoryTypeBits, memf);
    if (mt == UINT32_MAX) {
        vkDestroyBuffer(vk->device, *out_buf, NULL);
        *out_buf = VK_NULL_HANDLE;
        return 0;
    }
    VkMemoryAllocateInfo ai;
    memset(&ai, 0, sizeof ai);
    ai.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    ai.allocationSize = req.size;
    ai.memoryTypeIndex = mt;
    if (vkAllocateMemory(vk->device, &ai, NULL, out_mem) != VK_SUCCESS) {
        vkDestroyBuffer(vk->device, *out_buf, NULL);
        *out_buf = VK_NULL_HANDLE;
        return 0;
    }
    vkBindBufferMemory(vk->device, *out_buf, *out_mem, 0);
    return 1;
}

static int create_image(AilangVk_Context *vk, uint32_t w, uint32_t h, VkFormat fmt,
                        VkImageUsageFlags usage, VkImageAspectFlags aspect,
                        VkImage *out_img, VkDeviceMemory *out_mem, VkImageView *out_view)
{
    VkImageCreateInfo ii;
    memset(&ii, 0, sizeof ii);
    ii.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    ii.imageType = VK_IMAGE_TYPE_2D;
    ii.format = fmt;
    ii.extent.width = w;
    ii.extent.height = h;
    ii.extent.depth = 1;
    ii.mipLevels = 1;
    ii.arrayLayers = 1;
    ii.samples = VK_SAMPLE_COUNT_1_BIT;
    ii.tiling = VK_IMAGE_TILING_OPTIMAL;
    ii.usage = usage;
    ii.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    ii.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    if (vkCreateImage(vk->device, &ii, NULL, out_img) != VK_SUCCESS)
        return 0;

    VkMemoryRequirements req;
    vkGetImageMemoryRequirements(vk->device, *out_img, &req);
    uint32_t mt = find_memory_type(vk, req.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (mt == UINT32_MAX) {
        vkDestroyImage(vk->device, *out_img, NULL);
        *out_img = VK_NULL_HANDLE;
        return 0;
    }
    VkMemoryAllocateInfo ai;
    memset(&ai, 0, sizeof ai);
    ai.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    ai.allocationSize = req.size;
    ai.memoryTypeIndex = mt;
    if (vkAllocateMemory(vk->device, &ai, NULL, out_mem) != VK_SUCCESS) {
        vkDestroyImage(vk->device, *out_img, NULL);
        *out_img = VK_NULL_HANDLE;
        return 0;
    }
    vkBindImageMemory(vk->device, *out_img, *out_mem, 0);

    VkImageViewCreateInfo vi;
    memset(&vi, 0, sizeof vi);
    vi.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    vi.image = *out_img;
    vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
    vi.format = fmt;
    vi.subresourceRange.aspectMask = aspect;
    vi.subresourceRange.levelCount = 1;
    vi.subresourceRange.layerCount = 1;
    if (vkCreateImageView(vk->device, &vi, NULL, out_view) != VK_SUCCESS)
        return 0;
    return 1;
}

static int submit_and_wait(AilangVk_Context *vk)
{
    if (vkEndCommandBuffer(vk->cmd) != VK_SUCCESS)
        return 0;
    VkSubmitInfo si;
    memset(&si, 0, sizeof si);
    si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    si.commandBufferCount = 1;
    si.pCommandBuffers = &vk->cmd;
    vkResetFences(vk->device, 1, &vk->fence);
    if (vkQueueSubmit(vk->queue, 1, &si, vk->fence) != VK_SUCCESS)
        return 0;
    if (vkWaitForFences(vk->device, 1, &vk->fence, VK_TRUE, 10ull * 1000ull * 1000ull * 1000ull) != VK_SUCCESS)
        return 0;
    return 1;
}

static int begin_oneshot(AilangVk_Context *vk)
{
    vkResetCommandBuffer(vk->cmd, 0);
    VkCommandBufferBeginInfo bi;
    memset(&bi, 0, sizeof bi);
    bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    return vkBeginCommandBuffer(vk->cmd, &bi) == VK_SUCCESS;
}

static void destroy_target(AilangVk_Context *vk)
{
    if (!vk->device)
        return;
    vkDeviceWaitIdle(vk->device);
    if (vk->framebuffer)
        vkDestroyFramebuffer(vk->device, vk->framebuffer, NULL);
    if (vk->render_pass)
        vkDestroyRenderPass(vk->device, vk->render_pass, NULL);
    if (vk->color_view)
        vkDestroyImageView(vk->device, vk->color_view, NULL);
    if (vk->color_img)
        vkDestroyImage(vk->device, vk->color_img, NULL);
    if (vk->color_mem)
        vkFreeMemory(vk->device, vk->color_mem, NULL);
    if (vk->depth_view)
        vkDestroyImageView(vk->device, vk->depth_view, NULL);
    if (vk->depth_img)
        vkDestroyImage(vk->device, vk->depth_img, NULL);
    if (vk->depth_mem)
        vkFreeMemory(vk->device, vk->depth_mem, NULL);
    if (vk->readback)
        vkDestroyBuffer(vk->device, vk->readback, NULL);
    if (vk->readback_mem)
        vkFreeMemory(vk->device, vk->readback_mem, NULL);
    vk->framebuffer = VK_NULL_HANDLE;
    vk->render_pass = VK_NULL_HANDLE;
    vk->color_view = vk->depth_view = VK_NULL_HANDLE;
    vk->color_img = vk->depth_img = VK_NULL_HANDLE;
    vk->color_mem = vk->depth_mem = VK_NULL_HANDLE;
    vk->readback = VK_NULL_HANDLE;
    vk->readback_mem = VK_NULL_HANDLE;
    vk->readback_map = NULL;
    vk->readback_size = 0;
    vk->tw = vk->th = 0;
}

static void destroy_pipe(AilangVk_Context *vk, AilangVk_Pipe *p)
{
    if (!p->used || !vk->device)
        return;
    if (p->pipeline)
        vkDestroyPipeline(vk->device, p->pipeline, NULL);
    if (p->layout)
        vkDestroyPipelineLayout(vk->device, p->layout, NULL);
    if (p->pool)
        vkDestroyDescriptorPool(vk->device, p->pool, NULL);
    if (p->set_layout)
        vkDestroyDescriptorSetLayout(vk->device, p->set_layout, NULL);
    if (p->vs)
        vkDestroyShaderModule(vk->device, p->vs, NULL);
    if (p->fs)
        vkDestroyShaderModule(vk->device, p->fs, NULL);
    memset(p, 0, sizeof *p);
}

static VkFormat attr_format(uint32_t fmt)
{
    switch (fmt) {
    case AILANG_VK_FMT_F32X2:      return VK_FORMAT_R32G32_SFLOAT;
    case AILANG_VK_FMT_F32X3:      return VK_FORMAT_R32G32B32_SFLOAT;
    case AILANG_VK_FMT_F32X4:      return VK_FORMAT_R32G32B32A32_SFLOAT;
    case AILANG_VK_FMT_U8X4_UNORM: return VK_FORMAT_R8G8B8A8_UNORM;
    default:                       return VK_FORMAT_R32G32B32_SFLOAT;
    }
}

static int layer_available(const char *name)
{
    uint32_t n = 0;
    vkEnumerateInstanceLayerProperties(&n, NULL);
    if (!n)
        return 0;
    VkLayerProperties *props = (VkLayerProperties *)malloc(sizeof(VkLayerProperties) * n);
    if (!props)
        return 0;
    vkEnumerateInstanceLayerProperties(&n, props);
    int ok = 0;
    for (uint32_t i = 0; i < n; i++) {
        if (strcmp(props[i].layerName, name) == 0) {
            ok = 1;
            break;
        }
    }
    free(props);
    return ok;
}

static int score_device(const VkPhysicalDeviceProperties *p, int want_cpu, int want_gpu)
{
    int s = 0;
    switch (p->deviceType) {
    case VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU:   s = 400; break;
    case VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU: s = 300; break;
    case VK_PHYSICAL_DEVICE_TYPE_VIRTUAL_GPU:    s = 200; break;
    case VK_PHYSICAL_DEVICE_TYPE_CPU:            s = 100; break;
    default:                                     s = 10;  break;
    }
    if (want_cpu && p->deviceType == VK_PHYSICAL_DEVICE_TYPE_CPU)
        s += 1000;
    if (want_gpu && (p->deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU ||
                     p->deviceType == VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU))
        s += 1000;
    return s;
}

static int pick_queue_family(VkPhysicalDevice phys, uint32_t *out)
{
    uint32_t n = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(phys, &n, NULL);
    if (!n)
        return 0;
    VkQueueFamilyProperties *q = (VkQueueFamilyProperties *)malloc(sizeof(*q) * n);
    if (!q)
        return 0;
    vkGetPhysicalDeviceQueueFamilyProperties(phys, &n, q);
    int found = 0;
    for (uint32_t i = 0; i < n; i++) {
        if (q[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) {
            *out = i;
            found = 1;
            break;
        }
    }
    free(q);
    return found;
}

#endif /* HAS_VULKAN */

extern "C" AilangVk_Context *AilangVk_Create(void)
{
#ifdef HAS_VULKAN
    AilangVk_Context *vk = (AilangVk_Context *)calloc(1, sizeof(AilangVk_Context));
    return vk;
#else
    return (AilangVk_Context *)calloc(1, 8);
#endif
}

extern "C" void AilangVk_Destroy(AilangVk_Context *vk)
{
    if (!vk)
        return;
#ifdef HAS_VULKAN
    if (vk->device)
        vkDeviceWaitIdle(vk->device);
    destroy_target(vk);
    for (int i = 0; i < AILANG_VK_MAX_PIPES; i++)
        destroy_pipe(vk, &vk->pipes[i]);
    if (vk->ubo)
        vkDestroyBuffer(vk->device, vk->ubo, NULL);
    if (vk->ubo_mem)
        vkFreeMemory(vk->device, vk->ubo_mem, NULL);
    if (vk->fence)
        vkDestroyFence(vk->device, vk->fence, NULL);
    if (vk->cmd_pool)
        vkDestroyCommandPool(vk->device, vk->cmd_pool, NULL);
    if (vk->device)
        vkDestroyDevice(vk->device, NULL);
    if (vk->instance)
        vkDestroyInstance(vk->instance, NULL);
#endif
    free(vk);
}

extern "C" int AilangVk_InitInstance(AilangVk_Context *vk, const char *app_name)
{
#ifdef HAS_VULKAN
    if (!vk)
        return 0;
    if (vk->ready)
        return 1;

    VkApplicationInfo ai;
    memset(&ai, 0, sizeof ai);
    ai.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    ai.pApplicationName = app_name ? app_name : "AILang";
    ai.applicationVersion = VK_MAKE_VERSION(1, 0, 0);
    ai.pEngineName = "AilangVk";
    ai.engineVersion = VK_MAKE_VERSION(1, 0, 0);
    ai.apiVersion = VK_API_VERSION_1_0;

    const char *val_layer = "VK_LAYER_KHRONOS_validation";
    const char *layers[1];
    uint32_t nlayers = 0;
    const char *env = getenv("AILANG_VK_VALIDATE");
    if (env && env[0] == '1' && layer_available(val_layer)) {
        layers[0] = val_layer;
        nlayers = 1;
        vk_log("validation layer enabled");
    }

    VkInstanceCreateInfo ici;
    memset(&ici, 0, sizeof ici);
    ici.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    ici.pApplicationInfo = &ai;
    ici.enabledLayerCount = nlayers;
    ici.ppEnabledLayerNames = nlayers ? layers : NULL;

    if (vkCreateInstance(&ici, NULL, &vk->instance) != VK_SUCCESS) {
        vk_log("vkCreateInstance failed");
        return 0;
    }

    uint32_t ndev = 0;
    vkEnumeratePhysicalDevices(vk->instance, &ndev, NULL);
    if (ndev == 0) {
        vk_log("no physical devices");
        return 0;
    }
    VkPhysicalDevice *devs = (VkPhysicalDevice *)malloc(sizeof(VkPhysicalDevice) * ndev);
    if (!devs)
        return 0;
    vkEnumeratePhysicalDevices(vk->instance, &ndev, devs);

    int want_cpu = 0, want_gpu = 0, pin = -1;
    const char *dsel = getenv("AILANG_VK_DEVICE");
    if (dsel) {
        if (strcmp(dsel, "cpu") == 0)
            want_cpu = 1;
        else if (strcmp(dsel, "gpu") == 0)
            want_gpu = 1;
        else
            pin = atoi(dsel);
    }

    int best = -1, best_score = -1;
    for (uint32_t i = 0; i < ndev; i++) {
        uint32_t qf = 0;
        if (!pick_queue_family(devs[i], &qf))
            continue;
        VkPhysicalDeviceProperties p;
        vkGetPhysicalDeviceProperties(devs[i], &p);
        int sc = score_device(&p, want_cpu, want_gpu);
        if (pin >= 0)
            sc = ((int)i == pin) ? 10000 : -1;
        if (sc > best_score) {
            best_score = sc;
            best = (int)i;
            vk->phys = devs[i];
            vk->qfamily = qf;
            vk->props = p;
        }
    }
    free(devs);
    if (best < 0) {
        vk_log("no graphics-capable device");
        return 0;
    }

    float prio = 1.0f;
    VkDeviceQueueCreateInfo qci;
    memset(&qci, 0, sizeof qci);
    qci.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    qci.queueFamilyIndex = vk->qfamily;
    qci.queueCount = 1;
    qci.pQueuePriorities = &prio;

    VkDeviceCreateInfo dci;
    memset(&dci, 0, sizeof dci);
    dci.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    dci.queueCreateInfoCount = 1;
    dci.pQueueCreateInfos = &qci;

    if (vkCreateDevice(vk->phys, &dci, NULL, &vk->device) != VK_SUCCESS) {
        vk_log("vkCreateDevice failed");
        return 0;
    }
    vkGetDeviceQueue(vk->device, vk->qfamily, 0, &vk->queue);

    VkCommandPoolCreateInfo pci;
    memset(&pci, 0, sizeof pci);
    pci.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pci.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    pci.queueFamilyIndex = vk->qfamily;
    if (vkCreateCommandPool(vk->device, &pci, NULL, &vk->cmd_pool) != VK_SUCCESS)
        return 0;

    VkCommandBufferAllocateInfo cai;
    memset(&cai, 0, sizeof cai);
    cai.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    cai.commandPool = vk->cmd_pool;
    cai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cai.commandBufferCount = 1;
    if (vkAllocateCommandBuffers(vk->device, &cai, &vk->cmd) != VK_SUCCESS)
        return 0;

    VkFenceCreateInfo fi;
    memset(&fi, 0, sizeof fi);
    fi.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    fi.flags = VK_FENCE_CREATE_SIGNALED_BIT;
    if (vkCreateFence(vk->device, &fi, NULL, &vk->fence) != VK_SUCCESS)
        return 0;

    vk->ready = 1;
    fprintf(stderr, "[AilangVk] instance+device ready: %s (type=%u)\n",
            vk->props.deviceName, (unsigned)vk->props.deviceType);
    return 1;
#else
    (void)vk;
    (void)app_name;
    vk_log("built without HAS_VULKAN");
    return 0;
#endif
}

extern "C" int AilangVk_Ready(const AilangVk_Context *vk)
{
#ifdef HAS_VULKAN
    return vk && vk->ready;
#else
    (void)vk;
    return 0;
#endif
}

extern "C" void AilangVk_GetInfo(const AilangVk_Context *vk, AilangVk_Info *out)
{
    if (!out)
        return;
    memset(out, 0, sizeof *out);
#ifdef HAS_VULKAN
    if (!vk)
        return;
    out->ready = vk->ready;
    out->target_w = vk->tw;
    out->target_h = vk->th;
    out->graphics_queue_family = vk->qfamily;
    if (vk->ready) {
        snprintf(out->device_name, sizeof out->device_name, "%s", vk->props.deviceName);
        out->api_version = vk->props.apiVersion;
        out->vendor_id = vk->props.vendorID;
        out->device_id = vk->props.deviceID;
        out->device_type = (uint32_t)vk->props.deviceType;
    }
#else
    (void)vk;
#endif
}

extern "C" int AilangVk_CreateTarget(AilangVk_Context *vk, uint32_t width, uint32_t height)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->ready || width < 1 || height < 1)
        return 0;
    if (vk->tw == width && vk->th == height && vk->framebuffer)
        return 1;
    destroy_target(vk);
    /* Render pass died with the target — old graphics pipelines are invalid. */
    for (int i = 0; i < AILANG_VK_MAX_PIPES; i++)
        destroy_pipe(vk, &vk->pipes[i]);
    vk->bound = AILANG_VK_PIPE_NONE;

    vk->color_fmt = VK_FORMAT_R8G8B8A8_UNORM;
    vk->depth_fmt = VK_FORMAT_D32_SFLOAT;

    if (!create_image(vk, width, height, vk->color_fmt,
                      VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
                      VK_IMAGE_ASPECT_COLOR_BIT,
                      &vk->color_img, &vk->color_mem, &vk->color_view)) {
        vk_log("color target failed");
        return 0;
    }
    if (!create_image(vk, width, height, vk->depth_fmt,
                      VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
                      VK_IMAGE_ASPECT_DEPTH_BIT,
                      &vk->depth_img, &vk->depth_mem, &vk->depth_view)) {
        vk_log("depth target failed");
        destroy_target(vk);
        return 0;
    }

    VkAttachmentDescription atts[2];
    memset(atts, 0, sizeof atts);
    atts[0].format = vk->color_fmt;
    atts[0].samples = VK_SAMPLE_COUNT_1_BIT;
    atts[0].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    atts[0].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    atts[0].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    atts[0].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    atts[0].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    atts[0].finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;

    atts[1].format = vk->depth_fmt;
    atts[1].samples = VK_SAMPLE_COUNT_1_BIT;
    atts[1].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    atts[1].storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    atts[1].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    atts[1].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    atts[1].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    atts[1].finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

    VkAttachmentReference cref, dref;
    memset(&cref, 0, sizeof cref);
    memset(&dref, 0, sizeof dref);
    cref.attachment = 0;
    cref.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    dref.attachment = 1;
    dref.layout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

    VkSubpassDescription sub;
    memset(&sub, 0, sizeof sub);
    sub.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    sub.colorAttachmentCount = 1;
    sub.pColorAttachments = &cref;
    sub.pDepthStencilAttachment = &dref;

    VkSubpassDependency dep;
    memset(&dep, 0, sizeof dep);
    dep.srcSubpass = VK_SUBPASS_EXTERNAL;
    dep.dstSubpass = 0;
    dep.srcStageMask = VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT;
    dep.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                       VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
    dep.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
                        VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;

    VkRenderPassCreateInfo rp;
    memset(&rp, 0, sizeof rp);
    rp.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    rp.attachmentCount = 2;
    rp.pAttachments = atts;
    rp.subpassCount = 1;
    rp.pSubpasses = &sub;
    rp.dependencyCount = 1;
    rp.pDependencies = &dep;
    if (vkCreateRenderPass(vk->device, &rp, NULL, &vk->render_pass) != VK_SUCCESS) {
        destroy_target(vk);
        return 0;
    }

    VkImageView views[2] = { vk->color_view, vk->depth_view };
    VkFramebufferCreateInfo fb;
    memset(&fb, 0, sizeof fb);
    fb.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
    fb.renderPass = vk->render_pass;
    fb.attachmentCount = 2;
    fb.pAttachments = views;
    fb.width = width;
    fb.height = height;
    fb.layers = 1;
    if (vkCreateFramebuffer(vk->device, &fb, NULL, &vk->framebuffer) != VK_SUCCESS) {
        destroy_target(vk);
        return 0;
    }

    vk->readback_size = (uint64_t)width * (uint64_t)height * 4ull;
    if (!create_raw_buffer(vk, vk->readback_size,
                           VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                           VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                           &vk->readback, &vk->readback_mem)) {
        destroy_target(vk);
        return 0;
    }
    if (vkMapMemory(vk->device, vk->readback_mem, 0, vk->readback_size, 0, &vk->readback_map) != VK_SUCCESS) {
        destroy_target(vk);
        return 0;
    }

    vk->tw = width;
    vk->th = height;
    return 1;
#else
    (void)vk; (void)width; (void)height;
    return 0;
#endif
}

extern "C" int AilangVk_CreateBuffer(AilangVk_Context *vk, uint64_t size, uint32_t usage_bits,
                                     int host_visible, AilangVk_Buffer *out)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->ready || !out || size == 0)
        return 0;
    memset(out, 0, sizeof *out);
    VkBufferUsageFlags usage = 0;
    if (usage_bits & AILANG_VK_BUF_VERTEX)
        usage |= VK_BUFFER_USAGE_VERTEX_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    if (usage_bits & AILANG_VK_BUF_INDEX)
        usage |= VK_BUFFER_USAGE_INDEX_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    if (usage_bits & AILANG_VK_BUF_UNIFORM)
        usage |= VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT;
    if (usage_bits & AILANG_VK_BUF_STAGING)
        usage |= VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
    if (usage_bits & AILANG_VK_BUF_STORAGE)
        usage |= VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    if (!usage)
        usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;

    VkMemoryPropertyFlags memf = host_visible
        ? (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        : VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT;

    VkBuffer buf = VK_NULL_HANDLE;
    VkDeviceMemory mem = VK_NULL_HANDLE;
    if (!create_raw_buffer(vk, size, usage, memf, &buf, &mem))
        return 0;
    out->size = size;
    out->usage_bits = usage_bits;
    out->host_visible = host_visible ? 1u : 0u;
    out->handle = (uintptr_t)buf;
    out->memory = (uintptr_t)mem;
    if (host_visible) {
        if (vkMapMemory(vk->device, mem, 0, size, 0, &out->mapped) != VK_SUCCESS) {
            vkDestroyBuffer(vk->device, buf, NULL);
            vkFreeMemory(vk->device, mem, NULL);
            memset(out, 0, sizeof *out);
            return 0;
        }
    }
    return 1;
#else
    (void)vk; (void)size; (void)usage_bits; (void)host_visible; (void)out;
    return 0;
#endif
}

extern "C" int AilangVk_StageUpload(AilangVk_Context *vk, AilangVk_Buffer *dst,
                                    const void *src, uint64_t size)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->ready || !dst || !src || size == 0 || size > dst->size)
        return 0;
    if (dst->host_visible && dst->mapped) {
        memcpy(dst->mapped, src, (size_t)size);
        return 1;
    }
    AilangVk_Buffer staging;
    if (!AilangVk_CreateBuffer(vk, size, AILANG_VK_BUF_STAGING, 1, &staging))
        return 0;
    memcpy(staging.mapped, src, (size_t)size);
    if (!begin_oneshot(vk)) {
        AilangVk_DestroyBuffer(vk, &staging);
        return 0;
    }
    VkBufferCopy cp;
    memset(&cp, 0, sizeof cp);
    cp.size = size;
    vkCmdCopyBuffer(vk->cmd, (VkBuffer)staging.handle, (VkBuffer)dst->handle, 1, &cp);
    int ok = submit_and_wait(vk);
    AilangVk_DestroyBuffer(vk, &staging);
    return ok;
#else
    (void)vk; (void)dst; (void)src; (void)size;
    return 0;
#endif
}

extern "C" void AilangVk_DestroyBuffer(AilangVk_Context *vk, AilangVk_Buffer *buf)
{
#ifdef HAS_VULKAN
    if (!vk || !buf)
        return;
    if (buf->handle)
        vkDestroyBuffer(vk->device, (VkBuffer)buf->handle, NULL);
    if (buf->memory)
        vkFreeMemory(vk->device, (VkDeviceMemory)buf->memory, NULL);
    memset(buf, 0, sizeof *buf);
#else
    (void)vk; (void)buf;
#endif
}

#ifdef HAS_VULKAN
static int ensure_ubo(AilangVk_Context *vk, uint32_t size)
{
    if (size == 0)
        return 1;
    if (vk->ubo && vk->ubo_size >= size)
        return 1;
    if (vk->ubo) {
        vkDestroyBuffer(vk->device, vk->ubo, NULL);
        vkFreeMemory(vk->device, vk->ubo_mem, NULL);
        vk->ubo = VK_NULL_HANDLE;
        vk->ubo_mem = VK_NULL_HANDLE;
        vk->ubo_map = NULL;
        vk->ubo_size = 0;
    }
    if (!create_raw_buffer(vk, size, VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                           VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                           &vk->ubo, &vk->ubo_mem))
        return 0;
    if (vkMapMemory(vk->device, vk->ubo_mem, 0, size, 0, &vk->ubo_map) != VK_SUCCESS)
        return 0;
    vk->ubo_size = size;
    return 1;
}

static void bind_ubo_to_pipe(AilangVk_Context *vk, AilangVk_Pipe *p)
{
    if (!p->used || p->ubo_size == 0 || !vk->ubo)
        return;
    VkDescriptorBufferInfo bi;
    memset(&bi, 0, sizeof bi);
    bi.buffer = vk->ubo;
    bi.offset = 0;
    bi.range = p->ubo_size;
    VkWriteDescriptorSet w;
    memset(&w, 0, sizeof w);
    w.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    w.dstSet = p->set;
    w.dstBinding = 0;
    w.descriptorCount = 1;
    w.descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
    w.pBufferInfo = &bi;
    vkUpdateDescriptorSets(vk->device, 1, &w, 0, NULL);
}
#endif

extern "C" int AilangVk_CreatePipeline(AilangVk_Context *vk, const AilangVk_PipelineDesc *desc,
                                       AilangVk_PipelineId *out)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->ready || !desc || !out)
        return 0;
    if (!vk->render_pass) {
        vk_log("CreatePipeline needs a target first");
        return 0;
    }
    if (!desc->vert_spv || !desc->frag_spv || desc->vert_spv_words < 5 || desc->frag_spv_words < 5)
        return 0;
    if (desc->attr_count == 0 || desc->attr_count > AILANG_VK_MAX_ATTRS)
        return 0;

    int slot = -1;
    for (int i = 0; i < AILANG_VK_MAX_PIPES; i++) {
        if (!vk->pipes[i].used) {
            slot = i;
            break;
        }
    }
    if (slot < 0) {
        vk_log("pipeline table full");
        return 0;
    }
    AilangVk_Pipe *p = &vk->pipes[slot];
    memset(p, 0, sizeof *p);

    VkShaderModuleCreateInfo sm;
    memset(&sm, 0, sizeof sm);
    sm.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    sm.codeSize = (size_t)desc->vert_spv_words * 4u;
    sm.pCode = desc->vert_spv;
    if (vkCreateShaderModule(vk->device, &sm, NULL, &p->vs) != VK_SUCCESS) {
        vk_log("vertex SPIR-V rejected");
        return 0;
    }
    sm.codeSize = (size_t)desc->frag_spv_words * 4u;
    sm.pCode = desc->frag_spv;
    if (vkCreateShaderModule(vk->device, &sm, NULL, &p->fs) != VK_SUCCESS) {
        vk_log("fragment SPIR-V rejected");
        vkDestroyShaderModule(vk->device, p->vs, NULL);
        p->vs = VK_NULL_HANDLE;
        return 0;
    }

    VkDescriptorSetLayoutBinding lb;
    memset(&lb, 0, sizeof lb);
    uint32_t nbind = 0;
    if (desc->ubo_size) {
        lb.binding = 0;
        lb.descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        lb.descriptorCount = 1;
        lb.stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT;
        nbind = 1;
    }
    VkDescriptorSetLayoutCreateInfo sl;
    memset(&sl, 0, sizeof sl);
    sl.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    sl.bindingCount = nbind;
    sl.pBindings = nbind ? &lb : NULL;
    if (vkCreateDescriptorSetLayout(vk->device, &sl, NULL, &p->set_layout) != VK_SUCCESS)
        { destroy_pipe(vk, p); return 0; }

    VkPipelineLayoutCreateInfo pl;
    memset(&pl, 0, sizeof pl);
    pl.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    pl.setLayoutCount = 1;
    pl.pSetLayouts = &p->set_layout;
    if (vkCreatePipelineLayout(vk->device, &pl, NULL, &p->layout) != VK_SUCCESS)
        { destroy_pipe(vk, p); return 0; }

    if (desc->ubo_size) {
        VkDescriptorPoolSize ps;
        memset(&ps, 0, sizeof ps);
        ps.type = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        ps.descriptorCount = 1;
        VkDescriptorPoolCreateInfo dp;
        memset(&dp, 0, sizeof dp);
        dp.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
        dp.maxSets = 1;
        dp.poolSizeCount = 1;
        dp.pPoolSizes = &ps;
        if (vkCreateDescriptorPool(vk->device, &dp, NULL, &p->pool) != VK_SUCCESS)
            { destroy_pipe(vk, p); return 0; }
        VkDescriptorSetAllocateInfo da;
        memset(&da, 0, sizeof da);
        da.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
        da.descriptorPool = p->pool;
        da.descriptorSetCount = 1;
        da.pSetLayouts = &p->set_layout;
        if (vkAllocateDescriptorSets(vk->device, &da, &p->set) != VK_SUCCESS)
            { destroy_pipe(vk, p); return 0; }
        if (!ensure_ubo(vk, desc->ubo_size))
            { destroy_pipe(vk, p); return 0; }
        p->ubo_size = desc->ubo_size;
        bind_ubo_to_pipe(vk, p);
    }

    VkPipelineShaderStageCreateInfo stages[2];
    memset(stages, 0, sizeof stages);
    stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
    stages[0].module = p->vs;
    stages[0].pName = "main";
    stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
    stages[1].module = p->fs;
    stages[1].pName = "main";

    VkVertexInputBindingDescription bind;
    memset(&bind, 0, sizeof bind);
    bind.binding = 0;
    bind.stride = desc->vertex_stride;
    bind.inputRate = VK_VERTEX_INPUT_RATE_VERTEX;

    VkVertexInputAttributeDescription attrs[AILANG_VK_MAX_ATTRS];
    memset(attrs, 0, sizeof attrs);
    for (uint32_t i = 0; i < desc->attr_count; i++) {
        attrs[i].location = desc->attrs[i].location;
        attrs[i].binding = 0;
        attrs[i].format = attr_format(desc->attrs[i].format);
        attrs[i].offset = desc->attrs[i].offset;
    }

    VkPipelineVertexInputStateCreateInfo vi;
    memset(&vi, 0, sizeof vi);
    vi.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
    vi.vertexBindingDescriptionCount = 1;
    vi.pVertexBindingDescriptions = &bind;
    vi.vertexAttributeDescriptionCount = desc->attr_count;
    vi.pVertexAttributeDescriptions = attrs;

    VkPipelineInputAssemblyStateCreateInfo ia;
    memset(&ia, 0, sizeof ia);
    ia.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
    ia.topology = (desc->topology == AILANG_VK_TOPO_LINES)
        ? VK_PRIMITIVE_TOPOLOGY_LINE_LIST
        : VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

    VkPipelineViewportStateCreateInfo vp;
    memset(&vp, 0, sizeof vp);
    vp.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
    vp.viewportCount = 1;
    vp.scissorCount = 1;

    VkPipelineRasterizationStateCreateInfo rs;
    memset(&rs, 0, sizeof rs);
    rs.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
    rs.polygonMode = VK_POLYGON_MODE_FILL;
    rs.cullMode = desc->cull_back ? VK_CULL_MODE_BACK_BIT : VK_CULL_MODE_NONE;
    rs.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
    rs.lineWidth = 1.0f;

    VkPipelineMultisampleStateCreateInfo ms;
    memset(&ms, 0, sizeof ms);
    ms.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
    ms.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

    VkPipelineDepthStencilStateCreateInfo ds;
    memset(&ds, 0, sizeof ds);
    ds.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
    ds.depthTestEnable = desc->depth_test ? VK_TRUE : VK_FALSE;
    ds.depthWriteEnable = desc->depth_test ? VK_TRUE : VK_FALSE;
    ds.depthCompareOp = VK_COMPARE_OP_LESS;

    VkPipelineColorBlendAttachmentState ba;
    memset(&ba, 0, sizeof ba);
    ba.colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                        VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;

    VkPipelineColorBlendStateCreateInfo cb;
    memset(&cb, 0, sizeof cb);
    cb.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
    cb.attachmentCount = 1;
    cb.pAttachments = &ba;

    VkDynamicState dyns[2] = { VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR };
    VkPipelineDynamicStateCreateInfo dyn;
    memset(&dyn, 0, sizeof dyn);
    dyn.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO;
    dyn.dynamicStateCount = 2;
    dyn.pDynamicStates = dyns;

    VkGraphicsPipelineCreateInfo gp;
    memset(&gp, 0, sizeof gp);
    gp.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
    gp.stageCount = 2;
    gp.pStages = stages;
    gp.pVertexInputState = &vi;
    gp.pInputAssemblyState = &ia;
    gp.pViewportState = &vp;
    gp.pRasterizationState = &rs;
    gp.pMultisampleState = &ms;
    gp.pDepthStencilState = &ds;
    gp.pColorBlendState = &cb;
    gp.pDynamicState = &dyn;
    gp.layout = p->layout;
    gp.renderPass = vk->render_pass;
    gp.subpass = 0;
    if (vkCreateGraphicsPipelines(vk->device, VK_NULL_HANDLE, 1, &gp, NULL, &p->pipeline) != VK_SUCCESS) {
        vk_log("vkCreateGraphicsPipelines failed");
        { destroy_pipe(vk, p); return 0; }
    }

    p->used = 1;
    *out = (AilangVk_PipelineId)(slot + 1);
    fprintf(stderr, "[AilangVk] pipeline %u created (ubo=%u stride=%u)\n",
            (unsigned)*out, (unsigned)desc->ubo_size, (unsigned)desc->vertex_stride);
    return 1;
#else
    (void)vk; (void)desc; (void)out;
    return 0;
#endif
}

extern "C" int AilangVk_CreateDefaultMeshPipeline(AilangVk_Context *vk, AilangVk_PipelineId *out)
{
#ifdef HAS_VULKAN
    static const AilangVk_VertexAttr attrs[] = {
        { 0, AILANG_VK_FMT_F32X3,      0  },
        { 1, AILANG_VK_FMT_F32X3,      12 },
        { 2, AILANG_VK_FMT_F32X2,      24 },
        { 3, AILANG_VK_FMT_U8X4_UNORM, 32 },
    };
    AilangVk_PipelineDesc d;
    memset(&d, 0, sizeof d);
    d.vert_spv = kMeshVertSpv;
    d.vert_spv_words = kMeshVertSpv_WORDS;
    d.frag_spv = kMeshFragSpv;
    d.frag_spv_words = kMeshFragSpv_WORDS;
    d.vertex_stride = 36;
    d.attr_count = 4;
    d.attrs = attrs;
    /* Default mesh shader is clip-space pass-through. Display3D (and any
     * consumer) applies MVP on the CPU before staging. Custom compiler /
     * Display pipelines pass their own SPIR-V + ubo_size to CreatePipeline. */
    d.ubo_size = 0;
    d.depth_test = 1;
    d.topology = AILANG_VK_TOPO_TRIANGLES;
    d.cull_back = 0;
    return AilangVk_CreatePipeline(vk, &d, out);
#else
    (void)vk; (void)out;
    return 0;
#endif
}

extern "C" int AilangVk_UpdateUBO(AilangVk_Context *vk, const void *data, uint32_t size)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->ready || !data || size == 0)
        return 0;
    if (!ensure_ubo(vk, size) || !vk->ubo_map)
        return 0;
    memcpy(vk->ubo_map, data, size);
    return 1;
#else
    (void)vk; (void)data; (void)size;
    return 0;
#endif
}

extern "C" int AilangVk_BeginFrame(AilangVk_Context *vk, float clear_r, float clear_g, float clear_b)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->ready || !vk->framebuffer || vk->in_frame)
        return 0;
    vkResetCommandBuffer(vk->cmd, 0);
    VkCommandBufferBeginInfo bi;
    memset(&bi, 0, sizeof bi);
    bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    if (vkBeginCommandBuffer(vk->cmd, &bi) != VK_SUCCESS)
        return 0;

    VkClearValue clears[2];
    memset(clears, 0, sizeof clears);
    clears[0].color.float32[0] = clear_r;
    clears[0].color.float32[1] = clear_g;
    clears[0].color.float32[2] = clear_b;
    clears[0].color.float32[3] = 1.0f;
    clears[1].depthStencil.depth = 1.0f;

    VkRenderPassBeginInfo rp;
    memset(&rp, 0, sizeof rp);
    rp.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
    rp.renderPass = vk->render_pass;
    rp.framebuffer = vk->framebuffer;
    rp.renderArea.extent.width = vk->tw;
    rp.renderArea.extent.height = vk->th;
    rp.clearValueCount = 2;
    rp.pClearValues = clears;
    vkCmdBeginRenderPass(vk->cmd, &rp, VK_SUBPASS_CONTENTS_INLINE);

    VkViewport viewport;
    memset(&viewport, 0, sizeof viewport);
    viewport.width = (float)vk->tw;
    viewport.height = (float)vk->th;
    viewport.minDepth = 0.0f;
    viewport.maxDepth = 1.0f;
    vkCmdSetViewport(vk->cmd, 0, 1, &viewport);

    VkRect2D sc;
    memset(&sc, 0, sizeof sc);
    sc.extent.width = vk->tw;
    sc.extent.height = vk->th;
    vkCmdSetScissor(vk->cmd, 0, 1, &sc);

    vk->in_frame = 1;
    vk->bound = AILANG_VK_PIPE_NONE;
    return 1;
#else
    (void)vk; (void)clear_r; (void)clear_g; (void)clear_b;
    return 0;
#endif
}

extern "C" int AilangVk_BindPipeline(AilangVk_Context *vk, AilangVk_PipelineId pipe)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->in_frame || pipe == 0 || pipe > AILANG_VK_MAX_PIPES)
        return 0;
    AilangVk_Pipe *p = &vk->pipes[pipe - 1];
    if (!p->used)
        return 0;
    vkCmdBindPipeline(vk->cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, p->pipeline);
    if (p->ubo_size && p->set)
        vkCmdBindDescriptorSets(vk->cmd, VK_PIPELINE_BIND_POINT_GRAPHICS,
                                p->layout, 0, 1, &p->set, 0, NULL);
    vk->bound = pipe;
    return 1;
#else
    (void)vk; (void)pipe;
    return 0;
#endif
}

extern "C" int AilangVk_Draw(AilangVk_Context *vk, const AilangVk_Buffer *vbo,
                             const AilangVk_Buffer *ibo, uint32_t vertex_count, uint32_t index_count)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->in_frame || !vbo || !vbo->handle)
        return 0;
    VkDeviceSize off = 0;
    VkBuffer vb = (VkBuffer)vbo->handle;
    vkCmdBindVertexBuffers(vk->cmd, 0, 1, &vb, &off);
    if (ibo && ibo->handle && index_count) {
        vkCmdBindIndexBuffer(vk->cmd, (VkBuffer)ibo->handle, 0, VK_INDEX_TYPE_UINT32);
        vkCmdDrawIndexed(vk->cmd, index_count, 1, 0, 0, 0);
    } else if (vertex_count) {
        vkCmdDraw(vk->cmd, vertex_count, 1, 0, 0);
    } else {
        return 0;
    }
    return 1;
#else
    (void)vk; (void)vbo; (void)ibo; (void)vertex_count; (void)index_count;
    return 0;
#endif
}

extern "C" int AilangVk_EndFrame(AilangVk_Context *vk)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->in_frame)
        return 0;
    vkCmdEndRenderPass(vk->cmd);

    VkBufferImageCopy copy;
    memset(&copy, 0, sizeof copy);
    copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    copy.imageSubresource.layerCount = 1;
    copy.imageExtent.width = vk->tw;
    copy.imageExtent.height = vk->th;
    copy.imageExtent.depth = 1;
    vkCmdCopyImageToBuffer(vk->cmd, vk->color_img, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                           vk->readback, 1, &copy);

    vk->in_frame = 0;
    return submit_and_wait(vk);
#else
    (void)vk;
    return 0;
#endif
}

extern "C" int AilangVk_ReadbackBGRA(AilangVk_Context *vk, uint8_t *dst, uint32_t pitch)
{
#ifdef HAS_VULKAN
    if (!vk || !vk->ready || !vk->readback_map || !dst)
        return 0;
    if (pitch < vk->tw * 4)
        return 0;
    const uint8_t *src = (const uint8_t *)vk->readback_map;
    for (uint32_t y = 0; y < vk->th; y++) {
        const uint8_t *srow = src + (size_t)y * vk->tw * 4u;
        uint8_t *drow = dst + (size_t)y * pitch;
        for (uint32_t x = 0; x < vk->tw; x++) {
            /* shader out is RGBA8; host FB is BGRA8 (X11 / CAD_View). */
            drow[x * 4 + 0] = srow[x * 4 + 2];
            drow[x * 4 + 1] = srow[x * 4 + 1];
            drow[x * 4 + 2] = srow[x * 4 + 0];
            drow[x * 4 + 3] = srow[x * 4 + 3];
        }
    }
    return 1;
#else
    (void)vk; (void)dst; (void)pitch;
    return 0;
#endif
}
