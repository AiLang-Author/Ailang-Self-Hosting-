# Continuation Notes — Session 9 Pickup
# From: Session 8 (April 5, 2026)
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

---

## Priority: Auckland Markup Parser

### What It Does
`Library.AucklandParse.ailang` — tokenizes HTML-subset markup, builds AKNode tree from tags. Replaces manual `AK_CreateNode` / `AK_Set` / `AK_AddChild` boilerplate with declarative markup files.

### Example Input
```html
<window title="Calculator" design-w="360" design-h="540" bg="#1A1A2E">
  <panel bg="#0D1117" padding="8" border="1" border-color="#333">
    <label text="0" font-size="28" fg="#00FF88" text-align="right" />
  </panel>
  <group layout="grid" cols="4" gap="4" padding="8">
    <button label="7" action="digit:7" grow="1" />
    <button label="8" action="digit:8" grow="1" />
    <button label="9" action="digit:9" grow="1" />
    <button label="+" action="add" grow="1" fg="#FF6B6B" />
  </group>
</window>
```

### Example Output
An AKNode tree identical to what you'd get from hand-coding the CreateNode/Set/AddChild calls.

### Implementation Plan

**Phase 1: Tokenizer**
- Read file into buffer (SystemCall read)
- Scan for: `<tag`, `</tag>`, `/>`, attribute="value" pairs, text content
- Token types: TAG_OPEN, TAG_CLOSE, TAG_SELF_CLOSE, ATTR_NAME, ATTR_VALUE, TEXT
- No need for full XML parser — this is a controlled subset

**Phase 2: Tree Builder**
- TAG_OPEN → `AK_CreateNode(tag_to_AKTag(name))`, push onto parent stack
- Attributes → `AK_Set` / `AK_ExtraSet` based on attribute name mapping
- TAG_CLOSE → pop parent stack
- TAG_SELF_CLOSE → create node, add to current parent, don't push
- `AK_AddChild(stack_top, new_node)` for each new node

**Phase 3: Attribute Mapping**
Map attribute names to Auckland API calls:
```
layout="vbox"     → AK_Set(node, AKF.LAYOUT_MODE, AKLayout.VBOX)
gap="8"           → AK_Set(node, AKF.GAP, 8)
padding="12"      → AK_Set(node, AKF.PAD_T/R/B/L, 12)
grow="1"          → AK_Set(node, AKF.GROW, 1)
bg="#1A1A2E"      → AK_ExtraSet(node, AKExtra.COLOR_BG, parse_color("#1A1A2E"))
fg="#FFFFFF"       → AK_ExtraSet(node, AKExtra.COLOR_FG, parse_color("#FFFFFF"))
label="OK"        → AK_ExtraSet(node, AKExtra.STR_PTR, "OK") + STR_LEN
text="Hello"      → same as label
action="app.quit" → AK_ExtraSet(node, AKExtra.ACTION_PTR, "app.quit") + ACTION_LEN
font-size="18"    → AK_ExtraSet(node, AKExtra.FONT_SIZE, 18)
text-align="center" → AK_ExtraSet(node, AKExtra.TEXT_ALIGN, TRAlign.CENTER)
width="200"       → AK_Set(node, AKF.WIDTH, 200)
height="40"       → AK_Set(node, AKF.HEIGHT, 40)
min-w="100"       → AK_Set(node, AKF.MIN_W, 100)
cols="4"          → AK_Set(node, AKF.COLS, 4)
border="1"        → AK_ExtraSet(node, AKExtra.BORDER_W, 1)
border-color="#555" → AK_ExtraSet(node, AKExtra.BORDER_CLR, color)
icon="close"      → VIcon_Draw integration (future)
id="screen"       → AK_Set(node, AKF.ID_HASH, hash("screen"))
```

**Phase 4: Color Parser**
- `#RGB` → expand to `#RRGGBB`
- `#RRGGBB` → `TVG_PackColor(R, G, B, 255)`
- `#RRGGBBAA` → `TVG_PackColor(R, G, B, A)`
- Hex digit parsing: `'A'-'F'` = 10-15, `'a'-'f'` = 10-15, `'0'-'9'` = 0-9

**Phase 5: Tag Name → AKTag Mapping**
```
"window"    → AKTag.WINDOW
"group"     → AKTag.GROUP
"panel"     → AKTag.PANEL
"button"    → AKTag.BUTTON
"label"     → AKTag.LABEL
"text"      → AKTag.TEXT
"display"   → AKTag.DISPLAY
"spacer"    → AKTag.SPACER
"separator" → AKTag.SEPARATOR
"scroll"    → AKTag.SCROLL
"tabs"      → AKTag.TABS
"tab"       → AKTag.TAB
"checkbox"  → AKTag.CHECKBOX
"radio"     → AKTag.RADIO
"slider"    → AKTag.SLIDER
"progress"  → AKTag.PROGRESS
"image"     → AKTag.IMAGE
"canvas"    → AKTag.CANVAS
"theme"     → AKTag.THEME
```

