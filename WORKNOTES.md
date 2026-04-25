# Work Notes — Display Server AKSlot Migration

## Date: 2026-04-22
## Branch: display-server-akslot-migration

---

## CRASH / HANG INVESTIGATION

### Symptom
System hangs when opening File menu from toolbar. Last output:
```
[AKSlot] allocated slot 2
[SWAP.IN] 0->2 data=<ptr> root=-1 cnt=0
```
Then nothing — no crash message, no further output.

### Call chain that triggers it
1. Toolbar button UP fires `menu:file` -> pushed to EventRouter queue
2. Main loop: `EventRouter_Drain()` -> `EventRouter_Dispatch()` -> `EventRouter_Internal()`
3. `EventRouter_Internal` matches `"menu:file"` -> calls `Menu_Show(0, source_win)`
4. `Menu_Show` allocates AKSlot 2, calls `AKSlot_SwapIn(2)`
5. **HANGS** somewhere between SwapIn and tree building

### Diagnostic prints added (Library.Menu.ailang)
Added prints at lines 248-261, 272, 280-282, 295 to narrow down:
- After SwapIn: prints AKTree.data/count/root from loaded slot
- Before/after AK_CreateNode(AKTag.PANEL)
- After AK_SetRoot
- After builder dispatch (Menu_BuildFile)
- Before Surface_Create

### Hypotheses (ranked)
1. **Silent segfault** — AK_CreateNode writes to slot 2's buffer via AKTree.data, first StoreValue crashes if memory not properly mapped
2. **Font system interaction** — Menu_Render calls VFont_RasterAll(14) while fonts may not be ready for that size in this context
3. **AKExtraTable.data invalid** — slot 2's extra buffer might not be properly initialized

### Key files for the hang
- `Library.Menu.ailang:246` — AKSlot_SwapIn call
- `Library.Menu.ailang:258` — AK_CreateNode(AKTag.PANEL) — probable crash site
- `Library.AKSlot.ailang:244-298` — SwapIn implementation
- `Library.AKSlot.ailang:120-186` — Alloc implementation
- `Library.Auckland.ailang:517-584` — AK_CreateNode implementation

---

## CHANGES MADE THIS SESSION

### 1. Diagnostic prints in Menu_Show (Library.Menu.ailang)
- 6 print statements added between SwapIn and render to pinpoint hang location
- Will show exactly which line freezes

### 2. app.quit action + File > Quit menu item
- **Library.Menu.ailang** `Menu_BuildFile`: Added separator + "Quit" item (action="app.quit", len=8)
- **Library.EventRouter.ailang** `EventRouter_Internal` (around line 318): New handler:
  - Matches `"app.quit"`
  - Calls `Menu_Close()`
  - Sets `SysDisplayState.running = 0`
  - Main loop exits cleanly

### 3. Full SysDisplay_Shutdown (Library.SysDisplay.ailang lines 470-549)
Cleanup order:
1. `Menu_Close()` — free menu surface + AKSlot
2. Deskbar cleanup — `AKCtx_Destroy` + `Surface_Destroy`
3. `Win_Close()` all windows backwards (index shifting safe)
4. Sweep AKSlots 1-15, `AKSlot_Free` any still IN_USE
5. `Deallocate` AKSlot table
6. `AK_Shutdown()` — main tree buffers
7. `Deallocate` EventRouter queue buffer
8. `Deallocate` DebugLog ring buffer
9. `Surface_Destroy` desktop surface
10. Hardware teardown (evdev, cursor, DB, compositor, FB, TTY)

### 4. Bug fix: Win_Close toolbar slot leak (Library.WinManager.ailang ~line 491)
- **Was**: `AKCtx_Destroy(toolbar_ctx)` — treated AKSlot index (1-15) as memory address = crash/corruption
- **Now**: `AKSlot_Free(toolbar_slot)` — properly frees the AKSlot

---

## FILES MODIFIED (unstaged)
- `Librarys/Library.Menu.ailang` — diagnostic prints + Quit item
- `Librarys/Library.EventRouter.ailang` — app.quit handler
- `Librarys/Library.SysDisplay.ailang` — full shutdown
- `Librarys/Library.WinManager.ailang` — Win_Close AKSlot fix

---

## ARCHITECTURE NOTES (for quick re-orientation)

### AKSlot system (Library.AKSlot.ailang)
- 16 slots (0=main, 1-15 allocatable), 128 bytes each
- `AKSlot_SwapIn(slot)`: saves globals to current slot, loads target
- `AKSlot_SwapOut()`: saves globals to current, restores previous
- Tracks `AKSlotState.current` and `AKSlotState.previous` (2-deep stack only)
- Fields per slot: DATA, COUNT, ROOT, SCALE_NUM/DEN, DESIGN_W/H, CANVAS, EXTRA_DATA/COUNT, HOVER/PRESSED/FOCUS, ACTION_CB, DIRTY_COUNT, IN_USE

### Main loop (SysDisplay_Run, Library.SysDisplay.ailang ~line 988)
```
WhileLoop running==1:
  clock_gettime -> frame timing
  Evdev_Poll()
  SysDisplay_DrainInput() -> quit flag (ESC)
  AK_DrawDirty() -> main tree
  Win_RenderDirty() -> window content
  EventRouter_Drain() -> action dispatch (SAFE: all contexts restored)
  DebugLog_Render() -> overlay
  Win_BlitAll() -> composite to framebuffer
  nanosleep(16ms)
```

### Event flow for toolbar click
```
MOUSE_DOWN -> Win_ToolbarHitTest -> Win_ToolbarEvent:
  SwapIn(toolbar_slot) -> AK_EventMouse -> redraw if dirty -> capture action on UP -> SwapOut
  -> EventRouter_Push(action, win_idx)

Main loop later: EventRouter_Drain -> EventRouter_Dispatch -> EventRouter_Internal
  -> handles "menu:file", "win.new", "win.close", "app.quit", etc.
```

### Shutdown path
```
ESC key or app.quit -> SysDisplayState.running = 0 -> loop exits
Main.ailang calls SysDisplay_Shutdown()
```
