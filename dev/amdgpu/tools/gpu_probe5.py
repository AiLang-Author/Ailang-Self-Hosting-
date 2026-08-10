#!/usr/bin/env python3
"""
GPU probe 5: Post-dispatch VRAM analysis.
Read the exact addresses the shader uses (src @ 0x4082000, dst @ 0x4082100),
the shader code area, ring buffer state, and fence values.
Diagnose whether the shader actually wrote anything, or if reads are stale.

Run AFTER test_accel_gcn.x exits (card must still have PCI CMD enabled).
NO PCI RESET.  NO RESCAN.  NO HDP CONFIG WRITES.
"""
import mmap, struct, os

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

# Known layout from AccelGCNLayout + debug output
DATA_OFFSET   = 0x4082000   # data area base
SRC_OFFSET    = 0x4082000   # slot 0: src[0..63] (256 bytes)
DST_OFFSET    = 0x4082100   # slot 1: dst[0..63] (256 bytes)
SHADER_OFFSET = 0x4040000   # shader code
BUF_DESC_OFF  = 0x4080000   # V# descriptors
RING0_BASE    = 0x4000000   # ring buffer base
IB_OFFSET     = 0x4081000   # indirect buffer

# HDP flush register (write cache only — safe to write from CPU)
HDP_MEM_COHERENCY_FLUSH = 0x5480

print("=" * 60)
print("GPU PROBE 5 — Post-dispatch VRAM analysis")
print("  NO PCI RESET.  NO RESCAN.  NO HDP CONFIG WRITES.")
print("=" * 60)

mmio = open_bar(COMPUTE_DEV, "resource2", 256 * 1024)
vram = open_bar(COMPUTE_DEV, "resource0", 256 * 1024 * 1024)

# Do ONE HDP write-cache flush (safe, always works)
wr32(mmio, HDP_MEM_COHERENCY_FLUSH, 1)

# ── Read src and dst arrays ──────────────────────────────────────────
print("\n── SRC array (slot 0 @ 0x4082000) ──")
print("  Expected: src[i] = i (0, 1, 2, ... 63)")
src_vals = []
for i in range(64):
    v = rd32(vram, SRC_OFFSET + i * 4)
    src_vals.append(v)
# Print first 8 and last 4
for i in range(8):
    print(f"  src[{i:2d}] = 0x{src_vals[i]:08X}  (expect {i})")
print(f"  ...")
for i in range(60, 64):
    print(f"  src[{i:2d}] = 0x{src_vals[i]:08X}  (expect {i})")
unique_src = set(src_vals)
print(f"  Unique values: {len(unique_src)}")
if len(unique_src) <= 4:
    print(f"  Values: {', '.join(f'0x{v:08X}' for v in sorted(unique_src))}")

print("\n── DST array (slot 1 @ 0x4082100) ──")
print("  Expected: dst[i] = src[i] + 42 = i + 42")
dst_vals = []
for i in range(64):
    v = rd32(vram, DST_OFFSET + i * 4)
    dst_vals.append(v)
for i in range(8):
    print(f"  dst[{i:2d}] = 0x{dst_vals[i]:08X}  (expect {i + 42})")
print(f"  ...")
for i in range(60, 64):
    print(f"  dst[{i:2d}] = 0x{dst_vals[i]:08X}  (expect {i + 42})")
unique_dst = set(dst_vals)
print(f"  Unique values: {len(unique_dst)}")
if len(unique_dst) <= 4:
    print(f"  Values: {', '.join(f'0x{v:08X}' for v in sorted(unique_dst))}")

