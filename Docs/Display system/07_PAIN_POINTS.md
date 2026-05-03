# Pain Points & Hardening Roadmap — AILANG Display System

> **Copyright © 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.**
>
> Derived from full-system documentation review. This is not criticism — it's a prioritized
> list of things that will bite at scale, with suggested mitigations. Each item includes
> *when* it matters, so you can defer what doesn't apply yet.

---

## Tier 1 — Will bite you in production

### 1. No PostgreSQL fallback path

**What:** `Deskbar`, `StartMenu`, `IPCBroker`, and `SysDisplay` all import `PostgreSQL_Complete`
directly. If PG is unreachable at startup, the display server has no defined fallback
beyond "fail to init."

**When it matters:** During development (PG not running), during boot races (display
server starts before PG finishes recovery), during PG upgrades, or when disk is full
and PG refuses connections.

**Mitigation:**
```
- Add a SQLite mirror that syncs the services table + ui.cfg on PG write
- On PG connect failure, fall back to SQLite with a "degraded" flag
- Deskbar_LaunchService checks PG first, falls back to static list from ui.cfg
- The goal is: display server must reach a usable desktop even with PG down
```

### 2. Software cursor on high-resolution displays

**What:** Every frame does save/restore of pixels under the cursor. At 4K (3840×2160),
a 32×32 cursor means touching 8192 pixels twice (read then write). That's cheap
per frame but compounds with every other framebuffer operation. The FPS counter
exists partly to measure this cost.

**When it matters:** 4K displays, multiple monitors, or when framerate drops below
the target 60 FPS under compositing load.

**Mitigation:**
```
- Use DRM hardware cursor plane if available (check /sys/class/drm/card0*/cursor)
  and fall back to software cursor only when DRM cursor isn't supported
- For software path: only save/restore if the region under the cursor actually
  changed this frame (dirty-rect tracking)
- Consider a hardware sprite via libdrm — one ioctl, zero framebuffer touch
```

### 3. Blocking phases in the main loop

**What:** The main loop is 10 sequential phases. If any phase blocks (PG query in
`Deskbar_LaunchService`, slow `Win_BlitAll` on many windows, `Evdev_Poll` with no data),
the entire UI freezes for that frame.

**When it matters:** Any I/O-bound operation during a frame. Currently the system is
single-threaded, so a 200ms PG query is a 200ms screen freeze.

**Mitigation:**
```
- Phase 1: Keep Evdev_Poll non-blocking (already in place via O_NONBLOCK)
- Phase 4 (EventRouter): All handlers must be async-capable — PG queries
  should park a continuation and resume next frame, never block
- Long-term: Move PG queries to a worker thread, post results back via Ring1
- Short-term: Add a frame budget timer — if a phase exceeds 8ms, log it and
  defer remaining work to next frame
```

### 4. Single-threaded compositor

**What:** `DCompose` and `Win_BlitAll` run on the main thread. The BSP tree,
surface blit, and supersampling all compete with input polling and event dispatch.

**When it matters:** When window count grows past 8, or when surfaces are large
(4K fullscreen blits).

**Mitigation:**
```
- This is on your roadmap (multi-threaded). The natural split is:
  Thread 1: Input (evdev poll → Ring1)
  Thread 2: Logic (EventRouter, WinManager, Auckland)
  Thread 3: Render (DCompose → Framebuffer flip)
- Ring buffers are already structured for this — Ring1 and Ring3 are
  already directional, just need lock-free SPSC queues
- The compositor BSP tree is the main data structure to protect during
  the transition — consider double-buffering the compositor state
```

---

## Tier 2 — Will bite at scale

### 5. 8-window hard limit

**What:** `Deskbar` window list and `WinManager` both cap at 8 windows. The
deskbar only shows entries `wf.1` through `wf.8`, and WinManager's internal
array is fixed-size.

**When it matters:** When users open more than 8 windows (editor + file dialog
+ browser + terminal + calculator + settings + ...).

**Mitigation:**
```
- This is on your roadmap (ordered list). Implementation path:
  1. Convert WinManager.windows[] from fixed array to dynamic list
  2. Convert Deskbar window list to a scrollable region or shrink-to-fit
  3. The action prefix "wf." can stay as "wf." + numeric index
  4. Add Deskbar overflow: if >N windows fit, show "…" with a popup list
```

### 6. No window resize handle on all edges

**What:** `WinInput` currently handles resize from the bottom-right corner only.
Windows can't be resized from bottom, top, left, right, or other corners.

**When it matters:** Laptop trackpads (where bottom-right is awkward to reach),
touch screens, or any scenario where the corner is off-screen.

**Mitigation:**
```
- Add edge hit-test zones in WinInput_HitTest:
  - Top edge: 4px zone for N-resize
  - Bottom edge: 4px zone for S-resize
  - Left/right: 4px zone for E/W-resize
  - All 4 corners: 8×8 zone for diagonal resize
- Each zone maps to a resize mode enum that WinInput_Resize uses
  to adjust x, y, w, h differently per edge
```

