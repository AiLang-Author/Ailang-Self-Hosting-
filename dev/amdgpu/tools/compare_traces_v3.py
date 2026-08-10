#!/usr/bin/env python3
"""
Compare kernel mmiotrace (bus2_all.txt) vs our driver trace (our_mmiotrace.txt).
Resolves named registers in kernel trace to MMIO offsets using parse_mmiotrace.py mapping.
Focus on INIT PHASE: everything before the first write to CP_RB0_CNTL (0xC104).
"""

import re
import sys
from collections import OrderedDict, defaultdict

KERNEL_TRACE = "/home/bob/Ailang-Self-Hosting-/bus2_all.txt"
OUR_TRACE = "/home/bob/Ailang-Self-Hosting-/our_mmiotrace.txt"

# ── Name -> MMIO offset mapping (from parse_mmiotrace.py REGS, reversed) ──
NAME_TO_OFFSET = {
    "BIF_FB_EN": 0x5490,
    "CONFIG_MEMSIZE": 0x5428,
    "CONFIG_CNTL": 0x5430,
    "CG_SPLL_FUNC_CNTL": 0x0600,
    "CG_SPLL_FUNC_CNTL_2": 0x0604,
    "CG_SPLL_FUNC_CNTL_3": 0x0608,
    "CG_SPLL_FUNC_CNTL_4": 0x060C,
    "CG_SPLL_SPREAD_SPECTRUM": 0x0620,
    "CG_SPLL_SPREAD_SPECTRUM_2": 0x0624,
    "SPLL_STATUS": 0x0E18,
    "SMC_IND_INDEX_0": 0x0200,
    "SMC_IND_DATA_0": 0x0204,
    "SMC_IND_INDEX_1": 0x020C,
    "SMC_IND_DATA_1": 0x0210,
    "SMC_MSG": 0x0220,
    "SMC_RESP": 0x0224,
    "SMC_MSG_ARG": 0x0228,
    "SRBM_STATUS": 0x0E50,
    "SRBM_STATUS2": 0x0EC4,
    "SRBM_SOFT_RESET": 0x0E68,
    "SRBM_GFX_CNTL": 0x0E44,
    "GRBM_CNTL": 0x8000,
    "GRBM_STATUS": 0x8010,
    "GRBM_STATUS_SE0": 0x8014,
    "GRBM_STATUS_SE1": 0x8018,
    "GRBM_GFX_INDEX": 0x802C,
    "GRBM_SOFT_RESET": 0x8020,
    "MC_VM_FB_LOCATION": 0x2024,
    "MC_VM_AGP_TOP": 0x2028,
    "MC_VM_AGP_BOT": 0x202C,
    "MC_VM_AGP_BASE": 0x2030,
    "MC_VM_SYSTEM_APERTURE_LOW_ADDR": 0x2034,
    "MC_VM_SYSTEM_APERTURE_HIGH_ADDR": 0x2038,
    "MC_VM_SYSTEM_APERTURE_DEFAULT_ADDR": 0x203C,
    "MC_VM_MX_L1_TLB_CNTL": 0x2064,
    "MC_SHARED_CHMAP": 0x2004,
    "MC_SHARED_BLACKOUT_CNTL": 0x20AC,
    "MC_ARB_RAMCFG": 0x2760,
    "MC_SEQ_SUP_CNTL": 0x28C8,
    "MC_SEQ_TRAIN_WAKEUP_CNTL": 0x28E8,
    "MC_SEQ_MISC0": 0x2A00,
    "VM_L2_CNTL": 0x1400,
    "VM_L2_CNTL2": 0x1404,
    "VM_L2_CNTL3": 0x1408,
    "VM_L2_CNTL4": 0x140C,
    "VM_CONTEXT0_CNTL": 0x1410,
    "VM_CONTEXT1_CNTL": 0x1414,
    "VM_CONTEXT0_CNTL2": 0x1430,
    "VM_CONTEXT1_CNTL2": 0x1434,
    "VM_CONTEXT0_PAGE_TABLE_START_ADDR": 0x1440,
    "VM_CONTEXT1_PAGE_TABLE_START_ADDR": 0x1444,
    "VM_CONTEXT0_PAGE_TABLE_END_ADDR": 0x1460,
    "VM_CONTEXT1_PAGE_TABLE_END_ADDR": 0x1464,
    "VM_CONTEXT0_PAGE_TABLE_BASE_ADDR": 0x1540,
    "VM_CONTEXT1_PAGE_TABLE_BASE_ADDR": 0x1544,
    "VM_INVALIDATE_REQUEST": 0x1478,
    "VM_INVALIDATE_RESPONSE": 0x147C,
    "HDP_HOST_PATH_CNTL": 0x2C00,
    "HDP_NONSURFACE_BASE": 0x2C04,
    "HDP_NONSURFACE_INFO": 0x2C08,
    "HDP_NONSURFACE_SIZE": 0x2C0C,
    "HDP_ADDR_CONFIG": 0x2F48,
    "HDP_MISC_CNTL": 0x2F4C,
    "HDP_MEM_COHERENCY_FLUSH_CNTL": 0x5480,
    "GB_ADDR_CONFIG": 0x98F8,
    "DMIF_ADDR_CONFIG": 0x0BD4,
    "DMIF_ADDR_CALC": 0x0C00,
    "DMA_TILING_CONFIG": 0xD0B8,
    "TA_CNTL_AUX": 0x9508,
    "TCP_ADDR_CONFIG": 0xAC14,
    "TCP_CHAN_STEER_LO": 0xAC0C,
    "TCP_CHAN_STEER_HI": 0xAC10,
    "SPI_CONFIG_CNTL": 0x9100,
    "SPI_CONFIG_CNTL_1": 0x913C,
    "SX_DEBUG_1": 0x9060,
    "SQ_CONFIG": 0x8C00,
    "SH_MEM_CONFIG": 0x8C34,
    "SH_MEM_BASES": 0x8C28,
    "SH_MEM_APE1_BASE": 0x8C2C,
    "SH_MEM_APE1_LIMIT": 0x8C30,
    "CP_ME_CNTL": 0x86D8,
    "CP_RB0_CNTL": 0x8600,
    "CP_RB0_BASE": 0x8040,
    "CP_RB0_WPTR": 0x8610,
    "CP_RB0_RPTR": 0x8700,
    "CP_RB0_BASE_HI": 0x8604,
    "CP_RB_VMID": 0x867C,
    "CP_MEQ_THRESHOLDS": 0x8680,
    "CP_ME_RAM_WADDR": 0x86DC,
    "CP_ME_RAM_DATA": 0x86E0,
    "CP_PFP_UCODE_ADDR": 0x86E4,
    "CP_PFP_UCODE_DATA": 0x86E8,
    "CP_CE_UCODE_ADDR": 0x86EC,
    "CP_CE_UCODE_DATA": 0x86F0,
    "CP_SEM_WAIT_TIMER": 0x8060,
    "CP_SEM_INCOMPLETE_TIMER_CNTL": 0x8064,
    "RLC_CNTL": 0xC300,
    "RLC_CGTT_MGCG_OVERRIDE": 0xC400,
    "RLC_CGCG_CGLS_CTRL": 0xC404,
    "RLC_SAVE_AND_RESTORE_BASE": 0xC304,
    "RLC_GPM_UCODE_ADDR": 0xC30C,
    "RLC_GPM_UCODE_DATA": 0xC310,
    "VGA_HDP_CONTROL": 0x0328,
    "VGA_RENDER_CONTROL": 0x0300,
    "PA_SC_RASTER_CONFIG": 0x28350,
    "CGTS_SM_CTRL_REG": 0x9150,
    "SCRATCH_REG0": 0x8500,
    "SCRATCH_REG1": 0x8504,
    "SCRATCH_REG2": 0x8508,
    "SCRATCH_REG3": 0x850C,
    "SCRATCH_UMSK": 0x8540,
    "IH_RB_CNTL": 0x3E38,
    "IH_RB_BASE": 0x3E3C,
    "IH_RB_WPTR_ADDR_LO": 0x3E44,
    "IH_RB_WPTR_ADDR_HI": 0x3E48,
    "IH_CNTL": 0x3E4C,
    "CP_RB_WPTR_DELAY": 0x8048,
    "MC_VM_MD_L1_TLB0_CNTL": 0x2070,
    "MC_VM_MD_L1_TLB1_CNTL": 0x2074,
    "MC_VM_MD_L1_TLB2_CNTL": 0x2078,
    "MC_VM_MD_L1_TLB3_CNTL": 0x207C,
    "PCIE_INDEX": 0x1524,
    "PCIE_DATA": 0x1528,
    "BIF_SCRATCH0": 0x5420,
    "BIF_SCRATCH1": 0x5424,
    "ATOM_IIO_MC_INDEX": 0x000C,
    "ATOM_IIO_MC_DATA": 0x0010,
    "D1_CRTC_CONTROL": 0x6000,
    "D2_CRTC_CONTROL": 0x6800,
}

