#!/usr/bin/env python3
"""Extract the proven-working firmware images from bus2_all.txt (kernel
mmiotrace of a working cold init) and write them as firmware files our
loader can consume.

- ME/PFP/CE: raw old-radeon format = big-endian 32-bit words
  (PM4_LoadUcodeFile byte-swaps BE->LE while streaming).
- RLC: new amdgpu format = 256-byte header + little-endian words.
  PM4_LoadRLCFirmware reads ucode_size_bytes at [20] and
  ucode_array_offset_bytes at [24].
"""
import re, struct, sys, os

TRACE = "/home/bob/Ailang-Self-Hosting-/bus2_all.txt"
OUT = "/home/bob/Ailang-Self-Hosting-/fw_trace"
os.makedirs(OUT, exist_ok=True)

# Port map (sid.h): 0xC154 = CP_PFP_UCODE_DATA, 0xC16C = CP_CE_UCODE_DATA,
# 0xC160 = CP_ME_RAM_DATA. Trace upload order is PFP@433508, CE@435654,
# ME@437800 — §18's "ME first" reading was wrong and rotated these labels
# until 2026-07-02 (§24).
STREAMS = {
    "c154": ("TRACE_VERDE_pfp.bin", "be", 2144),
    "c16c": ("TRACE_VERDE_ce.bin", "be", 2144),
    "c160": ("TRACE_VERDE_me.bin", "be", 2144),
    "c330": ("TRACE_verde_rlc.bin", "rlc", 2048),
}

words = {k: [] for k in STREAMS}
pat = re.compile(r"WR REG_0x(c154|c16c|c160|c330)\s+= (0x[0-9A-Fa-f]+)")
with open(TRACE) as f:
    for line in f:
        m = pat.search(line)
        if m:
            words[m.group(1)].append(int(m.group(2), 16))

for reg, (name, fmt, expect) in STREAMS.items():
    w = words[reg]
    if len(w) != expect:
        sys.exit(f"FATAL: {reg} expected {expect} words, got {len(w)}")
    path = os.path.join(OUT, name)
    with open(path, "wb") as f:
        if fmt == "be":
            for v in w:
                f.write(struct.pack(">I", v))
        else:  # rlc new-format: 256-byte header, LE words
            hdr = bytearray(256)
            struct.pack_into("<I", hdr, 20, len(w) * 4)  # ucode_size_bytes
            struct.pack_into("<I", hdr, 24, 256)         # ucode_array_offset
            f.write(hdr)
            for v in w:
                f.write(struct.pack("<I", v))
    print(f"{path}: {len(w)} words, first=0x{w[0]:08X} last=0x{w[-1]:08X}")
