#!/usr/bin/env python3
"""
Compare kernel mmiotrace (bus2_all.txt) vs our driver trace (our_mmiotrace.txt)
to find register writes the kernel does that we don't.

Focus on INIT PHASE: everything before the first write to CP_RB0_CNTL (0xC104).
"""

import re
import sys
from collections import OrderedDict

KERNEL_TRACE = "/home/bob/Ailang-Self-Hosting-/bus2_all.txt"
OUR_TRACE = "/home/bob/Ailang-Self-Hosting-/our_mmiotrace.txt"

# Register block classifications
BLOCKS = OrderedDict([
    ("0x0000-0x0FFF: PLL/SPLL/Clock", (0x0000, 0x0FFF)),
    ("0x1000-0x1FFF: Display/CRTC/ROM", (0x1000, 0x1FFF)),
    ("0x2000-0x2FFF: HDP", (0x2000, 0x2FFF)),
    ("0x3000-0x3FFF: MC/GRBM", (0x3000, 0x3FFF)),
    ("0x5000-0x5FFF: PCIE/Misc", (0x5000, 0x5FFF)),
    ("0x8000-0x8FFF: SPI/SQ/CP config", (0x8000, 0x8FFF)),
    ("0x9000-0x9FFF: SPI/SQ", (0x9000, 0x9FFF)),
    ("0xA000-0xAFFF: CB/DB", (0xA000, 0xAFFF)),
    ("0xB000-0xBFFF: Compute/SH regs", (0xB000, 0xBFFF)),
    ("0xC000-0xCFFF: RLC/CP ring", (0xC000, 0xCFFF)),
    ("0xD000-0xDFFF: Interrupts", (0xD000, 0xDFFF)),
    ("0xE000-0xFFFF: RLC/Other", (0xE000, 0xFFFF)),
    ("MC indirect (0x2000+)", (0x20000, 0x3FFFF)),
])

# Known register names for interesting offsets
REG_NAMES = {
    0x2000: "HDP_HOST_PATH_CNTL",
    0x2004: "HDP_NONSURFACE_BASE",
    0x2008: "HDP_NONSURFACE_INFO",
    0x200C: "HDP_NONSURFACE_SIZE",
    0x2014: "HDP_ADDR_CONFIG",
    0x2024: "HDP_MISC_CNTL",
    0x2028: "HDP_MEM_POWER_LS",
    0x2034: "HDP_SC_MULTI_CHIP_CNTL",
    0x2458: "HDP_REG_COHERENCY_FLUSH_CNTL",
    0x3000: "GRBM_CNTL",
    0x3010: "GRBM_STATUS",
    0x3018: "GRBM_STATUS_SE0",
    0x301C: "GRBM_STATUS_SE1",
    0x3020: "GRBM_SOFT_RESET",
    0x3024: "GRBM_GFX_INDEX",
    0x302C: "GRBM_INT_CNTL",
    0x30AC: "CP_ME_CNTL",
    0x30B0: "CP_ME_RAM_WADDR",
    0x30B4: "CP_ME_RAM_RADDR",
    0x30B8: "CP_ME_RAM_DATA",
    0x30E0: "CP_PFP_UCODE_ADDR",
    0x30E4: "CP_PFP_UCODE_DATA",
    0x36E0: "SRBM_SOFT_RESET",
    0x36E4: "SRBM_STATUS",
    0x36E8: "SRBM_STATUS2",
    0x36EC: "SRBM_INT_CNTL",
    0x5010: "PCIE_INDEX",
    0x5014: "PCIE_DATA",
    0x8008: "SQC_CACHES",
    0x8010: "SQ_CONFIG",
    0x8018: "SQ_GPR_RESOURCE_MGMT_1",
    0x8040: "SQ_ESGS_RING_ITEMSIZE",
    0x8048: "SQ_GSVS_RING_OFFSET_1",
    0x8050: "SQ_ESTMP_RING_SIZE",
    0x806C: "SQ_DYN_GPR_CNTL_PS_FLUSH_REQ",
    0x8C00: "SPI_CONFIG_CNTL",
    0x8C04: "SPI_CONFIG_CNTL_1",
    0x9100: "SPI_SHADER_PGM_RSRC3_PS",
    0x9508: "TA_CNTL_AUX",
    0x913C: "SPI_SHADER_LATE_ALLOC_VS",
    0x9830: "DB_DEBUG",
    0x9834: "DB_DEBUG2",
    0x9838: "DB_DEBUG3",
    0x983C: "DB_DEBUG4",
    0x9D8C: "DB_SUBTILE_CONTROL",
    0x9830: "DB_DEBUG",
    0x9834: "DB_DEBUG2",
    0x9838: "DB_DEBUG3",
    0x983C: "DB_DEBUG4",
    0x9100: "SPI_SHADER_PGM_RSRC3_PS",
    0xA180: "PA_SC_AA_CONFIG",
    0xA184: "PA_SC_FIFO_SIZE",
    0xA204: "PA_SC_CLIPRECT_0_TL",
    0xA210: "PA_SC_CLIPRECT_RULE",
    0xA354: "PA_SC_RASTER_CONFIG",
    0xB014: "CB_PERFCOUNTER0_SELECT0",
    0xC104: "CP_RB0_CNTL",
    0xC10C: "CP_RB0_RPTR_ADDR",
    0xC110: "CP_RB0_RPTR_ADDR_HI",
    0xC114: "CP_RB0_WPTR",
    0xC100: "CP_RB0_BASE",
    0xC124: "CP_RB_VMID",
    0xC200: "CP_INT_CNTL_RING0",
    0xC774: "RLC_CGTT_MGCG_OVERRIDE",
    0xC778: "RLC_CGCG_CGLS_CTRL",
    0xC77C: "RLC_PG_CNTL",
    0xC780: "RLC_SAVE_AND_RESTORE_BASE",
    0xC7C0: "RLC_AUTO_PG_CTRL",
    0xEC08: "RLC_UCODE_ADDR",
    0xEC0C: "RLC_UCODE_DATA",
    0xEC1C: "RLC_CNTL",
    0xEC20: "RLC_MC_CNTL",
}


