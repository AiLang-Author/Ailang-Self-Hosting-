# Media Pipeline Atomization Plan — Option 4

## Design Principle: Orthogonality

Every component in this pipeline is a standalone process that communicates exclusively through two primitives: **PacketRing** (shm data transport) and **PlaybackClock** (shm timing/control). No component imports or links against another. Any component can be replaced, removed, or duplicated without affecting the rest. The pipeline is a graph of interchangeable nodes, not a stack.

This means:
- A demuxer doesn't know or care what consumes its output
- A decoder doesn't know if its input came from a demuxer, a network source, or a test harness
- A mixer is just another node: PacketRing in, PacketRing out — insert it or skip it
- The presenter doesn't know if audio went through a mixer or came straight from a decoder
- Any node can be an Ailang binary, a C shim, or anything that speaks the PacketRing layout

---

## Goal

Replace the monolithic `ffmpeg` fork/exec blob in `videoplayer.ailang` with a modular pipeline of orthogonal processes, all connected by shared memory ring buffers with a wall-clock synchronization system.

---

## Current State

The video player (`Applications/videoplayer.ailang`, 1084 lines) does this:

```
fork/exec ffmpeg -re -i file \
  -map 0:v -f rawvideo -pix_fmt bgra -s WxH pipe:1 \
  -map 0:a -af volume=2.0 -f s16le -ar 48000 -ac 2 pipe:4
```

FFmpeg handles everything: container parsing, codec decoding, pixel format conversion, resampling, and pacing (`-re`). The player just reads two pipes and blits. This works but:

- No control over individual codecs (can't swap, can't rewrite)
- FFmpeg is a 30MB+ monolith linked against everything
- `-re` flag is a crude timing mechanism (it paces output, not presentation)
- Seek requires killing and relaunching the process
- No proper wall-clock sync — relies on ffmpeg's output rate + audio sample counting

---

## Architecture Overview

Every box below is a separate process. Every arrow is a PacketRing over `/dev/shm`. The PlaybackClock is a shared shm region all nodes can read; only the presenter writes control state.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         PRESENTER (Ailang)                            │
│  Reads decoded frames, blits to ShmCanvas, writes PCM to AudioSink.  │
│  Owns the PlaybackClock. Orchestrates process lifecycle.              │
├──────────────────────────────────────────────────────────────────────┤
│       ▲ video frames (BGRA)       ▲ audio samples (S16LE)            │
│       │ dec_video ring            │ dec_audio ring                    │
│       │                           │                                   │
│       │                     ┌─────┴──────┐                            │
│       │                     │ MIXER      │ ◄── optional, same         │
│       │                     │ (process)  │     PacketRing in/out      │
│       │                     │ N inputs → │     can be bypassed        │
│       │                     │ 1 output   │                            │
│       │                     └─────┬──────┘                            │
│       │                           │ (or direct if no mixer)           │
├───────┴───────────┬───────────────┴──────────────────────────────────┤
│  VIDEO DECODER    │  AUDIO DECODER                                    │
│  (C shim process) │  (C shim process)                                 │
│  PacketRing in    │  PacketRing in                                    │
│  PacketRing out   │  PacketRing out                                   │
├───────────────────┴──────────────────────────────────────────────────┤
│       ▲ video packets             ▲ audio packets                     │
│       │ pkt_video ring            │ pkt_audio ring                    │
├───────┴───────────────────────────┴──────────────────────────────────┤
│                      DEMUXER (Ailang)                                 │
│  PacketRing out (video) + PacketRing out (audio)                      │
│  One per container format. Reads file, writes packets.                │
└──────────────────────────────────────────────────────────────────────┘
```

### Without mixer (direct, initial implementation)

```
demuxer → [pkt_video ring] → video_decoder → [dec_video ring] → presenter → ShmCanvas
demuxer → [pkt_audio ring] → audio_decoder → [dec_audio ring] → presenter → ALSA
```

### With mixer (drop-in later, zero changes to demuxer or decoders)

```
demuxer → [pkt_audio ring] → audio_decoder → [dec_audio_raw ring] → MIXER → [dec_audio ring] → presenter → ALSA
                                              other_source ────────→ MIXER ↗
