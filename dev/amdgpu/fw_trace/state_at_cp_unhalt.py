#!/usr/bin/env python3
# Reconcile last-written MMIO state at CP unhalt: kernel bus2_all.txt vs our_mmiotrace.txt
# Extends §23's RLC-start reconciliation to the CP-unhalt anchor.
import re, sys

REPO = "/home/bob/Ailang-Self-Hosting-"

NAME2OFF = {
    "GRBM_CNTL": 0x8000, "GRBM_SOFT_RESET": 0x8020, "GRBM_GFX_INDEX": 0x802C,
    "SCRATCH_REG0": 0x8500, "SCRATCH_UMSK": 0x8540, "CP_ME_CNTL": 0x86D8,
    "SQ_CONFIG": 0x8C00, "SX_DEBUG_1": 0x9060, "SPI_CONFIG_CNTL": 0x9100,
    "SPI_CONFIG_CNTL_1": 0x913C, "CGTS_SM_CTRL_REG": 0x9150,
    "GB_ADDR_CONFIG": 0x98F8, "TA_CNTL_AUX": 0x9508,
    "TCP_CHAN_STEER_LO": 0xAC0C, "TCP_CHAN_STEER_HI": 0xAC10, "TCP_ADDR_CONFIG": 0xAC14,
    "PA_SC_RASTER_CONFIG": 0x28350,
    "RLC_CNTL": 0xC300, "RLC_SAVE_AND_RESTORE_BASE": 0xC310,
    "RLC_GPM_UCODE_ADDR": 0xC32C, "RLC_GPM_UCODE_DATA": 0xC330,
    "RLC_CGCG_CGLS_CTRL": 0xC404, "RLC_CGTT_MGCG_OVERRIDE": 0xC400,
}
for i in range(32):
    NAME2OFF[f"GB_TILE_MODE{i}"] = 0x9910 + 4 * i

def in_ranges(off):
    return (0x8000 <= off < 0xC000) or (0xC000 <= off < 0xD000) or (0x28000 <= off < 0x29000)

KLINE = re.compile(r"^\s*(\d+)\s+\[b2\]\s+(WR|RD)\s+(\S+)\s+=\s+0x([0-9A-Fa-f]+)")
def kernel_state(anchor):
    st, order, unmapped = {}, {}, set()
    with open(f"{REPO}/bus2_all.txt") as f:
        for ln in f:
            m = KLINE.match(ln)
            if not m: continue
            seq = int(m.group(1))
            if seq > anchor: break
            if m.group(2) != "WR": continue
            tok, val = m.group(3), int(m.group(4), 16)
            if tok.startswith("REG_0x"):
                off = int(tok[6:], 16)
            elif tok in NAME2OFF:
                off = NAME2OFF[tok]
            else:
                unmapped.add(tok); continue
            if not in_ranges(off): continue
            st[off] = val
            order.setdefault(off, []).append((seq, val))
    return st, order, unmapped

OLINE = re.compile(r"MMIO_WR\s+(\d+)\s+0x0x([0-9A-Fa-f]+)\s+0x0x([0-9A-Fa-f]+)")
def our_state(anchor):
    st, order = {}, {}
    with open(f"{REPO}/our_mmiotrace.txt") as f:
        for ln in f:
            m = OLINE.search(ln)
            if not m: continue
            seq = int(m.group(1))
            if anchor and seq > anchor: continue
            off, val = int(m.group(2), 16), int(m.group(3), 16)
            if not in_ranges(off): continue
            st[off] = val
            order.setdefault(off, []).append((seq, val))
    return st, order

K_ANCHOR = 439964          # kernel WR CP_ME_CNTL=0
OUR_ANCHOR = int(sys.argv[1])  # our CP_ME_CNTL=0 write seq

kst, kord, unmapped = kernel_state(K_ANCHOR)
ost, oord = our_state(OUR_ANCHOR)
if unmapped:
    print("UNMAPPED KERNEL TOKENS (in no range check — verify none matter):", sorted(unmapped))

print(f"\nkernel regs tracked: {len(kst)}   ours: {len(ost)}")
print("\n=== KERNEL-ONLY (kernel wrote, we never did) ===")
for off in sorted(set(kst) - set(ost)):
    seqs = kord[off]
    print(f"  0x{off:05X} = 0x{kst[off]:08X}   ({len(seqs)} writes, first@{seqs[0][0]}, last@{seqs[-1][0]})")
print("\n=== OURS-ONLY (we wrote, kernel never did) ===")
for off in sorted(set(ost) - set(kst)):
    seqs = oord[off]
    print(f"  0x{off:05X} = 0x{ost[off]:08X}   ({len(seqs)} writes)")
print("\n=== VALUE MISMATCH at CP-unhalt anchor ===")
for off in sorted(set(kst) & set(ost)):
    if kst[off] != ost[off]:
        print(f"  0x{off:05X}  kernel=0x{kst[off]:08X}  ours=0x{ost[off]:08X}")
