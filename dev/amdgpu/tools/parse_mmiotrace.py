#!/usr/bin/env python3
"""
parse_mmiotrace.py — Decode raw mmiotrace log into named GPU register operations.

mmiotrace format (from kernel trace_pipe):
  MAP    - ioremap event:  MAP <timestamp> <id> <phys> <virt> <len> <pc> <mod>
  UNMAP  - iounmap event:  UNMAP <timestamp> <id> <phys> <pid>
  R      - MMIO read:      R <width> <timestamp> <map_id> <phys> <value> <pc> <pid>
  W      - MMIO write:     W <width> <timestamp> <map_id> <phys> <value> <pc> <pid>
  PCIDEV - PCI device:     PCIDEV <bus_devfn> <vendor_device> ...

We decode the physical address to a BAR offset, then look up the register name
from the Cape Verde (SI) register map.  Bus 1 vs Bus 2 is identified from
PCIDEV BAR base addresses.

Usage:
    python3 parse_mmiotrace.py mmiotrace_raw.log > mmiotrace_parsed.txt
    python3 parse_mmiotrace.py mmiotrace_raw.log --writes-only
    python3 parse_mmiotrace.py mmiotrace_raw.log --filter VM,MC,TLB
    python3 parse_mmiotrace.py mmiotrace_raw.log --summary
    python3 parse_mmiotrace.py mmiotrace_raw.log --summary --bus=2
"""
import sys
import re
from collections import OrderedDict, defaultdict

# ─── SI Register Map ────────────────────────────────────────────────────────
# Matches gpu_probe_fullstate.py register set + extras from radeon driver

REGS = OrderedDict()

# PCI/BIF
REGS[0x5490] = "BIF_FB_EN"
REGS[0x5428] = "CONFIG_MEMSIZE"
REGS[0x5430] = "CONFIG_CNTL"

# Clock/PLL
REGS[0x0600] = "CG_SPLL_FUNC_CNTL"
REGS[0x0604] = "CG_SPLL_FUNC_CNTL_2"
REGS[0x0608] = "CG_SPLL_FUNC_CNTL_3"
REGS[0x060C] = "CG_SPLL_FUNC_CNTL_4"
REGS[0x0620] = "CG_SPLL_SPREAD_SPECTRUM"
REGS[0x0624] = "CG_SPLL_SPREAD_SPECTRUM_2"
REGS[0x0E18] = "SPLL_STATUS"

# SMC
REGS[0x0200] = "SMC_IND_INDEX_0"
REGS[0x0204] = "SMC_IND_DATA_0"
REGS[0x020C] = "SMC_IND_INDEX_1"
REGS[0x0210] = "SMC_IND_DATA_1"
REGS[0x0220] = "SMC_MSG"
REGS[0x0224] = "SMC_RESP"
REGS[0x0228] = "SMC_MSG_ARG"

# SRBM
REGS[0x0E50] = "SRBM_STATUS"
REGS[0x0EC4] = "SRBM_STATUS2"
REGS[0x0E68] = "SRBM_SOFT_RESET"
REGS[0x0E44] = "SRBM_GFX_CNTL"

# GRBM
REGS[0x8000] = "GRBM_CNTL"
REGS[0x8010] = "GRBM_STATUS"
REGS[0x8014] = "GRBM_STATUS_SE0"
REGS[0x8018] = "GRBM_STATUS_SE1"
REGS[0x802C] = "GRBM_GFX_INDEX"
REGS[0x8020] = "GRBM_SOFT_RESET"

