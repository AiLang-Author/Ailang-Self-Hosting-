# AILANG Display System — Build Progress
**Status: Phase 7 Complete — BSP Window Management Next**
Last Updated: March 30, 2026

---

## What's Built and Working

### Phase 1 — Terminal Surface ✅
- `Library.DSurfaceTypes.ailang` — CELL_32/PIXEL_32 format constants, field offsets
- `Library.DSurface.ailang` — surface create/destroy/accessors, bounds checking (bias fix applied)
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

### Phase 5.5 — DSurface Bias Fix ✅
- `Library.DSurface.ailang` — Surface_GetWidth/Height/Pitch all now subtract 65536 bias
- `TestSurface.ailang` — ✅ all field reads, bounds checks, FillRect, PixelAt passing

### Phase 6 — Input System ✅
- `Library.DInputTypes.ailang` — EvdevEvent struct, Key codes, Btn codes, MouseState, KeyMod
- `Library.DInputEvdev.ailang` — Evdev_OpenDevice, Evdev_Poll, Evdev_ProcessEvent
- `Library.DInputDiscover.ailang` — getdents64 scan of /dev/input/by-id/, readlink resolution
- `TestInput.ailang` — ✅ keyboard + mouse discovered and opened
- Keyboard: ESC exits, key codes printed ✅
- Mouse: movement tracked, clicks registered ✅
- FB: blue background + shapes confirmed on screen ✅

### Phase 7 — KDSETMODE + Pixel Positioning ✅
- **KDSETMODE fix** — open `/dev/tty0`, `VT_GETSTATE` ioctl to find active VT number,
  open `/dev/ttyN` directly, `KDSETMODE(KD_GRAPHICS)` succeeds, text layer gone ✅
- **Pixel Y position fix** — SubRoutine local variable corruption isolated and fixed.
  Draw logic moved to dedicated `DrawInitialScreen()` Function with clean stack frame ✅
- **Photo confirmed**: Red rectangle at exact screen center, white crosshair lines
  intersecting through center of rectangle. Clean blue background, no text overlay ✅
- Hardware: Bob's Pop!_OS, Phenom II, 1280×1024

### Phase 8 — Message System ✅
- `Library.MessageTypes.ailang` — MsgField/MsgEnvelope/MsgPort LinkagePool definitions,
  MsgFieldType/MsgProtocol/WellKnownPort FixedPool constants, manual offset tables
- `Library.MessagePort.ailang` — Port registry (HashMap-backed), Port_Create/Destroy/Send/Receive,
  envelope allocation, field builder/lookup. **Kernel module seam** at Port_Send/Port_Receive.
- `Library.MessageTranslate.ailang` — Protocol dispatch tables (one HashMap per protocol),
  MsgTranslate_Register/Dispatch. BeAPI/Wayland/Qt/X11 all slot in here.
- `Library.MsgBeAPI.ailang` — BeAPI BMessage what codes, field name hashes, handler stubs.
  Registers with MsgTranslate on init.
- `TestMessagePort.ailang` — **14/14 passing** ✅
  - Port lifecycle (create/resolve/destroy)
  - Envelope fields (add/get int/handle, field count)
  - FIFO send/receive
  - Capacity overflow drop-oldest

---

## Known Issues / Deferred

### Dispatch Test (Test4) — Function Address as Argument
- Passing a Function name as a value argument to another function is not supported
- `MsgTranslate_Register(protocol, what_code, SpyHandler)` — compiler rejects `SpyHandler`
- OOP uses `Address` type for function pointers — mechanism not yet fully understood
- **Workaround**: dispatch test skipped for now, wire manually when integrating with display server tick

### Mouse coordinate bias in log
- `[Mouse] btn=0 at 32934,3` — mouse coordinates have 65536 bias not subtracted
- Already handled correctly in Ring1 drain (Subtract 65536), cosmetic log issue only

---

## Compiler Constraints Discovered (cumulative)

| Constraint | Workaround |
|------------|------------|
| 6-arg ABI limit | Functions max 6 inputs, use FixedPool for 7+ params |
| StoreValue byte bug (0-255) | Add 65536 bias, subtract on read — all FixedPool fields |
| Small local variable behavior | Add 65536 bias to any local holding values 0-255 |
| SubRoutine crash with locals | Use Function with Output: Integer instead |
| SubRoutine many locals corrupts values | Move computation into dedicated Functions |
| BreakLoop in nested IfCondition | Use flag variable exit pattern |
| ReturnValue inside WhileLoop IfCondition | Use result variable + ElseBlock, exit via flag |
| And()/Or() nested in IfCondition | Split into sequential IfCondition checks |
| WhileLoop EqualTo(1,1) + BreakLoop | Use bounded counter loop instead |
| 7-arg SystemCall fails | mmap with offset=0 drops arg |
| BSP_Init large mmap crash | Bypass Compose_Init for full-screen use |
| HashMap requires string keys | Convert int keys with NumberToString() before Set/Get |
| @ operator only on AllocateLinkage results | Use Dereference(Add(ptr, offset)) for HashMap-sourced pointers |
| Chained @ (ptr@field@field) not supported | Break into two steps with intermediate variable |
| Function address as argument value | Not supported — OOP mechanism under investigation |
| Multiple GetInt calls between function calls | Collect all values first, then do all checks |
| SubRoutine setter pattern via FixedPool | Inline StoreValue directly at call site |
| FB_GetWidth/Height returns value needs clean frame | Call from dedicated Function, not main SubRoutine |
| KDSETMODE on /dev/tty fails ENOTTY | Open /dev/tty0, VT_GETSTATE, open /dev/ttyN directly |

