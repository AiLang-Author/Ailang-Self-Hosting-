# Auckland UI Framework — Full Inventory

> **Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.**
>
> Baseline inventory of `Librarys/Display/` centered on **Auckland** (`Library.Auckland.ailang`) and the simplified HTML GUI pipeline. Use this as the reference before expanding widgets, attributes, or layout options.

---

## Auckland Stack — What It Is

Auckland is a **retained-mode layout engine**: you describe a widget tree (via HTML-like markup or programmatic API), then each frame it runs **measure → layout → draw**. The simplified HTML path is:

```
config/foo.html
    → HTMLParse (AST)
    → AucklandBind (AST → AK node tree)
    → Auckland (AK_Solve + AK_Draw)
    → DSurface canvas (window content area)
```

`AppHost_Open()` in `Library.AppHost.ailang` is the main entry point for apps: it parses the HTML, creates the window, wires toolbar/address bar, and registers the Auckland context for input routing.

---

## Core Auckland Files (UI Layer)

| File | Role | Key APIs |
|------|------|----------|
| `UI/Library.Auckland.ailang` (~1630 lines) | Tree, layout solver, renderer | `AK_CreateContext`, `AK_CreateNode`, `AK_Solve`, `AK_Draw`, `AK_DrawNode` |
| `UI/Library.AucklandBind.ailang` (~768 lines) | HTML → AK tree binding | `AKParse_File`, `AKParse_String`, `AKBind_ApplyAttr` |
| `UI/Library.AucklandEvent.ailang` (~463 lines) | Hit test, mouse/keyboard | `AK_HitTest`, `AK_EventMouse`, `AK_EventKey`, `AK_FireAction`, `AK_DrawDirty` |
| `UI/Library.TextRegion.ailang` (~770 lines) | Wrapped/aligned text rendering | `TextRegion_Create`, `TextRegion_Render`, `TextRegion_MeasureWidth` |
| `UI/Library.SyntaxColor.ailang` (~660 lines) | AILANG syntax highlighting for textfields | `SynColor_Line`, `SynColor_GetSpan` |
| `Content/Library.HTMLParse.ailang` (~1286 lines) | Generic HTML-subset lexer/parser/AST | `HTML_ParseFile`, `HTML_ParseString`, `HTML_GetTagName` |
| `Library.AppHost.ailang` (~190 lines) | Generic app window host from HTML | `AppHost_Open` |
| `Theme/Library.UITheme.ailang` | 50+ theme colors incl. Auckland widget defaults | `Theme.ak_btn_bg`, `Theme.ak_cursor_color`, etc. |
| `Theme/Library.UIScale.ailang` | Resolution-aware sizing | `UIScale.ak_btn_border_w`, `UIScale.ak_checkbox_sz`, etc. |

Higher-level apps built on Auckland: `Dialog`, `FileDialog`, `AboutDialog`, `NotepadApp`, `PaneDecorator`.

---

## Auckland Context Model

Each UI instance is an `AKContext` (LinkagePool) with:

- **Tree buffers**: up to 512 nodes × 256 bytes each
- **Extra buffers**: up to 512 extras × 200 bytes each (per-widget data)
- **State**: `hover_node`, `pressed_node`, `focus_node`, `dirty_count`
- **Window metadata**: `design_w/h`, `scale_num/den`, `toolbar_mode`, `addressbar`, `action_cb`

---

## Widget Tags — Defined vs Implemented

### Container tags

| HTML Tag | AKTag | Layout | Measure | Layout | Draw | Notes |
|----------|-------|--------|---------|--------|------|-------|
| `<window>` | WINDOW | vbox default | partial | yes | bg fill | Auto-grow single child to fill |
| `<group>` | GROUP | vbox/hbox/grid/flow | partial | vbox/hbox/grid only | bg fill | `flow` parsed but **not implemented** |
| `<panel>` | PANEL | vbox default | yes | yes | bg + border | |
| `<scroll>` | SCROLL | — | no | no | no | Tag exists, **no behavior** |
| `<tabs>` / `<tab>` | TABS / TAB | — | no | no | no | Tag exists, **no behavior** |
| `<spacer>` | SPACER | — | no | via grow | no | Works as layout filler via `grow` |
| `<separator>` | SEPARATOR | — | no | yes | yes | H or V line based on parent layout |
| `<theme>` | THEME | — | no | no | no | Tag exists, **no behavior** |