# Add tile modes
for i in range(32):
    NAME_TO_OFFSET[f"GB_TILE_MODE{i}"] = 0x9910 + i * 4

# Reverse mapping
OFFSET_TO_NAME = {v: k for k, v in NAME_TO_OFFSET.items()}

# Register block classifications
BLOCKS = OrderedDict([
    ("0x0000-0x0FFF: PLL/SPLL/Clock/SMC", (0x0000, 0x0FFF)),
    ("0x1000-0x1FFF: VM/TLB/PCIE", (0x1000, 0x1FFF)),
    ("0x2000-0x2FFF: MC/GART", (0x2000, 0x2FFF)),
    ("0x3000-0x3FFF: IH/GRBM_legacy", (0x3000, 0x3FFF)),
    ("0x5000-0x5FFF: BIF/Config/HDP_flush", (0x5000, 0x5FFF)),
    ("0x6000-0x7FFF: Display", (0x6000, 0x7FFF)),
    ("0x8000-0x8FFF: GRBM/CP/SQ/SH_MEM", (0x8000, 0x8FFF)),
    ("0x9000-0x9FFF: SPI/SQ/GB_TILE/TA", (0x9000, 0x9FFF)),
    ("0xA000-0xAFFF: CB/DB/TCP", (0xA000, 0xAFFF)),
    ("0xB000-0xBFFF: Compute/SH regs", (0xB000, 0xBFFF)),
    ("0xC000-0xCFFF: RLC/CP ring", (0xC000, 0xCFFF)),
    ("0xD000-0xDFFF: DMA/Interrupts", (0xD000, 0xDFFF)),
    ("0xE000-0xFFFF: RLC_ucode/Other", (0xE000, 0xFFFF)),
    ("0x28000+: Context regs (PA_SC)", (0x28000, 0x3FFFF)),
])


