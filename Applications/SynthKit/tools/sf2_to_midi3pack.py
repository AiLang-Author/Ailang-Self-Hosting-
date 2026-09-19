#!/usr/bin/env python3
"""Convert a SoundFont 2 bank into a MIDI 3.0 sample pack (SPEC.md §7).

Renders every MIDI note the importer maps, at that note's pitch, to
48 kHz WAV files named as the spec requires. Stretch in the SoundFont
is baked into those files; the player then plays them at ratio 1.0.

  python3 sf2_to_midi3pack.py GeneralUser-GS.sf2 opcode16.json out_dir
  python3 sf2_to_midi3pack.py GU.sf2 opcode16.json out --only flute,piano_bright

Public domain (CC0 1.0), matching the MIDI 3.0 spec.
"""
from __future__ import annotations

import json, math, os, struct, sys, wave
from collections import defaultdict

NOTE_NAMES = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]
RATE = 48000


def note_name(n: int) -> str:
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}"


def s16(u):
    return u - 65536 if u >= 32768 else u


def find_chunk(data, fourcc):
    def walk(p, e):
        while p + 8 <= e:
            cid = data[p : p + 4]
            clen = struct.unpack_from("<I", data, p + 4)[0]
            body = p + 8
            if cid == b"LIST":
                r = walk(body + 4, min(e, body + clen))
                if r is not None:
                    return r
            if cid == fourcc:
                return p
            p = body + clen + (clen & 1)
        return None
    return walk(12, len(data))


def chunk_body(data, name):
    off = find_chunk(data, name)
    clen = struct.unpack_from("<I", data, off + 4)[0]
    return off + 8, clen


def name20(data, off):
    return data[off : off + 20].split(b"\x00", 1)[0].decode("latin1", "replace")


def load_sf2(path):
    data = open(path, "rb").read()
    phdr, phdr_len = chunk_body(data, b"phdr")
    pbag, _ = chunk_body(data, b"pbag")
    pgen, _ = chunk_body(data, b"pgen")
    inst, _ = chunk_body(data, b"inst")
    ibag, _ = chunk_body(data, b"ibag")
    igen, _ = chunk_body(data, b"igen")
    shdr, shdr_len = chunk_body(data, b"shdr")
    smpl = find_chunk(data, b"smpl") + 8
    nsh = shdr_len // 46
    samples = []
    for i in range(nsh - 1):
        rec = shdr + i * 46
        st, en, ls, le, rate = struct.unpack_from("<IIIII", data, rec + 20)
        orig = data[rec + 40]
        typ = struct.unpack_from("<H", data, rec + 44)[0]
        pcm = struct.unpack_from("<" + "h" * (en - st), data, smpl + st * 2) if en > st else ()
        samples.append(dict(
            name=name20(data, rec), st=st, n=en - st, ls=ls - st, le=le - st,
            rate=rate or 44100, orig=orig, typ=typ, pcm=pcm,
        ))
    nphdr = phdr_len // 38
    presets = []
    for pi in range(nphdr - 1):
        rec = phdr + pi * 38
        prog, bankv, bag0 = struct.unpack_from("<HHH", data, rec + 20)
        bag1 = struct.unpack_from("<H", data, rec + 38 + 24)[0]
        presets.append(dict(name=name20(data, rec), prog=prog, bank=bankv, bag0=bag0, bag1=bag1))
    return dict(data=data, pbag=pbag, pgen=pgen, inst=inst, ibag=ibag, igen=igen,
                samples=samples, presets=presets)


