#!/usr/bin/env python3
"""
GPU probe 3: Compare both GPUs PCI config, test BAR0 on compute GPU.
  01:00.0 = display GPU (radeon bound) — READ ONLY, no BAR mmap
  02:00.0 = compute GPU (unbound)      — full probe + BAR0 test
NO PCI RESET. NO PCI RESCAN. Read-only on display GPU.
"""
import mmap, struct, os, sys

DISPLAY_DEV = "/sys/bus/pci/devices/0000:01:00.0"
COMPUTE_DEV = "/sys/bus/pci/devices/0000:02:00.0"

# ── PCI config space helpers ──────────────────────────────────────────

def read_pci_config(dev_path, nbytes=256):
    path = os.path.join(dev_path, "config")
    with open(path, "rb") as f:
        return f.read(nbytes)

def u16(buf, off):
    return struct.unpack_from('<H', buf, off)[0]

def u32(buf, off):
    return struct.unpack_from('<I', buf, off)[0]

def dump_pci_header(label, cfg):
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"{'─'*60}")
    vid = u16(cfg, 0x00)
    did = u16(cfg, 0x02)
    cmd = u16(cfg, 0x04)
    sts = u16(cfg, 0x06)
    rev = cfg[0x08]
    cls = (cfg[0x0B] << 16) | (cfg[0x0A] << 8) | cfg[0x09]
    hdr = cfg[0x0E]
    bar0 = u32(cfg, 0x10)
    bar1 = u32(cfg, 0x14)
    bar2 = u32(cfg, 0x18)
    bar3 = u32(cfg, 0x1C)
    bar4 = u32(cfg, 0x20)
    bar5 = u32(cfg, 0x24)
    sub_vid = u16(cfg, 0x2C)
    sub_did = u16(cfg, 0x2E)
    rombar = u32(cfg, 0x30)
    intline = cfg[0x3C]
    intpin  = cfg[0x3D]

    print(f"  VID:DID      = {vid:04X}:{did:04X}  rev {rev:02X}  class {cls:06X}")
    print(f"  CMD          = 0x{cmd:04X}  "
          f"IO={'Y' if cmd&1 else 'N'}  "
          f"MEM={'Y' if cmd&2 else 'N'}  "
          f"BusMaster={'Y' if cmd&4 else 'N'}  "
          f"INTxDis={'Y' if cmd&(1<<10) else 'N'}")
    print(f"  STS          = 0x{sts:04X}  "
          f"CapList={'Y' if sts&(1<<4) else 'N'}  "
          f"MstAbort={'Y' if sts&(1<<13) else 'N'}  "
          f"TgtAbort={'Y' if sts&(1<<11) else 'N'}  "
          f"SERR={'Y' if sts&(1<<14) else 'N'}  "
          f"DetParity={'Y' if sts&(1<<15) else 'N'}")
    print(f"  HDR type     = 0x{hdr:02X}")

    # BAR decode
    def bar_str(val, hi_val=None):
        if val == 0 and (hi_val is None or hi_val == 0):
            return "disabled"
        is_io = val & 1
        if is_io:
            return f"I/O  @ 0x{val & ~0x3:08X}"
        is_64 = (val >> 1) & 3 == 2
        pf = "PF" if val & 8 else "NP"
        base = val & ~0xF
        if is_64 and hi_val is not None:
            full = (hi_val << 32) | base
            return f"Mem64 {pf} @ 0x{full:016X}"
        return f"Mem32 {pf} @ 0x{base:08X}"

    is_bar0_64 = (bar0 >> 1) & 3 == 2
    is_bar2_64 = (bar2 >> 1) & 3 == 2

    print(f"  BAR0         = 0x{bar0:08X}  {bar_str(bar0, bar1 if is_bar0_64 else None)}")
    if is_bar0_64:
        print(f"  BAR1 (hi32)  = 0x{bar1:08X}")
    else:
        print(f"  BAR1         = 0x{bar1:08X}  {bar_str(bar1)}")
    print(f"  BAR2         = 0x{bar2:08X}  {bar_str(bar2, bar3 if is_bar2_64 else None)}")
    if is_bar2_64:
        print(f"  BAR3 (hi32)  = 0x{bar3:08X}")
    else:
        print(f"  BAR3         = 0x{bar3:08X}  {bar_str(bar3)}")
    print(f"  BAR4         = 0x{bar4:08X}  {bar_str(bar4)}")
    print(f"  BAR5         = 0x{bar5:08X}  {bar_str(bar5)}")
    print(f"  ROM BAR      = 0x{rombar:08X}  {'enabled' if rombar & 1 else 'disabled'}")
    print(f"  SubSys       = {sub_vid:04X}:{sub_did:04X}")
    print(f"  INT line/pin = {intline}/{intpin}")

    return {
        'vid': vid, 'did': did, 'cmd': cmd, 'sts': sts, 'rev': rev,
        'bar0': bar0, 'bar1': bar1, 'bar2': bar2, 'bar3': bar3,
        'sub_vid': sub_vid, 'sub_did': sub_did,
    }

