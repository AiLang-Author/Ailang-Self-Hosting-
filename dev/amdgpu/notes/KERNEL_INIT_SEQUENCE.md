# KERNEL SI (Cape Verde / GCN1) GPU INIT SEQUENCE — COMPLETE REFERENCE

## Source Files Cross-Referenced
- `/home/bob/linux/drivers/gpu/drm/amd/amdgpu/si.c` — Top-level IP block ordering + golden registers
- `/home/bob/linux/drivers/gpu/drm/amd/amdgpu/gmc_v6_0.c` — Memory controller (GMC) init
- `/home/bob/linux/drivers/gpu/drm/amd/amdgpu/gfx_v6_0.c` — GFX engine (CP, RLC, rings) init
- `/home/bob/linux/drivers/gpu/drm/amd/amdgpu/si_dpm.c` — DPM/SMC power management
- `/home/bob/linux/drivers/gpu/drm/amd/amdgpu/si_ih.c` — Interrupt handler setup
- `/home/bob/linux/drivers/gpu/drm/amd/amdgpu/si_dma.c` — DMA engine (not relevant for compute)
- Header files: `gca/gfx_6_0_d.h`, `gmc/gmc_6_0_d.h`, `oss/oss_1_0_d.h` for register offsets

---

## PHASE 0: IP BLOCK ORDERING (si.c:2693 `si_set_ip_blocks`)

For CHIP_VERDE, the kernel adds IP blocks in this EXACT order:

```
1. si_common_ip_block    — AMD_IP_BLOCK_TYPE_COMMON
2. gmc_v6_0_ip_block     — AMD_IP_BLOCK_TYPE_GMC
3. si_ih_ip_block        — AMD_IP_BLOCK_TYPE_IH
4. gfx_v6_0_ip_block     — AMD_IP_BLOCK_TYPE_GFX
5. si_dma_ip_block       — AMD_IP_BLOCK_TYPE_SDMA
6. si_smu_ip_block       — AMD_IP_BLOCK_TYPE_SMC
7. dce_v6_0_ip_block     — AMD_IP_BLOCK_TYPE_DCE (display; conditional: vkms/dm/dce_v6)
8. uvd_v3_1_ip_block     — AMD_IP_BLOCK_TYPE_UVD
9. vce_v1_0_ip_block     — AMD_IP_BLOCK_TYPE_VCE
```

Each block's `hw_init` is called IN ORDER. This is the master init sequence.

---

## PHASE 1: COMMON HW INIT (si.c:2634 `si_common_hw_init`)

```c
si_fix_pci_max_read_req_size(adev);    // Set PCIe max read request = 512
si_init_golden_registers(adev);         // Program golden registers (ASIC-specific)
si_pcie_gen3_enable(adev);             // Enable PCIe Gen3 if supported
si_program_aspm(adev);                 // Configure PCIe ASPM
```

### Golden Registers for Verde (si.c:313 `verde_golden_registers`)

These are register/mask/value triples applied via read-modify-write:

| Register | Mask | Value | Notes |
|----------|------|-------|-------|
| AZALIA_SCLK_CONTROL | 0x30 | 0x11 | Audio clock |
| CB_HW_CONTROL | 0x10000 | 0x18208 | Color buffer |
| DB_DEBUG | 0xffffffff | 0x0 | Depth buffer debug |
| DB_DEBUG2 | 0xf00fffff | 0x400 | |
| DB_DEBUG3 | 0x2021c | 0x20200 | |
| DCI_CLK_CNTL | 0x80 | 0x0 | |
| 0x340c | 0x300c0 | 0x800040 | |
| 0x360c | 0x300c0 | 0x800040 | |
| FBC_DEBUG_COMP | 0xf0 | 0x70 | |
| FBC_MISC | 0x200000 | 0x50100000 | |
| DIG0_HDMI_CONTROL | 0x31000311 | 0x11 | |
| MC_SEQ_PMG_PG_HWCNTL | 0x73ffe | 0x22a2 | MC sequencer PG |
| MC_XPB_P2P_BAR_CFG | 0x7ff | 0x0 | |
| PA_CL_ENHANCE | 0xf000001f | 0x7 | Clip reorder |
| PA_SC_FORCE_EOV_MAX_CNTS | 0xffffffff | 0xffffff | |
| PA_SC_LINE_STIPPLE_STATE | 0xff0f | 0x0 | |
| PA_SC_MODE_CNTL_1 | 0x7ffffff | 0x4e000000 | |
| **PA_SC_RASTER_CONFIG** | 0x3f3f3fff | **0x124a** | **Verde-specific raster config** |
| 0x000c | 0xffffffff | 0x40 | |
| 0x000d | 0x40 | 0x4040 | |
| **SPI_CONFIG_CNTL** | 0x7ffffff | **0x3000000** | SPI config |
| SQ_DED_CNT | 0x1ff1f3f | 0x0 | Clear ECC counters |
| SQ_SEC_CNT | 0x1ff1f3f | 0x0 | |
| SX_DEBUG_1 | 0x7f | 0x20 | |
| TA_CNTL_AUX | 0x10000 | 0x10000 | |
| **TCP_ADDR_CONFIG** | 0x3ff | **0x3** | Verde=4 TCCs |
| TCP_CHAN_STEER_HI | 0xffffffff | 0x0 | |
| TCP_CHAN_STEER_LO | 0xffffffff | 0x1032 | |
| VGT_GS_VERTEX_REUSE | 0x1f | 0x10 | |
| VM_L2_CG | 0xc0fc0 | 0xc0400 | VM L2 clock gating |
| VM_PRT_APERTURE0_LOW_ADDR | 0xfffffff | 0xffffffff | PRT (not used) |
| VM_PRT_APERTURE1_LOW_ADDR | 0xfffffff | 0xfffffff | PRT (not used) |
| VM_PRT_APERTURE2_LOW_ADDR | 0xfffffff | 0xfffffff | PRT (not used) |
| VM_PRT_APERTURE3_LOW_ADDR | 0xfffffff | 0xfffffff | PRT (not used) |

(34 entries total. Note: each chip has its own golden_registers array with chip-specific values like PA_SC_RASTER_CONFIG and TCP_ADDR_CONFIG.)

### Golden RLC Registers for Verde (si.c:303 `verde_golden_rlc_registers`)

| Register | Mask | Value | Notes |
|----------|------|-------|-------|
| **GB_ADDR_CONFIG** | 0xffffffff | **0x02010002** | RLC golden (overridden to 0x12010002 by constants_init Phase 4a) |
| RLC_LB_PARAMS | 0xffffffff | 0x033f1005 | Load-balance params |
| 0x311f | 0xffffffff | 0x10808020 | |
| 0x3122 | 0xffffffff | 0x00800008 | |
| RLC_LB_CNTR_MAX | 0xffffffff | 0x1000 | |
| RLC_LB_CNTL | 0xffffffff | 0x80010014 | |