```

The mixer reads N input PacketRings, mixes S16LE samples, writes one output PacketRing. The presenter doesn't know or care whether a mixer is in the chain — it reads the same `dec_audio` ring either way. The decoders don't know either — they write to their output ring regardless.

Plus one small shm region visible to all nodes: the **PlaybackClock**.

---

## Phase 1: Shared Memory Packet Ring Buffer

**New library: `Librarys/Library.PacketRing.ailang`**

A lock-free SPSC (single-producer, single-consumer) ring buffer over `/dev/shm`. Different from the existing `DRing` system which uses fixed-size entries for compositor events. This one handles variable-size media packets.

### Layout

```
/dev/shm/ailang_media_ring_<name>

Offset  Size   Field
0       8      write_pos       (producer writes, consumer reads)
8       8      read_pos        (consumer writes, producer reads)
16      8      capacity        (power of 2, e.g. 4MB)
24      8      flags           (FLUSH, EOF, ERROR)
32      -      data region     (ring of length-prefixed packets)
```

Each packet in the data region:

```
Offset  Size   Field
0       4      packet_size     (bytes of payload)
4       8      pts_usec        (presentation timestamp, microseconds)
12      4      flags           (KEYFRAME, CONFIG, FLUSH)
16      N      payload         (compressed packet data)
```

### Key functions

```
PacketRing_Create(name, capacity) -> shm_ptr
PacketRing_Open(name) -> shm_ptr
PacketRing_Write(ring, data, size, pts_usec, flags) -> 0/1
PacketRing_Read(ring, out_buf, out_size, out_pts, out_flags) -> 0/1
PacketRing_SignalEOF(ring)
PacketRing_SignalFlush(ring)
PacketRing_Destroy(name)
```

SPSC means no locks needed — just atomic reads/writes with proper memory ordering. One producer, one consumer per ring.

---

## Phase 2: PlaybackClock

**New library: `Librarys/Library.PlaybackClock.ailang`**

A 64-byte shm region that anchors playback to wall-clock time.

### Layout

```
/dev/shm/ailang_media_clock_<session_id>

Offset  Size   Field
0       8      state           (STOPPED=0, PLAYING=1, PAUSED=2, SEEKING=3)
8       8      epoch_usec      (CLOCK_MONOTONIC value when play started)
16      8      pause_offset    (accumulated pause time in usec)
24      8      rate_num        (playback rate numerator, 1000 = 1.0x)
32      8      rate_den        (playback rate denominator, 1000)
40      8      seek_target     (target PTS in usec, set by presenter)
48      8      audio_hw_pos    (frames written to ALSA, set by presenter)
56      8      reserved
```

### How it works

**Play start:**
```
clock.epoch_usec = clock_gettime(CLOCK_MONOTONIC)
clock.pause_offset = 0
clock.state = PLAYING
```

**Current media time (called by presenter, demuxer, decoders):**
```
if state == PLAYING:
    elapsed = clock_gettime(MONOTONIC) - epoch_usec - pause_offset
    media_time = elapsed * rate_num / rate_den
    return media_time
if state == PAUSED:
    return (pause_start - epoch_usec - pause_offset) * rate_num / rate_den
```

**Presenter frame scheduling:**
```
frame_target = frame.pts_usec
media_now = PlaybackClock_MediaTime(clock)

if media_now < frame_target:
    // too early — hold frame, sleep (frame_target - media_now)
if media_now > frame_target + DROP_THRESHOLD:
    // too late — drop frame, pull next
else:
    // on time — blit to ShmCanvas, present
