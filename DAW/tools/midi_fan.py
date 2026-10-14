#!/usr/bin/env python3
"""Turn a MIDI 3 song into per-instance bytes for the DAW mixer.

The session lists which song tracks get a process. Each output line is:
frame mixer_track nbytes status data1 data2
The mixer writes those bytes into that instance's midi.bin. The SynthKit
kernel already understands these bytes. This tool does not parse Surge
presets and does not read a raw MIDI file.

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
"""
from __future__ import annotations

import json
import sys


def vel7(v: int) -> int:
    n = (v * 127 + 32767) // 65535
    if n < 1:
        n = 1
    if n > 127:
        n = 127
    return n


def cc7(v: int) -> int:
    n = (v * 127 + 32767) // 65535
    if n < 0:
        n = 0
    if n > 127:
        n = 127
    return n


def bend14(cents: int) -> tuple[int, int]:
    # MIDI 3 cents use the import default of +/- 2 semitones.
    span = 200
    b = 8192 + int(round(cents / span * 8192))
    if b < 0:
        b = 0
    if b > 16383:
        b = 16383
    return b & 0x7F, (b >> 7) & 0x7F


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} session.json events.txt")
    session = json.load(open(sys.argv[1]))
    song = json.load(open(session["song"]))
    if song.get("format") != "midi3.song.v1":
        raise SystemExit(f"not a MIDI 3 song: {session['song']}")
    index = {}
    for i, t in enumerate(session["tracks"]):
        ids = t.get("song_tracks")
        if ids is None:
            ids = [t["song_track"]]
        for sid in ids:
            index[int(sid)] = i
    notes: dict[tuple[int, int], int] = {}
    n = 0
    with open(sys.argv[2], "w") as out:
        for ev in song["events"]:
            tid = int(ev["track"])
            if tid not in index:
                continue
            mi = index[tid]
            op = ev["op"]
            frame = int(ev["t"])
            if op == "NOTE_ON":
                note = int(ev["note"]) & 0x7F
                notes[(tid, int(ev["nid"]))] = note
                out.write(f"{frame} {mi} 3 90 {note:02x} {vel7(int(ev['vel'])):02x}\n")
                n += 1
            elif op == "NOTE_OFF":
                note = notes.get((tid, int(ev["nid"])))
                if note is None:
                    continue
                out.write(f"{frame} {mi} 3 80 {note:02x} 00\n")
                n += 1
            elif op == "CC":
                out.write(
                    f"{frame} {mi} 3 b0 {int(ev['cc']) & 0x7F:02x} {cc7(int(ev['value'])):02x}\n"
                )
                n += 1
            elif op == "BEND":
                lo, hi = bend14(int(ev["cents"]))
                out.write(f"{frame} {mi} 3 e0 {lo:02x} {hi:02x}\n")
                n += 1
    print(f"fan: {n} events -> {sys.argv[2]}", file=sys.stderr)
    covered = set(index)
    for t in song["tracks"]:
        if int(t["id"]) in covered:
            continue
        inst = t.get("inst", "")
        why = "no sample pack" if inst in ("marimba", "celesta") else "not in this session"
        print(f"skipped {t.get('name', t['id'])} inst={inst}: {why}", file=sys.stderr)


if __name__ == "__main__":
    main()