def get_block_name(offset):
    for name, (lo, hi) in BLOCKS.items():
        if lo <= offset <= hi:
            return name
    return f"Unknown block (0x{offset:04X})"


def get_reg_name(offset):
    return OFFSET_TO_NAME.get(offset, "")


def parse_kernel_writes(filepath, stop_at_c104=True):
    """
    Parse the kernel bus2_all.txt trace.
    Handles both:
    - REG_0xNNNN format (raw hex offsets)
    - NAMED_REGISTER format (resolved via NAME_TO_OFFSET)
    - MC_0xNNNN format (MC indirect via 0x28CC/0x28D0)

    Returns dict of offset -> list of (value, line_num)
    """
    writes = OrderedDict()  # offset -> list of values
    mc_writes = OrderedDict()  # mc_offset -> list of values

    # Patterns for bus 2 writes
    pat_reg = re.compile(r'\[b2\]\s+WR\s+REG_0x([0-9a-fA-F]+)\s+=\s+0x([0-9a-fA-F]+)')
    pat_mc  = re.compile(r'\[b2\]\s+WR\s+MC_0x([0-9a-fA-F]+)\s+=\s+0x([0-9a-fA-F]+)')
    pat_named = re.compile(r'\[b2\]\s+WR\s+([A-Z][A-Z0-9_]+)\s+=\s+0x([0-9a-fA-F]+)')

    line_count = 0
    with open(filepath) as f:
        for line in f:
            line_count += 1
            if '[b2]' not in line or ' WR ' not in line:
                continue

            # Try MC indirect first
            m = pat_mc.search(line)
            if m:
                mc_off = int(m.group(1), 16)
                value = int(m.group(2), 16)
                if mc_off not in mc_writes:
                    mc_writes[mc_off] = []
                mc_writes[mc_off].append(value)
                continue

            # Try named register
            m = pat_named.search(line)
            if m:
                name = m.group(1)
                value = int(m.group(2), 16)

                # Check if it's actually REG_0xNNNN pattern
                if name.startswith("REG_0x") or name.startswith("REG_"):
                    # It's a hex offset
                    try:
                        offset = int(name.replace("REG_0x", "").replace("REG_", ""), 16)
                    except ValueError:
                        continue
                else:
                    # Look up in name table
                    if name not in NAME_TO_OFFSET:
                        # Unknown named register -- skip
                        # print(f"WARNING: Unknown named register: {name} = 0x{value:08X}")
                        continue
                    offset = NAME_TO_OFFSET[name]

                # Stop at CP_RB0_CNTL
                if stop_at_c104 and offset == 0xC104:
                    print(f"[KERNEL] Stopped at CP_RB0_CNTL (0xC104) at line {line_count}")
                    break

                if offset not in writes:
                    writes[offset] = []
                writes[offset].append(value)
                continue

            # Try raw hex register
            m = pat_reg.search(line)
            if m:
                offset = int(m.group(1), 16)
                value = int(m.group(2), 16)

                if stop_at_c104 and offset == 0xC104:
                    print(f"[KERNEL] Stopped at CP_RB0_CNTL (0xC104) at line {line_count}")
                    break

                if offset not in writes:
                    writes[offset] = []
                writes[offset].append(value)

    return writes, mc_writes


