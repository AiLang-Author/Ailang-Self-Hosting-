#!/usr/bin/env python3
"""
Minimal cold-boot VRAM test. Run this IMMEDIATELY after reboot,
BEFORE test_accel_gcn or any other GPU code.

Tests whether VRAM works at all on bus 2 before our driver touches it.
Also checks if BIF_FB_EN is 0 (cold boot) or 3 (post-init).
"""
import mmap, os, struct

BUS2 = "0000:02:00.0"
BUS1 = "0000:01:00.0"
PCI = "/sys/bus/pci/devices"

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def wr32(mm, off, val):
    struct.pack_into('<I', mm, off, val & 0xFFFFFFFF)

def check_bus(dev, label):
    print(f"\n=== {label} ({dev}) ===")

    # MMIO
    try:
        fd_m = os.open(f"{PCI}/{dev}/resource2", os.O_RDWR | os.O_SYNC)
        mmio = mmap.mmap(fd_m, 0x40000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
    except Exception as e:
        print(f"  MMIO map failed: {e}")
        return

    bif    = rd32(mmio, 0x5490)
    memsize= rd32(mmio, 0x5428)
    grbm   = rd32(mmio, 0x8010)
    spll   = rd32(mmio, 0x060C)
    mc_fb  = rd32(mmio, 0x2024)
    blackout=rd32(mmio, 0x20AC)
    cp_me  = rd32(mmio, 0x86D8)

    print(f"  BIF_FB_EN        = 0x{bif:X}  {'(VRAM enabled)' if bif & 1 else '(VRAM DISABLED — cold boot, not initialized)'}")
    print(f"  CONFIG_MEMSIZE   = {memsize} MB {'(MC initialized)' if memsize else '(MC NOT initialized — cold boot)'}")
    print(f"  GRBM_STATUS      = 0x{grbm:08X}  GUI_ACTIVE={'YES — GPU HUNG' if grbm & 0x20000000 else 'no'}")
    print(f"  CG_SPLL_STATUS   = 0x{spll:08X}  SPLL={'locked' if spll & 2 else 'NOT locked'}")
    print(f"  MC_VM_FB_LOCATION= 0x{mc_fb:08X}")
    print(f"  MC_BLACKOUT      = 0x{blackout:X}")
    print(f"  CP_ME_CNTL       = 0x{cp_me:08X}  CP={'halted' if cp_me & 0x10000000 else 'running'}")

    # VRAM
    try:
        fd_v = os.open(f"{PCI}/{dev}/resource0", os.O_RDWR | os.O_SYNC)
        vram = mmap.mmap(fd_v, 16*1024*1024, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
    except Exception as e:
        print(f"  VRAM map failed: {e}")
        mmio.close(); os.close(fd_m)
        return

    print(f"\n  VRAM read test (no writes):")
    for off in [0x0, 0x1000, 0x4000, 0x100000, 0x400000]:
        v = rd32(vram, off)
        print(f"    [0x{off:07X}] = 0x{v:08X} {'(uninitialized)' if v == 0xFFFFFFFF else ''}")

    print(f"\n  VRAM write/read test:")
    for off in [0x1000, 0x4000, 0x100000]:
        wr32(vram, off, 0xDEADBEEF)
        v1 = rd32(vram, off)
        wr32(vram, off, 0xCAFEBABE)
        v2 = rd32(vram, off)
        wr32(vram, off, 0x12345678)
        v3 = rd32(vram, off)
        ok = v1 == 0xDEADBEEF and v2 == 0xCAFEBABE and v3 == 0x12345678
        print(f"    [0x{off:07X}] wr1=0x{v1:08X} wr2=0x{v2:08X} wr3=0x{v3:08X} {'ALL OK' if ok else 'FAIL'}")

    vram.close(); os.close(fd_v)
    mmio.close(); os.close(fd_m)

print("GPU Cold Boot VRAM Test")
print("Run IMMEDIATELY after reboot, BEFORE test_accel_gcn!")
check_bus(BUS1, "Bus 1 (display)")
check_bus(BUS2, "Bus 2 (compute)")
