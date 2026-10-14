#!/usr/bin/env python3
"""Turn a Standard MIDI File plus a songmap into a MIDI 3 song.

The song names each track with an opcode16 instrument. Players read that
name. They do not read General MIDI program numbers, and they do not
substitute piano when a name is missing.

A songmap line chooses the instrument. Channel 10 is not treated as drums
unless the songmap names a kit. Parts left as NEED_NAME are reported and
left out of the song.

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
"""
from __future__ import annotations

import json
import re
import struct
import sys

RATE = 48000


def read_vlq(data: bytes, i: int) -> tuple[int, int]:
    v = 0
    while True:
        b = data[i]
        i += 1
        v = (v << 7) | (b & 0x7F)
        if not (b & 0x80):
            return v, i


def load_map(path: str) -> list[dict]:
    tracks = []
    for line in open(path, encoding="utf-8"):
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        m = re.match(
            r"track\s+(\d+)\s+src=(\d+):(\d+)(?:@(\d+))?\s+inst=(\S+)",
            raw,
        )
        if not m:
            continue
        inst = m.group(5)
        if inst == "NEED_NAME":
            continue
        tracks.append({
            "id": int(m.group(1)),
            "ftrack": int(m.group(2)),
            "ch": int(m.group(3)) - 1,
            "tick": int(m.group(4) or 0),
            "inst": inst,
        })
    tracks.sort(key=lambda t: (t["ftrack"], t["ch"], t["tick"], t["id"]))
    return tracks


def track_at(parts: list[dict], ftrack: int, ch: int, tick: int) -> dict | None:
    hit = None
    for p in parts:
        if p["ftrack"] == ftrack and p["ch"] == ch and p["tick"] <= tick:
            hit = p
    return hit


def vel16(v: int) -> int:
    return (v * 65535 + 63) // 127


def cc16(v: int) -> int:
    return (v * 65535 + 63) // 127


def convert(mid_path: str, map_path: str, out_path: str) -> None:
    parts = load_map(map_path)
    if not parts:
        raise SystemExit(f"no named tracks in {map_path}")
    raw = open(mid_path, "rb").read()
    if raw[:4] != b"MThd":
        raise SystemExit(f"not a MIDI file: {mid_path}")
    hdr_len = struct.unpack(">I", raw[4:8])[0]
    _fmt, ntr, div = struct.unpack(">HHH", raw[8:14])
    if div & 0x8000:
        raise SystemExit("SMPTE division is not used")
    pos = 8 + hdr_len
    bodies = []
    for _ in range(ntr):
        if raw[pos:pos + 4] != b"MTrk":
            raise SystemExit("missing track")
        ln = struct.unpack(">I", raw[pos + 4:pos + 8])[0]
        bodies.append(raw[pos + 8:pos + 8 + ln])
        pos += 8 + ln

    names = [""] * ntr
    # First pass: track names, and a flat event list with ticks.
    # (tick, ftrack, kind, a, b, c) kind 0 tempo, 1 note, 2 cc, 3 bend
    pending: list[tuple] = []
    for ft, body in enumerate(bodies):
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
                if meta == 0x03:
                    names[ft] = payload.decode("latin1", "replace").strip()
                elif meta == 0x51 and len(payload) == 3:
                    tempo = (payload[0] << 16) | (payload[1] << 8) | payload[2]
                    pending.append((tick, ft, 0, tempo, 0, 0))
                continue
            if status in (0xF0, 0xF7):
                mlen, i = read_vlq(body, i)
                i += mlen
                continue
            hi = status & 0xF0
            ch = status & 0x0F
            if hi in (0xC0, 0xD0):
                i += 1
                continue
            d1 = body[i]
            d2 = body[i + 1] if i + 1 < len(body) else 0
            i += 2
            if hi == 0x90 and d2:
                pending.append((tick, ft, 1, ch, d1, d2))
            elif hi in (0x80, 0x90):
                pending.append((tick, ft, 1, ch, d1, 0))
            elif hi == 0xB0 and d1 not in (0, 32, 6, 38, 98, 99, 100, 101):
                pending.append((tick, ft, 2, ch, d1, d2))
            elif hi == 0xE0:
                pending.append((tick, ft, 3, ch, d1, d2))

    pending.sort(key=lambda e: (e[0], e[1], e[2]))
    tempo = 500000
    last_tick = 0
    us = 0
    events = []
    # open notes: (ftrack, ch, note) -> list of (song_track, nid)
    held: dict[tuple[int, int, int], list[tuple[int, int]]] = {}
    next_nid = 1
    used = set()
    for tick, ft, kind, a, b, c in pending:
        if tick < last_tick:
            tick = last_tick
        us += (tick - last_tick) * tempo // div
        last_tick = tick
        frame = us * RATE // 1_000_000
        if kind == 0:
            tempo = a
            events.append({"t": frame, "track": 0, "op": "TEMPO", "us_per_quarter": a, "tick": tick})
            continue
        part = track_at(parts, ft, a, tick)
        if part is None:
            continue
        tid = part["id"]
        used.add(tid)
        if kind == 1:
            note = b & 0x7F
            if c:
                nid = next_nid
                next_nid += 1
                held.setdefault((ft, a, note), []).append((tid, nid))
                events.append({
                    "t": frame, "track": tid, "op": "NOTE_ON",
                    "note": note, "vel": vel16(c), "nid": nid, "tick": tick,
                })
            else:
                stack = held.get((ft, a, note))
                if not stack:
                    continue
                on_tid, nid = stack.pop()
                events.append({"t": frame, "track": on_tid, "op": "NOTE_OFF", "nid": nid, "tick": tick})
        elif kind == 2:
            events.append({
                "t": frame, "track": tid, "op": "CC",
                "cc": b, "value": cc16(c), "tick": tick,
            })
        else:
            bend = b | (c << 7)
            cents = int(round((bend - 8192) / 8192 * 2 * 100))
            events.append({"t": frame, "track": tid, "op": "BEND", "cents": cents, "tick": tick})

    song_tracks = []
    for p in sorted(parts, key=lambda t: t["id"]):
        if p["id"] not in used and p["inst"]:
            pass
        name = names[p["ftrack"]] if p["ftrack"] < len(names) else ""
        song_tracks.append({
            "id": p["id"],
            "name": name,
            "inst": p["inst"],
            "group": 0,
            "smf_ch": p["ch"],
        })
    if events:
        end_t = events[-1]["t"]
        events.append({"t": end_t, "track": song_tracks[0]["id"], "op": "END"})
    song = {
        "format": "midi3.song.v1",
        "name": mid_path.rsplit("/", 1)[-1].rsplit(".", 1)[0],
        "rate": RATE,
        "tpqn": div,
        "tracks": song_tracks,
        "events": events,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(song, f, indent=1)
        f.write("\n")
    named = ", ".join(f"{t['id']}:{t['inst']}" for t in song_tracks)
    print(f"song: {len(events)} events tracks {named} -> {out_path}", file=sys.stderr)
    missing = []
    for line in open(map_path, encoding="utf-8"):
        if "NEED_NAME" in line or "AMBIGUOUS" in line or "no entry" in line:
            missing.append(line.strip())
    for line in missing:
        print(f"left out: {line}", file=sys.stderr)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(f"usage: {sys.argv[0]} song.mid song.songmap out.song.json")
    convert(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