def parse_kernel_writes(filepath, stop_at_c104=True):
    """
    Parse kernel mmiotrace.
    Format: <seq> [b2] WR <REG_NAME_OR_OFFSET> = <VALUE> [BLOCK]

    Register offset is embedded in the name like REG_0xNNNN or known names.
    Also handles MC indirect: MC_0xNNNN
    """
    writes = OrderedDict()  # offset -> list of values written (in order)

    # Patterns:
    # WR REG_0xNNNN = 0xVVVV
    # WR NAMED_REG = 0xVVVV
    # WR MC_0xNNNN = 0xVVVV (MC indirect registers)
    pat = re.compile(
        r'\[b2\]\s+WR\s+'
        r'(?:REG_0x|MC_0x|)([0-9a-fA-F]+|[\w_]+)'
        r'\s+=\s+0x([0-9a-fA-F]+)'
    )

    # More specific patterns
    pat_hex = re.compile(
        r'\[b2\]\s+WR\s+(?:REG_)?(?:0x)?([0-9a-fA-F]{3,5})\s+=\s+0x([0-9a-fA-F]+)'
    )
    pat_mc = re.compile(
        r'\[b2\]\s+WR\s+MC_0x([0-9a-fA-F]+)\s+=\s+0x([0-9a-fA-F]+)'
    )
    pat_named = re.compile(
        r'\[b2\]\s+WR\s+([A-Z_][A-Z0-9_]+)\s+=\s+0x([0-9a-fA-F]+)'
    )

    line_count = 0
    with open(filepath) as f:
        for line in f:
            line_count += 1
            if '[b2]' not in line or ' WR ' not in line:
                continue

            # Try MC indirect first
            m = pat_mc.search(line)
            if m:
                offset = int(m.group(1), 16)
                value = int(m.group(2), 16)
                key = ("MC", offset)
                if key not in writes:
                    writes[key] = []
                writes[key].append(value)
                continue

            # Try hex register pattern
            m = pat_hex.search(line)
            if m:
                offset_str = m.group(1)
                value = int(m.group(2), 16)
                try:
                    offset = int(offset_str, 16)
                except ValueError:
                    continue

                # Stop at CP_RB0_CNTL if requested
                if stop_at_c104 and offset == 0xC104:
                    print(f"[KERNEL] Stopped at CP_RB0_CNTL (0xC104) at line {line_count}")
                    break

                key = ("REG", offset)
                if key not in writes:
                    writes[key] = []
                writes[key].append(value)
                continue

            # Try named register (like CONFIG_MEMSIZE etc)
            m = pat_named.search(line)
            if m:
                name = m.group(1)
                value = int(m.group(2), 16)
                # We'll skip named regs that we can't map to offsets for now
                # but collect them separately
                key = ("NAMED", name)
                if key not in writes:
                    writes[key] = []
                writes[key].append(value)

    return writes


