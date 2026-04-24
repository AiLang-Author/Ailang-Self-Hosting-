# Project Memory

## Architecture Notes

- **AKContext system (refactored 2026-04-22):** Replaced global AKTree/AKExtraTable/AKEvent state with explicit `LinkagePool.AKContext` handles. Each context (main window, toolbar, deskbar, menu, dialog) owns its own node buffer, extra table, and event state. No more slot swapping or global corruption. `AK_CreateContext()` allocates, all AK_* functions take `ctx` as first param.
- Toolbar actions fire on UP (not DOWN). Action string -> EventRouter queue -> `EventRouter_Drain` in main loop dispatches.
- `Menu_Show` creates its own AKContext, builds tree, renders to surface, destroys context. Surface stored in MenuState. `Menu_Blit` called from `Win_BlitAll`.
- Main loop: Evdev_Poll -> DrainInput -> AK_DrawDirty -> Win_RenderDirty -> EventRouter_Drain -> DebugLog_Render -> Win_BlitAll -> sleep(16ms).
- Deskbar has its own AKContext stored in `DeskbarState.ak_ctx`. No global swap needed.
- Each window toolbar has its own AKContext stored via `WinMgr_SetToolbarCtx(idx, ctx)`.

### DebugLog_Push Instrumentation

**Scope:** 475 `DebugLog_Push` calls across 16 library files. Every `Function.*` and `SubRoutine.*` has an entry tag. All risky calls have before/after checkpoint tags.

**Config:** `DebugLogConst.MAX_ENTRIES` = 256. Toggle with `DebugLog_Toggle()`, rendered by `DebugLog_Render()`.

**Tag convention:** `"<module>.<fn>"` or `"<module>.<fn>.X"`, max 9 chars. Second arg = string length.

## Completed: Canvas Background Color on Resize (2026-04-23)

Expanded canvas area showed dark green (`WinColor.WINDOW = 0xFF1A2A1A`) instead of matching the window's actual background. Fix: sample the background color from the old content surface's top-left pixel before filling the new surface. Expanded area now matches the window's original background color.

## Completed: Preserve Canvas Content on Window Resize (2026-04-23)

Canvas drawing was lost on resize because `Win_UpdateResize` in `Library.WinInput.ailang` created a new content surface filled with solid background but never copied the old surface content. Fix: `Surface_BlitOpaque(new_content, old_content, 0, 0)` after background fill, before destroying old surface. Old content is preserved at top-left; new area gets background fill.

## Completed: Toolbar Re-render on Window Resize (2026-04-23)

Text disappeared from toolbars during window resize because `Win_UpdateResize` in `Library.WinInput.ailang` recreated the toolbar surface (blank solid fill) but never re-rendered the Auckland tree into it. There was a `// TODO: Phase C` comment where the call should have been. Fix: call `Win_RedrawToolbar(idx)` after surface recreation — this re-solves layout for new dimensions and draws text/buttons into the new surface.

## Completed: TextRegion Pool Exhaustion Fix (2026-04-23)

Text disappeared on 2nd/3rd windows because the global TextRegion pool (32 slots) was a bump allocator that never freed handles. Each `AK_DestroyContext` (menus, dialogs) and `AK_ResetContext` (deskbar refresh) leaked all TR_HANDLEs — once 32 slots consumed, `TextRegion_Create` returned -1 and text rendering stopped.

**Fix:**
- `Library.TextRegion.ailang`: Added free stack (`TRState.free_stack`, `TRState.free_top`). `TextRegion_Create` checks free stack before bumping count. New `TextRegion_Free(handle)` pushes handle onto free stack. Pool size increased 32 → 256 for headroom.
- `Library.Auckland.ailang`: New `AK_FreeContextTR(ctx)` iterates a context's extra table and calls `TextRegion_Free` for each valid `TR_HANDLE`. Called from both `AK_DestroyContext` and `AK_ResetContext` **before** buffer zeroing/dealloc.

