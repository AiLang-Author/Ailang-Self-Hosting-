#!/usr/bin/env python3
"""
PCIe / kernel level VRAM diagnostic.
Bypasses all GPU register logic. Tests whether the CPU can actually
reach the physical BAR address through different access methods.
"""
import mmap, os, struct, ctypes, ctypes.util

BUS1 = "0000:01:00.0"
BUS2 = "0000:02:00.0"
PCI = "/sys/bus/pci/devices"

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def wr32(mm, off, val):
    struct.pack_into('<I', mm, off, val & 0xFFFFFFFF)

def get_bar_phys_addr(dev, bar=0):
    """Read the actual BAR physical address from config space."""
    cfg_path = f"{PCI}/{dev}/config"
    try:
        with open(cfg_path, 'rb') as f:
            data = f.read(64)
        # BAR0 is at offset 0x10 in config space (64-bit, so 0x10 + 0x14)
        bar_lo = struct.unpack_from('<I', data, 0x10)[0]
        bar_hi = struct.unpack_from('<I', data, 0x14)[0]
        # Mask out type bits
        phys = ((bar_hi << 32) | (bar_lo & 0xFFFFFFF0))
        return phys
    except:
        return None

def get_resource_info(dev):
    """Read resource file for BAR addresses and flags."""
    path = f"{PCI}/{dev}/resource"
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
        bars = []
        for i, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) >= 3:
                start = int(parts[0], 16)
                end = int(parts[1], 16)
                flags = int(parts[2], 16)
                if start:
                    bars.append((i, start, end, flags))
        return bars
    except:
        return []

def check_iomem(phys_addr, size):
    """Check /proc/iomem for this physical address range."""
    try:
        with open('/proc/iomem', 'r') as f:
            for line in f:
                parts = line.strip().split(' : ', 1)
                if len(parts) == 2:
                    addr_range = parts[0].strip()
                    name = parts[1].strip()
                    if '-' in addr_range:
                        start_s, end_s = addr_range.split('-')
                        start = int(start_s, 16)
                        end = int(end_s, 16)
                        if start <= phys_addr <= end or start <= phys_addr + size <= end:
                            print(f"    {addr_range} : {name}")
    except:
        print("    (cannot read /proc/iomem)")

