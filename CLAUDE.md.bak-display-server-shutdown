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

### Bisecting Toolbar Freeze (2026-04-22, in progress)

**Symptom:** Hard freeze (not segfault) when clicking toolbar menu buttons (File/Edit/View/Help). System hangs unrecoverably.

**Bisection strategy:** Disable parts of the click dispatch path to isolate which stage freezes.

**Click dispatch path (full):**
1. `SysDisplay_DrainInput` (SysDisplay:999-1007) → `Win_ToolbarHitTest` → `Win_ToolbarEvent`
2. `Win_ToolbarEvent` (WinToolbar:92-171) → `AKSlot_SwapIn` → `AK_EventMouse` → redraw → `AKSlot_SwapOut` → `EventRouter_Push`
3. `EventRouter_Drain` → `EventRouter_Internal` (EventRouter:348-371) → string-matches `"menu:file/edit/view/help"` → `Menu_Show(id, win)`
4. `Menu_Show` (Menu:219-370) → `AKSlot_Alloc` → `AKSlot_SwapIn` → build tree → `Surface_Create` → render → `AKSlot_SwapOut`

**Bisect results:**
- **Step 1 (Option B):** Commented out `EventRouter_Push` in `Win_ToolbarEvent:160-163`. Toolbar buttons render and highlight normally. **NO CRASH.** → Bug is downstream of toolbar event handler.
- **Step 2 (Option A):** Re-enabled `EventRouter_Push`. Commented out all four `Menu_Show(...)` calls in `EventRouter_Internal:348-371`. Actions still match and print `(NO-OP)`. **NO CRASH.** → Bug is inside `Menu_Show`.
- **Step 3 (bisect Menu_Show):** Re-enabled all four `Menu_Show` calls in EventRouter. Added early-return inside `Menu_Show` (Menu.ailang:~298) AFTER `AKSlot_Alloc` + `AKSlot_SwapIn` + tree build (`Menu_BuildFile/Edit/View/Help`) but BEFORE `Surface_Create` / `Menu_Render` / `MenuState` storage. Early-return does `AKSlot_SwapOut` + `AKSlot_Free` to clean up. **FREEZE.** → Bug is in upper half: `AKSlot_Alloc`, `AKSlot_SwapIn`, tree build, or early `AKSlot_SwapOut`.
- **Step 4 (split upper half):** Moved early-return to Menu.ailang:261 — right after `AKSlot_SwapIn(ak_slot)`, BEFORE any tree build. Does `AKSlot_SwapOut` + `AKSlot_Free` immediately. **NO FREEZE.** → Slot machinery (Alloc/SwapIn/SwapOut/Free) is clean. Bug is in tree build.
- **Step 5 (split tree build):** Early-return at Menu.ailang:~293 — AFTER root PANEL node creation (`AK_CreateNode(AKTag.PANEL)` + 10× `AK_Set` + 3× `AK_ExtraSet` + `AK_SetRoot`) but BEFORE `Menu_BuildFile/Edit/View/Help` dispatch. **NO FREEZE.** → Root node setup (`AK_CreateNode`, `AK_Set`, `AK_ExtraSet`, `AK_SetRoot`) is clean. Bug is in child building.

**Narrowed to:** `Menu_BuildFile/Edit/View/Help` → `Menu_AddItem` → `AK_CreateNode` + `AK_AddChild`. Most likely `AK_AddChild` corrupts a `NEXT_SIBLING` link creating a cycle, which causes `AK_DrawDirtyWalk` (or similar sibling walk) to spin forever on the next main-loop frame. The freeze is NOT inside Menu_Show — it's on the next iteration when the main context walks a corrupted tree.