# ── MMIO / VRAM helpers (compute GPU only) ───────────────────────────

def open_bar(dev_path, resource, size):
    path = os.path.join(dev_path, resource)
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

# ── Register list ─────────────────────────────────────────────────────

KEY_REGS = [
    ("GRBM_STATUS",              0x8010),
    ("SRBM_STATUS",              0x0E50),
    ("BIF_FB_EN",                0x5490),
    ("MC_VM_FB_LOCATION",        0x2024),
    ("MC_VM_SYS_APT_LOW",       0x2034),
    ("MC_VM_SYS_APT_HIGH",      0x2038),
    ("MC_VM_SYS_APT_DEF",       0x203C),
    ("MC_SHARED_BLACKOUT_CNTL",  0x20AC),
    ("MC_SEQ_MISC0",             0x2A00),
    ("MC_ARB_RAMCFG",            0x2760),
    ("HDP_HOST_PATH_CNTL",      0x2C00),
    ("HDP_MISC_CNTL",           0x2F4C),
    ("HDP_MEM_COHERENCY_FLUSH", 0x5480),
    ("HDP_NONSURFACE_BASE",     0x2C04),
    ("HDP_NONSURFACE_INFO",     0x2C08),
    ("HDP_NONSURFACE_SIZE",     0x2C0C),
    ("HDP_ADDR_CONFIG",          0x2F48),
    ("VM_CONTEXT0_CNTL",        0x1410),
    ("MC_VM_MX_L1_TLB_CNTL",   0x2064),
    ("CG_SPLL_FUNC_CNTL",      0x0600),
    ("CG_SPLL_FUNC_CNTL_2",    0x0604),
    ("CG_SPLL_FUNC_CNTL_3",    0x0608),
    ("SPLL_STATUS",              0x060C),
    ("CP_ME_CNTL",               0x86D8),
    ("SCRATCH_REG0",             0x8500),
    ("SCRATCH_UMSK",             0x8540),
]

HDP_DECODE_BITS = {
    0:  "FLUSH_INVALIDATE_CACHE",
    25: "READ_CACHE_DISABLE",
}

# ══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("GPU PROBE 3 — Dual-card compare + BAR0 test")
print("  Display: 01:00.0 (radeon)  —  READ ONLY")
print("  Compute: 02:00.0 (unbound) —  full probe")
print("  NO PCI RESET.  NO PCI RESCAN.")
print("=" * 60)

# ── Check driver binding ─────────────────────────────────────────────
print("\n── Driver Binding ──")
for label, dev in [("Display 01:00.0", DISPLAY_DEV), ("Compute 02:00.0", COMPUTE_DEV)]:
    drv_link = os.path.join(dev, "driver")
    if os.path.islink(drv_link):
        drv = os.path.basename(os.readlink(drv_link))
    else:
        drv = "(none — unbound)"
    print(f"  {label}: {drv}")

# ── PCI config compare ───────────────────────────────────────────────
print("\n══ PCI CONFIG SPACE ══")
disp_cfg = read_pci_config(DISPLAY_DEV)
comp_cfg = read_pci_config(COMPUTE_DEV)

disp_info = dump_pci_header("DISPLAY GPU — 01:00.0", disp_cfg)
comp_info = dump_pci_header("COMPUTE GPU — 02:00.0", comp_cfg)

# Compare key fields
print(f"\n{'─'*60}")
print(f"  COMPARISON")
print(f"{'─'*60}")

def cmp(field, fmt="0x{:04X}"):
    dv = disp_info[field]
    cv = comp_info[field]
    match = "OK" if dv == cv else "DIFFER"
    print(f"  {field:12s}  disp={fmt.format(dv)}  comp={fmt.format(cv)}  [{match}]")
    return dv == cv

cmp('vid')
cmp('did')
cmp('rev', "0x{:02X}")
cmp('cmd')
cmp('sts')
cmp('sub_vid')
cmp('sub_did')

# CMD flags compare
dc = disp_info['cmd']
cc = comp_info['cmd']
print(f"\n  CMD flags detail:")
for bit, name in [(0,"IO"), (1,"MEM"), (2,"BusMaster"), (10,"INTxDisable")]:
    db = (dc >> bit) & 1
    cb = (cc >> bit) & 1
    match = "OK" if db == cb else "DIFFER"
    print(f"    {name:15s}  disp={db}  comp={cb}  [{match}]")

