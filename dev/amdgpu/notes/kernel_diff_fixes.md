## KERNEL gfx_v6_0 vs OUR CODE — REMAINING FIXES

### Source: /home/bob/linux/drivers/gpu/drm/amd/amdgpu/gfx_v6_0.c

### ALREADY DONE (this session):
1. CP firmware load order: PFP→CE→ME (was PFP→ME→CE) in PM4_LoadCPFirmware
2. Added CP halt + SCRATCH_UMSK=0 before firmware load
3. Added extra addr zeroing: CP_PFP_UCODE_ADDR=0, CP_CE_UCODE_ADDR=0, CP_ME_RAM_WADDR=0, CP_ME_RAM_RADDR=0

### FIX 1: Add CP_ME_RAM_RADDR to SIReg
- File: /home/bob/Ailang-Self-Hosting-/Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Regs.ailang
- Kernel: mmCP_ME_RAM_RADDR = 0x3056 (dword offset), byte = 0x3056*4 = 0xC158 = 49496
- Add near the other CP_ME_RAM_ entries (CP_ME_RAM_WADDR=0xC150, CP_ME_RAM_DATA=0xC154)

### FIX 2: Add SCRATCH_ADDR=0 in AccelGCN_Init
- File: /home/bob/Ailang-Self-Hosting-/Librarys/Accel/Library.AccelGCN.ailang
- Kernel gfx_v6_0_cp_gfx_resume line 2150: WREG32(mmSCRATCH_ADDR, 0)
- Add after the line "GPU_Wr32(gpu, SIReg.CP_DEBUG, 0)" around line 330
- SCRATCH_ADDR is already in SIReg at offset 34116 (0x8544)

### FIX 3: RLC init_pg ordering in PM4_LoadRLCFirmware
- File: /home/bob/Ailang-Self-Hosting-/Librarys/Drivers/AMDGPU/Library.AMDGPUPM4FW.ailang
- Kernel gfx_v6_0_rlc_resume: calls init_pg() BEFORE RLC_RL_BASE etc.
- init_pg (no PG flags, line 2966): writes RLC_SAVE_AND_RESTORE_BASE and RLC_CLEAR_STATE_RESTORE_BASE
- Our code currently writes these AFTER the RLC_LB regs (lines 265-268).
- Move rlc_sr_gpu/GPU_Wr32 RLC_SAVE_AND_RESTORE_BASE and rlc_cs_gpu/GPU_Wr32 RLC_CLEAR_STATE_RESTORE_BASE
  to BEFORE the RLC_RL_BASE=0 write (before line 254).
- Also note: kernel calls init_pg BEFORE the RLC_RL_BASE=0 block, but AFTER rlc_reset.

### FIX 4: enable_lbpw after RLC firmware load
- File: /home/bob/Ailang-Self-Hosting-/Librarys/Drivers/AMDGPU/Library.AMDGPUPM4FW.ailang
- Kernel line 2607: gfx_v6_0_enable_lbpw(adev, lbpw_supported(adev))
- Called AFTER firmware loaded to SRAM, BEFORE rlc_start (RLC_CNTL=1)
- lbpw_supported: read MC_SEQ_MISC0, check bits[31:28]==0xB (DDR3)
- enable_lbpw(true): set bit LOAD_BALANCE_ENABLE in RLC_LB_CNTL
- enable_lbpw(false): clear it, then WREG32(SPI_LB_CU_MASK, 0x00FF)
- Add between firmware stream and RLC_CNTL=1 in PM4_LoadRLCFirmware
- MC_SEQ_MISC0 is already in SIReg. RLC_LB_CNTL is already written.
- SPI_LB_CU_MASK offset: need to look up. Kernel gfx_6_0_d.h has mmSPI_LB_CU_MASK.

### FIX 5: enable_gui_idle_interrupt calls
- File: /home/bob/Ailang-Self-Hosting-/Librarys/Drivers/AMDGPU/Library.AMDGPUPM4FW.ailang and AccelGCN.ailang
- Kernel function at line 2302:
  - enable=false: tmp = RREG32(CP_INT_CNTL_RING0); tmp &= ~(CNTX_BUSY|CNTX_EMPTY); WREG32(CP_INT_CNTL_RING0, tmp)
    Then read DB_DEPTH_INFO, poll RLC_STAT for (GFX_CLOCK_STATUS|GFX_POWER_STATUS)
  - enable=true: tmp = RREG32(CP_INT_CNTL_RING0); tmp |= (CNTX_BUSY|CNTX_EMPTY); WREG32(CP_INT_CNTL_RING0, tmp)
- CNTX_BUSY_INT_ENABLE = bit 19 = 524288
- CNTX_EMPTY_INT_ENABLE = bit 20 = 1048576
- Call points: rlc_stop(false), rlc_start(true), cp_resume start(false), cp_resume end(true)
- Our PM4_SoftResetCP already writes CP_INT_CNTL_RING0=0 (line 551). Good for disable.
- Add enable call after RLC_CNTL=1 in PM4_LoadRLCFirmware.
- Add disable call before CP firmware load, enable call after CP start in AccelGCN_Init.

### FIX 6: HDP_HOST_PATH_CNTL read-then-writeback
- File: /home/bob/Ailang-Self-Hosting-/Librarys/Drivers/AMDGPU/Library.AMDGPUMC_SI.ailang
- Kernel line 1845-1846: hdp_host_path_cntl = RREG32(mmHDP_HOST_PATH_CNTL); WREG32(mmHDP_HOST_PATH_CNTL, hdp_host_path_cntl);
- We currently hardcode 0x0F200029. Change to: read, then write back.
- Around line 956 in MC_SI_GpuInit.

### FIX 7: RLC firmware addr register usage
- Kernel writes WREG32(RLC_UCODE_ADDR, i) for EACH word (sets addr each time)
- Our code sets addr=0 once then streams data words with auto-increment
- Auto-increment should work the same. LOW PRIORITY. Skip for now.

### MMIOTRACE PHASE 15a DETAIL — CP firmware load:
- The mmiotrace shows CP firmware loaded as ME→PFP→CE (seq 433505-439948)
- BUT the kernel source (gfx_v6_0_cp_gfx_load_microcode) does PFP→CE→ME
- The mmiotrace register offsets: ME=REG_0xc150/0xc154, PFP=0xc168/0xc16c, CE=0xc15c/0xc160
- CP_ME_RAM_WADDR=0xC150, CP_ME_RAM_DATA=0xC154
- CP_CE_UCODE_ADDR=0xC15C, CP_CE_UCODE_DATA=0xC160
- CP_PFP_UCODE_ADDR=0xC168, CP_PFP_UCODE_DATA=0xC16C
- Wait — mmiotrace seq 433505 writes CP_ME_CNTL (halt), then 433506 writes SCRATCH_UMSK=0
- Then seq 433507 writes REG_0xc168=0 (that's CP_PFP_UCODE_ADDR!)
- So mmiotrace actually does PFP first too. PFP→CE→ME matches.

### REGISTER OFFSETS TO ADD:
- CP_ME_RAM_RADDR: byte offset 0xC158 = 49496

### CP DEATH STATUS:
- RPTR=0, ME_INITIALIZE not consumed
- GRBM_STATUS=0xA0003028 (TA_BUSY)