### Verde MGCG/CGCG Init (si.c:668 `verde_mgcg_cgcg_init`)

**96 register triples** programming medium-grain clock gating (MGCG), coarse-grain clock gating
(CGCG), and CGTS scheduling tables. Includes:
- 26 `mmCGTT_*` clock domain overrides (CB, BCI, CP, GDS, IA, PA, PC, RLC, SC, SPI, SQ, SQG,
  SX0-3, TCI, TCP, VGT, DB, TA, TCA, TCC, TD) — most set to 0x00000100 (IA_CLK_CTRL and VGT_CLK_CTRL are 0x06000100)
- CGTS SM scheduling tables (dword offsets 0x2458-0x2498) — ~50 entries
- `mmCGTS_SM_CTRL_REG` = 0x96940200
- `mmCP_RB_WPTR_POLL_CNTL` = 0x00900100
- `mmRLC_GCPM_GENERAL_3` = 0x00000080
- `mmRLC_CGCG_CGLS_CTRL` = 0x0020003f
- Memory power/clock gating: MC_MEM_POWER_LS, MC_CITF_MISC_WR/RD_CG, HDP, XDMA, CP_MEM_SLP
- **This is the CGTS clock gating table the mmiotrace shows ~80 writes for (register byte offsets 0x9160-0x9260 for CGTS_SM entries; mmiotrace BAR-relative offsets differ)**

### Verde PG Init (si.c:176 `verde_pg_init`)

GMCON PGFSM programming — 123 register triples of GMCON_PGFSM_WRITE/CONFIG/RENG_RAM writes for
power-gating state machine initialization, plus GMCON_RENG_EXECUTE, GMCON_MISC2/MISC3, and
MC_PMG_AUTO_CFG. This programs the MC power gating FSM.

---

## PHASE 2: GMC HW INIT (gmc_v6_0.c:901 `gmc_v6_0_hw_init`)

```c
gmc_v6_0_mc_program(adev);           // Program MC apertures + HDP init
gmc_v6_0_mc_load_microcode(adev);    // Load MC sequencer firmware
gmc_v6_0_gart_enable(adev);          // Enable GART (PCIE page table)
```

### 2a: MC Program (gmc_v6_0.c:219 `gmc_v6_0_mc_program`)

```c
// Initialize HDP: 32 iterations, 5 regs each (dword offsets 0xb05..0xb09 + j*6)
for (i=0, j=0; i<32; i++, j+=6) {
    WREG32(0xb05+j, 0);    // HDP_XDP_DIRECT_TAG_INFO_0..31
    WREG32(0xb06+j, 0);
    WREG32(0xb07+j, 0);
    WREG32(0xb08+j, 0);
    WREG32(0xb09+j, 0);
}
WREG32(mmHDP_REG_COHERENCY_FLUSH_CNTL, 0);

// Wait for MC idle (poll SRBM_STATUS for MCB/MCC/MCD/VMC busy bits)
gmc_v6_0_wait_for_idle(ip_block);

// VGA lockout (if display present)
if (adev->mode_info.num_crtc) {
    tmp = RREG32(mmVGA_HDP_CONTROL);
    tmp |= VGA_MEMORY_DISABLE;
    WREG32(mmVGA_HDP_CONTROL, tmp);
    tmp = RREG32(mmVGA_RENDER_CONTROL);
    tmp &= VGA_VSTATUS_CNTL_MASK;
    WREG32(mmVGA_RENDER_CONTROL, tmp);
}

// VM Aperture configuration
WREG32(mmMC_VM_SYSTEM_APERTURE_LOW_ADDR,  vram_start >> 12);
WREG32(mmMC_VM_SYSTEM_APERTURE_HIGH_ADDR, vram_end >> 12);
WREG32(mmMC_VM_SYSTEM_APERTURE_DEFAULT_ADDR, scratch_gpu_addr >> 12);
WREG32(mmMC_VM_AGP_BASE, 0);
WREG32(mmMC_VM_AGP_TOP,  agp_end >> 22);
WREG32(mmMC_VM_AGP_BOT,  agp_start >> 22);

gmc_v6_0_wait_for_idle(ip_block);    // Wait for MC idle again
```

### 2b: MC Microcode Load (gmc_v6_0.c:145 `gmc_v6_0_mc_load_microcode`)

Only loads if MC sequencer NOT already running (`MC_SEQ_SUP_CNTL & RUN == 0`):

```c
// Check if MC already running
running = RREG32(mmMC_SEQ_SUP_CNTL) & RUN_MASK;
if (running == 0) {
    // Reset and set writable
    WREG32(mmMC_SEQ_SUP_CNTL, 0x00000008);
    WREG32(mmMC_SEQ_SUP_CNTL, 0x00000010);

    // Load MC IO debug regs (pairs: index, data)
    for (i=0; i<regs_size; i++) {
        WREG32(mmMC_SEQ_IO_DEBUG_INDEX, io_mc_regs[i*2]);
        WREG32(mmMC_SEQ_IO_DEBUG_DATA,  io_mc_regs[i*2+1]);
    }

    // Load MC ucode
    for (i=0; i<ucode_size; i++)
        WREG32(mmMC_SEQ_SUP_PGM, fw_data[i]);

    // Activate
    WREG32(mmMC_SEQ_SUP_CNTL, 0x00000008);
    WREG32(mmMC_SEQ_SUP_CNTL, 0x00000004);
    WREG32(mmMC_SEQ_SUP_CNTL, 0x00000001);

    // Wait for training complete (poll MC_SEQ_TRAIN_WAKEUP_CNTL TRAIN_DONE_D0/D1)
    poll TRAIN_DONE_D0;
    poll TRAIN_DONE_D1;
}
```

### 2c: GART Enable (gmc_v6_0.c:471 `gmc_v6_0_gart_enable`)