### 7. No damaged-region tracking in compositor

**What:** `Win_BlitAll` composites every window every frame, even if nothing
changed. The BSP tree determines occlusion but not change tracking.

**When it matters:** When windows are idle (no animation, no typing, no redraw).
Most frames, 90%+ of the screen is unchanged.

**Mitigation:**
```
- Add a dirty flag per window surface (already present in some form)
- In Win_BlitAll, skip windows with dirty=0 if they're fully occluded
- Short-term: even just skipping fully occluded windows saves BSP tree cost
- Long-term: dirty rectangle per window, blit only changed regions
```

### 8. No crash recovery for child processes

**What:** `IPCBroker` routes actions to external processes. If a child process
crashes, its window remains in WinManager as a zombie — unresponsive, but still
composited and still in the deskbar window list.

**When it matters:** Any time a service binary crashes, which in early-stage
software is "often."

**Mitigation:**
```
- IPCBroker should monitor child process health:
  - waitpid() with WNOHANG each frame
  - If child exits: destroy its window, remove from deskbar, log the event
- Add a "restart" action to Deskbar_LaunchService for crashed services
- Consider a supervisor protocol: child sends heartbeat every N frames,
  broker kills and restarts on timeout
```

### 9. No clipboard / drag-and-drop

**What:** There's no system clipboard. Cut/Copy/Paste in the Editor works within
one Editor instance but can't transfer data between windows or to external programs.

**When it matters:** Any multi-window workflow. A text editor without cross-window
copy-paste is a notepad, not an editor.

**Mitigation:**
```
- Add a system clipboard as a simple string buffer in EventRouter or a
  dedicated Clipboard module
- "edit.cut" and "edit.copy" populate the system clipboard
- "edit.paste" reads from it
- Long-term: support MIME types via a content-type tag on the clipboard buffer
- Drag-and-drop can be built on the same data channel — the dragged object
  references a clipboard entry
```

---

## Tier 3 — Quality of life / hardening

### 10. DebugLog is in-memory only

**What:** `DebugLog` uses a ring buffer in memory. F12 toggles the overlay.
There's no persistence — crash = lose the log.

**Mitigation:** Periodically flush to `/tmp/ailang_display.log` or a PostgreSQL
`display_log` table. Rotate at 1MB. F12 toggle still works on the in-memory buffer;
the file is forensic only.

### 11. No session save/restore

**What:** When the display server exits, all window state is lost. Re-launching
starts from scratch with zero windows.

**Mitigation:** On clean shutdown, serialize `WinManager` state (window positions,
sizes, z-order, associated service) to a JSON blob in PostgreSQL or
`~/.ailang/session.json`. On startup, restore windows and re-bind IPC channels.

### 12. No accessibility hooks

**What:** No screen reader interface, no high-contrast mode toggle, no keyboard
navigation for menus (only mouse hover), no focus indicator for keyboard-only
window switching.

**Mitigation:**
```
- Short-term: Add Alt+Tab window switcher (uses existing WinStack, just needs
  a key binding in InputRouter)
- Add a high_contrast boolean to UITheme that swaps all colors to
  black/white/yellow
- Long-term: Expose Auckland node tree via a text protocol for screen readers
```

### 13. No animation/transition system

**What:** Window open/close, menu open/close, deskbar show/hide are all instant.
No easing, no fade, no slide.

**Mitigation:** Add an `Animation` module with a simple tween queue. Each tween
has a target property (e.g., deskbar y-position), duration in frames, and an
easing function. The main loop advances all active tweens before compositing.
This is low-hanging fruit that dramatically improves perceived quality.

### 14. Font system is vector-sourced but bitmap-cached (no TTF/OTF)

**What:** `Fonts` (v2, Face+Instance model) loads `.vif` vector font files and
uses the TVG engine to rasterize Bezier glyph outlines on demand into a cached
bitmap surface per glyph+size. The pipeline is:

```
VIF font file (Bezier glyph outlines + styles)
    → TVG_Parse (zero-copy from file buffer)
    → TVG_Render (rasterize at requested pixel size → BGRA surface)
    → Cache in Instance glyph surface table (512 slots)
    → Surface_BlitAlpha (blit to target on draw)
```

This IS a vector font engine. What's missing: TTF/OTF support (an abandoned
`FontTTF.ailang` exists in `Librarys/deprecated/`), hinting at small sizes,
subpixel AA, and font fallback chains. Kerning pair data is defined in the
VIF spec but not yet consumed by the layout engine.

**When it matters:** Non-English text (CJK, Arabic, Cyrillic) requires glyph
coverage beyond the current DejaVuSans.vif + AlteixSans.vif fonts.
TTF/OTF support would unlock the entire open-source font ecosystem.

