#!/usr/bin/env python3
"""Preprocess an SFZ instrument into a MIDI 3.0 sample pack (SPEC.md §7).

SFZ is importer-only. The player never reads it. Each MIDI note in a region
is rendered to its own 48 kHz s16 WAV at that note's pitch; the player then
plays every file at ratio 1.0.

  python3 sfz_to_midi3pack.py piano.sfz opcode16.json out_dir
  python3 sfz_to_midi3pack.py piano.sfz opcode16.json out_dir --inst piano_grand

Public domain (CC0 1.0), matching the MIDI 3.0 spec.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import wave

NOTE_NAMES = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]
RATE = 48000
HELD_MS = 250


def note_name(n: int) -> str:
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}"


def midi_freq(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def default_opcode16() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(here, "..", "schemas", "opcode16.json"),
        os.path.join(here, "..", "..", "..", "Librarys", "Media", "opcode16.json"),
        os.path.join(here, "..", "..", "Librarys", "Media", "opcode16.json"),
    ]
    for p in cands:
        if os.path.isfile(p):
            return os.path.abspath(p)
    return os.path.abspath(cands[0])


def parse_sfz(path: str) -> list[dict]:
    """Return regions with resolved sample paths and numeric opcodes."""
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = []
    for raw in text.splitlines():
        if "//" in raw:
            raw = raw[: raw.index("//")]
        raw = raw.strip()
        if raw:
            lines.append(raw)
    src_dir = os.path.dirname(os.path.abspath(path))
    header: dict = {}
    group: dict = {}
    regions: list[dict] = []
    cur: dict | None = None
    section = "header"

    def flush():
        nonlocal cur
        if cur is None:
            return
        r = dict(header)
        r.update(group)
        r.update(cur)
        sample = r.get("sample")
        if not sample:
            cur = None
            return
        sample = sample.replace("\\", "/")
        r["sample"] = os.path.normpath(os.path.join(src_dir, sample))
        if "key" in r:
            k = int(float(r["key"]))
            r.setdefault("lokey", k)
            r.setdefault("hikey", k)
            r.setdefault("pitch_keycenter", k)
        r["lokey"] = int(float(r.get("lokey", 0)))
        r["hikey"] = int(float(r.get("hikey", 127)))
        r["pitch_keycenter"] = int(float(r.get("pitch_keycenter", r["lokey"])))
        r["lovel"] = int(float(r.get("lovel", 0)))
        r["hivel"] = int(float(r.get("hivel", 127)))
        r["loop_mode"] = str(r.get("loop_mode", "no_loop"))
        r["loop_start"] = int(float(r["loop_start"])) if "loop_start" in r else None
        r["loop_end"] = int(float(r["loop_end"])) if "loop_end" in r else None
        regions.append(r)
        cur = None

    def apply_op(target: dict, body: str):
        for tok in body.split():
            if "=" not in tok:
                continue
            k, v = tok.split("=", 1)
            target[k.strip()] = v.strip()

    for line in lines:
        i = 0
        while i < len(line):
            if line[i] == "<":
                j = line.find(">", i)
                if j < 0:
                    break
                tag = line[i + 1 : j].strip().lower()
                if tag == "region":
                    flush()
                    cur = {}
                    section = "region"
                elif tag == "group":
                    flush()
                    group = {}
                    section = "group"
                elif tag == "global":
                    flush()
                    header = {}
                    group = {}
                    section = "header"
                i = j + 1
                continue
            nxt = line.find("<", i)
            body = line[i:] if nxt < 0 else line[i:nxt]
            if section == "region" and cur is not None:
                apply_op(cur, body)
            elif section == "group":
                apply_op(group, body)
            else:
                apply_op(header, body)
            i = len(line) if nxt < 0 else nxt
    flush()
    return regions


def vel_layer(region: dict) -> int:
    """Map an SFZ velocity range onto a MIDI 3 layer top. Highest is always v127.

    A region that starts at a high velocity is the loud layer. A region whose
    top is below 127 is the quieter layer (packs split around 80, and also
    around 82 or 90). One region that covers the whole range stays v127.
    """
    hivel = region["hivel"]
    lovel = region["lovel"]
    if lovel >= 80:
        return 127
    if hivel < 127:
        return 80
    return 127


def wav_info(path: str) -> tuple[int, int]:
    """Return (sample_rate, nframes) of the source file via ffprobe."""
    r = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=sample_rate,nb_samples",
            "-of", "csv=p=0", path,
        ],
        capture_output=True, text=True, check=True,
    )
    parts = [p for p in r.stdout.strip().split(",") if p]
    rate = int(float(parts[0])) if parts else 44100
    n = int(float(parts[1])) if len(parts) > 1 and parts[1] else 0
    return rate, n


def read_s16_stereo(path: str) -> tuple[list[int], list[int]]:
    with wave.open(path, "rb") as w:
        ch = w.getnchannels()
        if w.getsampwidth() != 2 or w.getframerate() != RATE or ch not in (1, 2):
            raise RuntimeError(
                f"{path}: expected 48 kHz s16 mono/stereo, got "
                f"{ch}ch {w.getsampwidth()*8}bit {w.getframerate()}Hz"
            )
        raw = w.readframes(w.getnframes())
    n = len(raw) // 2
    samples = list(struct.unpack("<" + "h" * n, raw))
    if ch == 1:
        return samples, list(samples)
    return samples[0::2], samples[1::2]


def write_wav(path: str, left: list[int], right: list[int] | None = None) -> None:
    if right is None or len(right) != len(left):
        right = left
    inter = []
    for a, b in zip(left, right):
        inter.append(max(-32767, min(32767, int(a))))
        inter.append(max(-32767, min(32767, int(b))))
    buf = struct.pack("<" + "h" * len(inter), *inter)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(buf)


def convert_pcm(src: str, dsemi: int, cache: dict, tmpdir: str):
    """Rate-convert to 48 kHz stereo s16. If dsemi != 0, bake that many semitones."""
    key = (src, dsemi)
    if key in cache:
        return cache[key]
    orig_rate, _ = wav_info(src)
    out = os.path.join(tmpdir, f"{abs(hash(key)):016x}.wav")
    if dsemi == 0:
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", src, "-ac", "2", "-ar", str(RATE), "-sample_fmt", "s16", out,
        ]
    else:
        ratio = 2.0 ** (dsemi / 12.0)
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", src, "-ac", "2",
            "-af", f"asetrate={orig_rate}*{ratio:.10f},aresample={RATE},aformat=sample_fmts=s16",
            out,
        ]
    subprocess.run(cmd, check=True)
    left, right = read_s16_stereo(out)
    cache[key] = (left, right, orig_rate)
    return left, right, orig_rate


def scale_loop(idx: int | None, orig_rate: int, dsemi: int, n: int) -> int | None:
    if idx is None:
        return None
    r = 2.0 ** (dsemi / 12.0)
    out = int(round(idx * RATE / (orig_rate * r)))
    return max(0, min(n, out))


def tile(pcm: list[int], n: int) -> list[int]:
    if not pcm or n <= 0:
        return []
    if len(pcm) >= n:
        return pcm[:n]
    out = list(pcm)
    while len(out) < n:
        out.extend(pcm)
    return out[:n]


def held_from_loop(loop_pcm: list[int], note: int) -> list[int]:
    """Whole-file loop of integer periods, about HELD_MS long. Tile real PCM."""
    if not loop_pcm:
        return []
    period = RATE / midi_freq(note)
    target = int(RATE * HELD_MS / 1000)
    nper = max(1, int(round(target / period)))
    n = int(round(nper * period))
    n = max(1, n)
    return tile(loop_pcm, n)


def split_parts(pcm: list[int], orig_rate: int, region: dict, dsemi: int, note: int):
    """Return (attack, held) or (None, hit)."""
    n = len(pcm)
    looping = region["loop_mode"] == "loop_continuous"
    ls = scale_loop(region["loop_start"], orig_rate, dsemi, n) if looping else None
    le = scale_loop(region["loop_end"], orig_rate, dsemi, n) if looping else None
    if not looping or ls is None or le is None or le <= ls + 16 or ls < 64:
        return None, pcm
    atk = pcm[:ls]
    loop_pcm = pcm[ls:le]
    if len(loop_pcm) < 16:
        return None, pcm
    held = held_from_loop(loop_pcm, note)
    if len(atk) < 16 or len(held) < 16:
        return None, pcm
    return atk, held


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sfz", help="input .sfz file")
    ap.add_argument("json", nargs="?", default=default_opcode16(), help="opcode16.json")
    ap.add_argument("out_dir", help="output pack directory")
    ap.add_argument("--inst", default="piano_grand",
                    help="opcode16 instrument name for the output folder")
    ap.add_argument("--decay-ms", type=int, default=700,
                    help="held-loop 60 dB time written into the pack")
    ap.add_argument("--release-ms", type=int, default=220,
                    help="damper time after note-off, written into the pack")
    args = ap.parse_args()

    with open(args.json, encoding="utf-8") as f:
        tables = json.load(f)
    names = {e["name"] for e in tables.get("registry", [])}
    if args.inst not in names:
        print(f"error: {args.inst} is not in the opcode16 registry", file=sys.stderr)
        return 1
    if not os.path.isfile(args.sfz):
        print(f"error: {args.sfz} not found", file=sys.stderr)
        return 1

    regions = parse_sfz(args.sfz)
    if not regions:
        print("error: no SFZ regions", file=sys.stderr)
        return 1

    out_dir = os.path.abspath(args.out_dir)
    idir = os.path.join(out_dir, args.inst)
    os.makedirs(idir, exist_ok=True)

    pack = {
        "format": "midi3.pack.v1",
        "name": os.path.basename(out_dir.rstrip(os.sep)),
        "a4": 440.0,
        "source": os.path.basename(args.sfz),
        "instruments": {args.inst: {
            "decay_ms": args.decay_ms,
            "release_ms": args.release_ms,
        }},
        "note": (
            "decay_ms is how long the repeating tail takes to fall 60 dB while the key "
            "or pedal is holding the note. release_ms is the damper after both are up. "
            "The player reads these from pack.json. SFZ is not read at runtime."
        ),
    }
    open(os.path.join(out_dir, "pack.json"), "w").write(json.dumps(pack, indent=2) + "\n")

    written: dict[tuple[int, int], tuple] = {}
    nfiles = 0
    cache: dict = {}

    with tempfile.TemporaryDirectory(prefix="sfz2midi3-") as tmpdir:
        for ri, region in enumerate(regions):
            src = region["sample"]
            if not os.path.isfile(src):
                print(f"warning: missing sample {src}", file=sys.stderr)
                continue
            layer = vel_layer(region)
            center = region["pitch_keycenter"]
            print(
                f"  region {ri + 1}/{len(regions)} "
                f"{os.path.basename(src)} keys {region['lokey']}-{region['hikey']} "
                f"center={center} v{layer:03d}",
                flush=True,
            )
            for note in range(region["lokey"], region["hikey"] + 1):
                if note < 0 or note > 127:
                    continue
                dsemi = note - center
                left, right, orig_rate = convert_pcm(src, dsemi, cache, tmpdir)
                atk_l, held_l = split_parts(left, orig_rate, region, dsemi, note)
                nn = note_name(note)
                if atk_l is None:
                    fn = f"{nn}.hit.v{layer:03d}.wav"
                    write_wav(os.path.join(idir, fn), left, right)
                    nfiles += 1
                    written[(note, layer)] = ("H", fn)
                else:
                    ls = len(atk_l)
                    le = ls + max(len(held_l), 0)
                    looping = region["loop_mode"] == "loop_continuous"
                    ls_src = scale_loop(region["loop_start"], orig_rate, dsemi, len(right)) if looping else ls
                    le_src = scale_loop(region["loop_end"], orig_rate, dsemi, len(right)) if looping else le
                    if ls_src is None:
                        ls_src = ls
                    if le_src is None or le_src <= ls_src:
                        le_src = min(len(right), ls_src + len(held_l))
                    atk_r = right[:ls]
                    held_r = held_from_loop(right[ls_src:le_src], note)
                    if len(held_r) != len(held_l):
                        held_r = tile(right[ls_src:le_src] or right, len(held_l))
                    if len(atk_r) != len(atk_l):
                        atk_r = tile(atk_r or right, len(atk_l))
                    fa = f"{nn}.attack.v{layer:03d}.wav"
                    fh = f"{nn}.held.v{layer:03d}.wav"
                    write_wav(os.path.join(idir, fa), atk_l, atk_r)
                    write_wav(os.path.join(idir, fh), held_l, held_r)
                    nfiles += 2
                    written[(note, layer)] = ("AL", fa, fh)

    man_path = os.path.join(out_dir, "manifest.txt")
    with open(man_path, "w") as man:
        man.write("# midi3 pack manifest (implementation index; WAV names are the spec)\n")
        man.write(f"I {args.inst}\n")
        man.write(f"T {args.decay_ms} {args.release_ms}\n")
        for note, layer in sorted(written):
            rec = written[(note, layer)]
            if rec[0] == "H":
                man.write(f"H {note} {layer} {args.inst}/{rec[1]}\n")
            else:
                man.write(f"A {note} {layer} {args.inst}/{rec[1]}\n")
                man.write(f"L {note} {layer} {args.inst}/{rec[2]}\n")

    n127 = sum(1 for (_n, ly) in written if ly == 127)
    n080 = sum(1 for (_n, ly) in written if ly == 80)
    print(f"done {nfiles} wavs, v080={n080} v127={n127} -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
