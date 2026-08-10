#!/usr/bin/env python3
"""
Full GPU register state probe — READ ONLY (except PCI command enable on bus 2).

This probe:
  1. Enables PCI Mem+BusMaster on bus 2 (the BIOS leaves it disabled)
  2. Reads EVERY relevant register on BOTH GPUs
  3. Prints a side-by-side comparison
  4. Does NOT write any GPU registers — purely observational

Run after cold boot, BEFORE any AILang test binary.
Run AGAIN after test binary (to see what ASIC_INIT changed).

Usage:
    python3 gpu_probe_fullstate.py           # normal run
    python3 gpu_probe_fullstate.py post      # label output as "post-init"
"""
import mmap, struct, os, sys

BUS1_DEV = "/sys/bus/pci/devices/0000:01:00.0"
BUS2_DEV = "/sys/bus/pci/devices/0000:02:00.0"

# ─── PCI config space helpers ──────────────────────────────────────────────
def pci_read_config(dev, offset, size=1):
    path = os.path.join(dev, "config")
    fd = os.open(path, os.O_RDONLY)
    os.lseek(fd, offset, os.SEEK_SET)
    data = os.read(fd, size)
    os.close(fd)
    if size == 1:
        return data[0]
    elif size == 2:
        return struct.unpack('<H', data)[0]
    else:
        return struct.unpack('<I', data)[0]

def pci_write_config(dev, offset, value, size=1):
    path = os.path.join(dev, "config")
    fd = os.open(path, os.O_WRONLY)
    os.lseek(fd, offset, os.SEEK_SET)
    if size == 1:
        os.write(fd, bytes([value & 0xFF]))
    elif size == 2:
        os.write(fd, struct.pack('<H', value & 0xFFFF))
    else:
        os.write(fd, struct.pack('<I', value & 0xFFFFFFFF))
    os.close(fd)

