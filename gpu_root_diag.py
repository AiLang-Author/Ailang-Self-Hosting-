#!/usr/bin/env python3
"""
Root-level PCIe/kernel diagnostic for VRAM failure on bus 2.
Must run as: sudo python3 gpu_root_diag.py
"""
import struct, os, mmap, subprocess

PCI = "/sys/bus/pci/devices"

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def wr32(mm, off, v):
    struct.pack_into('<I', mm, off, v & 0xFFFFFFFF)

# 1. PAT MSR
print("=== PAT MSR ===")
try:
    fd = os.open('/dev/cpu/0/msr', os.O_RDONLY)
    os.lseek(fd, 0x277, os.SEEK_SET)
    pat = struct.unpack('<Q', os.read(fd, 8))[0]
    os.close(fd)
    print(f"  PAT = 0x{pat:016X}")
    t = {0:'UC', 1:'WC', 4:'WT', 5:'WP', 6:'WB', 7:'UC-'}
    for i in range(8):
        e = (pat >> (i * 8)) & 7
        print(f"    PAT[{i}] = {t.get(e, '?')} ({e})")
except Exception as e:
    print(f"  {e}")

# 2. MTRR
print("\n=== MTRR ===")
try:
    with open('/proc/mtrr', 'r') as f:
        content = f.read().strip()
        print(content if content else "  (empty)")
except Exception as e:
    print(f"  {e}")

# 3. /proc/iomem for our BARs
print("\n=== /proc/iomem (GPU regions) ===")
with open('/proc/iomem', 'r') as f:
    for line in f:
        if any(x in line.lower() for x in ['b0000', 'c0000', 'fea0', 'fe90',
                                             '01:00', '02:00', 'pci bus']):
            print(f"  {line.rstrip()}")

# 4. Full PCI config + AER for GPUs and bridges
for dev, label in [('0000:01:00.0', 'Bus1 GPU'), ('0000:02:00.0', 'Bus2 GPU'),
                   ('0000:00:02.0', 'Bridge->1'), ('0000:00:03.0', 'Bridge->2')]:
    print(f"\n=== {label} ({dev}) config ===")
    with open(f"{PCI}/{dev}/config", 'rb') as f:
        data = f.read()
    print(f"  {len(data)} bytes")
    cmd = struct.unpack_from('<H', data, 4)[0]
    sta = struct.unpack_from('<H', data, 6)[0]
    print(f"  Cmd=0x{cmd:04X} Sta=0x{sta:04X}")

    if len(data) >= 256:
        ptr = data[0x34]
        while ptr and ptr < 256:
            cid = data[ptr]
            if cid == 0x10:  # PCIe cap
                ds = struct.unpack_from('<H', data, ptr + 0xA)[0]
                dc = struct.unpack_from('<H', data, ptr + 0x8)[0]
                ls = struct.unpack_from('<H', data, ptr + 0x12)[0]
                lc = struct.unpack_from('<H', data, ptr + 0x10)[0]
                print(f"  PCIe: DevCtl=0x{dc:04X} DevSta=0x{ds:04X} LinkCtl=0x{lc:04X} LinkSta=0x{ls:04X} Gen{ls & 0xF} x{(ls >> 4) & 0x3F}")
                if ds & 0xF:
                    print(f"    ** DevSta errors: CorrDet={bool(ds&1)} NonFatal={bool(ds&2)} Fatal={bool(ds&4)} Unsup={bool(ds&8)}")
            ptr = data[ptr + 1]
            if ptr == 0:
                break

    if len(data) > 256:
        ptr = 0x100
        while ptr and ptr < len(data) - 4:
            h = struct.unpack_from('<I', data, ptr)[0]
            cid = h & 0xFFFF
            nxt = (h >> 20) & 0xFFC
            if cid == 0 or cid == 0xFFFF:
                break
            if cid == 1 and ptr + 0x30 < len(data):  # AER
                ue = struct.unpack_from('<I', data, ptr + 4)[0]
                ce = struct.unpack_from('<I', data, ptr + 0x10)[0]
                print(f"  AER: UncErr=0x{ue:08X} CorrErr=0x{ce:08X}")
                if ue:
                    for b, n in [(4,'DLP'), (12,'Poison'), (14,'CplTO'),
                                 (15,'CplAbort'), (16,'UnexpCpl'), (20,'UnsupReq')]:
                        if ue & (1 << b):
                            print(f"    ** {n}")
                if ce:
                    for b, n in [(0,'RxErr'), (6,'BadTLP'), (7,'BadDLLP'),
                                 (8,'Rollover'), (12,'Timeout'), (13,'NonFatal')]:
                        if ce & (1 << b):
                            print(f"    ** {n}")
            if nxt == 0:
                break
            ptr = nxt

