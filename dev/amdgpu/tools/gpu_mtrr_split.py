#!/usr/bin/env python3
"""
Definitive MTRR test: REMOVE the WB MTRR that covers bus 2 BAR0,
replace it with smaller MTRRs that only cover actual RAM.

If VRAM works after this → MTRR was the root cause (fix: rearrange at boot)
If VRAM still fails → problem is GPU-side HDP (not caching)

Also reads HDP_HOST_PATH_CNTL from both buses to compare.

Run as: sudo python3 gpu_mtrr_split.py
"""
import mmap, os, struct, time

PCI = "/sys/bus/pci/devices"
BUS1 = "0000:01:00.0"
BUS2 = "0000:02:00.0"

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def wr32(mm, off, v):
    struct.pack_into('<I', mm, off, v & 0xFFFFFFFF)

def vram_test(dev, label):
    try:
        fd = os.open(f"{PCI}/{dev}/resource0", os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, 0x200000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
        ok = 0
        for off in [0x1000, 0x2000, 0x4000, 0x10000, 0x100000]:
            wr32(mm, off, 0xDEADBEEF)
            v1 = rd32(mm, off)
            wr32(mm, off, 0xCAFEBABE)
            v2 = rd32(mm, off)
            passed = v1 == 0xDEADBEEF and v2 == 0xCAFEBABE
            if passed: ok += 1
            print(f"  {label} [0x{off:X}] wr1=0x{v1:08X} wr2=0x{v2:08X} {'OK' if passed else 'FAIL'}")
        mm.close()
        os.close(fd)
        return ok
    except Exception as e:
        print(f"  {label}: {e}")
        return -1

def read_mmio_reg(dev, offset):
    try:
        fd = os.open(f"{PCI}/{dev}/resource2", os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, 0x40000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
        val = rd32(mm, offset)
        mm.close()
        os.close(fd)
        return val
    except:
        return None

def show_mtrr():
    with open('/proc/mtrr', 'r') as f:
        content = f.read().strip()
    print(content)
    return content

# ========================================
print("=" * 60)
print("  DEFINITIVE MTRR + HDP TEST")
print("=" * 60)

# ========================================
print("\n=== HDP register comparison ===")
hdp_regs = [
    ("HDP_HOST_PATH_CNTL",       0x2C00),
    ("HDP_NONSURFACE_BASE",      0x2C04),
    ("HDP_NONSURFACE_INFO",      0x2C08),
    ("HDP_NONSURFACE_SIZE",      0x2C0C),
    ("HDP_ADDR_CONFIG",          0x2F48),
    ("HDP_MISC_CNTL",            0x2F4C),
    ("HDP_MEM_COHERENCY_FLUSH",  0x5480),
    ("BIF_FB_EN",                0x5490),
    ("CONFIG_MEMSIZE",           0x5428),
    ("MC_VM_FB_LOCATION",        0x2024),
]

print(f"  {'Register':<30s} {'Bus1':>12s} {'Bus2':>12s} {'Match':>6s}")
print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*6}")
diffs = []
for name, off in hdp_regs:
    v1 = read_mmio_reg(BUS1, off)
    v2 = read_mmio_reg(BUS2, off)
    if v1 is not None and v2 is not None:
        match = "==" if v1 == v2 else "DIFF"
        print(f"  {name:<30s} 0x{v1:08X}   0x{v2:08X}   {match}")
        if v1 != v2:
            diffs.append((name, off, v1, v2))

if diffs:
    print(f"\n  {len(diffs)} HDP/MC differences — these may explain BAR0 failure")
else:
    print(f"\n  All HDP registers match — MTRR/caching is the problem")

# ========================================
print("\n=== BEFORE: Current MTRR state ===")
show_mtrr()

print("\n=== BEFORE: VRAM test ===")
ok_before = vram_test(BUS2, "Bus2")

# ========================================
print("\n=== REMOVING conflicting MTRR reg02 (256MB WB @ 0xA0000000) ===")
print("  Also removing reg04 (our UC override) if present")

# First remove our UC override (reg04) if it exists
mtrr_text = open('/proc/mtrr').read()
if 'base=0x0b0000000' in mtrr_text:
    # Find which register number
    for line in mtrr_text.strip().split('\n'):
        if 'base=0x0b0000000' in line:
            reg_num = line.split(':')[0].replace('reg', '').strip()
            print(f"  Removing reg{reg_num} (UC override)...")
            with open('/proc/mtrr', 'w') as f:
                f.write(f"disable={reg_num}")

# Now remove reg02 (the problematic 256MB WB)
mtrr_text = open('/proc/mtrr').read()
for line in mtrr_text.strip().split('\n'):
    if 'base=0x0a0000000' in line and 'size=  256MB' in line:
        reg_num = line.split(':')[0].replace('reg', '').strip()
        print(f"  Removing reg{reg_num} (256MB WB @ 0xA0000000)...")
        try:
            with open('/proc/mtrr', 'w') as f:
                f.write(f"disable={reg_num}")
            print("    Removed")
        except Exception as e:
            print(f"    Failed: {e}")

# Add smaller MTRRs that cover RAM but NOT 0xB0000000+
# RAM goes to ~0xAFF00000 (2815MB), reg03 has 1MB UC at 0xAFF00000
# We need WB for: 0xA0000000-0xAFEFFFFF
# Using power-of-2 MTRRs:
#   128MB WB: 0xA0000000-0xA7FFFFFF
#    64MB WB: 0xA8000000-0xABFFFFFF
#    16MB WB: 0xAC000000-0xACFFFFFF
# Remaining 0xAD000000-0xAFEFFFFF (~47MB) will be UC — some RAM perf loss

replacements = [
    ("0xA0000000", "0x08000000", "write-back"),  # 128MB
    ("0xA8000000", "0x04000000", "write-back"),  #  64MB
    ("0xAC000000", "0x01000000", "write-back"),  #  16MB
]

print("  Adding replacement MTRRs (cover RAM but not BAR0)...")
for base, size, mtype in replacements:
    cmd = f"base={base} size={size} type={mtype}"
    try:
        with open('/proc/mtrr', 'w') as f:
            f.write(cmd)
        print(f"    Added: {cmd}")
    except Exception as e:
        print(f"    Failed ({cmd}): {e}")

print("\n=== AFTER: New MTRR state ===")
show_mtrr()

# Give system a moment to settle
time.sleep(1)

# ========================================
# Remove and rescan PCI device to get fresh mappings
print("\n=== Removing + rescanning PCI device for fresh PAT state ===")
for subfn in ["0000:02:00.1", "0000:02:00.0"]:
    remove_path = f"{PCI}/{subfn}/remove"
    if os.path.exists(remove_path):
        with open(remove_path, 'w') as f:
            f.write('1')
time.sleep(1)
with open("/sys/bus/pci/rescan", 'w') as f:
    f.write('1')
time.sleep(2)

if os.path.exists(f"{PCI}/{BUS2}"):
    # Enable
    try:
        with open(f"{PCI}/{BUS2}/enable", 'w') as f:
            f.write('1')
    except:
        pass
    print("  Device back and enabled")
else:
    print("  ERROR: Device not found after rescan!")

# ========================================
print("\n=== AFTER: VRAM test (no WB MTRR covering 0xB0000000) ===")
ok_after = vram_test(BUS2, "Bus2")

print()
vram_test(BUS1, "Bus1-check")

# ========================================
print(f"\n{'='*60}")
print(f"  RESULT: Before={ok_before}/5  After={ok_after}/5")
print(f"{'='*60}")

if ok_after == 5:
    print("  *** MTRR WAS THE ROOT CAUSE ***")
    print("  Fix: rearrange MTRRs at boot to not cover GPU BAR0")
    print("  Add to /etc/default/grub:")
    print("    GRUB_CMDLINE_LINUX_DEFAULT=\"... mem=2688M\"")
    print("  Or add a boot script to split MTRR reg02")
elif ok_after > ok_before:
    print("  *** PARTIAL IMPROVEMENT — MTRR is part of the problem ***")
elif ok_after == 0:
    print("  *** MTRR IS NOT THE PROBLEM ***")
    print("  The GPU's HDP is not configured for CPU BAR0 access.")
    if diffs:
        print("  HDP register differences that need fixing:")
        for name, off, v1, v2 in diffs:
            print(f"    {name} (0x{off:04X}): bus1=0x{v1:08X} bus2=0x{v2:08X}")

# ========================================
# Restore original MTRR (so system doesn't stay slow)
print(f"\n=== Restoring original MTRR reg02 (256MB WB @ 0xA0000000) ===")
# Remove our replacement MTRRs
mtrr_text = open('/proc/mtrr').read()
for line in mtrr_text.strip().split('\n'):
    for base in ['0x0a0000000', '0x0a8000000', '0x0ac000000']:
        if base in line and 'write-back' in line:
            reg_num = line.split(':')[0].replace('reg', '').strip()
            try:
                with open('/proc/mtrr', 'w') as f:
                    f.write(f"disable={reg_num}")
            except:
                pass

# Re-add the original 256MB WB
try:
    with open('/proc/mtrr', 'w') as f:
        f.write("base=0xA0000000 size=0x10000000 type=write-back")
    print("  Restored")
except Exception as e:
    print(f"  Restore failed: {e}")

print("\n=== Final MTRR state ===")
show_mtrr()