**Public API:**
```ailang
// Parse markup file, returns root node index
root = AKParse_File("markup/calculator.html")

// Parse markup string (for embedded/generated markup)
root = AKParse_String(markup_ptr, markup_len)

// Then use normally:
AK_SetRoot(root)
AK_Draw(canvas, w, h)
```

### Test Plan
- Parse the calculator markup from Auckland spec section 13.1
- Verify tree structure matches hand-built equivalent
- Visual comparison: parsed tree renders identically to manual tree

---

## Secondary: Wire Action Dispatch

Currently `AK_FireAction` just prints. Next step:
- `[ACTION] win.new` → call `Win_Create(...)` and `SysDisplayState.dirty = 1`
- `[ACTION] win.close` → call `Win_Close(WinMgr.focused)` and dirty
- `[ACTION] app.about` → placeholder (maybe popup panel later)

This is a string-match dispatch table in the entry point. Simple `StringCompare` chain for now, action pool / Service Manager for later.

---

## Tertiary: Items on Hold

### Icon Integration with Auckland
- Add `icon="close"` attribute to buttons
- AK_DrawNode button block: if icon name set, call `VIcon_Draw` alongside text
- Icon placement: left of label text, or centered if no text

### Document / Canvas Widget
- `<canvas>` tag → Auckland places rect, app draws whatever it wants
- Document pages are canvas widgets with PageSurface metadata
- Depends on parser being done first (canvas tag needs to be parseable)

### ExprChain Compiler Optimization
- From earlier today's chat: `ExprChain result { ab = Multiply(a, b) ... -> Add(ab, cd) }`
- `->` token already in lexer. Needs parser + compiler modules.
- Will improve readability AND performance (fewer register spills)

### Performance
- Vertical resize slower than horizontal — investigate hot path in Win_UpdateResize + Win_BlitAll
- AK_DrawDirty redraws full subtree — optimize to single-node redraw
- Strip TVG debug prints from VIF parser (still present, print on every glyph raster)

### Theme System
- `.2ptheme` files: VIF widgets + VIF fonts + JSON manifest
- `<theme pack="modern-dark" />` tag in markup
- Three-level property resolution: element → theme → platform default
- Icons already have this pattern via VIcon tiers

---

## File Inventory — What Exists

### Core Libraries (complete, tested):
```
Library.VIF.ailang              — TVG rasterizer
Library.SurfaceBlit.ailang      — surface compositing
Library.Fonts.ailang            — vector font engine
Library.SuperSample.ailang      — 2x/4x downsampling
Library.TextRegion.ailang       — region-bounded text (wrap, align, clip)
Library.Auckland.ailang         — layout solver (vbox/hbox/grid, flex, draw)
Library.AucklandEvent.ailang    — hit testing, state machine, dirty draw
Library.VIcon.ailang            — 3-tier named icon loading
Library.JSON.ailang             — JSON parse + serialize
```

### Display Server:
```
Library.SysDisplay.ailang       — display server infrastructure
SysDisplay.ailang               — entry point with Auckland taskbar
```

### Tools:
```
tools/export_font_glyphs.py     — FontForge TTF → SVG + metrics
tools/svg2tvg.py                — SVG → TVG converter
tools/pack_font_vif.py          — font VIF packer (codepoint-indexed)
tools/pack_widget_vif.py        — icon VIF packer (name-indexed, JSON manifest)
tools/radix_name_map.json       — Radix → standard name mapping
```

### Assets:
```
fonts/DejaVuSans.vif            — 94 ASCII glyphs, 14.5KB
icons/default.vif               — 344 Radix icons, 134KB
```

### TODO (next session priority order):
```
Library.AucklandParse.ailang    — markup parser ← START HERE
Library.AucklandTheme.ailang    — theme pack loader
Library.AucklandWidget.ailang   — VIF sprite sheet widget rendering
Library.PageSurface.ailang      — paper-sized canvases
Library.Document.ailang         — multi-page documents
```

---

## Quick Start for Next Session

```bash
cd ~/Ailang-Self-Hosting-
git pull

# Verify everything works
./Test.AucklandEvent.x
# Should print 20 PASS lines

# Live display server (from TTY)
sudo ./SysDisplay.x > /tmp/syslog.txt 2>&1
# Should see: blue desktop, title text, three buttons at bottom
# Hover buttons → lighten, click → darken + [ACTION] in log
# ESC to quit

# Start working on parser:
# Read auckland-spec.md sections 6 (markup tags) and 16 (parser scope)
# Read continuation notes above for implementation plan
```
