# MediaCenter — Design Document
**Project:** AILang Display System  
**Author:** Sean Collins, 2 Paws Machine and Engineering  
**Date:** 2026-05-16  
**Status:** Phase 1 complete — clock + rings tested, codec worker building

---

## 1. Problem Statement

The existing video player forks `ffmpeg` as a black-box subprocess and chases its output reactively. This approach has fundamental problems:

- **No system-wide sync.** Each app runs its own clock. Audio in one app has no relation to video timing in another.
- **Instancing is broken.** libavcodec carries global state. Running 5 simultaneous decoders (e.g. a DAW with MP3 + WAV + H.264 + AAC + H.265 channels) causes conflicts, thread contention, and unpredictable behavior.
- **ffmpeg's architecture is a hot mess above the codec layer.** libavformat, libavutil, libswresample, the CLI wrapper — all of this complexity exists between us and the codec math we actually want.
- **No formal API.** Applications cannot instance and use audio/video as a first-class windowing system service.

---

## 2. Design Goals

1. **One clock, one source.** All media timing derives from a single hardware-backed monotonic clock. No chasing. No reactive correction.
2. **Codec isolation.** Each codec runs as an independent worker process. Instancing N decoders means N processes with zero shared state.
3. **Formal API.** Any AILang application can create media sessions, send commands, and receive decoded output via canvas tags and mixer buses.
4. **Zero-copy video path.** Decoded video frames land directly in ShmCanvas regions. No memcpy between decoder and display.
5. **Forward-compatible plugin model.** New codecs can be written in any language. The binary ring protocol is the only contract.
6. **GPU/3D ready.** The clock and ring architecture directly supports the future GPU pipeline — the same mmap ring protocol and clock source will drive frame submission to the GPU stack.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Application (videoplayer, DAW, browser, game)                   │
│                                                                   │
│  media.create / media.play / media.pause / media.stop            │
│  canvas_tag="player1"  mixer_bus=0                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │  /tmp/ailang_media.sock
                           │  4-byte BE length prefix + JSON
┌──────────────────────────▼──────────────────────────────────────┐
│  MediaCenter  (MediaCenter.ailang → MediaCenter.x)               │
│                                                                   │
│  THE WALL CLOCK — CLOCK_MONOTONIC_RAW, ns resolution            │
│  Owns ALSA — 48kHz S16LE stereo, 3-bus mixer                    │
│  Session table — 32 concurrent sessions                          │
│  Tick loop — 2ms heartbeat, drains all sessions every tick       │
│                                                                   │
│  Routes: audio → mixer bus[session]                              │
│          video → ShmCanvas region[canvas_tag]                    │
└──────────┬────────────────────────────────────────┬─────────────┘
           │  /dev/shm/ailang_codec_<id>_pkt         │  _frm
           │  mmap ring (4MB)                        │  mmap ring (4MB)