# Status error bits
ds = disp_info['sts']
cs = comp_info['sts']
print(f"\n  STS error bits:")
for bit, name in [(11,"TgtAbortRcv"), (13,"MstAbortRcv"), (14,"SysErrSig"), (15,"DetParityErr")]:
    db = (ds >> bit) & 1
    cb = (cs >> bit) & 1
    flag = " *** ERROR ***" if cb else ""
    print(f"    {name:15s}  disp={db}  comp={cb}{flag}")

# ── Compute GPU MMIO registers ───────────────────────────────────────
print(f"\n══ COMPUTE GPU MMIO REGISTERS ══")
mmio = open_bar(COMPUTE_DEV, "resource2", 256 * 1024)

for name, off in KEY_REGS:
    val = rd32(mmio, off)
    extra = ""
    if name == "BIF_FB_EN":
        extra = f"  RD={'Y' if val&1 else 'N'} WR={'Y' if val&2 else 'N'}"
        if not (val & 1):
            extra += "  *** FB READ DISABLED ***"
    elif name == "MC_SHARED_BLACKOUT_CNTL" and val != 0:
        extra = "  *** BLACKOUT ACTIVE ***"
    elif name == "HDP_HOST_PATH_CNTL":
        extra = f"  RdCacheDis={(val>>25)&1}"
    elif name == "HDP_MISC_CNTL":
        extra = f"  FlushInvCache={val&1}"
    elif name == "SPLL_STATUS":
        extra = f"  locked={'Y' if val&1 else 'N'}"
    elif name == "MC_VM_FB_LOCATION":
        fb_base = val & 0xFFFF
        fb_top = (val >> 16) & 0xFFFF
        sz_mb = ((fb_top - fb_base + 1) << 24) // (1024*1024)
        extra = f"  base=0x{fb_base:04X} top=0x{fb_top:04X} -> {sz_mb}MB"
    print(f"  {name:30s} [0x{off:04X}] = 0x{val:08X}{extra}")

# ── BAR0 VRAM test (compute only) ────────────────────────────────────
print(f"\n══ COMPUTE GPU BAR0 VRAM TEST ══")

# Check BIF first
bif = rd32(mmio, 0x5490)
if not (bif & 1):
    print("  *** BIF_FB_EN bit 0 (read) is CLEAR — BAR0 reads will return garbage ***")
    print("  *** Skipping VRAM test ***")
else:
    vram = open_bar(COMPUTE_DEV, "resource0", 256 * 1024 * 1024)

    # Flush HDP write cache before any reads
    HDP_FLUSH = 0x5480
    wr32(mmio, HDP_FLUSH, 1)

    # Test pattern at several offsets
    TEST_PAT = 0xA5A5A5A5
    offsets = [
        (0x00000000, "VRAM base"),
        (0x00001000, "4KB"),
        (0x00010000, "64KB"),
        (0x00100000, "1MB"),
        (0x01000000, "16MB"),
        (0x04000000, "64MB (ring region)"),
        (0x04082000, "DATA region (src)"),
        (0x04082100, "DATA region (dst)"),
    ]

    print(f"\n  Write/Read test pattern 0x{TEST_PAT:08X}:")
    all_ok = True
    for off, desc in offsets:
        # Save original
        wr32(mmio, HDP_FLUSH, 1)
        orig = rd32(vram, off) if off < vram.size() else 0

        # Write pattern
        wr32(vram, off, TEST_PAT)
        # HDP flush then read back
        wr32(mmio, HDP_FLUSH, 1)
        rb = rd32(vram, off)
        # Restore
        wr32(vram, off, orig)

        ok = rb == TEST_PAT
        if not ok:
            all_ok = False
        print(f"    0x{off:08X} ({desc:20s}): "
              f"orig=0x{orig:08X}  wrote=0x{TEST_PAT:08X}  "
              f"readback=0x{rb:08X}  [{'OK' if ok else 'FAIL'}]")

    # Bulk 64 DWORD test at DATA region
    print(f"\n  Bulk 64-DWORD test @ 0x04082000:")
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
                print(f"    [{i:2d}] expected {i+42:5d}, got 0x{val:08X}")
    if errs == 0:
        print(f"    ALL 64 OK")
    else:
        print(f"    {errs}/64 FAILED")
    # Cleanup
    for i in range(64):
        wr32(vram, base + i*4, 0)

    vram.close()

mmio.close()

print(f"\n{'='*60}")
print("PROBE 3 COMPLETE — no PCI reset, no rescan")
print(f"{'='*60}")
