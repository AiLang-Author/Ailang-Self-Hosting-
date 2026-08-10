# Claude GPU Driver Context — AMD GCN 1.0 (Southern Islands)

## Project Overview

This is an AMD GPU driver written entirely in AILang, targeting Cape Verde (HD 7770) GCN 1.0 compute GPUs. It's a test of whether an AI system (Claude) can write a GPU driver in a novel language (AILang). The driver runs in userspace via sysfs PCI resource files (`/sys/bus/pci/devices/*/resource2` for MMIO, `resource0` for VRAM).

**No kernel driver manages this GPU.** Both `radeon` and `amdgpu` are blacklisted via `/etc/modprobe.d/blacklist-radeon.conf`. `amdgpu` also refuses SI chips without `amdgpu.si_support=1`. The AILang driver must handle everything from cold-start.

**Goal:** The only complete GCN (then RDNA) driver stack outside AMD. After DPM is fully working, revisit compute, then graphics runtime.

## Hardware

- **Card:** AMD Cape Verde XT (Radeon HD 7770 / R7 250X), PCI device 1002:683d
- **Architecture:** GCN 1.0 (Southern Islands), gfx600
- **CUs:** 10, SPs: 640
- **VRAM:** ~1GB GDDR5
- **PCI Topology:**
  - Bridge `00:02.0` → bus 01 → **Display GPU** (01:00.0) — DO NOT TOUCH
  - Bridge `00:03.0` → bus 02 → **Compute GPU** (02:00.0) — our target
  - Both are Cape Verde cards

### PCI BARs (Compute GPU 02:00.0)
- BAR0: `0xB0000000` (256MB, VRAM aperture) → sysfs `resource0`
- BAR2: `0xFE900000` (256KB, MMIO registers) → sysfs `resource2`
- BAR4: `0xD000` (256 bytes, I/O ports) → sysfs `resource4`
- ROM:  `0xFE940000` (128KB, VBIOS)

### Key MMIO Register Addresses (verified against Linux kernel `sid.h`)
```
# GFX / System domain — always alive
GRBM_STATUS           = 0x8010
SRBM_STATUS           = 0x0E50
CONFIG_MEMSIZE        = 0x5428
MC_VM_FB_LOCATION     = 0x2024
HDP_NONSURFACE_BASE   = 0x2C04

# Clock Generation (CG) domain — dies after GRBM soft reset
CG_SPLL_FUNC_CNTL    = 0x0600
CG_SPLL_FUNC_CNTL_2  = 0x0604
CG_SPLL_FUNC_CNTL_3  = 0x0608
CG_SPLL_FUNC_CNTL_4  = 0x060C
CG_SPLL_SPREAD_SPEC   = 0x0620
CG_SPLL_SPREAD_SPEC_2 = 0x0624
GENERAL_PWRMGT        = 0x0C00 (approx — verify in DPMReg pool)
SCLK_PWRMGT_CNTL      = (check DPMReg pool)

# SMC Indirect Access (direct MMIO, kernel confirmed)
SMC_IND_INDEX_0       = 0x0200  (write SMC/SRAM address here)
SMC_IND_DATA_0        = 0x0204  (read/write SMC/SRAM data here)
SMC_IND_INDEX_1       = 0x0208
SMC_IND_DATA_1        = 0x020C
SMC_IND_ACCESS_CNTL   = 0x0228  (bit 0 = AUTO_INCREMENT)
SMC_MESSAGE_0         = 0x022C  (write PPSMC command)
SMC_RESP_0            = 0x0230  (read response: 1=OK, 0xFF=fail)
SMC_SCRATCH0          = 0x0884

# SMC Internal (via IND_INDEX_0/IND_DATA_0, addresses >= 0x80000000)
SMC_SYSCON_RESET_CNTL   = 0x80000000  (bit 0 = RST_REG)
SMC_SYSCON_CLOCK_CNTL_0 = 0x80000004  (bit 0 = CK_DISABLE, bit 24 = CKEN)
SMC_SYSCON_MISC_CNTL    = 0x80000010

# SMC SRAM (via IND_INDEX_0/IND_DATA_0, addresses 0x00000-0x20000)
SI_UCODE_START        = 0x10000  (firmware loads here)
SRAM_END              = 0x20000  (128KB total)
BOOTSTRAP_INST        = 0x0E004040  (Thumb branch at addr 0)
```

## CRITICAL FINDINGS (Hard-won lessons)

### 1. SMC Indirect Registers ALWAYS Read as 0 from Userspace
**Reads** from IND_INDEX_0, IND_DATA_0, IND_ACCESS_CNTL through userspace sysfs mmap ALWAYS return 0. This is NOT a bug — it's how the hardware behaves with userspace MMIO.

**Writes** DO work through the same path. Evidence:
- SMC firmware uploads successfully (no read verification needed)
- SMC starts and responds to PPSMC messages
- RESP_0 (0x230) DOES return non-zero (1=success) when SMC processes messages
- Level 0 DPM force succeeded via SendMessage

**Implication:** Never rely on SRAM readback for verification. Verify SMC operations by checking RESP_0 after SendMessage.