**Result:** TR handles are recycled when contexts are destroyed or reset. Pool no longer leaks.

## Completed: HBOX MIN_W Layout Fix (2026-04-23)

Fixed deskbar rendering corruption (duplicated glyphs, overlapping zones, clipped right edge, invisible separators). Root cause: `AK_LayoutNode` HBOX pass and `AK_MeasureNode` used `AKF.WIDTH` for base width calculation, but deskbar buttons only set `AKF.MIN_W`. All buttons contributed 0 to space distribution, so the center GROW zone absorbed the full width and left/right zones collapsed to 0.

**Fix:** Added `MIN_W` fallback in 3 sites in `Library.Auckland.ailang`:
- `AK_MeasureNode` HBOX child width accumulation (+ symmetric MIN_H for VBOX)
- `AK_LayoutNode` HBOX first pass (total_base accumulation)
- `AK_LayoutNode` HBOX second pass (per-child base_w for positioning)

When `WIDTH=0` and `MIN_W>0`, MIN_W is used as the effective base width. This is correct CSS-like behavior — MIN_W should be the floor for layout space reservation.

## Completed: Framebuffer Bounds Checking (2026-04-22)

Added full 4-edge framebuffer clamping to `Win_BlitOne`, `Win_BlitClamped`, and `Win_DrawBorderFB` in `Library.WinRender.ailang`. Prevents segfaults when windows are partially off-screen.

## Completed: AKContext Refactor (2026-04-22)

Replaced global AKTree/AKExtraTable/AKEvent with explicit `LinkagePool.AKContext` handles. Fixed toolbar menu freeze caused by global state corruption during slot swapping. All AK_* functions now take `ctx` as first parameter. Commit: `1f65c03`.

## Completed: UIScale DPI System (2026-04-23)

- `Librarys/Library.UIConfig.ailang` — key=value config parser, supports `0x` hex, 128-entry max
- `Librarys/Library.UIScale.ailang` — DPI-aware dimension scaling, reads from `config/ui.cfg`
- `config/ui.cfg` — central config file for dimensions and colors
- All dimension constants across WinToolbar, Deskbar, WinRender, Menu, FileDialog, Dialog read from `UIScale.*`

## Completed: SVG Tooling + Widget Icons (2026-04-23)

- `tools/svg2tvg.py` — extended for widget SVGs (gradients, transforms, complex paths)
- `tools/pack_widget_vif.py` — batch packs TVG files into VIF container
- 63 Silver system atom SVGs converted to TVG and packed into `icons/silver_atoms.vif`
- Fixed stroke path reversal bug and gradient coordinate mismatch in SVG→TVG converter

## Completed: UI Theming System (2026-04-23)

Centralized all hardcoded color values into a single config-driven theme system.

### Files

- **`Librarys/Library.UITheme.ailang`** (NEW) — `FixedPool.Theme` with 42 color fields (all `CanChange=True`), `UITheme_Init()` loads from `config/ui.cfg` with fallback defaults
- **`config/ui.cfg`** — extended with 42 ARGB hex color entries (all optional, defaults match previous hardcoded values)

### Init Sequence (in Library.SysDisplay.ailang)

```
UIConfig_Load("config/ui.cfg")
UITheme_Init()          // loads Theme.* from config
UIScale_Init(w, h)      // loads UIScale.* from config
PaneDecorator_ScaleInit()
PaneDecorator_ThemeInit()  // copies Theme.* → WinColor.*
```

### Color Migration Summary

