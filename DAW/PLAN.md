# DAW plan

**Project:** AILANG Media / SynthKit DAW
**Author:** Sean Collins, 2 Paws Machine and Engineering
**Updated:** 2026-09-29

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

## What this is

The desk draws. It does not open the sound card. `view_gtk` blits the framebuffer and forwards pointer and keys. Instruments are `synth_app` and `wave_play`. During a session only `daw_mix.ailang` opens the card. Cords are `Library.DawRoute`, published as `route.bin`. The EQ picture is `Library.DawEq`. The EQ worker is `DAW/Effects/eq.ailang`. Carla is `/home/bob/Carla/bin/carla-ring`, exec'd by the desk, not linked. Capture is not built. The contracts are `DAW/AUDIO.md`, `DAW/ROUTE.md`, and `DAW/EFFECTS.md`.

A third-party effect, when we need one, is a separate process in front of an existing host. We do not write that host. Instruments stay the synth and the sample player.

## Work list

The checklists live in `DAW/AUDIO.md`, `DAW/ROUTE.md`, `DAW/EFFECTS.md`, `DAW/EDIT.md`, and `DAW/SONG.md`. This section is the order. A finished seam stays finished.

Every open box is card-free. `daw_mix.x check` parses. `daw_mix.x sum <graph>` prints one peak and does not open `/dev/snd`. Any other argv opens the card. Do not run `DAW/run_step1.sh`, `run_player.sh`, or `run_synth.sh` for one of these boxes. A live desk run waits for an ask. Do not restart Beverly Hills.

### Done seam

These are in the tree. Later boxes sit on them.

| Id | What is already there |
| --- | --- |
| AU-1 | `daw_mix.ailang` owns the card. Mix law, `levels.bin`, graph, card-free `sum`. |
| AU-2 | Missing `route.bin` sums every dry ring. |
| RT-1 | Desk writes `route.bin`. Mixer applies hear and wet. |
| EF-1 | EQ picture, `DAW/Effects/eq.ailang`, `eq check`, desk spawn, dry fallback. |
| SO-1 … SO-4 | Song folders, writer, pool fields, Save, Open, New, Close, FILE menu. |
| ED-1, ED-2 | Drag moves a part. Menu and keys split, copy, paste, duplicate, and erase. |
| AU-5, AU-6, RT-9, EF-4, ED-12, SO-9 | Holds. Leave them. |

### Paths that can start now

Four paths share no code. One box at a time inside a path. Do not stack two sum changes in one edit.

**Path A, parts.** No mixer. `DAW/EDIT.md`.

1. **ED-3** editor-bar part buttons. The bar CUT today deletes notes.
2. **ED-4** `offset` on the clip, then **ED-5** clipboard, then **SO-5** so Save and Open keep it.
3. **ED-7** arrange edge trim, and **ED-8** range split, and **ED-9** MIDI split. These three sit on **ED-2** and can be separate edits.
4. **ED-10** real waveform, then **ED-6** slip drag and **ED-11** zero crossing.

**Path B, song proof.** No card. `DAW/SONG.md`.

1. **SO-6** `song check` round-trips a fixture folder.
2. **SO-7** waits on **SO-6** and on an ask before `run_step1.sh` points at a song folder. Travel converts through `DawLevel.Gain` at that edge.

**Path C, prove the seam.** No song.

1. **RT-2** a hear check on the seed cords. `DawDesk.Hears` is compiled and has not been run.

**Path D, next effect.** No card. `DAW/EFFECTS.md`.

1. **EF-2** compressor worker, same files and rings as the EQ. `wet` follows `fx` 2. A dead worker stays dry.

**Picture, any time.** **RT-3** strip IN, OUT, and KEY rows. No sum change.

### Path E, one sum change at a time

Each row changes what the sum reads. The law in **AU-1** stays. Card-free `sum` is the proof. A listen waits for an ask. Do not stack two of these in one edit.

| Order | Id | Waits on |
| --- | --- | --- |
| 1 | RT-4 pan | AU-1. Pan is already stored. |
| 2 | RT-5 cord delay | RT-1. Delay is already saved. |
| 3 | RT-6 sends | RT-1. Snapshot grows. |
| 4 | RT-7 buses | RT-6. |
| 5 | RT-8 side chain | RT-6 and a worker that reads the key ring. |
| 6 | AU-4 Carla ring as a graph track | AU-1 and RT-1. |

### Path F, capture

Starts once **SO-6** has passed. It does not wait on pan or sends.

1. **AU-3** AILANG writer. Inside the card owner, or its own opener while the mixer is not holding the device. Proof is a fixture ring written to a wav. No listen.
2. **SO-8** stores that take under the song `audio/` and sets the clip `file`.

### Holds

`wave_hear` stays unused (**AU-5**). The mix law stays (**AU-6**). Extra device channels stay out of this mixer (**RT-9**). C and C++ stay off the card, the mix, the routes, and the workers. Carla's ring wrapper stays. The live desk is not the way to tick a box.

## Current work: the workstation

The picture is App Desk. GTK is a view facilitator only: one window, one blit of the framebuffer, pointer and keys forwarded into the AILANG app. No GTK buttons, sliders, menus, or progress widgets. Layout, type, meters, and hit testing stay in AILANG so the same picture can move to another display runtime later.

The layout reference is PreSonus Studio One, the shot in `Downloads/idealworkflow.jpg`. Four regions inside one App Desk window:

