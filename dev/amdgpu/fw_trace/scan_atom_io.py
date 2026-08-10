#!/usr/bin/env python3
# scan_atom_io.py — §35 offline audit: does this VBIOS's ASIC_Init (or anything
# it calls) switch ATOM register access to PCI/SYSIO port I/O (SETPORT opcodes
# 56/57)? Port I/O is invisible to mmiotrace, so any hit = init writes no trace
# has ever shown. Opcode lengths ported from kernel atom.c (amdgpu, 6.17).
#
# Usage: python3 scan_atom_io.py ../vbios_bus2.rom
import struct, sys

rom = open(sys.argv[1] if len(sys.argv) > 1 else '../vbios_bus2.rom', 'rb').read()
U8 = lambda o: rom[o]
U16 = lambda o: struct.unpack_from('<H', rom, o)[0]

assert rom[0] == 0x55 and rom[1] == 0xAA, "not a ROM image"
hdr = U16(0x48)
assert rom[hdr+4:hdr+8] == b'ATOM', f"no ATOM sig at 0x{hdr:X}"
cmd_table = U16(hdr + 0x1E)
n_tables = (U16(cmd_table) - 4) // 2
print(f"ATOM hdr @0x{hdr:X}  cmd_table @0x{cmd_table:X}  {n_tables} command tables")

# operand byte counts
def src_size(attr):
    arg, align = attr & 7, (attr >> 3) & 7
    if arg in (0, 4): return 2          # REG=0, ID=4 (atom.h enum)
    if arg == 5: return (4, 2, 2, 2, 1, 1, 1, 1)[align]  # IMM by align
    return 1                            # PS=1, WS=2, FB=3, PLL=6, MC=7
def dst_size(space):                    # space: 0=REG 1=PS 2=WS 3=FB 4=PLL 5=MC
    return 2 if space == 0 else 1
def direct_size(align):
    return (4, 2, 2, 2, 1, 1, 1, 1)[align]

# walk one table; returns (setport_hits, calltable_targets, notes)
def walk(base):
    size = U16(base)
    ptr = base + 6
    end = base + size
    hits, calls, notes = [], set(), []
    while ptr < end:
        op = U8(ptr); op_at = ptr; ptr += 1
        if op == 0 or op > 126:
            notes.append(f"  desync/unknown opcode {op} @0x{op_at:X} — stopping walk")
            break
        if 1 <= op <= 54 or 60 <= op <= 65 or 74 <= op <= 79 or 103 <= op <= 120 or 123 <= op <= 126:
            # move/and/or/sl/sr/mul/div/add/sub, compare, test, xor/shl/shr, mul32/div32
            space = {123: 1, 124: 2, 125: 1, 126: 2}.get(op, (op - 1) % 6)
            if 109 <= op <= 120: space = (op - 109) % 6
            elif 103 <= op <= 108: space = (op - 103) % 6
            elif 74 <= op <= 79: space = (op - 74) % 6
            elif 60 <= op <= 65: space = (op - 60) % 6
            attr = U8(ptr); ptr += 1
            ptr += dst_size(space)
            if 19 <= op <= 30:            # shift_left/right: direct BYTE0, no src
                ptr += 1
            else:
                ptr += src_size(attr)
        elif op == 55: ptr += 2; hits.append((op_at, 'ATI', U16(op_at+1)))
        elif op == 56: ptr += 1; hits.append((op_at, 'PCI', None))
        elif op == 57: ptr += 1; hits.append((op_at, 'SYSIO', None))
        elif op == 58: ptr += 2                                   # setregblock
        elif op == 59: attr = U8(ptr); ptr += 1 + src_size(attr)  # setfbbase
        elif op == 66:                                            # switch
            attr = U8(ptr); ptr += 1 + src_size(attr)
            while U16(ptr) != 0x5A5A:
                if U8(ptr) != 0x63:
                    notes.append(f"  switch case magic bad @0x{ptr:X}"); break
                ptr += 1 + direct_size((attr >> 3) & 7) + 2
            else:
                ptr += 2
                continue
            break
        elif 67 <= op <= 73: ptr += 2                             # jump
        elif op in (80, 81, 98, 121): ptr += 1                    # delay, postcard, debug
        elif op == 82:
            idx = U8(ptr); ptr += 1; calls.add(idx)
        elif op == 83 or op in (90, 99, 100, 101): pass           # repeat/nop/beep/save/restore
        elif op == 91: pass                                       # EOT (branches may follow)
        elif 84 <= op <= 89:                                      # clear: attr + dst
            space = (op - 84) % 6
            ptr += 1 + dst_size(space)
        elif 92 <= op <= 97:                                      # mask: attr + dst + direct + src
            space = (op - 92) % 6
            attr = U8(ptr); ptr += 1
            ptr += dst_size(space) + direct_size((attr >> 3) & 7) + src_size(attr)
        elif op == 102: ptr += 1                                  # setdatablock
        elif op == 122: ptr += U16(ptr) + 2                       # processds
    return hits, calls, notes

seen, queue = set(), [0]   # ASIC_Init = command table index 0
all_hits = {}
while queue:
    idx = queue.pop()
    if idx in seen or idx >= n_tables: continue
    seen.add(idx)
    base = U16(cmd_table + 4 + 2 * idx)
    if base == 0:
        print(f"table {idx}: not present"); continue
    hits, calls, notes = walk(base)
    print(f"table {idx} @0x{base:X} size={U16(base)}: "
          f"{len(hits)} SETPORT, calls -> {sorted(calls) or '-'}")
    for n in notes: print(n)
    for h in hits:
        print(f"  SETPORT_{h[1]} @0x{h[0]:X}" + (f" port=0x{h[2]:X}" if h[2] is not None else ""))
        all_hits.setdefault(h[1], []).append((idx, h[0]))
    queue.extend(calls)

print("\n=== VERDICT ===")
bad = {k: v for k, v in all_hits.items() if k in ('PCI', 'SYSIO')}
if bad:
    print("PORT-I/O SETPORT FOUND (invisible to mmiotrace):", bad)
else:
    print("NO PCI/SYSIO SETPORT reachable from ASIC_Init — the port-I/O channel is CLEAN.")
    ati = all_hits.get('ATI', [])
    print(f"(ATI/IIO SETPORTs seen: {len(ati)} — those route through MMIO, trace-visible.)")
