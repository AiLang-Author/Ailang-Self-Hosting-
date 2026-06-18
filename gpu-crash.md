# GPU Driver Debug Log — Jun 16-18, 2026

## Tell Claude

"Read ~/Ailang-Self-Hosting-/gpu-crash.md before touching ANY GPU driver code."

---

## Platform

- **CPU/Chipset**: FX-8320 / RD990 — no AMD-Vi, VFIO impossible
- **GPUs**: Two Cape Verde (GCN 1.0, Southern Islands) sharing PCIe root complex
  - `01:00.0` = display GPU (BIOS VESA framebuffer, **no radeon driver**) — **NEVER TOUCH**
  - `02:00.0` = compute GPU (userspace AILang driver, radeon unbound)
- **Driver**: Entirely userspace AILang. Maps BARs via sysfs, writes registers via mmap'd MMIO
- **VRAM layout**: 64MB base (0x4000000): Rings 0-2, RLC SR/CS, IH ring, shader, buf desc, IB, DATA
- **DPM**: SMC-managed clock/voltage: boot 302 -> 399 -> 501 -> 1049 MHz
- **Dispatch**: PM4 ring buffer, IB with DISPATCH_DIRECT + CS_PARTIAL_FLUSH, double EOP fence
- **Known silicon bug**: Cape Verde compute event engine leaks dispatch slots after ~36 dispatches
- **Compute works on bus 1** — same test, same shader, passes all 64 results on the display GPU

## Register Domains

- **SRBM-routed** (always-on): CG_SPLL_*, SMC, RLC_CGTT_*, MC_VM_*, BIF_FB_EN — work on reference clock
- **GRBM-routed** (engine clock required): CP_ME_CNTL, GRBM_SOFT_RESET, CP firmware, SPI_*, SCRATCH_REG* — need SPLL locked first

---

## ABSOLUTE RULES — DO NOT VIOLATE

1. **NEVER write ANY HDP register from CPU or GPU side.** Every attempt has crashed the machine.
   Only exception: `HDP_MEM_COHERENCY_FLUSH_CNTL` (0x5480) = 1 for write-cache drain (different block, never crashed).
2. **NEVER run MC_SI_*, PM4_SoftResetCP, PM4_HaltCP, or AtomExec_AsicInit on the display GPU (bus 1).**
   All have display GPU guards. The BIOS already configured bus 1 correctly.
3. **NEVER run code on the GPU without probing first.** Use `gpu_probe_fullstate.py` to see actual register state.
4. **Trust the radeon probe, not raw BIOS POST.** The "bus 1 BIOS POST" probe was taken
   before radeon loaded — those were ROM power-on defaults, not working values. Radeon
   overwrites them with correct kernel values. Use `probe_after_radeon_unbind.txt` as
   the reference for working register state.
5. **Use kernel/radeon values for ALL programmable registers** (VM/TLB, golden registers,
   clock gating, address config). Only exception: HDP registers — never write them
   (crash the RD990). Tile mode table uses ROM defaults (matches kernel anyway).

### HDP registers that CRASH the machine (0x2C00 range):

| Register | Offset | Status |
|---|---|---|
| `HDP_HOST_PATH_CNTL` | 0x2C00 | **NEVER WRITE** — CPU and GPU-side writes both deadlock RD990 |
| `HDP_NONSURFACE_BASE` | 0x2C04 | **NEVER WRITE** — removed from MC_SI_Program |
| `HDP_NONSURFACE_INFO` | 0x2C08 | **NEVER WRITE** — removed |
| `HDP_NONSURFACE_SIZE` | 0x2C0C | **NEVER WRITE** — removed |
| `HDP_MISC_CNTL` | 0x2F4C | **NEVER WRITE** — GPU-side WRITE_DATA also crashes |
| `HDP_ADDR_CONFIG` | 0x2F48 | **NEVER WRITE** — probe shows it already matches bus 1 |
| HDP protection buffers | 0x2C14+i*0x18 | **NEVER WRITE** — removed from MC_SI_Program and GpuInit |
| `HDP_MEM_COHERENCY_FLUSH_CNTL` | 0x5480 | **OK** — write-cache drain, different block, safe |

---

## Probe Results — Jun 18, 2026 (cold boot, PCI CMD enabled, BEFORE any driver init)

Tool: `python3 gpu_probe_fullstate.py`

**93 of 110 registers MATCH between bus 1 and bus 2 from VBIOS ROM defaults alone.**

