#!/usr/bin/env python3
"""
Fix the PAT/MTRR conflict for bus 2 BAR0.

Root cause: Kernel maps PCI resource0 as UC- (UC minus) via PAT.
On AMD Piledriver: MTRR WB + PAT UC- = WC (write-combining).
CPU writes go to WC buffer, never reach GPU VRAM.

Adding a UC MTRR didn't help because the kernel's PAT reservation
system cached the memory type at boot. We need to force re-evaluation.

Strategy:
1. Check kernel PAT memtype list (shows cached reservations)
2. Add UC MTRR for 0xB0000000
3. Remove PCI device from kernel (clears PAT reservation)
4. Rescan PCI bus (re-evaluates with UC MTRR in place)
5. Test VRAM

Run as: sudo python3 gpu_pat_fix.py
"""
import mmap, os, struct, time, subprocess, glob

PCI = "/sys/bus/pci/devices"
BUS2 = "0000:02:00.0"
BUS1 = "0000:01:00.0"

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

def check_smaps_cache_type(dev):
    """Mmap a PCI resource and check what cache flags the kernel assigned."""
    try:
        fd = os.open(f"{PCI}/{dev}/resource0", os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
        # Find our mapping in smaps
        pid = os.getpid()
        with open(f'/proc/{pid}/smaps', 'r') as f:
            lines = f.readlines()
        found = False
        for line in lines:
            if 'resource0' in line and dev.split(':')[-1] in line:
                found = True
            if found:
                print(f"    {line.rstrip()}")
                if 'VmFlags' in line:
                    break
        mm.close()
        os.close(fd)
    except Exception as e:
        print(f"    smaps check: {e}")

# ========================================
print("=== STEP 1: Kernel PAT memtype list ===")
pat_file = "/sys/kernel/debug/x86/pat_memtype_list"
try:
    with open(pat_file, 'r') as f:
        lines = f.readlines()
    # Show entries for our GPU BAR ranges
    print(f"  Total entries: {len(lines)}")
    for line in lines:
        lo = line.lower()
        if any(x in lo for x in ['b0000', 'c0000', 'fea0', 'fe90']):
            print(f"  {line.rstrip()}")
    if not any('b0000' in l.lower() for l in lines):
        print("  (no entries found for 0xB0000000 range)")
except FileNotFoundError:
    print("  debugfs not mounted or pat_memtype_list not available")
    print("  Trying to mount debugfs...")
    subprocess.run(['mount', '-t', 'debugfs', 'none', '/sys/kernel/debug'],
                   capture_output=True)
    try:
        with open(pat_file, 'r') as f:
            lines = f.readlines()
        for line in lines:
            if any(x in line.lower() for x in ['b0000', 'c0000']):
                print(f"  {line.rstrip()}")
    except:
        print("  Still can't read PAT memtype list")
except Exception as e:
    print(f"  {e}")

# ========================================
print("\n=== STEP 2: Current MTRR state ===")
with open('/proc/mtrr', 'r') as f:
    mtrr = f.read()
    print(mtrr.strip())

# Ensure UC MTRR is in place
if 'base=0x0b0000000' not in mtrr:
    print("  Adding UC MTRR for 0xB0000000...")
    with open('/proc/mtrr', 'w') as f:
        f.write("base=0xB0000000 size=0x10000000 type=uncachable")
    with open('/proc/mtrr', 'r') as f:
        print(f.read().strip())

# ========================================
print("\n=== STEP 3: BEFORE — VRAM test + smaps ===")
print("  Smaps for bus 2 mapping:")
check_smaps_cache_type(BUS2)
print()
ok_before = vram_test(BUS2, "Bus2-before")

# ========================================
print(f"\n=== STEP 4: Remove PCI device 02:00.0 (and 02:00.1) ===")
# Remove audio function first (depends on GPU)
for subfn in ["0000:02:00.1", "0000:02:00.0"]:
    remove_path = f"{PCI}/{subfn}/remove"
    if os.path.exists(remove_path):
        print(f"  Removing {subfn}...")
        try:
            with open(remove_path, 'w') as f:
                f.write('1')
            print(f"    Removed")
        except Exception as e:
            print(f"    Failed: {e}")
    else:
        print(f"  {subfn} already removed or doesn't exist")

time.sleep(1)

# Verify removal
if os.path.exists(f"{PCI}/{BUS2}"):
    print("  WARNING: Device still present after remove!")
else:
    print("  Device successfully removed from kernel")

# ========================================
print(f"\n=== STEP 5: Rescan PCI bus ===")
rescan_path = "/sys/bus/pci/rescan"
try:
    with open(rescan_path, 'w') as f:
        f.write('1')
    print("  Rescan triggered")
except Exception as e:
    print(f"  Rescan failed: {e}")

time.sleep(2)

# Verify device is back
if os.path.exists(f"{PCI}/{BUS2}"):
    print(f"  Device {BUS2} is back")
    # Check command register
    with open(f"{PCI}/{BUS2}/config", 'rb') as f:
        d = f.read(8)
    cmd = struct.unpack_from('<H', d, 4)[0]
    print(f"  PCI command: 0x{cmd:04X}")

    # Enable if needed
    with open(f"{PCI}/{BUS2}/enable", 'r') as f:
        en = f.read().strip()
    print(f"  Enable: {en}")
    if en == '0':
        with open(f"{PCI}/{BUS2}/enable", 'w') as f:
            f.write('1')
        print("  Enabled device")
else:
    print(f"  ERROR: Device {BUS2} not found after rescan!")
    print("  Trying bridge rescan...")
    bridge_rescan = f"{PCI}/0000:00:03.0/rescan"
    if os.path.exists(bridge_rescan):
        with open(bridge_rescan, 'w') as f:
            f.write('1')
        time.sleep(2)

# ========================================
print(f"\n=== STEP 6: Check PAT memtype list AFTER rescan ===")
try:
    with open(pat_file, 'r') as f:
        lines = f.readlines()
    for line in lines:
        if any(x in line.lower() for x in ['b0000', 'c0000']):
            print(f"  {line.rstrip()}")
except:
    print("  (cannot read)")

# ========================================
print(f"\n=== STEP 7: AFTER — VRAM test + smaps ===")
if os.path.exists(f"{PCI}/{BUS2}/resource0"):
    print("  Smaps for bus 2 mapping:")
    check_smaps_cache_type(BUS2)
    print()
    ok_after = vram_test(BUS2, "Bus2-after")

    # Also verify bus 1 still works
    print()
    vram_test(BUS1, "Bus1-check")

    print(f"\n=== RESULT ===")
    print(f"  Before PCI rescan: {ok_before}/5")
    print(f"  After PCI rescan:  {ok_after}/5")
    if ok_after == 5:
        print("  *** FIXED! The PAT reservation was stale. ***")
        print("  To make permanent: add UC MTRR at boot before driver runs.")
    elif ok_after > ok_before:
        print("  *** PARTIAL IMPROVEMENT ***")
    else:
        print("  *** No change — problem is deeper than PAT reservation ***")
else:
    print("  ERROR: resource0 not available after rescan")
