# Parts

**Project:** AILANG Media / SynthKit DAW
**Author:** Sean Collins, 2 Paws Machine and Engineering
**Status:** Menu, keys, and `DawClip.Command` split, copy, paste, duplicate, and erase. Slip is not built. The editor-bar button labeled CUT deletes selected notes.
**Updated:** 2026-09-29

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

A part is the clip already on a track (`LinkagePool.DawClip`). Studio One calls the same thing an event. This file is how a part is cut, copied, and heard. It is not an effect. Effects stay in `DAW/EFFECTS.md`.

## Checklist

Order is `DAW/PLAN.md`. Parts do not depend on the mixer. None of these boxes open the sound card.

- [x] **ED-1** Dragging a part calls `DawClip.SetStart`. The body moves. Arrange pick has no edge zones, so trim is **ED-7**.
- [x] **ED-2** Right-click menu and the desk keys call `DawClip.Command`. Menu order is CUT, COPY, PASTE, DUP, SPLIT, ERASE, mapped to commands 2, 1, 3, 4, 6, 5. `view_gtk` writes the same numbers: Ctrl+C 1, Ctrl+X 2, Ctrl+V 3, Ctrl+D 4, Delete 5. CUT and SPLIT both call `DawClip.SplitAt` at the playhead. ERASE unlinks the part. COPY, PASTE, and DUP use `FixedPool.DawBoard` (source, length, label, and MIDI notes inside the window). Paste lands on the selected track at the playhead. DUP places the copy after the original and selects it.
- [ ] **ED-3** Part buttons on the editor bar. Depends on **ED-2**. The bar today is ALL, CUT, KEY+, KEY-. That CUT calls `DawNote.DeleteSel`. Done when CUT, COPY, PASTE, DUP, and SPLIT on the bar call commands 2, 1, 3, 4, and 6, and the note-delete control is labeled as a note erase. Keys stay as they are.
- [ ] **ED-4** `offset` on `LinkagePool.DawClip`. Slip changes `offset` and leaves `start` and `length`. The field is absent. Save and Open grow a follow-up in **SO-5**.
- [ ] **ED-5** Clipboard stores `offset` and the wave identity. Depends on **ED-4**. `DawBoard` has no offset and no file.
- [ ] **ED-6** Drag the waveform to slip. Depends on **ED-4** and **ED-10**. The editor bar then says "drag the wave to slip".
- [ ] **ED-7** Arrange edge trim. Depends on **ED-1**. Left and right edges change the window. The body still moves. Dragging an edge back out shows the source outside the window, which needs **ED-4** once the source is longer than the window.
- [ ] **ED-8** Range split. Depends on **ED-2**. A rubber-band range cuts at both ends. `SplitAt` today is the playhead only, and it refuses a side shorter than 8.
- [ ] **ED-9** MIDI split. Depends on **ED-2**. Notes that fall in the window are the part. A note that crosses the split stays in the window where it starts. `SplitAt` does not move notes today.
- [ ] **ED-10** Real waveform. Depends on `DawClip.file`. `DawEditor.Wave` draws a modulo stand-in. The arrange shows the same window once the samples are read. The wave file is not rewritten.
- [ ] **ED-11** Zero crossing. Depends on **ED-10**. A wave split searches a few milliseconds for the nearest zero. If none is close, the split stays on the playhead.
- [x] **ED-12** Hold. Timestretch, clip gain envelopes, fades, layers, bend markers, and scoring are each a later box. They are not part of **ED-3** through **ED-11**.

## A part is a window

The source stays whole. A part is a window onto it: where the window sits on the arrange, how long the window is, and where in the source the window looks.

Splitting does not delete audio or notes. It makes two windows. Dragging an edge back out shows the source that was outside the window. That is the Studio One model, and it is why splice is safe.

```
LinkagePool.DawClip
  next
  start     arranged time of the left edge
  length    width of the window
  src       0 wave, 1 midi
  label
  offset    where in the source the window starts
```

`offset` is the slip. Moving the part changes `start`. Slipping changes `offset` and does not change `start` or `length`. The field is not on the clip yet.

MIDI source is the notes on that track whose time falls inside the window. Wave source is the take named by the part. Editing one does not rewrite the other.

## What you can see

No separate tool mode. A part is selected by clicking it. The body moves. The edges trim the window. The same commands are in three places, and they do the same thing:

1. Buttons on the editor bar, so the command is on screen.
2. A right-click menu on the part or on a wave selection. This is the mouse path.
3. A key, once the desk window has focus.

The shell never sees those keys. Ctrl+C interrupts a terminal only when the terminal itself has focus. A focused desk window gets the key instead. The conflicts that matter are the ones people already learned in other editors.

| Key | Command | Do not use |
| --- | --- | --- |
| Ctrl+C | COPY | not cut. Cut is Ctrl+X. |
| Ctrl+X | CUT, which splits the part at the playhead. It does not remove the part. | |
| Ctrl+V | PASTE | not Ctrl+P. Ctrl+P is print in most programs, and previous-line in a shell. |
| Ctrl+D | DUP | fine inside the desk. In a shell it means end-of-file, which does not apply here. |
| Delete | erase the selection | not Ctrl+E. Delete is the key with that name on it. |

Ctrl+E is free inside the window, and it is also "end of line" in a shell. Leave it unused. One erase key is enough.

The desk window takes the right button and those keys while it has focus. Right-click a part to open the menu. The gold outline is the selected part.

On the arrange, a part is selected by clicking it. The body moves. The left and right edges trim the window. The buttons sit on the editor bar, next to the ones already there:

| Button | What it does |
| --- | --- |
| CUT | Split the selected part at the playhead. It does not remove the part. |
| COPY | Keep the selection, leave the original. |
| PASTE | Put the clipboard at the playhead on the selected track. |
| DUP | Copy and place it immediately after the original. The copy is selected. |
| SPLIT | Cut the selected part at the playhead. |

DUP matches Studio One's duplicate: the new part starts where the old one ends, and it is the one selected afterward. SPLIT matches splitting at the timeline cursor. One click, not a separate blade tool.

A time range inside a part is a drag on empty wave or empty grid, the same rubber-band the notes already use. SPLIT with a range cuts at both ends of the range, which is the splice. CUT is that same split. ERASE removes the selection.

Paste and duplicate land on the selected track. They do not open a menu.

## Wave

A wave part opens in the editor as the waveform, not a drawn stand-in. The arrange shows the same window.

Drag the waveform itself to slip. Drag an edge to trim. The words on the editor bar say so: "drag the wave to slip". Slip is not a hidden chord.

A split on a wave prefers the nearest zero crossing, so the join does not click. The search stays a few milliseconds. If nothing is close, the split stays where the playhead is.

The wave file is not rewritten by cut, trim, slip, or duplicate. Those only add and remove windows. A later pass can write a new take when a part must become its own file. That pass is not this one.

## MIDI

A MIDI part is a window onto the track's notes. The piano roll edits the notes inside the window and already does move, trim, add, and box-select.

CUT, COPY, PASTE, and DUP on a MIDI part copy the notes that fall inside the window, not the whole track. SPLIT divides the window. Notes are not cut in half. A note that crosses the split stays in the window where it starts.

## Clipboard

One clipboard for the desk. It holds one part: source kind, length, offset, and either the note list or the wave identity. Paste creates one new part. It does not create a second clipboard and it does not keep a history.

## Not in a part

Timestretch, clip gain envelopes, fades, layers, bend markers, and scoring. Studio One has them. They are later, each as its own small addition, not as a second editor.