def parse_our_writes(filepath, stop_at_c104=True):
    """
    Parse our driver trace.
    Format: MMIO_WR <seq> 0x0xNNNN 0x0xVVVV
    Note the double 0x0x prefix.
    """
    writes = OrderedDict()

    pat = re.compile(r'MMIO_WR\s+\d+\s+0x0x([0-9a-fA-F]+)\s+0x0x([0-9a-fA-F]+)')
    # Also check for MC indirect writes via register 0x28CC (MC_SEQ_WR)
    # Our trace writes to 0x28CC the MC address, then 0x28D0 the value
    # But let's also look for explicit MC patterns
    pat_mc = re.compile(r'MC_WR\s+0x([0-9a-fA-F]+)\s+=\s+0x([0-9a-fA-F]+)', re.IGNORECASE)

    with open(filepath) as f:
        for line in f:
            m = pat.search(line)
            if m:
                offset = int(m.group(1), 16)
                value = int(m.group(2), 16)

                if stop_at_c104 and offset == 0xC104:
                    print(f"[OURS] Stopped at CP_RB0_CNTL (0xC104)")
                    break

                key = ("REG", offset)
                if key not in writes:
                    writes[key] = []
                writes[key].append(value)
                continue

            m = pat_mc.search(line)
            if m:
                offset = int(m.group(1), 16)
                value = int(m.group(2), 16)
                key = ("MC", offset)
                if key not in writes:
                    writes[key] = []
                writes[key].append(value)

    return writes


def get_block_name(reg_type, offset):
    if reg_type == "MC":
        return "MC indirect (0x2000+)"
    for name, (lo, hi) in BLOCKS.items():
        if lo <= offset <= hi:
            return name
    return f"Other (0x{offset:04X})"


def get_reg_name(offset):
    return REG_NAMES.get(offset, "")


