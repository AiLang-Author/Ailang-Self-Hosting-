# GPU Driver Debug Log — Jun 16–22, 2026

## Tell Claude

"Read ~/Ailang-Self-Hosting-/gpu-crash.md before touching ANY GPU driver code."

---

## Platform

- **CPU/Chipset**: FX-8320 / RD990 — no AMD-Vi, VFIO impossible
- **GPUs**: Two Cape Verde (GCN 1.0, Southern Islands) sharing PCIe root complex
  - `01:00.0` = display GPU (BIOS VESA framebuffer, **no radeon driver**) — **NEVER TOUCH**
  - `02:00.0` = compute GPU (userspace AILang driver, radeon unbound)
- **Driver**: Entirely userspace AILang. Maps BARs via sysfs, writes registers via mmap'd MMIO
- **VRAM layout (Jun 22)**:
  - 0x0000000–0x59FFFFF: 90MB GART page table (identity maps GART VA 0xFF00000000–0xFF3FFFFFFF)
  - 0x5A00000–0x5FFFFFF: 6MB padding
  - 0x6000000 (96MB): Ring 0 base
  - 0x6011000: Ring 1 base
  - 0x6022000: Ring 2 base
  - Remaining: RLC SR/CS, shader, buf desc, IB, DATA
- **GART**: System RAM mapped into GPU VA space via page table in VRAM.
  IH ring, WPTR writeback, and dummy page live in mlock'd system RAM, accessed through GART PTEs.
- **DPM**: SMC-managed clock/voltage: boot 302 → 399 → 501 → 1049 MHz
- **Dispatch**: PM4 ring buffer, IB with DISPATCH_DIRECT + CS_PARTIAL_FLUSH, double EOP fence

## Register Domains

- **SRBM-routed** (always-on): CG_SPLL_*, SMC, RLC_CGTT_*, MC_VM_*, BIF_FB_EN — work on reference clock
- **GRBM-routed** (engine clock required): CP_ME_CNTL, GRBM_SOFT_RESET, CP firmware, SPI_*, SCRATCH_REG* — need SPLL locked first

---

## RULES

1. **`HDP_HOST_PATH_CNTL` (0x2C00) / `HDP_MISC_CNTL` (0x2F4C): kernel-verbatim only.**
   AMENDED 2026-07-02 (Sean-approved): ad-hoc writes remain forbidden (Crash #2, Jun 16,
   deadlocked the RD990 fabric), but replaying the KERNEL'S values at the KERNEL'S trace
   positions is permitted — the VBIOS writes 0x2C00=0x0F200029 / 0x2F4C=0x00121FE0 at
   trace seq 130/131 on every working boot of this box (kernel echoes 0x2C00 at 329374),
   and skipping them left our HDP at power-on state: prime suspect for the historic
   CPU→VRAM write corruption (Known Issue 2, VRAM diag garbage, PTE readback garbage).
   Never write any OTHER value to these regs, and never write them outside the ATOM-init
   sequence position. Other HDP registers are fine — `HDP_NONSURFACE_BASE` (0x2C04),
   `HDP_ADDR_CONFIG` (0x2F48), and the protection buffers (0x2C14+) match the kernel.
   `HDP_MEM_COHERENCY_FLUSH_CNTL` (0x5480) is also safe (different block, write-cache drain).

2. **NEVER run MC_SI_*, PM4_SoftResetCP, PM4_HaltCP, or AtomExec_AsicInit on the display GPU (bus 1).**
   All have display GPU guards. The BIOS already configured bus 1 correctly.

3. **Use kernel/radeon register values for ALL programmable registers.** Match `gfx_v6_0.c`,
   `gmc_v6_0.c`, and the bus2 mmiotrace. Tile mode table can use ROM defaults (matches kernel).

4. **VM_CONTEXT0 page table registers must all be set** even with PAGE_TABLE_DEPTH=0.
   - `PAGE_TABLE_BASE_ADDR` = vram_start_page (0x0F400000) — where the page table data lives
   - `PAGE_TABLE_START_ADDR` = vram_start_page (0x0F400000) — **MUST match gtt_start>>12 = vram start, NOT GART VA start**
   - `PAGE_TABLE_END_ADDR` = GART end page (0x0FF3FFFF)
   The page table covers VRAM start through GART end. VRAM bypasses via system aperture; GART uses PTEs.
   **All PTEs must be filled with dummy page entries** before enabling the context (kernel does this).
   Without BASE_ADDR, the VM resolves all addresses to physical 0 (BAR0 register space) → TA_BUSY hang.
   Without correct START_ADDR, PTE indexing is wrong → ring 1+ hangs on cold boot.

