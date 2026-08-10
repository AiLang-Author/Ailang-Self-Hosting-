#!/usr/bin/env python3
# extract_dpm_replay.py — §26: extract the kernel's SMC/DPM sequence from
# bus2_all.txt into replay tables the driver executes verbatim.
#
# Background (handoff §25/§26): with ucode rotation fixed (§24) and the CG
# transition replicated (§25), the genuine ME still wedges at RPTR=64 on the
# first compute SET_SH. The 14:48/15:02 runs show our SMC rejects
# SetEnabledLevels/SetForcedLevels (resp 0xFF) while every kernel message gets
# 0x1: our SISLANDS statetable layout is wrong (driverState at +0x280, kernel
# at +0x6EC; 792B table vs ~3KB) and we never do the Halt(0x10) -> upload ->
# 0x80 -> Resume(0x11) -> SwitchToSwState(0x20) latch protocol. Fix: replay the
# kernel's own writes.
#
# Three windows (trace timestamps in bus2_all.txt):
#   P  (455000..463593): post-SMC-fw-upload table setup, ends just before the
#      kernel's RESET_CNTL/CLOCK_CNTL_0 SMC start @463594 (our Step 5 does the
#      start). Replayed between DPM Step 4 and Step 5 -> SMC boots on the
#      kernel's exact statetable/soft-reg/CAC SRAM image.
#   AB (463599..467045): message bursts A+B (si_dpm_enable + set_power_state).
#      Replayed right after DPM_SI_Enable, replacing UploadDriverState/force-high.
#   C  (667064..668462): the pre-IB-test burst, starts right after
#      CGLS_CTRL/CP_INT_CNTL_RING0 (the §25 block writes those). Replayed
#      immediately after the §25 CG block. Includes the DMA MGCG writes
#      (0xd0c0/0xd8c0/0xd0d8/0xd0dc) that §25 missed.
#
# Record format (12 bytes LE each): op u32, addr u32, val u32
#   op 1 = REG_WR   direct MMIO write (includes 0x884 msg-arg writes)
#   op 2 = SRAM_WR  SMC indirect: WR 0x200=addr, WR 0x204=val
#   op 3 = MSG      WR 0x22C=addr(msg id), poll 0x230 until nonzero
#
# Kept direct registers: PWRMGT/CG block 0x600-0x7FF, 0x828, the MC ARB set
# observed in the windows, msg-arg 0x884, and (window C) the DMA MGCG regs.
# Skipped on purpose: DCE/display + watermark latency regs (our own DCE6 init
# runs after), UVD block 0xE60/0xF4xx-0xF6xx, VM_CONTEXT*, CP int enables
# 0xC1A8-0xC1B0 (§25 block / IH own them), scratch/IB-test regs, 0x0030,
# 0x3E08 (fan ramp), 0x04F0/0x04FC. Every skipped reg is listed in the report.
import re
import struct
import sys
from collections import Counter

TRACE = sys.argv[1] if len(sys.argv) > 1 else "../bus2_all.txt"

# P starts right after the kernel's 15380-dword SMC fw upload (@440123-455502,
# one autoinc run from index 0x10000). Note: our own upload is 15097 dwords —
# slightly shorter than the kernel's; if replay alone doesn't fix message
# rejects, diff the fw upload sizes next.
WINDOWS = {
    "P":  (455503, 463593),
    "AB": (463599, 467045),
    "C":  (667064, 668462),
}

MC_KEEP = {0x2774, 0x2778, 0x2808, 0x27F0, 0x27FC, 0x27E8, 0x25BC, 0x25C0}
DMA_MGCG = {0xD0C0, 0xD8C0, 0xD0D8, 0xD0DC}

NAMED = {
    "SMC_IND_INDEX_0": 0x200,
    "SMC_IND_DATA_0": 0x204,
    "SMC_MSG_ARG": 0x884,
}

REG_WR, SRAM_WR, MSG = 1, 2, 3


def reg_offset(name):
    if name in NAMED:
        return NAMED[name]
    m = re.match(r"(?:REG|MC)_0x([0-9A-Fa-f]+)$", name)
    return int(m.group(1), 16) if m else None


