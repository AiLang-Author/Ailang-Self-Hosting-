#!/usr/bin/env python3
"""
GPU probe phase 2: MC (memory controller) state deep dive.
BAR0 reads return 0xFFFFFFFF everywhere — diagnose why.
"""
import mmap, struct, os

PCI_DEV = "/sys/bus/pci/devices/0000:02:00.0"

def open_bar(resource, size):
    path = os.path.join(PCI_DEV, resource)
    fd = os.open(path, os.O_RDWR | os.O_SYNC)
    mm = mmap.mmap(fd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
    os.close(fd)
    return mm

def rd32(mm, off):
    mm.seek(off)
    return struct.unpack('<I', mm.read(4))[0]

def wr32(mm, off, val):
    mm.seek(off)
    mm.write(struct.pack('<I', val & 0xFFFFFFFF))

mmio = open_bar("resource2", 256*1024)

print("=" * 60)
print("MC / BIF / HDP Deep Probe")
print("=" * 60)

# MC registers
mc_regs = [
    # MC config
    ("MC_VM_FB_LOCATION",          0x2024),
    ("MC_VM_AGP_TOP",              0x2028),
    ("MC_VM_AGP_BOT",              0x202C),
    ("MC_VM_AGP_BASE",             0x2030),
    ("MC_VM_SYS_APT_LOW",          0x2034),
    ("MC_VM_SYS_APT_HIGH",         0x2038),
    ("MC_VM_SYS_APT_DEF",          0x203C),

    # MC sequencer / config
    ("MC_SEQ_MISC0",               0x2A00),
    ("MC_SEQ_MISC1",               0x2A04),
    ("MC_SEQ_MISC3",               0x2A0C),
    ("MC_SEQ_MISC5",               0x2A14),
    ("MC_SEQ_MISC6",               0x2A18),
    ("MC_SEQ_MISC7",               0x2A1C),
    ("MC_SEQ_MISC8",               0x2A20),
    ("MC_ARB_RAMCFG",              0x2760),

    # MC status / control
    ("MC_SHARED_BLACKOUT_CNTL",    0x20AC),
    ("MC_HUB_MISC_STATUS",         0x206C),
    ("MC_HUB_MISC_HUB_CG",        0x2068),
    ("MC_HUB_MISC_VM_CG",         0x206C),
    ("MC_CITF_MISC_RD_CG",        0x2750),
    ("MC_CITF_MISC_WR_CG",        0x2754),
    ("MC_CITF_MISC_VM_CG",        0x2758),

    # BIF (Bus InterFace) — gates BAR0 access
    ("BIF_FB_EN",                  0x5490),
    ("BIF_DOORBELL_APER_EN",       0x3400),

    # HDP path
    ("HDP_HOST_PATH_CNTL",        0x2C00),
    ("HDP_NONSURFACE_BASE",       0x2C04),
    ("HDP_NONSURFACE_INFO",       0x2C08),
    ("HDP_NONSURFACE_SIZE",       0x2C0C),
    ("HDP_NONSURFACE_BASE_HI",   0x2C10),
    ("HDP_ADDR_CONFIG",           0x2F48),
    ("HDP_MISC_CNTL",            0x2F4C),
    ("HDP_MEM_COHERENCY_FLUSH",  0x5480),

    # VM / TLB
    ("VM_CONTEXT0_CNTL",          0x1410),
    ("VM_CONTEXT0_PAGE_TABLE_BASE", 0x153C),
    ("VM_CONTEXT0_PAGE_TABLE_START", 0x155C),
    ("VM_CONTEXT0_PAGE_TABLE_END",   0x157C),
    ("VM_L2_CNTL",                0x1400),
    ("VM_L2_CNTL2",               0x1404),
    ("VM_L2_CNTL3",               0x1408),
    ("MC_VM_MX_L1_TLB_CNTL",     0x2064),
    ("VM_INVALIDATE_REQUEST",     0x1478),
    ("VM_INVALIDATE_RESPONSE",    0x147C),

    # GRBM / SRBM status
    ("GRBM_STATUS",               0x8010),
    ("GRBM_STATUS2",              0x8008),
    ("GRBM_STATUS_SE0",           0x8014),
    ("GRBM_STATUS_SE1",           0x8018),
    ("SRBM_STATUS",               0x0E50),
    ("SRBM_STATUS2",              0x0E4C),

    # CP status
    ("CP_ME_CNTL",                0x86D8),
    ("CP_RB0_CNTL",               0x8604),
    ("CP_RB0_BASE",               0x8608),
    ("CP_RB0_RPTR",               0x8600),
    ("CP_RB0_WPTR",               0x8610),
]

print("\n--- Full Register Dump ---")
for name, off in mc_regs:
    val = rd32(mmio, off)
    print(f"  {name:35s} [0x{off:04X}] = 0x{val:08X}")

# Decode MC_VM_FB_LOCATION
fb_loc = rd32(mmio, 0x2024)
fb_base = fb_loc & 0xFFFF
fb_top = (fb_loc >> 16) & 0xFFFF
print(f"\n--- MC_VM_FB_LOCATION decode ---")
print(f"  raw = 0x{fb_loc:08X}")
print(f"  FB_BASE = 0x{fb_base:04X}  -> VRAM starts at GPU addr 0x{fb_base << 24:012X}")
print(f"  FB_TOP  = 0x{fb_top:04X}  -> VRAM ends at   GPU addr 0x{(fb_top+1) << 24:012X}")
print(f"  VRAM size = {((fb_top - fb_base + 1) << 24) // (1024*1024)} MB")

# Decode BIF_FB_EN
bif = rd32(mmio, 0x5490)
print(f"\n--- BIF_FB_EN decode ---")
print(f"  raw = 0x{bif:08X}")
print(f"  FB_READ_EN  (bit 0) = {bif & 1}")
print(f"  FB_WRITE_EN (bit 1) = {(bif >> 1) & 1}")

# Decode HDP_HOST_PATH_CNTL
hpc = rd32(mmio, 0x2C00)
print(f"\n--- HDP_HOST_PATH_CNTL decode ---")
print(f"  raw = 0x{hpc:08X}")
print(f"  bit 25 (READ_CACHE_DISABLE) = {(hpc >> 25) & 1}")

# Decode MC_SHARED_BLACKOUT_CNTL
blackout = rd32(mmio, 0x20AC)
print(f"\n--- MC_SHARED_BLACKOUT_CNTL ---")
print(f"  raw = 0x{blackout:08X}")
if blackout != 0:
    print(f"  *** BLACKOUT ACTIVE — THIS BLOCKS ALL MC ACCESS! ***")
else:
    print(f"  No blackout (normal)")

# Try toggling BIF_FB_EN
print("\n--- Attempting BIF_FB_EN toggle test ---")
print(f"  Current BIF_FB_EN = 0x{rd32(mmio, 0x5490):08X}")
# Ensure bits 0 and 1 are both set
wr32(mmio, 0x5490, 0x3)
print(f"  After write 0x3: BIF_FB_EN = 0x{rd32(mmio, 0x5490):08X}")

# Open VRAM and test
vram = open_bar("resource0", 256*1024*1024)
vram.seek(0)
val = struct.unpack('<I', vram.read(4))[0]
print(f"  VRAM[0x0] = 0x{val:08X}")

# Try HDP flush + read
wr32(mmio, 0x5480, 1)  # HDP flush
vram.seek(0x1000)
val = struct.unpack('<I', vram.read(4))[0]
print(f"  VRAM[0x1000] after HDP flush = 0x{val:08X}")

# Try disabling HDP nonsurface cache and reading
print("\n--- HDP nonsurface config test ---")
# Save current
ns_base = rd32(mmio, 0x2C04)
ns_info = rd32(mmio, 0x2C08)
ns_size = rd32(mmio, 0x2C0C)
print(f"  NONSURFACE_BASE = 0x{ns_base:08X}")
print(f"  NONSURFACE_INFO = 0x{ns_info:08X}")
print(f"  NONSURFACE_SIZE = 0x{ns_size:08X}")

# The NONSURFACE_BASE should match the GPU's view of VRAM start
# fb_base << 24 = 0xF400000000 but NONSURFACE_BASE = 0xF4000000
# These are 32-bit registers, so the upper bits are handled differently
# Check if there's a HI register
ns_base_hi = rd32(mmio, 0x2C10)
print(f"  NONSURFACE_BASE_HI = 0x{ns_base_hi:08X}")
print(f"  Full nonsurface base = 0x{ns_base_hi:08X}{ns_base:08X}")
print(f"  Expected (fb_base<<24) = 0x{fb_base << 24:016X}")

# Check if NONSURFACE base matches MC FB location
if ns_base == (fb_base << 24) & 0xFFFFFFFF:
    print(f"  BASE matches FB_LOCATION low 32 bits: OK")
else:
    print(f"  *** BASE MISMATCH! NONSURFACE=0x{ns_base:08X} vs FB=0x{(fb_base<<24)&0xFFFFFFFF:08X} ***")

# Check PCI config space for BAR0 address
print("\n--- PCI Config Space ---")
try:
    with open(os.path.join(PCI_DEV, "config"), "rb") as f:
        cfg = f.read(64)
        bar0 = struct.unpack_from('<I', cfg, 0x10)[0]
        bar1 = struct.unpack_from('<I', cfg, 0x14)[0]
        bar2 = struct.unpack_from('<I', cfg, 0x18)[0]
        bar3 = struct.unpack_from('<I', cfg, 0x1C)[0]
        cmd  = struct.unpack_from('<H', cfg, 0x04)[0]
        sts  = struct.unpack_from('<H', cfg, 0x06)[0]
        print(f"  CMD  = 0x{cmd:04X}  (mem={cmd&2}, bus_master={cmd&4})")
        print(f"  STS  = 0x{sts:04X}")
        print(f"  BAR0 = 0x{bar0:08X} (VRAM, {'64-bit' if bar0 & 4 else '32-bit'}, {'prefetch' if bar0 & 8 else 'no-prefetch'})")
        print(f"  BAR1 = 0x{bar1:08X} (BAR0 upper 32 if 64-bit)")
        print(f"  BAR2 = 0x{bar2:08X} (MMIO)")
        print(f"  BAR3 = 0x{bar3:08X} (BAR2 upper 32 if 64-bit)")
except Exception as e:
    print(f"  Failed to read config: {e}")

vram.close()
mmio.close()
print("\n" + "=" * 60)
print("DEEP PROBE COMPLETE")
print("=" * 60)
