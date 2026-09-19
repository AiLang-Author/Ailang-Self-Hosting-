# Opcode16 — player notes

Canonical specification: **https://github.com/AiLang-Author/midi-3** (`SPEC.md`).

This file is not the spec. SynthKit is an implementation. Songmaps use `track N src=FILETRACK:CHANNEL inst=name` (MIDI channel in `src` is 1–16). The player binds InstID from `src`, not from `track` as a channel.

This is the missing MIDI 3.0 piece: a 16-bit named instrument space. MIDI 1.0/2.0 kept the *shape* (timed events, note on/off, tracks) and the *8-bit hardware patch* model. We are not 8-bit hardware. We carry samples. The song must name the instrument. The pack must implement that name. Bind is set intersection, not a guess.

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

---

## 1. What is wrong

| Old object | Width | Meant for | What we did instead |
|---|---|---|---|
| MIDI channel | 4 bits (16) | Which *box* on the DIN cable | Pretend it is a track and an instrument role (ch 10 = drums) |
| Program Change | 7 bits (128) | Slot on *that* box this week | Pretend 73 always means flute |
| Bank Select CC0/CC32 | 7+7 bits | More slots on the box | SF2 bank 128 for kits because 0–127 was “melody” |
| SMF track | unbounded | A pile of events | Optional name, optional program, often neither |
| SF2 preset | (bank, program) | SoundFont table | Player fallback piano |

A song with 25 instruments on “channel 1” is legal SMF and has **no instrument identity**. Patch `25` on a DX7 is not patch `25` in GeneralUser. That is the bank ambiguity. Scripting can rewrite files. The player must not keep the old IDs.

MIDI 2.0 adds 16-bit velocity and 256 channels (16 groups × 16 channels). It does **not** add named instruments. Program is still a number for an outboard unit.

---

## 2. Law

1. **Track ID is 16-bit.** It is the identity of a line in the song. It is not a MIDI channel.
2. **Each track declares exactly one instrument.** Declaration is a **name**. A 16-bit opcode is the interned form of that name. Patch numbers are not a declaration.
3. **Group ID is 16-bit.** Mute, solo, exclusive choke (open/closed hat). Optional. 0 = none.
4. **Sample packs implement opcodes.** They do not invent GM programs. Missing opcode → load fail, not piano.
5. **MIDI channel, GM program, SF2 (bank,prog) exist only in importers.** A translation table may emit Opcode16. The engine never reads them.
6. **Two instruments ⇒ two tracks.** Mid-track program change while notes sound is a failed import. Consecutive programs with a silent gap split into two tracks.

---

## 3. IDs (16-bit, two 8-bit fields)

```
InstID   = (Family << 8) | Member     # u16
TrackID  = u16                        # 0 = first track, not “MIDI ch 0”
GroupID  = u16                        # 0 = none
SampleID = InstID                     # same namespace; region is (note, vel) inside the instrument
```

Family is the first 8 bits. Member is the second. `0x8080` is the user’s example: family 128 woodwinds, member 128 flute.

This is CAN-like: a small numeric ID with a hierarchical split, not a dense 0–127 enum. Sparse is fine. 256 families × 256 members = 65536. Reality is a few hundred named kinds.

**0 is reserved** in every field: `InstID 0` = unset (illegal on a track that has notes). `Family 0` = none. `Member 0` = unspecified member of a family (illegal in v1; must pick a member).

### 3.1 Family table (v1, assigned)

These are **kinds**, not brands. “Ocarina” is a member of pipe/woodwind, not “whatever GeneralUser program 79 is.”