def keep_direct(off, win):
    if off is None:
        return False
    if 0x600 <= off <= 0x7FF or off == 0x828 or off == 0x884 or off == 0x8B8:
        return True
    if off in MC_KEEP:
        return True
    if win == "C" and off in DMA_MGCG:
        return True
    return False


def main():
    events = []  # (t, name, val)
    for ln in open(TRACE):
        m = re.match(r"\s*(\d+)\s+\[b2\] WR (\S+)\s+= (0x[0-9A-Fa-f]+)", ln)
        if m:
            events.append((int(m.group(1)), m.group(2), int(m.group(3), 16)))

    # The traced boot's SMC firmware differs from disk VERDE_smc.bin (15380 vs
    # 15097 dwords; different fw-header table offsets: trace mc_reg=0x1C910 vs
    # disk 0x1DADC) — same failure class as §21's CP ucode mismatch. Extract
    # the exact image: the single 15380-dword autoinc run at index 0x10000
    # (@440123-455502). Stored as raw LE u32s, uploaded verbatim (no container
    # header, no byte swap).
    smc = []
    in_run = False
    for t, name, val in events:
        if name == "SMC_IND_INDEX_0":
            in_run = (val == 0x10000 and 440000 <= t <= 440130)
        elif name == "SMC_IND_DATA_0" and in_run:
            smc.append(val)
        elif in_run and name != "SMC_MSG_ARG":
            in_run = False
    # stored big-endian like TRACE_VERDE_{pfp,ce,me}.bin so the loader's
    # existing (b0<<24)|(b1<<16)|(b2<<8)|b3 assembly reproduces the exact
    # values the kernel wrote
    with open("TRACE_VERDE_smc.bin", "wb") as f:
        for w in smc:
            f.write(struct.pack(">I", w))
    print(f"== TRACE_VERDE_smc.bin: {len(smc)} dwords "
          f"(0x10000..0x{0x10000 + len(smc)*4:X}) head=0x{smc[0]:08X} tail=0x{smc[-1]:08X}")

    for win, (t0, t1) in WINDOWS.items():
        records = []
        skipped = Counter()
        msgs = []
        cur_index = None
        for t, name, val in events:
            off = reg_offset(name)
            # track the SRAM index across the whole trace so a window that
            # begins mid-stream still knows the current address
            if off == 0x200:
                cur_index = val
                continue
            if off == 0x204 and not (t0 <= t <= t1):
                cur_index = (cur_index + 4) if cur_index is not None else None
                continue
            if not (t0 <= t <= t1):
                continue
            if off == 0x204:
                if cur_index is None:
                    raise SystemExit(f"{win}@{t}: SRAM data write with no index")
                records.append((SRAM_WR, cur_index, val))
                cur_index += 4
                continue
            if off == 0x22C:
                records.append((MSG, val, 0))
                msgs.append(val)
                continue
            if off in (0x228, 0x230, 0x234):
                skipped[name] += 1
                continue
            if keep_direct(off, win):
                records.append((REG_WR, off, val))
            else:
                skipped[name] += 1

        binpath = f"DPM_REPLAY_{win}.bin"
        with open(binpath, "wb") as f:
            for r in records:
                f.write(struct.pack("<III", *r))
        with open(f"DPM_REPLAY_{win}.txt", "w") as f:
            for op, a, v in records:
                tag = {REG_WR: "REG", SRAM_WR: "SRAM", MSG: "MSG"}[op]
                f.write(f"{tag} 0x{a:X} 0x{v:X}\n")

        n = Counter(r[0] for r in records)
        print(f"== window {win} ({t0}-{t1}): {len(records)} records -> {binpath}")
        print(f"   REG_WR={n[REG_WR]} SRAM_WR={n[SRAM_WR]} MSG={n[MSG]}")
        if msgs:
            print(f"   msgs: {' '.join(f'{m:02X}' for m in msgs)}")
        if skipped:
            print(f"   skipped: {dict(skipped)}")


if __name__ == "__main__":
    main()