```c
table_addr = amdgpu_bo_gpu_offset(adev->gart.bo);    // GART page table addr in VRAM

// L1 TLB Control
WREG32(mmMC_VM_MX_L1_TLB_CNTL,
    (0xA << 7) |                      // NUM_EFFECTIVE_L1_TLB_ENTRIES = 10
    ENABLE_L1_TLB |
    ENABLE_L1_FRAGMENT_PROCESSING |
    SYSTEM_ACCESS_MODE_MASK |         // bits 1:0 = 3 (not-in-sys = GART)
    ENABLE_ADVANCED_DRIVER_MODEL |
    (0 << SYSTEM_APERTURE_UNMAPPED_ACCESS));   // 0 = passthrough

// L2 Cache Control
WREG32(mmVM_L2_CNTL,
    ENABLE_L2_CACHE |
    ENABLE_L2_FRAGMENT_PROCESSING |
    ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE |
    ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE |
    (7 << EFFECTIVE_L2_QUEUE_SIZE) |     // 128 entries
    (1 << CONTEXT1_IDENTITY_ACCESS_MODE));

WREG32(mmVM_L2_CNTL2,
    INVALIDATE_ALL_L1_TLBS |
    INVALIDATE_L2_CACHE);

WREG32(mmVM_L2_CNTL3,
    L2_CACHE_BIGK_ASSOCIATIVITY |
    (fragment_size << BANK_SELECT) |
    (fragment_size << L2_CACHE_BIGK_FRAGMENT_SIZE));

// Context 0 (System/GART)
WREG32(mmVM_CONTEXT0_PAGE_TABLE_START_ADDR, gart_start >> 12);
WREG32(mmVM_CONTEXT0_PAGE_TABLE_END_ADDR,   gart_end >> 12);
WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR,  table_addr >> 12);
WREG32(mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR, dummy_page_addr >> 12);
WREG32(mmVM_CONTEXT0_CNTL2, 0);
WREG32(mmVM_CONTEXT0_CNTL,
    ENABLE_CONTEXT |
    (0 << PAGE_TABLE_DEPTH) |           // Flat (no PDE levels)
    RANGE_PROTECTION_FAULT_ENABLE_DEFAULT);

WREG32(0x575, 0);    // Unknown regs
WREG32(0x576, 0);
WREG32(0x577, 0);

// Contexts 1-15 (VM)
WREG32(mmVM_CONTEXT1_PAGE_TABLE_START_ADDR, 0);
WREG32(mmVM_CONTEXT1_PAGE_TABLE_END_ADDR,   max_pfn - 1);

for (i=1; i<16; i++) {
    if (i < 8)
        WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i, table_addr >> 12);
    else
        WREG32(mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8, table_addr >> 12);
}

WREG32(mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR, dummy_page_addr >> 12);
WREG32(mmVM_CONTEXT1_CNTL2, 4);
WREG32(mmVM_CONTEXT1_CNTL,
    ENABLE_CONTEXT |
    (1 << PAGE_TABLE_DEPTH) |           // 1 level of PDE
    ((block_size-9) << PAGE_TABLE_BLOCK_SIZE));

// Enable fault reporting for contexts 1-15 (conditional on !amdgpu_vm_fault_stop)
gmc_v6_0_set_fault_enable_default(adev, value);
    // Reads VM_CONTEXT1_CNTL, sets RANGE/DUMMY/PDE0/VALID/READ/WRITE fault enable bits
    // value depends on amdgpu_vm_fault_stop module parameter

// Invalidate all TLBs (via gmc_v6_0_flush_gpu_tlb indirection)
gmc_v6_0_flush_gpu_tlb(adev, 0, 0, 0);    // Writes VM_INVALIDATE_REQUEST for VMID 0
```

---

## PHASE 3: IH HW INIT (si_ih.c — interrupt handler)

Sets up the interrupt ring buffer. Writes:
- IH_RB_BASE, IH_RB_CNTL (size, watermark)
- IH_RB_WPTR, IH_RB_RPTR = 0
- IH_CNTL (enable, MC write clean threshold)
- Enables interrupt sources

---

## PHASE 4: GFX HW INIT (gfx_v6_0.c:3194 `gfx_v6_0_hw_init`)

This is the CORE init sequence. Three sub-phases:

```c
gfx_v6_0_constants_init(adev);           // Phase 4a: GPU engine constants
r = adev->gfx.rlc.funcs->resume(adev);  // Phase 4b: RLC firmware (gfx_v6_0_rlc_resume)
r = gfx_v6_0_cp_resume(adev);           // Phase 4c: CP firmware + rings
adev->gfx.ce_ram_size = 0x8000;
```

### 4a: Constants Init (gfx_v6_0.c:1644 `gfx_v6_0_constants_init`)

#### Step 1: CHIP CONFIG for Verde
```c
max_shader_engines = 1
max_tile_pipes = 4
max_cu_per_sh = 5
max_sh_per_se = 2
max_backends_per_se = 4
max_texture_channel_caches = 4
max_gprs = 256
max_gs_threads = 32
max_hw_contexts = 8
sc_prim_fifo_size_frontend = 0x20
sc_prim_fifo_size_backend = 0x40
sc_hiz_tile_fifo_size = 0x30
sc_earlyz_tile_fifo_size = 0x130
gb_addr_config = 0x12010002     (VERDE_GB_ADDR_CONFIG_GOLDEN, gfx_v6_0.c:53)
```

#### Step 2: GRBM/SRBM Setup
```c
WREG32(mmGRBM_CNTL, 0xff << READ_TIMEOUT);     // 255 cycle timeout
WREG32(mmSRBM_INT_CNTL, 1);
WREG32(mmSRBM_INT_ACK, 1);
WREG32(mmBIF_FB_EN, FB_READ_EN | FB_WRITE_EN); // Enable framebuffer access
```

#### Step 3: GB_ADDR_CONFIG propagation
```c
// Read MC_ARB_RAMCFG to determine mem_row_size
mc_arb_ramcfg = RREG32(mmMC_ARB_RAMCFG);
// ... compute row size ...

// Set GB_ADDR_CONFIG ROW_SIZE and NUM_SHADER_ENGINES fields
WREG32(mmGB_ADDR_CONFIG,    gb_addr_config);    // 0x12010002 (before ROW_SIZE patch)
WREG32(mmDMIF_ADDR_CONFIG,  gb_addr_config);
WREG32(mmDMIF_ADDR_CALC,    gb_addr_config);
WREG32(mmHDP_ADDR_CONFIG,   gb_addr_config);
WREG32(mmDMA_TILING_CONFIG + DMA0_REGISTER_OFFSET, gb_addr_config);
WREG32(mmDMA_TILING_CONFIG + DMA1_REGISTER_OFFSET, gb_addr_config);
```

#### Step 4: Tiling Mode Table
```c
gfx_v6_0_tiling_mode_table_init(adev);
// Writes tilemode[0..31] to GB_TILE_MODE0..31 registers
// Verde-specific tiling modes with PIPE_CONFIG = P4_8x16
```