```

**Audio writes anchor the clock:**
The presenter writes `audio_hw_pos` (from `Mixer_GetSamplesWritten()`) every tick. If audio drifts from the monotonic clock by more than a threshold (e.g. 10ms), the presenter adjusts `epoch_usec` to re-anchor. Audio is always the authority — the monotonic clock is just the mechanism.

**Pause:**
```
pause_start = clock_gettime(MONOTONIC)
clock.state = PAUSED
// on resume:
clock.pause_offset += clock_gettime(MONOTONIC) - pause_start
clock.state = PLAYING
```

**Seek:**
```
clock.state = SEEKING
clock.seek_target = target_pts_usec
// demuxer sees SEEKING, flushes rings, seeks in container, signals decoders to flush
// when demuxer resumes feeding:
clock.epoch_usec = clock_gettime(MONOTONIC) - target_pts_usec
clock.pause_offset = 0
clock.state = PLAYING
```

### Key functions

```
PlaybackClock_Create(session_id) -> shm_ptr
PlaybackClock_Open(session_id) -> shm_ptr
PlaybackClock_Play(clock)
PlaybackClock_Pause(clock)
PlaybackClock_Resume(clock)
PlaybackClock_Seek(clock, target_usec)
PlaybackClock_MediaTime(clock) -> usec
PlaybackClock_SetRate(clock, num, den)
PlaybackClock_SetAudioHWPos(clock, frames_written)
PlaybackClock_Destroy(session_id)
```

---

## Phase 3: Demuxers (Ailang)

One demuxer binary per container family. Each is a standalone Ailang program that:

1. Opens the media file
2. Parses container headers (tracks, codecs, timebases)
3. Opens two PacketRings (video + audio)
4. Opens the PlaybackClock (reads state, seek_target)
5. Loops: extract next packet, convert PTS to microseconds, write to appropriate ring
6. Respects clock state (pause = stop feeding, seek = seek in container + flush rings)

### Demuxer binaries

| Binary | Container | Spec complexity | Priority |
|--------|-----------|-----------------|----------|
| `demux_mp4.x` | MP4/MOV (ISO BMFF) | Medium — box-based, well-documented | 1st |
| `demux_mkv.x` | MKV/WebM (EBML) | Medium — variable-length integers, nested elements | 2nd |
| `demux_wav.x` | WAV/RIFF | Trivial — fixed header + raw PCM | 3rd (good test case) |
| `demux_avi.x` | AVI/RIFF | Low — legacy but simple | 4th |
| `demux_flac.x` | FLAC | Low — fixed header + frames | 5th |

### Demuxer output

Each demuxer writes a small header to stdout (JSON or fixed struct) announcing:
- Video codec ID (H264, VP9, AV1, etc.)
- Audio codec ID (AAC, OPUS, VORBIS, MP3, etc.)
- Video dimensions, framerate
- Audio sample rate, channels
- Total duration (if known)

The presenter reads this to know which decoder processes to launch.

### Demuxer IPC control

The demuxer reads the PlaybackClock shm for state changes. No separate control socket needed — the clock IS the control channel:
- `state == SEEKING` → demux seeks to `seek_target`, flushes rings
- `state == PAUSED` → demux stops reading (rings will fill, natural backpressure)
- `state == STOPPED` → demux exits

### Container parsing notes

**MP4 (ISO BMFF):** Recursive box parsing. `moov` box contains `trak` entries, each `trak` has `mdia/minf/stbl` with sample tables (`stts`, `stsc`, `stsz`, `stco`/`co64`). Sample-to-chunk + chunk-offset tables give byte positions of every packet. Seek = binary search in `stts` for target PTS, find nearest keyframe in `stss`.

**MKV (EBML):** Variable-length element IDs and sizes (like UTF-8 encoding for integers). `Segment/Tracks` for codec info, `Segment/Cluster/SimpleBlock` for packets. Cues element for seek index. WebM is MKV subset (VP8/VP9/AV1 + Opus/Vorbis only).

**WAV:** 44-byte header (RIFF + fmt + data chunks). Everything after the header is raw PCM. Seek = byte offset math. Trivial — good first implementation to prove the pipeline.

---

## Phase 4: Codec Decoder Processes (C shims)

Each decoder is a tiny C program (~100-200 lines) that:

1. Opens input PacketRing (compressed packets from demuxer)
2. Opens output PacketRing (decoded frames to presenter)
3. Opens PlaybackClock (reads state for flush/stop)
4. Initializes the codec library
5. Loops: read packet → decode → write decoded output
6. On FLUSH signal: flush codec internal buffers, drain output ring

### Video decoders

| Binary | Codec | Library | Notes |
|--------|-------|---------|-------|
| `decode_h264.x` | H.264/AVC | OpenH264 (`libopenh264`) | Cisco's BSD-licensed decoder. ~2MB. Decode-only is simple API. |
| `decode_h265.x` | H.265/HEVC | libde265 | LGPL, ~500KB. Clean decode API. |
| `decode_vp9.x` | VP9 | libvpx | BSD, Google-maintained. `vpx_codec_decode()` + `vpx_codec_get_frame()`. |
| `decode_av1.x` | AV1 | dav1d | BSD, VideoLAN. Best AV1 decoder, clean API. |

**Video decoder output format:** Raw BGRA pixels, same as current. Each output packet = one full frame + PTS.

**Output packet in video decode ring:**
```
[4 bytes: size] [8 bytes: pts_usec] [4 bytes: flags] [W*H*4 bytes: BGRA pixels]
```

### Audio decoders

| Binary | Codec | Library | Notes |
|--------|-------|---------|-------|
| `decode_aac.x` | AAC | faad2 or fdk-aac | faad2 is simpler API, fdk-aac is higher quality. |
| `decode_opus.x` | Opus | libopus | BSD, reference implementation. `opus_decode()` is one function. |
| `decode_mp3.x` | MP3 | libmpg123 | LGPL, ~200KB. `mpg123_decode()` is trivial. |
| `decode_vorbis.x` | Vorbis | libvorbis + libogg | BSD. Mainly for MKV/WebM. |
| `decode_pcm.x` | PCM/WAV | None needed | Pass-through — just copy packets, maybe endian swap. |
| `decode_flac.x` | FLAC | libFLAC | BSD, reference implementation. |

**Audio decoder output format:** S16LE 48kHz stereo, same as current. Resampling (if source != 48kHz) done inside the decoder process using a simple linear resampler or libsamplerate.

### C shim template (pseudocode)

```c
int main(int argc, char *argv[]) {
    // argv: input_ring_name, output_ring_name, clock_name, codec_params...

    void *in_ring  = packetring_open(argv[1]);
    void *out_ring = packetring_open(argv[2]);
    void *clock    = playbackclock_open(argv[3]);

    codec_ctx *ctx = codec_init(/* params from argv */);

    uint8_t pkt_buf[MAX_PACKET];
    uint8_t frame_buf[MAX_FRAME];
    int64_t pts;
    uint32_t flags;

    while (1) {
        int clock_state = *(volatile int64_t *)clock;
        if (clock_state == STOPPED) break;
        if (clock_state == SEEKING) { codec_flush(ctx); continue; }

        if (!packetring_read(in_ring, pkt_buf, &pkt_size, &pts, &flags)) {
            if (flags & FLAG_EOF) break;
            usleep(1000); // ring empty, wait 1ms
            continue;
        }

        int frame_size = codec_decode(ctx, pkt_buf, pkt_size, frame_buf);
        if (frame_size > 0) {
            while (!packetring_write(out_ring, frame_buf, frame_size, pts, 0)) {
                usleep(500); // output ring full, backpressure
            }
        }
    }

    codec_cleanup(ctx);
    return 0;
}
```

### Building the C shims

Each shim compiles to a small standalone binary:

```bash
gcc -O2 -o decode_h264.x decode_h264.c packetring.c -lopenh264
gcc -O2 -o decode_av1.x  decode_av1.c  packetring.c -ldav1d
gcc -O2 -o decode_opus.x decode_opus.c packetring.c -lopus
# etc.
```

`packetring.c` is a small C library (~100 lines) that mirrors the Ailang PacketRing interface for the shm ring buffers. Same layout, same protocol.

---

## Phase 5: Presenter (Reworked videoplayer.ailang)

The presenter replaces the current `videoplayer.ailang`. It becomes the orchestrator — but critically, it only touches two interfaces: PacketRing (for reading decoded data) and PlaybackClock (for timing). It does NOT import or depend on any demuxer, decoder, or mixer code.

### AudioSink abstraction

The presenter writes decoded PCM to an **AudioSink** — a PacketRing output. What happens downstream is not its concern:

**Mode A — Direct (no mixer, initial implementation):**
Presenter reads `dec_audio` ring, writes directly to ALSA via the existing AudioEngine calls. Simple, works now.

**Mode B — Via mixer (drop-in later):**
Presenter reads `mixed_audio` ring (output of mixer process), writes to ALSA. The mixer consumed `dec_audio` ring plus any other sources. Presenter code doesn't change — only the ring name it reads from changes (config/argv).

**Mode C — Headless / pipe out:**
Presenter reads `dec_audio` ring, writes raw PCM to a file or pipe. No ALSA at all. Useful for transcoding, testing.

The presenter accepts the audio input ring name as a parameter. It doesn't know or care what produced the data in that ring.

### Startup sequence

1. Receive file path (via IPC action or argv)
2. Probe file: read first 12 bytes, detect container format
3. Create shm rings: `pkt_video`, `pkt_audio`, `dec_video`, `dec_audio`
4. Create PlaybackClock
5. Fork/exec the appropriate demuxer, pass ring names + clock name + file path
6. Read demuxer's stdout header to learn codec IDs, dimensions, sample rate
7. Fork/exec the appropriate video decoder, pass input/output ring names + clock name
8. Fork/exec the appropriate audio decoder, pass input/output ring names + clock name
9. (Optional) Fork/exec mixer if configured, remap ring names so presenter reads mixer output
10. Begin playback loop

### Main loop (replaces current VP tick)

```
// audio_ring = dec_audio (direct) or mixed_audio (via mixer) — set at startup

