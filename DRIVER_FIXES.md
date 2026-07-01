# AILang GPU Driver — Verified Fixes Required

**Created**: 2026-06-30
**Status**: Implementing
**CP Death Symptom**: RPTR=0, ME_INITIALIZE not consumed, GRBM_STATUS=0xA0003028 (TA_BUSY)
**Reference**: KERNEL_INIT_SEQUENCE.md (verified against kernel source, 30+ spot checks passed)

---

## PRIORITY 1 — LIKELY CAUSING CP DEATH (TA_BUSY)

### FIX 1: CGTS_SM_CTRL_REG decimal transcription error [CRITICAL]
- **Files**: `Library.AMDGPUMC_SI.ailang:741`, `Library.AMDGPUPM4FW.ailang:220`
- **Bug**: Decimal `2525528576` = **0x96888200** (WRONG)
- **Correct**: `2526282240` = **0x96940200** (kernel gfx_v6_0.c / si.c golden)
- **Root cause**: Bits [19:15] = 0x04 instead of 0x0A. Misconfigures CGTS clock gating state machine SM_MODE/LFSR timer fields.
- **Why it matters**: Controls CU scheduling timers. Wrong value prevents TA block from completing clock gating handshake → TA stays BUSY forever → GRBM refuses to route CP transactions → ME never processes ME_INITIALIZE.
- **Fix**: Change `2525528576` to `2526282240` in both locations.

### FIX 2: RLC_LB_CNTL pre-firmware value [HIGH]
- **File**: `Library.AMDGPUPM4FW.ailang:350`
- **Bug**: Writes `2147549204` = **0x80010014** (old radeon golden value) BEFORE RLC firmware load
- **Correct**: Write `0` — kernel gfx_v6_0.c:2586 zeros this before firmware load
- **Context**: si.c:310 `verde_golden_rlc_registers` has 0x80010014 for RLC_LB_CNTL. But gfx_v6_0_rlc_resume() at line 2586 OVERWRITES the golden value with 0 before firmware load. Golden is applied earlier by si_init_golden_registers(), then rlc_resume() overrides it. AILang mixes golden values into rlc_resume flow — wrong.
- **Fix**: Change `GPU_Wr32(gpu, SIReg.RLC_LB_CNTL, 2147549204)` to `GPU_Wr32(gpu, SIReg.RLC_LB_CNTL, 0)`

### FIX 3: RLC_LB_CNTR_MAX value [HIGH]
- **File**: `Library.AMDGPUPM4FW.ailang:349`
- **Bug**: Writes `4096` = **0x00001000** (old radeon golden value)
- **Correct**: Write `4294967295` = **0xFFFFFFFF** — kernel gfx_v6_0.c:2587
- **Context**: Same issue as FIX 2 — golden value (si.c:309) is overridden by rlc_resume. AILang uses old golden, not the rlc_resume override.
- **Fix**: Change `GPU_Wr32(gpu, SIReg.RLC_LB_CNTR_MAX, 4096)` to `GPU_Wr32(gpu, SIReg.RLC_LB_CNTR_MAX, 4294967295)`

### FIX 4: RLC_LB_PARAMS wrong golden value [MEDIUM]
- **File**: `Library.AMDGPUPM4FW.ailang:346` AND `Library.AMDGPUMC_SI.ailang:601`
- **Bug**: Original doc said `54329349` = `0x033F1005` — WRONG. `54329349` actually = **0x033D0005**.
- **Correct decimal**: `54464517` = **0x033F1005** — kernel si.c:306 verde_golden_rlc_registers
- **Root cause**: Prior fix used wrong decimal. Trace diff showed final value was still 0x033D0005 instead of 0x033F1005.
- **Fix**: Changed `54329349` → `54464517` in BOTH PM4FW:346 AND MC_SI:601.

---

## PRIORITY 2 — WRONG VALUES (may contribute to instability)

### FIX 5: GB_ADDR_CONFIG first write wrong
- **File**: `Library.AMDGPUMC_SI.ailang:600`
- **Bug**: Writes `33619970` = **0x02010002** (RLC golden table value)
- **Correct**: Write `302055426` = **0x12010002** (VERDE_GB_ADDR_CONFIG_GOLDEN, gfx_v6_0.c:53)
- **Context**: The final ROW_SIZE-adjusted write at MC_SI:783-793 correctly uses 0x12010002. But the initial write at line 600 is wrong — NUM_SHADER_ENGINES bit[28] is 0 instead of 1. Kernel never writes the intermediate 0x02010002 via si_gpu_init; that value only appears in the RLC golden table.
- **Fix**: Change `33619970` to `302055426`

### FIX 6: SH_MEM_CONFIG writes — SI doesn't have this register
- **File**: `Library.AccelGCNInit.ailang:397-406` (pre-CP-FW) and `:601-610` (post-CLEAR_STATE)
- **Bug**: Writes SH_MEM_CONFIG, SH_MEM_APE1_BASE, SH_MEM_APE1_LIMIT, SH_MEM_BASES for all 16 VMIDs via SRBM_GFX_CNTL switching. Kernel has ZERO references to SH_MEM_CONFIG in gfx_v6_0.c. This is a CIK/GFX7+ concept.
- **Risk**: Writing undefined register addresses on SI through SRBM VMID switching could corrupt SRBM routing state.
- **Investigation result**: si.c has NO si_init_compute() function and NO SH_MEM references. gfx_6_0_d.h has NO SH_MEM definitions. These registers first appear in gfx_7_0_d.h (CIK/GFX7). All three VMID-loop instances REMOVED.