#### Step 5: RB, TCC, SPI Setup
```c
gfx_v6_0_setup_rb(adev);     // Program render backend config per SE/SH
gfx_v6_0_setup_tcc(adev);    // Patch TCP channel steering for disabled TCCs
gfx_v6_0_setup_spi(adev);    // Program SPI_STATIC_THREAD_MGMT_3 per SE/SH
                               // (disable one CU per SH for thread management)
gfx_v6_0_get_cu_info(adev);
gfx_v6_0_config_init(adev);  // double_offchip_lds_buf = 0
```

#### Step 6: CP Queue/MEQ Thresholds
```c
WREG32(mmCP_QUEUE_THRESHOLDS,
    (0x16 << ROQ_IB1_START) |
    (0x2b << ROQ_IB2_START));

WREG32(mmCP_MEQ_THRESHOLDS,
    (0x30 << MEQ1_START) |
    (0x60 << MEQ2_START));
```

#### Step 7: Various GFX Engine Constants
```c
sx_debug_1 = RREG32(mmSX_DEBUG_1);
WREG32(mmSX_DEBUG_1, sx_debug_1);          // Read-write-back

WREG32(mmSPI_CONFIG_CNTL_1, 4 << VTX_DONE_DELAY);

WREG32(mmPA_SC_FIFO_SIZE,
    (frontend << SC_FRONTEND_PRIM_FIFO_SIZE) |
    (backend << SC_BACKEND_PRIM_FIFO_SIZE) |
    (hiz << SC_HIZ_TILE_FIFO_SIZE) |
    (earlyz << SC_EARLYZ_TILE_FIFO_SIZE));

WREG32(mmVGT_NUM_INSTANCES, 1);
WREG32(mmCP_PERFMON_CNTL, 0);
WREG32(mmSQ_CONFIG, 0);
WREG32(mmPA_SC_FORCE_EOV_MAX_CNTS,
    (4095 << FORCE_EOV_MAX_CLK_CNT) |
    (255 << FORCE_EOV_MAX_REZ_CNT));

WREG32(mmVGT_CACHE_INVALIDATION,
    (VC_AND_TC << CACHE_INVALIDATION) |
    (ES_AND_GS_AUTO << AUTO_INVLD_EN));

WREG32(mmVGT_GS_VERTEX_REUSE, 16);
WREG32(mmPA_SC_LINE_STIPPLE_STATE, 0);
```

#### Step 8: CB Perf Counters Clear
```c
WREG32(mmCB_PERFCOUNTER0_SELECT0, 0);
WREG32(mmCB_PERFCOUNTER0_SELECT1, 0);
WREG32(mmCB_PERFCOUNTER1_SELECT0, 0);
WREG32(mmCB_PERFCOUNTER1_SELECT1, 0);
WREG32(mmCB_PERFCOUNTER2_SELECT0, 0);
WREG32(mmCB_PERFCOUNTER2_SELECT1, 0);
WREG32(mmCB_PERFCOUNTER3_SELECT0, 0);
WREG32(mmCB_PERFCOUNTER3_SELECT1, 0);
```

#### Step 9: HDP HOST PATH CNTL Read-Write-Back
```c
hdp_host_path_cntl = RREG32(mmHDP_HOST_PATH_CNTL);     // READ first!
WREG32(mmHDP_HOST_PATH_CNTL, hdp_host_path_cntl);       // Write SAME value back
// *** CRITICAL: The kernel READS first, then writes back.
// *** Our driver hardcodes 0x0F200029. Must change to read-then-writeback.
```

#### Step 10: PA CL Enhance
```c
WREG32(mmPA_CL_ENHANCE,
    CLIP_VTX_REORDER_ENA |
    (3 << NUM_CLIP_SEQ));

udelay(50);    // 50us settle
```

### 4b: RLC Resume (gfx_v6_0.c:2568 `gfx_v6_0_rlc_resume`)

**EXACT sequence:**

```c
// Step 1: Stop RLC
adev->gfx.rlc.funcs->stop(adev);
    // gfx_v6_0_rlc_stop (line 2528):
    WREG32(mmRLC_CNTL, 0);                              // Halt RLC
    gfx_v6_0_enable_gui_idle_interrupt(adev, false);     // Disable GUI idle int
        // Reads CP_INT_CNTL_RING0, clears CNTX_BUSY_INT_ENABLE (bit 19)
        //   and CNTX_EMPTY_INT_ENABLE (bit 20), writes back
        // Then reads DB_DEPTH_INFO
        // Polls RLC_STAT for (GFX_CLOCK_STATUS | GFX_POWER_STATUS)
    gfx_v6_0_wait_for_rlc_serdes(adev);
        // Polls RLC_SERDES_MASTER_BUSY_0 == 0
        // Polls RLC_SERDES_MASTER_BUSY_1 == 0

// Step 2: Reset RLC
adev->gfx.rlc.funcs->reset(adev);
    // gfx_v6_0_rlc_reset (line 2545):
    WREG32_FIELD(GRBM_SOFT_RESET, SOFT_RESET_RLC, 1);   // Assert RLC soft reset
    udelay(50);
    WREG32_FIELD(GRBM_SOFT_RESET, SOFT_RESET_RLC, 0);   // Deassert
    udelay(50);

// Step 3: Init PG (power gating)
gfx_v6_0_init_pg(adev);
    // gfx_v6_0_init_pg (line 2943):
    // For Cape Verde with no PG flags (else branch, line 2964):
    WREG32(mmRLC_SAVE_AND_RESTORE_BASE, save_restore_gpu_addr >> 8);
    WREG32(mmRLC_CLEAR_STATE_RESTORE_BASE, clear_state_gpu_addr >> 8);
    // *** CRITICAL: These are written BEFORE RLC_RL_BASE below ***

// Step 4: Init CG (clock gating — empty for SI)
gfx_v6_0_init_cg(adev);    // NOP

// Step 5: RLC register config
WREG32(mmRLC_RL_BASE, 0);
WREG32(mmRLC_RL_SIZE, 0);
WREG32(mmRLC_LB_CNTL, 0);
WREG32(mmRLC_LB_CNTR_MAX, 0xffffffff);
WREG32(mmRLC_LB_CNTR_INIT, 0);
WREG32(mmRLC_LB_INIT_CU_MASK, 0xffffffff);

WREG32(mmRLC_MC_CNTL, 0);
WREG32(mmRLC_UCODE_CNTL, 0);

// Step 6: Load RLC firmware
// NOTE: Kernel sets ADDR for EACH word, not auto-increment
for (i=0; i<fw_size; i++) {
    WREG32(mmRLC_UCODE_ADDR, i);
    WREG32(mmRLC_UCODE_DATA, fw_data[i]);
}
WREG32(mmRLC_UCODE_ADDR, 0);

// Step 7: Enable LBPW
gfx_v6_0_enable_lbpw(adev, gfx_v6_0_lbpw_supported(adev));
    // gfx_v6_0_lbpw_supported (line 2553):
    //   tmp = RREG32(mmMC_SEQ_MISC0)
    //   return (tmp & 0xF0000000) == 0xB0000000  (DDR3 only)
    // gfx_v6_0_enable_lbpw (line 2476):
    //   If enable: set LOAD_BALANCE_ENABLE bit in RLC_LB_CNTL
    //   If !enable: clear it, then:
    //     gfx_v6_0_select_se_sh(0xffffffff, 0xffffffff, 0xffffffff, 0)
    //     WREG32(mmSPI_LB_CU_MASK, 0x00ff)
    // *** Cape Verde has GDDR5 (0x50000000), so lbpw_supported = FALSE ***
    // *** So: clear LOAD_BALANCE_ENABLE, write SPI_LB_CU_MASK = 0x00ff ***

// Step 8: Start RLC
adev->gfx.rlc.funcs->start(adev);
    // gfx_v6_0_rlc_start (line 2536):
    WREG32(mmRLC_CNTL, RLC_ENABLE_F32);    // RLC_CNTL = 1
    gfx_v6_0_enable_gui_idle_interrupt(adev, true);
        // Reads CP_INT_CNTL_RING0, sets CNTX_BUSY_INT_ENABLE (bit 19)
        //   and CNTX_EMPTY_INT_ENABLE (bit 20), writes back
    udelay(50);
```