every 2ms tick:
    // 1. Drain decoded audio from audio ring -> ALSA
    while PacketRing_Read(audio_ring, audio_buf, ...):
        Mixer_AppWrite(audio_buf, size)    // existing AudioEngine, writes to ALSA
    Mixer_DrainTick()

    // 2. Update clock with audio hardware position
    PlaybackClock_SetAudioHWPos(clock, Mixer_GetSamplesWritten())

    // 3. Get current media time from clock
    media_now = PlaybackClock_MediaTime(clock)

    // 4. Present video frame if it's time
    if have_pending_frame == false:
        if PacketRing_Read(dec_video, frame_buf, &frame_pts, ...):
            have_pending_frame = true

    if have_pending_frame:
        if frame_pts <= media_now:
            // check if NEXT frame is also past due (drop this one)
            if PacketRing_Peek(dec_video) and next_pts <= media_now:
                frames_dropped++
                // pull next frame instead
            else:
                MemoryCopy(shm_canvas_buf, frame_buf, frame_size)
                ShmCanvas_Present(sock, win_id)
                frames_presented++
                have_pending_frame = false

    // 5. Handle IPC actions (play/pause/seek/stop/volume)
    Poll_IPC()
```

### Action handling

| Action | Behavior |
|--------|----------|
| `v.play` / Space | `PlaybackClock_Play()` or `PlaybackClock_Resume()` |
| `v.paus` / Space | `PlaybackClock_Pause()` |
| `v.stop` / S | `PlaybackClock_Stop()`, kill child processes, destroy rings |
| `v.seek.fwd` / Right | `PlaybackClock_Seek(clock, media_now + 10_000_000)` (10s forward) |
| `v.seek.bck` / Left | `PlaybackClock_Seek(clock, media_now - 10_000_000)` (10s back) |
| `doc.open` | Stop current, start new file |
| Up/Down | Volume via `Mixer_SetMasterVol()` (ALSA-level, independent of pipeline) |

### Process management

The presenter tracks PIDs of all child processes (demuxer + decoders + optional mixer). On stop or file change:
1. Set clock state to STOPPED
2. Wait briefly for children to exit (they poll clock state)
3. SIGTERM any that didn't exit
4. Destroy shm rings + clock
5. Clean up `/dev/shm/ailang_media_*` files

---

## Phase 5b: Mixer Node (Optional, orthogonal)

The mixer is a standalone process — just another pipeline node. It is NOT required for playback. It exists to combine multiple audio sources into one output.

### Interface

```
mixer_audio.x <input_ring_1> [input_ring_2] ... [input_ring_N] <output_ring> <clock_name>
```

- Reads S16LE 48kHz stereo from N input PacketRings
- Mixes samples (sum + clamp16, with per-input volume from clock or control shm)
- Writes S16LE 48kHz stereo to one output PacketRing
- Reads PlaybackClock for state (pause = stop draining, stop = exit)

### What it enables (later)

- Multiple audio sources playing simultaneously (video + notification sounds + music)
- Per-source volume control
- System sound bus (UI clicks, alerts) mixed with app audio
- Recording/capture tap (fork the output ring)

### Integration with existing AudioEngine

The current `Library.AudioEngine.ailang` has a 3-bus mixer (AppBus, SysBus, Master) built into the presenter process. Two paths forward:

**Path A — Keep AudioEngine as the ALSA sink, use new mixer for pre-mix:**
The new mixer process combines multiple decoded streams into one PacketRing. The presenter reads that single ring and feeds it into AudioEngine's AppBus as today. AudioEngine still handles the final ALSA write + system sounds on SysBus. This requires zero changes to AudioEngine.

**Path B — Replace AudioEngine mixer with the new mixer process (later):**
Move all mixing into the external mixer process. AudioEngine becomes a thin ALSA writer only (Audio_Init + Audio_WriteFrames, no bus logic). The mixer process handles all volume, all sources. More orthogonal, but more work.

**Recommendation: Path A first.** It's additive. AudioEngine already works. The new mixer slots in upstream of it. Path B can happen later if needed.

### Mixer shm layout (optional per-input control)

```
/dev/shm/ailang_media_mixer_ctl_<session_id>

