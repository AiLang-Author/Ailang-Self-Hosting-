# AILang 3D Vulkan Display Library — Architecture & Handoff Specification

**Status:** Host AilangVk instance + staging + pipeline implemented.  
**CPU path:** **unchanged.** `CAD_View` (tess → software FB → BMP / `frame.raw`) remains the AILang rasterizer. `Library.Vulkan` / `Library.Display3D` keep their existing AILang contracts.

---

## Split

```
AILang (intact)
  CAD_Tess  →  CAD_View FillTri/Z  →  Framebuffer / frame.raw
  Library.Vulkan / Library.Display3D   (existing handle API)

Host GPU resource (new, optional)
  AilangVk  →  instance / device / staging / pipeline / BGRA readback
  Display3D C facade consumes AilangVk
```

Vulkan does **not** replace the software viewport. `cad_app` / `cad_view` keep going through `CAD_View`. The `.so` is a compiler / Display / CAD **host** resource when a GPU (or lavapipe) is present.

### Hardware
- **CPU path:** existing `CAD_View` (and the existing AILang Display3D/Vulkan libraries).
- **GPU path:** `libvulkan.so.1`, offscreen, no WSI.
- **Host-only fallback** inside the `.so` if `vkCreateInstance` fails — not a second CAD rasterizer.

Env: `AILANG_VK_VALIDATE=1`, `AILANG_VK_DEVICE=cpu|gpu|<index>`.

---

## What the C library does

| Piece | File | Role |
|---|---|---|
| **AilangVk** | `include/ailang_vk.h`, `src/ailang_vk.cpp` | Orthogonal GPU resource: instance, device, buffers, SPIR-V pipelines, BGRA readback. No B-Rep. |
| **Display3D C** | `include/ailang_display3d.h`, `src/display3d_vulkan.cpp` | Host consumer of AilangVk (mesh + orbit camera). |
| **AILang CPU** | `Librarys/Cad/Library.CAD_View.ailang` | Software viewport — **do not rewrite for Vulkan.** |
| **AILang API** | `Librarys/Display/Render/Library.Vulkan.ailang`, `Library.Display3D.ailang` | Existing contracts (`CAD_Store` handles, `SetCamera` as written). |

Implemented in AilangVk: instance init, vertex staging, graphics pipeline, offscreen readback.

```bash
cd CAD/display3d && make test
```

---

## Files

- Spec: `docs/cad/AILANG_3D_VULKAN_DISPLAY_PLAN.md`
- Orthogonal C API: `CAD/display3d/include/ailang_vk.h`
- Viewport C API: `CAD/display3d/include/ailang_display3d.h`
- Vulkan core: `CAD/display3d/src/ailang_vk.cpp`
- Host facade: `CAD/display3d/src/display3d_vulkan.cpp`
- Default SPIR-V: `CAD/display3d/src/shaders/`
- Build: `CAD/display3d/Makefile`
