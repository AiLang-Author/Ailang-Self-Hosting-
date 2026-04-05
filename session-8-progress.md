# Session Handoff — Day 8 (April 5, 2026, Session 2)
# Machine: bob@pop-os (native Linux)
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

---

## What Was Accomplished This Session

### 1. Auckland Event Routing — COMPLETE
- **Library.AucklandEvent.ailang** — new file
- `AK_HitTest(x, y)` — pre-order walk, deepest visible+enabled interactive node wins (painter's algorithm match)
- `AK_SetState(node, new_state)` — updates STATE field, marks DIRTY, returns old state
- `AK_EventMouse(mx, my, event_type)` — full state machine:
  - MOVE: hover tracking, old node→NORMAL, new node→HOVER
  - DOWN: target→PRESSED, records pressed_node, click-to-focus
  - UP: if over pressed_node → fire action + HOVER, else → cancel + NORMAL
- `AK_FireAction(node)` — reads ACTION_PTR/ACTION_LEN from extra, prints `[ACTION] service.method` (placeholder for Service Manager)
- `AK_DrawDirty(canvas)` — walks tree, redraws only DIRTY=1 nodes, clears flags
- `AKEvent_Init()` — reset hover/pressed/focus to -1
- **Test.AucklandEvent.ailang** — 20 tests, all passing:
  - Hit testing (empty space, buttons, labels)
  - Hover transitions (enter/leave)
  - Press/release (click fires action)
  - Press-drag-release-outside (cancels, no action)
  - Dirty flag tracking and clearing

### 2. Button State Visual Feedback
- `AK_DrawNode` button block updated to read `AK_Get(node, AKF.STATE)`
- NORMAL: base bg color
- HOVER: bg lightened (+30 per channel, clamped to 255)
- PRESSED: bg darkened (-30 per channel, clamped to 0)
- DISABLED: bg grayed to average, text dimmed
- Border color also adjusts per state
- Color unpacking via Divide(bg, 256/65536) for channel extraction

### 3. Live Display Server Integration
- **SysDisplay.ailang** (entry point) — rewritten to build Auckland taskbar
  - `SysDisplay_Init()` replaces old `SysDisplay_Start()` (split: init returns, run is separate)
  - Auckland tree built in entry point (application code, not library)
  - Three buttons: "New Window" (cyan), "Close Focused" (red), "About" (gray)
  - Status label: "Auckland Event Routing — Live"
  - Spacer with grow=1 pushes UI to bottom of screen
  - `AK_Draw` + `Win_BlitAll` for initial render
- **Library.SysDisplay.ailang** — modified:
  - Added `LibraryImport.Auckland` and `LibraryImport.AucklandEvent`
  - Added `SysDisplayState.desktop_surf` field (exposed for entry point)
  - Renamed `SysDisplay_Start` → `SysDisplay_Init` (Run+Shutdown moved to entry point)
  - `SysDisplay_DrainInput`: added `AK_EventMouse` calls for MOUSE_MOVE, MOUSE_DOWN, MOUSE_UP
  - `SysDisplay_Run`: added `AK_DrawDirty(AKTree.canvas)` check before `Win_RenderDirty`
  - Removed desktop TextBuffer (was overwriting Auckland draws with FillRect every frame)

### 4. Icon System — COMPLETE
- **tools/pack_widget_vif.py** — Python packer for named-entry VIF icon packs
  - Reads folder of TVG files, maps filenames to standard names via JSON
  - VIF v2 format: magic "VIF\x02", entry_count, JSON manifest, then TVG entries
  - Each entry: tvg_len, design_w, design_h, raw TVG data
  - Manifest is JSON hash: `{"standard-name": entry_index, ...}`
- **tools/radix_name_map.json** — maps Radix SVG filenames to standard widget names
  - ~100 mappings: arrow-left, close, check, settings, search, etc.
  - Unmapped files use filename stem as-is
- **Library.VIcon.ailang** — runtime icon loader
  - Three-tier resolution: CUSTOM → WIDGETS → DEFAULT (first match wins)
  - Per-tier state: manifest (XSHash via JSON), file data, entry offsets
  - `VIcon_Init()` — allocate tier table and cache
  - `VIcon_LoadVIF(tier, path)` — read file, parse JSON manifest, store in tier
  - `VIcon_FindIn(tier, name)` — lookup name in tier's manifest hash
  - `VIcon_Resolve(name)` — walk all three tiers, rasterize TVG at current size
  - `VIcon_Draw(canvas, name, x, y, color)` — resolve + tinted blit
  - Uses Library.JSON for manifest parsing (XSHash = free hash lookup)
- **icons/default.vif** — 344 Radix icons packed, 134KB
  - All 15×15 SVGs converted to TVG, packed with standard names
  - Standard name scheme: arrow-left, close, check, settings, search, edit, trash, etc.

---

## Bugs Found and Fixed

### TextBuffer Overwrites Auckland UI
- **Symptom**: Auckland buttons visible for one frame then disappear, reappear on hover
- **Cause**: Desktop (index 0) had a TextBuffer. `Win_RenderDirty` calls `TextBuffer_Render` which does `Draw_Pix_FillRect(surf, 0, 0, sw, sh, bg)` — wipes entire desktop surface including Auckland content
- **Fix**: Set desktop TB to -1 (`WinMgr_SetTB(idx, -1)`), TextBuffer_Create call commented out

### Initial Frame Not Visible
- **Symptom**: Auckland buttons flash then disappear on startup
- **Cause**: `SysDisplay_Init` calls `Win_BlitAll()` before Auckland tree is built. Entry point draws Auckland after init, sets dirty=1, but first loop tick processes before flip
- **Fix**: Added `Win_BlitAll()` in entry point after `AK_Draw()` to force immediate flip

### Double Buffer Flip
- **Observation**: `Win_BlitAll` writes to back buffer via `FB_GetDrawBuffer()`. `FB_FlipFast()` is called at the end of `Win_BlitAll` (already present in WinManager). Not a bug — just needed to understand the flip path.

---

## Current State of Files

### New this session:
```
Librarys/Library.AucklandEvent.ailang    — event routing (hit test, state machine, dirty draw)
Librarys/Library.VIcon.ailang            — 3-tier named icon loading
Test.AucklandEvent.ailang                — 20-case event routing test
tools/pack_widget_vif.py                 — icon pack packer (TVG → VIF v2)
tools/radix_name_map.json               — Radix → standard name mapping
icons/default.vif                        — 344 icons packed (134KB)
4-5-2026-session8-progress.md            — this file
4-5-2026-session8-continuation.md        — next session pickup notes
```

### Modified this session:
```
Librarys/Library.SysDisplay.ailang       — Init/Run split, Auckland wiring, TB removal
Librarys/Library.Auckland.ailang         — Button draw with state-aware colors
SysDisplay.ailang                        — Entry point with Auckland taskbar UI
```

### Downloaded (not committed to repo):
```
radix-icons/                             — 344 SVG icons from Radix UI
radix-icons/tvg/                         — converted TVG files
radix-icons.zip                          — source archive
```

---

## Architecture Decisions Made

1. **Application UI code lives in entry point, not library** — Auckland tree construction is app-level. SysDisplay library provides infrastructure (init, event forwarding, dirty checking). Entry point builds the actual UI.
2. **SysDisplay_Init / SysDisplay_Run split** — Init returns control to caller. Run blocks in event loop. Allows app code to execute between init and run.
3. **Three-tier icon resolution** — custom → widgets → default. First match wins. Same pattern as Auckland theme spec's property resolution.
4. **Standard icon names** — widgets ask for "close", "check", "settings" etc. Resolution finds the icon. Apps never know which tier provided it.
5. **JSON manifest in VIF** — icon pack metadata is a JSON string parsed by Library.JSON at load time. XSHash gives hash-based O(1) name lookup for free.
6. **VIF v2 format** — magic "VIF\x02" distinguishes icon packs from font packs ("VIF\x01" implied). Same container concept, different entry structure (name-indexed vs codepoint-indexed).

---

## Key Patterns / Gotchas

### All previous session gotchas still apply:
- Flatten all expressions (6-register ABI)
- TR_HANDLE init to -1
- Distinct variable names across WhileLoop blocks
- TVG_PackColor for all colors (alpha=255)
- FixedPool declarations before Functions

### New this session:
- **TextBuffer and Auckland don't coexist on the same surface** — TB's FillRect wipes everything. Any surface managed by Auckland must not have a TB.
- **Win_BlitAll writes to back buffer** — need FB_FlipFast to make it visible. Win_BlitAll already calls it at the end, but standalone blits from entry point need their own flip.
- **Button color unpacking** — `Divide(packed_color, 256)` and `Divide(packed_color, 65536)` extract G and R channels from BGRA. Works because packed format is `B | (G<<8) | (R<<16) | (A<<24)`.
- **AK_DrawDirty redraws more than necessary** — AK_DrawNode recurses into children unconditionally. Optimization: only redraw the dirty node itself, not its subtree. Good enough for now.

---

## How to Run

```bash
# Standalone event routing test
./Test.AucklandEvent.x

# Live display server with Auckland taskbar (from TTY, not SSH)
sudo ./SysDisplay.x > /tmp/syslog.txt 2>&1
# ESC to exit
# Check: grep "[Auckland]\|[AK]\|[ACTION]" /tmp/syslog.txt
```

---

## Git Status
All committed and pushed to origin/master.