def main():
    print("=" * 80)
    print("KERNEL vs OUR DRIVER: Missing Register Writes During INIT Phase")
    print("(Init = everything before first write to CP_RB0_CNTL @ 0xC104)")
    print("=" * 80)
    print()

    print("Parsing kernel trace...")
    kernel_writes = parse_kernel_writes(KERNEL_TRACE, stop_at_c104=True)

    print("Parsing our trace...")
    our_writes = parse_our_writes(OUR_TRACE, stop_at_c104=True)

    # Separate REG from MC and NAMED
    kernel_reg = {offset: vals for (rtype, offset), vals in kernel_writes.items() if rtype == "REG"}
    kernel_mc = {offset: vals for (rtype, offset), vals in kernel_writes.items() if rtype == "MC"}
    kernel_named = {name: vals for (rtype, name), vals in kernel_writes.items() if rtype == "NAMED"}

    our_reg = {offset: vals for (rtype, offset), vals in our_writes.items() if rtype == "REG"}
    our_mc = {offset: vals for (rtype, offset), vals in our_writes.items() if rtype == "MC"}

    print(f"\n--- Summary ---")
    print(f"Kernel: {len(kernel_reg)} unique MMIO register offsets written (REG)")
    print(f"Kernel: {len(kernel_mc)} unique MC indirect register offsets written")
    print(f"Kernel: {len(kernel_named)} unique named register writes")
    print(f"Our driver: {len(our_reg)} unique MMIO register offsets written (REG)")
    print(f"Our driver: {len(our_mc)} unique MC indirect register offsets written")

    # Find missing MMIO registers
    missing_reg = set(kernel_reg.keys()) - set(our_reg.keys())
    common_reg = set(kernel_reg.keys()) & set(our_reg.keys())
    extra_reg = set(our_reg.keys()) - set(kernel_reg.keys())

    print(f"\nMMIO Registers: {len(missing_reg)} MISSING (kernel has, we don't)")
    print(f"MMIO Registers: {len(common_reg)} COMMON (both write)")
    print(f"MMIO Registers: {len(extra_reg)} EXTRA (we write, kernel doesn't)")

    # Find missing MC registers
    missing_mc = set(kernel_mc.keys()) - set(our_mc.keys())

    # Also check: kernel writes MC via 0x28CC/0x28D0 pairs
    # Our driver also does this. Let's check if our driver writes to 0x28CC
    # If so, the MC indirect values are encoded in the 0x28CC writes
    # We need to extract those

    # Extract MC indirect addresses from 0x28CC writes
    # The kernel format is MC_0xNNNN, our format uses 0x28CC with the MC offset as value
    # Let's also compare MC indirects via 0x28CC writes
    our_mc_via_28cc = set()
    if 0x28CC in our_reg:
        for val in our_reg[0x28CC]:
            # The value written to 0x28CC is (mc_offset << 2) | flags
            # Actually, looking at the kernel trace, MC_0x28cc is the MC register
            # Let's check what values
            our_mc_via_28cc.add(val)

    kernel_mc_via_28cc = set()
    if 0x28CC in kernel_reg:
        for val in kernel_reg[0x28CC]:
            kernel_mc_via_28cc.add(val)

    # Now group missing registers by block
    print("\n" + "=" * 80)
    print("MISSING MMIO REGISTER WRITES (Kernel writes, We DON'T)")
    print("Grouped by register block")
    print("=" * 80)

    # Group by block
    by_block = OrderedDict()
    for offset in sorted(missing_reg):
        block = get_block_name("REG", offset)
        if block not in by_block:
            by_block[block] = []
        by_block[block].append(offset)

    total_missing = 0
    for block_name, offsets in sorted(by_block.items()):
        print(f"\n--- {block_name} ({len(offsets)} missing) ---")
        for offset in sorted(offsets):
            vals = kernel_reg[offset]
            reg_name = get_reg_name(offset)
            name_str = f"  ({reg_name})" if reg_name else ""
            # Show first and last value (or unique values if few)
            unique_vals = list(OrderedDict.fromkeys(vals))
            if len(unique_vals) <= 3:
                val_str = ", ".join(f"0x{v:08X}" for v in unique_vals)
            else:
                val_str = f"0x{unique_vals[0]:08X} ... 0x{unique_vals[-1]:08X} ({len(unique_vals)} unique values)"
            print(f"  0x{offset:04X}{name_str}: {val_str}  [{len(vals)} writes]")
            total_missing += 1

    print(f"\n  TOTAL MISSING MMIO REGISTERS: {total_missing}")

    # MC indirect missing
    if missing_mc:
        print(f"\n--- MC Indirect Registers ({len(missing_mc)} missing) ---")
        for offset in sorted(missing_mc):
            vals = kernel_mc[offset]
            unique_vals = list(OrderedDict.fromkeys(vals))
            if len(unique_vals) <= 3:
                val_str = ", ".join(f"0x{v:08X}" for v in unique_vals)
            else:
                val_str = f"0x{unique_vals[0]:08X} ... 0x{unique_vals[-1]:08X} ({len(unique_vals)} unique values)"
            print(f"  MC_0x{offset:04X}: {val_str}  [{len(vals)} writes]")

    # Named registers
    if kernel_named:
        print(f"\n--- Named Kernel Registers ({len(kernel_named)} total) ---")
        for name, vals in sorted(kernel_named.items()):
            unique_vals = list(OrderedDict.fromkeys(vals))
            if len(unique_vals) <= 3:
                val_str = ", ".join(f"0x{v:08X}" for v in unique_vals)
            else:
                val_str = f"0x{unique_vals[0]:08X} ... 0x{unique_vals[-1]:08X} ({len(unique_vals)} unique values)"
            print(f"  {name}: {val_str}  [{len(vals)} writes]")

    # Show what registers we write that kernel doesn't (extra)
    if extra_reg:
        print(f"\n\n{'=' * 80}")
        print(f"EXTRA REGISTERS WE WRITE THAT KERNEL DOESN'T ({len(extra_reg)} registers)")
        print(f"{'=' * 80}")
        for offset in sorted(extra_reg):
            vals = our_reg[offset]
            reg_name = get_reg_name(offset)
            name_str = f"  ({reg_name})" if reg_name else ""
            unique_vals = list(OrderedDict.fromkeys(vals))
            if len(unique_vals) <= 3:
                val_str = ", ".join(f"0x{v:08X}" for v in unique_vals)
            else:
                val_str = f"0x{unique_vals[0]:08X} ... 0x{unique_vals[-1]:08X} ({len(unique_vals)} unique values)"
            print(f"  0x{offset:04X}{name_str}: {val_str}  [{len(vals)} writes]")

    # Also show value differences for common registers
    print(f"\n\n{'=' * 80}")
    print(f"VALUE DIFFERENCES FOR COMMON REGISTERS")
    print(f"(registers both write, but with different final values)")
    print(f"{'=' * 80}")

    diff_count = 0
    for offset in sorted(common_reg):
        k_last = kernel_reg[offset][-1]
        o_last = our_reg[offset][-1]
        if k_last != o_last:
            reg_name = get_reg_name(offset)
            name_str = f"  ({reg_name})" if reg_name else ""
            print(f"  0x{offset:04X}{name_str}: kernel=0x{k_last:08X}  ours=0x{o_last:08X}")
            diff_count += 1

    if diff_count == 0:
        print("  (none - all common registers have matching final values)")
    else:
        print(f"\n  {diff_count} registers with different final values")


if __name__ == "__main__":
    main()