1. **Arrange, top.** A track header column and a time ruler. Each header is one instance: arm, mute, solo, name, instrument. The lane to the right holds that instance's clips. Marker blocks sit above the ruler. Horizontal scroll moves every lane together. A vertical scrollbar appears when the rows do not fit.
2. **Editor, middle.** The selected instance, at a finer zoom. A synth or MIDI track scrolls a note grid in time and in pitch. A sample track scrolls a waveform in time. Same clock as the arrange. Changing the selection changes this pane. It is not a second program.
3. **Console, bottom.** One meter and one fader per instance, in track order. A vertical scrollbar when the strips do not fit. These are `Library.Gauge` bars and readouts (`Gauge.Bar`, `Gauge.BarH`, `Gauge.DrawReadout`). New gauge functions go in that library when the desk needs them. Fork a gauge into the DAW only when the change would break the ECU dash.
4. **Inspector, right.** The selected instance only. Name, kind (synth or sample), instrument, and a short stack of Gauge readouts. No plugin browser yet.

### How many tracks

Sixteen rows on screen is the starting view, not a cap. The session holds as many instances as it needs. The arrange and the console each scroll in their own window onto that list. Adding a part appends a row, a lane, and a strip. Two xylophones are two rows of kind sample, view wave. A saw and the bass are rows of kind synth, view midi. The kit is one sample row.

### The timeline is not a tape

A song is not one recording from bar 1 to the end. The arrange stores clips. A clip has a start time, a length, and a source. Sources are a MIDI 3 track or a wave take. Clips may leave gaps, sit in any order, repeat, and be moved without rewriting the source. The marker bar names ranges (intro, verse, and the rest) and those ranges can be rearranged. The playhead walks the arranged time, not the file order of the original MIDI.

The editor uses the same clip model. A MIDI clip opens as notes you can scroll through. A wave clip opens as samples you can scroll through. Editing a clip does not require the other clips on that lane to be one continuous buffer.

Scrollbars are drawn by the desk, in both directions where the content is larger than the pane: time on the arrange and the editor, pitch on the note grid, and tracks on the arrange and the console.

### Desk bar and channel strip

The workspace keeps a vertical desk bar on the right edge, the same idea as the AOS desk bar. A 12px checkerboard is always drawn, on top of every window. The pointer wakes a 48px bar; leaving it hides the bar again. The bar is not a window. It stashes three panels:

- **SYN** — synth config for the selected synth track
- **SMP** — sample player for the selected sample track
- **EQ** — four bands. The picture is `Library.DawEq`. The worker is `DAW/Effects/eq.ailang` (`DAW/EFFECTS.md`).

Closing the panel's X stashes it. The button lights while the panel is open. Clicking the button again stashes it too.

Record, mute, and solo are the same three flags on the track (`arm`, `mute`, `solo`). They show up in three places, which is the Studio One layout:

1. Arrange track header, at the right of the name: **R** red when recording is armed, **M** yellow when muted, **S** green when soloed.
2. Mixer strip, top to bottom: instrument slot (SYN or SMP), EQ slot, then R M S, then the pan bar, then the fader, then the name. The master pair does not scroll and has no insert slots.
3. Inspector, spelled out (`R record on`) plus the same SYN/SMP and EQ buttons.

Clicking a slot selects that track and opens the matching panel. More effect slots come later. None of these buttons touch the sound card yet.

### Libraries

`Library.Gauge` and the rest of the ECU drawing code are the meters, faders, and readouts. Upgrade those libraries when a function is useful outside the DAW. Fork into `DAW/` when a change is only for this desk. App Desk stays the window chrome: title bar, drag, resize, close. The four regions are drawn in the content area under that bar. One session window first. A torn-off editor can be a second App Desk window later.

### Picture, already on screen

The five steps below are in the tree. Remaining work is the work list above, not a second build of the desk.

1. **Shared picture.** The framebuffer is `/dev/shm/daw/desk.fb`. `view_gtk` blits it and writes pointer and keys.
2. **Arrange.** Rows, ruler, clip rectangles, both scrollbars.
3. **Editor.** The selected row. MIDI clips draw a note grid. A wave clip still draws the modulo stand-in in `DawEditor.Wave` (**ED-10**).
4. **Console and inspector.** Faders and the selected track. Meters follow the fader, not the audio level.
5. **Session picture.** Clips and the playhead are drawn. The desk does not open the card and does not launch the mixer.

WAV capture is **AU-3**. A take is a wave clip on a row, not a GTK dialog. The desk is already on screen, and capture is still unbuilt.

## What already plays

SynthKit stays the reference. `run_player.sh` and `run_synth.sh` keep working. The DAW starts `Applications/SynthKit/synth_app.x` once per part. Only the mixer opens the sound card. Kernels were not forked.

A session is `DAW/Sessions/step1.json`. The song is `DAW/MIDI/Beverly Hills Cop Theme.song.json`. `DAW/tools/midi_fan.py` fans that file by track id. The last session, now stopped, had syn1 and syn2 on Megasynth 1, bass on Dirty Hole, two xylophone instances, one glass instance, and one Muldjord kit. Marimba in the file was renamed xylophone. Celesta was renamed glass. Playback testing of that mix is closed.

MIDI 3 routes notes. The track id is the route, and `inst` is the instrument. The song does not store the pack path, the Surge preset, or the fader. Those stay in the session. `group` is mute, solo, and choke, not a mixer bus.

## Not in this pass

Recording MIDI, a plugin browser, writing a VST/AU/LV2 host, Surge scene B, wavetable oscillators, forking the synth kernel, and any further sample-pack conversion. Open boxes for capture, parts, and the sum are the checklists. Sends, buses, side chains, and extra hardware pairs are drawn and saved. Path E is where a send or a bus starts to change the stereo sum. Extra device channels stay **RT-9**.
