# Effects

**Project:** AILANG Media / SynthKit DAW
**Author:** Sean Collins, 2 Paws Machine and Engineering
**Status:** EQ picture is in the desk. The worker is `DAW/Effects/eq.ailang`. The mixer chooses the ring.
**Updated:** 2026-09-29

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

This is the whole interface. If a feature is not named here, it is not part of an effect.

## Two programs, one kind

An effect is a name, a fixed list of integer parameters, and two programs:

1. **Picture.** One AILANG window. It draws the effect and writes parameters. It does not see samples and it does not open the sound card. The EQ picture is `Library.DawEq`.
2. **Worker.** One AILANG process. It reads the dry ring and writes the wet ring. It does not draw. Shipped workers are AILANG. C, C++, and Python are not workers on this path.

The desk does not load a shared library. The mixer never calls into the effect. Hot plug is: set the track's effect slot, start or stop that worker. The desk starts `DAW/Effects/eq` when the slot is EQ (`fx` 1) and stops it when the slot is cleared.

The instrument is not an insert. It stays the track's own process and its own ring. The insert sits after that ring and before the fader.

## Effects only

An effect takes audio in and writes audio out. It does not take notes. The synth and the sample player stay the instruments.

Carla is not an effect. It is an instrument process behind `/home/bob/Carla/bin/carla-ring`. A later wrapper in front of someone else's effect host would still be just another worker: same files, same rings. The mixer does not load the plugin.

## Files

One directory per instance:

```
/dev/shm/daw/<track>/fx/<slot>/
  kind.txt      one word, the kind name
  bypass.txt    0 or 1
  param.txt     one integer per line, in parameter order
  out           the wet ring, same layout as a SynthKit pcm.bin
```

The dry ring is the track's `pcm.bin`, the parent of `fx/<slot>`. `param.txt` is decimal integers. A missing line stays at that parameter's default. Extra lines are ignored. The worker reads the file at the start of a block, not per sample.

The wet ring is 64-byte header, capacity at byte 8, write index at byte 16, read index at byte 24, then interleaved int16. 48000 Hz. Stereo.

## What the mixer does

The mix law does not change. Each heard track is still `ring * fader / 256`, then the sum times `master / 256`, then one clamp.

Which ring, from `route.bin` (`DAW/ROUTE.md`):

- `wet` is 0, or `bypass.txt` is 1, or `out` has no samples: read the dry ring.
- `wet` is 1 and `out` has samples: read `out`.

A dead worker does not silence the track.

## Kind table

| Kind | Parameters, in order | Range | Default |
| --- | --- | --- | --- |
| eq | low gain, low freq, low-mid gain, low-mid freq, high-mid gain, high-mid freq, high gain, high freq | gain −120…120 (tenths of a dB), freq 20…20000 (Hz) | gain 0, freq 120, 800, 2500, 8000 |

`eq` bands are a low shelf, a low-mid band, a high-mid band, and a high shelf. Gain 0 is unity: the four bands sum back to the input sample. The worker is integer AILANG. `eq check` runs that unity case and a +12 dB low shelf without opening the sound card.

A new kind adds one row here, one picture file, and one AILANG worker.

## Not an effect

- A plugin host inside the mixer, or a shared library loaded into it
- A GUI toolkit inside the worker
- Floating-point parameters on the wire
- A C or C++ stand-in for a shipped worker

## Checklist

Order is `DAW/PLAN.md`. A new kind is one row in the table above, one picture, one AILANG worker, and the same files and rings. The mix law stays on **AU-1**. The wet bit stays on **RT-1**.

- [x] **EF-1** EQ. Picture is `Library.DawEq`. Worker is `DAW/Effects/eq.ailang`. Gain 0 is unity. `eq check` passed unity and a +12 dB low shelf with no card. Desk starts the worker when `fx` is 1 and stops it when the slot clears (`DawDesk.EqSync`). Dead worker and `bypass.txt` `1` stay on the dry ring.
- [ ] **EF-2** Compressor. Depends on **EF-1** and **RT-1**. The picker already has the word. `fx` 2 has no worker and does not set `wet`. Done when the kind table has the row, the picture writes `param.txt`, the worker is AILANG, `wet` follows that slot, and a dead worker leaves the dry ring. `eq check` style proof, no card.
- [ ] **EF-3** Next kind after the compressor. Depends on **EF-1**. Same files, same rings, one new row. No shared library in the mixer.
- [x] **EF-4** Hold. `EqSync` is compiled and has not been watched on a live desk. Starting the desk to watch it waits for an ask. Do not bring the worker back as C or C++.
