# AILANG Display System — Build Progress
**Status: Phase 7b Complete — BSP Tiling on Real Hardware**
Last Updated: March 31, 2026

---

## What's Built and Working

### Phase 1 — Terminal Surface ✅
- `Library.DSurfaceTypes.ailang` — CELL_32/PIXEL_32 format constants, field offsets
- `Library.DSurface.ailang` — surface create/destroy/accessors, bounds checking
- `Library.DDrawCell.ailang` — Draw_FillRect, Draw_Rect, Draw_Text, Draw_TextAttr, Draw_HLine, Draw_VLine
- `Library.DRenderTerm.ailang` — ANSI terminal flush, diff'd color state, FlushRect
- `TestDisplay01.ailang` — ✅ passing

### Phase 2 — Framebuffer Pixel ✅
- `Library.DDrawPixel.ailang` — Draw_Pix_FillRect, Draw_Pix_Rect, Draw_Pix_HLine, Draw_Pix_VLine, Draw_Pix_Pixel
- `Library.DRenderFB.ailang` — wraps Library.Framebuffer, flush surface to /dev/fb0
- `Library.Framebuffer.ailang` — FB_FillRectFast, double buffering, FB_FlipFast
- `TestDisplay02.ailang` — ✅ passing, RGB bars + shapes on real framebuffer

### Phase 3 — Ring Buffers ✅
- `Library.DRingTypes.ailang` — RingFields, RingID, RingCap, Ring0Cmd, Ring1Event, RingEntry
- `Library.DRing.ailang` — Ring_Create/Destroy/Post/Drain/DropOldest/Peek/IsEmpty/IsFull
- `Library.DRing0/1/2/3.ailang` — all four rings with overflow policies
- `TestRing.ailang` — ✅ passing

### Phase 4 — BSP Compositor ✅
- `Library.DComposeTypes.ailang` — BSPNodeType, BSPNodeFields, StackGroupFields, FloatEntryFields
- `Library.DComposeBSP.ailang` — BSP_Init, BSP_Split, BSP_Merge, BSP_Query, BSP_Free
- `Library.DComposeStack.ailang` — Stack group management
- `Library.DComposeFloat.ailang` — Float window list, hit testing
- `Library.DCompose.ailang` — Compose_Init/Shutdown/Tick, Ring2→dirty→Ring3 pipeline, Compose_Blit
- `TestBSP.ailang`, `TestCompose.ailang`, `TestComposeTick.ailang` — ✅ all passing

### Phase 5 — Live Compositor ✅
- `Library.DZoneTypes.ailang` — Zone struct fields, DisplayConfig pool
- `Library.DZone.ailang` — Zone_InitSingle (full-screen single zone)
- `TestLiveCompositor.ailang` — ✅ blue screen + RGB bars + magenta patch on framebuffer
- Photo confirmed: green crosshair and magenta patch visible on Bob's 1280×1024

### Phase 5.5 — Bias Cleanup ✅
- Confirmed via `TestSmallNumbers.ailang` (20/20 pass): FixedPool `Initialize=` constants,
  local variables, and arithmetic are all correct with raw values. No bias needed anywhere.
- Removed all `+65536/-65536` bias pairs from DSurface, DRing, DRing0/1/2/3,
  DComposeBSP, DComposeFloat, DCompose, DZone, MsgBeAPI.
- All display system fields now stored and read raw.

### Phase 6 — Input System ✅
- `Library.DInputTypes.ailang` — EvdevEvent struct, Key codes, Btn codes, MouseState, KeyMod
- `Library.DInputEvdev.ailang` — Evdev_OpenDevice, Evdev_Poll, Evdev_ProcessEvent
- `Library.DInputDiscover.ailang` — getdents64 scan of /dev/input/by-id/, readlink resolution
- `TestInput.ailang` — ✅ keyboard + mouse discovered and opened

### Phase 7 — KDSETMODE + Pixel Positioning ✅
- KDSETMODE fix — open `/dev/tty0`, VT_GETSTATE ioctl to find active VT number,
  open `/dev/ttyN` directly, KDSETMODE(KD_GRAPHICS) succeeds, text layer gone ✅
- Pixel Y position fix — draw logic in dedicated Function with clean stack frame ✅
- Photo confirmed: Red rectangle at exact screen center, white crosshair lines ✅

### Phase 7b — BSP Window Management ✅
- `Library.DCompose.ailang` — WinTable, WinColors, WinCreate_ForLeaf, all Ring0 handlers
- Ring0 handlers: TILE_SPLIT_V, TILE_SPLIT_H, TILE_MERGE, WIN_CREATE, WIN_DESTROY,
  FOCUS_SET, FOCUS_MODE, QUIT — all working
- `TestWindowBSP.ailang` — ✅ running on real hardware
- Alt+V splits screen into two colored panes ✅
- Alt+H splits horizontally ✅
- Alt+M merges back ✅
- ESC exits cleanly ✅
- Photo confirmed: BSP tiling visible on Bob's 1280×1024 ✅

### Phase 8 — Message System ✅
- `Library.MessageTypes.ailang` — MsgField/MsgEnvelope/MsgPort LinkagePool definitions
- `Library.MessagePort.ailang` — Port registry, Port_Create/Destroy/Send/Receive
- `Library.MessageTranslate.ailang` — Protocol dispatch tables
- `Library.MsgBeAPI.ailang` — BeAPI BMessage what codes, handler stubs
- `TestMessagePort.ailang` — 14/14 passing ✅