5. **GRBM_SOFT_RESET = SOFT_RESET_RLC (bit 2 = 0x4) only.** CP is controlled via CP_ME_CNTL
   halt/unhalt, never soft-reset. No MC blackout, no BIF_FB_EN toggle, no SRBM_SOFT_RESET
   during GFX init.

6. **Golden regs (MC_SI_GpuInit) BEFORE RLC reset (PM4_SoftResetCP).** Matches kernel:
   `gfx_v6_0_gpu_init()` then `gfx_v6_0_rlc_resume()`.

7. **CP firmware load order: PFP → CE → ME.** Matches kernel `gfx_v6_0_cp_gfx_load_microcode()`.

8. **Pre-RLC writes required before RLC_CNTL=1:**
   - `GRBM_GFX_INDEX = 0xE0000000` (broadcast all SE/SH/instances)
   - `SPI_LB_CU_MASK (0x9354) = 0xFF` (enable all CUs)
   - `PA_CL_ENHANCE (0x8A14) = 0x7` (CLIP_VTX_REORDER_ENA | NUM_CLIP_SEQ(3))

---

## Init Sequence (Jun 22, 2026)

```
 1. GPU_Discover → GPU_BAR_MapMMIO → GPU_BAR_MapVRAM
 2. AtomBIOS_LoadROM → Parse → PP_Parse → Volt_Parse
 3. DPM_SI_InitSPLL → AtomExec_AsicInit (bus 2 only; bus 1 skips)
 4. MC_SI_GpuInit (golden regs, tile modes, SPI, CG — bus 2 only)
 5. MC_SI_LoadMicrocode (MC sequencer firmware — bus 2 only)
 6. PM4_HaltCP → PM4_InitMCBase (reads MC_VM_FB_LOCATION)
 7. GART_Init (allocate system RAM, write PTEs for IH + DMA0/DMA1 rings)
 8. PM4_ConfigureVM (VM/TLB + system aperture + GART page table config)
 9. PM4_SetupIHRing (IH ring in GART-mapped system RAM)
10. PM4_SoftResetCP (RLC-only reset: halt → GRBM_SOFT_RESET=0x4 → deassert)
11. PM4_LoadRLCFirmware (upload → GRBM_GFX_INDEX broadcast → CU enable → PA_CL_ENHANCE → start)
12. PM4_HaltCP → PM4_LoadCPFirmware (PFP → CE → ME)
13. PM4_SetupRing(0) → PM4_SetupRing(1) → PM4_SetupRing(2) (all BEFORE unhalt)
14. PM4_CPStart (ME_INIT + unhalt + CLEAR_STATE on all 3 rings)
15. PM4_RingTest(0) → PM4_RingTest(1) → PM4_RingTest(2)
16. PM4_DMAResume (DMA0 + DMA1 ring init — cayman_dma_resume)
17. SCRATCH_UMSK=0xFF, roundtrip check
18. SMC_LoadFirmware → DPM_Init → DPM_Enable → Force HIGH
19. DCE6_FullInit (6 CRTCs disabled, HPD/AFMT/DIG configured)
20. GPU_BAR_PrimeVRAM
21. Build kernel → upload → AccelGCN_Dispatch (ring test + compute)
```

---

## Current Status (Jun 22, 2026)

### What works
- Full ASIC_INIT + MC + golden regs + VRAM mapping on bus 2
- GART page table in VRAM (90MB, maps system RAM for IH ring/writeback)
- RLC firmware load + start
- CP firmware load (PFP/CE/ME)
- Ring 0/1/2 setup

### What fails
- **Ring 1 test hangs.** Ring 0 works (RPTR catches WPTR), but ring 1 RPTR stays at 0.
  Ring 1 CP does not consume NOPs on cold init. Works on warm boot.
- **GRBM_STATUS = 0xA0003028** — this is **NORMAL**: bit 31=GUI_ACTIVE, bit 29=CP_BUSY
  (expected when halted), bit 13=CB_CLEAN, bit 12=DB_CLEAN, bit 5=SRBM_RQ_PENDING.
  The pipeline is clean/idle, NOT stuck. Previous decoding as "TA_BUSY/DB_BUSY/CB_BUSY" was wrong.