| File | Sites | What changed |
|------|-------|-------------|
| Library.PaneDecorator.ailang | 9 | WinColor fields CanChange=True, bridge function copies Theme→WinColor |
| Library.WinToolbar.ailang | 6 | toolbar_bg, text_secondary, toolbar_close_bg/fg |
| Library.Deskbar.ailang | 8 | deskbar_bg, btn_bg/fg, btn2_bg/fg (hotzone checkerboard raw bytes kept) |
| Library.WinRender.ailang | 4 | tabbar_bg, tab_active_bg, tab_icon, tab_text |
| Library.Menu.ailang | 4 | menu_bg/fg/sep via MenuConst bridge, menu_border |
| Library.Auckland.ailang | 7 | ak_sep, ak_btn_bg/fg, ak_btn_border/hover/pressed, text_disabled |
| Library.FileDialog.ailang | 7 | fd_path_text, fd_list_bg/border, fd_sep, fd_dir/file/empty_text |

### Theme Color Groups (FixedPool.Theme keys)

- Desktop/window: `desktop_bg`, `window_bg`, `dialog_bg`, `panel_bg`, `terminal_bg`
- Chrome: `border`, `header_color`
- Text: `text_fg`, `text_bg`, `text_secondary`, `text_disabled`, `text_light`
- Toolbar: `toolbar_bg`, `toolbar_close_bg`, `toolbar_close_fg`
- Deskbar: `deskbar_bg`, `deskbar_btn_bg/fg`, `deskbar_btn2_bg/fg`, `deskbar_hot_fg/bg`
- Tabs: `tabbar_bg`, `tab_active_bg`, `tab_icon`, `tab_text`
- Menu: `menu_bg`, `menu_fg`, `menu_sep`, `menu_border`
- Auckland: `ak_sep`, `ak_btn_bg/fg`, `ak_btn_border/hover/pressed`
- FileDialog: `fd_path_text`, `fd_list_bg/border`, `fd_sep`, `fd_dir/file/empty_text`
- Debug: `debug_bg`

### Important Notes

- Dynamic color modifications (hover lighten +30, press darken -30, disabled grayscale) in Auckland button rendering stay as runtime computation — only the base/fallback colors are themed
- Deskbar hotzone checkerboard (raw SetByte for BGRA channels) not themed — would need color unpacking utility
- `UIConfig MAX_ENTRIES` = 128 (25 dimension + 42 color = 67 used)

**Last commit:** `b5b613a` on `ak-context-refactor` — all theming work saved

## In Progress: Deskbar Rewrite (2026-04-23)

Full plan at: `.claude/plans/transient-sauteeing-pike.md`

### Vision

Rewrite placeholder deskbar into full system bar with 3 zones:
- **Left**: App launchers from PostgreSQL `services` table
- **Center**: Live window list (click to focus, auto-refreshes on create/close/focus)
- **Right**: System tray (user label, About dialog)

PostgreSQL is the backbone — `services` table already exists with binary_path/args/enabled/priority. Convention: `binary_path = "internal:action.name"` fires EventRouter action, otherwise fork/exec.

### Phase Plan

1. **Phase 1**: Three-zone layout + window list + `AK_ResetContext` + refresh triggers
2. **Phase 2**: PostgreSQL service loading + dynamic launchers + `svc.N` routing + `display_name` column + default service seeds
3. **Phase 3**: About dialog (new `Library.AboutDialog.ailang`)
4. **Phase 4**: Fork/exec service launching (SystemCall 57/59)

### Key Technical Decisions

- **`AK_ResetContext(ctx)`** needed in Library.Auckland.ailang — zeros node+extra buffers without dealloc/realloc. Critical for tree rebuild on window list refresh.
- **Refresh trigger**: `DeskbarState.needs_refresh = 1` set in `Win_Create`/`Win_Close`/`Win_Focus`, checked in main loop after `EventRouter_Drain`
- **Pre-allocated action strings**: `"wf.1"` through `"wf.7"` avoid allocation per refresh (max 8 windows)
- **Service ID actions**: `"svc.N"` where N is services.id from postgres
- **Internal actions**: services with `binary_path = "internal:win.new"` strip prefix and push to EventRouter

### New Theme Colors Added

- `deskbar_win_bg`, `deskbar_win_fg`, `deskbar_win_act_bg`, `deskbar_sep`