# 5. Enable bus 2 and test VRAM
print("\n=== ENABLE TEST ===")
dev = "0000:02:00.0"
with open(f"{PCI}/{dev}/enable", 'r') as f:
    print(f"  Before: enable={f.read().strip()}")
with open(f"{PCI}/{dev}/config", 'rb') as f:
    d = f.read(8)
print(f"  Before: cmd=0x{struct.unpack_from('<H', d, 4)[0]:04X}")

with open(f"{PCI}/{dev}/enable", 'w') as f:
    f.write('1')
with open(f"{PCI}/{dev}/enable", 'r') as f:
    print(f"  After:  enable={f.read().strip()}")
with open(f"{PCI}/{dev}/config", 'rb') as f:
    d = f.read(8)
cmd_after = struct.unpack_from('<H', d, 4)[0]
print(f"  After:  cmd=0x{cmd_after:04X}")

# 6. VRAM test after enable
print("\n=== VRAM TEST (after enable) ===")
for dev, label in [('0000:02:00.0', 'Bus2'), ('0000:01:00.0', 'Bus1')]:
    try:
        fd = os.open(f"{PCI}/{dev}/resource0", os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, 0x200000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
        for off in [0x1000, 0x2000, 0x4000, 0x10000, 0x100000]:
            wr32(mm, off, 0xDEADBEEF)
            v1 = rd32(mm, off)
            wr32(mm, off, 0xCAFEBABE)
            v2 = rd32(mm, off)
            ok = v1 == 0xDEADBEEF and v2 == 0xCAFEBABE
            print(f"  {label} [0x{off:X}] wr1=0x{v1:08X} wr2=0x{v2:08X} {'OK' if ok else 'FAIL'}")
        mm.close()
        os.close(fd)
    except Exception as e:
        print(f"  {label}: {e}")

# 7. /dev/mem direct access to bus 2 BAR0
print("\n=== /dev/mem DIRECT (bus 2 BAR0 @ 0xB0000000) ===")
try:
    fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
    ps = os.sysconf('SC_PAGE_SIZE')
    target = 0xB0001000
    pb = target & ~(ps - 1)
    po = target - pb
    mm = mmap.mmap(fd, ps, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=pb)
    wr32(mm, po, 0xDEADBEEF)
    v1 = rd32(mm, po)
    wr32(mm, po, 0xCAFEBABE)
    v2 = rd32(mm, po)
    print(f"  0x{target:X}: wr1=0x{v1:08X} wr2=0x{v2:08X} {'OK' if v1==0xDEADBEEF and v2==0xCAFEBABE else 'FAIL'}")
    mm.close()
    os.close(fd)
except Exception as e:
    print(f"  /dev/mem: {e}")

# 8. dmesg
print("\n=== dmesg (PCI/error related) ===")
r = subprocess.run(['dmesg'], capture_output=True, text=True)
for line in r.stdout.split('\n'):
    lo = line.lower()
    if any(x in lo for x in ['pci', 'aer', 'error', '02:00', '01:00',
                              'b0000', 'c0000', 'iommu', 'fault', 'mce']):
        print(f"  {line.strip()}")