Offset  Size   Field
0       8      num_inputs
8       8      input_0_vol     (0-1024, 256=unity)
16      8      input_1_vol
...
N*8+8   8      master_vol
```

The presenter (or any controller) can adjust per-input volumes by writing to this shm region. The mixer reads it each tick. No IPC messages needed — just shared memory.

---

## Phase 6: Format Detection

**New library: `Librarys/Library.MediaProbe.ailang`**

Reads the first 16 bytes of a file and returns container + likely codec info.

```
Magic bytes:
  00 00 00 xx 66 74 79 70  →  MP4  (ftyp box)
  1A 45 DF A3              →  MKV/WebM (EBML header)
  52 49 46 46 ... 41 56 49 →  AVI  (RIFF....AVI)
  52 49 46 46 ... 57 41 56 →  WAV  (RIFF....WAV)
  66 4C 61 43              →  FLAC (fLaC)
  4F 67 67 53              →  OGG  (OggS)
  FF FB / FF F3 / FF F2    →  MP3  (frame sync)
  49 44 33                 →  MP3  (ID3 tag)
```

Returns a struct with container_type, so the presenter knows which demuxer to launch.

---

## Implementation Order

### Step 1 — PacketRing library (Ailang + C mirror)
Write `Library.PacketRing.ailang` and `packetring.c`. Test with a trivial producer/consumer that writes and reads dummy packets across two processes. This is the foundation — every other component depends on it.

### Step 2 — PlaybackClock library (Ailang + C mirror)
Write `Library.PlaybackClock.ailang` and `playbackclock.c`. Test monotonic timing, pause/resume math, seek reset. Second foundation piece.

### Step 3 — WAV demuxer + PCM pass-through decoder
Simplest possible end-to-end test. WAV is trivial to parse (44-byte header + raw PCM). PCM decoder is a no-op copy. Proves the full pipeline works: demuxer → ring → decoder → ring → presenter → AudioEngine → speakers. No video, no complex codecs — just audio through the pipe.

### Step 4 — MediaProbe library
File detection so the presenter can pick the right demuxer.

### Step 5 — Rework videoplayer.ailang into presenter
Replace ffmpeg fork/exec with process orchestration. Parameterize the audio input ring name (for future mixer drop-in). Keep existing ShmCanvas and AudioEngine integration. Add clock-driven frame scheduling.

### Step 6 — MP4 demuxer
Parse ISO BMFF boxes, extract H.264/AAC packets with correct PTS. This is the most important container — covers most video files.

### Step 7 — H.264 decoder shim (OpenH264)
C shim wrapping `libopenh264`. Input: H.264 NAL packets from ring. Output: BGRA frames to ring.

### Step 8 — AAC decoder shim (faad2)
C shim wrapping `libfaad`. Input: AAC packets. Output: S16LE 48kHz stereo.

### Step 9 — MKV/WebM demuxer
EBML parsing, Cluster/SimpleBlock extraction. Covers VP9+Opus (YouTube downloads) and H.264+AAC in MKV.

### Step 10 — Additional codec shims as needed
VP9 (libvpx), Opus (libopus), AV1 (dav1d), MP3 (libmpg123), FLAC (libFLAC). Each is a ~150-line C file. Add as formats are needed.

### Step 11 — Mixer node (when needed, not before)
Standalone mixer process. Reads N input PacketRings, writes 1 output PacketRing. Only build this when you actually need multiple simultaneous audio sources. The presenter already accepts an arbitrary ring name — swapping in the mixer output requires zero code changes to any other component.

---

## File Inventory (New Files)

```
Librarys/
  Library.PacketRing.ailang          # shm SPSC ring buffer for media packets
  Library.PlaybackClock.ailang       # wall-clock sync over shm
  Library.MediaProbe.ailang          # container format detection