**Mitigation:**
```
- Short-term: Convert additional fonts to .vif format using a 
  TTF→VIF conversion tool (DejaVu covers Latin/Greek/Cyrillic already)
- The VIF entry types already define KERN_PAIR (type 6) — implement
  kerning in VInst_DrawString for better text quality
- Long-term: A TTF/OTF parser that extracts glyph outlines and feeds
  them into the existing TVG rasterizer, reusing the glyph cache
- The existing VIF/TVG path stays as the fast/hardened code path
```

### 15. No compositor vsync beyond page flip

**What:** `Framebuffer` does double-buffer page flip, which gives tear-free
display if the driver supports it. But there's no DRM vblank synchronization
or adaptive sync. Frame pacing is purely CPU-timed.

**Mitigation:** Check for DRM vblank events via `/sys/class/drm/card0` properties.
If available, block flip until vblank. If not, the current CPU timer is
adequate for most use cases.

---

## Tier 4 — Security hardening (for the encrypted PG-boot roadmap)

### 16. Framebuffer mmap is world-readable while active

**What:** `/dev/fb0` is mmap'd into the display server process. Any process with
sufficient permissions can read `/dev/fb0` and see the screen contents, or worse,
write to it.

**When it matters:** In a security-hardened system where screen contents may
contain decrypted data.

**Mitigation:**
```
- After the encrypted boot chain lands: run display server as a dedicated
  user with exclusive /dev/fb0 access (udev rule)
- Consider DRM render nodes (/dev/dri/renderD*) which isolate access
  per-process — no other process can snoop the framebuffer
- The encrypted mmap separation from kernel memory (already on roadmap)
  covers the other side of this
```

### 17. IPC channels are unencrypted

**What:** `IPCBroker` uses Unix domain sockets or message queues with no
transport-layer encryption. Child process communication is plaintext.

**When it matters:** In the encrypted-PG world where all inter-process
communication must be encrypted.

**Mitigation:**
```
- Wrap IPC message payloads in a simple symmetric cipher (the rolling-key
  system from the encrypted init chain)
- Or use abstract socket namespace + per-connection ephemeral keys
- The MessageTranslate layer can handle encrypt/decrypt as a pass-through
```

### 18. PostgreSQL connection credentials

**What:** PG connection string is presumably in a config file or hardcoded.
In the encrypted-boot scenario, PG credentials must never appear in plaintext.

**Mitigation:**
```
- PG connection should use Unix socket with peer authentication
  (no password on disk) where possible
- If TCP is needed: credentials come from the encrypted init ramdisk,
  passed via environment variable that's cleared after connect
```

---

## Summary matrix

| # | Pain Point | Impact | Effort | When To Fix |
|---|-----------|--------|--------|-------------|
| 1 | No PG fallback | High | Medium | Before anyone else runs this |
| 2 | Software cursor at 4K | Medium | Low | Before 4K testing |
| 3 | Blocking main loop | High | High | During multi-thread work |
| 4 | Single-threaded compositor | High | High | Already on roadmap |
| 5 | 8-window limit | Medium | Low | Already on roadmap |
| 6 | Single-corner resize | Low | Low | Anytime |
| 7 | No damaged-region tracking | Medium | Medium | After multi-thread work |
| 8 | No crash recovery | Medium | Medium | Before external services ship |
| 9 | No system clipboard | Medium | Low | Before multi-window workflow |
| 10 | DebugLog in-memory only | Low | Low | Anytime |
| 11 | No session save/restore | Low | Low | Anytime |
| 12 | No accessibility hooks | Low | Medium | Defer |
| 13 | No animation system | Low | Low | Anytime (big UX win) |
| 14 | Bitmap-only fonts | Medium | High | Already on roadmap (TVG) |
| 15 | No DRM vblank sync | Low | Low | Anytime |
| 16 | FB mmap world-readable | Medium | Low | Before encrypted boot ships |
| 17 | IPC unencrypted | High | Medium | During encrypted IPC work |
| 18 | PG creds on disk | High | Low | During encrypted boot work |

---

## What's NOT a pain point (despite first impressions)

**The import tangle.** 750KB binary, 10-second compile. At that scale, the
engineering cost of dependency-injection layering exceeds any build-time savings.
Don't fix what isn't broken.

**HTML UI.** It's a pragmatic choice that moves the complexity to a known
problem domain (parsing HTML). The ~1100-line `HTMLParse` is modest for what it
does. It's not a web browser — it's a UI description format that happens to
use HTML syntax. That's fine.

**Single-threaded for now.** The ring buffer architecture is already structured
for multi-producer-single-consumer. The transition to multi-threaded is
unlocking existing design, not rewriting from scratch.

**PostgreSQL as systemd.** This is an architectural choice with security
properties (encrypted file tree in PG, rolling keys, encrypted IPC). The
trade-offs are understood and intentional. The SQLite backup recommendation
is purely an availability concern, not a critique of the PG-centric design.