┌──────────▼────────────────┐           ┌────────────▼────────────┐
│  Codec Worker             │           │  Codec Worker            │
│  mp3_worker / h264_worker │           │  aac_worker              │
│  (standalone C process)   │           │  (same session, linked   │
│                           │           │   by shared pts space)   │
│  libavcodec inside        │           │  libavcodec inside       │
│  speaks ring protocol     │           │  speaks ring protocol    │
└───────────────────────────┘           └──────────────────────────┘
```

---

## 4. The Clock

### Source
`CLOCK_MONOTONIC_RAW` (Linux clock ID 4) via `clock_gettime()` (syscall 228 on x86-64).

- Raw TSC — zero NTP influence, zero frequency slewing
- Invariant TSC on all post-Nehalem (2008+) hardware — fixed frequency regardless of power states
- On WSL2 — maps to Windows `QueryPerformanceCounter` (same hardware path)
- Resolution: nanoseconds

### Implementation
`Library.MediaClock.ailang` — single file, no external dependencies.

```
MediaClock_Init()              record origin_ns = CLOCK_MONOTONIC_RAW now
MediaClock_NowNS()             nanoseconds since init — the one truth
MediaClock_SetSamplesOut(n)    called by audio engine after each ALSA period
MediaClock_AudioNS()           samples_out * 1e9 / 48000
MediaClock_DriftNS()           AudioNS - NowNS (negative = underrun)
MediaClock_PTStoNS(start, pts, timebase)  convert container PTS to absolute ns
```

### Cross-check
Every 2ms tick:
```
expected_samples = NowNS() * 48000 / 1e9
actual_samples   = samples_out
drift            = expected - actual   (negative = underrun)
```

If `|drift| > period_size`, an underrun occurred. MediaCenter logs it and can resync.

---

## 5. Codec Ring Protocol

### Layout
Two rings per session in `/dev/shm`:

```
/dev/shm/ailang_codec_<id>_pkt   packet ring  (MediaCenter → worker)
/dev/shm/ailang_codec_<id>_frm   frame ring   (worker → MediaCenter)
```

Each ring is a 4MB mmap'd file with this header:

```
Offset  Size  Field
0       8     magic ('AILRNG\0\0')
8       8     capacity (data region bytes)
16      8     write_pos (producer advances)
24      8     read_pos  (consumer advances)
32      cap   data[]
```

### Record Format
Variable-length records written into the data region:

```
Offset  Size  Field
0       4     len      (payload bytes, not including this header)
4       2     type     (1=PACKET, 2=FRAME)
6       2     flags    (FLAG_KEYFRAME=1, FLAG_EOF=2, FLAG_FLUSH=4)
8       8     pts_ns   (absolute nanoseconds, MediaClock_PTStoNS output)
16      len   payload
+pad         aligned to 8 bytes
```

### Frame Payload (RTYPE_FRAME)
Begins with a `CRFrameDesc` struct:

```c
typedef struct {
    uint32_t width;         // video: pixel width (0 for audio)
    uint32_t height;        // video: pixel height
    uint32_t pixel_fmt;     // AILFMT_BGRA=1
    uint32_t sample_count;  // audio: decoded samples in frame
    uint32_t sample_rate;   // audio: 48000
    uint16_t channels;      // audio: 2 (stereo)
    uint16_t bit_depth;     // audio: 16
    uint8_t  data[];        // raw BGRA pixels or S16LE PCM
} CRFrameDesc;
```

---

## 6. Codec Workers

### Worker Model
Each codec is a standalone process:
- Launched by MediaCenter via `fork/execve`
- Receives session ID as `argv[1]`
- Opens its rings from `/dev/shm` by session ID
- Decodes in a tight loop: read packet → decode → write frame(s)
- Exits cleanly on `FLAG_EOF` packet after flushing decoder

### Worker ABI
Defined in `MediaCenter/Codec/ailang_codec_abi.h`. Workers must:
1. Open packet ring read-only, frame ring write-only
2. Use the `cr_*` inline helpers from the header
3. Write `CRFrameDesc` + raw data as frame payload
4. Respect `FLAG_EOF` — flush decoder, drain remaining frames, exit

### Building Workers
```bash
cd MediaCenter/Codec
make          # builds all available workers
```

Workers link against the system `libavcodec.so`. The shim is ~200 lines of C. The codec logic is untouched ffmpeg.

### Current Workers
| Worker | Codec | Output |
|--------|-------|--------|
| `mp3_worker` | MP3 (libavcodec) | S16LE 48kHz stereo |

### Planned Workers
| Worker | Codec | Output |
|--------|-------|--------|
| `aac_worker` | AAC | S16LE 48kHz stereo |
| `h264_worker` | H.264 | BGRA frames |
| `h265_worker` | H.265 | BGRA frames |
| `vp9_worker` | VP9 | BGRA frames |
| `av1_worker` | AV1 | BGRA frames |
| `wav_worker` | PCM/WAV | S16LE passthrough |

---

## 7. Session Lifecycle

```
App                    MediaCenter               Codec Worker
 │                          │                         │
 │  media.create            │                         │
 │  {codec, stream,         │                         │
 │   canvas_tag, bus}  ───► │  CodecRing_Create()     │
 │                          │  fork/exec worker  ───► │ opens rings
 │  ◄── {session_id}        │                         │ init decoder
 │                          │                         │
 │  [app feeds packets]     │                         │
 │  media.packet            │                         │
 │  {session_id, pts,  ───► │  CodecRing_WriteRecord  │
 │   dts, data}             │  → pkt ring        ───► │ decode
 │                          │                         │ write frames
 │                          │  MediaSession_Tick()    │
 │                          │  ◄── frm ring      ◄─── │
 │                          │  audio → Mixer_AppWrite  │
 │                          │  video → ShmCanvas_Present
 │                          │                         │
 │  media.stop         ───► │  SIGTERM worker    ───► │ flush + exit
 │                          │  CodecRing_Destroy()    │