### 4c: CP Resume (gfx_v6_0.c:2330 `gfx_v6_0_cp_resume`)

```c
// Step 1: Disable GUI idle interrupt
gfx_v6_0_enable_gui_idle_interrupt(adev, false);

// Step 2: Load CP microcode
gfx_v6_0_cp_load_microcode(adev);
    // gfx_v6_0_cp_gfx_load_microcode (line 2015):

    // 2a: Halt CP and clear scratch mask
    gfx_v6_0_cp_gfx_enable(adev, false);
        // WREG32(mmCP_ME_CNTL, ME_HALT | PFP_HALT | CE_HALT)
        // WREG32(mmSCRATCH_UMSK, 0)
        // udelay(50)

    // 2b: Load PFP firmware
    WREG32(mmCP_PFP_UCODE_ADDR, 0);
    for (i=0; i<pfp_fw_size; i++)
        WREG32(mmCP_PFP_UCODE_DATA, pfp_fw[i]);
    WREG32(mmCP_PFP_UCODE_ADDR, 0);    // Reset addr

    // 2c: Load CE firmware
    WREG32(mmCP_CE_UCODE_ADDR, 0);
    for (i=0; i<ce_fw_size; i++)
        WREG32(mmCP_CE_UCODE_DATA, ce_fw[i]);
    WREG32(mmCP_CE_UCODE_ADDR, 0);

    // 2d: Load ME firmware
    WREG32(mmCP_ME_RAM_WADDR, 0);
    for (i=0; i<me_fw_size; i++)
        WREG32(mmCP_ME_RAM_DATA, me_fw[i]);
    WREG32(mmCP_ME_RAM_WADDR, 0);

    // 2e: Zero all address registers
    WREG32(mmCP_PFP_UCODE_ADDR, 0);
    WREG32(mmCP_CE_UCODE_ADDR, 0);
    WREG32(mmCP_ME_RAM_WADDR, 0);
    WREG32(mmCP_ME_RAM_RADDR, 0);     // *** Our code is MISSING this ***

// Step 3: GFX ring resume
gfx_v6_0_cp_gfx_resume(adev);
    // (line 2135):
    WREG32(mmCP_SEM_WAIT_TIMER, 0);
    WREG32(mmCP_SEM_INCOMPLETE_TIMER_CNTL, 0);
    WREG32(mmCP_RB_WPTR_DELAY, 0);
    WREG32(mmCP_DEBUG, 0);
    WREG32(mmSCRATCH_ADDR, 0);         // *** Our code is MISSING this ***

    // Ring 0 setup
    rb_bufsz = order_base_2(ring_size / 8);
    tmp = (order_base_2(PAGE_SIZE/8) << 8) | rb_bufsz;
    WREG32(mmCP_RB0_CNTL, tmp);
    WREG32(mmCP_RB0_CNTL, tmp | RB_RPTR_WR_ENA);    // Enable RPTR write
    ring->wptr = 0;
    WREG32(mmCP_RB0_WPTR, 0);
    WREG32(mmCP_RB0_RPTR_ADDR,    lower_32(rptr_addr));
    WREG32(mmCP_RB0_RPTR_ADDR_HI, upper_32(rptr_addr) & 0xFF);
    WREG32(mmSCRATCH_UMSK, 0);
    mdelay(1);                          // 1ms delay!
    WREG32(mmCP_RB0_CNTL, tmp);         // Clear RB_RPTR_WR_ENA
    WREG32(mmCP_RB0_BASE, ring_gpu_addr >> 8);

    // Start CP (ME_INITIALIZE + CLEAR_STATE)
    gfx_v6_0_cp_gfx_start(adev);
        // (line 2070):
        // Allocate ring space, write:
        //   PACKET3(ME_INITIALIZE, 5):
        //     0x1, 0x0, max_hw_contexts-1, DEVICE_ID(1), 0, 0
        //   PACKET3(SET_BASE, 2):
        //     BASE_INDEX(CE_PARTITION_BASE), 0xc000, 0xe000
        // Commit ring

        // UNHALT CP:
        gfx_v6_0_cp_gfx_enable(adev, true);
            // WREG32(mmCP_ME_CNTL, 0)     // Clear all halt bits
            // udelay(50)

        // Allocate ring space for CLEAR_STATE:
        //   PACKET3(PREAMBLE_CNTL, 0): PREAMBLE_BEGIN_CLEAR_STATE
        //   For each cs_data section (SECT_CONTEXT):
        //     PACKET3(SET_CONTEXT_REG, count): reg_index, data...
        //   PACKET3(PREAMBLE_CNTL, 0): PREAMBLE_END_CLEAR_STATE
        //   PACKET3(CLEAR_STATE, 0): 0
        //   PACKET3(SET_CONTEXT_REG, 2): 0x316, 0x0e, 0x10
        //     (VGT_VERTEX_REUSE_BLOCK_CNTL + VGT_OUT_DEALLOC_CNTL)
        // Commit ring

    // Ring test
    amdgpu_ring_test_helper(ring);

// Step 4: Compute ring resume
gfx_v6_0_cp_compute_resume(adev);
    // Ring 1 setup
    rb_bufsz = order_base_2(ring_size / 8);
    tmp = (order_base_2(PAGE_SIZE/8) << 8) | rb_bufsz;
    WREG32(mmCP_RB1_CNTL, tmp);
    WREG32(mmCP_RB1_CNTL, tmp | RB_RPTR_WR_ENA);
    ring->wptr = 0;
    WREG32(mmCP_RB1_WPTR, 0);
    WREG32(mmCP_RB1_RPTR_ADDR,    lower_32(rptr_addr));
    WREG32(mmCP_RB1_RPTR_ADDR_HI, upper_32(rptr_addr) & 0xFF);
    mdelay(1);
    WREG32(mmCP_RB1_CNTL, tmp);
    WREG32(mmCP_RB1_BASE, ring_gpu_addr >> 8);

    // Ring 2 setup — same pattern with CP_RB2_* registers

    // Test both compute rings
    amdgpu_ring_test_helper(&compute_ring[0]);
    amdgpu_ring_test_helper(&compute_ring[1]);

// Step 5: Re-enable GUI idle interrupt
gfx_v6_0_enable_gui_idle_interrupt(adev, true);
```

