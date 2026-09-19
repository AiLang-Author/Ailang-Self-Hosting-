#!/usr/bin/env python3
"""Resample every SF2 sample to 48 kHz with ffmpeg. Playback then does pitch only."""
import struct, subprocess, sys, os

def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def p16(v): return struct.pack("<H", v & 0xFFFF)
def p32(v): return struct.pack("<I", v & 0xFFFFFFFF)

def find_chunk(buf, tag):
    pos = 12
    n = len(buf)
    while pos + 8 <= n:
        ident = buf[pos : pos + 4]
        clen = u32(buf, pos + 4)
        if ident == tag:
            return pos, clen
        if ident == b"LIST":
            sub = pos + 12
            end = pos + 8 + clen
            while sub + 8 <= end:
                t2 = buf[sub : sub + 4]
                sl = u32(buf, sub + 4)
                if t2 == tag:
                    return sub, sl
                sub += 8 + sl + (sl & 1)
        pos += 8 + clen + (clen & 1)
    return -1, 0

def ffmpeg_resample(pcm: bytes, rate: int, out_rate: int = 48000) -> bytes:
    if rate <= 0:
        rate = out_rate
    if rate == out_rate:
        return pcm
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error",
        "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", "pipe:0",
        "-f", "s16le", "-ar", str(out_rate), "-ac", "1", "pipe:1",
    ]
    p = subprocess.run(cmd, input=pcm, capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[:400])
    return p.stdout

def scale(n, old, new):
    if old <= 0:
        return n
    return int(round(n * new / old))

def convert(src, dst, out_rate=48000):
    buf = open(src, "rb").read()
    if buf[:4] != b"RIFF" or buf[8:12] != b"sfbk":
        raise SystemExit("not an sf2")
    smpl_at, smpl_len = find_chunk(buf, b"smpl")
    shdr_at, shdr_len = find_chunk(buf, b"shdr")
    if smpl_at < 0 or shdr_at < 0:
        raise SystemExit("missing smpl/shdr")
    smpl = buf[smpl_at + 8 : smpl_at + 8 + smpl_len]
    shdr = bytearray(buf[shdr_at + 8 : shdr_at + 8 + shdr_len])
    nsh = shdr_len // 46
    new_smpl = bytearray()
    print(f"resampling {nsh - 1} samples from {src} -> {out_rate} Hz")
    for si in range(nsh):
        rec = shdr[si * 46 : (si + 1) * 46]
        name = rec[:20].split(b"\x00")[0]
        if si == nsh - 1 or name in (b"EOS", b"EOP"):
            rec[20:40] = p32(len(new_smpl) // 2) + p32(len(new_smpl) // 2) + p32(0) + p32(0) + p32(out_rate)
            shdr[si * 46 : (si + 1) * 46] = rec
            continue
        st, en = u32(rec, 20), u32(rec, 24)
        ls, le = u32(rec, 28), u32(rec, 32)
        rate = u32(rec, 36)
        if en <= st or st * 2 >= len(smpl):
            rec[20:40] = p32(len(new_smpl) // 2) + p32(len(new_smpl) // 2) + p32(0) + p32(0) + p32(out_rate)
            shdr[si * 46 : (si + 1) * 46] = rec
            continue
        pcm = smpl[st * 2 : min(en * 2, len(smpl))]
        out = ffmpeg_resample(pcm, rate, out_rate)
        # 8-frame pad
        pad = b"\x00\x00" * 8
        start = len(new_smpl) // 2 + 8
        new_smpl.extend(pad)
        new_smpl.extend(out)
        new_smpl.extend(pad)
        nn = len(out) // 2
        end = start + nn
        nls = start + scale(max(0, ls - st), rate, out_rate)
        nle = start + scale(max(0, le - st), rate, out_rate)
        if nle <= nls:
            nle = end
        if nle > end:
            nle = end
        rec[20:40] = p32(start) + p32(end) + p32(nls) + p32(nle) + p32(out_rate)
        shdr[si * 46 : (si + 1) * 46] = rec
        if si % 50 == 0:
            print(f"  {si}/{nsh - 1} {name.decode('latin1', 'replace')} {rate} -> {out_rate} ({nn} frames)")
    # rebuild RIFF: keep everything except smpl payload and shdr payload
    def chunk_bytes(tag, data):
        if len(data) & 1:
            data = data + b"\x00"
        return tag + p32(len(data) if not (len(data) & 1 and tag) else len(data)) 
    # simpler: splice smpl and shdr in place with size fixups via full rebuild of LIST sdta/pdta
    # copy INFO list
    info_at, info_len = find_chunk(buf, b"INFO")
    # INFO find returns the INFO fourcc inside LIST. We need the LIST header.
    # Walk top-level for LIST chunks.
    pos = 12
    info_list = b""
    pdta_body = b""
    while pos + 8 <= len(buf):
        ident = buf[pos : pos + 4]
        clen = u32(buf, pos + 4)
        chunk = buf[pos : pos + 8 + clen + (clen & 1)]
        if ident == b"LIST":
            kind = buf[pos + 8 : pos + 12]
            if kind == b"INFO":
                info_list = chunk
            elif kind == b"pdta":
                pdta_body = bytearray(buf[pos + 12 : pos + 8 + clen])
        pos += 8 + clen + (clen & 1)
    new_pdta = bytearray()
    p = 0
    while p + 8 <= len(pdta_body):
        tag = bytes(pdta_body[p : p + 4])
        ln = u32(pdta_body, p + 4)
        payload = bytes(pdta_body[p + 8 : p + 8 + ln])
        if tag == b"shdr":
            payload = bytes(shdr)
        new_pdta.extend(tag)
        new_pdta.extend(p32(len(payload)))
        new_pdta.extend(payload)
        if len(payload) & 1:
            new_pdta.append(0)
        p += 8 + ln + (ln & 1)
    smpl_data = bytes(new_smpl)
    if len(smpl_data) & 1:
        smpl_data += b"\x00"
    sdta = b"LIST" + p32(4 + 8 + len(smpl_data)) + b"sdta" + b"smpl" + p32(len(smpl_data)) + smpl_data
    pdta = b"LIST" + p32(4 + len(new_pdta)) + b"pdta" + bytes(new_pdta)
    body = b"sfbk" + info_list + sdta + pdta
    out = b"RIFF" + p32(len(body)) + body
    open(dst, "wb").write(out)
    print(f"wrote {dst} ({len(out)} bytes)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: sf2_resample48.py in.sf2 out.sf2")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
