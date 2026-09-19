#!/usr/bin/env python3
"""Create a .songmap file from a Standard MIDI File (MIDI 3.0 importer helper).

Reads a Standard MIDI File (Type 0 or 1) and splits it into parts, following
SPEC.md section 9: first by file track, then by channel, then at any Program
Change that happens after the part has already played notes. Each part gets a
TrackID, numbered 0, 1, 2, ... in file order.

For each part, the instrument name is looked up from its Program Change in the
gm table of schemas/opcode16.json. Parts that cannot be mapped are written as
commented-out lines marked NEED_NAME, for a person to fill in.

The tool never decides that a part is a drum kit. Parts on MIDI channel 10 are
marked AMBIGUOUS and left for a person to name; the kit table is shown only as
a hint in a comment.

A Program Change while notes are still sounding is an import error (SPEC.md
section 6.2). It is reported, and the tool exits with status 1.

  python3 tools/midi3_songmap.py song.mid
  python3 tools/midi3_songmap.py song.mid -o song.mid.songmap

Public domain (CC0 1.0).
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

DRUM_CHANNEL = 9  # MIDI channel 10, counted from 0. Used only to add warnings.


class SMFError(Exception):
    pass


def read_vlq(data: bytes, i: int) -> tuple[int, int]:
    """Read a MIDI variable-length quantity. Returns (value, next index)."""
    value = 0
    for _ in range(4):
        if i >= len(data):
            raise SMFError("truncated variable-length value")
        byte = data[i]
        i += 1
        value = (value << 7) | (byte & 0x7F)
        if byte < 0x80:
            return value, i
    raise SMFError("variable-length value longer than 4 bytes")


class Part:
    """One (file track, channel, program) run. Becomes one MIDI 3.0 track."""

    def __init__(self, ftrack: int, channel: int, start_tick: int,
                 program: int | None, bank: int):
        self.ftrack = ftrack
        self.channel = channel
        self.start_tick = start_tick
        self.program = program
        self.bank = bank
        self.note_count = 0
        self.lo = 127
        self.hi = 0

    def add_note(self, note: int) -> None:
        self.note_count += 1
        self.lo = min(self.lo, note)
        self.hi = max(self.hi, note)


def parse_smf(path: str):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"MThd" or len(data) < 14:
        raise SMFError("not a Standard MIDI File (missing MThd header)")
    hlen = struct.unpack_from(">I", data, 4)[0]
    fmt, ntracks, division = struct.unpack_from(">HHH", data, 8)
    if fmt not in (0, 1):
        raise SMFError(f"SMF format {fmt} is not supported (only 0 and 1)")

    pos = 8 + hlen
    chunks = []
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        clen = struct.unpack_from(">I", data, pos + 4)[0]
        if cid == b"MTrk":
            chunks.append(data[pos + 8:pos + 8 + clen])
        pos += 8 + clen  # skip unknown chunk types, as the SMF spec requires

    parts: list[Part] = []
    track_names: list[str] = []
    errors: list[str] = []

    for ft, tr in enumerate(chunks):
        tick = 0
        i = 0
        running = None  # running status; cleared by meta and SysEx events
        name = ""
        current: dict[int, Part] = {}               # channel -> open part
        pending_prog: dict[int, int | None] = {}    # channel -> program not yet used
        bank: dict[int, int] = {}                   # channel -> last CC0
        sounding: dict[int, dict[int, int]] = {}    # channel -> {note: count}

        try:
            while i < len(tr):
                delta, i = read_vlq(tr, i)
                tick += delta
                if i >= len(tr):
                    raise SMFError("event missing after delta time")
                status = tr[i]

                if status == 0xFF:  # meta event
                    i += 1
                    running = None
                    mtype = tr[i]
                    i += 1
                    length, i = read_vlq(tr, i)
                    payload = tr[i:i + length]
                    i += length
                    if mtype == 0x03 and not name:
                        name = payload.decode("latin1", "replace").split("\x00")[0].strip()
                    if mtype == 0x2F:
                        break
                    continue

                if status in (0xF0, 0xF7):  # SysEx
                    i += 1
                    running = None
                    length, i = read_vlq(tr, i)
                    i += length
                    continue

                if status >= 0x80:
                    running = status
                    i += 1
                elif running is None:
                    raise SMFError(f"data byte with no running status at tick {tick}")
                status = running

                kind, ch = status & 0xF0, status & 0x0F
                nbytes = 1 if kind in (0xC0, 0xD0) else 2
                if i + nbytes > len(tr):
                    raise SMFError("truncated channel message")
                d1 = tr[i]
                d2 = tr[i + 1] if nbytes == 2 else 0
                i += nbytes

                notes_on = sounding.setdefault(ch, {})

                if kind == 0x90 and d2 > 0:  # note on
                    part = current.get(ch)
                    if part is None or ch in pending_prog:
                        prog = pending_prog.pop(ch, part.program if part else None)
                        part = Part(ft, ch, tick, prog, bank.get(ch, 0))
                        parts.append(part)
                        current[ch] = part
                    part.add_note(d1)
                    notes_on[d1] = notes_on.get(d1, 0) + 1

                elif kind == 0x80 or (kind == 0x90 and d2 == 0):  # note off
                    if notes_on.get(d1):
                        notes_on[d1] -= 1
                        if notes_on[d1] == 0:
                            del notes_on[d1]

                elif kind == 0xC0:  # program change
                    part = current.get(ch)
                    if notes_on:
                        errors.append(
                            f"file track {ft}, channel {ch + 1}, tick {tick}: "
                            f"Program Change to {d1} while notes are sounding")
                    if part is not None and part.program == d1 and ch not in pending_prog:
                        continue  # same program again; nothing changes
                    pending_prog[ch] = d1

                elif kind == 0xB0 and d1 == 0:  # bank select MSB
                    bank[ch] = d2

        except (SMFError, IndexError) as e:
            msg = str(e) if isinstance(e, SMFError) else "truncated data"
            raise SMFError(f"file track {ft}: {msg}") from None

        track_names.append(name)

    return fmt, len(chunks), division, parts, track_names, errors


def load_tables(path: str):
    with open(path, encoding="utf-8") as f:
        j = json.load(f)
    registry = {e["name"] for e in j.get("registry", [])}
    gm = {int(e["prog"]): e["name"] for e in j.get("gm", [])}
    kit = {int(e["prog"]): e["name"] for e in j.get("kit", [])}
    for table, rows in (("gm", gm), ("kit", kit)):
        for prog, name in rows.items():
            if name not in registry:
                print(f"warning: {table} program {prog} maps to '{name}', "
                      f"which is not in the registry", file=sys.stderr)
    return gm, kit


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mid", help="input .mid file")
    ap.add_argument("-o", "--output", help="write the songmap to this file")
    ap.add_argument("--json", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "schemas", "opcode16.json"),
        help="path to opcode16.json")
    args = ap.parse_args()

    try:
        fmt, ntracks, division, parts, names, errors = parse_smf(args.mid)
    except (SMFError, OSError) as e:
        print(f"error: {args.mid}: {e}", file=sys.stderr)
        return 1
    gm, kit = load_tables(args.json)

    lines = [
        "# songmap v1",
        f"# source: {os.path.basename(args.mid)} "
        f"(SMF type {fmt}, {ntracks} tracks, division {division})",
        "# src=FILETRACK:CHANNEL[@TICK]  (file track from 0, MIDI channel 1-16,",
        "#   @TICK only when a Program Change split the part)",
        "",
    ]

    for tid, p in enumerate(parts):
        src = f"{p.ftrack}:{p.channel + 1}"
        if p.start_tick and any(q is not p and q.ftrack == p.ftrack
                                and q.channel == p.channel for q in parts):
            src += f"@{p.start_tick}"
        label = names[p.ftrack] or "(unnamed)"
        prog = "none" if p.program is None else str(p.program)
        notes = "note" if p.note_count == 1 else "notes"
        lines.append(f"# {label}: {p.note_count} {notes}, range {p.lo}-{p.hi}, "
                     f"program {prog}, bank {p.bank}")

        inst = None
        if p.channel == DRUM_CHANNEL:
            hint = kit.get(p.program) if p.program is not None else None
            lines.append("# AMBIGUOUS: MIDI channel 10. Not assumed to be drums."
                         + (f" If this is a kit, the kit table suggests {hint}." if hint else ""))
        elif p.program is None:
            lines.append("# No Program Change; no instrument can be chosen.")
        elif p.program in gm:
            inst = gm[p.program]
        else:
            lines.append(f"# Program {p.program} has no entry in the gm table.")

        if inst:
            lines.append(f"track {tid}  src={src}  inst={inst}")
        else:
            lines.append(f"# track {tid}  src={src}  inst=NEED_NAME")
        lines.append("")

    for e in errors:
        lines.append(f"# ERROR: {e}")

    text = "\n".join(lines).rstrip() + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(text, end="")

    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
