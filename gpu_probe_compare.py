#!/usr/bin/env python3
"""Compare key registers between POSTed (bus 1) and un-POSTed (bus 2) GPUs."""
import mmap, os, struct

REGS = {
    "GRBM_CNTL":                    0x8000,
    "GRBM_STATUS":                  0x8010,
    "GRBM_STATUS_SE0":              0x8014,
    "SRBM_STATUS":                  0x0E50,
    "GB_ADDR_CONFIG":               0x98F8,
    "MC_VM_FB_LOCATION":            0x2024,
    "MC_VM_AGP_TOP":                0x2028,
    "MC_VM_AGP_BOT":                0x202C,
    "MC_VM_AGP_BASE":               0x2030,
    "MC_VM_SYS_APE_LOW":            0x2034,
    "MC_VM_SYS_APE_HIGH":           0x2038,
    "MC_VM_SYS_APE_DEFAULT":        0x203C,
    "CONFIG_MEMSIZE":               0x5428,
    "BIF_FB_EN":                    0x5490,
    "MC_SHARED_BLACKOUT_CNTL":      0x20AC,
    "MC_SHARED_CHMAP":              0x2004,
    "MC_ARB_RAMCFG":                0x2760,
    "MC_SEQ_SUP_CNTL":              0x28C8,
    "MC_SEQ_MISC0":                 0x2A00,
    "MC_SEQ_TRAIN_WAKEUP_CNTL":     0x28E8,
    "HDP_HOST_PATH_CNTL":           0x2C00,
    "HDP_NONSURFACE_BASE":          0x2C04,
    "HDP_NONSURFACE_INFO":          0x2C08,
    "HDP_NONSURFACE_SIZE":          0x2C0C,
    "HDP_ADDR_CONFIG":              0x2F48,
    "HDP_MISC_CNTL":                0x2F4C,
    "DMIF_ADDR_CONFIG":             0x0BD4,
    "DMIF_ADDR_CALC":               0x0C00,
    "VM_CONTEXT0_CNTL":             0x1410,
    "MC_VM_MX_L1_TLB_CNTL":        0x2064,
    "VGA_HDP_CONTROL":              0x0328,
    "SPLL_STATUS":                  0x0E18,
    "CG_SPLL_FUNC_CNTL":           0x0600,
    "SQ_CONFIG":                    0x8C00,
    "SH_MEM_CONFIG":                0x8C34,
    "SH_MEM_BASES":                 0x8C28,
    "CP_RB0_CNTL":                  0x8600,
    "SCRATCH_REG0":                 0x8500,
    "VM_L2_CNTL":                   0x1400,
    "VM_L2_CNTL2":                  0x1404,
    "VM_L2_CNTL3":                  0x1408,
    "VM_CONTEXT0_CNTL2":            0x1430,
    "VM_CONTEXT0_PT_START":         0x1440,
    "VM_CONTEXT0_PT_END":           0x1460,
    "VM_CONTEXT0_PT_BASE":          0x1540,
    "RLC_CGTT_MGCG_OVERRIDE":      0xC400,
    "RLC_CGCG_CGLS_CTRL":          0xC404,
    "RLC_CNTL":                     0xC300,
    "CP_ME_CNTL":                   0x86D8,
    "GRBM_GFX_INDEX":              0x802C,
    # TC pipeline (golden regs — critical for buffer_load)
    "TA_CNTL_AUX":                  0x9508,
    "TCP_ADDR_CONFIG":              0xAC14,
    "TCP_CHAN_STEER_LO":            0xAC0C,
    "TCP_CHAN_STEER_HI":            0xAC10,
    "SPI_CONFIG_CNTL":              0x9100,
    "SPI_CONFIG_CNTL_1":            0x913C,
    "SX_DEBUG_1":                   0x9060,
    # Tile modes (first 4)
    "GB_TILE_MODE0":                0x9910,
    "GB_TILE_MODE1":                0x9914,
    "GB_TILE_MODE13":               0x9944,  # 1D_THIN1 compute
    # Shader memory config
    "SH_MEM_APE1_BASE":            0x8C2C,
    "SH_MEM_APE1_LIMIT":           0x8C30,
    # DMA
    "DMA_TILING_CONFIG":           0xD0B8,
    # CP ring state
    "CP_RB0_BASE":                 0x8040,
    "CP_RB0_RPTR":                 0x8700,
    "CP_RB0_WPTR":                 0x8610,
}

def open_mmio(bus):
    path = f"/sys/bus/pci/devices/0000:0{bus}:00.0/resource2"
    fd = os.open(path, os.O_RDWR | os.O_SYNC)
    mm = mmap.mmap(fd, 256*1024, mmap.MAP_SHARED, mmap.PROT_READ, offset=0)
    os.close(fd)
    return mm

def rd32(mm, off):
    mm.seek(off)
    return struct.unpack('<I', mm.read(4))[0]

try:
    mm1 = open_mmio(1)
    mm2 = open_mmio(2)
except Exception as e:
    print(f"Error opening MMIO: {e}")
    print("Try: sudo python3 gpu_probe_compare.py")
    exit(1)

print(f"{'Register':<30s}  {'Bus1 (POSTed)':<14s}  {'Bus2 (unPOST)':<14s}  {'Match'}")
print("-" * 80)

diffs = []
for name, off in sorted(REGS.items(), key=lambda x: x[1]):
    v1 = rd32(mm1, off)
    v2 = rd32(mm2, off)
    match = "  ==" if v1 == v2 else "  **DIFF**"
    print(f"{name:<30s}  0x{v1:08X}      0x{v2:08X}    {match}")
    if v1 != v2:
        diffs.append((name, off, v1, v2))

mm1.close()
mm2.close()

print(f"\n{len(diffs)} differences found out of {len(REGS)} registers")
if diffs:
    print("\nDifferences summary:")
    for name, off, v1, v2 in diffs:
        print(f"  {name} (0x{off:04X}): bus1=0x{v1:08X} bus2=0x{v2:08X}")