| Family | Hex | Kind |
|---:|---|---|
| 1 | `0x01` | Piano / keys (acoustic) |
| 2 | `0x02` | Electric keys / clav / harpsichord |
| 3 | `0x03` | Organ |
| 4 | `0x04` | Guitar |
| 5 | `0x05` | Bass (acoustic/electric) |
| 6 | `0x06` | Strings (bowed) |
| 7 | `0x07` | Ensemble / choir |
| 8 | `0x08` | Brass |
| 9 | `0x09` | Reed (sax, oboe, bassoon) |
| 10 | `0x0A` | Pipe (lead flutes, recorder) |
| 16 | `0x10` | Synth lead |
| 17 | `0x11` | Synth pad / atmosphere |
| 18 | `0x12` | Synth bass |
| 19 | `0x13` | FX / texture |
| 32 | `0x20` | Tuned percussion (mallets, bells) |
| 33 | `0x21` | Kit (one instrument, note selects piece) |
| 34 | `0x22` | Percussion piece (kick, snare as its own track) |
| **128** | **`0x80`** | **Woodwinds (user: 128/x)** |
| 129 | `0x81` | Brass (extended / historical) |
| 254 | `0xFE` | Analog / oscillator (SynthKit waves 0–7) |
| 255 | `0xFF` | Unpitched / noise / one-shot FX |

Member `0x80` (128) inside family `0x80` = flute → **InstID `0x8080`**.

Member assignment is **`Librarys/Media/opcode16.json`**, loaded at runtime (`Opcode_LoadJson`). The engine interns InstID numbers only. Kind names are JSON (and later SF2 `phdr` / MIDI track names), not AILANG string tables. GM/kit arrays in that JSON are **importers**. Unmapped program → InstID 0 → `BIND_MISS`, not piano.

See `opcode16.json` keys `registry`, `gm`, `kit`. Adding a kind is editing JSON, not recompiling the kernel. Incomplete GM map is correct: those programs bind-fail.

### 3.2 Why not 8-bit InstID

128 GM programs already collided (Ice Rain vs piano vs “prog 96”). Families need room. 8-bit family still fits in a MIDI-sized byte; the second byte is the member. Wire can be two 8-bit values. In-memory it is one u16.

---

## 4. Packet shape (MIDI-shaped, not MIDI)

Keep the good MIDI shape: small opcodes, streamable, 8-bit friendly. Do not keep 7-bit data or 4-bit channel.

### 4.1 Track header (once per track, required)

```
TRACK   u16     TrackID
GROUP   u16     GroupID, 0 = none
INST    u16     InstID from registry (required if the track has notes)
NAME    utf8    human track name (optional)
```

No Program Change. No Bank Select. If you need a different instrument, that is another track.

### 4.2 Stream opcodes (u8)

| Op | Name | Payload |
|---:|---|---|
| `0x00` | NOP | — |
| `0x10` | NOTE_ON | note u16, vel u16, nid u16 |
| `0x11` | NOTE_OFF | nid u16 (not note number — overlapping D6s) |
| `0x20` | CC | cc u16, value u16 |
| `0x21` | BEND | cents i16 |
| `0x30` | TEMPO | us_per_qn u32 |
| `0x3F` | END | — |

Time is **not** in the opcode. File format stores `frame u32` (48 kHz) before each event. Live wire uses the DAC clock / CAN-style successive frames.

**Note** u16: low 8 bits 0–127 are MIDI note for zone match and musicians; high 8 bits extra cents (signed, −128..127) or 0. v1: high byte 0, cents live on BEND / instrument `tune`.

**Vel** u16: 0 = off. 1..65535. MIDI 1.0 7-bit maps with the existing `MIDI_UMP_Scale7to16`.

**Nid** u16: note-id. Off uses nid, not (note, channel).

Instrument is **not** on NOTE_ON. It is on the track. That is the whole point.

### 4.3 CAN-sized live frame (optional physical layer)

8-byte data + 29-bit ID, if we ever sit on CAN or want a compact live packet:

```
29-bit ID:  prio:3 | track:16 | op:8 | 0:2
8-byte data NOTE_ON:  note_u16 | vel_u16 | nid_u16 | reserved_u16
```

Family/member are **not** in the live note packet. The receiver already bound TrackID → InstID at session start (`live.txt` / track header). Re-binding mid-note is a new track.

This is the “fit in an 8-bit data packet” reading: opcode is one byte, IDs are 16-bit fields inside a small payload. We are not stuffing GM into 7 bits.

---

## 5. Three namespaces (do not collapse them)

```
Kind        InstID + name     "this line is a flute"
Track       TrackID           "sung melody"
Realization pack + samples    "these WAVs are flute at 48 kHz"
```

