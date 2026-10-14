# Audio clock

**Updated:** 2026-09-29

One process owns the sound card during a session: `DAW/Mixer/daw_mix.ailang`. It opens `/dev/snd/pcmC0D0p` through `Library.AudioEngine` (ioctl, no libasound, no miniaudio). Period 256, buffer 1024, four periods. It writes one period only when the card has that much room. A short ring is silence for that period. A ring deeper than 1024 frames is cut back to the last 1024. It does not repeat a stuck sample.

A ring is the SynthKit `pcm.bin`: 64-byte header, capacity 8192, stereo 16-bit. Capacity is at byte 8, write index at 16, read index at 24, rate at 32, frames at 64. Writers stop when the ring already holds 1024 frames.

The mix law is `sample * fader / 256`, then master L and master R `/ 256`, then one clamp into 16-bit. Each instrument has already clamped its own ring. This second sum is the session bus.

## Who opens the card

| Program | Card |
| --- | --- |
| `daw_mix` | Owns it for a session. Reads the graph and `levels.bin`. |
| `synth_app` | Opens it only when launched with the argument `card`. A session track omits that argument and writes a ring. |
| `wave_play` | Opens it when the card is free. If the open fails, it fills the ring and stops at 1024 frames. |
| `wave_hear` | Still on disk. The desk does not start it. |
| Desk, `view_gtk`, effect picture, effect worker | Never. |

`view_gtk` blits `/dev/shm/daw/desk.fb` and writes pointer and keys. It is not a mixer.

## Graph

`run_step1.sh` writes the graph the mixer reads: a `master` line, an `events` line, then one `track <pcm.bin> <midi.bin> <fader>` line per ring. The desk does not start those kernels. Faders, mute, and solo arrive in `/dev/shm/daw/levels.bin`. Cords arrive in `/dev/shm/daw/route.bin`. Both are optional. Missing `route.bin` means every graph track is in the master sum, dry ring.

## Preview and record

PLAY on a wave track starts `DAW/Mixer/wave_play` on `/dev/shm/daw/wplay/pcm.bin`. It does not start `wave_hear`.

REC does not capture. There is no capture process. A later take is an AILANG writer, either inside the card owner or as its own opener when the mixer is not holding the device.

## Carla

`/home/bob/Carla/bin/carla-ring` is a separate program the desk execs. It is not a library. Its ring is an instrument ring. The mixer does not link Carla.

## Checklist

Order is `DAW/PLAN.md`. A box is card-free. `daw_mix.x check` parses. `daw_mix.x sum <graph>` prints one peak and does not open `/dev/snd`. Any other argv opens the card.

- [x] **AU-1** Session card owner is `DAW/Mixer/daw_mix.ailang`. Period 256, buffer 1024. One period only when the card has room. Short ring is silence. A ring past 1024 frames is cut to the last 1024. Law is `sample * fader / 256`, then master L and master R `/ 256`, then one clamp. `levels.bin` is magic `827019852`. Card-free peaks on 2026-09-29: seven constant-10240 rings, fader 256, master 80, peak 22400, 0 rails.
- [x] **AU-2** Missing `route.bin` sums every dry graph ring. Same fail-open as `DAW/ROUTE.md` **RT-1**.
- [ ] **AU-3** Capture. Depends on **AU-1** and **SO-6**. An AILANG writer, either inside the card owner or its own opener while the mixer is not holding the device. The take file lands in the song `audio/` folder. REC today only clears `recpid`. Done when a fixture ring becomes a wav with no listen. Do not open `/dev/snd` to prove it.
- [ ] **AU-4** Carla in the sum. Depends on **AU-1** and **RT-1**. `carla-ring` already writes an instrument ring and does not open the card. Done when that ring is a graph track the existing law can hear. The mixer does not link Carla.
- [x] **AU-5** Hold. `wave_hear` stays on disk. The desk does not start it. A session does not run it beside `daw_mix`.
- [x] **AU-6** Hold. The mix law stays as written until a listen is asked for. Routing does not replace the second sum. Do not restart Beverly Hills.
