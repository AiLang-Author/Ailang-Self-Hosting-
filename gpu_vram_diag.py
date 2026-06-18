#!/usr/bin/env python3
"""
GPU VRAM Diagnostic — raw CPU read/write test on both buses.
No GPU driver, no registers, no AILang. Just mmap the BAR and poke VRAM.

Tests:
  1. First-write-readback (the 0xFFFFFFFF bug)
  2. Sequential write/read patterns at multiple offsets
  3. UC (resource0) vs WC (resource0_wc) mapping comparison
  4. Large block write/read integrity
  5. Timing comparison between buses

Run as: python3 gpu_vram_diag.py
Needs to be in video group or root for BAR access.
"""

import mmap
import os
import struct
import time
import sys

BUS1_DEV = "0000:01:00.0"
BUS2_DEV = "0000:02:00.0"

PCI_BASE = "/sys/bus/pci/devices"

def pci_path(dev, resource):
    return f"{PCI_BASE}/{dev}/{resource}"

def enable_device(dev):
    """Enable PCI device via sysfs if not already enabled."""
    en_path = f"{PCI_BASE}/{dev}/enable"
    try:
        with open(en_path, 'r') as f:
            if f.read().strip() == '1':
                return True
        with open(en_path, 'w') as f:
            f.write('1')
        return True
    except PermissionError:
        print(f"  Cannot enable {dev} (need root or video group)")
        return False

def check_pci_command(dev):
    """Read PCI command register to check Mem/BusMaster bits."""
    cfg_path = f"{PCI_BASE}/{dev}/config"
    try:
        with open(cfg_path, 'rb') as f:
            data = f.read(8)
        cmd = struct.unpack_from('<H', data, 4)[0]
        mem = bool(cmd & 0x02)
        bm = bool(cmd & 0x04)
        io = bool(cmd & 0x01)
        return cmd, mem, bm, io
    except:
        return None, None, None, None

def map_bar(dev, resource, size, offset=0):
    """mmap a PCI BAR resource file. Returns (mmap_obj, fd) or (None, None)."""
    path = pci_path(dev, resource)
    if not os.path.exists(path):
        return None, None
    try:
        fd = os.open(path, os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=offset)
        return mm, fd
    except Exception as e:
        print(f"  mmap failed for {path}: {e}")
        return None, None

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def wr32(mm, off, val):
    struct.pack_into('<I', mm, off, val & 0xFFFFFFFF)

def test_first_write(mm, offset, label):
    """Test the first-write-readback bug at a given offset."""
    # Read current value
    before = rd32(mm, offset)

    # Write a known value
    wr32(mm, offset, 0xDEADBEEF)
    read1 = rd32(mm, offset)

    # Write a second value
    wr32(mm, offset, 0xCAFEBABE)
    read2 = rd32(mm, offset)

    # Write a third value
    wr32(mm, offset, 0x12345678)
    read3 = rd32(mm, offset)

    ok1 = read1 == 0xDEADBEEF
    ok2 = read2 == 0xCAFEBABE
    ok3 = read3 == 0x12345678

    status = "OK" if (ok1 and ok2 and ok3) else "FAIL"
    print(f"  {label} @ 0x{offset:08X}: before=0x{before:08X}")
    print(f"    wr(DEADBEEF)->rd=0x{read1:08X} {'OK' if ok1 else 'FAIL'}")
    print(f"    wr(CAFEBABE)->rd=0x{read2:08X} {'OK' if ok2 else 'FAIL'}")
    print(f"    wr(12345678)->rd=0x{read3:08X} {'OK' if ok3 else 'FAIL'}")
    return ok1 and ok2 and ok3

def test_pattern_sweep(mm, base_offset, count, label):
    """Write incrementing pattern, read back, count errors."""
    errors = 0
    first_err_off = None
    first_err_exp = None
    first_err_got = None

    # Write phase
    for i in range(count):
        off = base_offset + i * 4
        wr32(mm, off, 0xA5A50000 + i)

    # Read phase
    for i in range(count):
        off = base_offset + i * 4
        got = rd32(mm, off)
        exp = 0xA5A50000 + i
        if got != exp:
            if first_err_off is None:
                first_err_off = off
                first_err_exp = exp
                first_err_got = got
            errors += 1

    if errors == 0:
        print(f"  {label}: {count} DWORDs OK")
    else:
        print(f"  {label}: {errors}/{count} errors!")
        print(f"    First error @ 0x{first_err_off:08X}: exp=0x{first_err_exp:08X} got=0x{first_err_got:08X}")
    return errors

