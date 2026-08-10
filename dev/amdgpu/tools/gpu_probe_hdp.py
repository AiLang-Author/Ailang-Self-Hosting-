#!/usr/bin/env python3
"""
GPU probe: Test if programming HDP_NONSURFACE registers (kernel si_mc_program values)
fixes BAR0 VRAM access.  All writes are MMIO (BAR2), no PCI deadlock risk.
"""
import mmap, struct, os, sys

COMPUTE_DEV = "/sys/bus/pci/devices/0000:02:00.0"

def open_bar(dev, resource, size):
    path = os.path.join(dev, resource)
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

# Register offsets
HDP_NONSURFACE_BASE = 0x2C04
HDP_NONSURFACE_INFO = 0x2C08
HDP_NONSURFACE_SIZE = 0x2C0C
HDP_HOST_PATH_CNTL  = 0x2C00
HDP_MISC_CNTL       = 0x2F4C
HDP_FLUSH           = 0x5480
MC_VM_FB_LOCATION   = 0x2024
BIF_FB_EN           = 0x5490
SCRATCH_REG0        = 0x8500

print("=" * 60)
print("HDP NONSURFACE FIX TEST")
print("=" * 60)

mmio = open_bar(COMPUTE_DEV, "resource2", 256 * 1024)

# Read current state
mc_raw = rd32(mmio, MC_VM_FB_LOCATION)
mc_base = mc_raw & 0xFFFF
mc_top = (mc_raw >> 16) & 0xFFFF
vram_start = mc_base << 24  # 40-bit MC address
bif = rd32(mmio, BIF_FB_EN)

print(f"\n  MC_VM_FB_LOCATION = 0x{mc_raw:08X}  base=0x{mc_base:04X} top=0x{mc_top:04X}")
print(f"  vram_start = 0x{vram_start:010X}")
print(f"  BIF_FB_EN = 0x{bif:08X}")

# Current HDP values
cur_base = rd32(mmio, HDP_NONSURFACE_BASE)
cur_info = rd32(mmio, HDP_NONSURFACE_INFO)
cur_size = rd32(mmio, HDP_NONSURFACE_SIZE)
cur_hpc  = rd32(mmio, HDP_HOST_PATH_CNTL)
cur_misc = rd32(mmio, HDP_MISC_CNTL)

print(f"\n  BEFORE:")
print(f"    HDP_NONSURFACE_BASE = 0x{cur_base:08X}  (expect 0x{(vram_start >> 8) & 0xFFFFFFFF:08X})")
print(f"    HDP_NONSURFACE_INFO = 0x{cur_info:08X}  (kernel = 0x40000100)")
print(f"    HDP_NONSURFACE_SIZE = 0x{cur_size:08X}  (kernel = 0x3FFFFFFF)")
print(f"    HDP_HOST_PATH_CNTL  = 0x{cur_hpc:08X}  (RdCacheDis={(cur_hpc>>25)&1})")
print(f"    HDP_MISC_CNTL       = 0x{cur_misc:08X}  (FlushInvCache={cur_misc&1})")

# --- Test 1: BAR0 VRAM before fix ---
print(f"\n── BAR0 VRAM BEFORE fix ──")
vram = open_bar(COMPUTE_DEV, "resource0", 256 * 1024 * 1024)

def test_vram(label):
    offsets = [0x00000000, 0x00001000, 0x04082000, 0x04082004]
    ok = 0
    for off in offsets:
        wr32(mmio, HDP_FLUSH, 1)
        rd32(mmio, HDP_FLUSH)  # barrier
        wr32(vram, off, 0xA5A5A5A5)
        wr32(mmio, HDP_FLUSH, 1)
        rd32(mmio, HDP_FLUSH)  # barrier
        rb = rd32(vram, off)
        wr32(vram, off, 0)  # cleanup
        status = "OK" if rb == 0xA5A5A5A5 else "FAIL"
        if rb != 0xA5A5A5A5:
            print(f"    0x{off:08X}: wrote 0xA5A5A5A5 read 0x{rb:08X}  [{status}]")
        else:
            ok += 1
    if ok == len(offsets):
        print(f"    ALL {ok} OK!")
    else:
        print(f"    {ok}/{len(offsets)} passed")
    return ok == len(offsets)