def zones_for_preset(sf, preset):
    """Yield dicts: klo,khi,vlo,vhi,sid,coarse,mode,orig,ls,le,n,pcm,rate."""
    data, pbag, pgen = sf["data"], sf["pbag"], sf["pgen"]
    inst, ibag, igen = sf["inst"], sf["ibag"], sf["igen"]
    bag0, bag1 = preset["bag0"], preset["bag1"]
    gklo, gkhi, gvlo, gvhi = 0, 127, 0, 127
    g_coarse = 32767
    seen_i = 0
    out = []
    for b in range(bag0, bag1):
        g0 = struct.unpack_from("<H", data, pbag + b * 4)[0]
        g1 = struct.unpack_from("<H", data, pbag + (b + 1) * 4)[0]
        inst_idx = -1
        plo, phi, pvlo, pvhi = 0, 127, 0, 127
        p_has_kr = p_has_vr = 0
        p_coarse = 32767
        for g in range(g0, g1):
            op, am = struct.unpack_from("<HH", data, pgen + g * 4)
            if op == 41:
                inst_idx = am
            if op == 43:
                plo, phi = am & 255, am >> 8
                p_has_kr = 1
            if op == 44:
                pvlo, pvhi = am & 255, am >> 8
                p_has_vr = 1
            if op == 52:
                p_coarse = s16(am)
        if p_has_kr == 0:
            plo, phi = gklo, gkhi
        if p_has_vr == 0:
            pvlo, pvhi = gvlo, gvhi
        if inst_idx < 0:
            if seen_i == 0:
                gklo, gkhi, gvlo, gvhi = plo, phi, pvlo, pvhi
                g_coarse = p_coarse
            continue
        seen_i = 1
        irec = inst + inst_idx * 22
        ib0 = struct.unpack_from("<H", data, irec + 20)[0]
        ib1 = struct.unpack_from("<H", data, irec + 22 + 20)[0]
        iklo, ikhi, ivlo, ivhi = 0, 127, 0, 127
        i_coarse = 32767
        i_mode = 32767
        seen_s = 0
        for ib in range(ib0, ib1):
            ig0 = struct.unpack_from("<H", data, ibag + ib * 4)[0]
            ig1 = struct.unpack_from("<H", data, ibag + (ib + 1) * 4)[0]
            sid = -1
            zlo, zhi, zvlo, zvhi = 0, 127, 0, 127
            z_has_kr = z_has_vr = 0
            z_coarse = 32767
            z_mode = 32767
            for ig in range(ig0, ig1):
                op, am = struct.unpack_from("<HH", data, igen + ig * 4)
                if op == 53:
                    sid = am
                if op == 43:
                    zlo, zhi = am & 255, am >> 8
                    z_has_kr = 1
                if op == 44:
                    zvlo, zvhi = am & 255, am >> 8
                    z_has_vr = 1
                if op == 52:
                    z_coarse = s16(am)
                if op == 54:
                    z_mode = am
            if z_has_kr == 0:
                zlo, zhi = iklo, ikhi
            if z_has_vr == 0:
                zvlo, zvhi = ivlo, ivhi
            if sid < 0:
                if seen_s == 0:
                    iklo, ikhi, ivlo, ivhi = zlo, zhi, zvlo, zvhi
                    i_coarse = z_coarse
                    i_mode = z_mode
                continue
            seen_s = 1
            if sid >= len(sf["samples"]):
                continue
            klo, khi = max(zlo, plo), min(zhi, phi)
            vlo, vhi = max(zvlo, pvlo), min(zvhi, pvhi)
            if vhi == 0:
                vhi = 127
            if klo > khi or vlo > vhi:
                continue
            pc = 0
            if g_coarse != 32767:
                pc = g_coarse
            if p_coarse != 32767:
                pc = pc + p_coarse
            ic = 0
            if i_coarse != 32767:
                ic = i_coarse
            if z_coarse != 32767:
                ic = z_coarse
            md = 0
            if i_mode != 32767:
                md = i_mode
            if z_mode != 32767:
                md = z_mode
            sm = sf["samples"][sid]
            if sm["typ"] in (2, 4):
                continue
            out.append(dict(
                klo=klo, khi=khi, vlo=vlo, vhi=vhi, coarse=pc + ic, mode=md,
                orig=sm["orig"], ls=sm["ls"], le=sm["le"], n=sm["n"],
                pcm=sm["pcm"], rate=sm["rate"], name=sm["name"],
            ))
    return out


def pick_zone(zones, note, vel):
    hits = [z for z in zones if z["klo"] <= note <= z["khi"] and z["vlo"] <= vel <= z["vhi"]]
    if not hits:
        return None
    hits.sort(key=lambda z: abs(z["coarse"]))
    return hits[0]


def resample(pcm, ratio):
    """Linear resample: ratio>1 plays faster (higher pitch)."""
    if not pcm:
        return []
    if abs(ratio - 1.0) < 1e-6:
        return list(pcm)
    n_out = max(1, int(len(pcm) / ratio))
    out = [0] * n_out
    last = len(pcm) - 1
    for i in range(n_out):
        x = i * ratio
        j = int(x)
        f = x - j
        a = pcm[j] if j <= last else pcm[last]
        b = pcm[j + 1] if j + 1 <= last else pcm[last]
        out[i] = int(a + (b - a) * f)
    return out


def period_frames(note, rate=RATE):
    freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
    if freq < 20:
        freq = 20
    return rate / freq


def held_frames(note, ms, rate=RATE):
    p = period_frames(note, rate)
    nper = max(1, int(round((ms / 1000.0) * (rate / p))))
    return max(8, int(round(nper * p)))


def crossfade_loop(xs, fade=8):
    if len(xs) < fade * 2:
        return xs
    out = list(xs)
    for i in range(fade):
        t = (i + 1) / fade
        a = xs[len(xs) - fade + i]
        b = xs[i]
        out[len(xs) - fade + i] = int(a * (1 - t) + b * t)
    return out