### Control tags

| HTML Tag | AKTag | Draw | Events | Notes |
|----------|-------|------|--------|-------|
| `<button>` | BUTTON | yes | yes | State colors, optional icon via `ICON_SURF` |
| `<label>` | LABEL | yes | hittable | Text via `label` or `text` attr |
| `<text>` | TEXT | no | hittable | **No draw path** — alias of label conceptually |
| `<display>` | DISPLAY | no | hittable | **No draw path** — read-only display stub |
| `<checkbox>` | CHECKBOX | yes | yes | Toggles `VALUE` on click |
| `<textfield>` | TEXTFIELD | yes | keyboard only | Multi-line editor, cursor, scroll, syntax, line numbers |
| `<radio>` | RADIO | no | hittable | **No draw or group logic** |
| `<slider>` | SLIDER | no | hittable | **No draw or drag logic** |
| `<progress>` | PROGRESS | no | — | **No draw path** |
| `<image>` | IMAGE | no | — | **No draw path** (field `ICON_SURF` exists for buttons) |
| `<canvas>` | CANVAS | no | hittable | **No draw path** — apps must paint externally |

**Fully working today:** `window`, `group`, `panel`, `button`, `label`, `separator`, `checkbox`, `textfield`, `spacer` (layout only).

**Defined but stubbed:** `scroll`, `tabs`, `tab`, `text`, `display`, `radio`, `slider`, `progress`, `image`, `canvas`, `theme`, `flow` layout.

---

## Layout System

### Layout modes (`layout` attribute)

| Value | Constant | Measure | Layout |
|-------|----------|---------|--------|
| `vbox` | AKLayout.VBOX | yes | yes — vertical stack, grow distribution |
| `hbox` | AKLayout.HBOX | yes | yes — horizontal stack, grow distribution |
| `grid` | AKLayout.GRID | yes | yes — `cols` attribute, equal cell sizing |
| `flow` | AKLayout.FLOW | no | no — **parsed only, falls through** |

### Alignment

- **Cross-axis**: `align` = `start` | `center` | `end` | `stretch`
- **Justify constants exist** (`AKJustify`: start, center, end, space-between, space-around) but **`justify` is not wired in AucklandBind** and not used in layout pass

### Sizing attributes (all supported in bind)

`width`, `height`, `min-w`, `min-h`, `max-w`, `max-h`, `grow`, `shrink`, `gap`, `padding`, `pad-t/r/b/l`, `cols`

### Scaling

`AK_ComputeScale` fits design space into canvas using `min(canvas_w/design_w, canvas_h/design_h)`. Values in the tree are design-space; `AK_Scale()` converts at layout/draw time.

---

## HTML Attributes — Full Bind Inventory

### Layout / structure

`layout`, `gap`, `padding`, `pad-t`, `pad-r`, `pad-b`, `pad-l`, `grow`, `shrink`, `width`, `height`, `min-w`, `min-h`, `max-w`, `max-h`, `cols`, `align`, `id`

### Visual

`bg`, `fg`, `border`, `border-color`, `font-size`, `text-align`

### Content / behavior

`label`, `text`, `action`

### Window-level

`title`, `design-w`, `design-h`, `toolbar` (`none` | `about` | `file` | `full` | `browser`), `addressbar` (`true`)

### Textfield-specific

`syntax` (`ailang`), `line-numbers` (`1`)

### Color format

`#RGB`, `#RRGGBB`, `#RRGGBBAA` → packed BGRA

### Not yet in bind (but fields exist in engine)

