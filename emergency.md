# EMERGENCY CONTEXT SAVE — 2026-06-10

## What We Were Doing
Windows-style text selection & clipboard for Auckland UI framework.

## Completed (code written & compiles)
- Phase 1-8: Full TEXTFIELD selection (shift+arrow, ctrl+C/V/X/A, mouse click, mouse drag)
- AK_DrawNode decomposed into 3 new library files (DrawWidgets, DrawText, DrawScroll)
- INPUT widget: click-to-cursor, drag-select, selection highlight, ctrl shortcuts
- VFont_PixelToCol (reverse pixel-to-column conversion)
- TextBuffer range ops (GetRangeText, DeleteRange, InsertString, NormalizeRange)
- Global Clipboard (FixedPool.Clipboard with Set/Get/Clear)
- Theme: ak_selection_bg = 0xFF264F78

## BUGS TO FIX (reported by user, not yet fixed)
1. **Solid bar on current line in Notepad** — ak_current_line_bg (0xFF2A2A3A) is rendering as solid bar covering text. Likely the FillRect for current line highlight is drawing OVER the text instead of UNDER it, or alpha isn't working. Check draw order in AK_DrawTFLines — current line highlight draws, then selection, then text content. Should be fine but maybe the color is too opaque or the rect covers wrong area.

2. **Cursor not visible in Notepad** — ak_cursor_color is 0xFFE8EEF8, width=2px. Should be visible. Maybe being drawn under the current line bar? Or VFont_GetLineHeight() returning wrong value causing cursor to be off-screen?

3. **Click-to-cursor not working at all** — Neither TEXTFIELD nor INPUT. AK_TextfieldClick and AK_InputClick added to AK_EventMouseDown but not functioning. Possible causes:
   - VFont_PixelToCol might not work correctly
   - Mouse coordinates might be in wrong coordinate space
   - TextBuf_SetCursor might not be taking effect
   - The click might not be reaching the handler (hit-test issue?)

4. **Selection/highlight not working in user mgmt or about window** — INPUT fields don't show selection. Could be same root cause as #3.

## Files Modified (from original)
- `Librarys/Display/UI/Library.Auckland.ailang` — AKExtra layout (SEL_END_COL=192, ICON_SURF=200, ENTRY_SIZE=208), AK_DrawNode thin dispatcher, imports for 3 new libs
- `Librarys/Display/UI/Library.AucklandEvent.ailang` — AK_TextfieldClick, AK_TextfieldDrag, AK_InputClick, AK_InputDrag, AK_EventKey decomposed (Nav/Edit/Ctrl), selection helpers (HasSelection, ClearSelection, DeleteSelection, CopySelection), mouse move drag detection
- `Librarys/Display/UI/Library.AucklandDrawText.ailang` — NEW FILE: AK_DrawSelLine, AK_DrawTextfield, AK_DrawTFViewport, AK_DrawTFLines, AK_DrawTFLineNum, AK_DrawTFContent, AK_DrawTFSyntax, AK_DrawInput, AK_DrawInputContent, AK_DrawInputText, AK_DrawInputSel
- `Librarys/Display/UI/Library.AucklandDrawWidgets.ailang` — NEW FILE: Panel, Label, Separator, Button, Checkbox draws
- `Librarys/Display/UI/Library.AucklandDrawScroll.ailang` — NEW FILE: Scroll container draws
- `Librarys/Display/Render/Library.Fonts.ailang` — VInst_PixelToCol, VFont_PixelToCol
- `Librarys/Library.TextBuffer.ailang` — Clipboard pool, range ops, InsertString
- `Librarys/Display/Theme/Library.UITheme.ailang` — ak_selection_bg
- `config/ui.cfg` — ak_selection_bg=0xFF264F78

## Key Theme Values
- ak_current_line_bg = 0xFF2A2A3A
- ak_cursor_color = 0xFFE8EEF8
- ak_cursor_w = 2
- ak_textfield_pad = 4
- ak_input_pad = 6
- ak_selection_bg = 0xFF264F78

## Compiler Constraint
All functions MUST have <20 local variables or stack corruption occurs.

## Plan File
/home/bob/.claude/plans/mighty-baking-blossom.md

## Apps With TEXTFIELD
- Notepad (notepad.html) — full-screen editor
- IDE (ide.html) — code editor with syntax + line numbers
- Grep (in installer_ipc) — pattern input

## Build Command
./build_image.sh --qemu

## Next Steps
1. Debug why click-to-cursor doesn't work (check coordinate spaces, VFont_PixelToCol, hit-test)
2. Fix current line highlight solid bar in notepad
3. Fix cursor visibility
4. Test all fixes