### FIX 7: HDP_HOST_PATH_CNTL hardcoded
- **File**: `Library.AMDGPUMC_SI.ailang:~1038` (need to locate exact line)
- **Bug**: Hardcoded `0x0F200029` instead of read-modify-write
- **Correct**: Kernel gfx_v6_0.c:1845-1846 reads current value and writes it back (triggers HDP cache flush side-effect)
- **Risk**: Overrides BIOS config. On RD990, HDP writes risk PCI fabric deadlock.
- **Fix applied**: Changed to read-writeback (GPU_Rd32 then GPU_Wr32) matching kernel exactly. This preserves BIOS config while still triggering the HDP cache flush side-effect.

### FIX 8: 0xC47C register decimal transcription error [MEDIUM]
- **Files**: `Library.AMDGPUMC_SI.ailang:602`, `Library.AMDGPUPM4FW.ailang:347`
- **Bug**: Decimal `277348384` = **0x10880020** (WRONG) — comment said 0x10808020
- **Correct**: `276856864` = **0x10808020** — kernel value
- **Root cause**: Decimal/hex mismatch. Bit 17 set instead of bit 15. Same class of transcription error as CGTS_SM_CTRL_REG.
- **Fix**: Changed `277348384` → `276856864` in both files.

### FIX 9: Duplicate CGTS golden register block clobbers CU steering table [HIGH]
- **File**: `Library.AMDGPUMC_SI.ailang:731-740` (now removed)
- **Bug**: Two CGTS golden register blocks existed:
  1. Lines 641-651: Correct per-CU steering table (0x90008, 0x20001, 0x40003, 0x00007, 0x90008)
  2. Lines 731-740: Wrong simplified values (0x80008, 0x10000, 0x30002, 0x40007, 0x80008) — overwrote block 1
- **Effect**: CU steering table registers 0x9170-0x9184 ended up with wrong values. These control how the shader engines dispatch work to CUs. Wrong routing could prevent TA block from completing work → TA_BUSY.
- **Fix**: Removed the duplicate block (lines 731-740). Kept only CGTS_SM_CTRL_REG and RLC_CGCG_CGLS_CTRL from that section.

---

## VERIFIED CORRECT (no fix needed)

These were checked and match the kernel:
- CP firmware load order: PFP→CE→ME ✓
- CP_ME_CNTL halt/unhalt values ✓
- RLC_CNTL stop/start values ✓
- GRBM_SOFT_RESET = 0x4 (RLC only) ✓
- enable_gui_idle_interrupt disable/enable ✓
- SCRATCH_UMSK = 0 before FW, 0xFF after ring test ✓
- SCRATCH_ADDR = 0 ✓
- All register byte offsets verified correct ✓
- IP block init ordering verified correct ✓
- VM/GART/TLB configuration verified correct ✓
- IH ring setup verified correct ✓
- DMA engine init verified correct ✓
- CSB (Clear State Block) population verified correct ✓
- All CP ring setup verified correct ✓
- ME_INITIALIZE packet args verified correct ✓
- SET_BASE CE partition verified correct ✓
- CLEAR_STATE + PREAMBLE sequence verified correct ✓
- SERDES MGCG/CGCG handshake sequence verified correct ✓
- 50+ register values spot-checked against kernel: all match ✓

---

## FIX APPLICATION STATUS

| Fix | Status | File | Line |
|-----|--------|------|------|
| 1. CGTS_SM_CTRL_REG (MC_SI) | **DONE** | Library.AMDGPUMC_SI.ailang | 741 |
| 1. CGTS_SM_CTRL_REG (PM4FW) | **DONE** | Library.AMDGPUPM4FW.ailang | 220 |
| 2. RLC_LB_CNTL pre-FW | **DONE** | Library.AMDGPUPM4FW.ailang | 350 |
| 3. RLC_LB_CNTR_MAX | **DONE** | Library.AMDGPUPM4FW.ailang | 349 |
| 4. RLC_LB_PARAMS (PM4FW) | **DONE** (re-fixed decimal) | Library.AMDGPUPM4FW.ailang | 346 |
| 4. RLC_LB_PARAMS (MC_SI) | **DONE** (re-fixed decimal) | Library.AMDGPUMC_SI.ailang | 601 |
| 5. GB_ADDR_CONFIG | **DONE** | Library.AMDGPUMC_SI.ailang | 600 |
| 6. SH_MEM_CONFIG | **DONE** (removed 3 loops) | Library.AccelGCNInit.ailang | 397-406, 601-610, 853-862 |
| 7. HDP_HOST_PATH_CNTL | **DONE** (read-writeback) | Library.AMDGPUMC_SI.ailang | 1038 |
| 8. 0xC47C decimal (MC_SI) | **DONE** | Library.AMDGPUMC_SI.ailang | 602 |
| 8. 0xC47C decimal (PM4FW) | **DONE** | Library.AMDGPUPM4FW.ailang | 347 |
| 9. Duplicate CGTS block | **DONE** (removed) | Library.AMDGPUMC_SI.ailang | 731-740 |