**Song** lists tracks → InstID (or name, interned at compile).  
**Pack** lists InstID → regions/samples.  
**Bind:** every InstID in the song exists in the pack, or the song does not arm.

```
song track 4  name=Lead   inst=calliope    # registry 0x1003
pack GeneralUser implements 0x1003 with SFZ/compiled regions
bind OK
```

```
song track 4  inst=calliope
pack PTQ implements piano_grand, whistle, … no calliope
BIND FAIL track 4 calliope
```

No `{stem}/b0/p82`. The stem is which **pack** you loaded. The opcode is which **kind** the track is. Same song, different pack: bind succeeds only if that pack implements the kinds.

---

## 6. Percussion (no channel 10)

- **Kit:** InstID family `0x21`. One track. Note number selects the piece (`pitch_keytrack=0` on regions). The track *declares* `kit_standard`.
- **Piece:** InstID family `0x22`. One track per drum if you want a snare line of its own.
- SMF channel 10 with no declaration → **import fail** unless a sidecar says `inst=kit_standard`. Never `ch==9 → bank 128`.

---

## 7. Samples (same IDs)

A sample pack is a directory:

```
packs/GeneralUser-GS/
  pack.toml          # name, sample_rate=48000
  instreg.map        # optional local aliases
  flute.sfz          # or flute/ with regions
  ocarina.sfz
  kit_standard.sfz
  ...
```

`pack.toml`:

```
name = "GeneralUser-GS"
rate = 48000
implement 0x8080 = flute.sfz
implement 0x8083 = ocarina.sfz
implement 0x1003 = calliope.sfz
implement 0x2101 = kit_standard.sfz
```

SF2 compile **emits this map**, it does not stay the player. GM program 79 → `0x8083 ocarina` is a line in `gm_import.map`, used only when ingesting `.mid`. After ingest, the `.aisong` (or whatever on-disk song IR) has TrackID + InstID only.

Region match inside an instrument stays a total function of (note, vel): all matching layers play, zero matches = silence + miss. That is instrument data, not addressing.

---

## 8. SMF ingest (scriptable, then throw away MIDI IDs)

1. Parse SMF (existing `Library.MIDI`).
2. Split Type 0 by channel; Type 1 by file track, then by channel if mixed.
3. Each resulting stream becomes a TrackID 0,1,2,…
4. Instrument: sidecar name/opcode **preferred**. Else `gm_import.map` on a *declared* Program Change. Else **fail**.
5. Write Opcode16 song (headers + events). Original `.mid` is source, not runtime.

Sidecar (data):

```
# songmap v1
track 0  inst=bass_electric
track 1  inst=piano_grand
track 2  inst=calliope
track 9  inst=kit_standard
```

Names, not `b128/p0`.

---

## 9. Engine (what we keep / burn)

**Keep:** voice pool, 48 kHz, `Smp_StepD`, signed cents, steal idle→release→quiet, host chrome, AILANG kernel, DAC clock.

**Burn as runtime:** `SK_NoteOn` channel 9 → bank 128, program 0 fallback, `OSC_FALLBACK` for missing GM, `{stem}/b{bank}/p{prog}` as the song’s identity, `ch & 15` as track id.

**New:** TrackID u16 on the voice (`SOsc.TRACK`), InstID u16 on the track, nid Off, pack bind before first sample.

---

## 10. Open (product)

1. Registry ownership: one global `instreg v1` in-tree vs packs can add members in 128–255 of a family.
2. Kit notes: keep MIDI drum note numbers as `0x22` members for import, or force sidecar names (`kick`, `snare`) only.
3. On-disk song: text (headers + events) vs binary IR. Text is greppable; binary is what the kernel mmap’s.
4. How complete `gm_import.map` must be on day one (128 GM + drum kit vs only what The Sign / 1943 need).

---

## 11. Not this spec

- SFZ opcode list (instrument *realization*; separate, closed subset).
- Analog knobs, filter math, mixer NCH.
- MIDI 2.0 Clip files as the song format.
- Kontakt, sfizz, FluidLite as engine.