---

## PHASE 5: DMA HW INIT (si_dma.c)

Programs SDMA/DMA engines. Not relevant for pure compute path.

---

## PHASE 6: SMU HW INIT (si_dpm.c)

Programs SMC firmware, DPM tables, voltage, clocks. Includes:
- SMC firmware load
- Voltage table init
- DPM state table setup
- Performance level configuration
- Fan control

---

## PHASE 7: DCE HW INIT (dce_v6_0.c — display)

Display controller initialization. NOT relevant for bus 2 compute-only GPU.

---

## CRITICAL FINDINGS: What Our Driver Is Missing vs Kernel

### CONFIRMED MISSING ITEMS:

1. **CP_ME_RAM_RADDR = 0** (gfx_v6_0.c:2066)
   - Kernel zeroes this after CP firmware load
   - Register byte offset: 0xC158 (dword 0x3056)
   - Our code: MISSING entirely
   - **Status: Must add to PM4_LoadCPFirmware after firmware stream**

2. **SCRATCH_ADDR = 0** (gfx_v6_0.c:2150)
   - Written as part of cp_gfx_resume, before ring setup
   - Register already in SIReg at offset 34116 (0x8544)
   - Our code: MISSING
   - **Status: Must add to AccelGCN_Init after CP_DEBUG=0**

3. **RLC init_pg ordering** (gfx_v6_0.c:2568-2581)
   - Kernel order: rlc_stop → rlc_reset → init_pg → init_cg → RLC_RL_BASE=0...
   - init_pg writes RLC_SAVE_AND_RESTORE_BASE and RLC_CLEAR_STATE_RESTORE_BASE
   - These MUST come BEFORE RLC_RL_BASE=0
   - Our code: writes them AFTER RLC_RL_BASE (wrong order)
   - **Status: Must reorder in PM4_LoadRLCFirmware**

4. **enable_lbpw after RLC firmware** (gfx_v6_0.c:2607)
   - Called AFTER firmware loaded, BEFORE rlc_start
   - Cape Verde = GDDR5, so lbpw = false
   - lbpw=false: clear LOAD_BALANCE_ENABLE in RLC_LB_CNTL, write SPI_LB_CU_MASK=0x00ff
   - Our code: MISSING this step
   - **Status: Must add between firmware stream and RLC_CNTL=1**

5. **enable_gui_idle_interrupt calls** (gfx_v6_0.c:2302)
   - Kernel calls: disable at rlc_stop, enable at rlc_start
   - Kernel calls: disable at cp_resume start, enable at cp_resume end
   - Operates on CP_INT_CNTL_RING0 bits 19 (CNTX_BUSY) and 20 (CNTX_EMPTY)
   - When disabling: reads DB_DEPTH_INFO, polls RLC_STAT for CLOCK+POWER status
   - Our code: PM4_SoftResetCP writes CP_INT_CNTL_RING0=0 (good for disable)
   - Our code: MISSING the enable calls
   - **Status: Must add enable_gui_idle_interrupt(true) after RLC_CNTL=1 and after CP start**

6. **HDP_HOST_PATH_CNTL read-then-writeback** (gfx_v6_0.c:1845-1846)
   - Kernel: `tmp = RREG32(mmHDP_HOST_PATH_CNTL); WREG32(mmHDP_HOST_PATH_CNTL, tmp);`
   - Our code: hardcodes `0x0F200029`
   - **Status: DANGEROUS — must change to read-then-writeback**
   - **Note: This is in constants_init (GRBM context), different from MC_SI_GpuInit**

### CONFIRMED CORRECT IN OUR CODE:

1. **CP firmware load order**: PFP → CE → ME ✓ (matches kernel gfx_v6_0.c:2036-2061)
2. **CP halt before firmware**: ME_HALT | PFP_HALT | CE_HALT + SCRATCH_UMSK=0 ✓
3. **ME_INITIALIZE packet**: 7 DWORDs with correct args ✓
4. **SET_BASE CE_PARTITION**: 0xc000, 0xe000 ✓
5. **CLEAR_STATE packet sequence**: PREAMBLE_BEGIN → ctx regs → PREAMBLE_END → CLEAR_STATE ✓
6. **Ring setup pattern**: CNTL → CNTL|WR_ENA → WPTR=0 → RPTR_ADDR → delay → CNTL → BASE ✓
7. **RLC reset**: GRBM_SOFT_RESET bit for RLC ✓
8. **VM/GART config**: L1 TLB, L2 cache, context 0 setup ✓

### KEY OBSERVATION: SH_MEM_CONFIG is NOT a kernel concern for SI

The kernel's `gfx_v6_0.c` does NOT write SH_MEM_CONFIG or SH_MEM_BASES anywhere.
These registers are GFX v7+ (CIK) concepts. On SI/GCN1, the compute shader memory
configuration works differently — the VM system handles address translation, and
the shader directly accesses through the GART VA range without SH_MEM mapping.

This means our dispatch path's lack of SH_MEM_CONFIG writes is actually CORRECT
for SI hardware. The compute wavefront launch failure is NOT due to missing
SH_MEM_CONFIG.

### REGISTER BYTE OFFSETS FOR REFERENCE:

All offsets from `gca/gfx_6_0_d.h` (dword offsets × 4 = byte offsets).
*Corrected after agent verification against kernel headers.*

