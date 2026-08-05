#!/usr/bin/env python3
"""
Fix MTRR overlap on bus 2 BAR0 (0xB0000000-0xBFFFFFFF).

The BIOS set MTRR reg02 to cover 0xA0000000-0xBFFFFFFF as write-back
(for system RAM), but bus 2's VRAM BAR0 sits at 0xB0000000-0xBFFFFFFF.
CPU caches VRAM writes instead of sending them over PCIe.

Fix: Add a UC MTRR to override WB for the BAR0 range.

Run as: sudo python3 gpu_mtrr_fix.py
"""
import mmap, os, struct, subprocess

PCI = "/sys/bus/pci/devices"

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def wr32(mm, off, v):
    struct.pack_into('<I', mm, off, v & 0xFFFFFFFF)

def vram_test(dev, label):
    """Quick VRAM write/read test."""
    try:
        fd = os.open(f"{PCI}/{dev}/resource0", os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, 0x200000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
        ok = 0
        total = 0
        for off in [0x1000, 0x2000, 0x4000, 0x10000, 0x100000]:
            wr32(mm, off, 0xDEADBEEF)
            v1 = rd32(mm, off)
            wr32(mm, off, 0xCAFEBABE)
            v2 = rd32(mm, off)
            passed = v1 == 0xDEADBEEF and v2 == 0xCAFEBABE
            total += 1
            if passed:
                ok += 1
            print(f"  {label} [0x{off:X}] wr1=0x{v1:08X} wr2=0x{v2:08X} {'OK' if passed else 'FAIL'}")
        mm.close()
        os.close(fd)
        return ok, total
    except Exception as e:
        print(f"  {label}: {e}")
        return 0, 0

print("=== CURRENT MTRR STATE ===")
with open('/proc/mtrr', 'r') as f:
    print(f.read().strip())

print("\n=== BEFORE FIX: VRAM test ===")
vram_test("0000:02:00.0", "Bus2")

print("\n=== APPLYING MTRR FIX ===")
# Add UC MTRR for 0xB0000000-0xBFFFFFFF (256MB)
# This overrides the WB from reg02
mtrr_cmd = "base=0xB0000000 size=0x10000000 type=uncachable"
print(f"  Writing to /proc/mtrr: {mtrr_cmd}")
try:
    with open('/proc/mtrr', 'w') as f:
        f.write(mtrr_cmd)
    print("  MTRR written successfully")
except Exception as e:
    print(f"  MTRR write failed: {e}")
    print("  Trying alternative: echo to /proc/mtrr via shell...")
    r = subprocess.run(
        ['sh', '-c', f'echo "{mtrr_cmd}" > /proc/mtrr'],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print("  MTRR written via shell")
    else:
        print(f"  Shell write failed: {r.stderr.strip()}")

print("\n=== NEW MTRR STATE ===")
with open('/proc/mtrr', 'r') as f:
    print(f.read().strip())

print("\n=== AFTER FIX: VRAM test ===")
ok, total = vram_test("0000:02:00.0", "Bus2")

print(f"\n=== RESULT: {ok}/{total} {'ALL PASS — MTRR WAS THE BUG' if ok == total else 'STILL FAILING'} ===")

if ok == total:
    print("""
To make this permanent, add to your kernel command line:
  mtrr_cleanup=1
Or add a boot script that writes:
  echo "base=0xB0000000 size=0x10000000 type=uncachable" > /proc/mtrr
""")
