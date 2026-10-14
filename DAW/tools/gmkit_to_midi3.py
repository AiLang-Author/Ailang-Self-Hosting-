#!/usr/bin/env python3
"""Convert General MIDI drum grooves into MIDI 3 songs for one kit.

Muldjord kit_standard is not the General MIDI drum map. This importer
names the track kit_standard and moves each known drum onto that pack's
note. Notes the pack does not have are left out and reported. The
original .mid is not modified.

It also writes a Standard MIDI File whose note numbers already match the
pack, plus a songmap, because the sample player still reads those.

  python3 gmkit_to_midi3.py grooves.zip out_dir

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import zipfile
from collections import Counter

RATE = 48000

# GM drum note -> Muldjord kit_standard note. See that pack's pack.json.
GM_TO_KIT = {
    35: 48,  # acoustic bass drum -> kick L
    36: 48,  # bass drum 1 -> kick L
    38: 50,  # acoustic snare
    40: 51,  # electric snare -> snare 2
    41: 61,  # low floor tom
    42: 52,  # closed hi-hat
    43: 62,  # high floor tom
    44: 52,  # pedal hi-hat -> closed
    45: 63,  # low tom
    46: 53,  # open hi-hat
    47: 64,  # low-mid tom
    48: 64,  # hi-mid tom (this pack has four toms)
    49: 58,  # crash 1 -> crash L
    51: 54,  # ride 1 -> ride L
    52: 60,  # china
    53: 55,  # ride bell -> bell L
    57: 59,  # crash 2 -> crash R
    59: 56,  # ride 2 -> ride R
}


def read_vlq(data: bytes, i: int) -> tuple[int, int]:
    v = 0
    while True:
        b = data[i]
        i += 1
        v = (v << 7) | (b & 0x7F)
        if not (b & 0x80):
            return v, i


def write_vlq(n: int) -> bytes:
    if n < 0:
        n = 0
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def parse_notes(raw: bytes) -> tuple[int, list[tuple[int, int, int, int]]]:
    """Return division and (tick, kind, note, vel). kind 0 tempo, 1 note."""
    if raw[:4] != b"MThd":
        raise ValueError("not a MIDI file")
    hdr_len = struct.unpack(">I", raw[4:8])[0]
    _fmt, ntr, div = struct.unpack(">HHH", raw[8:14])
    if div & 0x8000:
        raise ValueError("SMPTE division")
    pos = 8 + hdr_len
    events: list[tuple[int, int, int, int]] = []
    for _ in range(ntr):
        if raw[pos:pos + 4] != b"MTrk":
            break
        ln = struct.unpack(">I", raw[pos + 4:pos + 8])[0]
        body = raw[pos + 8:pos + 8 + ln]
        pos += 8 + ln
        tick = 0
        i = 0
        running = 0
        while i < len(body):
            dt, i = read_vlq(body, i)
            tick += dt
            if i >= len(body):
                break
            status = body[i]
            if status < 0x80:
                if running == 0:
                    break
                status = running
            else:
                i += 1
                if status < 0xF0:
                    running = status
            if status == 0xFF:
                if i >= len(body):
                    break
                meta = body[i]
                i += 1
                mlen, i = read_vlq(body, i)
                payload = body[i:i + mlen]
                i += mlen
                if meta == 0x51 and len(payload) == 3:
                    tempo = (payload[0] << 16) | (payload[1] << 8) | payload[2]
                    events.append((tick, 0, tempo, 0))
                continue
            if status in (0xF0, 0xF7):
                mlen, i = read_vlq(body, i)
                i += mlen
                continue
            hi = status & 0xF0
            if hi in (0xC0, 0xD0):
                i += 1
                continue
            d1 = body[i]
            d2 = body[i + 1] if i + 1 < len(body) else 0
            i += 2
            if hi in (0x80, 0x90):
                vel = 0 if hi == 0x80 else d2
                events.append((tick, 1, d1, vel))
    events.sort(key=lambda e: (e[0], e[1]))
    return div, events


def frames_of(events: list[tuple[int, int, int, int]], div: int) -> list[tuple[int, int, int, int]]:
    tempo = 500000
    last = 0
    us = 0
    out = []
    for tick, kind, a, b in events:
        if tick < last:
            tick = last
        us += (tick - last) * tempo // div
        last = tick
        if kind == 0:
            tempo = a
            out.append((us * RATE // 1_000_000, 0, a, 0))
            continue
        out.append((us * RATE // 1_000_000, 1, a, b))
    return out


def write_smf(path: str, div: int, events: list[tuple[int, int, int, int]]) -> None:
    """events are (tick, kind, note_or_tempo, vel) already remapped."""
    body = bytearray()
    last = 0
    wrote_tempo = False
    for tick, kind, a, b in events:
        if tick < last:
            tick = last
        if kind == 0 and not wrote_tempo:
            body += write_vlq(tick - last)
            last = tick
            body += bytes([0xFF, 0x51, 0x03, (a >> 16) & 0xFF, (a >> 8) & 0xFF, a & 0xFF])
            wrote_tempo = True
            continue
        if kind != 1:
            continue
        body += write_vlq(tick - last)
        last = tick
        if b:
            body += bytes([0x90, a & 0x7F, b & 0x7F])
        else:
            body += bytes([0x80, a & 0x7F, 0])
    body += write_vlq(0)
    body += bytes([0xFF, 0x2F, 0x00])
    hdr = b"MThd" + struct.pack(">IHHH", 6, 0, 1, div)
    trk = b"MTrk" + struct.pack(">I", len(body)) + bytes(body)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(hdr + trk)


def write_songmap(path: str) -> None:
    text = (
        "# songmap v1\n"
        "# Drum groove named kit_standard. Note numbers are this pack's map,\n"
        "# not General MIDI.\n"
        "track 0  src=0:1  inst=kit_standard\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def convert_one(raw: bytes, title: str, mid_out: str, song_out: str) -> Counter:
    div, events = parse_notes(raw)
    missed: Counter = Counter()
    kept: list[tuple[int, int, int, int]] = []
    for tick, kind, a, b in events:
        if kind == 0:
            kept.append((tick, 0, a, 0))
            continue
        if b == 0:
            # Note-off uses the same translated note, matched below.
            kept.append((tick, 1, a, 0))
            continue
        dest = GM_TO_KIT.get(a)
        if dest is None:
            missed[a] += 1
            kept.append((tick, 1, a, 0))  # placeholder, dropped after pairing
            continue
        kept.append((tick, 1, dest, b))
    # Drop note-offs and placeholders whose pitch was not translated.
    # Pair by original pitch before translation: re-walk with a stack.
    div, events = parse_notes(raw)
    held: dict[int, list[int]] = {}
    smf_ev: list[tuple[int, int, int, int]] = []
    for tick, kind, a, b in events:
        if kind == 0:
            smf_ev.append((tick, 0, a, 0))
            continue
        if b:
            dest = GM_TO_KIT.get(a)
            if dest is None:
                continue
            held.setdefault(a, []).append(dest)
            smf_ev.append((tick, 1, dest, b))
        else:
            stack = held.get(a)
            if not stack:
                continue
            dest = stack.pop()
            smf_ev.append((tick, 1, dest, 0))
    write_smf(mid_out, div, smf_ev)
    write_songmap(mid_out + ".songmap")
    timed = frames_of(smf_ev, div)
    song_events = []
    nid_stack: dict[int, list[int]] = {}
    next_nid = 1
    for frame, kind, a, b in timed:
        if kind == 0:
            song_events.append({"t": frame, "track": 0, "op": "TEMPO", "us_per_quarter": a})
            continue
        if b:
            nid = next_nid
            next_nid += 1
            nid_stack.setdefault(a, []).append(nid)
            song_events.append({
                "t": frame, "track": 0, "op": "NOTE_ON",
                "note": a, "vel": (b * 65535 + 63) // 127, "nid": nid,
            })
        else:
            stack = nid_stack.get(a)
            if not stack:
                continue
            song_events.append({"t": frame, "track": 0, "op": "NOTE_OFF", "nid": stack.pop()})
    if song_events:
        song_events.append({"t": song_events[-1]["t"], "track": 0, "op": "END"})
    song = {
        "format": "midi3.song.v1",
        "name": title,
        "rate": RATE,
        "tpqn": div,
        "tracks": [{"id": 0, "name": title, "inst": "kit_standard", "group": 0, "smf_ch": 0}],
        "events": song_events,
    }
    os.makedirs(os.path.dirname(song_out), exist_ok=True)
    with open(song_out, "w", encoding="utf-8") as f:
        json.dump(song, f, indent=1)
        f.write("\n")
    return missed


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} grooves.zip out_dir")
    zip_path, out_dir = sys.argv[1], sys.argv[2]
    z = zipfile.ZipFile(zip_path)
    names = [n for n in z.namelist() if n.endswith(".mid") and "Groove Packs" in n]
    missed: Counter = Counter()
    n = 0
    for name in names:
        rel = name.split("Groove Packs)/", 1)[-1]
        title = os.path.splitext(os.path.basename(rel))[0]
        mid_out = os.path.join(out_dir, rel)
        song_out = os.path.splitext(mid_out)[0] + ".song.json"
        missed.update(convert_one(z.read(name), title, mid_out, song_out))
        n += 1
    print(f"converted {n} grooves -> {out_dir}", file=sys.stderr)
    if missed:
        print("left out (this kit has no such piece):", file=sys.stderr)
        for note, count in sorted(missed.items()):
            print(f"  gm {note} x{count}", file=sys.stderr)
    else:
        print("every drum note mapped onto the kit", file=sys.stderr)


if __name__ == "__main__":
    main()