### New UIScale Dimensions Added

- `deskbar_win_btn_w` (96px default)

### PostgreSQL Tables Used

- `services` — app registry (name, display_name, binary_path, enabled, priority)
- `service_status` — runtime PID tracking (service_id, pid, state, started_at)
- `users` — user info for system tray label

### Files Modified Per Phase

| Phase | New Files | Modified Files |
|-------|-----------|----------------|
| 1 | — | Auckland, Deskbar, EventRouter, SysDisplay, WinManager, UITheme, UIScale, ui.cfg |
| 2 | — | Deskbar, EventRouter, SysDisplay |
| 3 | Library.AboutDialog.ailang | EventRouter, SysDisplay |
| 4 | — | Deskbar |

**Last commit:** `826e151` on `ak-context-refactor` — all prior work saved

## Completed: CLD Fix for REP MOVSB/STOSB (2026-04-23)

`MemoryCopy` and `MemorySet` emitted `REP MOVSB` / `REP STOSB` without a preceding `CLD` instruction. If the CPU direction flag (DF) was set by anything earlier in execution, these instructions copy backwards, corrupting memory. Caused hard crash/lockup when clicking NEW in deskbar (window creation triggers `FB_FlipFast` → `MemoryCopy` on multi-MB framebuffer).

**Root cause:** `CompileMem_MemoryCopy` and `CompileMem_MemorySet` in `Library.CCompileMem.ailang` emitted `0xF3 0xA4` (REP MOVSB) and `0xF3 0xAA` (REP STOSB) without `0xFC` (CLD) first. The `X86_Cld` emitter existed in `Library.CEmitX86Sys.ailang` but had no arch-dispatch wrapper and was never called.

**Fix (2 files):**
- `Librarys/Compiler/CodeEmit/Library.CEmitCoreArch.ailang` — Added `Emit_Cld` wrapper function that calls `X86_Cld()` (emits `0xFC`)
- `Librarys/Compiler/Compile/Modules/Library.CCompileMem.ailang` — Added `Emit_Cld()` before `Emit_RepMovsb()` in `CompileMem_MemoryCopy` and before `Emit_RepStosb()` in `CompileMem_MemorySet`

**Validation:**
- 3-generation bootstrap: all byte-identical (`c8f06ee8...`)
- 57/57 CoreUtils build pass
- 86/86 smoke tests pass (1 pre-existing `logname` env failure)
- grep (uses `memchar` → `MemoryCopy`) passes all tests

**Note:** `RepMovsq`, `RepStosq`, `RepeCmpsb`, `RepneScasb` exist in emit layer but are never called from any compile module — no fix needed there.

**Commit:** `ce0c420` on `ak-context-refactor`. `ailang.x` updated to gen3 with fix.

## Completed: Register Save/Restore for REP MOVSB/STOSB (2026-04-23)

`REP MOVSB` destroys RSI, RDI, RCX. `REP STOSB` destroys RDI, RCX. `CompileMem_MemoryCopy` and `CompileMem_MemorySet` emitted these inline without saving/restoring the clobbered registers. If the register allocator placed any loop variable in RSI/RDI/RCX, the next loop iteration used garbage values — computing wild pointers into unmapped memory → hard lockup.

