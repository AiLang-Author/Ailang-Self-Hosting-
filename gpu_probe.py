#!/usr/bin/env python3
"""
Raw GPU probe — bypass all AILang driver code.
Directly mmap BAR0 (VRAM) and BAR2 (MMIO) via sysfs,
read hardware registers, test VRAM read/write at multiple offsets.
"""
import mmap, struct, os, sys, time

PCI_DEV = "/sys/bus/pci/devices/0000:02:00.0"

# SI register offsets (byte addresses)
GRBM_STATUS              = 0x8010
SRBM_STATUS              = 0x0E50
CP_RB0_RPTR              = 0x8600
CP_RB0_WPTR              = 0x8610
MC_VM_FB_LOCATION         = 0x2024
MC_VM_SYSTEM_APERTURE_LOW = 0x2034
MC_VM_SYSTEM_APERTURE_HIGH= 0x2038
MC_VM_SYSTEM_APERTURE_DEF = 0x203C
VM_CONTEXT0_CNTL         = 0x1410
MC_VM_MX_L1_TLB_CNTL    = 0x2064
HDP_HOST_PATH_CNTL       = 0x2C00
HDP_MISC_CNTL            = 0x2F4C
HDP_MEM_COHERENCY_FLUSH  = 0x5480
HDP_NONSURFACE_BASE      = 0x2C04
HDP_NONSURFACE_INFO      = 0x2C08
HDP_NONSURFACE_SIZE      = 0x2C0C
HDP_ADDR_CONFIG          = 0x2F48
SCRATCH_REG0             = 0x8500
SCRATCH_UMSK             = 0x8540
CG_SPLL_FUNC_CNTL       = 0x0600
CG_SPLL_FUNC_CNTL_2     = 0x0604
CG_SPLL_FUNC_CNTL_3     = 0x0608
SPLL_STATUS              = 0x060C
BIF_FB_EN                = 0x5490
MC_SEQ_MISC0             = 0x2A00
MC_ARB_RAMCFG            = 0x2760