# MC / VRAM
REGS[0x2024] = "MC_VM_FB_LOCATION"
REGS[0x2028] = "MC_VM_AGP_TOP"
REGS[0x202C] = "MC_VM_AGP_BOT"
REGS[0x2030] = "MC_VM_AGP_BASE"
REGS[0x2034] = "MC_VM_SYSTEM_APERTURE_LOW_ADDR"
REGS[0x2038] = "MC_VM_SYSTEM_APERTURE_HIGH_ADDR"
REGS[0x203C] = "MC_VM_SYSTEM_APERTURE_DEFAULT_ADDR"
REGS[0x2064] = "MC_VM_MX_L1_TLB_CNTL"
REGS[0x2004] = "MC_SHARED_CHMAP"
REGS[0x20AC] = "MC_SHARED_BLACKOUT_CNTL"
REGS[0x2760] = "MC_ARB_RAMCFG"
REGS[0x28C8] = "MC_SEQ_SUP_CNTL"
REGS[0x28E8] = "MC_SEQ_TRAIN_WAKEUP_CNTL"
REGS[0x2A00] = "MC_SEQ_MISC0"

# VM / TLB
REGS[0x1400] = "VM_L2_CNTL"
REGS[0x1404] = "VM_L2_CNTL2"
REGS[0x1408] = "VM_L2_CNTL3"
REGS[0x140C] = "VM_L2_CNTL4"
REGS[0x1410] = "VM_CONTEXT0_CNTL"
REGS[0x1414] = "VM_CONTEXT1_CNTL"
REGS[0x1430] = "VM_CONTEXT0_CNTL2"
REGS[0x1434] = "VM_CONTEXT1_CNTL2"
REGS[0x1440] = "VM_CONTEXT0_PAGE_TABLE_START_ADDR"
REGS[0x1444] = "VM_CONTEXT1_PAGE_TABLE_START_ADDR"
REGS[0x1460] = "VM_CONTEXT0_PAGE_TABLE_END_ADDR"
REGS[0x1464] = "VM_CONTEXT1_PAGE_TABLE_END_ADDR"
REGS[0x1540] = "VM_CONTEXT0_PAGE_TABLE_BASE_ADDR"
REGS[0x1544] = "VM_CONTEXT1_PAGE_TABLE_BASE_ADDR"
REGS[0x1478] = "VM_INVALIDATE_REQUEST"
REGS[0x147C] = "VM_INVALIDATE_RESPONSE"

# HDP (crash-prone on RD990)
REGS[0x2C00] = "HDP_HOST_PATH_CNTL"
REGS[0x2C04] = "HDP_NONSURFACE_BASE"
REGS[0x2C08] = "HDP_NONSURFACE_INFO"
REGS[0x2C0C] = "HDP_NONSURFACE_SIZE"
REGS[0x2F48] = "HDP_ADDR_CONFIG"
REGS[0x2F4C] = "HDP_MISC_CNTL"
REGS[0x5480] = "HDP_MEM_COHERENCY_FLUSH_CNTL"

# Address config
REGS[0x98F8] = "GB_ADDR_CONFIG"
REGS[0x0BD4] = "DMIF_ADDR_CONFIG"
REGS[0x0C00] = "DMIF_ADDR_CALC"
REGS[0xD0B8] = "DMA_TILING_CONFIG"

# TC pipeline
REGS[0x9508] = "TA_CNTL_AUX"
REGS[0xAC14] = "TCP_ADDR_CONFIG"
REGS[0xAC0C] = "TCP_CHAN_STEER_LO"
REGS[0xAC10] = "TCP_CHAN_STEER_HI"

# SPI
REGS[0x9100] = "SPI_CONFIG_CNTL"
REGS[0x913C] = "SPI_CONFIG_CNTL_1"
REGS[0x9060] = "SX_DEBUG_1"

# Shader memory
REGS[0x8C00] = "SQ_CONFIG"
REGS[0x8C34] = "SH_MEM_CONFIG"
REGS[0x8C28] = "SH_MEM_BASES"
REGS[0x8C2C] = "SH_MEM_APE1_BASE"
REGS[0x8C30] = "SH_MEM_APE1_LIMIT"