**Symptom:** Site 3 MemoryCopy rollout (`Win_BlitOne`/`Win_BlitClamped` row loop) caused system lockup. Sites 1-2 worked by luck (register allocator didn't place loop vars in clobbered regs, or no loop at all).

**Fix (1 file):**
- `Librarys/Compiler/Compile/Modules/Library.CCompileMem.ailang`:
  - `CompileMem_MemoryCopy`: Added `Emit_PushRsi/Rdi/Rcx` before arg compilation, `Emit_PopRcx/Rdi/Rsi` after `REP MOVSB`
  - `CompileMem_MemorySet`: Added `Emit_PushRdi/Rcx` before arg compilation, `Emit_PopRcx/Rdi` after `REP STOSB`

**Validation:**
- 3-generation bootstrap: all byte-identical (`bc74bd2b...`)
- 57/57 CoreUtils build pass
- 86/86 smoke tests pass (1 pre-existing `logname` env failure)
- grep (uses `memchar` → `MemoryCopy`) passes all tests

**Commit:** on `ak-context-refactor`. `ailang.x` to be updated to gen3 with fix.

## In Progress: MemoryCopy Rollout (2026-04-23)

Incrementally replacing byte-by-byte copy loops with `MemoryCopy` across 5 sites. Going one at a time to isolate any issues. Depend on CLD fix (`ce0c420`) + register save/restore fix.

| # | File | Function | Status |
|---|------|----------|--------|
| 1 | Library.Framebuffer.ailang | `FB_Flip`, `FB_FlipFast` | Done (commit `f311746`) |
| 2 | Library.SurfaceBlit.ailang | `Surface_BlitOpaque` | Done (commit `8bb9323`) |
| 3 | Library.WinRender.ailang | `Win_BlitOne`, `Win_BlitClamped` | Reverted to byte-by-byte (MemoryCopy itself works; crash was VInst_DrawString 7-arg bug) |
| 4 | Library.Deskbar.ailang | `Deskbar_Draw` | Done (commit `400a3d0`, uses MemoryCopy in row loop) |
| 5 | Library.DDrawPixel.ailang | `Draw_Pix_FillRect` | Pending (different — `DPix_PutPixel` → `StoreValue`, not MemoryCopy) |

**Site 2 detail (SurfaceBlit):** Replaced 4-channel `GetByte`/`SetByte` inner loop (per-pixel BGRA copy) with per-row `MemoryCopy(dr_ptr, sr_ptr, row_bytes)`. Also folded `sx_start`/`dst_x` pixel offsets into the row pointer calculation (matching the original c99bee4 approach).

**Site 3 detail (WinRender):** Original commit `3c21636` crashed (lockup) even after register save/restore fix (`4917789`). Root cause: deeply nested address expressions (4 levels of `Add(Multiply(Add(...)))`) triggered the peephole optimizer (`Library.CCompilerOptimizer.ailang`) which can mishandle complex recursive expression trees. Fix: flattened all address computations into intermediate local variables (max 2-level nesting), matching the proven `Surface_BlitOpaque` pattern. Each loop iteration now computes `sry`, `dry`, `sr_off`, `dr_off`, `src_row`, `dst_row` as separate flat assignments before calling `MemoryCopy(dst_row, src_row, row_bytes)`.

**Optimizer note:** The peephole optimizer has a potential bug — `Multiply(1, x)` where left operand is literal 1 returns without emitting `MOV RAX, RBX`, leaving RAX=1 instead of x (line ~199 of CCompilerOptimizer.ailang). Not the cause of this lockup but a real latent bug.

## Completed: MemoryCopy in FB_Flip/FB_FlipFast (2026-04-23)

Replaced byte-by-byte and 8-byte-chunk framebuffer copy loops in `FB_Flip` and `FB_FlipFast` (`Library.Framebuffer.ailang`) with single `MemoryCopy(FB.fb_ptr, FB.back_buffer, FB.size)` calls. This was commit `f311746` — a conservative re-application of the performance optimization after the full rollout in `c99bee4` was reverted (`16e1075`). Only the framebuffer flip functions were changed; SurfaceBlit/WinRender/DDrawPixel/Deskbar kept their byte-by-byte loops.

**Depends on:** CLD fix above (`ce0c420`) — without CLD, MemoryCopy can corrupt memory.

## Completed: Screenshot PPM Support (2026-04-23)

Added PPM (P6) output mode to `Library.Screenshot.ailang` alongside existing BMP. PPM chosen because Claude Code's Read tool segfaults on BMP files but handles PNG/JPG/PPM reliably.

### Files

- **`Librarys/Library.Screenshot.ailang`** (NEW) — `Screenshot_Save()` (BMP) + `Screenshot_SavePPM()` (PPM P6) + `SS_WriteDecimal()` helper
- **`Librarys/Library.EventRouter.ailang`** — `sys.screenshot` action now calls both `Screenshot_SavePPM()` then `Screenshot_Save()`

### Output Files

- `/tmp/screenshot.ppm` — PPM P6 binary (RGB, top-to-bottom, no padding, no compression). Use this for Claude Code viewing.
- `/tmp/screenshot.bmp` — 24-bit BMP (BGR, bottom-up, padded). Fallback for standard image viewers.

### PPM Format Notes

- Header: ASCII `"P6\n{width} {height}\n255\n"` followed by raw RGB bytes
- Pixel conversion: BGRA (framebuffer) → RGB (swap B↔R, drop alpha)
- Rows: top-to-bottom (no reversal needed unlike BMP)
- No row padding required
- To convert for external use: `convert /tmp/screenshot.ppm /tmp/screenshot.png`

## Completed: Stack Leak Fix for >6-Arg Function Calls (2026-04-24)

`CompileFunc_UserCall` in `Library.CCompileFunc.ailang` had a stack leak for function calls with more than 6 arguments. SysV AMD64 passes args 1-6 in registers (RDI, RSI, RDX, RCX, R8, R9); args 7+ go on the stack and the **caller** must clean them up. The compiler pushed all N args, popped 6 into registers, but never cleaned up the remaining (N-6) stack-passed args after the call returned. Each >6-arg call leaked `(N-6)*8` bytes off the caller's stack frame.

**Symptom:** SIGSEGV (`si_addr=0x98`) after returning from functions containing >6-arg calls. The leaked stack bytes shifted where the epilogue's `POP R12; POP RBX` read from, filling R12 (used for RSP preservation at call sites) with garbage. Next function call did `MOV R12, RSP; AND RSP, -16; CALL` — the CALL tried to push a return address to the corrupt RSP (~0xA0) → segfault.

**Root cause site:** `CompileFunc_UserCall` in `Librarys/Compiler/Compile/Modules/Library.CCompileFunc.ailang:669-671`. After `MOV RSP, R12` restore, no cleanup of stack-passed arguments.

**Fix:** Added `ADD RSP, (arg_count - 6) * 8` after the `MOV RSP, R12` restore when `arg_count > 6`.

**Affected call sites across codebase (examples):**
- `SystemCall(9, 0, size, 3, 34, -1, 0)` — 7 args (mmap, in Arena, Framebuffer, ThreadTrampoline, compiler import)
- `VInst_DrawString(inst, surf, ptr, len, x, y, color)` — 7 args (Fonts, WinRender)
- `Item_RegisterFull(...)` — 12 args (Item system)
- `Char_SetLevelGains(...)` — 9 args (Character system, 45+ call sites)
- `Enc_RegisterZone(...)` — 8 args (Encounter system)

**Also fixed:** `TestCode/test_offscreen_render.ailang` passed 8 args to `Menu_AddItem` (which takes 6) — removed the extra `iw, ih` arguments.

**Validation:**
- 3-generation bootstrap: all byte-identical (`6c84e377...`)
- 86/86 smoke tests pass (1 pre-existing `logname` env failure)
- `test_offscreen_render.x` runs all 4 render tests cleanly (toolbar, menu, deskbar, file dialog)

**Commit:** on `ak-context-refactor`. `ailang.x` updated to gen3 with fix.

### Test Program: test_offscreen_render.ailang

Build & run (no framebuffer needed):
```
./ailang.x TestCode/test_offscreen_render.ailang test_offscreen.x
./test_offscreen.x
# Check /tmp/ak_*.ppm for rendered output
```

Tests: FileDialog (real Dialog_Create/Win_Create/FD_BuildTree chain), Deskbar, Toolbar, Menu. Dumps surfaces to PPM. Requires PostgreSQL (ailang_system db, user bob).

## Completed: VInst_DrawString 7-Arg Fix (2026-04-24)

`VInst_DrawString` was the **only function in the entire codebase with 7 parameters**, violating the compiler's deliberate 6-register limit (no spill by design). The 7th arg (`color`) went on the stack, which the compiler's `CompileFunc_UserCall` cannot handle correctly — `AND RSP, -16` alignment mispositions stack-passed arguments before `CALL`, so the callee reads garbage for arg 7+.

**Symptom:** Desktop renders one frame then locks up. Every `Win_DrawTabBar` call invoked `VInst_DrawString(inst, surf, title_ptr, title_len, text_x, text_y, text_color)` with 7 args, corrupting the stack on every window tab render.

**Root cause:** `VInst_DrawString` in `Library.Fonts.ailang` had 7 `Input:` lines. The compiler's 6-arg limit is intentional (enforced by `analyzer.x` arity checker). The >6-arg codegen path was never designed for production use.

**Fix:** Moved `color` from a 7th parameter to `FontState.draw_color` (FixedPool global). Callers set the global before calling.

**Files changed (2):**
- `Librarys/Library.Fonts.ailang`:
  - Added `"draw_color": Initialize=0, CanChange=True` to `FixedPool.FontState`
  - `VInst_DrawString`: removed `Input: color: Integer` (7→6 params), body reads `color = FontState.draw_color`
  - `VFont_DrawString` wrapper: sets `FontState.draw_color = color` before calling `VInst_DrawString`
  - Removed unused `em` variable in `VInst_DrawString`
- `Librarys/Library.WinRender.ailang`:
  - `Win_DrawTabBar` line 419: `FontState.draw_color = Theme.tab_text` then `VInst_DrawString(inst, surf, title_ptr, title_len, text_x, text_y)`

**Also in this working tree (uncommitted):**
- `Win_BlitOne`/`Win_BlitClamped` reverted from MemoryCopy back to byte-by-byte (MemoryCopy itself is correct; the lockup was always this 7-arg bug, not MemoryCopy)
- `FB_FontDefineChar` refactored from 10 args to 2 args (char + packed 64-bit int) — eliminates another >6-arg call site

**How the crash was found:**
1. `./analyzer.x Main.ailang` reported `Excessive arity: 1` → `VInst_DrawString` has 7 params
2. Test programs confirmed: 7-arg functions SEGFAULT, identical logic with ≤6 args PASSES
3. `test_offscreen_render.x` (exercises real library pipeline including `VInst_DrawString`) passes with the fix

**Validation:**
- `./analyzer.x Main.ailang` → `Excessive arity: 0`
- 3-generation bootstrap: all byte-identical (`6c84e377...`)
- 86/86 smoke tests pass (1 pre-existing `logname` env failure)
- `test_offscreen_render.x` all 4 render tests pass (toolbar, menu, deskbar, file dialog)
- Main.ailang compiles successfully

**Design note:** The 6-arg limit is deliberate — the compiler targets SysV AMD64's 6 register args (RDI, RSI, RDX, RCX, R8, R9) with no spill. The `analyzer.x` arity checker exists specifically to catch violations. Any function needing >6 values should use FixedPool globals for the extras.

**Test programs created during debugging (in TestCode/):**
- `test_memcopy_blit.ailang` — 6 MemoryCopy isolation tests (all pass)
- `test_deskbar_blit.ailang` — 5 real Surface API + MemoryCopy tests (all pass)
- `test_real_blit.ailang` — 7-arg reproduction case (SEGFAULT, proves >6-arg bug)
- `test_real_blit2.ailang` — same logic with ≤6 args + globals (passes)
- `test_real_blit3.ailang` — exact real-code function signatures (passes)
- `test_blit_loop.ailang` — minimal blit loop (passes)