---

## Session Timeline

**March 30, 2026 — Day 1 (5PM–11:30PM)**
Built Phases 1–6 from scratch. 65+ files. Display server + input on real hardware in 6.5 hours.

**March 30, 2026 — Day 1 continued (evening)**
Phase 7: KDSETMODE fix + pixel Y position fix. Red rectangle at screen center confirmed in photo.
Phase 8: Full message system. 14/14 tests passing.
Compiler constraint: SubRoutine local corruption root-caused and documented.
Architectural docs: Debloat Linux v1.0, Graphics API v1.0, Module system design.

---

## What's Next

### Phase 7b — BSP Window Management (IMMEDIATE)
Complete the Ring0 command handlers in `Library.DCompose.ailang`.
Currently only `FOCUS_SET` and `QUIT` are handled. Need:

```
WIN_CREATE   → BSP_Split current focused leaf, allocate surface
WIN_DESTROY  → BSP_Merge leaf back, free surface
TILE_SPLIT_H → BSP_Split horizontal
TILE_SPLIT_V → BSP_Split vertical
TILE_MERGE   → BSP_Merge
TILE_RESIZE  → adjust split position
STACK_ADD    → Stack_Add to current leaf group
STACK_REMOVE → Stack_Remove
STACK_SWITCH → Stack_Switch tab
```

Goal: Alt+V splits screen vertically into two colored surfaces.
First live BSP tiling on real hardware.

### Phase 9 — SysSeat (unblocks sudo dependency)
- Open `/dev/tty0`, find active VT
- Seat daemon grants device fds via SCM_RIGHTS
- Display server requests `/dev/fb0` and `/dev/input/event*` via MessagePort
- No more `sudo ./TestInput.x`

### Phase 10 — Kernel Module (MessagePort cross-process)
- Small C file: `port_create`, `port_write`, `port_read` as kernel objects
- Port_Send / Port_Receive swap to kernel transport
- Everything above unchanged

### Phase 11 — Arch VM
- Strip Arch down to kernel + AILANG modules
- SysInit as PID 1
- SysSupervisor replacing systemd units
- Test profile: 9 modules, boots to display server

### Phase 12 — BeAPI Shim
- BMessage port listener
- MsgTranslate BeAPI handlers wired to Ring0
- First Haiku app renders on AILANG display server

### Phase 13 — Wayland Shim
- Minimal 8-object Wayland protocol
- GTK/Qt apps connect via $WAYLAND_DISPLAY
- XWayland as subprocess for X11 legacy

---

## Hardware

- **Bob** — Pop!_OS, Phenom II 6-core, 1280×1024 (primary dev machine)
- **CAD/CAM machine** — higher spec, Arch VM planned
- Compiler: ailang VSCode plugin (click arrow to build)
- FB test: `Ctrl+Alt+F2` → TTY2 → `sudo chmod a+rw /dev/fb0 /dev/input/event*` → `sudo ./TestInput.x`
- Repo: github.com/AiLang-Author/Ailang-Self-Hosting- (branch: master)

---

## The Bigger Picture

```
AILANG stack as of March 30, 2026:

ailang-html    (design complete, impl pending)
ailang-ui      (aimacro transpiler working, dungeon escape runs)
Widget Kit     (design complete, impl pending)
SPIR-V         (design complete, impl pending)
─────────────────────────────────────────────
Message System (Phase 8 ✅ — 14/14 tests)
Display Server (Phase 7 ✅ — pixels on screen)
Input System   (Phase 6 ✅ — kb+mouse on hardware)
BSP Compositor (Phase 4 ✅ — split/merge/query)
Ring Buffers   (Phase 3 ✅ — all four rings)
Framebuffer    (Phase 2 ✅ — double buffered)
─────────────────────────────────────────────
System Layer   (design complete, impl pending)
  SysInit      → replace systemd PID 1
  SysSupervisor→ replace systemd units
  SysSeat      → replace logind device grants
─────────────────────────────────────────────
Linux Kernel   (for now)
```

Self-hosted compiler writing a display server driving real hardware.
No Qt. No GTK. No Wayland. No systemd. No headers. No build system.
Pixels on screen from a language that compiled itself.

*Document version: 2.0*
*Author: Sean Collins, 2 Paws Machine and Engineering*
*Copyright © 2025 Sean Collins. All rights reserved. SCSL.*