#!/usr/bin/env python3
"""Write DAW/Songs/step1 from DAW/Sessions/step1.json.

Copies the three factory .fxp files the synth tracks name. Does not copy
packs, does not call realpath, and does not modify the factory files or
step1.json.

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path("/home/bob/Ailang-Self-Hosting-")
SRC = ROOT / "DAW" / "Sessions" / "step1.json"
SONG = ROOT / "DAW" / "Songs" / "step1"
MAP = (0, 0, 1, 1)


def gain(p):
    if p <= 0:
        return 0
    if p > 1000:
        p = 1000
    if p >= 700:
        return 256 + (p - 700) * 256 // 300
    if p >= 560:
        return 128 + (p - 560) * 128 // 140
    if p >= 430:
        return 64 + (p - 430) * 64 // 130
    if p >= 300:
        return 16 + (p - 300) * 48 // 130
    if p >= 160:
        return 1 + (p - 160) * 15 // 140
    return 0


def travel_for(target):
    found = None
    for p in range(0, 1001):
        if gain(p) == target:
            found = p
            break
    if found is None:
        raise SystemExit("no travel for gain %s" % target)
    return found


def kind_view(word):
    if word == "synth":
        return 1, 1
    if word == "sample":
        return 0, 1
    raise SystemExit("unknown kind %s" % word)


def midi_of(row):
    if "song_tracks" in row:
        return " ".join(str(n) for n in row["song_tracks"])
    return str(row["song_track"])


def cord(src, dst):
    return {
        "src": src,
        "dst": dst,
        "kind": 0,
        "loop": 0,
        "delay": 0,
        "map": list(MAP),
    }


def main():
    if gain(700) != 256 or gain(699) != 255:
        raise SystemExit("gain(700) drift")
    if gain(463) != 80 or gain(462) != 79:
        raise SystemExit("gain(463) drift")
    if travel_for(256) != 700 or travel_for(80) != 463:
        raise SystemExit("inverse drift")

    doc = json.loads(SRC.read_text())
    tracks = []
    copies = []
    for row in doc["tracks"]:
        name = row["id"]
        kind, view = kind_view(row["kind"])
        preset = ""
        library = ""
        pack = row.get("pack", "")
        src_fxp = row.get("preset", "")
        if src_fxp:
            src_path = Path(src_fxp)
            if not src_path.is_file():
                raise SystemExit("missing patch %s" % src_fxp)
            preset = "patches/%s.fxp" % name
            library = src_fxp
            copies.append((src_path, SONG / "patches" / ("%s.fxp" % name)))
        tracks.append({
            "name": name,
            "kind": kind,
            "view": view,
            "inst": row["inst"],
            "preset": preset,
            "library": library,
            "pack": pack,
            "midi": midi_of(row),
            "arm": 0,
            "mute": 0,
            "solo": 0,
            "fader": travel_for(row["fader"]),
            "pan": 500,
            "fx": 0,
            "clips": [],
            "notes": [],
            "automation": [],
        })

    names = [t["name"] for t in tracks]
    conns = [cord("%s.out" % n, "%s.mst" % n) for n in names]
    conns.append(cord("master.out", "hw.out"))
    out = {
        "version": 1,
        "name": "step1",
        "song": "DAW/MIDI/Beverly Hills Cop Theme.song.json",
        "master_l": travel_for(doc["master"]),
        "master_r": travel_for(doc["master"]),
        "play": 360,
        "zoom": 100,
        "rule": 0,
        "tracks": tracks,
        "conns": conns,
    }

    for folder in (
        ROOT / "DAW" / "Instruments" / "wave",
        ROOT / "DAW" / "Instruments" / "synth",
        ROOT / "DAW" / "Instruments" / "vst",
        ROOT / "DAW" / "Effects",
        SONG / "patches",
        SONG / "audio",
        SONG / "midi",
    ):
        folder.mkdir(parents=True, exist_ok=True)
        keep = folder / ".keep"
        if folder.name != "patches":
            keep.write_bytes(b"")

    for src_path, dst_path in copies:
        shutil.copyfile(src_path, dst_path)
        if src_path.read_bytes() != dst_path.read_bytes():
            raise SystemExit("patch bytes differ %s" % dst_path)

    session = SONG / "session.json"
    session.write_text(json.dumps(out, indent=2) + "\n")
    check(out, copies)
    print("wrote %s tracks %d cords %d patches %d" % (
        session, len(tracks), len(conns), len(copies)))


def check(out, copies):
    assert out["zoom"] == 100
    assert out["master_l"] == 463 and out["master_r"] == 463
    assert len(out["conns"]) == 8
    assert out["conns"][-1]["src"] == "master.out"
    by = {t["name"]: t for t in out["tracks"]}
    assert by["syn1"]["fader"] == 700
    assert by["xylo1"]["fader"] == 463
    assert by["syn1"]["preset"] == "patches/syn1.fxp"
    assert by["syn1"]["automation"] == []
    assert by["drums"]["midi"] == "6 7 8"
    assert by["drums"]["preset"] == ""
    assert by["drums"]["pack"].endswith("MuldjordKit")
    assert len(copies) == 3
    for src_path, dst_path in copies:
        assert src_path.read_bytes() == dst_path.read_bytes()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise
