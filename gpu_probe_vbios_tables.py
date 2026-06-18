#!/usr/bin/env python3
"""Dump all AtomBIOS command tables from the VBIOS ROM."""
import struct, sys

# Command table names from atombios.h ATOM_MASTER_LIST_OF_COMMAND_TABLES
CMD_NAMES = {
    0: "ASIC_Init",
    1: "GetDisplaySurfaceSize",
    2: "ASIC_RegistersInit",
    3: "VRAM_BlockVenderDetection",
    4: "DIGxEncoderControl",
    5: "MemoryControllerInit",
    6: "EnableCRTCMemReq",
    7: "MemoryParamAdjust",
    8: "DVOEncoderControl",
    9: "GPIOPinControl",
    10: "SetEngineClock",
    11: "SetMemoryClock",
    12: "SetPixelClock",
    13: "EnableDispPowerGating",
    14: "ResetMemoryDLL",
    15: "ResetMemoryDevice",
    16: "MemoryPLLInit",
    17: "AdjustDisplayPll",
    18: "AdjustMemoryController",
    19: "EnableASIC_StaticPwrMgt",
    20: "SetUniphyInstance",
    21: "DAC_LoadDetection",
    22: "LVTMAEncoderControl",
    23: "HW_Misc_Operation",
    24: "DAC1EncoderControl",
    25: "DAC2EncoderControl",
    26: "ProcessAuxChannelTransaction",
    27: "GetVoltageInfo",
    28: "TVEncoderControl/ASIC_StaticPwrMgtStatusChange",
}

rom_path = "/sys/bus/pci/devices/0000:02:00.0/rom"
try:
    with open(rom_path, "rb") as f:
        # Enable ROM read
        pass
except:
    pass

# Enable ROM reading
try:
    with open(rom_path, "wb") as f:
        f.write(b"1")
except PermissionError:
    print("Need root: sudo python3 gpu_probe_vbios_tables.py")
    sys.exit(1)

with open(rom_path, "rb") as f:
    rom = f.read()

# Disable ROM
with open(rom_path, "wb") as f:
    f.write(b"0")

print(f"ROM size: {len(rom)} bytes")
sig = struct.unpack_from('<H', rom, 0)[0]
print(f"Signature: 0x{sig:04X} ({'OK' if sig == 0xAA55 else 'BAD'})")

# ATOM header pointer at 0x48
atom_off = struct.unpack_from('<H', rom, 0x48)[0]
print(f"ATOM header at: 0x{atom_off:04X}")
magic = rom[atom_off+4:atom_off+8]
print(f"Magic: {magic} ({'OK' if magic == b'ATOM' else 'BAD'})")

# Master command table offset at atom_off + 30
cmd_tbl_off = struct.unpack_from('<H', rom, atom_off + 30)[0]
# Master data table offset at atom_off + 32
data_tbl_off = struct.unpack_from('<H', rom, atom_off + 32)[0]
print(f"Master command table at: 0x{cmd_tbl_off:04X}")
print(f"Master data table at:    0x{data_tbl_off:04X}")

# Command table: first 4 bytes are header (size u16, rev u8, rev u8)
# Then u16 offsets for each table
cmd_hdr_size = struct.unpack_from('<H', rom, cmd_tbl_off)[0]
n_cmds = (cmd_hdr_size - 4) // 2  # each entry is u16, header is 4 bytes
print(f"\nCommand table header size: {cmd_hdr_size}, entries: {n_cmds}")
print(f"\n{'Idx':>3}  {'Offset':>8}  {'Size':>6}  Name")
print("-" * 60)

for i in range(n_cmds):
    entry_off = cmd_tbl_off + 4 + i * 2
    tbl_off = struct.unpack_from('<H', rom, entry_off)[0]
    name = CMD_NAMES.get(i, f"(unknown_{i})")
    if tbl_off == 0:
        print(f"{i:3d}  {'---':>8}  {'---':>6}  {name}  [NOT PRESENT]")
    else:
        # Read table header to get size
        tbl_size = struct.unpack_from('<H', rom, tbl_off)[0]
        fmt_rev = rom[tbl_off + 2]
        cnt_rev = rom[tbl_off + 3]
        print(f"{i:3d}  0x{tbl_off:04X}  {tbl_size:5d}B  {name}  (rev {fmt_rev}.{cnt_rev})")

# Also dump data tables
print(f"\n{'Idx':>3}  {'Offset':>8}  {'Size':>6}  Data Table")
print("-" * 60)
DATA_NAMES = {
    0: "UtilityPipeLine",
    1: "MultimediaCapabilityInfo",
    2: "MultimediaConfigInfo",
    3: "StandardVESA_Timing",
    4: "FirmwareInfo",
    5: "PaletteData",
    6: "LCD_Info",
    7: "DIGTransmitterInfo",
    8: "SMU_Info/AnalogTV_Info",
    9: "SupportedDevicesInfo",
    10: "GPIO_I2C_Info",
    11: "VRAM_UsageByFirmware",
    12: "GPIO_Pin_LUT",
    13: "VESA_ToInternalModeLUT",
    14: "GFX_Info",
    15: "PowerPlayInfo",
    16: "GPUVirtualizationInfo/CompassionateData",
    17: "DisplayDeviceInfo/SaveRestoreInfo",
    18: "PPLL_SS_Info",
    19: "OemInfo",
    20: "XTMDS_Info",
    21: "MclkSS_Info",
    22: "Object_Header",
    23: "IndirectIOAccess",
    24: "MC_InitParameter",
    25: "ASIC_VDDC_Info",
    26: "ASIC_InternalSS_Info",
    27: "TV_VideoMode",
    28: "VRAM_Info",
    29: "MemoryTrainingInfo",
    30: "IntegratedSystemInfo",
    31: "ASIC_ProfilingInfo",
    32: "VoltageObjectInfo",
    33: "PowerSourceInfo",
    34: "ServiceInfo",
}

data_hdr_size = struct.unpack_from('<H', rom, data_tbl_off)[0]
n_data = (data_hdr_size - 4) // 2
for i in range(min(n_data, 40)):
    entry_off = data_tbl_off + 4 + i * 2
    tbl_off = struct.unpack_from('<H', rom, entry_off)[0]
    name = DATA_NAMES.get(i, f"(unknown_{i})")
    if tbl_off == 0:
        print(f"{i:3d}  {'---':>8}  {'---':>6}  {name}  [NOT PRESENT]")
    else:
        tbl_size = struct.unpack_from('<H', rom, tbl_off)[0]
        fmt_rev = rom[tbl_off + 2]
        cnt_rev = rom[tbl_off + 3]
        print(f"{i:3d}  0x{tbl_off:04X}  {tbl_size:5d}B  {name}  (rev {fmt_rev}.{cnt_rev})")