# CP
REGS[0x86D8] = "CP_ME_CNTL"
REGS[0x8600] = "CP_RB0_CNTL"
REGS[0x8040] = "CP_RB0_BASE"
REGS[0x8610] = "CP_RB0_WPTR"
REGS[0x8700] = "CP_RB0_RPTR"
REGS[0x8604] = "CP_RB0_BASE_HI"
REGS[0x867C] = "CP_RB_VMID"
REGS[0x8680] = "CP_MEQ_THRESHOLDS"
REGS[0x86DC] = "CP_ME_RAM_WADDR"
REGS[0x86E0] = "CP_ME_RAM_DATA"
REGS[0x86E4] = "CP_PFP_UCODE_ADDR"
REGS[0x86E8] = "CP_PFP_UCODE_DATA"
REGS[0x86EC] = "CP_CE_UCODE_ADDR"
REGS[0x86F0] = "CP_CE_UCODE_DATA"
REGS[0x8060] = "CP_SEM_WAIT_TIMER"
REGS[0x8064] = "CP_SEM_INCOMPLETE_TIMER_CNTL"

# RLC
REGS[0xC300] = "RLC_CNTL"
REGS[0xC400] = "RLC_CGTT_MGCG_OVERRIDE"
REGS[0xC404] = "RLC_CGCG_CGLS_CTRL"
REGS[0xC304] = "RLC_SAVE_AND_RESTORE_BASE"
REGS[0xC30C] = "RLC_GPM_UCODE_ADDR"
REGS[0xC310] = "RLC_GPM_UCODE_DATA"

# VGA
REGS[0x0328] = "VGA_HDP_CONTROL"
REGS[0x0300] = "VGA_RENDER_CONTROL"

# Tile modes
for i in range(32):
    REGS[0x9910 + i * 4] = f"GB_TILE_MODE{i}"

# Raster
REGS[0x28350] = "PA_SC_RASTER_CONFIG"
REGS[0x9150] = "CGTS_SM_CTRL_REG"

# Scratch
REGS[0x8500] = "SCRATCH_REG0"
REGS[0x8504] = "SCRATCH_REG1"
REGS[0x8508] = "SCRATCH_REG2"
REGS[0x850C] = "SCRATCH_REG3"
REGS[0x8540] = "SCRATCH_UMSK"

# IH (interrupt handler)
REGS[0x3E38] = "IH_RB_CNTL"
REGS[0x3E3C] = "IH_RB_BASE"
REGS[0x3E44] = "IH_RB_WPTR_ADDR_LO"
REGS[0x3E48] = "IH_RB_WPTR_ADDR_HI"
REGS[0x3E4C] = "IH_CNTL"

# Display (we mostly don't care but it's useful context)
REGS[0x6000] = "D1_CRTC_CONTROL"
REGS[0x6800] = "D2_CRTC_CONTROL"

# GPU timer
REGS[0x8048] = "CP_RB_WPTR_DELAY"

# Additional MC regs radeon writes
REGS[0x2070] = "MC_VM_MD_L1_TLB0_CNTL"
REGS[0x2074] = "MC_VM_MD_L1_TLB1_CNTL"
REGS[0x2078] = "MC_VM_MD_L1_TLB2_CNTL"
REGS[0x207C] = "MC_VM_MD_L1_TLB3_CNTL"

# AtomBIOS indirect registers
REGS[0x000C] = "ATOM_IIO_MC_INDEX"
REGS[0x0010] = "ATOM_IIO_MC_DATA"

# BIF
REGS[0x5420] = "BIF_SCRATCH0"
REGS[0x5424] = "BIF_SCRATCH1"
REGS[0x1524] = "PCIE_INDEX"
REGS[0x1528] = "PCIE_DATA"

# ─── Helper to look up register name ────────────────────────────────────────