| Register | Dword Offset | Byte Offset | Notes |
|----------|-------------|-------------|-------|
| CP_ME_CNTL | 0x21B6 | 0x86D8 | ME/PFP/CE halt |
| SCRATCH_UMSK | 0x2150 | 0x8540 | Scratch mask |
| SCRATCH_ADDR | 0x2151 | 0x8544 | Scratch base |
| CP_PFP_UCODE_ADDR | 0x3054 | 0xC150 | PFP firmware addr |
| CP_PFP_UCODE_DATA | 0x3055 | 0xC154 | PFP firmware data |
| CP_ME_RAM_RADDR | 0x3056 | 0xC158 | ME firmware read addr |
| CP_ME_RAM_WADDR | 0x3057 | 0xC15C | ME firmware write addr |
| CP_ME_RAM_DATA | 0x3058 | 0xC160 | ME firmware data |
| CP_CE_UCODE_ADDR | 0x305A | 0xC168 | CE firmware addr |
| CP_CE_UCODE_DATA | 0x305B | 0xC16C | CE firmware data |
| CP_RB0_BASE | 0x3040 | 0xC100 | Ring 0 base (gpu_addr>>8) |
| CP_RB0_CNTL | 0x3041 | 0xC104 | Ring 0 control |
| CP_RB0_WPTR | 0x3045 | 0xC114 | Ring 0 write pointer |
| CP_RB1_BASE | 0x3060 | 0xC180 | Ring 1 base |
| CP_RB1_CNTL | 0x3061 | 0xC184 | Ring 1 control |
| CP_RB2_BASE | 0x3065 | 0xC194 | Ring 2 base |
| CP_INT_CNTL_RING0 | 0x306A | 0xC1A8 | Int enable (bits 19,20) |
| RLC_CNTL | 0x30C0 | 0xC300 | RLC enable/disable |
| GRBM_SOFT_RESET | 0x2008 | 0x8020 | Soft reset register |
| RLC_LB_CNTL | - | 0xC30C | Load balance control |
| SPI_LB_CU_MASK | - | 0x9354 | SPI CU mask for LBPW |
| RLC_STAT | - | - | RLC status (clock/power) |
| DB_DEPTH_INFO | - | - | Depth buffer (read for sync) |
| MC_SEQ_MISC0 | - | 0x2A00 | Memory type (DDR3/GDDR5) |

---

## EXACT CALL GRAPH (for Verde init)

```
amdgpu_device_ip_init
  ├─ si_common_hw_init
  │   ├─ si_fix_pci_max_read_req_size
  │   ├─ si_init_golden_registers (verde golden + rlc golden + verde_mgcg_cgcg_init + verde_pg_init)
  │   ├─ si_pcie_gen3_enable
  │   └─ si_program_aspm
  │
  ├─ gmc_v6_0_hw_init
  │   ├─ gmc_v6_0_mc_program
  │   │   ├─ HDP init (32 × 5 zeroed regs)
  │   │   ├─ HDP_REG_COHERENCY_FLUSH_CNTL = 0
  │   │   ├─ wait_for_idle (SRBM_STATUS)
  │   │   ├─ VGA lockout
  │   │   ├─ MC_VM_SYSTEM_APERTURE_LOW/HIGH/DEFAULT
  │   │   ├─ MC_VM_AGP_BASE/TOP/BOT
  │   │   └─ wait_for_idle
  │   ├─ gmc_v6_0_mc_load_microcode
  │   │   ├─ MC_SEQ_SUP_CNTL check (skip if already running)
  │   │   ├─ MC_SEQ_IO_DEBUG_INDEX/DATA pairs
  │   │   ├─ MC_SEQ_SUP_PGM stream
  │   │   └─ wait TRAIN_DONE_D0/D1
  │   └─ gmc_v6_0_gart_enable
  │       ├─ MC_VM_MX_L1_TLB_CNTL (L1 enable + advanced driver model)
  │       ├─ VM_L2_CNTL (L2 enable + fragment + queue size)
  │       ├─ VM_L2_CNTL2 (invalidate all)
  │       ├─ VM_L2_CNTL3 (fragment size)
  │       ├─ VM_CONTEXT0_* (GART page table, flat)
  │       ├─ VM_CONTEXT1-15 (VM page tables, 1-level PDE)
  │       ├─ fault enable defaults
  │       └─ VM_INVALIDATE_REQUEST (flush TLB)
  │
  ├─ si_ih_hw_init (IH ring setup)
  │
  ├─ gfx_v6_0_hw_init
  │   ├─ gfx_v6_0_constants_init
  │   │   ├─ chip config (Verde SE/SH/CU/backend counts)
  │   │   ├─ GRBM_CNTL, SRBM_INT_CNTL/ACK, BIF_FB_EN
  │   │   ├─ GB_ADDR_CONFIG propagation (×6 regs)
  │   │   ├─ tiling_mode_table_init (32 tile modes)
  │   │   ├─ setup_rb (per SE/SH render backend config)
  │   │   ├─ setup_tcc (TCP channel steering)
  │   │   ├─ setup_spi (SPI_STATIC_THREAD_MGMT_3)
  │   │   ├─ CP_QUEUE_THRESHOLDS, CP_MEQ_THRESHOLDS
  │   │   ├─ SX_DEBUG_1 read-writeback
  │   │   ├─ SPI_CONFIG_CNTL_1, PA_SC_FIFO_SIZE
  │   │   ├─ VGT_NUM_INSTANCES=1, CP_PERFMON_CNTL=0, SQ_CONFIG=0
  │   │   ├─ PA_SC_FORCE_EOV_MAX_CNTS, VGT_CACHE_INVALIDATION
  │   │   ├─ VGT_GS_VERTEX_REUSE=16, PA_SC_LINE_STIPPLE_STATE=0
  │   │   ├─ CB_PERFCOUNTER*=0 (×8)
  │   │   ├─ *** HDP_HOST_PATH_CNTL read-writeback ***
  │   │   ├─ PA_CL_ENHANCE
  │   │   └─ udelay(50)
  │   │
  │   ├─ gfx_v6_0_rlc_resume
  │   │   ├─ rlc_stop (RLC_CNTL=0, disable gui_idle_int, wait serdes)
  │   │   ├─ rlc_reset (GRBM_SOFT_RESET RLC bit toggle)
  │   │   ├─ *** init_pg (RLC_SAVE_AND_RESTORE_BASE, RLC_CLEAR_STATE_RESTORE_BASE) ***
  │   │   ├─ init_cg (NOP)
  │   │   ├─ RLC_RL_BASE=0, RLC_RL_SIZE=0, RLC_LB_CNTL=0
  │   │   ├─ RLC_LB_CNTR_MAX=0xffffffff, RLC_LB_CNTR_INIT=0
  │   │   ├─ RLC_LB_INIT_CU_MASK=0xffffffff
  │   │   ├─ RLC_MC_CNTL=0, RLC_UCODE_CNTL=0
  │   │   ├─ RLC firmware stream (with per-word ADDR set)
  │   │   ├─ RLC_UCODE_ADDR=0
  │   │   ├─ *** enable_lbpw(false): clear LB_ENABLE, SPI_LB_CU_MASK=0x00ff ***
  │   │   └─ rlc_start (RLC_CNTL=1, enable gui_idle_int, udelay(50))
  │   │
  │   └─ gfx_v6_0_cp_resume
  │       ├─ *** enable_gui_idle_interrupt(false) ***
  │       ├─ cp_gfx_load_microcode
  │       │   ├─ cp_gfx_enable(false): ME_HALT|PFP_HALT|CE_HALT, SCRATCH_UMSK=0
  │       │   ├─ PFP firmware: ADDR=0, stream DATA, ADDR=0
  │       │   ├─ CE firmware: ADDR=0, stream DATA, ADDR=0
  │       │   ├─ ME firmware: WADDR=0, stream DATA, WADDR=0
  │       │   ├─ PFP_ADDR=0, CE_ADDR=0, ME_WADDR=0
  │       │   └─ *** ME_RADDR=0 ***
  │       ├─ cp_gfx_resume
  │       │   ├─ CP_SEM_WAIT_TIMER=0, CP_SEM_INCOMPLETE_TIMER_CNTL=0
  │       │   ├─ CP_RB_WPTR_DELAY=0
  │       │   ├─ CP_DEBUG=0
  │       │   ├─ *** SCRATCH_ADDR=0 ***
  │       │   ├─ Ring 0: CP_RB0_CNTL, WPTR=0, RPTR_ADDR, SCRATCH_UMSK=0
  │       │   ├─ mdelay(1)
  │       │   ├─ CP_RB0_BASE
  │       │   ├─ cp_gfx_start (ME_INIT + SET_BASE + unhalt + CLEAR_STATE)
  │       │   └─ ring test
  │       ├─ cp_compute_resume
  │       │   ├─ Ring 1: CP_RB1_CNTL, WPTR=0, RPTR_ADDR, mdelay(1), BASE
  │       │   ├─ Ring 2: CP_RB2_CNTL, WPTR=0, RPTR_ADDR, mdelay(1), BASE
  │       │   └─ ring tests ×2
  │       └─ *** enable_gui_idle_interrupt(true) ***
  │
  ├─ si_dma_hw_init (DMA0/DMA1 ring setup)
  │
  ├─ si_smu_hw_init (SMC firmware, DPM, voltages)
  │
  └─ dce_v6_0_hw_init (display — NOT relevant for bus 2)
```