---

## Compiler Constraints (confirmed real)

| Constraint | Workaround |
|------------|------------|
| 6-arg ABI limit | Functions max 6 inputs, use FixedPool for 7+ params |
| SubRoutine locals corrupt when many locals present | Move computation into dedicated Functions — each gets a clean stack frame. Keep SubRoutine.Main with zero locals, call Functions for all real work. |
| 7-arg SystemCall fails | mmap with offset=0 drops arg |
| HashMap requires string keys | Convert int keys with NumberToString() before Set/Get |
| @ operator only on AllocateLinkage results | Use Dereference(Add(ptr, offset)) for HashMap-sourced pointers |
| Chained @ (ptr@field@field) not supported | Break into two steps with intermediate variable |
| Function address as argument value | Not supported — OOP Address mechanism under investigation |
| FB_GetWidth/Height needs clean stack frame | Call from dedicated Function, not SubRoutine.Main |
| KDSETMODE on /dev/tty fails ENOTTY | Open /dev/tty0, VT_GETSTATE, open /dev/ttyN directly |
| Surface_Create arg order | format is first: Surface_Create(SurfaceFormat.PIXEL_32, w, h) |
| Top-level statements outside Function/SubRoutine silently fail | All logic must be inside a Function or SubRoutine. Top level: LibraryImport, FixedPool, Function/SubRoutine definitions, RunTask only. |

## Confirmed NOT constraints (tested, removed from table)

These were previously listed as constraints but are confirmed working correctly:

- And()/Or() nested in IfCondition — works fine
- ReturnValue inside WhileLoop/IfCondition — works fine, early exit works
- BreakLoop in nested IfCondition — works fine
- SubRoutine crash with any locals — only crashes with many locals (see real constraint above)
- WhileLoop EqualTo(1,1) + BreakLoop — works fine
- StoreValue byte bug for values 0-255 — does NOT exist. All values store correctly raw.
  The +65536 bias was unnecessary and has been removed from the entire codebase.

---

## Known Issues / Deferred

### Dispatch Test (Test4) — Function Address as Argument
- Passing a Function name as a value argument to another function is not supported
- `MsgTranslate_Register(protocol, what_code, SpyHandler)` — compiler rejects `SpyHandler`
- OOP uses `Address` type for function pointers — mechanism under investigation
- Workaround: dispatch test skipped, wire manually when integrating with display server tick

### Tech Debt
- TestBSP, TestCompose, TestComposeTick — written with old bias assumptions, need audit
- TestRing — same, needs audit against cleaned DRing
- Parser should reject bare assignments/calls at top level with a clear error message

---

## What's Next

### Phase 9 — Font Rendering
- `Library.FontTTF.ailang` exists but is untested
- Need: render text into a PIXEL_32 surface
- Goal: panes show labels, not just solid colors
- First real visual content in the windowing system

### Phase 10 — Mouse Focus
- Connect Ring1 mouse events to BSP_Query hit testing
- Click a pane → focused_leaf updates → visual distinction (border color change)
- Makes the system feel interactive rather than just keyboard-driven

### Phase 11 — Application Model
- A function that acts as an "app": receives a surface, draws into it, posts to Ring2
- Proves the full pipeline: app draws → Ring2 → compositor → framebuffer
- No process model yet — single binary, multiple logical "apps"

### Phase 12 — SysSeat (drops sudo requirement)
- Open /dev/tty0, find active VT
- Seat daemon grants device fds via SCM_RIGHTS
- Display server requests /dev/fb0 and /dev/input/event* via MessagePort

### Phase 13 — Kernel Module (MessagePort cross-process)
- Small C file: port_create, port_write, port_read as kernel objects
- Port_Send/Port_Receive swap to kernel transport

---

## Hardware

- **Bob** — Pop!_OS, Phenom II 6-core, 1280×1024 (primary dev machine)
- Compiler: ailang VSCode plugin (click arrow to build), shorthand acronyms added (IF, Else, GE etc.)
- FB test: `Ctrl+Alt+F2` → TTY2 → `sudo ./TestWindowBSP.x`
- Repo: github.com/AiLang-Author/Ailang-Self-Hosting- (branch: master)

---

## The Bigger Picture

```
AILANG stack as of March 31, 2026:

ailang-html    (design complete, impl pending)
ailang-ui      (aimacro transpiler working)
Widget Kit     (design complete, impl pending)
SPIR-V         (design complete, impl pending)
─────────────────────────────────────────────
Message System (Phase 8 ✅ — 14/14 tests)
Display Server (Phase 7b ✅ — BSP tiling on hardware)
Input System   (Phase 6 ✅ — kb+mouse on hardware)
BSP Compositor (Phase 4 ✅ — split/merge/query)
Ring Buffers   (Phase 3 ✅ — all four rings, bias-free)
Framebuffer    (Phase 2 ✅ — double buffered)
─────────────────────────────────────────────
System Layer   (design complete, impl pending)
  SysInit      → replace systemd PID 1
  SysSupervisor→ replace systemd units
  SysSeat      → replace logind device grants
─────────────────────────────────────────────
Linux Kernel   (for now)
```

Self-hosted compiler writing a tiling window manager driving real hardware.
No Qt. No GTK. No Wayland. No systemd. No headers. No build system.
Pixels on screen from a language that compiled itself.

*Document version: 3.0*
*Author: Sean Collins, 2 Paws Machine and Engineering*
*Copyright © 2025 Sean Collins. All rights reserved. SCSL.*