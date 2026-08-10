#!/usr/bin/env python3
"""
Compare our MMIO trace against the kernel mmiotrace.
Extracts register writes from both, normalizes format, and shows differences.
"""
import re
import sys

def parse_our_trace(filename):
    """Parse our MMIO_WR lines: MMIO_WR SEQ 0x0xOFFSET 0x0xVALUE"""
    writes = []
    with open(filename) as f:
        for line in f:
            m = re.match(r'MMIO_WR\s+(\d+)\s+0x0x([0-9A-Fa-f]+)\s+0x0x([0-9A-Fa-f]+)', line)
            if m:
                seq = int(m.group(1))
                offset = int(m.group(2), 16)
                value = int(m.group(3), 16)
                writes.append((seq, offset, value))
    return writes

def parse_kernel_trace(filename, max_seq=440000):
    """Parse kernel mmiotrace: SEQ  WR REGNAME/REG_0xOFFSET  = 0xVALUE"""
    writes = []
    # Map known register names to offsets
    reg_map = {
        'GRBM_CNTL': 0x8000, 'GRBM_STATUS': 0x8010, 'GRBM_SOFT_RESET': 0x8020,
        'GRBM_GFX_INDEX': 0x802C,
        'CP_RB0_CNTL': 0xC104, 'CP_RB0_BASE': 0xC100, 'CP_RB0_RPTR_ADDR': 0xC10C,
        'CP_RB0_RPTR_ADDR_HI': 0xC110, 'CP_RB0_WPTR': 0xC114,
        'CP_RB1_CNTL': 0xC184, 'CP_RB1_BASE': 0xC180, 'CP_RB1_RPTR_ADDR': 0xC188,
        'CP_RB1_RPTR_ADDR_HI': 0xC18C, 'CP_RB1_WPTR': 0xC190,
        'CP_RB2_CNTL': 0xC198, 'CP_RB2_BASE': 0xC194, 'CP_RB2_RPTR_ADDR': 0xC19C,
        'CP_RB2_RPTR_ADDR_HI': 0xC1A0, 'CP_RB2_WPTR': 0xC1A4,
        'CP_ME_CNTL': 0x86D8,
        'MC_VM_FB_LOCATION': 0x2024,
        'MC_VM_AGP_TOP': 0x2028, 'MC_VM_AGP_BOT': 0x202C, 'MC_VM_AGP_BASE': 0x2030,
        'MC_VM_SYSTEM_APERTURE_LOW_ADDR': 0x2034,
        'MC_VM_SYSTEM_APERTURE_HIGH_ADDR': 0x2038,
        'MC_VM_SYSTEM_APERTURE_DEFAULT_ADDR': 0x203C,
        'MC_VM_MX_L1_TLB_CNTL': 0x2064,
        'VM_L2_CNTL': 0x1400, 'VM_L2_CNTL2': 0x1404, 'VM_L2_CNTL3': 0x1408,
        'VM_CONTEXT0_CNTL': 0x1410, 'VM_CONTEXT0_CNTL2': 0x1430,
        'VM_CONTEXT0_PAGE_TABLE_BASE_ADDR': 0x153C,
        'VM_CONTEXT1_PAGE_TABLE_BASE_ADDR': 0x1540,
        'VM_CONTEXT0_PAGE_TABLE_START_ADDR': 0x1440,
        'VM_CONTEXT1_PAGE_TABLE_START_ADDR': 0x1444,
        'VM_CONTEXT1_CNTL': 0x1414, 'VM_CONTEXT1_CNTL2': 0x1434,
        'VM_INVALIDATE_REQUEST': 0x1478,
        'HDP_MEM_COHERENCY_FLUSH_CNTL': 0x5480,
        'HDP_HOST_PATH_CNTL': 0x2C00, 'HDP_MISC_CNTL': 0x2F4C,
        'HDP_ADDR_CONFIG': 0x2F48, 'HDP_NONSURFACE_BASE': 0x2C04,
        'VGA_HDP_CONTROL': 0x0328, 'VGA_RENDER_CONTROL': 0x0300,
        'RLC_CNTL': 0xC300, 'RLC_SAVE_AND_RESTORE_BASE': 0xC310,
        'RLC_GPM_UCODE_ADDR': 0xC32C, 'RLC_GPM_UCODE_DATA': 0xC330,
        'GB_ADDR_CONFIG': 0x98F8, 'DMIF_ADDR_CONFIG': 0x0BD4,
        'DMIF_ADDR_CALC': 0x0C00, 'DMA_TILING_CONFIG': 0xD0B8,
        'SX_DEBUG_1': 0x9060, 'SPI_CONFIG_CNTL_1': 0x913C,
        'SQ_CONFIG': 0x8C00, 'PA_SC_RASTER_CONFIG': 0x28350,
        'BIF_FB_EN': 0x5490, 'SCRATCH_UMSK': 0x8540, 'SCRATCH_REG0': 0x8500,
        'MC_SEQ_SUP_CNTL': 0x28C8,
        'HDP_NONSURFACE_BASE': 0x2C04, 'HDP_NONSURFACE_INFO': 0x2C08,
        'HDP_NONSURFACE_SIZE': 0x2C0C,
        'HDP_ADDR_CONFIG': 0x2F48,
        'VGA_HDP_CONTROL': 0x0328,
        'IH_RB_CNTL': 0x3E00, 'IH_RB_BASE': 0x3E04, 'IH_RB_RPTR': 0x3E08,
        'IH_RB_WPTR': 0x3E0C, 'IH_RPTR_ADDR_HI': 0x3E10,
        'IH_RPTR_ADDR_LO': 0x3E14, 'IH_CNTL': 0x3E18,
        'INTERRUPT_CNTL': 0x5468, 'INTERRUPT_CNTL2': 0x546C,
        'IH_RB_WPTR_ADDR_LO': 0x3E20, 'IH_RB_WPTR_ADDR_HI': 0x3E24,
    }
    # Also handle GB_TILE_MODEn
    for i in range(32):
        reg_map[f'GB_TILE_MODE{i}'] = 0x9910 + i * 4

    with open(filename) as f:
        for line in f:
            line = line.strip()
            # Skip comments, headers, phase markers, summary lines
            if not line or line.startswith('=') or line.startswith('-') or line.startswith('PHASE') or line.startswith('Notes') or line.startswith('Format') or line.startswith('Bus') or line.startswith('Total'):
                continue
            # Skip MC indirect writes (MC_0x...) and SMC writes
            if 'MC_0x' in line or 'SMC_' in line:
                continue
            # Skip ellipsis lines
            if '...' in line:
                continue

            # Named register: SEQ  WR REGNAME  = 0xVALUE
            m = re.match(r'\s*(\d+)\s+WR\s+(\S+)\s+=\s+0x([0-9A-Fa-f]+)', line)
            if m:
                seq = int(m.group(1))
                if seq > max_seq:
                    continue  # skip post-init writes
                regname = m.group(2)
                value = int(m.group(3), 16)

                if regname.startswith('REG_0x'):
                    offset = int(regname[6:], 16)
                elif '+' in regname:
                    # Handle HDP_PROT_BUFn+0xNN style names
                    # HDP_PROT_BUF starts at 0x2C14, each buffer is 0x18 apart
                    import re as re2
                    m2 = re2.match(r'HDP_PROT_BUF(\d+)\+0x([0-9a-fA-F]+)', regname)
                    if m2:
                        offset = 0x2C14 + int(m2.group(1)) * 0x18 + int(m2.group(2), 16)
                    else:
                        continue
                elif regname in reg_map:
                    offset = reg_map[regname]
                else:
                    continue  # skip unknown named regs
                writes.append((seq, offset, value))
    return writes