`justify`, `visible`, `enabled`, `border-rad`, `rows`, `value`, `icon`/image src, `checked`, selection fields (`SEL_START_ROW`, etc.), horizontal scroll (`SCROLL_X`)

### Parsed but not applied at draw time

`font-size` — stored in `AKExtra.FONT_SIZE` but draw code uses global `VFont_GetLineHeight()` / `UIScale.font_body`, not per-node size

---

## Draw Pipeline Detail (`AK_DrawNode`)

What actually renders to the canvas:

1. **WINDOW / GROUP** — `Draw_Pix_FillRect` if `bg` set
2. **PANEL** — bg fill + 4-sided border
3. **LABEL** — `TextRegion` with fg, text-align, middle v-align
4. **SEPARATOR** — 1px line (orientation from parent vbox/hbox)
5. **BUTTON** — state-aware bg/border (normal/hover/pressed/disabled), optional icon blit, centered label
6. **CHECKBOX** — box + checkmark fill + label text
7. **TEXTFIELD** — bordered editor, line numbers gutter, syntax-colored or plain text, cursor rect, vertical scroll

Uses: `Draw_Pix_FillRect`, `Surface_BlitAlpha`, `TextRegion_*`, `VFont_DrawString`, `VFont_MeasureWidth`, `SynColor_Line` (syntax), `TextBuf_*` (editing).

---

## Event System

### Mouse (`AK_EventMouse`)

- States: NORMAL → HOVER → PRESSED
- Click fires `AK_FireAction` → prints action string + calls `action_cb` via `CallIndirect`
- Checkbox auto-toggles `VALUE`

### Hittable tags

`button`, `label`, `text`, `checkbox`, `radio`, `slider`, `canvas`, `display`

**Gap:** `textfield` is **not** in the hittable list — you can't click-to-focus a textfield; focus is set only at bind time (first textfield) or programmatically.

### Keyboard (`AK_EventKey`)

Routes to focused `TEXTFIELD` only. Supports: printable chars, Tab (4 spaces), Backspace, Delete, Enter, arrows, Home/End, PageUp/Down.

### Dirty redraw

`AK_DrawDirty` repaints only nodes with `DIRTY=1`.

---

## Attached Library Dependency Tree

```
Auckland
├── Arena (allocation)
├── Render: DSurfaceTypes, DSurface, DDrawPixel, VIF, SurfaceBlit, Fonts
├── UI: TextRegion
├── Theme: UITheme
└── TextBuffer (textfield editing)

AucklandBind
├── Arrays
├── Content: HTMLParse
├── UI: Auckland, AucklandEvent
└── TextBuffer

AucklandEvent
├── UI: Auckland
├── TextBuffer
└── Input: DInputTypes (Key.* scancodes)

TextRegion
├── Render: DSurface, DDrawPixel, VIF, SurfaceBlit, Fonts
└── Arena

AppHost (application glue)
├── Auckland + AucklandBind + AucklandEvent
├── HTMLParse
├── WinManager + WinToolbar
├── Fonts, TextRegion, PaneDecorator
└── Theme: UIScale, UITheme
```

### Render stack (what actually puts pixels on screen)

| Layer | Libraries |
|-------|-----------|
| Pixel primitives | `DDrawPixel`, `DDrawCell` |
| Surfaces | `DSurface`, `DSurfaceTypes`, `SurfaceBlit` |
| Framebuffer | `Framebuffer`, `DRenderFB` |
| Compositor | `DCompose`, `DComposeStack`, `DComposeBSP`, `DComposeFloat` |
| Fonts/icons | `Fonts`, `VIF`, `VIcon`, `SuperSample` |
| Window chrome | `WinRender`, `WinToolbar`, `PaneDecorator` |
| Desktop shell | `Deskbar`, `Menu`, `StartMenu`, `CascadeMenu` |

---

## Real HTML Config Files in Use (20 apps)

Under `config/`:

