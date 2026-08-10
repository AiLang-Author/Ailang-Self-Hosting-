#!/usr/bin/env python3
"""
GPU probe MC: Read-only dump of MC and aperture registers via MMIO.
NO VRAM access. NO writes to any GPU register. NO PCI reset/rescan.
Pure MMIO reads through BAR2 only.

Safe to run before or after test_accel_gcn.x.
Run TWICE: once before test (cold card), once after, compare output.
"""
import mmap, struct, os, sys

COMPUTE_DEV = "/sys/bus/pci/devices/0000:02:00.0"

def open_bar_ro(dev, resource, size):
    path = os.path.join(dev, resource)
    fd = os.open(path, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, size, mmap.MAP_SHARED, mmap.PROT_READ)
    os.close(fd)
    return mm

def rd32(mm, off):
    mm.seek(off)
    return struct.unpack('<I', mm.read(4))[0]

# Check PCI CMD first — if MEM bit is 0, BAR2 reads will bus-fault
with open(os.path.join(COMPUTE_DEV, "config"), "rb") as f:
    cfg = f.read(8)
cmd = struct.unpack_from('<H', cfg, 4)[0]
if not (cmd & 0x02):
    print(f"PCI CMD = 0x{cmd:04X} — MEM bit not set, BAR2 inaccessible.")
    print("Run: python3 gpu_probe4.py  first to enable PCI CMD.")
    sys.exit(1)

mmio = open_bar_ro(COMPUTE_DEV, "resource2", 256 * 1024)

print("=" * 60)
print("GPU PROBE MC — Read-only MC/aperture/HDP register dump")
print("  Pure MMIO reads. No VRAM. No writes. No resets.")
print("=" * 60)

# MC and memory controller registers
mc_regs = [
    ("MC_VM_FB_LOCATION",              0x2024),
    ("MC_VM_AGP_TOP",                  0x2028),
    ("MC_VM_AGP_BOT",                  0x202C),
    ("MC_VM_AGP_BASE",                 0x2030),
    ("MC_VM_SYSTEM_APERTURE_LOW_ADDR", 0x2034),
    ("MC_VM_SYSTEM_APERTURE_HIGH_ADDR",0x2038),
    ("MC_VM_SYSTEM_APERTURE_DEFAULT_ADDR", 0x203C),
    ("MC_VM_FB_OFFSET",                0x2068),
    ("MC_VM_MX_L1_TLB_CNTL",          0x2064),
    ("VM_CONTEXT0_CNTL",               0x1410),
    ("VM_CONTEXT0_PAGE_TABLE_BASE_ADDR", 0x153C),
    ("VM_CONTEXT0_PAGE_TABLE_START_ADDR", 0x155C),
    ("VM_CONTEXT0_PAGE_TABLE_END_ADDR",   0x157C),
    ("MC_SHARED_BLACKOUT_CNTL",        0x20AC),
    ("MC_SEQ_MISC0",                   0x2A00),
    ("MC_ARB_RAMCFG",                  0x2760),
]

print("\n── MC / VM Registers ──")
for name, off in mc_regs:
    val = rd32(mmio, off)
    extra = ""
    if name == "MC_VM_FB_LOCATION":
        fb_base = val & 0xFFFF
        fb_top = (val >> 16) & 0xFFFF
        sz_mb = ((fb_top - fb_base + 1) << 24) // (1024*1024) if fb_top >= fb_base else 0
        extra = f"  base=0x{fb_base:04X}({fb_base<<24:#012x}) top=0x{fb_top:04X} -> {sz_mb}MB"
    elif "APERTURE_LOW" in name:
        extra = f"  -> 0x{val<<12:012X}"
    elif "APERTURE_HIGH" in name:
        extra = f"  -> 0x{val<<12:012X}"
    elif "APERTURE_DEFAULT" in name:
        extra = f"  -> 0x{val<<12:012X}"
    elif name == "MC_VM_FB_OFFSET":
        extra = f"  -> offset 0x{val<<22:012X}"
    elif name == "MC_SHARED_BLACKOUT_CNTL" and val != 0:
        extra = "  *** BLACKOUT ACTIVE ***"
    print(f"  {name:42s} [0x{off:04X}] = 0x{val:08X}{extra}")

# HDP registers
hdp_regs = [
    ("HDP_HOST_PATH_CNTL",            0x2C00),
    ("HDP_NONSURFACE_BASE",           0x2C04),
    ("HDP_NONSURFACE_INFO",           0x2C08),
    ("HDP_NONSURFACE_SIZE",           0x2C0C),
    ("HDP_MISC_CNTL",                 0x2F4C),
    ("HDP_ADDR_CONFIG",               0x2F48),
    ("HDP_MEM_COHERENCY_FLUSH_CNTL",  0x5480),
]

print("\n── HDP Registers ──")
for name, off in hdp_regs:
    val = rd32(mmio, off)
    extra = ""
    if name == "HDP_HOST_PATH_CNTL":
        extra = f"  RdCacheDis={(val>>25)&1}"
    elif name == "HDP_MISC_CNTL":
        extra = f"  FlushInvCache={val&1}"
    print(f"  {name:42s} [0x{off:04X}] = 0x{val:08X}{extra}")

# BIF
bif_regs = [
    ("BIF_FB_EN",                     0x5490),
    ("CONFIG_MEMSIZE",                0x5428),
]

print("\n── BIF / Config ──")
for name, off in bif_regs:
    val = rd32(mmio, off)
    extra = ""
    if name == "BIF_FB_EN":
        extra = f"  RD={val&1} WR={(val>>1)&1}"
    elif name == "CONFIG_MEMSIZE":
        extra = f"  -> {val//(1024*1024)}MB"
    print(f"  {name:42s} [0x{off:04X}] = 0x{val:08X}{extra}")

# SPLL / clock status
clk_regs = [
    ("CG_SPLL_FUNC_CNTL",            0x0600),
    ("CG_SPLL_FUNC_CNTL_2",          0x0604),
    ("CG_SPLL_FUNC_CNTL_3",          0x0608),
    ("CG_SPLL_FUNC_CNTL_4",          0x060C),
    ("SPLL_STATUS",                   0x0614),
    ("CG_SPLL_SPREAD_SPECTRUM",       0x0620),
    ("CG_SPLL_SPREAD_SPECTRUM_2",     0x0624),
]

print("\n── SPLL / Clock ──")
for name, off in clk_regs:
    val = rd32(mmio, off)
    extra = ""
    if name == "SPLL_STATUS":
        extra = f"  locked={'Y' if val&1 else 'N'}"
    print(f"  {name:42s} [0x{off:04X}] = 0x{val:08X}{extra}")

# CP status
cp_regs = [
    ("GRBM_STATUS",                   0x8010),
    ("GRBM_STATUS2",                  0x8008),
    ("SRBM_STATUS",                   0x0E50),
    ("SRBM_STATUS2",                  0x0EC4),
    ("CP_ME_CNTL",                    0x86D8),
    ("SCRATCH_REG0",                  0x8500),
    ("SCRATCH_UMSK",                  0x8540),
]

print("\n── CP / GRBM Status ──")
for name, off in cp_regs:
    val = rd32(mmio, off)
    print(f"  {name:42s} [0x{off:04X}] = 0x{val:08X}")

mmio.close()

print(f"\n{'='*60}")
print("PROBE MC COMPLETE — read only, no side effects")
print(f"{'='*60}")