# ─── MMIO helpers ──────────────────────────────────────────────────────────
def open_mmio(dev):
    path = os.path.join(dev, "resource2")
    fd = os.open(path, os.O_RDWR | os.O_SYNC)
    mm = mmap.mmap(fd, 256 * 1024, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
    os.close(fd)
    return mm

def rd32(mm, off):
    mm.seek(off)
    return struct.unpack('<I', mm.read(4))[0]

# ─── Register map ─────────────────────────────────────────────────────────
# Grouped by function for readability
REGS = {}

# PCI/BIF
REGS["BIF_FB_EN"]                     = 0x5490
REGS["CONFIG_MEMSIZE"]                = 0x5428

# Clock/PLL
REGS["CG_SPLL_FUNC_CNTL"]            = 0x0600
REGS["CG_SPLL_FUNC_CNTL_2"]          = 0x0604
REGS["CG_SPLL_FUNC_CNTL_3"]          = 0x0608
REGS["CG_SPLL_FUNC_CNTL_4"]          = 0x060C
REGS["CG_SPLL_SPREAD_SPECTRUM"]       = 0x0620
REGS["CG_SPLL_SPREAD_SPECTRUM_2"]     = 0x0624
REGS["SPLL_STATUS"]                   = 0x0E18

# SRBM
REGS["SRBM_STATUS"]                   = 0x0E50
REGS["SRBM_STATUS2"]                  = 0x0EC4

# GRBM
REGS["GRBM_CNTL"]                    = 0x8000
REGS["GRBM_STATUS"]                  = 0x8010
REGS["GRBM_STATUS_SE0"]              = 0x8014
REGS["GRBM_STATUS_SE1"]              = 0x8018
REGS["GRBM_GFX_INDEX"]               = 0x802C

# MC / VRAM
REGS["MC_VM_FB_LOCATION"]            = 0x2024
REGS["MC_VM_AGP_TOP"]                = 0x2028
REGS["MC_VM_AGP_BOT"]                = 0x202C
REGS["MC_VM_AGP_BASE"]               = 0x2030
REGS["MC_VM_SYS_APE_LOW"]            = 0x2034
REGS["MC_VM_SYS_APE_HIGH"]           = 0x2038
REGS["MC_VM_SYS_APE_DEFAULT"]        = 0x203C
REGS["MC_VM_MX_L1_TLB_CNTL"]        = 0x2064
REGS["MC_SHARED_CHMAP"]              = 0x2004
REGS["MC_SHARED_BLACKOUT_CNTL"]      = 0x20AC
REGS["MC_ARB_RAMCFG"]                = 0x2760
REGS["MC_SEQ_SUP_CNTL"]              = 0x28C8
REGS["MC_SEQ_TRAIN_WAKEUP_CNTL"]     = 0x28E8
REGS["MC_SEQ_MISC0"]                 = 0x2A00

# VM
REGS["VM_CONTEXT0_CNTL"]             = 0x1410
REGS["VM_CONTEXT0_CNTL2"]            = 0x1430
REGS["VM_CONTEXT0_PT_START"]         = 0x1440
REGS["VM_CONTEXT0_PT_END"]           = 0x1460
REGS["VM_CONTEXT0_PT_BASE"]          = 0x1540
REGS["VM_L2_CNTL"]                   = 0x1400
REGS["VM_L2_CNTL2"]                  = 0x1404
REGS["VM_L2_CNTL3"]                  = 0x1408
REGS["VM_INVALIDATE_REQUEST"]        = 0x1478
REGS["VM_INVALIDATE_RESPONSE"]       = 0x147C

# HDP — the registers that keep crashing
REGS["HDP_HOST_PATH_CNTL"]           = 0x2C00
REGS["HDP_NONSURFACE_BASE"]          = 0x2C04
REGS["HDP_NONSURFACE_INFO"]          = 0x2C08
REGS["HDP_NONSURFACE_SIZE"]          = 0x2C0C
REGS["HDP_ADDR_CONFIG"]              = 0x2F48
REGS["HDP_MISC_CNTL"]                = 0x2F4C
REGS["HDP_MEM_COHERENCY_FLUSH"]      = 0x5480

# Address config (THE critical ones for buffer_load routing)
REGS["GB_ADDR_CONFIG"]               = 0x98F8
REGS["DMIF_ADDR_CONFIG"]             = 0x0BD4
REGS["DMIF_ADDR_CALC"]               = 0x0C00
REGS["DMA_TILING_CONFIG"]            = 0xD0B8

# TC pipeline (buffer_load path)
REGS["TA_CNTL_AUX"]                  = 0x9508
REGS["TCP_ADDR_CONFIG"]              = 0xAC14
REGS["TCP_CHAN_STEER_LO"]            = 0xAC0C
REGS["TCP_CHAN_STEER_HI"]            = 0xAC10

# SPI / shader dispatch
REGS["SPI_CONFIG_CNTL"]              = 0x9100
REGS["SPI_CONFIG_CNTL_1"]            = 0x913C
REGS["SX_DEBUG_1"]                   = 0x9060

# Shader memory config
REGS["SQ_CONFIG"]                    = 0x8C00
REGS["SH_MEM_CONFIG"]                = 0x8C34
REGS["SH_MEM_BASES"]                 = 0x8C28
REGS["SH_MEM_APE1_BASE"]             = 0x8C2C
REGS["SH_MEM_APE1_LIMIT"]            = 0x8C30

# CP
REGS["CP_ME_CNTL"]                   = 0x86D8
REGS["CP_RB0_CNTL"]                  = 0x8600
REGS["CP_RB0_BASE"]                  = 0x8040
REGS["CP_RB0_WPTR"]                  = 0x8610
REGS["CP_RB0_RPTR"]                  = 0x8700

# RLC / clock gating
REGS["RLC_CNTL"]                     = 0xC300
REGS["RLC_CGTT_MGCG_OVERRIDE"]       = 0xC400
REGS["RLC_CGCG_CGLS_CTRL"]           = 0xC404

# VGA
REGS["VGA_HDP_CONTROL"]              = 0x0328
REGS["VGA_RENDER_CONTROL"]           = 0x0300

# Tile modes (full table: GB_TILE_MODE0..31 at 0x9910 + n*4)
for i in range(32):
    REGS[f"GB_TILE_MODE{i}"]          = 0x9910 + i * 4

# Raster config
REGS["PA_SC_RASTER_CONFIG"]          = 0x28350  # context reg, may not read back
REGS["CGTS_SM_CTRL_REG"]             = 0x9150

# Scratch regs (canary — if these don't readback, MMIO is dead)
REGS["SCRATCH_REG0"]                 = 0x8500
REGS["SCRATCH_REG1"]                 = 0x8504
REGS["SCRATCH_UMSK"]                 = 0x8540

# ─── Main ─────────────────────────────────────────────────────────────────
label = "post-init" if len(sys.argv) > 1 and sys.argv[1] == "post" else "cold-boot"

print(f"╔══════════════════════════════════════════════════════════════════════╗")
print(f"║  GPU Register Probe — {label:>12s}                                  ║")
print(f"╚══════════════════════════════════════════════════════════════════════╝")

# Step 1: Read PCI command register on bus 2
cmd2 = pci_read_config(BUS2_DEV, 0x04, 2)
cmd1 = pci_read_config(BUS1_DEV, 0x04, 2)
print(f"\nPCI Command Register:")
print(f"  Bus 1: 0x{cmd1:04X}  Mem={'ON' if cmd1 & 2 else 'OFF'}  BusMaster={'ON' if cmd1 & 4 else 'OFF'}")
print(f"  Bus 2: 0x{cmd2:04X}  Mem={'ON' if cmd2 & 2 else 'OFF'}  BusMaster={'ON' if cmd2 & 4 else 'OFF'}")

# Enable Mem + BusMaster on bus 2 if needed
if not (cmd2 & 0x06):
    print(f"\n  >>> Enabling Mem+BusMaster on bus 2 (writing 0x{cmd2 | 0x06:04X})...")
    pci_write_config(BUS2_DEV, 0x04, cmd2 | 0x06, 2)
    cmd2_after = pci_read_config(BUS2_DEV, 0x04, 2)
    print(f"  >>> Bus 2 CMD now: 0x{cmd2_after:04X}  Mem={'ON' if cmd2_after & 2 else 'OFF'}  BusMaster={'ON' if cmd2_after & 4 else 'OFF'}")

# Step 2: Open MMIO on both
try:
    mm1 = open_mmio(BUS1_DEV)
except Exception as e:
    print(f"FATAL: Cannot open bus 1 MMIO: {e}")
    sys.exit(1)

try:
    mm2 = open_mmio(BUS2_DEV)
except Exception as e:
    print(f"FATAL: Cannot open bus 2 MMIO: {e}")
    sys.exit(1)

# Step 3: Quick sanity check — is bus 2 actually responding?
test1 = rd32(mm1, 0x8010)  # GRBM_STATUS
test2 = rd32(mm2, 0x8010)  # GRBM_STATUS
print(f"\nSanity: GRBM_STATUS bus1=0x{test1:08X} bus2=0x{test2:08X}")
if test2 == 0xFFFFFFFF:
    print("  *** Bus 2 still reads 0xFFFFFFFF — card not responding to MMIO")
    print("  *** This is expected at cold boot (no VBIOS POST)")
    print("  *** Run your test binary first, then re-run with: python3 gpu_probe_fullstate.py post")

# Step 4: Dump all registers
print(f"\n{'Register':<30s}  {'Bus1 (POSTed)':>14s}  {'Bus2':>14s}  {'Match'}")
print("─" * 80)

diffs = []
matches = []
dead_bus2 = 0

# Sort by register address for logical grouping
for name, off in sorted(REGS.items(), key=lambda x: x[1]):
    v1 = rd32(mm1, off)
    v2 = rd32(mm2, off)
    if v1 == v2:
        mark = "  =="
        matches.append((name, off, v1, v2))
    else:
        mark = "  !! DIFF"
        diffs.append((name, off, v1, v2))
    if v2 == 0xFFFFFFFF:
        dead_bus2 += 1
    print(f"{name:<30s}  0x{v1:08X}      0x{v2:08X}    {mark}")

mm1.close()
mm2.close()

# Step 5: Summary
print(f"\n{'═' * 80}")
print(f"SUMMARY: {len(diffs)} diffs, {len(matches)} matches out of {len(REGS)} registers")
print(f"Bus 2 registers reading 0xFFFFFFFF: {dead_bus2}/{len(REGS)}")

if dead_bus2 > len(REGS) * 0.8:
    print(f"\n*** Bus 2 is DARK — {dead_bus2} of {len(REGS)} regs read 0xFFFFFFFF.")
    print("*** The card hasn't been POSTed. ASIC_INIT hasn't run yet.")
    print("*** To see what ASIC_INIT configures:")
    print("***   1. Run your test binary (it calls AtomExec_AsicInit)")
    print("***   2. Re-run: python3 gpu_probe_fullstate.py post")
else:
    print(f"\nRegisters that DIFFER (need to match bus 1 for compute to work):")
    print(f"{'─' * 80}")
    for name, off, v1, v2 in diffs:
        print(f"  {name:<28s} (0x{off:04X})  bus1=0x{v1:08X}  bus2=0x{v2:08X}")

    # Flag the critical address routing registers specifically
    critical = ["GB_ADDR_CONFIG", "TCP_ADDR_CONFIG", "TCP_CHAN_STEER_LO",
                "TCP_CHAN_STEER_HI", "HDP_ADDR_CONFIG", "DMIF_ADDR_CONFIG",
                "MC_ARB_RAMCFG", "MC_SHARED_CHMAP", "MC_VM_FB_LOCATION",
                "DMA_TILING_CONFIG"]
    crit_diffs = [(n, o, v1, v2) for n, o, v1, v2 in diffs if n in critical]
    if crit_diffs:
        print(f"\n*** CRITICAL ADDRESS ROUTING DIFFERENCES (cause of data corruption):")
        for name, off, v1, v2 in crit_diffs:
            print(f"  *** {name:<24s} bus1=0x{v1:08X}  bus2=0x{v2:08X}")

print()