### Fixes applied (Jun 22 late)
Trace diff (bus2_all.txt vs our_mmiotrace.txt) revealed several init gaps:
1. **RLC_SAVE_AND_RESTORE_BASE** was 0 — now set to valid VRAM address (0x6034000)
2. **verde_golden_rlc_registers** missing — added 0xC424, 0xC47C, 0xC488 writes
3. **RLC_LB_CNTL / RLC_LB_CNTR_MAX** had wrong values — now match kernel golden regs
4. **verde_mgcg_cgcg_init** missing — added full CGTS per-block clock gating table (~30 regs)
5. **IIO golden registers** (MC indirect via 0x30/0x34 port) missing — added
6. **CP_PERFMON_CNTL** was 0x104 — kernel writes 0x0, fixed
7. Removed unnecessary GFX pipeline soft reset (0xDDFA) — based on wrong GRBM_STATUS decode

### Fix #12 (Jun 22 night) — PAGE_TABLE_START_ADDR was wrong
**Root cause of ring 1 cold-boot hang:** `VM_CONTEXT0_PAGE_TABLE_START_ADDR` was set to
`0x0FF00000` (GART VA start) instead of `0x0F400000` (vram_start_page). The kernel uses
`gtt_start >> 12 = vram_start >> 12`. With the wrong START_ADDR, PTE indexing was completely
off — any GART VA lookup hit the wrong PTE slot.
Also added: full dummy-page PTE fill (11.8M entries) matching kernel's `radeon_gart_table_vram_pin()`.

### Next test
```bash
cd ~/Ailang-Self-Hosting-
./ailang.x TestCode/test_accel_gcn.ailang test_accel_gcn
sudo ./test_accel_gcn 2>&1 | tee our_mmiotrace.txt
```

---

## Known Issues

1. **SMC message timeouts.** NoDisplay (0x5D), ForceHigh (0x82/0x83), and disable (0x84)
   all timeout. DPM may not be fully working. Unknown if this affects compute.

2. **First VRAM write reads back 0 after full init.** `Wr32(0xDEADBEEF) → Rd32=0x0`,
   then immediately `Wr32(0xCAFEBABE) → Rd32=0xCAFEBABE`. Does not happen on warm boot.
   Likely BAR coherency issue from ASIC_INIT sequence. Workaround: prime pages at map time.

3. **Silicon bug: dispatch slot leak.** Cape Verde compute event engine leaks dispatch
   tracking slots after ~36 dispatches (IH ring drains them via RLC).

---

## HDP Register Safety Reference

| Register | Offset | Status |
|---|---|---|
| `HDP_HOST_PATH_CNTL` | 0x2C00 | **NEVER WRITE** — deadlocks RD990 |
| `HDP_NONSURFACE_BASE` | 0x2C04 | Safe — kernel writes it in `gmc_v6_0_mc_program` |
| `HDP_NONSURFACE_INFO` | 0x2C08 | Safe — kernel writes it |
| `HDP_NONSURFACE_SIZE` | 0x2C0C | Safe — kernel writes it |
| HDP protection buffers | 0x2C14+i*0x18 | Safe — kernel zeros them in `gmc_v6_0_mc_program` |
| `HDP_ADDR_CONFIG` | 0x2F48 | Safe — kernel writes it |
| `HDP_MISC_CNTL` | 0x2F4C | **NEVER WRITE** — deadlocks RD990 |
| `HDP_MEM_COHERENCY_FLUSH_CNTL` | 0x5480 | Safe — write-cache drain, different block |

---

## Crash History (resolved)

- **Crash #1** (Jun 16): GRBM writes before SPLL up. Fixed: SPLL init first.
- **Crash #2** (Jun 16): CPU-side HDP_HOST_PATH_CNTL write. Fixed: removed.
- **Crash #3** (Jun 17): MC_SI_Program on display GPU. Fixed: display GPU guards.
- **Crash #4** (Jun 18): PM4_SoftResetCP on display GPU. Fixed: display GPU guards.
- **Crash #5** (Jun 22): Screen froze + system locked 30s later. Cause: likely ran old
  binary with RunOnGPU(1) still compiled, or cascading RD990 bus effects from stuck pipeline.

## Key Fixes History

| Fix | Date | What |
|-----|------|------|
| #1-4 | Jun 16-17 | SPLL ordering, HDP removal, display GPU guards |
| #5 | Jun 18 | AtomBIOS skip MC_SI_Program, keep BIOS VRAM addr |
| #6 | Jun 18-19 | VM_CONTEXT0_PAGE_TABLE_BASE_ADDR — fixed TA_BUSY root cause |
| #7 | Jun 19 | Register value corrections (kernel values, not ROM) |
| #8 | Jun 19 | Init ordering restructure (golden regs before RLC reset, RLC-only soft reset) |
| #9 | Jun 20-21 | GART page table, BAR0 page priming, IH ring in system RAM |
| #10 | Jun 22 | Pre-RLC writes, CP FW order, VM CTX0 start addr, remove CP MMIO writes |
| #11 | Jun 22 | RLC_SAVE_AND_RESTORE_BASE, golden RLC regs, CGTS table, IIO golden, CP_PERFMON |
| #12 | Jun 22 | PAGE_TABLE_START_ADDR fix (0xFF00000→vram_start_page) + full dummy PTE fill |
| #13 | Jun 22 | DMA engine init (PM4_DMAResume: DMA0+DMA1 ring buffers in GART) |
| #14 | Jun 22 | Full DCE6 display init (6 CRTCs, HPD, AFMT, DIG — stop skipping steps) |
| #15 | Jun 22 | Ring init order: all 3 rings before CP unhalt + CLEAR_STATE on all 3 rings |

