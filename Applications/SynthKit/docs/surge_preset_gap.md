# Surge XT preset gap

A Surge XT `.fxp` file is a VST chunk whose payload is one XML patch.
An Init patch holds about 560 parameter values. A played preset adds
modulation routes, and may add step sequences, drawn envelopes, formulas,
and wavetable data.

The sample player does not read these files. Playback of a MIDI 3 pack
stays on wave 8 and `Synth_SampleBlock`. Nothing in this document changes
that path.

The synth is a second instrument on its own IPC directory. The window only
writes files. The engine owns voices, envelopes, and the modulation routes.

## What one preset describes

Each preset has two full scenes, A and B. Scene mode is single, key-split,
or both at once.

Per scene:

- 3 oscillators. Types, in file order: Classic, Sine, Wavetable,
  sample-and-hold noise, audio input, FM3, FM2, Window, Modern, String,
  Twist, Alias. Each has octave, pitch, keytrack, retrigger, and up to
  7 shape parameters.
- Mixer: level, mute, solo, and a route of each oscillator to filter 1,
  filter 2, or both. Oscillator FM and feedback.
- 2 filters, serial or parallel. About 35 algorithms (12 dB and 24 dB
  lowpass, highpass, bandpass, notch, ladders, comb, allpass, warps).
  Cutoff, resonance, keytrack, envelope depth. A waveshaper in that path.
- 2 envelopes (loudness and filter). Times are `log2(seconds)`: −8 is
  about 4 ms, 0 is 1 second. Sustain is 0 to 1. Each stage has a curve.
- 12 modulators (6 per voice, 6 per scene). A modulator is an LFO, a step
  sequencer, a drawn envelope, or a formula.
- Modulation list. Each entry is `source`, `depth`, and a target parameter.
  Sources use the Surge `modsources` numbers: velocity 1, keytrack 2,
  mod wheel 6, amp envelope 15, filter envelope 16, LFO 1 is 17.
  Eight macro knobs are sources too.
- Play mode: poly, several mono and portamento modes, drift, bend range.

After the scenes, up to 16 effect slots. About 30 effect types (delay,
reverb, phaser, chorus, distortion, EQ, and the rest), each with its own
parameters.

## What the engine can sound today

| Preset asks for | Engine has |
|---|---|
| 3 oscillators, 12 types | 2 oscillators. Sine, square, pulse, saw, triangle, noise, NES triangle, user wave. Oscillator 2 is mix plus octave. One sub level. |
| Oscillator FM, mute, solo, filter assign | Not present. |
| 2 filters, ~35 types | 1 lowpass. Cutoff and resonance are single knobs. |
| 2 envelopes with curves | Loudness envelope and a separate filter envelope. Both use sample counts, so a stage can be several seconds. Curves are still linear. |
| 12 modulators, step sequences, drawn envelopes, formulas | 1 LFO, tapped to pulse width, filter, or loudness. |
| A route list from any source to any knob | 3 fixed slots in the synth window, applied by the host over IPC. |
| Scene B, split, dual | One scene. |
| 16 effect slots | 1 delay: time, feedback, wet mix. |
| Wavetable oscillators | Not present. Sample playback is the other instrument, not an oscillator type. |

The window only writes the `.fxp` path. `Library.SurgePatch` reads scene A:
oscillator 1 and 2, cutoff in semitones, resonance, both envelopes, and the
routes for filter cutoff, pitch, and resonance. Classic shape 0 (the center)
is a saw. Clearly negative shapes are pulse or square. Sine, FM2, FM3, and
Window use the sine. Noise uses noise. Wavetable, Modern, String, Twist, and
Alias do not have their own oscillator yet, so they play as a saw and the
log prints the real type number. A knob does not replace the patch value
unless that knob moved after the patch was loaded. The master volume always
follows its slider.

## How the missing routing is being built

Routes live in the engine, not in the window.

`LinkagePool.MRoute` is one route: Surge source number, destination number,
depth, and the next route. `LinkagePool.MLists` is the free list and the
live list. Adding or removing a route does not resize a fixed array and
does not touch a sample voice.

Depth is engine units. 256 on the source is "full". A cutoff depth of
65536 swings the lowpass across its whole range when the source is full.
`Library.SurgePatch` reads the `.fxp` in AILANG and converts the file's
decimals to these integers. The window only writes the path to `surge.txt`.

## Build order

1. Integer loader (done). Scene A oscillators, filter, envelope, volume,
   and routes whose target we already understand: filter 1 cutoff, scene
   pitch, filter 1 resonance. Smoke-tested on Init Sine and Fast Fingers.
2. 64-bit envelope clock so a stage longer than about 1.4 seconds stays
   that long. Analog voices only. The sample player keeps its own clock.
3. A second envelope for the filter, source number 16, still integer.
4. Apply the stored pitch, resonance, and loudness routes to the voice.
5. Third oscillator, then one more filter slope. Record the type the file
   asked for even before every algorithm exists.
6. A MIDI 3 song aimed at a preset, in the synth process only.

Destinations defined now: cutoff 1, resonance 2, pitch 3, pulse width 4,
loudness 5, drive 6. Only cutoff is applied to the voice. The others are
stored on the list so the importer has somewhere to put them.

Sample voices (wave 8) do not walk the list and do not read the route
offset. `Synth_SampleBlock` is unchanged.

The synth kernel may read `routes.txt` (one `source destination depth` line
per route) from its own IPC directory. The sample player does not write
that file. An empty list adds nothing, so a synth note with no routes
sounds the same as before.
