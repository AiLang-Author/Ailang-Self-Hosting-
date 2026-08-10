#!/usr/bin/env python3
# Catalog every kernel MMIO WRITE after CP unhalt (seq 439964) in bus2_all.txt,
# in order, with runs of the same offset collapsed. Companion to
# state_at_cp_unhalt.py — that reconciles state AT unhalt; this shows what the
# working boot does AFTER unhalt that our dispatch path may lack.
import re, sys

REPO = "/home/bob/Ailang-Self-Hosting-"
START = int(sys.argv[1]) if len(sys.argv) > 1 else 439964

NAMES = {
    0x8020: "GRBM_SOFT_RESET", 0x802C: "GRBM_GFX_INDEX", 0x8040: "GRBM_STATUS2",
    0x8500: "SCRATCH_REG0", 0x8504: "SCRATCH_REG1", 0x8540: "SCRATCH_UMSK",
    0x85BC: "CP_RB_VMID", 0x86D8: "CP_ME_CNTL", 0x8680: "CP_STAT",
    0x8704: "CP_DEBUG", 0x8C00: "SQ_CONFIG",
    0x9100: "SPI_CONFIG_CNTL", 0x913C: "SPI_CONFIG_CNTL_1", 0x9150: "CGTS_SM_CTRL_REG",
    0x9508: "TA_CNTL_AUX", 0x98F8: "GB_ADDR_CONFIG",
    0xB020: "SPI_SHADER_PGM_LO_PS", 0xB830: "COMPUTE_PGM_LO",
    0xB858: "SPI_STATIC_THREAD_MGMT_SE0", 0xB85C: "SPI_STATIC_THREAD_MGMT_SE1",
    0xC100: "CP_RB0_BASE", 0xC104: "CP_RB0_CNTL", 0xC10C: "CP_RB0_RPTR_ADDR",
    0xC110: "CP_RB0_RPTR_ADDR_HI", 0xC114: "CP_RB0_WPTR",
    0xC144: "CP_INT_CNTL_RING0?", 0xC154: "CP_PFP_UCODE_DATA",
    0xC160: "CP_ME_RAM_DATA", 0xC16C: "CP_CE_UCODE_DATA",
    0xC1A8: "CP_RB_WPTR_DELAY?", 0xC1FC: "?CP",
    0xC300: "RLC_CNTL", 0xC304: "RLC_RL_BASE", 0xC30C: "RLC_LB_CNTL",
    0xC310: "RLC_SAVE_AND_RESTORE_BASE", 0xC314: "RLC_CLEAR_STATE_RESTORE_BASE",
    0xC344: "RLC_MC_CNTL", 0xC348: "RLC_UCODE_CNTL", 0xC34C: "RLC_STAT",
    0xC400: "RLC_CGTT_MGCG_OVERRIDE", 0xC404: "RLC_CGCG_CGLS_CTRL",
    0xC45C: "RLC_SERDES_WR_CTRL?",
    0x200: "SMC_IND_INDEX", 0x204: "SMC_IND_DATA",
    0x0: "MM_INDEX", 0x4: "MM_DATA",
    0x30: "PCIE_INDEX", 0x34: "PCIE_DATA", 0x38: "PCIE_PORT_INDEX", 0x3C: "PCIE_PORT_DATA",
    0x600: "CG_SPLL_FUNC_CNTL", 0x604: "CG_SPLL_FUNC_CNTL_2", 0x608: "CG_SPLL_FUNC_CNTL_3",
}

KLINE = re.compile(r"^\s*(\d+)\s+\[b2\]\s+(WR|RD)\s+(\S+)\s+=\s+0x([0-9A-Fa-f]+)")
NAME2OFF = {}  # named tokens seen in trace resolve via NAMES reverse where possible

events = []  # (seq, off_or_token, val)
with open(f"{REPO}/bus2_all.txt") as f:
    for ln in f:
        m = KLINE.match(ln)
        if not m:
            continue
        seq = int(m.group(1))
        if seq < START or m.group(2) != "WR":
            continue
        tok, val = m.group(3), int(m.group(4), 16)
        if tok.startswith("REG_0x"):
            off = int(tok[6:], 16)
        else:
            off = tok  # keep symbolic
        events.append((seq, off, val))

print(f"{len(events)} kernel WRITES after seq {START}\n")

# Collapse consecutive runs on the same offset (ucode streams, polls)
i = 0
while i < len(events):
    seq, off, val = events[i]
    j = i
    vals = []
    while j < len(events) and events[j][1] == off:
        vals.append(events[j][2])
        j += 1
    if isinstance(off, int):
        name = NAMES.get(off, "")
        offs = f"0x{off:05X} {name}".rstrip()
    else:
        offs = str(off)
    if j - i == 1:
        print(f"  @{seq:<7} WR {offs} = 0x{val:08X}")
    elif j - i <= 4:
        v = " ".join(f"0x{x:08X}" for x in vals)
        print(f"  @{seq:<7} WR {offs} x{j-i} = {v}")
    else:
        print(f"  @{seq:<7} WR {offs} x{j-i} = 0x{vals[0]:08X} .. 0x{vals[-1]:08X}")
    i = j