```

---

## 8. MediaCenter IPC Protocol

Socket: `/tmp/ailang_media.sock`  
Format: 4-byte big-endian length prefix + JSON (same as display server)

### Client → MediaCenter

| Method | Fields | Response |
|--------|--------|----------|
| `media.create` | `codec` (int), `stream` (1=audio/2=video), `canvas_tag` (str), `mixer_bus` (0=app/1=sys) | `{ok:1, session_id:N}` |
| `media.pause` | `session_id` | `{ok:1}` |
| `media.resume` | `session_id` | `{ok:1}` |
| `media.stop` | `session_id` | `{ok:1}` |
| `media.vol` | `bus` (0=app/1=sys/2=master), `vol` (0-1024) | `{ok:1}` |
| `media.clock` | — | `{now_ns, audio_ns, drift_ns}` |
| `media.quit` | — | `{ok:1}` |

### Codec Type Constants

| Constant | Value | Codec |
|----------|-------|-------|
| `CODEC_MP3` | 1 | MP3 |
| `CODEC_AAC` | 2 | AAC |
| `CODEC_H264` | 3 | H.264 |
| `CODEC_H265` | 4 | H.265 |
| `CODEC_VP9` | 5 | VP9 |
| `CODEC_AV1` | 6 | AV1 |
| `CODEC_WAV` | 7 | PCM/WAV |

---

## 9. Frame Presentation — Clock-Driven

Every 2ms tick in MediaCenter:

```
now_ns = MediaClock_NowNS()
MediaClock_SetSamplesOut(MixerState.samples_written)
Mixer_DrainTick()                            // push ALSA period

for each ACTIVE session:
    while frm_ring has records:
        peek header → pts_ns
        if pts_ns > now_ns: break            // too early, hold
        consume frame
        if audio: Mixer_AppWrite(pcm, bytes)
        if video: ShmCanvas_Present(canvas_tag)
```

No division. No accumulator. Every frame has an absolute nanosecond deadline. The clock is the judge.

---

## 10. File Structure

```
Librarys/Media/
├── Library.MediaClock.ailang      clock singleton — CLOCK_MONOTONIC_RAW
├── Library.CodecRing.ailang       mmap ring protocol
└── Library.MediaSession.ailang    session table, worker lifecycle

MediaCenter/
├── MediaCenter.ailang             service entry point
├── MediaCenter.x                  compiled binary
└── Codec/
    ├── ailang_codec_abi.h         C binary interface contract
    ├── Makefile
    ├── mp3_worker.c               MP3 codec worker
    └── mp3_worker                 compiled binary

TestCode/
└── test_media_clock.ailang        24/24 passing
```

---

## 11. Build

```bash
# Compile MediaCenter service
./ailang.x MediaCenter/MediaCenter.ailang MediaCenter/MediaCenter.x

# Build codec workers (requires libavcodec-dev, libswresample-dev, pkg-config)
cd MediaCenter/Codec && make

# Run tests
./ailang.x TestCode/test_media_clock.ailang test_media_clock.x
./test_media_clock.x

# Run MediaCenter (requires ALSA — run on bare Linux, not WSL2)
./MediaCenter/MediaCenter.x
```

---

## 12. Next Steps

### Immediate (Bob / bare Linux)
- [ ] Test MediaCenter.x with real ALSA — confirm audio init and tick loop
- [ ] Write `h264_worker.c` — video decode, BGRA frame output
- [ ] Wire `videoplayer.ailang` to use MediaCenter instead of forking ffmpeg directly
- [ ] Add `media.packet` dispatch to MediaCenter (demux feeds packets in)

### Short Term
- [ ] Minimal MP4 demuxer in AILang (`Library.Demux.ailang`) — parse box structure, extract H.264 + AAC packet streams, feed to sessions
- [ ] `aac_worker.c`
- [ ] Video canvas routing — `MediaSession_Tick` video path → `ShmCanvas_Present`
- [ ] `media.seek` — send `FLAG_FLUSH` packet, re-anchor `session.start_ns`

### Medium Term
- [ ] `wav_worker.c` — trivial, S16LE passthrough, enables DAW channel model
- [ ] Multi-session stress test — 8 simultaneous sessions on bare Linux
- [ ] Extract codec C files from FFmpeg source (true isolation — no libavcodec.so dependency)
- [ ] VP9, AV1 workers

### GPU / 3D Stack (future)
The mmap ring protocol and `CLOCK_MONOTONIC_RAW` clock are directly reusable for GPU frame submission. The same worker model (isolated process, ring in/out, clock-driven presentation) applies to:
- Vulkan command buffer submission
- 3D scene frame pacing
- Shader compile workers

---

## 13. Design Invariants

- **One clock.** `MediaClock_NowNS()` is the only time source in the media stack.
- **Worker isolation.** Codec workers share zero memory except their assigned rings.
- **Audio first.** Mixer tick runs before session frame drain on every heartbeat.
- **Never block.** All rings are non-blocking. If a ring is full, the write fails — it does not wait.
- **Platform clock only.** `CLOCK_MONOTONIC_RAW` — not `gettimeofday`, not `CLOCK_REALTIME`, not `clock()`.