## Test Command

```bash
cd ~/Ailang-Self-Hosting-
./ailang.x TestCode/test_accel_gcn.ailang test_accel_gcn
sudo ./test_accel_gcn 2>&1 | tee our_mmiotrace.txt
```


---

## Cold→Warm Compliance Plan (2026-06-22, ring 1 cold-init fix)

### Root cause (proven by cold-vs-warm trace diff)
Static layers all verified correct: dispatch payload, VM aperture/context, shader machine code
(`dst[i]=src[i]+42`, clean `s_endpgm`, 5 VGPR/9 SGPR within `rsrc1=0x41`). The divergence is
**ring memory location**:

| Reg | Warm (kernel, ring 1 works) | Cold (ours, ring 1 dead) |
|---|---|---|
| RB0/1/2_BASE | `0xFF00xxxx` = **GART** | `0xF406xxxx` = **VRAM** |
| RB0/1/2_RPTR_ADDR(+HI) | `0xFF_004010xx` = **GART** | `0xF4_06xxxxxx` = **VRAM** |
| RB0_CNTL | `0x90B` | `0x90D` |
| RB1/RB2_CNTL | `0x90A` | `0x90D` |

Kernel puts all CP rings + RPTR writeback in GART (system RAM via PTEs). Ring 0 tolerates VRAM cold;
the CP's fetch path for rings 1/2 does not → RB1_RPTR register never advances cold, works warm.
(Trace formats: warm `WR REG_0x<off> = 0x<val>`; cold `MMIO_WR <n> 0x0x<off> 0x0x<val>`.)

### Fix: relocate CP rings 0/1/2 + writeback into GART (mirror IH-ring pattern)
GART region free above `0xF440061000`. Each 64KB ring = 16 scattered phys pages mapped to 16
consecutive GART-VA pages (linear in GART VA, like the existing IH ring).

1. **GARTConf** — add VAs (HI=0xF4): RB0=`0x40070000`, RB1=`0x40090000`, RB2=`0x400B0000`,
   WB=`0x400D0000`; plus PTE indices (`VA_LO/4096`).
2. **GARTState** — add `cprb{0,1,2}_host_ptr`, `cprb{0,1,2}_phys_base`, `cprb_wb_host_ptr/phys`.
3. **GART_Init** — mmap+mlock 3×64KB (+1 WB page), per-page `GART_GetPhysAddr` + `GART_WritePTE`
   (16 PTEs/ring), store in GARTState. (Reuse the IH-ring loop pattern verbatim.)
4. **RingField** — add `HOST_PTR` (system-RAM ptr for packet writes) and `GART_VA`.
5. **PM4_SetupRing** — set `HOST_PTR = GARTState.cprbN_host_ptr`, `GART_VA = 0xF44007/09/0B0000`;
   zero via HOST_PTR; `CP_RB*_BASE = GART_VA >> 8`; `RPTR_ADDR = GART_VA + RPTR_WB_OFFSET` (or a
   slot in the WB page); per-ring CNTL: RB0 size→`0x90B`, RB1/RB2→`0x90A`.
6. **PM4_EmitDWord / PM4_Pkt** — write to `HOST_PTR + pos` when set, else fall back to VRAM.

### Safety (testing this is NON-destructive)
`ring_idx=1` + display guard remain. Ring setup is register config; the ring **test is NOPs** — no
compute dispatch (the fabric-hang source), no bus-1 DPM (the display-kill source). Worst case: ring 1
test still times out harmlessly. Success = RB1_RPTR advances.

### Current safe state on disk
- Edit #1: ring tests non-fatal (init completes ~36k). KEEP.
- Display guard in AccelGCN_Init (aborts on bus-1 fallback). KEEP.
- `ring_idx=1`. Instrumentation present: `[DBG]`/`[DBG-SUBMIT]` (dispatch addrs), `[VMDBG]`
  (VM readback), `[MC]` (shader dump). Backups: `*.bak_*` alongside each edited lib.