**Key suspect — `AK_AddChild` (Auckland.ailang:607-633):**
```
- Sets child.PARENT = parent
- If parent has no children: parent.FIRST_CHILD = child
- If parent has children: walks sibling chain to last, sets last.NEXT_SIBLING = child
- Increments parent.CHILD_COUNT
```
This runs in the MENU slot context (menu's node buffer). After `AKSlot_SwapOut`, main globals are restored. The menu slot is then freed. So the menu tree itself can't cause a walk — BUT if AK_AddChild (or AK_CreateNode) accidentally writes to a GLOBAL that isn't slot-scoped, it could corrupt the main tree.

**Also suspect:** `DebugLog_Push` is called from every `AK_Set`, `AK_Get`, `AK_CreateNode`, `AK_AddChild`, `AK_ExtraSet`, `AK_AllocExtra`, `AK_Ptr`, `AK_ExtraPtr` — potentially 200+ calls during a single menu build. If `DebugLog_Push` itself corrupts memory or overflows, that could be the trigger.

**Current state of code:**
- `Library.WinToolbar.ailang:160-163` — `EventRouter_Push` RE-ENABLED (normal).
- `Library.EventRouter.ailang:348-371` — all four `Menu_Show` calls RE-ENABLED (normal).
- `Library.Menu.ailang:~293` — early-return inserted AFTER root PANEL + AK_SetRoot, BEFORE Menu_Build* dispatch.

**Step 6 result — FREEZE.** Even a single `Menu_BuildHelp(root)` (1 "About" button) causes hang. Narrows to: 1× `AK_CreateNode(BUTTON)` + 7× `AK_Set`/`AK_ExtraSet` + 1× `AK_AddChild`.

**Step 7 result — FREEZE.** `AK_AddChild` commented out, but all `AK_Set`/`AK_ExtraSet` still run on the child BUTTON node. Still freezes. → `AK_AddChild` is NOT the sole culprit. Problem is in `AK_CreateNode(AKTag.BUTTON)` or the `AK_Set`/`AK_ExtraSet` calls on the child node.

**Step 8 result — FREEZE.** `AK_CreateNode(AKTag.BUTTON)` alone (no AK_Set/AK_ExtraSet/AK_AddChild) causes hang. Since BUTTON tag >= 10, `AK_CreateNode` calls `AK_AllocExtra` internally. The root PANEL also called `AK_AllocExtra` (step 5, no freeze), so the second extra alloc in the same slot session is suspect.

**Note on AK_AllocExtra:** NOT a malloc — it's a counter bump into a pre-allocated 65536-byte slab (512 slots × 128 bytes). Only ONE caller in entire codebase: `AK_CreateNode:597`. Only called for tags BUTTON(>=10), PANEL(3), WINDOW(1), TABS(5), TAB(6). No AKTag.BOX exists — using GROUP(2) instead (no extra alloc, same 30 AK_Set defaults).

**Step 9 result — FREEZE.** Swapped `AK_CreateNode(AKTag.BUTTON)` to `AK_CreateNode(AKTag.GROUP)` in `Menu_AddItem:70`. GROUP = 2, skips `AK_AllocExtra` entirely. All AK_Set/AK_ExtraSet/AK_AddChild still commented out. **Still freezes.** → `AK_AllocExtra` is NOT the cause. The ~30 default `AK_Set` calls inside `AK_CreateNode` (or just bumping `AKTree.count`) are enough.

**Eliminated by bisection (steps 1-9):**
- EventRouter_Push — clean (step 1)
- Menu_Show call site — clean (step 2)
- AKSlot_Alloc/SwapIn/SwapOut/Free — clean in isolation (step 4)
- Root PANEL node (AK_CreateNode + AK_Set + AK_ExtraSet + AK_SetRoot) — clean (step 5)
- AK_AddChild — not sole cause (step 7)
- AK_Set/AK_ExtraSet on child node — not sole cause (step 8)
- AK_AllocExtra — not the cause (step 9)

**What remains:** The second `AK_CreateNode` call in the menu slot. Node idx=1, writes to `AKTree.data + 256`. Freeze is on next frame in `AK_DrawDirtyWalk`, not inside Menu_Show.

**Investigated and ruled out:**
- `CanChange=True` missing on `AKTree.*` fields: compiler emits fresh memory loads (`MOV RAX, [R15+offset]`) regardless of CanChange. No caching, no inlining. CanChange is parsed but never consulted during codegen.
- Deskbar `AKCtx_SwapIn`/`AKSlot_SwapIn` conflict: both systems touch the same globals (`AKTree.*`, `AKExtraTable.*`, `AKEvent.*`), but Deskbar hotzone is screen-bottom while toolbar is screen-top — they can't fire on the same click event. Sequential in single-threaded loop.
- Bare `AK_EventMouse` calls on main context: harmless — `AKTree.root == -1` triggers early-out in `AK_HitTest`.

**Step 10 (tree dump + block draw):** Instead of early-return, dump tree state at three points:
1. Main tree snapshot from slot 0 BEFORE `Menu_BuildHelp`
2. Menu tree (every node's TAG/PARENT/FIRST_CHILD/NEXT_SIBLING/DIRTY) AFTER build
3. Cross-check: is `slot0.data == AKTree.data`? (same buffer = writes hit main tree)
4. Main tree dump (first 16 nodes) AFTER `AKSlot_SwapOut` restores main context
5. `SysDisplayState.running = 0` to exit cleanly
6. `AK_DrawDirty` commented out in main loop to prevent freeze

**Current state of code:**
- `Library.WinToolbar.ailang:160-163` — `EventRouter_Push` RE-ENABLED (normal).
- `Library.EventRouter.ailang:348-371` — all four `Menu_Show` calls RE-ENABLED (normal).
- `Library.Menu.ailang:70` — `Menu_AddItem` calls `AK_CreateNode(AKTag.GROUP)` (not BUTTON). All `AK_Set`, `AK_ExtraSet`, `AK_AddChild` COMMENTED OUT.
- `Library.Menu.ailang:~289-370` — tree dump + SwapOut + exit instead of early-return.
- `Library.SysDisplay.ailang:~1139` — `AK_DrawDirty` COMMENTED OUT.

**If chat dies:** Resume from this commit. Run the binary, click a toolbar menu button, read stdout for `[DUMP]` lines. Key line: `*** SAME BUFFER ***` means menu writes are landing on the main tree.

### DebugLog_Push Full Instrumentation (2026-04-22)

**Purpose:** Trace a hard freeze on toolbar button click (File/Edit/Help). Ring buffer captures last ~256 tags before hang.

**Scope:** 475 `DebugLog_Push` calls across 16 library files. Every `Function.*` and `SubRoutine.*` has an entry tag. All risky calls (Allocate, Deallocate, Surface_Create, Surface_Destroy, AK_Draw, Draw_Pix_FillRect, AKSlot_SwapIn/SwapOut, AK_EventMouse, CallIndirect, EventRouter_Push) have before/after checkpoint tags.

**Config:** `DebugLogConst.MAX_ENTRIES` = 256 (was 128). Toggle with `DebugLog_Toggle()`, rendered by `DebugLog_Render()`.

**Tag convention:** `"<module>.<fn>"` or `"<module>.<fn>.X"`, max 9 chars. Second arg = string length. `DebugLog_Push` itself is NOT instrumented (infinite recursion).

**Key tags for toolbar click path:**
- `DN` → `sd.drin.1` → `tb.ev` → `tb.ev.1` (AKSlot_SwapIn) → `tb.ev.3` (AK_EventMouse) → `tb.ev.5` (Draw_Pix_FillRect) → `tb.ev.6` (AK_Draw) → `tb.ev.7` (AKSlot_SwapOut) → `tb.ev.9` (EventRouter_Push)
- Menu path: `sd.drin.2` → `mn.evt` → `mn.ev.1` (SwapIn) → `mn.ev.2` (EventMouse) → `mn.ev.4` (SwapOut)
- `MN.show` → `mn.sho.2` (AKSlot_Alloc) → `mn.sho.3` (SwapIn) → `mn.sho.1` (Surface_Create) → `mn.sho.4` (Render) → `mn.sho.6` (SwapOut)