def open_bar(resource, size=None):
    """mmap a PCI BAR resource file."""
    path = os.path.join(PCI_DEV, resource)
    fd = os.open(path, os.O_RDWR | os.O_SYNC)
    if size is None:
        size = os.fstat(fd).st_size
    mm = mmap.mmap(fd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
    os.close(fd)
    return mm

def mmio_rd32(mm, offset):
    mm.seek(offset)
    return struct.unpack('<I', mm.read(4))[0]

def mmio_wr32(mm, offset, val):
    mm.seek(offset)
    mm.write(struct.pack('<I', val & 0xFFFFFFFF))

def vram_rd32(mm, offset):
    mm.seek(offset)
    return struct.unpack('<I', mm.read(4))[0]

def vram_wr32(mm, offset, val):
    mm.seek(offset)
    mm.write(struct.pack('<I', val & 0xFFFFFFFF))

def hdp_flush(mmio):
    """Flush HDP write cache (safe MMIO write)."""
    mmio_wr32(mmio, HDP_MEM_COHERENCY_FLUSH, 1)

print("=" * 60)
print("GPU RAW PROBE — Python direct BAR access")
print("=" * 60)

# Open BARs
print("\n--- Opening BARs ---")
mmio = open_bar("resource2", 256 * 1024)
print(f"  BAR2 (MMIO): mapped 256KB")

# Try both resource0 (uncached) and resource0_wc (write-combining)
# The AILang driver uses resource0 with O_RDWR|O_SYNC
vram_uc = open_bar("resource0", 256 * 1024 * 1024)
print(f"  BAR0 (VRAM uncached/resource0): mapped 256MB")

try:
    vram_wc = open_bar("resource0_wc", 256 * 1024 * 1024)
    print(f"  BAR0 (VRAM WC/resource0_wc): mapped 256MB")
    has_wc = True
except:
    print(f"  BAR0 (VRAM WC/resource0_wc): FAILED to map")
    has_wc = False

# --- Dump key registers ---
print("\n--- Key MMIO Registers ---")
regs = [
    ("GRBM_STATUS",              GRBM_STATUS),
    ("SRBM_STATUS",              SRBM_STATUS),
    ("MC_VM_FB_LOCATION",        MC_VM_FB_LOCATION),
    ("MC_VM_SYS_APERTURE_LOW",   MC_VM_SYSTEM_APERTURE_LOW),
    ("MC_VM_SYS_APERTURE_HIGH",  MC_VM_SYSTEM_APERTURE_HIGH),
    ("MC_VM_SYS_APERTURE_DEF",   MC_VM_SYSTEM_APERTURE_DEF),
    ("VM_CONTEXT0_CNTL",         VM_CONTEXT0_CNTL),
    ("MC_VM_MX_L1_TLB_CNTL",    MC_VM_MX_L1_TLB_CNTL),
    ("HDP_HOST_PATH_CNTL",       HDP_HOST_PATH_CNTL),
    ("HDP_MISC_CNTL",            HDP_MISC_CNTL),
    ("HDP_MEM_COHERENCY_FLUSH",  HDP_MEM_COHERENCY_FLUSH),
    ("HDP_NONSURFACE_BASE",      HDP_NONSURFACE_BASE),
    ("HDP_NONSURFACE_INFO",      HDP_NONSURFACE_INFO),
    ("HDP_NONSURFACE_SIZE",      HDP_NONSURFACE_SIZE),
    ("HDP_ADDR_CONFIG",          HDP_ADDR_CONFIG),
    ("BIF_FB_EN",                BIF_FB_EN),
    ("SCRATCH_REG0",             SCRATCH_REG0),
    ("SCRATCH_UMSK",             SCRATCH_UMSK),
    ("MC_SEQ_MISC0",             MC_SEQ_MISC0),
    ("MC_ARB_RAMCFG",            MC_ARB_RAMCFG),
    ("CG_SPLL_FUNC_CNTL",       CG_SPLL_FUNC_CNTL),
    ("SPLL_STATUS",              SPLL_STATUS),
]
for name, off in regs:
    val = mmio_rd32(mmio, off)
    print(f"  {name:30s} [0x{off:04X}] = 0x{val:08X}")

# --- VRAM probe: test read/write at multiple offsets ---
print("\n--- VRAM Read/Write Probe (resource0 = UC) ---")
test_offsets = [
    0x0,          # very start of VRAM
    0x1000,       # 4KB in
    0x10000,      # 64KB in
    0x100000,     # 1MB in
    0x400000,     # 4MB in
    0x1000000,    # 16MB in
    0x4000000,    # 64MB in (ring buffer region)
    0x4040000,    # shader region
    0x4080000,    # buf desc region
    0x4082000,    # DATA region (where test writes src/dst)
    0x4082100,    # DATA+256 (dst area)
]

test_val = 0xDEADBEEF
for off in test_offsets:
    # Read original
    orig = vram_rd32(vram_uc, off)
    # Write test pattern
    vram_wr32(vram_uc, off, test_val)
    # Read back immediately
    rb1 = vram_rd32(vram_uc, off)
    # HDP flush then read
    hdp_flush(mmio)
    rb2 = vram_rd32(vram_uc, off)
    # Restore
    vram_wr32(vram_uc, off, orig)

    ok1 = "OK" if rb1 == test_val else "FAIL"
    ok2 = "OK" if rb2 == test_val else "FAIL"
    print(f"  0x{off:08X}: orig=0x{orig:08X}  wr=0x{test_val:08X}  "
          f"rd_imm=0x{rb1:08X} [{ok1}]  rd_hdp=0x{rb2:08X} [{ok2}]")

# --- Same test with resource0_wc ---
if has_wc:
    print("\n--- VRAM Read/Write Probe (resource0_wc = WC) ---")
    for off in test_offsets:
        orig = vram_rd32(vram_wc, off)
        vram_wr32(vram_wc, off, test_val)
        # WC needs explicit flush
        rb1 = vram_rd32(vram_wc, off)
        hdp_flush(mmio)
        rb2 = vram_rd32(vram_wc, off)
        vram_wr32(vram_wc, off, orig)

        ok1 = "OK" if rb1 == test_val else "FAIL"
        ok2 = "OK" if rb2 == test_val else "FAIL"
        print(f"  0x{off:08X}: orig=0x{orig:08X}  wr=0x{test_val:08X}  "
              f"rd_imm=0x{rb1:08X} [{ok1}]  rd_hdp=0x{rb2:08X} [{ok2}]")

# --- MMIO scratch register roundtrip ---
print("\n--- MMIO Scratch Register Roundtrip ---")
mmio_wr32(mmio, SCRATCH_REG0, 0xCAFEBABE)
rb = mmio_rd32(mmio, SCRATCH_REG0)
print(f"  SCRATCH_REG0: wrote 0xCAFEBABE, read 0x{rb:08X} {'OK' if rb == 0xCAFEBABE else 'FAIL'}")
mmio_wr32(mmio, SCRATCH_REG0, 0)

# --- Check what the AILang driver opens BAR0 as ---
# The AILang driver uses O_RDWR | O_SYNC on resource0
# O_SYNC on PCI resources forces uncacheable mapping (UC)
# resource0_wc gives write-combining (WC)
print("\n--- BAR0 mapping analysis ---")
print(f"  resource0    exists: {os.path.exists(os.path.join(PCI_DEV, 'resource0'))}")
print(f"  resource0_wc exists: {os.path.exists(os.path.join(PCI_DEV, 'resource0_wc'))}")
print(f"  AILang uses: resource0 with O_RDWR|O_SYNC (= UC mapping)")
print(f"  Kernel GPU drivers typically use resource0_wc for VRAM (WC for writes, UC for reads)")

# --- BIF_FB_EN check ---
bif = mmio_rd32(mmio, BIF_FB_EN)
print(f"\n--- BIF_FB_EN = 0x{bif:08X} ---")
if bif & 1:
    print("  FB access ENABLED (bit 0 set)")
else:
    print("  FB access DISABLED (bit 0 clear) — THIS WOULD BLOCK ALL VRAM ACCESS!")

# --- Quick bulk test: write 64 DWORDs, read them all back ---
print("\n--- Bulk VRAM test: 64 DWORDs at 0x4082000 (UC) ---")
base = 0x4082000
# Write
for i in range(64):
    vram_wr32(vram_uc, base + i*4, i + 42)
hdp_flush(mmio)
# Read
errors = 0
for i in range(64):
    val = vram_rd32(vram_uc, base + i*4)
    if val != i + 42:
        errors += 1
        if i < 4 or i > 61:
            print(f"  [{i}] expected {i+42}, got 0x{val:08X}")
if errors == 0:
    print(f"  ALL 64 OK")
else:
    print(f"  {errors}/64 FAILED")

# Cleanup
for i in range(64):
    vram_wr32(vram_uc, base + i*4, 0)

print("\n" + "=" * 60)
print("PROBE COMPLETE")
print("=" * 60)

mmio.close()
vram_uc.close()
if has_wc:
    vram_wc.close()
