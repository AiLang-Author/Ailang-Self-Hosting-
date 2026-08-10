#!/usr/bin/env python3
"""
Write bus 1 HDP values to bus 2, then test VRAM access.
"""
import mmap, os, struct, time

BUS2_DEV = "0000:02:00.0"
PCI = "/sys/bus/pci/devices"

def rd32(mm, off):
    return struct.unpack_from('<I', mm, off)[0]

def wr32(mm, off, val):
    struct.pack_into('<I', mm, off, val & 0xFFFFFFFF)

def main():
    # Map MMIO (BAR2)
    mmio_path = f"{PCI}/{BUS2_DEV}/resource2"
    mmio_fd = os.open(mmio_path, os.O_RDWR | os.O_SYNC)
    mmio = mmap.mmap(mmio_fd, 0x40000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

    # Map VRAM (BAR0)
    vram_path = f"{PCI}/{BUS2_DEV}/resource0"
    vram_fd = os.open(vram_path, os.O_RDWR | os.O_SYNC)
    vram = mmap.mmap(vram_fd, 16*1024*1024, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

    print("=== BEFORE: Bus 2 HDP registers ===")
    for name, off in [
        ("HDP_HOST_PATH_CNTL",  0x2C00),
        ("HDP_NONSURFACE_BASE", 0x2C04),
        ("HDP_NONSURFACE_INFO", 0x2C08),
        ("HDP_NONSURFACE_SIZE", 0x2C0C),
        ("HDP_ADDR_CONFIG",     0x2F48),
        ("MC_VM_FB_LOCATION",   0x2024),
        ("BIF_FB_EN",           0x5490),
    ]:
        print(f"  {name:30s} = 0x{rd32(mmio, off):08X}")

    print("\n=== BEFORE: VRAM test ===")
    for off in [0x1000, 0x100000, 0x400000]:
        wr32(vram, off, 0xDEADBEEF)
        v = rd32(vram, off)
        print(f"  VRAM[0x{off:07X}] wr(DEADBEEF) rd=0x{v:08X} {'OK' if v==0xDEADBEEF else 'FAIL'}")

    # Bus 1 values (from BIOS POST):
    #   HDP_NONSURFACE_BASE = 0xF4000000  (matches MC_VM_FB_LOCATION base on bus 1)
    #   HDP_NONSURFACE_INFO = 0x00020080
    #   HDP_NONSURFACE_SIZE = 0x7FFFFBFF
    #   HDP_ADDR_CONFIG     = 0x42011003
    #
    # Bus 2 has MC_VM_FB_LOCATION = 0x003F0000 (base=0).
    # So HDP_NONSURFACE_BASE should be 0x00000000 (already is).
    # The INFO and SIZE and ADDR_CONFIG need to match bus 1's layout.

    print("\n=== WRITING HDP registers ===")

    # Write HDP_NONSURFACE_INFO to bus 1 value
    print("  Writing HDP_NONSURFACE_INFO = 0x00020080 ...", end=" ", flush=True)
    wr32(mmio, 0x2C08, 0x00020080)
    rb = rd32(mmio, 0x2C08)
    print(f"readback=0x{rb:08X} {'OK' if rb==0x00020080 else 'DIFF'}")

    # Write HDP_NONSURFACE_SIZE to bus 1 value
    print("  Writing HDP_NONSURFACE_SIZE = 0x7FFFFBFF ...", end=" ", flush=True)
    wr32(mmio, 0x2C0C, 0x7FFFFBFF)
    rb = rd32(mmio, 0x2C0C)
    print(f"readback=0x{rb:08X} {'OK' if rb==0x7FFFFBFF else 'DIFF'}")

    # Write HDP_ADDR_CONFIG to bus 1 value
    print("  Writing HDP_ADDR_CONFIG = 0x42011003 ...", end=" ", flush=True)
    wr32(mmio, 0x2F48, 0x42011003)
    rb = rd32(mmio, 0x2F48)
    print(f"readback=0x{rb:08X} {'OK' if rb==0x42011003 else 'DIFF'}")

    # HDP_NONSURFACE_BASE — keep at 0 since MC base is 0
    # But let's also try writing it explicitly
    print("  Writing HDP_NONSURFACE_BASE = 0x00000000 ...", end=" ", flush=True)
    wr32(mmio, 0x2C04, 0x00000000)
    rb = rd32(mmio, 0x2C04)
    print(f"readback=0x{rb:08X} {'OK' if rb==0x00000000 else 'DIFF'}")

    # Flush HDP
    wr32(mmio, 0x5480, 1)

    print("\n=== AFTER: HDP registers ===")
    for name, off in [
        ("HDP_NONSURFACE_BASE", 0x2C04),
        ("HDP_NONSURFACE_INFO", 0x2C08),
        ("HDP_NONSURFACE_SIZE", 0x2C0C),
        ("HDP_ADDR_CONFIG",     0x2F48),
    ]:
        print(f"  {name:30s} = 0x{rd32(mmio, off):08X}")

    print("\n=== AFTER: VRAM test ===")
    total = 0
    ok = 0
    for off in [0x1000, 0x2000, 0x3000, 0x4000, 0x100000, 0x200000, 0x400000, 0x800000]:
        val = 0xA5000000 | off
        wr32(vram, off, val)
        got = rd32(vram, off)
        status = "OK" if got == val else "FAIL"
        print(f"  VRAM[0x{off:07X}] wr(0x{val:08X}) rd=0x{got:08X} {status}")
        total += 1
        if got == val:
            ok += 1

    # Pattern test
    print("\n=== Pattern write/read (256 DWORDs at 0x100000) ===")
    errs = 0
    for i in range(256):
        wr32(vram, 0x100000 + i*4, 0xBEEF0000 + i)
    for i in range(256):
        got = rd32(vram, 0x100000 + i*4)
        if got != 0xBEEF0000 + i:
            if errs < 3:
                print(f"  [{i}] exp=0x{0xBEEF0000+i:08X} got=0x{got:08X}")
            errs += 1
    print(f"  {256-errs}/256 correct, {errs} errors")

    print(f"\n=== SUMMARY: {ok}/{total} single writes OK, {256-errs}/256 pattern OK ===")

    vram.close(); os.close(vram_fd)
    mmio.close(); os.close(mmio_fd)

if __name__ == "__main__":
    main()