### 2. GRBM Soft Reset Kills the CG Domain PERMANENTLY
The `reset_gpu.ailang` tool uses GRBM_SOFT_RESET mask 0xDDFB + SRBM mask 0x300. After this reset:
- All CG/SPLL registers (0x600+) read as 0 AND writes don't stick
- All SMC registers (0x200+) become unresponsive
- SMC_SCRATCH0 (0x884) becomes unresponsive
- GFX domain (GRBM_STATUS) and MC domain continue working
- **Recovery requires full system reboot** (VBIOS POST)
- D3hot→D0, bridge reset, PCI remove/rescan — NONE of these fix it
- amdgpu bind fails with I/O error on SI chips

**DO NOT use reset_gpu.x in its current form.** It bricks the card until reboot.

### 3. SPLL State After VBIOS POST (healthy card)
```
CG_SPLL_FUNC_CNTL_3: 0x100ED097
GENERAL_PWRMGT:       0x00000000
SCLK_PWRMGT_CNTL:    0x000F3803
SPLL_STATUS:          0x00700202  (SPLL locked and running)
```

### 4. AtomBIOS Execution
- VBIOS loaded from sysfs ROM (`/sys/bus/pci/devices/.../rom`)
- AtomExec_AsicInit sets up SPLL/clocks — requires SPLL to be in bypass or running
- If SPLL is completely zeroed (post-soft-reset), AtomExec_AsicInit fails ("Stuck in loop")
- When SPLL is healthy (VBIOS POST state), AsicInit succeeds and locks the PLL

### 5. DPM State Machine
The DPM enable sequence:
1. Parse PowerPlay table from VBIOS → clock entries + states
2. Parse Voltage Object table → GPIO voltage entries + leakage
3. Stop SMC, reset, load firmware (VERDE_smc.bin), start SMC
4. Read FW header from SRAM for table addresses (state_tbl, soft_regs, mc_arb, spll)
5. Build state table in host memory (initialState, driverState, SPLL div table, MC ARB)
6. Upload to SMC SRAM, fix header DWORD
7. Start SMC, send SwitchToSwState message
8. For runtime level changes: stop SMC, upload new driverState, restart, send messages

