#!/usr/bin/env python3
"""
Read HDP, BIF, and MC registers via MMIO (BAR2) on both GPUs.
Find why BAR0 (VRAM) reads return 0xFFFFFFFF on bus 2.

The CPU→VRAM path is: CPU → PCIe → BIF → HDP → MC → VRAM
Any misconfigured block in that chain kills VRAM access.
"""

import mmap
import os
import struct
import sys

BUS1 = "0000:01:00.0"
BUS2 = "0000:02:00.0"
PCI = "/sys/bus/pci/devices"

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def dump_regs(dev, label):
    path = f"{PCI}/{dev}/resource2"
    if not os.access(path, os.R_OK):
        print(f"  {label}: cannot read MMIO BAR")
        return {}

    fd = os.open(path, os.O_RDWR | os.O_SYNC)
    mm = mmap.mmap(fd, 0x40000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

    regs = {}
    reg_list = [
        # HDP block — the CPU→VRAM translation layer
        ("HDP_HOST_PATH_CNTL",       0x2C00),
        ("HDP_NONSURFACE_BASE",      0x2C04),
        ("HDP_NONSURFACE_INFO",      0x2C08),
        ("HDP_NONSURFACE_SIZE",      0x2C0C),
        ("HDP_ADDR_CONFIG",          0x2F48),
        ("HDP_MISC_CNTL",           0x2F4C),
        ("HDP_MEM_COHERENCY_FLUSH",  0x5480),

        # BIF — bus interface, controls BAR0→MC routing
        ("BIF_FB_EN",                0x5490),
        ("BIF_DOORBELL_APER_EN",     0x3938),   # might not exist on SI

        # MC — memory controller, VRAM addressing
        ("MC_VM_FB_LOCATION",        0x2024),
        ("MC_VM_AGP_TOP",            0x2028),
        ("MC_VM_AGP_BOT",            0x202C),
        ("MC_VM_AGP_BASE",           0x2030),
        ("MC_VM_SYSTEM_APERTURE_LOW",  0x2034),
        ("MC_VM_SYSTEM_APERTURE_HIGH", 0x2038),
        ("MC_VM_SYSTEM_APERTURE_DEFAULT", 0x203C),
        ("CONFIG_MEMSIZE",           0x5428),
        ("MC_SHARED_BLACKOUT_CNTL",  0x20AC),
        ("MC_ARB_RAMCFG",           0x2760),
        ("MC_SHARED_CHMAP",          0x2004),
        ("MC_SEQ_MISC0",            0x2A00),
        ("MC_SEQ_TRAIN_WAKEUP",     0x2808),

        # VM/TLB — address translation
        ("VM_CONTEXT0_CNTL",         0x1410),
        ("MC_VM_MX_L1_TLB_CNTL",   0x2064),
        ("VM_L2_CNTL",              0x1400),
        ("VM_L2_CNTL2",             0x1404),
        ("VM_L2_CNTL3",             0x1408),
        ("VM_CONTEXT0_PT_BASE",      0x1430),

        # GRBM/SRBM status
        ("GRBM_STATUS",             0x8010),
        ("GRBM_STATUS2",            0x8014),
        ("SRBM_STATUS",             0x0E50),
        ("SRBM_STATUS2",            0x0E4C),

        # GB/engine config
        ("GB_ADDR_CONFIG",           0x98F8),

        # CP state
        ("CP_ME_CNTL",              0x86D8),
        ("SCRATCH_UMSK",            0x8540),

        # SPLL (clock) — is the engine even clocked?
        ("CG_SPLL_FUNC_CNTL",      0x0600),
        ("CG_SPLL_STATUS",          0x060C),
    ]

    print(f"\n{'='*70}")
    print(f"  {label}  ({dev})")
    print(f"{'='*70}")
    print(f"  {'Register':<35} {'Offset':>8}  {'Value':>12}")
    print(f"  {'-'*35} {'-'*8}  {'-'*12}")

    for name, off in reg_list:
        try:
            val = rd32(mm, off)
            regs[name] = val
            print(f"  {name:<35} 0x{off:04X}    0x{val:08X}")
        except Exception as e:
            print(f"  {name:<35} 0x{off:04X}    ERROR: {e}")
            regs[name] = None

    mm.close()
    os.close(fd)
    return regs

def compare(r1, r2):
    print(f"\n{'='*70}")
    print(f"  COMPARISON: Bus 1 vs Bus 2")
    print(f"{'='*70}")
    print(f"  {'Register':<35} {'Bus 1':>12} {'Bus 2':>12} {'Match':>6}")
    print(f"  {'-'*35} {'-'*12} {'-'*12} {'-'*6}")

    diffs = []
    for name in r1:
        v1 = r1.get(name)
        v2 = r2.get(name)
        if v1 is None or v2 is None:
            continue
        match = "==" if v1 == v2 else "DIFF"
        line = f"  {name:<35} 0x{v1:08X}   0x{v2:08X}   {match}"
        print(line)
        if v1 != v2:
            diffs.append((name, v1, v2))

    print(f"\n  {len(diffs)} differences found")

    # Highlight critical diffs
    critical = ["HDP_NONSURFACE_BASE", "HDP_NONSURFACE_INFO", "HDP_NONSURFACE_SIZE",
                "HDP_HOST_PATH_CNTL", "HDP_MISC_CNTL", "BIF_FB_EN",
                "MC_VM_FB_LOCATION", "CONFIG_MEMSIZE", "MC_SHARED_BLACKOUT_CNTL",
                "CG_SPLL_STATUS", "CG_SPLL_FUNC_CNTL"]

    print(f"\n  CRITICAL REGISTER ANALYSIS:")
    for name, v1, v2 in diffs:
        if name in critical:
            print(f"  *** {name}: bus1=0x{v1:08X} bus2=0x{v2:08X}")

    # Specific checks
    print(f"\n  SPECIFIC CHECKS:")

    bif1 = r1.get("BIF_FB_EN", 0)
    bif2 = r2.get("BIF_FB_EN", 0)
    print(f"  BIF_FB_EN: bus1=0x{bif1:X} bus2=0x{bif2:X} — {'VRAM enabled' if bif2 & 1 else 'VRAM DISABLED (!!)'}")

    hdp_base1 = r1.get("HDP_NONSURFACE_BASE", 0)
    hdp_base2 = r2.get("HDP_NONSURFACE_BASE", 0)
    print(f"  HDP_NONSURFACE_BASE: bus1=0x{hdp_base1:08X} bus2=0x{hdp_base2:08X}")

    hdp_size1 = r1.get("HDP_NONSURFACE_SIZE", 0)
    hdp_size2 = r2.get("HDP_NONSURFACE_SIZE", 0)
    print(f"  HDP_NONSURFACE_SIZE: bus1=0x{hdp_size1:08X} bus2=0x{hdp_size2:08X}")

    mc_fb1 = r1.get("MC_VM_FB_LOCATION", 0)
    mc_fb2 = r2.get("MC_VM_FB_LOCATION", 0)
    fb_base1 = (mc_fb1 & 0xFFFF) << 24
    fb_base2 = (mc_fb2 & 0xFFFF) << 24
    print(f"  MC_VM_FB_LOCATION: bus1=0x{mc_fb1:08X} (base=0x{fb_base1:X}) bus2=0x{mc_fb2:08X} (base=0x{fb_base2:X})")

    mem1 = r1.get("CONFIG_MEMSIZE", 0)
    mem2 = r2.get("CONFIG_MEMSIZE", 0)
    print(f"  CONFIG_MEMSIZE: bus1={mem1}MB bus2={mem2}MB")

    blackout2 = r2.get("MC_SHARED_BLACKOUT_CNTL", 0)
    print(f"  MC_SHARED_BLACKOUT_CNTL bus2=0x{blackout2:X} — {'BLACKOUT ACTIVE (!!)' if blackout2 else 'OK'}")

    spll2 = r2.get("CG_SPLL_STATUS", 0)
    print(f"  CG_SPLL_STATUS bus2=0x{spll2:08X} — {'SPLL locked' if spll2 & 0x02 else 'SPLL NOT LOCKED (!!)'}")

    hdp_hpc1 = r1.get("HDP_HOST_PATH_CNTL", 0)
    hdp_hpc2 = r2.get("HDP_HOST_PATH_CNTL", 0)
    print(f"  HDP_HOST_PATH_CNTL: bus1=0x{hdp_hpc1:08X} bus2=0x{hdp_hpc2:08X}")
    if hdp_hpc1 != hdp_hpc2:
        xor = hdp_hpc1 ^ hdp_hpc2
        print(f"    XOR = 0x{xor:08X} — bits {bin(xor)} differ")

    hdp_misc1 = r1.get("HDP_MISC_CNTL", 0)
    hdp_misc2 = r2.get("HDP_MISC_CNTL", 0)
    print(f"  HDP_MISC_CNTL: bus1=0x{hdp_misc1:08X} bus2=0x{hdp_misc2:08X}")

    hdp_info1 = r1.get("HDP_NONSURFACE_INFO", 0)
    hdp_info2 = r2.get("HDP_NONSURFACE_INFO", 0)
    print(f"  HDP_NONSURFACE_INFO: bus1=0x{hdp_info1:08X} bus2=0x{hdp_info2:08X}")

    return diffs

def main():
    r1 = dump_regs(BUS1, "Bus 1 (display)")
    r2 = dump_regs(BUS2, "Bus 2 (compute)")
    if r1 and r2:
        compare(r1, r2)

if __name__ == "__main__":
    main()