Librarys/Media/
  Library.DemuxWAV.ailang            # WAV/RIFF demuxer
  Library.DemuxMP4.ailang            # MP4/MOV demuxer
  Library.DemuxMKV.ailang            # MKV/WebM demuxer

Media/                               # C shim sources + build
  packetring.h / packetring.c        # C mirror of PacketRing (shared by all shims)
  playbackclock.h / playbackclock.c  # C mirror of PlaybackClock
  decode_h264.c                      # OpenH264 wrapper
  decode_h265.c                      # libde265 wrapper
  decode_vp9.c                       # libvpx wrapper
  decode_av1.c                       # dav1d wrapper
  decode_aac.c                       # faad2 wrapper
  decode_opus.c                      # libopus wrapper
  decode_mp3.c                       # libmpg123 wrapper
  decode_pcm.c                       # PCM pass-through
  decode_flac.c                      # libFLAC wrapper
  mixer_audio.c                      # N-input mixer node (optional, Step 11)
  Makefile                           # builds all shims

Applications/
  videoplayer.ailang                 # reworked into presenter/orchestrator
```

### Orthogonality test

Every binary in this list can be tested in isolation:
- `packetring` test: producer writes N packets, consumer reads N packets, verify data integrity
- `playbackclock` test: play/pause/resume, verify media time math
- `demux_wav.x` test: feed it a WAV file, read output ring, verify packet count matches sample count
- `decode_h264.x` test: feed it raw NAL packets via ring, verify BGRA output dimensions
- `mixer_audio.x` test: feed it two sine wave rings, verify mixed output
- Each test uses the same PacketRing/PlaybackClock primitives. No test needs any other component running.

---

## What This Gives You

1. **Orthogonality**: Every component talks through two primitives (PacketRing + PlaybackClock). No component imports another. Swap, remove, duplicate, or rewrite any node without touching any other node. A demuxer doesn't know what reads its output. A decoder doesn't know what wrote its input. The mixer is optional — insert it or don't, nothing else changes.

2. **Crash isolation**: Decoder segfaults? Presenter detects child exit, cleans up, shows error. Display server never touched. Other pipeline nodes keep running.

3. **Proper timing**: Wall-clock anchored playback via CLOCK_MONOTONIC. Frames presented at the right real-world time, not "whenever ffmpeg feels like outputting them." Audio hardware position cross-checks the monotonic clock for drift correction.

4. **Seek that works**: Clock enters SEEKING state, demuxer seeks in container to nearest keyframe, flushes rings, decoders flush internal state, clock re-anchors, playback resumes from new position. All coordinated through the shared clock — no control messages bouncing between processes.

5. **Rewritability**: Demuxers are pure Ailang from day one. Codec shims are tiny C files you can eventually replace with Ailang implementations. The ring buffer and clock are format-agnostic infrastructure that works for any future use case (streaming, recording, transcoding).

6. **Mixer-ready without mixer code**: The presenter reads from a named ring. Today that ring comes from a decoder. Tomorrow it comes from a mixer. The day after, it comes from a network source. Zero code changes — just a different ring name at launch.

7. **No FFmpeg dependency**: Zero lines of FFmpeg code. Each codec library is small, focused, and independently licensed (mostly BSD). You can audit, patch, or replace any single codec without rebuilding anything else.

8. **Testable in isolation**: Every binary can be tested standalone with synthetic input. No integration test needed to verify a single component. Feed a ring, read a ring, check the output.