All engine config, address routing, tile modes, TC pipeline, SPI, shader memory already correct:
- `GB_ADDR_CONFIG` == , `TCP_ADDR_CONFIG` == , `TCP_CHAN_STEER_LO/HI` ==
- All 32 `GB_TILE_MODE` entries == , `DMIF_ADDR_CONFIG` == , `HDP_ADDR_CONFIG` ==
- `PA_SC_RASTER_CONFIG` == , `SPI_CONFIG_CNTL_1` == , `SH_MEM_CONFIG` ==
- `SX_DEBUG_1` == , `GRBM_CNTL` == , `GRBM_STATUS` ==

**Only 17 registers differ — all MC/SPLL/BIF (memory controller not initialized):**

| Register | Bus 1 (POSTed) | Bus 2 (cold) | Meaning |
|---|---|---|---|
| `MC_VM_FB_LOCATION` | `0xF43FF400` | `0x00000000` | No VRAM aperture |
| `CONFIG_MEMSIZE` | `0x00000400` | `0x00000000` | Card doesn't know VRAM size |
| `MC_ARB_RAMCFG` | `0x0000025A` | `0x00007001` | MC arbiter not configured |
| `MC_SHARED_CHMAP` | `0x00002210` | `0x00000210` | Memory channel map wrong |
| `MC_SEQ_MISC0` | `0x500026A9` | `0x00000000` | MC sequencer not initialized |
| `MC_SEQ_TRAIN_WAKEUP_CNTL` | `0x000000E0` | `0x00000000` | VRAM not trained |
| `MC_SHARED_BLACKOUT_CNTL` | `0x00000000` | `0x00000001` | **MC in blackout mode** |
| `BIF_FB_EN` | `0x00000003` | `0x00000000` | CPU can't reach VRAM |
| `CG_SPLL_FUNC_CNTL` | `0x80400000` | `0x0020002D` | SPLL not configured |
| `CG_SPLL_FUNC_CNTL_3` | `0x100B1C70` | `0x10280000` | PLL params wrong |
| `CG_SPLL_FUNC_CNTL_4` | `0x80880047` | `0x00800000` | PLL params wrong |
| `CG_SPLL_SPREAD_SPECTRUM` | `0x00200000` | `0x00000000` | SS not configured |
| `HDP_HOST_PATH_CNTL` | `0x0F200029` | `0x0F00002F` | Slight HDP diff (DO NOT FIX) |
| `HDP_NONSURFACE_BASE` | `0xF4000000` | `0x00000000` | HDP base not set (DO NOT FIX) |
| `HDP_MISC_CNTL` | `0x00121FE0` | `0x00321FE1` | HDP mode diff (DO NOT FIX) |
| `VGA_RENDER_CONTROL` | `0x0201000F` | `0x0000000F` | VGA display (don't care) |
| `VGA_HDP_CONTROL` | `0x00000001` | `0x00000000` | VGA (don't care) |

---

## Post-Init Probe — Jun 18, 2026 (after ASIC_INIT + full driver init from clean boot)

After a **clean boot** (SPLL alive), ASIC_INIT succeeds and most registers align.
The probe after full init showed **21 diffs** (down from 32 before fixes).

### Registers that NOW match after fixes (were wrong before):

| Register | Old wrong value | Corrected to (bus 1) |
|---|---|---|
| `TCP_ADDR_CONFIG` | `0x3` (kernel) | `0xFB` (ROM) |
| `TCP_CHAN_STEER_LO` | `0x1032` (kernel) | `0x76543210` (ROM) |
| `TCP_CHAN_STEER_HI` | `0x0` (kernel) | `0xFEDCBA98` (ROM) |
| `TA_CNTL_AUX` | `bit 16 set` (kernel) | `0x0` (ROM) |
| `SPI_CONFIG_CNTL` | `0x03000000` (kernel) | `0x0` (ROM) |
| `SPI_CONFIG_CNTL_1` | `0x4` (kernel) | `0x01000100` (ROM) |
| `SX_DEBUG_1` | RMW pattern | `0x20` (ROM) |
| `DMIF_ADDR_CONFIG` | `0x12010002` (kernel) | `0x00011003` (bus 1) |
| `DMIF_ADDR_CALC` | `0x12010002` (kernel) | `0x0` (bus 1) |
| `RLC_CGTT_MGCG_OVERRIDE` | `0xFFFFFFFC` (kernel) | `0xFFFFFFFF` (bus 1) |
| `RLC_CGCG_CGLS_CTRL` | `0x0` (kernel) | `0x3` (bus 1) |
| `CGTS_SM_CTRL_REG` | `0x600000` (kernel) | `0x200` (bus 1) |
| `PA_SC_RASTER_CONFIG` | `0xA` (computed) | `0x2A00126A` (bus 1) |
| `HDP_HOST_PATH_CNTL` | was different | matches (ASIC_INIT fixed it) |
| `HDP_NONSURFACE_BASE/INFO/SIZE` | were different | match (ASIC_INIT fixed them) |
| `HDP_ADDR_CONFIG` | was different | matches |
| `HDP_MISC_CNTL` | was different | matches |
| `MC_VM_MX_L1_TLB_CNTL` | `0x18` (gart_disable) | ~~`0x503` (ROM default)~~ **now 0x055B (kernel)** |
| `VM_L2_CNTL` | `0xB8600` (gart_disable) | ~~`0x0C0B8E02` (ROM default)~~ **now 0x000B8603 (kernel)** |
| `VM_L2_CNTL3` | `0x100000` (gart_disable) | ~~`0x100004` (ROM default)~~ **now 0x00120004 (kernel)** |
| `VM_CONTEXT0_CNTL` | `0x0` (disabled) | ~~`0xFFFED8` (ROM default)~~ **now 0x11 (kernel)** |

### Remaining 21 diffs after clean boot + init:

**Expected diffs (different VRAM base, operational state — not bugs):**
- `MC_VM_FB_LOCATION` — bus1=0xF43FF400 (BIOS high), bus2=0x003F0000 (remapped to 0)
- `MC_VM_AGP_TOP/BOT`, `MC_VM_SYS_APE_HIGH` — different aperture layout
- `CP_ME_CNTL` — bus1=0x15000000 (halted), bus2=0x0 (running)
- `CP_RB0_RPTR` — bus1=0 (idle), bus2=0x11 (consumed ring test)
- `SCRATCH_UMSK`, `GRBM_CNTL` — bus2 has scratch enabled, different timeout
- `RLC_CNTL` — bus2=1 (RLC running)
- `VGA_RENDER_CONTROL`, `VGA_HDP_CONTROL` — display vs compute, don't care
- `GB_ADDR_CONFIG` — write-only, readback is power-on default not written value
- `SRBM_STATUS` — live status, varies

**Possibly relevant diffs:**
- `VM_L2_CNTL` — bus1=0x0C0B8E02, bus2=0x0C07FE02 (close, HW may mask some bits)
- `VM_INVALIDATE_RESPONSE` — bus2=1 (invalidation completed), bus1=0
- `MC_SEQ_MISC0` — bus1=0x500026A9, bus2=varies (MC sequencer state)

### Current symptom: dispatch stalls with TA_BUSY

- GRBM_STATUS = 0xA0003028: bit 29 GUI_ACTIVE, bit 13 TA_BUSY
- CP consumes ring test (RPTR=17=WPTR=17) — ring works
- CP partially consumes dispatch IB (RPTR=64 of WPTR=121) — then stalls
- Shader launches, issues buffer_load_dword, TA sends to TC, TC request hangs
- VRAM from CPU: first Wr32 reads back 0xFFFFFFFF, second Wr32 reads back correctly
- dst[] all 0xFFFFFFFF — shader never completed

---

## What ASIC_INIT Does

`AtomExec_AsicInit` (VBIOS command table 0) is the same code the motherboard BIOS runs during POST.
It chains through sub-tables and programs: SPLL, MC sequencer, VRAM training, PLL lock, and hundreds
of other registers.  After ASIC_INIT:

- SPLL should be configured and locked
- MC should be initialized with VRAM trained
- `CONFIG_MEMSIZE` should be non-zero
- `MC_VM_FB_LOCATION` should be set (ASIC_INIT uses `0xF43FF400` = VRAM at 0xF400000000)
- `BIF_FB_EN` should be enabled
- `MC_SHARED_BLACKOUT_CNTL` should be cleared

**After ASIC_INIT, the only thing MC_SI_Program needs to do is remap VRAM to base=0**
(our ring/dispatch code expects VRAM at offset 0, matching the display GPU layout).

---

## Current Init Sequence (Jun 18, 2026 — post-fix)

```
1.  GPU_Discover -> GPU_BAR_MapMMIO -> GPU_BAR_MapVRAM
2.  AtomBIOS_LoadROM -> Parse -> PP_Parse -> Volt_Parse
3.  DPM_SI_InitSPLL -> AtomExec_AsicInit (bus 2 only; bus 1 skips)
4.  MC_SI_Program (bus 2 only — remaps VRAM to base=0, NO HDP writes)
5.  PM4_HaltCP -> PM4_InitMCBase (reads MC_VM_FB_LOCATION only, no VM/TLB)
6.  PM4_SoftResetCP (bus 2 only, SRBM resets GRBM only — no HDP reset) -> PM4_HaltCP
7.  MC_SI_GpuInit (bus 2 only — golden regs, addr config, tile table, CP_MEQ fixed)
8.  PM4_ConfigureVM (NEW — VM/TLB + system aperture, AFTER soft reset)
9.  PM4_LoadCPFirmware -> PM4_LoadRLCFirmware -> PM4_SetupIHRing
10. PM4_SetupRing(0) -> PM4_CPStart -> PM4_RingTest(0)
11. PM4_SetupRing(1) -> PM4_RingTest(1)
12. PM4_SetupRing(2) -> PM4_RingTest(2)
13. SCRATCH_UMSK=0xFF, roundtrip check
14. SMC_LoadFirmware -> DPM_Init -> DPM_Enable -> Force HIGH
15. CIR_Begin -> build kernel -> CIR_Lower_GCN -> upload to VRAM
16. AccelGCN_Dispatch (PM4_SubmitCompute + fence wait + readback)
```

## Known Issues

1. **Card does not survive stalled dispatches.** A failed dispatch leaves TA_BUSY set, and
   subsequent runs find SPLL=0 (all SPLL registers zeroed). ASIC_INIT fails on a dead SPLL.
   Reboot required to recover. This is the #1 problem — we cannot iterate without rebooting.

2. **SMC message timeouts.** NoDisplay (0x5D), ForceHigh (0x82/0x83), and disable (0x84)
   all timeout. DPM may not be fully working. Unknown if this affects compute dispatch.

3. **First VRAM write reads back wrong.** `Wr32(0xDEADBEEF) -> Rd32=0xFFFFFFFF` but
   immediately after, `Wr32(0xCAFEBABE) -> Rd32=0xCAFEBABE`. Could be write-combine
   or cache coherency issue.

## Debug Plan

**Root cause identified (Jun 18): four bugs found by cross-referencing GCNinit.md against driver code.**
All four fixed. See "Critical Fixes — Jun 18" section below. Reboot and test required.

If dispatch still fails after these fixes:
1. Add debug prints for buffer descriptor GPU addresses vs system aperture range
2. Check SH_MEM_CONFIG / SH_MEM_BASES for VMID 0 compute context
3. Investigate first-VRAM-write-reads-back-0xFFFFFFFF issue (write-combine BAR?)

---

## Crash History (resolved — for reference only)

- **Crash #1** (Jun 16): GRBM writes before SPLL up. Fixed: moved SPLL init first.
- **Crash #2** (Jun 16): CPU-side `HDP_HOST_PATH_CNTL` write + WC BAR0. Fixed: removed all HDP writes, restored O_SYNC.
- **Crash #3** (Jun 17): `MC_SI_Program` on display GPU killed VESA. Fixed: display GPU guards.
- **Crash #4** (Jun 18): `PM4_SoftResetCP` on display GPU killed VESA. Fixed: display GPU guards.

## Committed Fixes (still relevant)

- **Fix #6**: AtomBIOS IIO opcode swap (MOVE_ATTR/MOVE_DATA) — correct VBIOS interpreter
- **Fix #7**: AtomBIOS delay timing (was 2-5x too short) — correct POST timing
- **Fix #11**: Always run ASIC_INIT on un-POSTed GPUs, skip on display GPU

## Register Value Corrections (Jun 18 — two rounds)

### Round 1 (early Jun 18): BIOS ROM values
Initially changed all golden registers from kernel values to bus 1 BIOS POST probe values.
This was based on Rule 5 ("never trust kernel source"), which turned out to be wrong.

### Round 2 (late Jun 18): Back to kernel/radeon values
After radeon probe comparison showed compute WORKS with kernel values, switched all
golden registers back to kernel/radeon probe values. Both MC_SI_GpuInit and
PM4_SoftResetCP Step 7 updated consistently.

**Registers switched to kernel/radeon values:**

| Register | BIOS ROM (was) | Kernel (now) | File(s) |
|---|---|---|---|
| RLC_CGTT_MGCG_OVERRIDE | 0xFFFFFFFF | 0xFFFFFFC0 | MC_SI, PM4FW |
| RLC_CGCG_CGLS_CTRL | 0x00000003 | 0x0020003C | MC_SI, PM4FW |
| CGTS_SM_CTRL_REG | 0x00000200 | 0x96941200 | MC_SI, PM4FW |
| TA_CNTL_AUX | 0x00000000 | 0x00010000 | MC_SI, PM4FW |
| TCP_ADDR_CONFIG | 0x000000FB | 0x00000003 | MC_SI, PM4FW |
| TCP_CHAN_STEER_LO | 0x76543210 | 0x00001032 | MC_SI, PM4FW |
| TCP_CHAN_STEER_HI | 0xFEDCBA98 | 0x00000000 | MC_SI, PM4FW |
| SPI_CONFIG_CNTL | 0x00000000 | 0x03000000 | MC_SI, PM4FW |
| SPI_CONFIG_CNTL_1 | 0x01000100 | 0x00000004 | MC_SI, PM4FW |
| DMIF_ADDR_CONFIG | 0x00011003 | 0x10010002 | MC_SI, PM4FW |
| DMIF_ADDR_CALC | 0x00000000 | 0x10000000 | MC_SI, PM4FW |
| PA_SC_RASTER_CONFIG | 0x2A00126A | 0x0000000A | MC_SI |

**Key lesson (revised):** Rule 5 was wrong. The "bus 1 BIOS POST" probe was taken before
radeon loaded — those were ROM power-on defaults, not working compute values. Radeon
overwrites them. For VM/TLB AND golden registers, kernel/radeon values are correct.
Only HDP registers are still untouchable (crash the RD990).

### Also fixed: System aperture calculation
MC_VM_SYSTEM_APERTURE_HIGH_ADDR was calculated as start of last 16MB block (0x3F000)
instead of last page (0x3FFFF). Fixed in PM4_ConfigureVM.

## Removed (Jun 18 — probe proved unnecessary)

- All HDP register writes (protection buffers, NONSURFACE, HOST_PATH_CNTL, MISC_CNTL, ADDR_CONFIG)
- GPU-side HDP WRITE_DATA in dispatch path (HDP_HOST_PATH_CNTL, HDP_MISC_CNTL)
- hdp_hpc_val / hdp_misc_val snapshots in PM4_InitMCBase
- si_pcie_gart_disable() VM/TLB pattern — replaced with kernel gart_enable values

---

## Test Command

```bash
cd ~/Ailang-Self-Hosting-
./ailang.x TestCode/test_accel_gcn.ailang test_accel_gcn.x
./test_accel_gcn.x
python3 gpu_probe_fullstate.py post    # run after test to see register state
```

---

## Radeon Bind Test (next reboot)

### Purpose
Bind the radeon kernel driver to see what register values it ACTUALLY programs on this
specific card. Three-way comparison: BIOS-only vs kernel-init vs our-init. Also tests
whether our dispatch works on a kernel-initialized card (skip ASIC_INIT, just set up rings).

### GRUB change (already applied for next boot)
In `/etc/default/grub`, changed:
```
# WAS:
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash amdgpu.si_support=0 radeon.si_support=0
modprobe.blacklist=radeon,amdgpu,snd_hda_codec_atihdmi iommu=pt"

# NOW:
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash amdgpu.si_support=0 modprobe.blacklist=amdgpu,snd_hda_codec_atihdmi iommu=pt"
```
Changes: removed `radeon.si_support=0`, removed `radeon` from blacklist.
Run `sudo update-grub` before rebooting.

### After reboot with radeon enabled

Radeon will grab BOTH GPUs on boot. Steps:

```bash
cd ~/Ailang-Self-Hosting-

# 1. Probe bus 1 with radeon managing it — see what kernel actually programs
python3 gpu_probe_fullstate.py > probe_with_radeon.txt

# 2. Unbind bus 2 from radeon so we can use it with our driver
sudo sh -c 'echo 0000:02:00.0 > /sys/bus/pci/drivers/radeon/unbind'

# 3. Probe bus 2 after radeon unbind — card is now kernel-initialized but unmanaged
python3 gpu_probe_fullstate.py > probe_after_radeon_unbind.txt

# 4. Run our test on bus 2 (kernel already initialized the card)
./test_accel_gcn.x

# 5. Probe after our test
python3 gpu_probe_fullstate.py post > probe_after_our_test.txt
```

### What we're looking for

1. **Does radeon change the BIOS values?** Compare probe_with_radeon.txt vs the cold-boot
   probe in this doc. If TCP_ADDR_CONFIG, SPI_CONFIG_CNTL_1, etc. change, the kernel
   really does stomp BIOS defaults.

2. **Does our dispatch work on a radeon-initialized card?** If step 4 passes, the problem
   is in our ASIC_INIT / MC init, not our dispatch path. If it fails, dispatch is broken
   independent of card init.

3. **What VM/TLB values does radeon actually use?** The kernel's si_pcie_gart_enable()
   sets up full GART page tables. See if those values differ from BIOS POST values.

### Step 1 Results — Radeon Probe (Jun 18, 2026)

Radeon grabbed both GPUs. Probe with radeon active: **only 10 diffs, 100 matches**.
Saved to `probe_with_radeon.txt`.

**Critical finding: Radeon uses Linux kernel values, NOT BIOS POST values.**
Both buses show identical kernel values — radeon stomped BIOS defaults on both cards.

| Register | BIOS POST (cold) | Radeon programs | Our driver used |
|---|---|---|---|
| `SPI_CONFIG_CNTL` | `0x0` | `0x03000000` | `0x0` (BIOS) |
| `SPI_CONFIG_CNTL_1` | `0x01000100` | `0x00000004` | `0x01000100` (BIOS) |
| `TA_CNTL_AUX` | `0x0` | `0x00010000` | `0x0` (BIOS) |
| `TCP_CHAN_STEER_LO` | `0x76543210` | `0x00001032` | `0x76543210` (BIOS) |
| `TCP_CHAN_STEER_HI` | `0xFEDCBA98` | `0x00000000` | `0xFEDCBA98` (BIOS) |
| `TCP_ADDR_CONFIG` | `0xFB` | `0x00000003` | `0xFB` (BIOS) |
| `PA_SC_RASTER_CONFIG` | `0x2A00126A` | `0x0000000A` | `0x2A00126A` (BIOS) |
| `CGTS_SM_CTRL_REG` | `0x200` | `0x96941200` | `0x200` (BIOS) |
| `DMIF_ADDR_CONFIG` | `0x00011003` | `0x10010002` | `0x00011003` (BIOS) |
| `DMIF_ADDR_CALC` | `0x0` | `0x10000000` | `0x0` (BIOS) |
| `HDP_ADDR_CONFIG` | `0x12010002` (ROM) | `0x12010002` | don't write |
| `VM_L2_CNTL` | `0x0C0B8E02` | `0x000B8603` | BIOS value |
| `VM_L2_CNTL3` | `0x100004` | `0x00120004` | BIOS value |
| `VM_CONTEXT0_CNTL` | `0xFFFED8` | `0x00000011` | BIOS value |
| `MC_VM_MX_L1_TLB_CNTL` | `0x503` | `0x0000055B` | BIOS value |
| `RLC_CGTT_MGCG_OVERRIDE` | `0xFFFFFFFF` | `0xFFFFFFC0` | BIOS value |
| `RLC_CGCG_CGLS_CTRL` | `0x3` | `0x0020003C` | BIOS value |
| `GB_TILE_MODE[0..31]` | ROM defaults | kernel values (differ) | BIOS values |

**VM/TLB setup — radeon uses GART page table, not pass-through:**
- `VM_CONTEXT0_CNTL` = `0x11` (page table enabled, not `0xFFFED8` pass-through)
- `VM_CONTEXT0_PT_BASE` = `0x00000AF0` (bus 1), `0x0` (bus 2) — actual GART page tables
- `MC_VM_MX_L1_TLB_CNTL` = `0x55B` (full TLB, not `0x503`)
- `MC_VM_FB_LOCATION` = `0x003F0000` (both — VRAM at base 0, same as our remap)

**Implication:** Rule 5 ("NEVER use Linux kernel register values") may be wrong.
Radeon compute works with these kernel values. The BIOS POST values we were copying
from bus 1 were the ROM defaults that radeon then overwrites. If dispatch works after
unbinding bus 2 (step 4), then the kernel values are correct and our BIOS-sourced
golden registers are the bug.

**The 10 remaining diffs (all expected operational state):**
- `VGA_RENDER_CONTROL/HDP_CONTROL` — display vs non-display
- `CG_SPLL_FUNC_CNTL_3` — 1 bit diff (bit 0), likely PLL phase
- `VM_INVALIDATE_RESPONSE` — live status (7 vs 1)
- `VM_CONTEXT0_PT_BASE` — different GART page table allocation
- `MC_SEQ_MISC0` — `0x500026A9` vs `0x500036A9` (1 bit, VRAM type readback)
- `SCRATCH_REG0`, `CP_RB0_CNTL/WPTR/RPTR` — ring operational state

### Next: Step 2-5

After unbinding bus 2 (`sudo sh -c 'echo 0000:02:00.0 > /sys/bus/pci/drivers/radeon/unbind'`):
- Probe again to see if registers change on unbind
- Run `./test_accel_gcn.x` on kernel-initialized bus 2
- If dispatch WORKS: our golden registers are wrong, switch to kernel values
- If dispatch FAILS: problem is in our dispatch path itself, not init

### To restore (disable radeon again)
Change grub back to:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash amdgpu.si_support=0 radeon.si_support=0 modprobe.blacklist=radeon,amdgpu,snd_hda_codec_atihdmi iommu=pt"
```
Then `sudo update-grub` and reboot.

---

## Critical Fixes — Jun 18, 2026 (TA_BUSY root cause analysis)

### Source material

Analysis cross-referenced the driver code against `/home/bob/GCNinit.md` — a 1585-line
reference document built by halcode from 66 pages of kernel documentation at
`docs.kernel.org/gpu/amdgpu/`. Three parallel analysis agents independently converged
on the same root cause.

Key kernel sources used for verification:
- `gmc_v6_0.c` — `gmc_v6_0_gart_enable()` VM/TLB setup
- `gfx_v6_0.c` — `gfx_v6_0_gpu_init()` engine defaults, CP_MEQ_THRESHOLDS
- `sid.h` — register bit definitions (SYSTEM_ACCESS_MODE, ENABLE_ADVANCED_DRIVER_MODEL)
- `si.c` (radeon) — `si_gpu_soft_reset()` SRBM reset mask

### Root cause: soft reset ordering + wrong VM/TLB values

The `buffer_load_dword` data path is:
```
Shader -> TA (Texture Addresser) -> TC (Texture Cache) -> L1 TLB -> L2 Cache -> MC -> VRAM
```

Two independent bugs caused the TA_BUSY hang:

1. **Ordering bug**: VM/TLB registers were programmed in `PM4_InitMCBase` (step 5) but
   then wiped by `PM4_SoftResetCP` (step 6) via GRBM_SOFT_RESET + SRBM_SOFT_RESET.
   The registers reverted to power-on defaults and were never restored.

2. **Value bug**: Even if the ordering were correct, the values themselves were wrong.
   The "bus 1 BIOS POST" values we were copying (0x0503, 0x00FFFED8, etc.) were ROM
   power-on defaults — NOT what makes compute work. Radeon overwrites these with kernel
   values during `gart_enable()`. The probe showing "bus 1 matches" was taken BEFORE
   radeon loaded, so we were copying un-initialized defaults.

### Fix #1: Move VM/TLB programming after soft reset

**Files**: `Library.AMDGPUPM4Ring.ailang`, `Library.AccelGCN.ailang`

Extracted ~70 lines of VM/TLB code from `PM4_InitMCBase` into new function
`PM4_ConfigureVM`. Wired into `AccelGCN_Init` at step 8 (after `PM4_SoftResetCP`
and `MC_SI_GpuInit`), so soft reset can no longer wipe the values.

### Fix #2: Remove SOFT_RESET_HDP from SRBM mask

**File**: `Library.AMDGPUPM4FW.ailang` line 608

```
# Before (BROKEN):
srbm_mask = Add(SRBMResetBits.SOFT_RESET_HDP, SRBMResetBits.SOFT_RESET_GRBM)

# After (FIXED):
srbm_mask = SRBMResetBits.SOFT_RESET_GRBM
```

SOFT_RESET_HDP destroys HDP_HOST_PATH_CNTL, HDP_ADDR_CONFIG, HDP_MISC_CNTL which
were programmed by ASIC_INIT. Nothing re-programmed them after reset (and we can't —
CPU-side HDP writes crash the RD990). The kernel `si_gpu_soft_reset()` does NOT
include SOFT_RESET_HDP.

### Fix #3: Fix CP_MEQ_THRESHOLDS encoding

**File**: `Library.AMDGPUMC_SI.ailang` line 853

```
# Before (WRONG — 0x6030, MEQ2_START in bits [15:8]):
GPU_Wr32(gpu, SIReg.CP_MEQ_THRESHOLDS, 24624)      // 0x6030

# After (CORRECT — 0x00600030, MEQ2_START in bits [22:16]):
GPU_Wr32(gpu, SIReg.CP_MEQ_THRESHOLDS, 6291504)     // 0x00600030
```

The MEQ2_START field is at bits [22:16], not [15:8]. Kernel source
`gfx_v6_0_gpu_init()` uses `(0x60 << CP_MEQ_THRESHOLDS__MEQ2_START__SHIFT)` where
the shift is 16. Our old value put 0x60 in the wrong bitfield.

### Fix #4: Correct VM/TLB register values (THE smoking gun)

**File**: `Library.AMDGPUPM4Ring.ailang` lines 266-286 (in `PM4_ConfigureVM`)

| Register | Old value (ROM default) | New value (kernel/radeon) | Decimal |
|---|---|---|---|
| `VM_CONTEXT0_CNTL` | 0x00FFFED8 | **0x00000011** | 17 |
| `MC_VM_MX_L1_TLB_CNTL` | 0x0503 | **0x055B** | 1371 |
| `VM_L2_CNTL` | 0x0C0B8E02 | **0x000B8603** | 755203 |
| `VM_L2_CNTL3` | 0x00100004 | **0x00120004** | 1179652 |

**Why MC_VM_MX_L1_TLB_CNTL = 0x055B is critical:**

Bit decode of the difference:

| Bits | Field | 0x0503 (old) | 0x055B (new) |
|---|---|---|---|
| 0 | ENABLE_L1_TLB | 1 | 1 |
| 1 | ENABLE_L1_FRAGMENT_PROCESSING | 1 | 1 |
| [4:3] | SYSTEM_ACCESS_MODE | 0 (PA_ONLY) | **3 (NOT_IN_SYS)** |
| 6 | ENABLE_ADVANCED_DRIVER_MODEL | 0 | **1** |
| [11:7] | (undocumented) | 0xA | 0xA |

With `SYSTEM_ACCESS_MODE=PA_ONLY`, the L1 TLB sends ALL addresses through VM
page-table translation — but VMID 0 has no page tables (PAGE_TABLE_DEPTH=0).
The translation request goes into a void, TC never gets data, TA waits forever.

With `SYSTEM_ACCESS_MODE=NOT_IN_SYS`, addresses within the system aperture
(MC_VM_SYSTEM_APERTURE_LOW/HIGH, which covers all VRAM) bypass VM translation
entirely and go direct to MC as physical addresses. This is what bare-metal
compute needs.

**Why VM_CONTEXT0_CNTL = 0x11:**

The old value 0x00FFFED8 had garbage bits set across multiple fields. The correct
value is just `ENABLE_CONTEXT(bit 0) | RANGE_PROTECTION_FAULT_ENABLE(bit 4)` with
`PAGE_TABLE_DEPTH=0` (flat passthrough for VMID 0).

### Key lesson learned

Rule 5 was wrong. The "bus 1 BIOS POST" probe was taken before radeon loaded —
those values were ROM power-on defaults, not working compute values. Radeon's
`gart_enable()` overwrites them with the correct kernel values. For VM/TLB
registers, the kernel values are correct. For golden registers (TCP, SPI, tile
modes), the BIOS values are still correct.

### Verification

Reboot required. After reboot:
```bash
cd ~/Ailang-Self-Hosting-
./ailang.x TestCode/test_accel_gcn.ailang test_accel_gcn.x
./test_accel_gcn.x
python3 gpu_probe_fullstate.py post > probe_after_fix.txt
```

If `buffer_load_dword` completes and dst[] contains computed values instead of
0xFFFFFFFF, the TA_BUSY hang is resolved.

---

## Fix #5: Skip MC_SI_Program — Keep BIOS VRAM Address (Jun 18, 2026)

**File**: `Library.AccelGCN.ailang` — removed MC_SI_Program call for bus 2.

**Problem**: MC_SI_Program remapped VRAM from the BIOS address (0xF43FF400 = GPU addr
0xF400000000) to base 0 (0x003F0000 = GPU addr 0x0). GPU address 0 overlaps system
RAM in the MC address decode. Shader `buffer_load_dword` at GPU addr 0x04082000
may route through BIF to PCI instead of staying on-card, causing master abort
(reads back 0xFFFFFFFF). The BIOS high address (0xF400000000) is unambiguous.

**Evidence**: Bus 2 PCI bridge (00:03.0) shows `<MAbort+>` even at fresh boot.
First VRAM write reads back 0xFFFFFFFF. Bus 1 (BIOS address, never remapped) works.
VM/TLB fixes from earlier confirmed applied but dispatch still fails with TA_BUSY.

**Change**: Skip MC_SI_Program on all GPUs. ASIC_INIT's MC_VM_FB_LOCATION stands.
PM4_InitMCBase reads it, PM4_VramToGPU adds mc_fb_base, PM4_ConfigureVM computes
system aperture from it automatically. No other code changes needed.