def test_timing(mm, offset, iterations, label):
    """Measure write-read latency."""
    # Warmup
    for i in range(10):
        wr32(mm, offset, i)
        rd32(mm, offset)

    t0 = time.perf_counter_ns()
    for i in range(iterations):
        wr32(mm, offset, i)
    t1 = time.perf_counter_ns()
    wr_ns = (t1 - t0) / iterations

    t0 = time.perf_counter_ns()
    for i in range(iterations):
        rd32(mm, offset)
    t1 = time.perf_counter_ns()
    rd_ns = (t1 - t0) / iterations

    t0 = time.perf_counter_ns()
    for i in range(iterations):
        wr32(mm, offset, i)
        v = rd32(mm, offset)
    t1 = time.perf_counter_ns()
    wr_rd_ns = (t1 - t0) / iterations

    print(f"  {label} ({iterations} iters):")
    print(f"    Write: {wr_ns:.0f} ns/op   Read: {rd_ns:.0f} ns/op   Write+Read: {wr_rd_ns:.0f} ns/op")
    return wr_ns, rd_ns

def test_fresh_page_access(mm, page_size, num_pages, label):
    """Test first access to each new 4KB page — hunting the first-write bug."""
    fails = 0
    for p in range(num_pages):
        off = p * page_size
        # Fresh page — first ever write+read
        wr32(mm, off, 0xBEEF0000 + p)
        got = rd32(mm, off)
        exp = 0xBEEF0000 + p
        if got != exp:
            if fails < 5:
                print(f"    Page {p} @ 0x{off:08X}: exp=0x{exp:08X} got=0x{got:08X}")
            fails += 1
    print(f"  {label}: {num_pages} pages, {fails} first-access failures")
    return fails

def test_mmio_read(dev, label):
    """Read a few MMIO registers (BAR2) to check basic access."""
    mm, fd = map_bar(dev, "resource2", 0x40000)  # 256KB
    if mm is None:
        print(f"  {label}: Cannot map MMIO BAR")
        return

    # Read some known registers
    grbm_status = rd32(mm, 0x8010)     # GRBM_STATUS
    srbm_status = rd32(mm, 0xE50)      # SRBM_STATUS
    config_memsize = rd32(mm, 0x5428)  # CONFIG_MEMSIZE
    mc_vm_fb = rd32(mm, 0x2024)        # MC_VM_FB_LOCATION
    bif_fb_en = rd32(mm, 0x5898)       # BIF_FB_EN (0x1624 * 4 = 0x5890... actually offset)

    # Corrected register offsets for SI
    grbm_status = rd32(mm, 0x8010)
    srbm_status = rd32(mm, 0xE50)
    config_memsize = rd32(mm, 0x5428)

    print(f"  {label} MMIO:")
    print(f"    GRBM_STATUS    = 0x{grbm_status:08X}")
    print(f"    SRBM_STATUS    = 0x{srbm_status:08X}")
    print(f"    CONFIG_MEMSIZE = 0x{config_memsize:08X} ({config_memsize} MB)")

    mm.close()
    os.close(fd)