def check_pagemap(mm, vram_size):
    """Check actual physical addresses backing the mmap via /proc/self/pagemap."""
    page_size = os.sysconf('SC_PAGE_SIZE')
    vaddr = ctypes.addressof(ctypes.c_char.from_buffer(mm, 0))

    try:
        pm_fd = os.open('/proc/self/pagemap', os.O_RDONLY)
    except:
        print("    (cannot open pagemap)")
        return None, None

    results = []
    for i in range(min(4, vram_size // page_size)):
        va = vaddr + i * page_size
        offset = (va // page_size) * 8
        try:
            os.lseek(pm_fd, offset, os.SEEK_SET)
            data = os.read(pm_fd, 8)
            entry = struct.unpack('<Q', data)[0]
            present = bool(entry & (1 << 63))
            if present:
                pfn = entry & ((1 << 55) - 1)
                phys = pfn * page_size
                results.append((i, va, phys))
                if i < 3:
                    print(f"    Page {i}: VA=0x{va:X} -> PA=0x{phys:X}")
            else:
                if i < 3:
                    print(f"    Page {i}: VA=0x{va:X} -> NOT PRESENT")
        except Exception as e:
            if i < 3:
                print(f"    Page {i}: error: {e}")

    os.close(pm_fd)
    return results

def test_devmem(phys_addr, offset=0x1000):
    """Try accessing BAR through /dev/mem directly."""
    target = phys_addr + offset
    try:
        fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
        # Map one page at the target address
        page_size = os.sysconf('SC_PAGE_SIZE')
        page_base = target & ~(page_size - 1)
        page_off = target - page_base
        mm = mmap.mmap(fd, page_size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=page_base)

        v_before = rd32(mm, page_off)
        wr32(mm, page_off, 0xDEADBEEF)
        v1 = rd32(mm, page_off)
        wr32(mm, page_off, 0xCAFEBABE)
        v2 = rd32(mm, page_off)

        mm.close()
        os.close(fd)

        ok = v1 == 0xDEADBEEF and v2 == 0xCAFEBABE
        print(f"    /dev/mem @ PA 0x{target:X}: before=0x{v_before:08X} wr1=0x{v1:08X} wr2=0x{v2:08X} {'OK' if ok else 'FAIL'}")
        return ok
    except PermissionError:
        print(f"    /dev/mem: permission denied (need root, or CONFIG_STRICT_DEVMEM=y)")
        return None
    except Exception as e:
        print(f"    /dev/mem: {e}")
        return None

def test_dd_raw(dev):
    """Test raw read of resource0 via os.read() instead of mmap."""
    path = f"{PCI}/{dev}/resource0"
    try:
        fd = os.open(path, os.O_RDWR | os.O_SYNC)
        # Seek to offset 0x1000 and read 4 bytes
        os.lseek(fd, 0x1000, os.SEEK_SET)
        data = os.read(fd, 4)
        val = struct.unpack('<I', data)[0]
        print(f"    raw read(0x1000) = 0x{val:08X}")

        # Write via os.write
        os.lseek(fd, 0x1000, os.SEEK_SET)
        os.write(fd, struct.pack('<I', 0xBAADF00D))
        os.lseek(fd, 0x1000, os.SEEK_SET)
        data = os.read(fd, 4)
        val2 = struct.unpack('<I', data)[0]
        print(f"    raw write(0xBAADF00D) readback = 0x{val2:08X} {'OK' if val2==0xBAADF00D else 'FAIL'}")

        os.close(fd)
    except Exception as e:
        print(f"    raw read/write: {e}")

def check_kernel_claims(dev):
    """Check what the kernel thinks about this device."""
    base = f"{PCI}/{dev}"

    # Driver
    driver_path = f"{base}/driver"
    if os.path.islink(driver_path):
        driver = os.path.basename(os.readlink(driver_path))
        print(f"    Driver: {driver}")
    else:
        print(f"    Driver: none")

    # Enable state
    try:
        with open(f"{base}/enable", 'r') as f:
            print(f"    Enable: {f.read().strip()}")
    except:
        pass

    # Broken state
    try:
        with open(f"{base}/broken_parity_status", 'r') as f:
            v = f.read().strip()
            if v != '0':
                print(f"    broken_parity_status: {v}")
    except:
        pass

    # d3cold allowed
    try:
        with open(f"{base}/d3cold_allowed", 'r') as f:
            print(f"    d3cold_allowed: {f.read().strip()}")
    except:
        pass

    # power state
    try:
        with open(f"{base}/power_state", 'r') as f:
            print(f"    power_state: {f.read().strip()}")
    except:
        pass

    # current link
    for f_name in ['current_link_speed', 'current_link_width']:
        try:
            with open(f"{base}/{f_name}", 'r') as f:
                print(f"    {f_name}: {f.read().strip()}")
        except:
            pass

def run_bus(dev, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    # BAR physical address
    phys = get_bar_phys_addr(dev)
    print(f"\n  BAR0 physical address (from config): 0x{phys:X}" if phys else "  BAR0: unknown")

    # Resource info
    print(f"\n  Resource entries:")
    for idx, start, end, flags in get_resource_info(dev):
        sz = end - start + 1
        prefetch = "prefetch" if flags & 0x2000 else "non-pref"
        print(f"    BAR{idx}: 0x{start:012X}-0x{end:012X} ({sz//1024//1024}MB) flags=0x{flags:X} {prefetch}")

    # iomem
    if phys:
        print(f"\n  /proc/iomem entries covering 0x{phys:X}:")
        check_iomem(phys, 256*1024*1024)

    # Kernel state
    print(f"\n  Kernel device state:")
    check_kernel_claims(dev)

    # mmap test
    print(f"\n  mmap (sysfs resource0 + O_SYNC):")
    try:
        fd = os.open(f"{PCI}/{dev}/resource0", os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, 4096*4, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
        wr32(mm, 0x1000, 0xDEADBEEF)
        v1 = rd32(mm, 0x1000)
        wr32(mm, 0x1000, 0xCAFEBABE)
        v2 = rd32(mm, 0x1000)
        ok = v1 == 0xDEADBEEF and v2 == 0xCAFEBABE
        print(f"    wr1=0x{v1:08X} wr2=0x{v2:08X} {'OK' if ok else 'FAIL'}")

        # Check pagemap
        print(f"\n  Pagemap (physical address backing mmap):")
        check_pagemap(mm, 4096*4)

        mm.close()
        os.close(fd)
    except Exception as e:
        print(f"    mmap failed: {e}")

    # Raw read/write (no mmap)
    print(f"\n  Raw read/write (pread/pwrite, no mmap):")
    test_dd_raw(dev)

    # /dev/mem bypass
    if phys:
        print(f"\n  /dev/mem direct access (bypass kernel PCI layer):")
        test_devmem(phys, 0x1000)

run_bus(BUS1, "Bus 1 (display) — WORKING")
run_bus(BUS2, "Bus 2 (compute) — BROKEN")