def write_wav(path, samples, rate=RATE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = len(samples)
    buf = struct.pack("<" + "h" * n, *[max(-32767, min(32767, int(s))) for s in samples])
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(buf)


def render_note(zone, note, held_ms):
    """Bake SF2 pitch into a 48 kHz stream, then split attack/held."""
    pcm = zone["pcm"]
    if not pcm:
        return None, None
    dsemi = (note - zone["orig"]) + zone["coarse"]
    ratio = (2.0 ** (dsemi / 12.0)) * (zone["rate"] / RATE)
    if ratio <= 0:
        ratio = 1.0
    pitched = resample(pcm, ratio)
    if len(pitched) < 32:
        return None, None
    ls = int(zone["ls"] / ratio) if ratio else 0
    le = int(zone["le"] / ratio) if ratio else 0
    looping = zone["mode"] in (1, 3) and le > ls + 8
    atk_n = ls if looping and 16 < ls < len(pitched) else min(int(RATE * 0.04), len(pitched) // 3)
    if atk_n < 16:
        atk_n = min(16, len(pitched) // 4)
    attack = pitched[:atk_n]
    hn = held_frames(note, held_ms)
    if looping and le <= len(pitched):
        loop = pitched[ls:le]
        if len(loop) < 8:
            loop = pitched[atk_n : atk_n + hn] or pitched[-hn:]
        if len(loop) < hn:
            reps = (hn // max(1, len(loop))) + 1
            loop = (loop * reps)[:hn]
        else:
            loop = loop[:hn]
        held = crossfade_loop(loop)
    else:
        rest = pitched[atk_n:]
        if len(rest) < hn:
            rest = rest + [0] * (hn - len(rest))
        held = crossfade_loop(rest[:hn])
    if attack:
        held[0] = attack[-1]
    return attack, held


def vel_layers(zones, note):
    """Unique vhi values covering this note; always end with 127."""
    vis = sorted({z["vhi"] for z in zones if z["klo"] <= note <= z["khi"]})
    if not vis:
        return [127]
    if vis[-1] != 127:
        vis.append(127)
    return vis


def main():
    if len(sys.argv) < 4:
        print("usage: sf2_to_midi3pack.py bank.sf2 opcode16.json out_dir [--only a,b]", file=sys.stderr)
        sys.exit(2)
    sf2_path, json_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    meta = json.load(open(json_path, encoding="utf-8"))
    gm = {int(e["prog"]): e["name"] for e in meta.get("gm", [])}
    kit = {int(e["prog"]): e["name"] for e in meta.get("kit", [])}
    names = {e["name"] for e in meta.get("registry", [])}
    print("loading", sf2_path, flush=True)
    sf = load_sf2(sf2_path)
    inst_zones = defaultdict(list)
    inst_kind = {}
    for pr in sf["presets"]:
        if pr["bank"] == 128:
            name = kit.get(pr["prog"])
            kind = "hit"
        elif pr["bank"] == 0:
            name = gm.get(pr["prog"])
            kind = "held"
        else:
            continue
        if not name or name not in names:
            continue
        if only and name not in only:
            continue
        zs = zones_for_preset(sf, pr)
        if not zs:
            continue
        inst_zones[name].extend(zs)
        inst_kind[name] = kind
        print(f"  {pr['bank']}:{pr['prog']:3d} {pr['name']!r} -> {name}  zones={len(zs)}", flush=True)

    os.makedirs(out_dir, exist_ok=True)
    pack = {
        "format": "midi3.pack.v1",
        "name": os.path.splitext(os.path.basename(sf2_path))[0],
        "a4": 440.0,
        "source": os.path.basename(sf2_path),
        "note": "Converted from SF2. Stretch in the source is baked into each note file.",
    }
    open(os.path.join(out_dir, "pack.json"), "w").write(json.dumps(pack, indent=2) + "\n")
    man = open(os.path.join(out_dir, "manifest.txt"), "w")
    man.write("# midi3 pack manifest (implementation index; WAV names are the spec)\n")

    nfiles = 0
    for name, zones in sorted(inst_zones.items()):
        kind = inst_kind[name]
        idir = os.path.join(out_dir, name)
        os.makedirs(idir, exist_ok=True)
        man.write(f"I {name}\n")
        held_ms = 250 if name.startswith("piano") else 100
        notes = range(0, 128) if kind == "hit" else range(21, 109)
        at_pitch = name.startswith("piano") or name.startswith("bass")
        for note in notes:
            layers = vel_layers(zones, note) if kind != "hit" else [127]
            for vhi in layers:
                z = pick_zone(zones, note, vhi)
                if z is None:
                    continue
                dsemi = (note - z["orig"]) + z["coarse"]
                if at_pitch and abs(dsemi) > 0:
                    continue
                nn = note_name(note)
                if kind == "hit":
                    atk, held = render_note(z, note, 80)
                    clip = (atk or []) + (held or [])
                    if len(clip) < 16:
                        continue
                    fn = f"{nn}.hit.v{vhi:03d}.wav"
                    write_wav(os.path.join(idir, fn), clip[: int(RATE * 0.4)])
                    man.write(f"H {note} {vhi} {fn}\n")
                    nfiles += 1
                else:
                    atk, held = render_note(z, note, held_ms)
                    if not atk or not held:
                        continue
                    fa = f"{nn}.attack.v{vhi:03d}.wav"
                    fh = f"{nn}.held.v{vhi:03d}.wav"
                    write_wav(os.path.join(idir, fa), atk)
                    write_wav(os.path.join(idir, fh), held)
                    man.write(f"A {note} {vhi} {fa}\n")
                    man.write(f"L {note} {vhi} {fh}\n")
                    nfiles += 2
        print(f"wrote {name}", flush=True)
    man.close()
    print(f"done {nfiles} wavs -> {out_dir}")


if __name__ == "__main__":
    main()