def run_bus_tests(dev, bus_label, map_size=0x100000):
    """Run all VRAM tests on one GPU."""
    print(f"\n{'='*60}")
    print(f"  {bus_label}  ({dev})")
    print(f"{'='*60}")

    # Check PCI state
    cmd, mem, bm, io = check_pci_command(dev)
    if cmd is not None:
        print(f"  PCI CMD=0x{cmd:04X}  Mem={mem}  BusMaster={bm}  IO={io}")

    # Check driver binding
    driver_path = f"{PCI_BASE}/{dev}/driver"
    if os.path.islink(driver_path):
        driver = os.path.basename(os.readlink(driver_path))
        print(f"  WARNING: Kernel driver '{driver}' is bound! Results may be unreliable.")
    else:
        print(f"  No kernel driver bound — good")

    # MMIO register snapshot
    test_mmio_read(dev, bus_label)

    # === Test with UC mapping (resource0 + O_SYNC) ===
    print(f"\n  --- UC mapping (resource0 + O_SYNC) ---")
    mm_uc, fd_uc = map_bar(dev, "resource0", map_size)
    if mm_uc is None:
        print(f"  CANNOT MAP VRAM — aborting bus tests")
        return

    # Test at several offsets including the data region (0x4082000)
    # and low VRAM
    for off_label, off in [
        ("Low VRAM (0x1000)", 0x1000),
        ("64MB+ring area (0x4000000)", 0x4000100),  # skip ring header
        ("Data region (0x4082000)", 0x4082000),
        ("Mid VRAM (0x8000000)", 0x8000000),
    ]:
        if off + 16 <= map_size:
            test_first_write(mm_uc, off, f"UC {off_label}")
        else:
            print(f"  UC {off_label}: offset beyond map size")

    # Pattern sweep in data region
    data_off = 0x4082000
    if data_off + 4096 <= map_size:
        test_pattern_sweep(mm_uc, data_off, 256, "UC pattern (data region, 1KB)")

    # Fresh page test
    start_page_off = 0x5000000  # 80MB in
    if start_page_off + 64 * 4096 <= map_size:
        test_fresh_page_access(mm_uc, 4096, 64, "UC fresh-page (64 pages @ 80MB)")

    # Timing
    if data_off + 4 <= map_size:
        test_timing(mm_uc, data_off, 10000, "UC timing (data region)")

    mm_uc.close()
    os.close(fd_uc)

    # === Test with WC mapping (resource0_wc) ===
    wc_path = pci_path(dev, "resource0_wc")
    if os.path.exists(wc_path):
        print(f"\n  --- WC mapping (resource0_wc) ---")
        try:
            fd_wc = os.open(wc_path, os.O_RDWR)
            mm_wc = mmap.mmap(fd_wc, map_size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

            for off_label, off in [
                ("Low VRAM (0x1000)", 0x1000),
                ("Data region (0x4082000)", 0x4082000),
            ]:
                if off + 16 <= map_size:
                    test_first_write(mm_wc, off, f"WC {off_label}")

            if data_off + 4096 <= map_size:
                test_pattern_sweep(mm_wc, data_off + 0x1000, 256, "WC pattern (data+0x1000, 1KB)")

            if data_off + 4 <= map_size:
                test_timing(mm_wc, data_off + 0x2000, 10000, "WC timing (data region)")

            mm_wc.close()
            os.close(fd_wc)
        except Exception as e:
            print(f"  WC mapping failed: {e}")

    print()

def main():
    print("=" * 60)
    print("  GPU VRAM DIAGNOSTIC — Raw CPU Read/Write Test")
    print("=" * 60)
    print(f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  UID: {os.getuid()}  Groups: {os.getgroups()}")

    # Check what we can access
    for dev, label in [(BUS1_DEV, "Bus 1 (display)"), (BUS2_DEV, "Bus 2 (compute)")]:
        r0 = pci_path(dev, "resource0")
        r0wc = pci_path(dev, "resource0_wc")
        r2 = pci_path(dev, "resource2")
        print(f"\n  {label}:")
        print(f"    resource0:    {'exists' if os.path.exists(r0) else 'MISSING'}  readable: {os.access(r0, os.R_OK)}  writable: {os.access(r0, os.W_OK)}")
        print(f"    resource0_wc: {'exists' if os.path.exists(r0wc) else 'MISSING'}  readable: {os.access(r0wc, os.R_OK)}  writable: {os.access(r0wc, os.W_OK)}")
        print(f"    resource2:    {'exists' if os.path.exists(r2) else 'MISSING'}  readable: {os.access(r2, os.R_OK)}  writable: {os.access(r2, os.W_OK)}")

    # Map 256MB for both (full BAR)
    MAP_SIZE = 256 * 1024 * 1024  # 256MB

    # Run on bus 2 first (compute — the broken one)
    run_bus_tests(BUS2_DEV, "Bus 2 (compute)", MAP_SIZE)

    # Run on bus 1 (display — the working one) for comparison
    # WARNING: bus 1 may have radeon/display active
    run_bus_tests(BUS1_DEV, "Bus 1 (display)", MAP_SIZE)

    print("=" * 60)
    print("  DONE")
    print("=" * 60)

if __name__ == "__main__":
    main()
