#!/usr/bin/env python3
"""
GPU probe 4: Enable PCI CMD bits on compute GPU, then re-probe.
  02:00.0 CMD=0x0000 — MEM/BusMaster disabled. Card ignores BAR accesses.
  Fix: write CMD=0x0006 (MEM + BusMaster).  NOT a PCI reset/rescan.
"""
import mmap, struct, os, sys

COMPUTE_DEV = "/sys/bus/pci/devices/0000:02:00.0"

def read_pci_config(dev, n=256):
    with open(os.path.join(dev, "config"), "rb") as f:
        return f.read(n)

def write_pci_config_word(dev, offset, val):
    """Write a 16-bit value to PCI config space."""
    with open(os.path.join(dev, "config"), "r+b") as f:
        f.seek(offset)
        f.write(struct.pack('<H', val & 0xFFFF))

def u16(buf, off):
    return struct.unpack_from('<H', buf, off)[0]

def u32(buf, off):
    return struct.unpack_from('<I', buf, off)[0]

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

# ──────────────────────────────────────────────────────────────────────
print("=" * 60)
print("GPU PROBE 4 — Enable compute GPU PCI CMD + re-probe")
print("  NO PCI RESET.  NO RESCAN.  Just CMD register bits.")
print("=" * 60)

# Read current CMD
cfg = read_pci_config(COMPUTE_DEV)
cmd_before = u16(cfg, 0x04)
sts_before = u16(cfg, 0x06)
print(f"\n  CMD before = 0x{cmd_before:04X}  "
      f"(IO={cmd_before&1} MEM={(cmd_before>>1)&1} BM={(cmd_before>>2)&1})")
print(f"  STS before = 0x{sts_before:04X}")

# Enable MEM (bit 1) + BusMaster (bit 2)
new_cmd = cmd_before | 0x0006
print(f"\n  Writing CMD = 0x{new_cmd:04X}  (enabling MEM + BusMaster)")
write_pci_config_word(COMPUTE_DEV, 0x04, new_cmd)

# Read back
cfg2 = read_pci_config(COMPUTE_DEV)
cmd_after = u16(cfg2, 0x04)
sts_after = u16(cfg2, 0x06)
print(f"  CMD after  = 0x{cmd_after:04X}  "
      f"(IO={cmd_after&1} MEM={(cmd_after>>1)&1} BM={(cmd_after>>2)&1})")
print(f"  STS after  = 0x{sts_after:04X}")

if not (cmd_after & 0x06):
    print("\n  *** CMD bits did not stick — card may be in D3 or broken ***")
    sys.exit(1)

# ── Now probe MMIO ────────────────────────────────────────────────────
print(f"\n── MMIO Register Probe ──")
mmio = open_bar(COMPUTE_DEV, "resource2", 256 * 1024)

regs = [
    ("GRBM_STATUS",              0x8010),
    ("SRBM_STATUS",              0x0E50),
    ("BIF_FB_EN",                0x5490),
    ("MC_VM_FB_LOCATION",        0x2024),
    ("MC_VM_SYS_APT_LOW",       0x2034),
    ("MC_VM_SYS_APT_HIGH",      0x2038),
    ("MC_SHARED_BLACKOUT_CNTL",  0x20AC),
    ("MC_SEQ_MISC0",             0x2A00),
    ("MC_ARB_RAMCFG",            0x2760),
    ("HDP_HOST_PATH_CNTL",      0x2C00),
    ("HDP_MISC_CNTL",           0x2F4C),
    ("HDP_NONSURFACE_BASE",     0x2C04),
    ("HDP_NONSURFACE_INFO",     0x2C08),
    ("HDP_NONSURFACE_SIZE",     0x2C0C),
    ("HDP_ADDR_CONFIG",          0x2F48),
    ("CG_SPLL_FUNC_CNTL",      0x0600),
    ("SPLL_STATUS",              0x060C),
    ("CP_ME_CNTL",               0x86D8),
    ("SCRATCH_REG0",             0x8500),
]