test_vram("before")

# --- Apply kernel si_mc_program() HDP values ---
print(f"\n── Applying kernel HDP_NONSURFACE values ──")
kernel_base = (vram_start >> 8) & 0xFFFFFFFF
kernel_info = (2 << 7) | (1 << 30)   # 0x40000100
kernel_size = 0x3FFFFFFF

print(f"    HDP_NONSURFACE_BASE = 0x{kernel_base:08X}")
print(f"    HDP_NONSURFACE_INFO = 0x{kernel_info:08X}")
print(f"    HDP_NONSURFACE_SIZE = 0x{kernel_size:08X}")

wr32(mmio, HDP_NONSURFACE_BASE, kernel_base)
wr32(mmio, HDP_NONSURFACE_INFO, kernel_info)
wr32(mmio, HDP_NONSURFACE_SIZE, kernel_size)

# Readback verify
rb_base = rd32(mmio, HDP_NONSURFACE_BASE)
rb_info = rd32(mmio, HDP_NONSURFACE_INFO)
rb_size = rd32(mmio, HDP_NONSURFACE_SIZE)
print(f"    Readback: BASE=0x{rb_base:08X} INFO=0x{rb_info:08X} SIZE=0x{rb_size:08X}")

# Also do the kernel si_gpu_init HDP flush sequence
print(f"\n── Applying kernel si_gpu_init HDP flush ──")
tmp = rd32(mmio, HDP_MISC_CNTL)
wr32(mmio, HDP_MISC_CNTL, tmp | 1)  # FLUSH_INVALIDATE_CACHE
hpc = rd32(mmio, HDP_HOST_PATH_CNTL)
wr32(mmio, HDP_HOST_PATH_CNTL, hpc)  # read-write-back
print(f"    HDP_MISC_CNTL: 0x{tmp:08X} -> 0x{tmp|1:08X}")
print(f"    HDP_HOST_PATH_CNTL: read-write-back 0x{hpc:08X}")

# Flush
wr32(mmio, HDP_FLUSH, 1)
rd32(mmio, HDP_FLUSH)

# --- Test 2: BAR0 VRAM after fix ---
print(f"\n── BAR0 VRAM AFTER fix ──")
worked = test_vram("after")

# --- Bulk test if single DWORDs work ---
if worked:
    print(f"\n── Bulk 64-DWORD test @ 0x04082000 ──")
    base = 0x04082000
    for i in range(64):
        wr32(vram, base + i*4, i + 42)
    wr32(mmio, HDP_FLUSH, 1)
    rd32(mmio, HDP_FLUSH)
    errs = 0
    for i in range(64):
        val = rd32(vram, base + i*4)
        if val != i + 42:
            errs += 1
            if errs <= 5:
                print(f"    [{i:2d}] expected {i+42}, got 0x{val:08X}")
    if errs == 0:
        print(f"    ALL 64 OK!")
    else:
        print(f"    {errs}/64 FAILED")
    # cleanup
    for i in range(64):
        wr32(vram, base + i*4, 0)

# --- Restore original values if fix didn't help ---
if not worked:
    print(f"\n── Restoring original BIOS values ──")
    wr32(mmio, HDP_NONSURFACE_BASE, cur_base)
    wr32(mmio, HDP_NONSURFACE_INFO, cur_info)
    wr32(mmio, HDP_NONSURFACE_SIZE, cur_size)
    print(f"    Restored.")

vram.close()
mmio.close()

print(f"\n{'='*60}")
if worked:
    print("HDP NONSURFACE FIX: SUCCESS — BAR0 VRAM IS WORKING")
else:
    print("HDP NONSURFACE FIX: NO CHANGE — BAR0 still broken")
print(f"{'='*60}")