def reg_name(offset):
    """Look up register name by MMIO offset."""
    if offset in REGS:
        return REGS[offset]
    # Check HDP protection buffer range
    if 0x2C14 <= offset <= 0x2CFC:
        idx = (offset - 0x2C14) // 0x18
        sub = (offset - 0x2C14) % 0x18
        return f"HDP_PROT_BUF{idx}+{sub:#x}"
    # MC indirect range
    if 0x2000 <= offset < 0x3000:
        return f"MC_{offset:#06x}"
    # CP firmware data (large contiguous writes)
    if offset in (0x86E0, 0x86E8, 0x86F0):
        return REGS.get(offset, f"CP_FW_DATA_{offset:#06x}")
    return f"REG_{offset:#06x}"


# ─── Category tagging ───────────────────────────────────────────────────────

def reg_category(name):
    """Tag a register with a high-level category for grouping."""
    if name.startswith("CG_SPLL") or name == "SPLL_STATUS":
        return "SPLL/PLL"
    if name.startswith("MC_") or name.startswith("CONFIG_MEM"):
        return "MC/VRAM"
    if name.startswith("VM_") or "TLB" in name:
        return "VM/TLB"
    if name.startswith("HDP_"):
        return "HDP"
    if name.startswith("CP_") or name.startswith("SCRATCH"):
        return "CP"
    if name.startswith("RLC_"):
        return "RLC"
    if name.startswith("SPI_") or name.startswith("SX_"):
        return "SPI"
    if name.startswith("SH_MEM") or name.startswith("SQ_"):
        return "SHADER"
    if name.startswith("GB_") or name.startswith("PA_"):
        return "GFX_CONFIG"
    if name.startswith("TA_") or name.startswith("TCP_"):
        return "TC_PIPELINE"
    if name.startswith("GRBM"):
        return "GRBM"
    if name.startswith("SRBM"):
        return "SRBM"
    if name.startswith("BIF_") or name == "CONFIG_CNTL":
        return "BIF/PCI"
    if name.startswith("SMC_"):
        return "SMC"
    if name.startswith("IH_"):
        return "IH"
    if name.startswith("D1_") or name.startswith("D2_") or name.startswith("VGA_"):
        return "DISPLAY"
    if name.startswith("DMIF_"):
        return "DMIF"
    if name.startswith("CGTS"):
        return "CLOCK_GATING"
    if name.startswith("DMA_"):
        return "DMA"
    if "TILE_MODE" in name:
        return "TILE_MODE"
    return "OTHER"


# ─── Parse mmiotrace ────────────────────────────────────────────────────────

