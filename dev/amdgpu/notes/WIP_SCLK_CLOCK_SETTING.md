# WIP: SCLK Clock Setting for GCN Compute

## Goal
Set SCLK (engine clock) on AMD GCN 1.0 (Southern Islands) GPU to run LLM engine
at full performance clocks without blanking the display / locking the machine.

## Status: IN PROGRESS

## What We Know

### Current test_sclk.ailang behavior
- Saves SPLL registers, reprograms SCLK to MAX_ENGINE_CLK from AtomBIOS
- **Blanks display at bypass-disable (line 387)** because CRTC scanout loses
  coherent clocking when SPLL output changes under it
- Has voltage guard (skip if target needs >100mV above boot VDDC)
- Has save/restore of SPLL registers
- Restore sequence is correct (bypass->reset->program->unreset->lock->unbypass)

### AccelGCN_SetSCLK (Library.AccelGCN.ailang:335)
- Production version of the same SPLL reprogram sequence
- Same problem: no display quenching before clock switch
- Called from AccelGCN_Init, currently non-fatal if it fails

### Register definitions (Library.AMDGPUPM4Regs.ailang)
- SPLL registers: 0x600-0x624 (CG_SPLL_FUNC_CNTL family) -- DONE
- SPLLBits: all bit masks defined -- DONE
- VGA_RENDER_CONTROL: 0x300 -- exists, used in reset_gpu
- **NO CRTC registers defined yet** (need EVERGREEN_CRTC_CONTROL etc.)
- **NO GRPH_ENABLE register defined**

### GPU info
- Southern Islands (GCN 1.0): TAHITI, PITCAIRN, VERDE, OLAND, HAINAN
- Display engine: DCE 6.x (Evergreen-family register layout)
- CRTC registers are per-pipe at 0x6DF0 stride (CRTC0 base ~0x6DF0)

## Root Cause of Screen Blank
When SPLL bypass is disabled (switching engine from ref clock to PLL output),
the display controller's scanout timing glitches because:
1. SCLK drives the memory controller read path for scanout
2. The instantaneous frequency change causes the CRTC to lose sync
3. Monitor blanks, GPU may hang waiting for scanout that never completes

## Fix Strategy

### Phase 1: Read-only clock test (SAFE - no writes)
- Read and decode current SPLL state
- Read AtomBIOS target clocks
- Compare current vs target
- Print what WOULD happen
- **NO register writes**

### Phase 2: Add CRTC blanking
SI/DCE6 CRTC registers needed (MMIO byte offsets):
```
EVERGREEN_CRTC_CONTROL          = 0x6E70  (per-CRTC, stride 0x800 per pipe)
EVERGREEN_CRTC_BLANK_CONTROL    = 0x6E74
EVERGREEN_CRTC_STATUS           = 0x6E8C
EVERGREEN_CRTC_STATUS_POSITION  = 0x6E90
EVERGREEN_CRTC_UPDATE_LOCK      = 0x6ED4
EVERGREEN_GRPH_ENABLE           = 0x6800  (per-CRTC, stride 0x800)
EVERGREEN_GRPH_UPDATE           = 0x6844
```

CRTC pipe bases (byte offsets):
```
CRTC0: 0x6DF0 base  (control at 0x6E70)
CRTC1: 0x79F0 base  (control at 0x7A70)  (+0xC00)
CRTC2: 0x105F0 base (control at 0x10670) (+0x8C00)
CRTC3: 0x111F0 base
CRTC4: 0x11DF0 base
CRTC5: 0x129F0 base
```

Sequence for safe SCLK change:
1. For each active CRTC: set CRTC_BLANK_CONTROL to force blank
2. Wait for vblank (poll CRTC_STATUS for VBLANK bit)
3. Do SPLL reprogram sequence
4. Re-enable CRTC blanking (clear force blank)

### Phase 3: Voltage guard improvement
- If MAX_ENGINE_VDDC > BOOT_VDDC, need voltage programming
- Without SMC firmware, voltage control is via GPIO/I2C to VRM
- For now: only allow clocks within boot voltage capability

## Files Involved
- `TestCode/test_sclk.ailang` -- test harness (current crash source)
- `Librarys/Accel/Library.AccelGCN.ailang:335` -- production SetSCLK
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Regs.ailang` -- register defs
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4FW.ailang` -- firmware/init code

## Next Steps
1. [x] Read and understand existing code
2. [ ] Write read-only clock diagnostic test
3. [ ] Add CRTC register definitions to PM4Regs
4. [ ] Add CRTC blank/unblank helper functions
5. [ ] Update test_sclk.ailang with CRTC blanking
6. [ ] Update AccelGCN_SetSCLK with CRTC blanking
7. [ ] Test read-only first, then with blanking