def main():
    our = parse_our_trace('our_mmiotrace.txt')
    kernel = parse_kernel_trace('mmiotrace_init_sequence.txt')

    print(f"Our trace: {len(our)} writes")
    print(f"Kernel trace: {len(kernel)} writes")
    print()

    # Convert to (offset, value) sequences for comparison
    # Skip firmware bulk writes (repeated writes to same addr) and MC indirect writes
    # Focus on init sequence: filter to unique meaningful registers

    # Build ordered list of (offset, value) for both, skipping firmware data regs
    firmware_regs = {0xC330, 0xC32C,  # RLC ucode
                     0xC154, 0xC150,  # CP ME ucode
                     0xC16C, 0xC168,  # CP PFP ucode
                     0xC160, 0xC15C,  # CP CE ucode
                     0xC158,          # CP ME RAM RADDR
                     0x2A44, 0x2A48,  # MC indirect
                     0x28CC}          # MC_SEQ_SUP_PGM

    # Also skip SPLL/SMC registers that are AtomBIOS-driven (different per card)
    # Skip display controller regs (0x6xxx-0x12xxx range, except known GFX regs)

    # SMC indirect port regs (we use them, kernel does too but via different mechanism)
    smc_regs = {0x0200, 0x0204, 0x0228, 0x022C, 0x0230}

    # MC indirect port registers (0x0000-0x0004 are MC_SEQ_IO_DEBUG_INDEX/DATA,
    # not real GPU registers — they appear in traces during MC training)
    # 0x5428 = HDP_MEM_COHERENCY_FLUSH_CNTL — written repeatedly during MC training
    mc_indirect_regs = {0x0000, 0x0004, 0x5428}

    # BIF config space registers written by AtomBIOS (unfixable)
    bif_config_regs = {0x0030, 0x0034, 0x0038, 0x003C}

    # IH ring address-dependent registers — kernel allocates IH ring, writeback,
    # and dummy page in GART (system memory); we allocate in VRAM.  The addresses
    # will inherently differ.  Control bits (IH_RB_CNTL, IH_CNTL) are compared
    # but pure address registers are skipped.
    ih_addr_regs = {0x3E04,  # IH_RB_BASE (ring GPU addr >> 8)
                    0x3E08,  # IH_RB_RPTR (advances after enable — timing dependent)
                    0x3E10,  # IH_RB_WPTR_ADDR_HI (writeback addr hi)
                    0x3E14,  # IH_RB_WPTR_ADDR_LO (writeback addr lo)
                    0x546C}  # INTERRUPT_CNTL2 (dummy page addr >> 8)

    # DPM/SMC direct access regs (0x0600-0x08FF) — kernel uses SMC indirect,
    # we write directly. Same effect, different trace appearance.
    # Also 0x2000-0x2F4F range used by MC indirect and DPM except known regs.
    known_mc_regs = {0x2024, 0x2028, 0x202C, 0x2030, 0x2034, 0x2038, 0x203C,
                     0x2064, 0x2C00, 0x2C04, 0x2C08, 0x2C0C, 0x2F48, 0x2F4C}

    def is_init_reg(offset):
        """Filter to GFX/compute init registers, skip display/SPLL/firmware bulk"""
        if offset in firmware_regs:
            return False
        if offset in smc_regs:
            return False
        if offset in mc_indirect_regs:
            return False
        if offset in bif_config_regs:
            return False
        if offset in ih_addr_regs:
            return False
        # DPM/SMC registers — kernel writes via SMC indirect, we write directly
        if 0x0600 <= offset <= 0x08FF:
            return False
        # MC/DPM registers (0x2000-0x2F4F) except known VM/HDP regs
        if 0x2000 <= offset <= 0x2F4F and offset not in known_mc_regs:
            return False
        # Display controller range
        if 0x6000 <= offset <= 0x12FFF and offset not in {0x8000, 0x8010, 0x8020, 0x802C}:
            return False
        return True

    our_init = [(off, val) for (_, off, val) in our if is_init_reg(off)]
    kernel_init = [(off, val) for (_, off, val) in kernel if is_init_reg(off)]

    print(f"Our init writes (filtered): {len(our_init)}")
    print(f"Kernel init writes (filtered): {len(kernel_init)}")
    print()

    # Now do a sequential comparison - find where they diverge
    # First, let's compare the register write ORDER and VALUES

    # Group writes by offset to see what we write vs what kernel writes
    from collections import OrderedDict

    our_by_reg = OrderedDict()
    for off, val in our_init:
        if off not in our_by_reg:
            our_by_reg[off] = []
        our_by_reg[off].append(val)

    kernel_by_reg = OrderedDict()
    for off, val in kernel_init:
        if off not in kernel_by_reg:
            kernel_by_reg[off] = []
        kernel_by_reg[off].append(val)

    # Find registers kernel writes but we don't
    missing = set(kernel_by_reg.keys()) - set(our_by_reg.keys())
    extra = set(our_by_reg.keys()) - set(kernel_by_reg.keys())
    common = set(our_by_reg.keys()) & set(kernel_by_reg.keys())

    if missing:
        print("=" * 70)
        print("REGISTERS KERNEL WRITES BUT WE DON'T:")
        print("=" * 70)
        for off in sorted(missing):
            vals = kernel_by_reg[off]
            print(f"  0x{off:04X}: kernel writes {len(vals)}x, last value=0x{vals[-1]:08X}")
        print()

    if extra:
        print("=" * 70)
        print("REGISTERS WE WRITE BUT KERNEL DOESN'T:")
        print("=" * 70)
        for off in sorted(extra):
            vals = our_by_reg[off]
            print(f"  0x{off:04X}: we write {len(vals)}x, last value=0x{vals[-1]:08X}")
        print()

    # For common registers, compare final values
    mismatched = []
    for off in sorted(common):
        our_last = our_by_reg[off][-1]
        kernel_last = kernel_by_reg[off][-1]
        if our_last != kernel_last:
            mismatched.append((off, our_last, kernel_last))

    if mismatched:
        print("=" * 70)
        print("REGISTERS WITH DIFFERENT FINAL VALUES:")
        print("=" * 70)
        for off, ours, theirs in mismatched:
            print(f"  0x{off:04X}: ours=0x{ours:08X}  kernel=0x{theirs:08X}")
        print()

    # Now do sequential order comparison for the init phase
    # This shows where our ordering differs from kernel
    print("=" * 70)
    print("SEQUENTIAL ORDER COMPARISON (first 500 filtered writes):")
    print("=" * 70)
    limit = min(500, len(our_init), len(kernel_init))
    diverge_count = 0
    for i in range(limit):
        our_off, our_val = our_init[i]
        ker_off, ker_val = kernel_init[i]
        if our_off != ker_off or our_val != ker_val:
            diverge_count += 1
            if diverge_count <= 30:
                marker = ""
                if our_off != ker_off:
                    marker = " *** DIFFERENT REG"
                elif our_val != ker_val:
                    marker = " *** DIFFERENT VALUE"
                print(f"  [{i:4d}] ours: 0x{our_off:04X}=0x{our_val:08X}  kernel: 0x{ker_off:04X}=0x{ker_val:08X}{marker}")
    print(f"\n  Total divergences in first {limit}: {diverge_count}")


if __name__ == '__main__':
    main()