def parse_mmiotrace(filepath, args):
    writes_only = "--writes-only" in args
    summary_mode = "--summary" in args

    # Filter keywords
    filter_kw = None
    for a in args:
        if a.startswith("--filter="):
            filter_kw = [k.upper() for k in a.split("=", 1)[1].split(",")]

    # Known BAR base addresses from PCI config (Cape Verde on RD990)
    # Populated from PCIDEV lines in the trace, with fallback defaults
    bar_bases = {
        # bus 1 (display GPU)
        "bus1_mmio": 0xfea00000,   # BAR2, 256KB MMIO registers
        "bus1_vram": 0xc0000000,   # BAR0, 256MB VRAM aperture
        # bus 2 (compute GPU)
        "bus2_mmio": 0xfe900000,   # BAR2, 256KB MMIO registers
        "bus2_vram": 0xb0000000,   # BAR0, 256MB VRAM aperture
    }

    maps = {}   # map_id -> (phys_base, length, module, bus_label)
    events = []
    write_summary = defaultdict(list)  # reg_name -> [(seq, value, op, bus)]

    # Parse --bus=N filter
    bus_filter = None
    for a in args:
        if a.startswith("--bus="):
            bus_filter = int(a.split("=", 1)[1])

    def identify_bar(phys, length):
        """Identify BAR type and bus from physical address."""
        for label, base in bar_bases.items():
            # MMIO BARs are 256KB (0x40000), VRAM BARs are 256MB (0x10000000)
            if label.endswith("_mmio") and phys == base:
                bus = 1 if "bus1" in label else 2
                return "MMIO", bus
            if label.endswith("_vram") and base <= phys < base + 0x10000000:
                bus = 1 if "bus1" in label else 2
                return "VRAM", bus
        # Fallback: use size heuristic
        if length >= 0x1000000:
            return "VRAM", 0
        elif length >= 0x40000:
            return "MMIO", 0
        return "OTHER", 0

    with open(filepath, "r") as f:
        seq = 0
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                if line.startswith("# "):
                    if not summary_mode:
                        print(line)
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            op = parts[0]

            if op == "PCIDEV":
                # PCIDEV <bus_devfn> <vendor_device> <irq> <BAR0> ... <BAR5> <size0> ... <size5> [driver]
                # Parse BAR addresses for GPU devices (vendor 1002, device 683d)
                if len(parts) >= 4:
                    bdf = parts[1]   # e.g. "0100" = bus 1 dev 0 fn 0
                    vid_did = parts[2]
                    if vid_did.lower().startswith("1002683d"):
                        bus_num = int(bdf[:2], 16)
                        # BAR0 at parts[3+1]=parts[4], BAR2 at parts[3+3]=parts[6]
                        if len(parts) >= 10:
                            try:
                                bar0_raw = int(parts[4], 16)
                                bar2_raw = int(parts[6], 16)
                                bar0 = bar0_raw & 0xFFFFFFF0  # mask PCI flags
                                bar2 = bar2_raw & 0xFFFFFFF0
                                if bus_num == 1:
                                    if bar2: bar_bases["bus1_mmio"] = bar2
                                    if bar0: bar_bases["bus1_vram"] = bar0
                                elif bus_num == 2:
                                    if bar2: bar_bases["bus2_mmio"] = bar2
                                    if bar0: bar_bases["bus2_vram"] = bar0
                            except ValueError:
                                pass
                continue

            if op == "MAP":
                # MAP <timestamp> <id> <phys> <virt> <len> <pc> <mod>
                if len(parts) >= 7:
                    map_id = parts[2]
                    try:
                        phys = int(parts[3], 16)
                        length = int(parts[5], 16)
                    except (ValueError, IndexError):
                        continue
                    mod = parts[7] if len(parts) > 7 else "?"
                    bar_type, bus = identify_bar(phys, length)
                    maps[map_id] = (phys, length, mod, bar_type, bus)
                    if not summary_mode:
                        bus_label = f"bus {bus}" if bus else "unknown"
                        print(f"{'─'*80}")
                        print(f"MAP id={map_id}: phys={phys:#010x} len={length:#x} => {bar_type} ({bus_label})")
                        print(f"{'─'*80}")

            elif op == "UNMAP":
                if not summary_mode and len(parts) >= 3:
                    print(f"UNMAP: id={parts[2]} @ t={parts[1]}")

            elif op in ("R", "W"):
                # R/W <width> <timestamp> <map_id> <phys_addr> <value> <pc> <pid>
                if len(parts) < 6:
                    continue

                width = int(parts[1])
                map_id = parts[3]
                try:
                    phys_addr = int(parts[4], 16)
                except ValueError:
                    continue
                try:
                    value = int(parts[5], 16)
                except ValueError:
                    continue

                # Find which MAP this address belongs to
                bar_offset = None
                bar_type = "?"
                bus = 0
                if map_id in maps:
                    base, length, mod, bar_type, bus = maps[map_id]
                    bar_offset = phys_addr - base
                else:
                    # Fallback: search all MAPs
                    for mid, (base, length, mod, bt, b) in maps.items():
                        if base <= phys_addr < base + length:
                            bar_offset = phys_addr - base
                            bar_type = bt
                            bus = b
                            break

                if bar_offset is None:
                    bar_offset = phys_addr & 0x3FFFF  # guess MMIO offset
                    bar_type = "??"

                # Apply bus filter
                if bus_filter and bus and bus != bus_filter:
                    continue

                # Only decode MMIO register accesses (not VRAM bulk transfers)
                if bar_type == "VRAM":
                    if not summary_mode and not writes_only:
                        if seq % 1000 == 0:
                            print(f"  ... {op} bus{bus} VRAM+{bar_offset:#010x} = {value:#010x} (bulk)")
                    seq += 1
                    continue

                if bar_type == "OTHER":
                    seq += 1
                    continue

                name = reg_name(bar_offset)
                cat = reg_category(name)

                # Apply filter
                if filter_kw:
                    match = False
                    for kw in filter_kw:
                        if kw in name.upper() or kw in cat.upper():
                            match = True
                            break
                    if not match:
                        continue

                if writes_only and op == "R":
                    continue

                seq += 1
                events.append((seq, op, bar_offset, name, value, width, cat, bus))
                write_summary[name].append((seq, value, op, bus))

                if not summary_mode:
                    rw = "WR" if op == "W" else "RD"
                    bus_tag = f"b{bus}" if bus else "b?"
                    # Flag critical registers
                    flag = ""
                    if "HDP" in name and name != "HDP_MEM_COHERENCY_FLUSH_CNTL":
                        flag = " *** HDP ***"
                    elif name == "MC_VM_MX_L1_TLB_CNTL":
                        flag = f" *** L1 TLB: SAM={(value>>3)&3} ADM={(value>>6)&1} ***"
                    elif name == "VM_CONTEXT0_CNTL":
                        flag = f" *** CTX0: EN={value&1} DEPTH={(value>>1)&3} ***"
                    elif name == "VM_L2_CNTL":
                        flag = " *** L2 ***"
                    elif name == "GRBM_SOFT_RESET":
                        flag = " *** SOFT RESET ***"
                    elif name == "SRBM_SOFT_RESET":
                        flag = " *** SRBM RESET ***"
                    elif name == "CP_ME_CNTL":
                        halt = "HALTED" if value & 0x10000000 else "RUNNING"
                        flag = f" *** CP {halt} ***"

                    print(f"  {seq:5d}  [{bus_tag}] {rw} {name:<40s} = 0x{value:08X}  [{cat}]{flag}")

    # ── Summary mode ──────────────────────────────────────────────────────
    if summary_mode:
        print(f"{'='*90}")
        print(f"  MMIOTRACE SUMMARY — {len(events)} register operations")
        print(f"{'='*90}")
        print()

        # Group by category
        cat_ops = defaultdict(list)
        for seq, op, off, name, val, width, cat, bus in events:
            cat_ops[cat].append((seq, op, off, name, val, bus))

        # Category order
        cat_order = ["SPLL/PLL", "MC/VRAM", "VM/TLB", "HDP", "GRBM", "SRBM",
                     "CP", "RLC", "SPI", "TC_PIPELINE", "SHADER", "GFX_CONFIG",
                     "TILE_MODE", "DMIF", "CLOCK_GATING", "SMC", "IH",
                     "BIF/PCI", "DISPLAY", "DMA", "OTHER"]

        for cat in cat_order:
            ops = cat_ops.get(cat, [])
            if not ops:
                continue
            writes = [o for o in ops if o[1] == "W"]
            reads = [o for o in ops if o[1] == "R"]
            print(f"  [{cat}] — {len(writes)} writes, {len(reads)} reads")

            # Show unique register writes with final values, per bus
            reg_final = OrderedDict()  # (name, bus) -> val
            reg_writes = defaultdict(int)
            for seq, op, off, name, val, bus in ops:
                if op == "W":
                    reg_final[(name, bus)] = val
                    reg_writes[(name, bus)] += 1

            for (name, bus), final_val in reg_final.items():
                wcount = reg_writes[(name, bus)]
                flag = ""
                bus_tag = f"b{bus}" if bus else "b?"
                if "HDP" in name and name != "HDP_MEM_COHERENCY_FLUSH_CNTL":
                    flag = " *** CRASH RISK ***"
                if wcount > 1:
                    print(f"    [{bus_tag}] {name:<38s} = 0x{final_val:08X}  ({wcount} writes){flag}")
                else:
                    print(f"    [{bus_tag}] {name:<38s} = 0x{final_val:08X}{flag}")
            print()

        # Show the registers we care most about
        print(f"{'='*90}")
        print(f"  KEY REGISTERS — final written values")
        print(f"{'='*90}")
        critical = [
            "MC_VM_MX_L1_TLB_CNTL", "VM_CONTEXT0_CNTL", "VM_L2_CNTL",
            "VM_L2_CNTL2", "VM_L2_CNTL3",
            "MC_VM_FB_LOCATION", "MC_VM_SYSTEM_APERTURE_LOW_ADDR",
            "MC_VM_SYSTEM_APERTURE_HIGH_ADDR", "MC_VM_SYSTEM_APERTURE_DEFAULT_ADDR",
            "BIF_FB_EN", "MC_SHARED_BLACKOUT_CNTL",
            "SPI_CONFIG_CNTL", "SPI_CONFIG_CNTL_1",
            "TCP_ADDR_CONFIG", "TCP_CHAN_STEER_LO", "TCP_CHAN_STEER_HI",
            "TA_CNTL_AUX", "GB_ADDR_CONFIG", "PA_SC_RASTER_CONFIG",
            "DMIF_ADDR_CONFIG", "DMIF_ADDR_CALC",
            "SH_MEM_CONFIG", "SH_MEM_BASES",
            "CP_MEQ_THRESHOLDS", "GRBM_SOFT_RESET",
            "RLC_CGTT_MGCG_OVERRIDE", "RLC_CGCG_CGLS_CTRL", "CGTS_SM_CTRL_REG",
            "HDP_HOST_PATH_CNTL", "HDP_NONSURFACE_BASE", "HDP_ADDR_CONFIG",
            "HDP_MISC_CNTL",
        ]
        for name in critical:
            entries = write_summary.get(name, [])
            # Group writes by bus
            bus_writes = defaultdict(list)
            bus_reads = defaultdict(list)
            for s, v, o, b in entries:
                if o == "W":
                    bus_writes[b].append((s, v))
                else:
                    bus_reads[b].append((s, v))
            if bus_writes:
                for b in sorted(bus_writes.keys()):
                    ws = bus_writes[b]
                    final_val = ws[-1][1]
                    bus_tag = f"b{b}" if b else "b?"
                    if len(ws) > 1:
                        first_val = ws[0][1]
                        print(f"  [{bus_tag}] {name:<42s} = 0x{final_val:08X}  (first: 0x{first_val:08X}, {len(ws)} writes)")
                    else:
                        print(f"  [{bus_tag}] {name:<42s} = 0x{final_val:08X}")
            elif bus_reads:
                for b in sorted(bus_reads.keys()):
                    rs = bus_reads[b]
                    bus_tag = f"b{b}" if b else "b?"
                    print(f"  [{bus_tag}] {name:<42s} = 0x{rs[-1][1]:08X}  (read-only, never written)")
            else:
                print(f"  {name:<48s} (not accessed)")

        print()
        print(f"Total MMIO operations: {len(events)}")
        total_w = sum(1 for e in events if e[1] == "W")
        total_r = sum(1 for e in events if e[1] == "R")
        print(f"  Writes: {total_w}")
        print(f"  Reads:  {total_r}")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 parse_mmiotrace.py <mmiotrace_raw.log> [options]")
        print()
        print("Options:")
        print("  --writes-only        Only show writes (skip reads)")
        print("  --summary            Show summary with final values per register")
        print("  --filter=KW1,KW2     Filter by register name or category keyword")
        print()
        print("Examples:")
        print("  python3 parse_mmiotrace.py mmiotrace_raw.log --summary")
        print("  python3 parse_mmiotrace.py mmiotrace_raw.log --writes-only --filter=VM,TLB")
        print("  python3 parse_mmiotrace.py mmiotrace_raw.log --filter=HDP")
        sys.exit(1)

    parse_mmiotrace(sys.argv[1], sys.argv[2:])