def parse_our_writes(filepath, stop_at_c104=True):
    """
    Parse our driver's our_mmiotrace.txt.
    Format: MMIO_WR <seq> 0x0xNNNN 0x0xVVVV
    """
    writes = OrderedDict()

    pat = re.compile(r'MMIO_WR\s+\d+\s+0x0x([0-9a-fA-F]+)\s+0x0x([0-9a-fA-F]+)')

    with open(filepath) as f:
        for line in f:
            m = pat.search(line)
            if m:
                offset = int(m.group(1), 16)
                value = int(m.group(2), 16)

                if stop_at_c104 and offset == 0xC104:
                    print(f"[OURS] Stopped at CP_RB0_CNTL (0xC104)")
                    break

                if offset not in writes:
                    writes[offset] = []
                writes[offset].append(value)

    return writes


def main():
    print("=" * 90)
    print("KERNEL vs OUR DRIVER: Missing Register Writes During INIT Phase")
    print("(Init = everything before first write to CP_RB0_CNTL @ 0xC104)")
    print("Named registers resolved to MMIO offsets via parse_mmiotrace.py mapping")
    print("=" * 90)
    print()

    print("Parsing kernel trace...")
    kernel_mmio, kernel_mc = parse_kernel_writes(KERNEL_TRACE, stop_at_c104=True)

    print("Parsing our trace...")
    our_mmio = parse_our_writes(OUR_TRACE, stop_at_c104=True)

    print(f"\n--- Summary ---")
    print(f"Kernel: {len(kernel_mmio)} unique MMIO register offsets written")
    print(f"Kernel: {len(kernel_mc)} unique MC indirect register offsets written")
    total_kernel_writes = sum(len(v) for v in kernel_mmio.values())
    print(f"Kernel: {total_kernel_writes} total MMIO write operations")
    print(f"Our driver: {len(our_mmio)} unique MMIO register offsets written")
    total_our_writes = sum(len(v) for v in our_mmio.values())
    print(f"Our driver: {total_our_writes} total MMIO write operations")

    # Find missing/common/extra
    missing_offsets = set(kernel_mmio.keys()) - set(our_mmio.keys())
    common_offsets = set(kernel_mmio.keys()) & set(our_mmio.keys())
    extra_offsets = set(our_mmio.keys()) - set(kernel_mmio.keys())

    print(f"\nMMIO Registers: {len(missing_offsets)} MISSING (kernel writes, we don't)")
    print(f"MMIO Registers: {len(common_offsets)} COMMON (both write)")
    print(f"MMIO Registers: {len(extra_offsets)} EXTRA (we write, kernel doesn't)")

    # ── MC indirect: check what our driver does ──
    # Our driver accesses MC registers through direct MMIO offsets in the 0x2000+ range
    # The kernel does it through MC_0xNNNN indirect notation
    # Need to check if the MC indirect offsets map to the same offsets our driver uses
    # MC indirect register 0xNNNN is accessed via MMIO 0x28CC (MC_SEQ_IO_DEBUG_INDEX) and 0x28D0 (MC_SEQ_IO_DEBUG_DATA)
    # But our driver might write these same MC regs directly since they're memory-mapped
    # Let's check: does our driver write 0x28CC/0x28D0?
    our_has_28cc = 0x28CC in our_mmio
    our_has_28d0 = 0x28D0 in our_mmio
    print(f"\nOur driver writes to 0x28CC (MC indirect index): {our_has_28cc}")
    print(f"Our driver writes to 0x28D0 (MC indirect data): {our_has_28d0}")

    # Extract MC indirect addresses from our 0x28CC writes
    our_mc_addrs = set()
    if our_has_28cc:
        for val in our_mmio[0x28CC]:
            # The value written to 0x28CC encodes the MC register address
            # Format varies -- let's just collect the raw values
            our_mc_addrs.add(val)

    # Check overlap between kernel MC indirect and our MC indirect
    kernel_mc_set = set(kernel_mc.keys())
    # The kernel MC_0xNNNN offsets -- check if our direct MMIO writes cover them
    # MC registers at 0x2000-0x2FFF are often direct MMIO as well
    # Let's see which kernel MC offsets are also in our MMIO writes
    mc_covered_directly = set()
    mc_missing = set()
    for mc_off in kernel_mc:
        if mc_off in our_mmio:
            mc_covered_directly.add(mc_off)
        else:
            mc_missing.add(mc_off)

    print(f"\nMC indirect regs covered by our direct MMIO writes: {len(mc_covered_directly)}")
    print(f"MC indirect regs NOT covered by our driver: {len(mc_missing)}")

    # ── MISSING MMIO REGISTERS ──
    print("\n" + "=" * 90)
    print("MISSING MMIO REGISTER WRITES (kernel writes these, we don't)")
    print("=" * 90)

    by_block = OrderedDict()
    for offset in sorted(missing_offsets):
        block = get_block_name(offset)
        if block not in by_block:
            by_block[block] = []
        by_block[block].append(offset)

    for block_name in sorted(by_block.keys()):
        offsets = by_block[block_name]
        print(f"\n--- {block_name} ({len(offsets)} missing) ---")
        for offset in sorted(offsets):
            vals = kernel_mmio[offset]
            name = get_reg_name(offset)
            name_str = f"  ({name})" if name else ""
            unique_vals = list(OrderedDict.fromkeys(vals))
            if len(unique_vals) <= 4:
                val_str = ", ".join(f"0x{v:08X}" for v in unique_vals)
            else:
                val_str = f"0x{unique_vals[0]:08X} ... 0x{unique_vals[-1]:08X} ({len(unique_vals)} unique vals)"
            print(f"  0x{offset:04X}{name_str}: {val_str}  [{len(vals)} writes]")

    print(f"\n  TOTAL MISSING MMIO REGISTERS: {len(missing_offsets)}")

    # ── MC INDIRECT REGISTERS NOT COVERED ──
    if mc_missing:
        # Filter out the 0x2D00-0x2F50 zero-write range (GART page table entries)
        mc_gart = set()
        mc_real = set()
        for mc_off in mc_missing:
            vals = kernel_mc[mc_off]
            if all(v == 0 for v in vals) and 0x2D00 <= mc_off <= 0x2F0C:
                mc_gart.add(mc_off)
            else:
                mc_real.add(mc_off)

        print(f"\n\n{'=' * 90}")
        print(f"MISSING MC INDIRECT REGISTERS (via MC_SEQ, kernel writes, we don't)")
        print(f"Total: {len(mc_missing)} ({len(mc_gart)} are GART zeroing, {len(mc_real)} are real config)")
        print(f"{'=' * 90}")

        if mc_real:
            print(f"\n--- Important MC indirect config registers ({len(mc_real)}) ---")
            for mc_off in sorted(mc_real):
                vals = kernel_mc[mc_off]
                unique_vals = list(OrderedDict.fromkeys(vals))
                if len(unique_vals) <= 4:
                    val_str = ", ".join(f"0x{v:08X}" for v in unique_vals)
                else:
                    val_str = f"0x{unique_vals[0]:08X} ... 0x{unique_vals[-1]:08X} ({len(unique_vals)} unique vals)"
                print(f"  MC_0x{mc_off:04X}: {val_str}  [{len(vals)} writes]")

        if mc_gart:
            print(f"\n--- GART page table zeroing ({len(mc_gart)} entries, all 0x00000000) ---")
            addrs = sorted(mc_gart)
            print(f"  MC_0x{addrs[0]:04X} through MC_0x{addrs[-1]:04X} (all zeroed)")

    # ── VALUE DIFFERENCES ──
    print(f"\n\n{'=' * 90}")
    print(f"VALUE DIFFERENCES FOR COMMON REGISTERS")
    print(f"(both drivers write these, but final values differ)")
    print(f"{'=' * 90}")

    diff_count = 0
    for offset in sorted(common_offsets):
        k_last = kernel_mmio[offset][-1]
        o_last = our_mmio[offset][-1]
        if k_last != o_last:
            name = get_reg_name(offset)
            name_str = f"  ({name})" if name else ""
            print(f"  0x{offset:04X}{name_str}: kernel=0x{k_last:08X}  ours=0x{o_last:08X}")
            diff_count += 1

    if diff_count == 0:
        print("  (none)")
    else:
        print(f"\n  {diff_count} registers with different final values")

    # ── EXTRA REGISTERS ──
    print(f"\n\n{'=' * 90}")
    print(f"REGISTERS ONLY WE WRITE ({len(extra_offsets)} registers)")
    print(f"(we write these, kernel doesn't — might be harmless or wrong)")
    print(f"{'=' * 90}")

    extra_by_block = OrderedDict()
    for offset in sorted(extra_offsets):
        block = get_block_name(offset)
        if block not in extra_by_block:
            extra_by_block[block] = []
        extra_by_block[block].append(offset)

    for block_name in sorted(extra_by_block.keys()):
        offsets = extra_by_block[block_name]
        print(f"\n--- {block_name} ({len(offsets)} extra) ---")
        for offset in sorted(offsets):
            vals = our_mmio[offset]
            name = get_reg_name(offset)
            name_str = f"  ({name})" if name else ""
            unique_vals = list(OrderedDict.fromkeys(vals))
            if len(unique_vals) <= 4:
                val_str = ", ".join(f"0x{v:08X}" for v in unique_vals)
            else:
                val_str = f"0x{unique_vals[0]:08X} ... 0x{unique_vals[-1]:08X} ({len(unique_vals)} unique vals)"
            print(f"  0x{offset:04X}{name_str}: {val_str}  [{len(vals)} writes]")


if __name__ == "__main__":
    main()