**Current DPM status:**
- Steps 1-7 work (when card is healthy)
- SwitchToSwState succeeds (RESP_0 returns 1)
- Level 0 force succeeds
- **Level 1+ transitions hang** — root cause identified (see finding #9 below)

### 9. DPM Level 1+ Hang — Root Cause: SPLL Div Table Misalignment

**THE blocking bug.** The SMC firmware uses a 256-entry SPLL_DIV_TABLE for fast clock transitions. Each entry covers one index at 512 × 10kHz = 5.12 MHz granularity. When the SMC transitions to a new DPM level, it looks up the SCLK_VALUE from the HWLevel structure, divides by 512 to get a div table index, and reads the pre-computed FBDIV/PDIV from that entry.

**The problem:** PowerPlay SCLK values (e.g., 30000 for 300 MHz) are NOT multiples of 512.
- 30000 / 512 = 58.59 → fractional index, no valid entry
- The SMC gets garbage divider values → SPLL can't lock → firmware hangs waiting for lock → RESP_0 never returns

**Where it lives in code:**
- `DPM_SI_PopulateLevel` (line 443): stores raw `sclk_10k` from PowerPlay into `HWLevel.SCLK_VALUE`
- `DPM_SI_InitSPLLDivTable` (line 1304): builds table at `i * 512` steps — entries only exist at exact multiples of 512

**Fix required:** Round each level's SCLK_VALUE to the nearest multiple of 512 before storing in HWLevel. This means the actual clock will be quantized to 5.12 MHz steps (e.g., 300 MHz → 299.008 MHz or 304.128 MHz). This is what the kernel does implicitly via `radeon_atom_get_clock_dividers()` which returns quantized values.

### 6. DPM Fixes Applied (cumulative)
1. **Bootstrap re-write:** si_program_jump_on_start before every SMC restart
2. **Single-level driverState init:** Upload with 1 level initially, multi-level at runtime (matches kernel)
3. **aT=0 for level 0:** First level must have zero activity threshold when multi-level
4. **Runtime transition:** Halt SMC → upload new driverState → FlushDataCache → Resume → SwitchToSwState
5. **SPLL div table alignment:** SCLK_VALUE rounded to nearest multiple of 512 (5120 kHz steps) in `DPM_SI_ComputeSPLL`. Verified: all levels show remainder=0.
6. **DPM_SI_Disable full teardown:** 7-step sequence matching kernel's `si_dpm_disable()`: disable auto throttle → stop DPM → disable SCLK control → set RESET_TO_DEFAULTS → halt SMC → stop SMC → wait inactive.
7. **PCI Bridge Subordinate Reset:** `GPU_BAR_BridgeReset` auto-discovers parent bridge by scanning bus 0 PCI config, writes `1` to `reset_subordinate` sysfs file. Recovers dead CG domain without system reboot. (Requires root permissions on `reset_subordinate`.)
8. **SRAM loopback test removed:** Extra SMC stop/start cycle between firmware load and DPM enable destabilized the SMC. The kernel never does this.
9. **SMC timeout doubled:** 5M → 10M iterations (~2s) in `SMC_SI_SendMessage`. Kernel's SI-specific patches note that `SetForcedLevels`, `SetEnabledLevels`, `SwitchToSwState` are "especially slow" on SI.
10. **MCLK pinned to boot clock:** All DPM levels now store `boot_mclk` instead of PowerPlay's `pp_mclk`. We don't do MCLK DPM and MPLL shadow registers (HWLevel offsets 0x2C-0x4C) are not populated, so any MCLK change would hang the SMC trying to reprogram MPLL with zeros.
11. **Leakage voltage ID resolution + monotonic enforcement:** `Volt_ResolveLeakageVDDC(gpu, pp_vddc)` is now called on every PP voltage before level building. Monotonic ordering enforced: each level's VDDC ≥ previous level's VDDC (matching kernel's `si_apply_state_adjust_rules`).
12. **Level sorting by ascending SCLK:** Bubble sort on parallel arrays (sclk, mclk, vddc, vddci) after PP entry collection. Level 0 (boot) stays fixed, levels 1..N-1 sorted. Required for correct Force HIGH/LOW targeting and SMC auto-throttle.

### 8. Hard System Hang (Jun 15, 2026)
After DPM clock adjustment work, the system hard-locked (frozen screen, no keyboard, required power cycle). dmesg from the crash boot captured nothing — the kernel log just stops dead. The journal was corrupted (`uncleanly shut down`). No oops, no MCE, no watchdog output — consistent with a PCI bus stall where a CPU MMIO access never completes.

**Root cause:** Not conclusively determined, but the shared PCI root complex means a hung MMIO transaction on the compute GPU (02:00.0) can stall any CPU access to the display GPU (01:00.0) BAR, freezing `simpledrm` and the entire system.

**Fix applied:** Added display GPU lockout guards to `Library.AMDGPUBAR.ailang`. The following functions now refuse to operate on PCI bus 1 (the display GPU):
- `GPU_BAR_Enable()` — won't enable PCI memory/bus-master
- `GPU_BAR_MapMMIO()` — won't mmap MMIO BAR2
- `GPU_BAR_MapVRAM()` — won't mmap VRAM BAR0
- `GPU_BAR_Unbind()` — won't unbind kernel driver
- `GPU_BAR_Reset()` — won't trigger PCI FLR
- `GPU_BAR_BridgeReset()` — won't bridge-reset display GPU

New helper: `GPU_BAR_IsDisplayGPU(index)` returns 1 if PCI bus matches `GPUBarLockout.DISPLAY_BUS` (bus 1). Guard is at the library level — no application code can bypass it.

### 9. SPLL Div Table Alignment — VERIFIED FIXED

**Was THE blocking bug for DPM Level 1+ hangs (partially).** The SMC firmware uses a 256-entry SPLL_DIV_TABLE for fast clock transitions. Each entry covers one index at 512 × 10kHz = 5.12 MHz granularity. PowerPlay SCLK values (e.g., 30000 for 300 MHz) were NOT multiples of 512.

**Fix:** Round `sclk_khz` at the top of `DPM_SI_ComputeSPLL` to nearest multiple of 5120 kHz. This ensures FBDIV is computed for the rounded frequency and SCLK_VALUE stored in HWLevel is an exact multiple of 512.

**Verified:** All 3 DPM levels show `remainder=0` in alignment diagnostics.

### 10. DPM Level Transitions — FULLY WORKING (Jun 16, 2026)

DPM SCLK scaling fully operational across 4 levels: 302 → 399 → 501 → 1049 MHz. All SMC messages succeed, all PLL transitions complete, full HIGH/LOW/AUTO cycle works.

**Root cause of previous hang:** MCLK values differed between DPM levels. Level 0 stored `boot_mclk` (14900 = 149 MHz) while Level 1+ stored `pp_mclk` from PowerPlay (112500 = 1125 MHz). The SMC attempted MPLL reprogramming with all-zero shadow registers → memory controller death → SMC hang.

**Fixes applied (session 23):**
1. **MCLK pinned to boot_mclk** (Fix #10) — Prevents MPLL reprogramming since we don't do MCLK DPM.
2. **Leakage voltage ID resolution** (Fix #11) — `Volt_ResolveLeakageVDDC()` + monotonic voltage enforcement.
3. **Level sorting** (Fix #12) — Bubble sort by ascending SCLK after PP entry collection.

**Verified output:**
```
Force HIGH → SPLL_FUNC_CNTL_3: 0x1009B7F0 (1049 MHz)  resp=0x1
Force LOW  → SPLL_FUNC_CNTL_3: 0x100B302A (302 MHz)   resp=0x1
AUTO       → SetEnabledLevels(4) resp=0x1
DPM disabled (full teardown) → clean
```

### 11. Grok Incident (Jun 15, 2026)

Grok (another AI model) executed `modprobe` commands without user permission, which locked up the PC and required a forced reboot. The `radeon` blacklist in `/etc/modprobe.d/` was lost. Both `radeon` and `amdgpu` have been re-blacklisted via `/etc/modprobe.d/blacklist-radeon.conf`.

### 12. Secondary Issues (not blocking, but need fixing later)

**ACIndex = 0 for all levels** — In `DPM_SI_PopulateLevel` (line 761), byte 0 of the HWLevel (AC_INDEX) is always 0. This means all DPM levels reference the same voltage lookup in the SMC's AC register table. For SCLK-only DPM with fixed voltage this works, but for proper per-level voltage scaling, each level needs its own ACIndex.

**MC ARB timing — same for all levels** — `DPM_SI_ProgramMCArbTimingTable` (line 1526) copies boot DRAM timing to all entries. This is correct for SCLK-only DPM (MCLK doesn't change), but will need per-level timing when MCLK DPM is added.

**aT (activity threshold)** — Already fixed. `PopulateLevel` sets `aT = 0xFFFF` (CG_R=0xFFFF, CG_L=0), and level 0 gets overwritten to 0 in the driverState builder (line 1265). Matches kernel behavior.

### 7. AILang Syntax Gotchas
- **No `break` in WhileLoop** — must restructure loops to avoid break
- **`LessEqual` not `LessThanOrEqual`** — AILang comparison operators
- **`StoreValue` defaults to 64-bit** — use `StoreValue(..., "dword")` for 32-bit MMIO writes
- **`Dereference` defaults to 64-bit** — use `Dereference(..., "dword")` for 32-bit MMIO reads

## File Inventory

### Driver Libraries (`Librarys/Drivers/AMDGPU/`)

| File | Purpose |
|------|---------|
| Library.AMDGPUBAR.ailang | BAR mmap, GPU_Rd32/Wr32, PCI config save/restore, driver unbind, bridge reset recovery |
| Library.AMDGPUDiscover.ailang | PCI sysfs enumeration, GPU_Discover(), GPU_PrintAll() |
| Library.AMDGPUFamily.ailang | PCI ID → chip/gen/ISA identification from JSON database |
| Library.AMDGPUAtomBIOS.ailang | VBIOS ROM parser (headers, FirmwareInfo, VRAM usage) |
| Library.AMDGPUAtomExec.ailang | AtomBIOS interpreter main loop |
| Library.AMDGPUAtomExecDecode.ailang | AtomBIOS instruction decoder |
| Library.AMDGPUAtomExecOps.ailang | AtomBIOS opcode implementations |
| Library.AMDGPUAtomExecIO.ailang | AtomBIOS I/O port and register access |
| Library.AMDGPUAtomExecRun.ailang | AtomBIOS script runner (AsicInit entry point) |
| Library.AMDGPUPowerPlay.ailang | PowerPlay table parser (clock entries, states) |
| Library.AMDGPUVoltage.ailang | Voltage Object Table parser (GPIO, leakage) |
| Library.AMDGPUDisplay.ailang | DCE 6.x CRTC pipe control (active detection, blanking) |
| Library.AMDGPUPM4Regs.ailang | All SIReg, GRBMResetBits, SRBMResetBits, SPLLBits, etc. |
| Library.AMDGPUSMCRegs.ailang | SMCReg, SMCSyscon, SMCAccessBits, DPMReg, PPSMC messages |
| Library.AMDGPUSMC.ailang | SMC dispatch layer (routes to SI backend) |
| Library.AMDGPUSMC_SI.ailang | SI SMC: firmware load, start/stop, SRAM access, message protocol |
| Library.AMDGPUDPM.ailang | DPM dispatch layer (routes to SI backend) |
| Library.AMDGPUDPM_SI.ailang | SI DPM: state table build, SPLL computation, voltage, enable/disable |
| Library.AMDGPUPM4.ailang | Meta-import for all PM4 sub-libraries |
| Library.AMDGPUPM4Ring.ailang | Ring buffer setup, RPTR/WPTR, emit/commit |
| Library.AMDGPUPM4FW.ailang | CP/RLC firmware loading, IH ring, soft reset |
| Library.AMDGPUPM4Pkt.ailang | PM4 packet builders, ring idle/reset |
| Library.AMDGPUPM4Dispatch.ailang | Compute dispatch, fencing, CP start |
| Library.GCNEnc.ailang | GCN 1.0 instruction encoder (528 instructions) |

### Test Programs (`TestCode/`)

| File | Purpose |
|------|---------|
| test_dpm_enable.ailang | Full DPM enable test with level transitions |
| test_smc_indirect.ailang | SMC indirect register diagnostic |
| test_raw_mmio.ailang | Raw MMIO bypass test (no library code) |
| pci_bar_restore.ailang | Standalone BAR restore from sysfs resource file |
| reset_gpu.ailang | GPU soft reset — **BROKEN, kills CG domain** |
| test_gpu_discover.ailang | GPU PCI discovery test |
| test_gpu_bar.ailang | BAR mapping test |
| test_gpu_atombios.ailang | AtomBIOS parsing test |
| test_gpu_pm4.ailang | PM4 ring buffer / compute dispatch test |

## SMC State Table Layout (SI)

The SMC state table is uploaded to SRAM at the address from the firmware header. Layout:

```
Offset  Size   Field
0x000   1      THERMAL_PROTECT
0x001   1      SYSTEM_FLAGS (bit0=GPIO_DC, bit1=STEPVDDC, bit2=GDDR5)
0x002   1      MAX_VDDC_IDX
0x003   1      EXTRA_FLAGS
0x004   128    LOW_SMIO[32] (u32 array)
0x084   16     VOLT_MASK_TBL
0x094   16     PHASE_MASK_TBL
0x0A4   20     DPM2_PARAMS
0x0B8   152    INITIAL_STATE (SWSTATE: 4-byte header + 1 HWLevel)
0x150   152    ACPI_STATE
0x1E8   152    ULV_STATE
0x280   4+N*148 DRIVER_STATE (header + N performance levels)
```

### HWLevel Structure (148 bytes each)
```
Offset  Size  Field
0x00    4     first_dw (AC_INDEX, DISPLAY_WM, GEN2_PCIE flags)
0x04    4     SCLK_VALUE (engine clock in 10kHz units, byte-swapped)
0x08    4     VDDC voltage setting
0x0C    4     FUNC_CNTL (SPLL register value, must preserve bit 31)
0x10    4     FUNC_CNTL_2
0x14    4     FUNC_CNTL_3
0x18    4     FUNC_CNTL_4
0x1C    4     SPREAD_SPECTRUM
0x20    4     SPREAD_SPECTRUM_2
0x24    4     aT (activity threshold — must be 0 for level 0)
... (more fields through offset 0x94)
```

## SMC Firmware

- File: `/lib/firmware/radeon/VERDE_smc.bin`
- Size: 60388 bytes (15097 DWORDs)
- Upload address: 0x10000 (SI_UCODE_START)
- Bootstrap: Write 0x0E004040 to SRAM address 0 before each start
- Byte order: firmware file is big-endian, must byte-swap to LE for GPU_Wr32 (hardware swaps LE→BE in SRAM)

## PPSMC Messages Used

```
SwitchToSwState     = 0x40 (transition to software-controlled DPM state)
NoForcedLevel       = 0x41 (release forced level, allow automatic switching)
ForceLevel_0        = 0x46
ForceLevel_1        = 0x47
ForceLevel_2        = 0x48
NoDisplay           = 0x5D (indicate no display connected — for compute GPU)
```

## GPU Reset States

### Healthy (after VBIOS POST at boot)
```
GRBM_STATUS:           0x3028         (GUI active, various blocks idle)
SRBM_STATUS:           0x200000C0     (IH_BUSY, SEM_BUSY, bit29)
CG_SPLL_FUNC_CNTL_3:  0x100ED097     (SPLL configured and locked)
SCLK_PWRMGT_CNTL:     0x000F3803     (power management active)
CONFIG_MEMSIZE:        0x400          (VRAM configured)
MC_VM_FB_LOCATION:     0xF43FF400     (MC configured)
```

### Dead (after GRBM soft reset)
```
GRBM_STATUS:           0x3028         (still alive!)
SRBM_STATUS:           0x200000C0     (still alive!)
CG_SPLL_FUNC_CNTL_*:  0x0            (CG domain dead)
SMC registers 0x200+:  0x0            (SMC domain dead)
SMC_SCRATCH0 0x884:    0x0            (SMC domain dead)
CONFIG_MEMSIZE:        0x400          (MC still alive)
GENERAL_PWRMGT:        0x0            (power management dead)
```

### What dies vs what survives after GRBM soft reset
- **Survives:** GFX (GRBM), System (SRBM), MC, HDP, some CGTS
- **Dies permanently:** CG/SPLL (0x600+), SMC (0x200+, 0x884), GENERAL_PWRMGT
- **Cannot recover without:** System reboot (VBIOS POST)

## Build & Run

```bash
# Build any test
./ailang.x TestCode/test_dpm_enable.ailang test_dpm_enable.x

# Run (needs video group for sysfs access)
sg video -c "./test_dpm_enable.x"

# Cannot run sudo — ask user to run privileged commands
```

## TODO / Next Steps

### Immediate (DPM Level 1+ fix)
1. ~~**Fix SPLL div table alignment**~~ — DONE. Verified all levels remainder=0.
2. **Fix SMC resume sequence** — Add `PPSMC_FlushDataCache` before `PPSMC_MSG_Resume` in test runtime state switch.
3. **Fix level forcing to match kernel** — Use kernel's HIGH mode: `SetEnabledLevels(all)` → `SetForcedLevels(1)`. Remove extra `NoForcedLevel` between force operations.
4. **Investigate voltage ordering** — Level 2 (501MHz) at 825mV vs Level 0/1 (302/399MHz) at 950mV. Lower voltage at higher clock is suspicious. May need leakage ID translation or VBIOS voltage lookup.
5. **Test DPM Level 1+ transition** — After fixes, rebuild and test. Verify RESP_0 returns 1 for SetForcedLevels.
6. **Full DPM lifecycle test** — Enable, all levels, disable, re-enable.

### Secondary (correctness)
7. **Fix ACIndex per level** — Each DPM level should reference its own AC register table entry for proper voltage lookup.
8. **Build CG/SPLL cold-init path** — so the driver can recover without kernel/reboot.
9. **Fix or replace reset_gpu.x** — current version permanently bricks the CG domain.
10. **Auto-discover GPUs** — Driver should mount all GPUs it supports on any bus, not hardcode bus numbers.

### Future (after DPM works)
11. **Revisit compute dispatch** — PM4 ring, shader execution with DPM-managed clocks.
12. **Graphics runtime** — DCE display engine, framebuffer, mode setting.
13. **MCLK DPM** — Per-level MC ARB timing, MPLL reprogramming.
14. **RDNA port** — Extend driver stack beyond GCN 1.0.

### DO NOT
- **DO NOT run `test_raw_mmio.x`** — hangs the card
- **DO NOT touch display GPU (01:00.0, bus 1)** — under any circumstances
- **DO NOT use `reset_gpu.x`** — permanently kills CG domain until reboot
- **DO NOT run modprobe** — both radeon and amdgpu are blacklisted intentionally

## Linux Kernel Reference Files

For verifying register addresses and sequences against the official driver:
```
/home/bob/linux/drivers/gpu/drm/radeon/sid.h          — SI register definitions
/home/bob/linux/drivers/gpu/drm/radeon/si_smc.c       — SI SMC implementation
/home/bob/linux/drivers/gpu/drm/radeon/si_dpm.c       — SI DPM implementation
/home/bob/linux/drivers/gpu/drm/radeon/si.c            — SI GPU init/startup
/home/bob/linux/drivers/gpu/drm/radeon/radeon.h        — RREG32_SMC macro (uses IND path)
/home/bob/linux/drivers/gpu/drm/radeon/ni.c            — tn_smc_rreg/wreg (IND implementation)
/home/bob/linux/drivers/gpu/drm/radeon/evergreen_reg.h — TN_SMC_IND_INDEX_0 = 0x200
```

## Session History (key events)

1. **Compute dispatch working** — PM4 ring, CP firmware, GCN shader execution verified
2. **DPM enable working** — PowerPlay + Voltage parsing, state table build, SMC firmware load
3. **DPM Level 0 force working** — PPSMC_ForceLevel_0 accepted
4. **DPM Level 1 force hangs** — SPLL changes frequency but SMC RESP_0 times out
5. **SMC crash → SRAM loopback test added** — but reads always return 0 (normal!)
6. **GRBM soft reset run** → **CG domain permanently killed**
7. **Multiple recovery attempts failed** — D3hot, bridge reset, PCI rescan, amdgpu bind
8. **Root cause identified** — SRAM reads from userspace always return 0; CG domain death is separate from SRAM issue
9. **Hard system hang during DPM clock work** → system froze solid, required power cycle. No crash data captured.
10. **Display GPU lockout added** — `Library.AMDGPUBAR.ailang` now refuses all operations on PCI bus 1 (01:00.0)
11. **Grok modprobe incident** — Grok ran modprobe without permission, locked up PC, forced reboot. Radeon blacklist lost.
12. **Root cause analysis complete** — SPLL div table alignment identified as THE blocking bug for DPM Level 1+ hangs. Confirmed via code analysis + Gemini cross-check.
13. **Blacklists restored** — Both `radeon` and `amdgpu` re-blacklisted in `/etc/modprobe.d/blacklist-radeon.conf`
14. **Card state: healthy** — Freshly rebooted, VBIOS POST state, no driver bound, ready for AILang driver
15. **SPLL div table fix applied and verified** — All 3 DPM levels show remainder=0. Level 0 force works.
16. **DPM_SI_Disable rewritten** — 7-step teardown matching kernel's `si_dpm_disable()`.
17. **GPU_BAR_BridgeReset added** — Auto-discovers parent PCI bridge, performs subordinate reset. Card recovery without reboot.
18. **SMC timeout doubled** — 5M → 10M iterations. Kernel patches confirm SI SMC messages need extended timeouts.
19. **SRAM loopback test removed** — Extra SMC stop/start destabilized firmware.
20. **Level 1 PLL transition observed** — SPLL_FUNC_CNTL_3 changes correctly, TARGET_PROFILE shows level 1, but SMC RESP_0 times out. SMC dead after timeout.
21. **Kernel comparison reveals missing FlushDataCache** — Kernel sends `PPSMC_FlushDataCache` before `Resume` in runtime state transitions. Our test skipped this.
22. **Level forcing protocol differs from kernel** — Our test sends `NoForcedLevel` + restricted `SetEnabledLevels`. Kernel HIGH mode sends `SetEnabledLevels(all)` + `SetForcedLevels(1)`.
23. **ROOT CAUSE: MCLK mismatch between levels** — Level 0 stored boot_mclk (14900), Level 1+ stored pp_mclk from PowerPlay (112500). SMC attempted MPLL reprogramming with all-zero shadow registers → memory controller death → SMC hang. Fixed by pinning all levels to boot_mclk.
24. **Leakage voltage resolution + monotonic ordering** — `Volt_ResolveLeakageVDDC()` now called on PP voltages. Monotonic VDDC enforced across levels.
25. **Level sorting by ascending SCLK** — Bubble sort on parallel arrays after PP collection. Levels now: 302 → 399 → 501 → 1049 MHz.
26. **DPM FULLY WORKING** — Force HIGH (1049MHz), Force LOW (302MHz), AUTO mode all return 0x1. Full enable/disable cycle clean. SCLK DPM milestone complete.
27. **VFIO passthrough testing regime planned** — test_gcn_accel causes hard system lockup (no logs, no oops, instant kernel death). QEMU + VFIO isolates the blast radius to the VM.

---

## VFIO/QEMU GPU Driver Testing Regime

### Problem

`test_gcn_accel` (PM4 compute dispatch) causes an unrecoverable hard system lockup. No kernel logs, no MCE, no watchdog — the CPU hangs on a PCI MMIO transaction and never returns. Because the compute GPU (02:00.0) and display GPU (01:00.0) share the same PCI root complex (RD990), a stalled MMIO on 02:00.0 can block all CPU access to 01:00.0, freezing `simpledrm` and the entire system instantly.

Running the driver inside a QEMU VM with VFIO PCI passthrough isolates this: the IOMMU contains the fault to the VM. If the GPU hangs, the VM dies — the host survives.

### Hardware Topology (for passthrough)

```
CPU:       AMD FX-8320 (Piledriver), AMD-V supported
Chipset:   RD990 (AMD-Vi / IOMMU capable)
Bridge 00:02.0 → bus 01 → Display GPU 01:00.0  [1002:683d]  ← DO NOT TOUCH
Bridge 00:03.0 → bus 02 → Compute GPU 02:00.0  [1002:683d]  ← passthrough target
                           HDMI Audio  02:00.1  [1002:aab0]  ← must pass through with GPU
```

Both functions on bus 02 (GPU + audio) will be in the same IOMMU group and must be passed through together.

### Step 1: Enable IOMMU (one-time, requires reboot)

Edit `/etc/default/grub`:

```
GRUB_DEFAULT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_TIMEOUT=0
GRUB_DISTRIBUTOR=`( . /etc/os-release; echo ${NAME:-Ubuntu} ) 2>/dev/null || echo Ubuntu`
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash amdgpu.si_support=0 radeon.si_support=0 modprobe.blacklist=radeon,amdgpu,snd_hda_codec_atihdmi amd_iommu=on iommu=pt"
GRUB_CMDLINE_LINUX=""
```

Only change: added `amd_iommu=on iommu=pt` to `GRUB_CMDLINE_LINUX_DEFAULT`.
- `amd_iommu=on` — enables the AMD-Vi IOMMU hardware
- `iommu=pt` — passthrough mode: only devices explicitly bound to VFIO get translated, everything else has direct access (no performance penalty for host devices)

Then:
```bash
sudo update-grub
sudo reboot
```

**Verify after reboot:**
```bash
dmesg | grep AMD-Vi          # should show "AMD-Vi: Found IOMMU" and "Interrupt remapping enabled"
ls /sys/kernel/iommu_groups/  # should have numbered directories
```

### Step 2: Install packages (if not already present)

```bash
sudo apt install ovmf qemu-system-x86
```

Both are likely already installed from the AILang OS QEMU setup.

### Step 3: Create the Driver Test environment

**Do NOT modify the AILang OS QEMU setup.** Copy the disk image and create a separate launcher.

```bash
mkdir -p /home/bob/DriverTest
cp /home/bob/buildroot/output/images/ailang_os.img /home/bob/DriverTest/driver_test.img
```

The AILang compiler and test sources live in `/home/bob/Ailang-Self-Hosting-/` on the host. They can be shared into the VM via SSH (scp over port 2223) or baked into the image. The driver test VM uses port 2223 to avoid colliding with the OS test VM on 2222.

### Step 4: Bind compute GPU to vfio-pci (before each test session)

Script: `/home/bob/DriverTest/bind_vfio.sh`

```bash
#!/bin/bash
# Bind compute GPU (02:00.0) + HDMI audio (02:00.1) to vfio-pci
# Run as root before launching the test VM
set -e

GPU="0000:02:00.0"
AUDIO="0000:02:00.1"
VENDOR_GPU="1002 683d"
VENDOR_AUDIO="1002 aab0"

# Load modules
modprobe vfio-pci

# Unbind from any current driver (should be none, but just in case)
for DEV in $GPU $AUDIO; do
    if [ -e "/sys/bus/pci/devices/$DEV/driver" ]; then
        echo "$DEV" > "/sys/bus/pci/devices/$DEV/driver/unbind"
    fi
done

# Bind to vfio-pci
echo "$VENDOR_GPU" > /sys/bus/pci/drivers/vfio-pci/new_id 2>/dev/null || true
echo "$VENDOR_AUDIO" > /sys/bus/pci/drivers/vfio-pci/new_id 2>/dev/null || true

# Verify
for DEV in $GPU $AUDIO; do
    DRIVER=$(readlink -f "/sys/bus/pci/devices/$DEV/driver" 2>/dev/null | xargs basename 2>/dev/null)
    if [ "$DRIVER" = "vfio-pci" ]; then
        echo "[OK] $DEV bound to vfio-pci"
    else
        echo "[FAIL] $DEV driver is: $DRIVER"
        exit 1
    fi
done
echo "Ready for passthrough."
```

**WARNING:** Both GPUs have the same PCI device ID (1002:683d). The `new_id` approach may grab BOTH cards. If IOMMU groups confirm they're separate, use the sysfs `driver_override` method instead:

```bash
# Safer per-device override (use this if new_id grabs both GPUs)
echo "vfio-pci" > /sys/bus/pci/devices/0000:02:00.0/driver_override
echo "vfio-pci" > /sys/bus/pci/devices/0000:02:00.1/driver_override
echo "0000:02:00.0" > /sys/bus/pci/drivers/vfio-pci/bind
echo "0000:02:00.1" > /sys/bus/pci/drivers/vfio-pci/bind
```

### Step 5: Launch the test VM

Script: `/home/bob/DriverTest/run_driver_test.sh`

```bash
#!/bin/bash
# QEMU VM with VFIO passthrough of compute GPU for driver testing
# Run as root (VFIO device access requires it)
set -e

IMAGES="/home/bob/DriverTest"
DISK_IMAGE="$IMAGES/driver_test.img"
OVMF_CODE="/usr/share/OVMF/OVMF_CODE_4M.fd"
OVMF_VARS="/usr/share/OVMF/OVMF_VARS_4M.fd"

# Verify VFIO is bound
for DEV in 0000:02:00.0 0000:02:00.1; do
    DRIVER=$(readlink -f "/sys/bus/pci/devices/$DEV/driver" 2>/dev/null | xargs basename 2>/dev/null)
    if [ "$DRIVER" != "vfio-pci" ]; then
        echo "ERROR: $DEV not bound to vfio-pci (is: $DRIVER)"
        echo "Run: sudo ./bind_vfio.sh"
        exit 1
    fi
done

exec qemu-system-x86_64 \
    -enable-kvm \
    -m 2G \
    -smp 2 \
    -drive if=pflash,format=raw,readonly=on,unit=0,file="$OVMF_CODE" \
    -drive if=pflash,format=raw,snapshot=on,unit=1,file="$OVMF_VARS" \
    -drive file="$DISK_IMAGE",format=raw,if=none,id=disk0 \
    -device virtio-blk-pci,drive=disk0 \
    -device virtio-vga,xres=1024,yres=768 \
    -device qemu-xhci -device usb-kbd -device usb-mouse \
    -device vfio-pci,host=02:00.0 \
    -device vfio-pci,host=02:00.1 \
    -nic user,model=virtio-net-pci,hostfwd=tcp::2223-:22 \
    -serial stdio \
    -display gtk
```

Key differences from the OS test VM:
- `-device vfio-pci,host=02:00.0` — passes the real compute GPU into the VM
- Port 2223 for SSH (avoids collision with OS test VM on 2222)
- No `snapshot=on` for the disk — we want persistent test results
- `-serial stdio` — serial console in the terminal for crash debugging

### Step 6: Inside the VM — run tests

```bash
# SSH in from host
ssh -p 2223 root@localhost

# The compute GPU should appear in lspci inside the VM
lspci | grep Cape

# Build and run the test
cd /path/to/ailang
./ailang.x TestCode/test_gcn_accel.ailang test_gcn_accel.x
sg video -c "./test_gcn_accel.x"
```

If the test hangs the GPU:
- The VM freezes or crashes — **host stays alive**
- Kill the VM from host: `kill $(pgrep qemu-system)`
- The GPU may need a host-side reset: `echo 1 > /sys/bus/pci/devices/0000:02:00.0/reset`
- Rebind to vfio-pci and relaunch

### Step 7: Unbind after testing (return GPU to unbound state)

```bash
echo "0000:02:00.0" > /sys/bus/pci/drivers/vfio-pci/unbind
echo "0000:02:00.1" > /sys/bus/pci/drivers/vfio-pci/unbind
echo "" > /sys/bus/pci/devices/0000:02:00.0/driver_override
echo "" > /sys/bus/pci/devices/0000:02:00.1/driver_override
```

### Known Risks & Caveats

1. **Same PCI device ID on both GPUs** — Both are 1002:683d. Use `driver_override` (Step 4 safer method) to avoid accidentally grabbing the display GPU.
2. **IOMMU group granularity** — If the RD990 puts both bridges in one IOMMU group (unlikely but possible on older chipsets), passthrough won't isolate them properly. Verify with `ls /sys/kernel/iommu_groups/*/devices/` after enabling IOMMU.
3. **ACS support** — FX-8320 / RD990 may not have full ACS (Access Control Services). If IOMMU groups are too broad, the `pcie_acs_override=downstream,multifunction` kernel parameter is a last resort (reduces isolation guarantees but still better than bare metal testing).
4. **VM PCI bus numbering** — Inside the VM, the GPU won't be at 02:00.0. The AILang driver's `GPU_Discover()` should find it on whatever bus QEMU assigns. Verify with `lspci` inside the VM.
5. **sysfs permissions** — The VM runs its own kernel. sysfs PCI access inside the VM is native — no userspace mmap restrictions from the host apply.

### Quick Reference

```bash
# Full test cycle:
sudo ./bind_vfio.sh              # bind GPU to VFIO
sudo ./run_driver_test.sh        # launch VM with GPU passthrough
ssh -p 2223 root@localhost       # SSH into VM
# ... run tests ...
# If VM dies: kill qemu, reset GPU, rebind, relaunch
```