# ── Pattern analysis ─────────────────────────────────────────────────
print("\n── Pattern analysis ──")
# Check alternating pattern
if len(dst_vals) >= 4:
    even_same = all(dst_vals[i] == dst_vals[0] for i in range(0, 64, 2))
    odd_same = all(dst_vals[i] == dst_vals[1] for i in range(1, 64, 2))
    if even_same and odd_same and dst_vals[0] != dst_vals[1]:
        print(f"  ALTERNATING pattern: even=0x{dst_vals[0]:08X} odd=0x{dst_vals[1]:08X}")
        print(f"    ~even = 0x{(~dst_vals[0])&0xFFFFFFFF:08X}")
        print(f"    ~odd  = 0x{(~dst_vals[1])&0xFFFFFFFF:08X}")
    else:
        print(f"  No simple alternating pattern")

# ── Write-then-read test at dst area ─────────────────────────────────
print("\n── Fresh write/read test at dst area ──")
test_off = DST_OFFSET
for pat in [0xAAAAAAAA, 0x55555555, 0x12345678, 0x00000000]:
    wr32(vram, test_off, pat)
    wr32(mmio, HDP_MEM_COHERENCY_FLUSH, 1)
    rb = rd32(vram, test_off)
    ok = "OK" if rb == pat else "FAIL"
    print(f"  Write 0x{pat:08X} → Read 0x{rb:08X}  [{ok}]")

# ── Read raw bytes around dst[0] to check alignment ──────────────────
print("\n── Raw bytes around dst area (16 DWORDs) ──")
for i in range(16):
    off = DST_OFFSET + i * 4
    v = rd32(vram, off)
    print(f"  0x{off:08X}: 0x{v:08X}")

# ── Shader code area ─────────────────────────────────────────────────
print("\n── Shader code (first 20 DWORDs @ 0x4040000) ──")
for i in range(20):
    v = rd32(vram, SHADER_OFFSET + i * 4)
    print(f"  [{i:2d}] 0x{v:08X}")

# ── IB content ────────────────────────────────────────────────────────
print("\n── IB scratch area (7 DWORDs @ 0x4081000) ──")
for i in range(7):
    v = rd32(vram, IB_OFFSET + i * 4)
    print(f"  [{i}] 0x{v:08X}")

# ── V# descriptor area ───────────────────────────────────────────────
print("\n── V# descriptor area (8 DWORDs @ 0x4080000) ──")
for i in range(8):
    v = rd32(vram, BUF_DESC_OFF + i * 4)
    print(f"  [{i}] 0x{v:08X}")

# ── Fence/breadcrumb area (scan first 64 DWORDs of ring region) ──────
print("\n── Key MMIO registers ──")
regs = [
    ("GRBM_STATUS",     0x8010),
    ("CP_ME_CNTL",      0x86D8),
    ("SCRATCH_REG0",    0x8500),
    ("CP_RB1_RPTR",     0x8620),
    ("CP_RB1_WPTR",     0x8630),
]
for name, off in regs:
    v = rd32(mmio, off)
    print(f"  {name:20s} = 0x{v:08X}")

# ── Test: write known values to src, see if they survive ──────────────
print("\n── Canary test: write known values to src area ──")
canary = [0xDEAD0000 + i for i in range(8)]
for i, c in enumerate(canary):
    wr32(vram, SRC_OFFSET + i * 4, c)
wr32(mmio, HDP_MEM_COHERENCY_FLUSH, 1)
errs = 0
for i, c in enumerate(canary):
    rb = rd32(vram, SRC_OFFSET + i * 4)
    ok = rb == c
    if not ok:
        errs += 1
    print(f"  src[{i}]: wrote 0x{c:08X} read 0x{rb:08X} [{'OK' if ok else 'FAIL'}]")
if errs == 0:
    print(f"  ALL 8 canaries passed — BAR0 VRAM read/write is functional")
else:
    print(f"  {errs}/8 FAILED — BAR0 path is broken")

# Cleanup
for i in range(8):
    wr32(vram, SRC_OFFSET + i * 4, 0)

vram.close()
mmio.close()
print(f"\n{'='*60}")
print("PROBE 5 COMPLETE")
print(f"{'='*60}")