all_ff = True
for name, off in regs:
    val = rd32(mmio, off)
    extra = ""
    if val != 0xFFFFFFFF:
        all_ff = False
    if name == "BIF_FB_EN":
        extra = f"  RD={(val)&1} WR={(val>>1)&1}" if val != 0xFFFFFFFF else ""
    elif name == "MC_VM_FB_LOCATION" and val != 0xFFFFFFFF:
        fb_b = val & 0xFFFF
        fb_t = (val >> 16) & 0xFFFF
        extra = f"  base=0x{fb_b:04X} top=0x{fb_t:04X} -> {((fb_t-fb_b+1)<<24)//(1024*1024)}MB"
    elif name == "SPLL_STATUS" and val != 0xFFFFFFFF:
        extra = f"  locked={'Y' if val&1 else 'N'}"
    elif name == "HDP_HOST_PATH_CNTL" and val != 0xFFFFFFFF:
        extra = f"  RdCacheDis={(val>>25)&1}"
    elif name == "HDP_MISC_CNTL" and val != 0xFFFFFFFF:
        extra = f"  FlushInvCache={val&1}"
    print(f"  {name:30s} [0x{off:04X}] = 0x{val:08X}{extra}")

if all_ff:
    print("\n  *** ALL REGISTERS STILL 0xFFFFFFFF — card not responding ***")
    mmio.close()
    sys.exit(1)

print(f"\n  Card is RESPONDING to MMIO reads!")

# ── BAR0 VRAM test ────────────────────────────────────────────────────
print(f"\n── BAR0 VRAM Test ──")

bif = rd32(mmio, 0x5490)
if bif != 0xFFFFFFFF and not (bif & 1):
    print(f"  BIF_FB_EN = 0x{bif:08X} — FB read disabled, skipping VRAM test")
else:
    vram = open_bar(COMPUTE_DEV, "resource0", 256 * 1024 * 1024)
    HDP_FLUSH = 0x5480

    TEST_PAT = 0xA5A5A5A5
    offsets = [
        (0x00000000, "VRAM base"),
        (0x00001000, "4KB"),
        (0x00100000, "1MB"),
        (0x04000000, "64MB (ring region)"),
        (0x04082000, "DATA region (src)"),
        (0x04082100, "DATA region (dst)"),
    ]

    print(f"  Write/Read pattern 0x{TEST_PAT:08X}:")
    ok_count = 0
    for off, desc in offsets:
        wr32(mmio, HDP_FLUSH, 1)
        orig = rd32(vram, off)
        wr32(vram, off, TEST_PAT)
        wr32(mmio, HDP_FLUSH, 1)
        rb = rd32(vram, off)
        wr32(vram, off, orig)

        ok = rb == TEST_PAT
        if ok:
            ok_count += 1
        print(f"    0x{off:08X} ({desc:20s}): "
              f"orig=0x{orig:08X}  rb=0x{rb:08X}  [{'OK' if ok else 'FAIL'}]")

    # Bulk test
    print(f"\n  Bulk 64-DWORD @ 0x04082000:")
    base = 0x04082000
    for i in range(64):
        wr32(vram, base + i*4, i + 42)
    wr32(mmio, HDP_FLUSH, 1)
    errs = 0
    for i in range(64):
        wr32(mmio, HDP_FLUSH, 1)
        val = rd32(vram, base + i*4)
        if val != i + 42:
            errs += 1
            if errs <= 5:
                print(f"    [{i:2d}] expected {i+42}, got 0x{val:08X}")
    if errs == 0:
        print(f"    ALL 64 OK")
    else:
        print(f"    {errs}/64 FAILED")
    for i in range(64):
        wr32(vram, base + i*4, 0)

    vram.close()

# ── SCRATCH register roundtrip ────────────────────────────────────────
print(f"\n── SCRATCH_REG0 Roundtrip ──")
wr32(mmio, 0x8500, 0xCAFEBABE)
rb = rd32(mmio, 0x8500)
print(f"  Wrote 0xCAFEBABE, read 0x{rb:08X}  [{'OK' if rb == 0xCAFEBABE else 'FAIL'}]")
wr32(mmio, 0x8500, 0)

mmio.close()

print(f"\n{'='*60}")
print("PROBE 4 COMPLETE")
print(f"{'='*60}")