`about`, `browser`, `calculator`, `canvas_demo`, `chrome`, `claude`, `filedialog`, `grep`, `ide`, `installer`, `ladybird`, `notepad`, `settings`, `terminal`, `usermgmt`, `usermgmt_lock`, `usermgmt_setup`, `videoplayer`, `vscode`, `wifi`

### Example patterns

**Minimal app shell** (`config/notepad.html`):

```html
<window title="Untitled - Notepad" design-w="620" design-h="460" toolbar="file">
  <group layout="vbox" gap="0" padding="0" bg="#FFFFFF">
    <textfield grow="1" bg="#FFFFFF" fg="#1A1A1A" border-color="#CCCCCC" padding="4"/>
  </group>
</window>
```

**Rich settings UI** (`config/settings.html`): vbox groups, labels, separators, hbox button rows, `id` hashes for dynamic label updates, `action` strings like `s.theme.dark`.

**Toolbar presets** via `toolbar="about|file|full|browser"` + optional `addressbar="true"`.

---

## Full `Librarys/Display/` Folder Map (61 files)

| Subfolder | Files | Purpose |
|-----------|-------|---------|
| **System/** (3) | SysDisplay, EventRouter, Screenshot | Main loop, action dispatch |
| **Window/** (5) | WinManager, WinInput, WinRender, WinStack, WinToolbar | Window CRUD, drag/resize, chrome |
| **Render/** (22) | Framebuffer, DSurface, DCompose*, DRings, Fonts, VIF, etc. | Pixel pipeline |
| **Input/** (4) | DInputTypes, DInputEvdev, DInputDiscover, Cursor* | Evdev input, software cursor |
| **IPC/** (2) | IPCBroker, InputRouter (vestigial) | App IPC |
| **UI/** (11) | Auckland*, TextRegion, SyntaxColor, Dialog*, NotepadApp, PaneDecorator | Widget toolkit |
| **Menu/** (4) | Deskbar, Menu, StartMenu, CascadeMenu | Desktop shell |
| **Theme/** (3) | UIConfig, UITheme, UIScale | Config + theming |
| **Content/** (4) | HTMLParse, Document, PageSurface, Editor | Markup + document engine |

---

## Gaps Worth Knowing Before Expansion

These are the highest-signal gaps between **what the type system defines** and **what actually works**:

1. **9 widget tags have no draw implementation** (radio, slider, progress, image, canvas, text, display, scroll, tabs)
2. **`flow` layout** and **`justify`** are defined but not implemented
3. **`font-size` per node** is stored but not honored at render time
4. **`textfield` click-to-focus** missing from hit test
5. **`SynColor`** is called from Auckland but not explicitly imported there (may rely on link order / transitive inclusion)
6. **No runtime data binding** — despite doc references, AucklandBind is really an HTML→tree compiler, not a live binding system; dynamic updates require manual `AK_Set` / `AK_ExtraSet` + dirty flag (as settings app does)
7. **`id` attribute** sets `ID_HASH` but no `AK_FindById` helper in Auckland core (FileDialog has its own `FD_FindNodeById`)
8. Debug `PrintMessage` calls still in hot draw path (`[DRAW]`, `[GRP_BG]`, etc.)

---

## Suggested Expansion Priority

If growing options from this baseline, a natural order would be:

1. **`<image>` + `<canvas>`** — most apps need these (videoplayer, browser, canvas_demo already reference canvas)
2. **`<radio>` + `<slider>` + `<progress>`** — complete the form control set
3. **`justify` + `flow` layout** — already in constants/parser
4. **Per-node `font-size`** — attribute already parsed
5. **`<scroll>` container** — unlock large content UIs
6. **`<tabs>` / `<tab>`** — multi-view apps
7. **`AK_FindById(ctx, hash)`** — simplify dynamic UI updates from action callbacks

---

## Related Documentation

- `Docs/Display system/00_MASTER_INDEX.md` — full display system overview
- `Docs/Display system/04_UI_FRAMEWORK.md` — Auckland design doc (some details differ from current code; this inventory reflects the code)
- `Docs/Display system/07_PAIN_POINTS.md` — known pain points and hardening roadmap