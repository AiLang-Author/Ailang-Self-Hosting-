# Routing

**Project:** AILANG Media / SynthKit DAW
**Author:** Sean Collins, 2 Paws Machine and Engineering
**Status:** The bay is in the desk. The mixer reads a snapshot, not the pool.
**Updated:** 2026-09-29

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

The desk holds the connection list in `Library.DawRoute`. The mixer never imports that library. It reads `/dev/shm/daw/route.bin`, the same way it reads `levels.bin`.

## What a cord is

Ports, slots, and cables live in the desk. Direction 0 is in, 1 is out. Owner 0 is hardware, 1 is a track, 2 is a bus, 3 is master. Kind 0 is audio, 1 is send, 2 is return, 3 is key.

The Route window is App Desk object 9. Top to bottom: inputs, mixer, effects, side chain, master, outputs. Jack names come from `DAW/Desk/alsa_names`, which reads `/proc/asound` and does not open a PCM device.

A default audio cord runs from the track out to that track's master input. `DawRoute.Monitor` cords `master.out` to `hw.out`. An effect or a side chain is a send plus a return that share a loop id. Break on that pair removes both cords and puts the dry cord back when no same-track effect or side send remains. Break on a loop-0 cord removes that cord only.

The list is saved in `session.json`. Saving it does not itself change the sound. The snapshot does.

Strip IN, OUT, and KEY rows are not built.

## Snapshot

The desk writes `/dev/shm/daw/route.bin` every frame, in the same track order as `levels.bin`.

```
u32 magic   827019853
u32 seq
u32 count
count times:
  u32 hear  1 = this track enters the master sum, 0 = it does not
  u32 wet   1 = prefer fx/0/out, 0 = the graph pcm.bin
u32 seq
```

A snapshot applies only when the magic matches, `count` is at most 64, the byte count covers the records, and both seq words match. Anything else is ignored.

Missing file, or a rejected file: every graph track is heard, and every track uses its dry ring. That is the sum `run_step1.sh` gets when the desk is not running.

`hear` is 1 when an audio cord from the track out reaches a master port, or a return cord from that track lands on a master port. No out port, or an empty connection list, stays heard. `wet` is 1 when the track's effect slot is the EQ (`fx` 1).

The first graph tracks line up with the first desk tracks, the same contract as `levels.bin`. The mixer applies `min(count, graph tracks)`.

## What the mixer does with it

The mix law does not change. Mute, solo, fader, and master still come from `levels.bin`.

For each graph track, in order:

1. `hear` 0 adds nothing this period.
2. `wet` 1 and `fx/0/bypass.txt` is not `1` and `fx/0/out` has samples: read that ring.
3. Otherwise read the dry `pcm.bin` named in the graph. A missing worker does not silence the track.

Sends, buses, side chains, hardware inputs, delay, and more than two channels are drawn and saved. They do not change the stereo master sum. Multi-channel device setup is not part of this mixer.

## Not this path

`DAW/Mixer/mix.cc`, miniaudio, `pcm_play.cc`, and `wave_cap.cc` are not the mixer. Do not put them back. The card owner is `daw_mix.ailang`.

## Checklist

Order is `DAW/PLAN.md`. Snapshot work is finished. Later boxes extend what the sum reads. They leave the mix law and the card owner on **AU-1**.

- [x] **RT-1** Desk writes `/dev/shm/daw/route.bin` every frame (`DawDesk.Route`). Mixer reads it (`Mix.Route`). Magic `827019853`, both seq words, count at most 64. `hear` 0 adds nothing. `wet` 1 reads `fx/0/out` when that ring has samples and `bypass.txt` is not `1`, otherwise the dry ring. Missing or rejected file: every graph track, dry. Card-free peaks: dry 1000, hear 0 gives 0, wet 2000, bypass 1000.
- [ ] **RT-2** Prove `DawDesk.Hears` on the seed cords without the card and without a song. Depends on **RT-1**. Default cord is track out to that track's master input, and `SameOwner` treats owner 3 as one owner. Done when a check prints hear 1 for a seeded track and hear 0 for a track whose audio cord does not reach master. Empty connection list stays heard. Do not start the desk window or `daw_mix` to find out.
- [ ] **RT-3** Strip IN, OUT, and KEY rows. Picture only. The bay already draws. No sum change. Can start any time.
- [ ] **RT-4** Pan in the stereo sum. Depends on **AU-1**. `DawTrack.pan` is already stored (0..1000, center 500). One extra scale inside the existing law, still one clamp. Card-free `sum` only.
- [ ] **RT-5** Cord delay in the sum. Depends on **RT-1**. `delay` is already saved on the cord and is not applied. Card-free `sum` only.
- [ ] **RT-6** Sends change which samples reach the master. Depends on **RT-1**. Grow the snapshot. Draws and `session.json` already keep the cords. Law and card owner stay.
- [ ] **RT-7** Buses in that same sum. Depends on **RT-6**. A bus is kind 2, view 0. The inspector still labels one as a sample.
- [ ] **RT-8** Side chain in that sum. Depends on **RT-6** and a worker that reads the key ring (**EF-2** or a later kind).
- [x] **RT-9** Hold. More than two device channels are not this mixer. Hardware inputs stay drawn and saved.
