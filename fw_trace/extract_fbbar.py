#!/usr/bin/env python3
# extract_fbbar.py — §36: pull the kernel's VRAM-side (FB-BAR) writes for bus 2
# out of the amdgpu mmiotrace raw log (the channel bus2_all.txt's parser dropped).
#
# Bus 2: FB BAR 0xb0000000 (256MB), reg BAR 0xfe900000.
# Bus 1 (DO NOT MIX): FB 0xc0000000, reg 0xfea00000.
#
# Pass 1 (default): map inventory, bus-2 FB write-region clustering (gap>16K),
#   and reg-BAR writes to RLC_SAVE_AND_RESTORE_BASE (0xC310) /
#   RLC_CLEAR_STATE_RESTORE_BASE (0xC30C) to locate SR/CSB in amdgpu's layout.
# Pass 2 (--dump LO HI out.bin): reconstruct VRAM content [LO,HI) from writes
#   (last-write-wins, byte-granular via width) and save as .bin.
import sys, struct
from collections import defaultdict

LOG = 'mmiotrace_raw.log'
FB2_LO, FB2_HI = 0xb0000000, 0xc0000000
REG2 = 0xfe900000

dump = None
if len(sys.argv) >= 4 and sys.argv[1] == '--dump':
    dump = (int(sys.argv[2], 0), int(sys.argv[3], 0), sys.argv[4])

maps = {}
fb_writes = []          # (phys, width, value, ts)
reg_hits = []           # (ts, off, value) for RLC base regs
n_w = 0
for line in open(LOG, errors='replace'):
    t = line.split()
    if not t: continue
    if t[0] == 'MAP':
        # MAP ts id phys virt len ...
        maps[int(t[2])] = (int(t[3], 16), int(t[5], 16))
        continue
    if t[0] not in ('W', 'R'): continue
    # W width ts map_id phys value ...
    width = int(t[1]); ts = float(t[2]); phys = int(t[4], 16); val = int(t[5], 16)
    if t[0] == 'W':
        n_w += 1
        if FB2_LO <= phys < FB2_HI:
            fb_writes.append((phys, width, val, ts))
        elif phys - REG2 in (0xC310, 0xC30C):
            reg_hits.append((ts, phys - REG2, val))

print(f"total W records: {n_w}; bus-2 FB-BAR writes: {len(fb_writes)}")
print("\nmaps (phys, len):")
for mid in sorted(maps):
    p, l = maps[mid]
    tag = ''
    if FB2_LO <= p < FB2_HI: tag = ' <== bus2 FB region'
    if p == REG2: tag = ' <== bus2 reg BAR'
    print(f"  id {mid}: 0x{p:x} +0x{l:x}{tag}")

print("\nRLC base-reg writes (reg BAR):")
for ts, off, val in reg_hits:
    name = 'SAVE_AND_RESTORE' if off == 0xC310 else 'CLEAR_STATE_RESTORE'
    print(f"  t={ts:.6f} {name}(0x{off:X}) = 0x{val:08X}  -> VRAM off 0x{(val << 8) - 0xF400000000:X}")

if dump:
    lo, hi, out = dump
    buf = bytearray(hi - lo)
    seen = bytearray(hi - lo)
    for phys, width, val, ts in fb_writes:
        o = phys - FB2_LO
        if o >= hi or o + width <= lo: continue
        b = val.to_bytes(width, 'little')
        for i in range(width):
            if lo <= o + i < hi:
                buf[o + i - lo] = b[i]
                seen[o + i - lo] = 1
    open(out, 'wb').write(buf)
    print(f"\ndumped [0x{lo:x},0x{hi:x}) -> {out}; bytes written by kernel: "
          f"{sum(seen)}/{hi-lo}")
else:
    # cluster FB writes into regions (gap > 16K starts a new region)
    offs = sorted(set(p - FB2_LO for p, w, v, ts in fb_writes))
    print(f"\nbus-2 FB regions (distinct addrs: {len(offs)}):")
    if offs:
        start = prev = offs[0]
        regions = []
        for o in offs[1:]:
            if o - prev > 0x4000:
                regions.append((start, prev)); start = o
            prev = o
        regions.append((start, prev))
        # count writes per region + first/last ts
        for lo, hi in regions:
            ws = [(p, w, v, ts) for p, w, v, ts in fb_writes if lo <= p - FB2_LO <= hi]
            print(f"  VRAM 0x{lo:08X}-0x{hi:08X} ({hi-lo+1:>9} span) "
                  f"writes={len(ws):<7} t={ws[0][3]:.3f}..{ws[-1][3]:.3f}")