---

## NOTES ON OUR DRIVER'S CURRENT STATE

### What bus2_writes.txt trace shows:
- Lines 130-131: `WR HDP_HOST_PATH_CNTL = 0x0F200029` and `WR HDP_MISC_CNTL = 0x00121FE0`
  - These are in our MC_SI_GpuInit
  - HDP_HOST_PATH_CNTL should be read-then-writeback per kernel
  - HDP_MISC_CNTL we have marked as DANGEROUS in gpu-crash.md
- The trace shows our init sequence includes AtomBIOS init (register 0x0030 etc.)
  which the kernel does NOT do in the GFX init path (it's done earlier in VBIOS POST)

### SH_MEM_CONFIG clarification:
- SI/GCN1 does NOT use SH_MEM_CONFIG — this is a CIK+ (GFX v7+) register
- The kernel's `gfx_v6_0.c` has ZERO references to SH_MEM
- Compute shaders on SI access memory through the VM system directly
- Our SET_SH_REG writes for compute dispatch are the correct way to program
  compute state on SI — via PM4 packets, not via MMIO SH_MEM registers

### Compute Ring Architecture:
- The kernel creates 2 compute rings (GFX6_NUM_COMPUTE_RINGS = 2)
- Ring 1 = compute_ring[0], Ring 2 = compute_ring[1]
- Both use CP_RB1_*/CP_RB2_* registers
- ME=1, PIPE=0/1, QUEUE=0/1 for the two compute rings
- Ring test uses SET_CONFIG_REG to write SCRATCH_REG0 (same as GFX ring test)

---

*Generated from kernel source at /home/bob/linux/drivers/gpu/drm/amd/amdgpu/ — cross-referenced to exact line numbers*

---

## APPENDIX: AGENT VERIFICATION RESULTS (2026-06-29)

Three independent verification agents cross-checked every claim in this document against the
actual kernel source files. Results summary:

### Agent 1: GMC/GART/VM (vs gmc_v6_0.c) — 28 claims checked
- **26 CORRECT**, 2 minor issues (corrected above):
  - `set_fault_enable_default` is conditional on `amdgpu_vm_fault_stop` — fixed
  - `VM_INVALIDATE_REQUEST` goes through `gmc_v6_0_flush_gpu_tlb()` indirection — fixed

### Agent 2: GFX/CP/RLC (vs gfx_v6_0.c) — 100+ claims checked
- All function names, line numbers, call ordering, register names: **CORRECT**
- All register values (except GB_ADDR_CONFIG golden): **CORRECT**
- SH_MEM_CONFIG non-existence on SI: **CONFIRMED** (zero grep matches)
- **Errors found and corrected above:**
  - `VERDE_GB_ADDR_CONFIG_GOLDEN` was 0x02010002, kernel defines 0x12010002 — fixed
  - 13/18 register byte offsets were wrong (PFP/CE/ME swapped, CP_RB* from legacy r600 space) — fixed
  - SCRATCH_UMSK byte offset was 0x8568, should be 0x8540 — fixed
  - SPI_LB_CU_MASK notation inconsistency (0xFF vs 0x00ff) — fixed

### Agent 3: Golden Regs / IP Order (vs si.c) — 40+ claims checked
- IP block ordering (blocks 1-9): **CORRECT** (display block conditional noted)
- si_common_hw_init call order: **CORRECT**
- verde_golden_registers: 31/31 entries **CORRECT**, 3 entries were MISSING — added
- verde_golden_rlc_registers: 6/6 entries **CORRECT**
- verde_pg_init description: **CORRECT** (count updated ~100→123)
- **CRITICAL FINDING:** `verde_mgcg_cgcg_init` (98 entries, si.c:668-766) was completely
  omitted from document — **added as new section above**
- Golden registers line reference was si.c:303, should be si.c:313 — fixed

### Overall Accuracy After Corrections
- **Phase 0 (IP blocks)**: Fully verified ✓
- **Phase 1 (Common HW init)**: Fully verified ✓ (with verde_mgcg_cgcg_init now documented)
- **Phase 2 (GMC)**: Fully verified ✓
- **Phase 4 (GFX)**: Fully verified ✓
- **Register byte offset table**: Fully corrected ✓
- **Critical findings #1-#6**: All verified correct ✓
- **Call graph**: Fully verified ✓
