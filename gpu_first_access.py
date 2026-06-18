#!/usr/bin/env python3
"""
Investigate the first-access bug. On bus 2, the SECOND write to any
address works but the FIRST returns 0xFFFFFFFF.

Tests:
1. Check MTRR default type (MSR 0x2FF)
2. Read-first pattern (read, then write, then read)
3. Write-twice pattern (write garbage, write real value, read)
4. Sequential writes to same address (does it "warm up"?)
5. Large sequential write then read (simulate ring buffer fill)
6. Write via CPU, read via GPU (MMIO scratch reg test)

Run as: sudo python3 gpu_first_access.py
"""
import mmap, os, struct, time

PCI = "/sys/bus/pci/devices"
BUS2 = "0000:02:00.0"
BUS1 = "0000:01:00.0"

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def wr32(mm, off, v):
    struct.pack_into('<I', mm, off, v & 0xFFFFFFFF)

# ========================================
print("=== MTRR Default Type (MSR 0x2FF) ===")
try:
    fd = os.open('/dev/cpu/0/msr', os.O_RDONLY)
    os.lseek(fd, 0x2FF, os.SEEK_SET)
    data = os.read(fd, 8)
    msr = struct.unpack('<Q', data)[0]
    os.close(fd)
    def_type = msr & 0xFF
    mtrr_e = bool(msr & (1 << 11))
    fix_e = bool(msr & (1 << 10))
    types = {0:'UC', 1:'WC', 4:'WT', 5:'WP', 6:'WB', 7:'UC-'}
    print(f"  IA32_MTRR_DEF_TYPE = 0x{msr:016X}")
    print(f"  Default type: {types.get(def_type, '?')} ({def_type})")
    print(f"  MTRR enabled: {mtrr_e}")
    print(f"  Fixed MTRR enabled: {fix_e}")
    if def_type == 6:
        print("  *** DEFAULT IS WB! This means ALL addresses without explicit")
        print("      MTRR coverage get WB. Combined with PAT UC- = WC on AMD. ***")
except Exception as e:
    print(f"  {e}")

# ========================================
print("\n=== Test: First-access pattern analysis ===")
# Map a FRESH region we haven't touched before
fd2 = os.open(f"{PCI}/{BUS2}/resource0", os.O_RDWR | os.O_SYNC)
mm2 = mmap.mmap(fd2, 16*1024*1024, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

print("\n  --- Test A: Read-first (read, write, read) ---")
for off in [0x500000, 0x501000, 0x502000]:
    v_before = rd32(mm2, off)       # first access: read
    wr32(mm2, off, 0xAABBCCDD)      # second access: write
    v_after = rd32(mm2, off)         # third access: read
    print(f"  [0x{off:X}] rd1=0x{v_before:08X} wr(AABBCCDD) rd2=0x{v_after:08X} {'OK' if v_after==0xAABBCCDD else 'FAIL'}")

print("\n  --- Test B: Write-twice (write garbage, write value, read) ---")
for off in [0x600000, 0x601000, 0x602000]:
    wr32(mm2, off, 0x00000000)      # first access: dummy write
    wr32(mm2, off, 0x11223344)      # second access: real write
    v = rd32(mm2, off)               # third access: read
    print(f"  [0x{off:X}] wr(0) wr(11223344) rd=0x{v:08X} {'OK' if v==0x11223344 else 'FAIL'}")

print("\n  --- Test C: Multiple writes to warm up, then test ---")
for off in [0x700000, 0x701000]:
    # Write 10 times to "warm up"
    for i in range(10):
        wr32(mm2, off, i)
    # Now test
    wr32(mm2, off, 0xDEADBEEF)
    v = rd32(mm2, off)
    print(f"  [0x{off:X}] 10x warmup, wr(DEADBEEF) rd=0x{v:08X} {'OK' if v==0xDEADBEEF else 'FAIL'}")

print("\n  --- Test D: Same address, repeated write/read cycles ---")
off = 0x800000
results = []
for i in range(8):
    val = 0xBEEF0000 + i
    wr32(mm2, off, val)
    got = rd32(mm2, off)
    results.append((val, got, got == val))
    print(f"  [0x{off:X}] cycle {i}: wr(0x{val:08X}) rd=0x{got:08X} {'OK' if got==val else 'FAIL'}")

print("\n  --- Test E: Write block then read block (like ring buffer) ---")
base = 0x900000
count = 64
# Write all
for i in range(count):
    wr32(mm2, base + i*4, 0xFACE0000 + i)
# Read all
errs = 0
for i in range(count):
    got = rd32(mm2, base + i*4)
    exp = 0xFACE0000 + i
    if got != exp:
        if errs < 3:
            print(f"  [{i}] exp=0x{exp:08X} got=0x{got:08X}")
        errs += 1
print(f"  Write-then-read block: {count-errs}/{count} correct")

# Now write ALL again (second pass) and read ALL
for i in range(count):
    wr32(mm2, base + i*4, 0xCAFE0000 + i)
errs2 = 0
for i in range(count):
    got = rd32(mm2, base + i*4)
    exp = 0xCAFE0000 + i
    if got != exp:
        if errs2 < 3:
            print(f"  [{i}] exp=0x{exp:08X} got=0x{got:08X}")
        errs2 += 1
print(f"  Second pass block:     {count-errs2}/{count} correct")

print("\n  --- Test F: Different offsets on same page ---")
page_base = 0xA00000
wr32(mm2, page_base, 0x11111111)        # first touch on this page
v0 = rd32(mm2, page_base)
wr32(mm2, page_base + 4, 0x22222222)    # second dword, same page
v1 = rd32(mm2, page_base + 4)
wr32(mm2, page_base + 8, 0x33333333)    # third dword, same page
v2 = rd32(mm2, page_base + 8)
print(f"  [+0] wr(11111111) rd=0x{v0:08X} {'OK' if v0==0x11111111 else 'FAIL'}")
print(f"  [+4] wr(22222222) rd=0x{v1:08X} {'OK' if v1==0x22222222 else 'FAIL'}")
print(f"  [+8] wr(33333333) rd=0x{v2:08X} {'OK' if v2==0x33333333 else 'FAIL'}")

mm2.close()
os.close(fd2)

# ========================================
# Compare with bus 1
print("\n=== Bus 1 reference (same tests) ===")
fd1 = os.open(f"{PCI}/{BUS1}/resource0", os.O_RDWR | os.O_SYNC)
mm1 = mmap.mmap(fd1, 16*1024*1024, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

off = 0x800000
results = []
for i in range(4):
    val = 0xBEEF0000 + i
    wr32(mm1, off, val)
    got = rd32(mm1, off)
    print(f"  [0x{off:X}] cycle {i}: wr(0x{val:08X}) rd=0x{got:08X} {'OK' if got==val else 'FAIL'}")

mm1.close()
os.close(fd1)
