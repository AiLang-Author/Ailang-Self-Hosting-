# Synth + Sampler — Work Plan

**Project:** AILANG Media / SynthKit  
**Author:** Sean Collins, 2 Paws Machine and Engineering  
**Date:** 2026-09-17  
**Status:** Skeleton + stereo SF2 loadable. Next: one slice at a time, starting with live MIDI-in.

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

---

## 1. Where we are (done)

SynthKit: AILANG owns voices and PCM; GTK is chrome (keys, knobs, bank picker, playhead). Same IPC split as Arcade/CAD.

| Piece | State |
|---|---|
| MIDI 1.0 parser, SMF, UMP, GM/GS/XG names | Done |
| Osc + ADSR + filter + delay + detune + PolyBLEP + mod matrix + sustain | Done |
| Dual osc (wave2, mix, osc2 octave) + LFO to filter/amp + JSON patches | Done |
| JSON save/load (`synthkit.patch.v1`) + amsynth bank converter | Done |
| Sample voice (WAV, pitch, loop) **S0** | Done |
| SF2 load + `sampleLink` stereo **S1** | Done (rudimentary zones) |
| Loadable banks (`bank.txt`, PTQ / Studio Grand / browse) | Done |
| Stereo mix `NCH=2` (L/R, dual delay) | Done |
| GTK `c`–`b` tester | Done |

**Not done:** live MIDI controller, velocity-accurate SF2 zones, program/preset pick, exclusive class, SFZ, 5.1/7.1.

Hardware: MIDI controller plugs in **tomorrow**. Slice **R** is first so that works.

---

## 2. Next — one at a time (do not skip ahead)

| # | Slice | Done when | Notes |
|---|---|---|---|
| **1 / R** | **Live MIDI-in + MIDI file play** | Controller and **Play .mid** through the loaded bank | Host: rawmidi + ALSA seq (`vmpk` → SynthKit:in). Kernel: `midi.bin` + SMF sequencer (`song.txt` / `song_cmd.txt`). Not full GM 16-channel yet. |
| **2 / S2a** | **Velocity layers + program pick** | Studio Grand soft/hard follows vel; PTQ Square Piano vs PanFlute is a spinner | Fix `igen` bags so `lovel/hivel` stick to the right sample. UI: program number. |
| **3 / S2b** | **Exclusive class** | Closed hat kills open hat | SF2 gen 57 / SFZ `group`+`off_by`. |
| **4 / S3** | **SFZ** | Folder of `.sfz` + `.wav` uses the same IR | After SF2 zones feel right. |
| **5** | **5.1 / 7.1** | `NCH=6` or `8`, pan/surround | Same mix loop. Not a rewrite. After MIDI+zones. |

Do not start 2 until 1 is playable on the real controller. Do not start SFZ until velocity/program work on Studio Grand + PTQ.

---

## 3. Slice 1 — MIDI-in (current)

```
USB / DIN controller
        │  ALSA rawmidi  (host C, same role as miniaudio)
        ▼
 /dev/shm/synth_app/midi.bin     byte ring
        │
        ▼
 kernel MIDI_StreamFeed
        │
        ├── 9n note on  vel → VoiceOnSample / VoiceOnNote
        ├── 8n / 9n vel0    → NoteOff  (respect sustain)
        ├── CC1  mod wheel  → SK.mod  (same matrix as GTK)
        ├── CC64 sustain    → SK.sus
        ├── CC7  volume     → mix gain
        └── pitch bend      → Synth_SetPitchMod
```

- 256-voice pool (idle voices skipped in the mix). Per-channel note alloc so Type 1 tracks do not collapse onto one C4. Engine cap 4096; 10k simultaneous is a later threaded job, not a bigger silent array.
- GTK computer keys remain; they are not the product.
- If the stick only shows up as a sequencer client (no `midiC*D*`), add ALSA seq subscribe as a follow-up **inside this slice**, not as slice 2.

---

## 4. Goal (unchanged)

One voice pool. Oscillator **or** sample. Same env, filter, LFO, mod, delay, mix.

SF2 and SFZ compile to one instrument IR. Kontakt never. FluidLite is a layout reference, not the player.

**Bus:** `NCH=2` now. Surround is more channels later.

**Memory:** mmap the bank. Do not copy 200 MB into a second buffer if we can avoid it (today’s loader still `Allocate`s the file — mmap is a polish inside S1, not a new slice).

---

## 5. Format lock

| Format | Do? |
|---|---|
| SF2 | Yes — in, keep hardening |
| SFZ | Yes — slice 4 |
| SF3 | After SF2 + Ogg demux |
| DecentSampler | Only if we need a library that is not SFZ |
| Kontakt | **Never** |

---

## 6. Files

```
Librarys/Media/Library.Sample.ailang
Librarys/Media/Library.SF2.ailang
Librarys/Media/Library.Synth.ailang
Applications/SynthKit/          kernel + GTK + pcm_play + midi_in
tests/sample/sine_c4.{wav,sf2}
docs/apps/SYNTH_SAMPLER.md      this file
```

IPC: `keys.txt` `ctl.txt` `cmd.txt` `bank.txt` `pcm.bin` `midi.bin`

---

## 7. Decision lock

- One slice at a time, list above.
- Controller tomorrow → **MIDI-in is the active slice.**
- AILANG owns parse + play. Host C is chrome, PCM, and MIDI bytes.
- One IR. No second engine.
- Kontakt is a hard no.
