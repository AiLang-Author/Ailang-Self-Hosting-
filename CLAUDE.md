# Project Memory

## Display Server Crash Fix (2026-04-22)

### Bug: Crash on mouse-down on toolbar menu buttons (File/Edit/Help)

**Root cause:** `Win_BlitOne`, `Win_BlitClamped`, and `Win_DrawBorderFB` in `Library.WinRender.ailang` had zero framebuffer bounds checking. Raw byte offsets computed with negative coords or overflow past screen edges caused writes outside the framebuffer buffer — segfault.

**Trigger:** Clicking a toolbar button calls `Win_Focus` -> `Win_BringToFront` (z-order shuffle) -> sets dirty -> `Win_BlitAll` runs. Toolbar blit at `y = Win_GetY(win) - toolbar_h` goes negative if window Y < 24px. Same for tab bar header, border, and menu overlay at any screen edge.

**Fix applied:** Added full 4-edge framebuffer clamping to all three functions in `Library.WinRender.ailang`:
- `Win_BlitOne` (line ~87): negative dst_x/dst_y skip source rows/cols; right/bottom overflow reduces draw dims; early-out if nothing visible.
- `Win_BlitClamped` (line ~158): same clamping added on top of existing clip logic.
- `Win_DrawBorderFB` (line ~228): per-pixel x/y bounds checks against FB_GetWidth/FB_GetHeight.

### Architecture Notes

- AKSlot system: 16 slots (0=main), `AKSlot_SwapIn`/`SwapOut` for context switching. 2-deep stack only (current/previous).
- Deskbar uses OLD `AKCtx_SwapIn` (manual save/restore) — not AKSlot. Mismatch but works since they're sequential in single-threaded loop.
- Deskbar manual save does NOT save `AKEvent.dirty_count` — minor state leak, not crash-causing.
- Toolbar actions fire on UP (not DOWN). Action string -> EventRouter queue -> `EventRouter_Drain` in main loop dispatches.
- `Menu_Show` allocates AKSlot, swaps in, builds tree, renders, swaps out. Surface stored in MenuState. `Menu_Blit` called from `Win_BlitAll`.
- Main loop: Evdev_Poll -> DrainInput -> AK_DrawDirty -> Win_RenderDirty -> EventRouter_Drain -> DebugLog_Render -> Win_BlitAll -> sleep(16ms).
- Bare `AK_EventMouse` calls on main context (lines 944, 1004, 1041 of SysDisplay) are harmless — main root==-1, hit test returns -1, event handlers bail early.
