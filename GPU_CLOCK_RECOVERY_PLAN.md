# GPU Clock Recovery & Test Campaign

## Status: WAITING — hardware reconfiguration needed

## Problem
Setting SCLK to 1GHz on the HD 7770 (GCN 1.0 / Southern Islands) tanks the display
because the card is running VESA framebuffer and the SPLL clock change glitches the
CRTC scanout. Previous attempts used `test_sclk.ailang` which lacked CRTC blanking
and the `SPLL_CTLREQ_CHG` handshake.

## Solution: Dual-GPU Setup
- **Display card**: Second HD 7770 in a second PCIe slot, running off slot power only (75W),
  VESA framebuffer for display. No compute, no 6-pin power cable needed.
- **Compute card**: Primary HD 7770 (with 6-pin power), no display attached, zero active CRTCs.
  This is the card we clock up for GCN compute.
- **BIOS**: Set the display card's slot as primary display adapter.

### Why this works
- Compute card has zero active CRTCs, so SCLK changes can't glitch scanout
- If compute card's PCIe bus locks, terminal is still alive on the display card
- Recovery tools (`reset_gpu.x`, `pci_reset.x`) can be run from the display card's terminal

## Existing Code (all working, already built)

### Clock Harness
- `TestCode/test_sclk_safe.ailang` — Full SCLK reprogramming with:
  - DPM table scan for boot-voltage-safe target
  - 12.14 fixed-point FBDIV with VCO range validation (600-1200 MHz)
  - Kernel-style SPLL sequence: powerdown -> program -> powerup
  - `SPLL_CTLREQ_CHG` handshake (the fix for the old crash)
  - `SPLL_CNTL_MODE` SW direct control for powerdown/powerup
  - DCE6 CRTC blanking before clock switch, unblanking after
  - Emergency unblank on every failure path
  - Crash-safe breadcrumb log (`sclk_safe_log.txt`) with `fdatasync` per step
- Build: `./ailang.x TestCode/test_sclk_safe.ailang -o test_sclk_safe.x`

### Old Harness (DO NOT USE — causes the crash)
- `TestCode/test_sclk.ailang` — No CRTC blanking, no CTLREQ_CHG handshake.
  This is what was crashing the display. Superseded by `test_sclk_safe.ailang`.

### Recovery Tools
- `TestCode/reset_gpu.ailang` → `reset_gpu.x` — MC-safe GPU soft reset
  (halt CP, halt RLC, MC blackout, GRBM+SRBM reset, MC resume, restart RLC+CP)
- `TestCode/pci_reset.ailang` → `pci_reset.x` — PCI-level reset
- Nuclear option from shell: `echo 1 > /sys/bus/pci/devices/<BDF>/remove && echo 1 > /sys/bus/pci/rescan`

### Display Library
- `Librarys/Drivers/AMDGPU/Library.AMDGPUDisplay.ailang` — DCE6 CRTC pipe lookup,
  `DCE6_IsCRTCActive()`, `DCE6_BlankCRTC()`, `DCE6_UnblankCRTC()`,
  `DCE6_BlankAllActive()`, `DCE6_UnblankAllActive()`

### Read-only Diagnostics
- `TestCode/test_sclk_readonly.ailang` — Decode SPLL state, no writes
- `TestCode/test_sclk_decode.ailang` — Decode SPLL dividers
- `TestCode/test_gpu_discover.ailang` — Enumerate GPUs on PCI bus

## Code Changes Needed After Hardware Install

### 1. Auto-select compute GPU (test_sclk_safe.ailang)
Currently hardcodes `gpu = 0`. Need to:
- Call `GPU_Discover()` — will return 2
- Check `DCE6_IsCRTCActive(gpu, pipe)` for all 6 pipes on each GPU
- Pick the GPU index with zero active CRTCs (that's the compute card)
- If both have active CRTCs or neither does, print error and bail

### 2. Incremental DPM stepping
Currently jumps to the highest boot-safe DPM clock. Change to:
- Start at DPM level 0 (lowest clock)
- Verify PLL lock and stability
- Step to DPM level 1, verify
- Continue up to max boot-safe level
- This isolates which specific DPM entry (if any) causes problems

### 3. Fix reset_gpu.ailang GPU index
Currently hardcodes GPU index 0. Need to accept target index or auto-detect
the wedged card (the one NOT driving display).

## Test Sequence After Hardware Ready

1. Boot with dual GPUs, monitor on display card
2. Run `test_gpu_discover.x` — note which index is display vs compute
3. Run `test_sclk_readonly.x` on compute card — verify SPLL state readable
4. Run `test_sclk_safe.x` — verify Phase 3 shows `Active CRTCs: 0` on compute card
5. Let Phase 5 run (SPLL reprogram) — display stays on other card
6. If display survives: success, check `sclk_safe_log.txt` for verification
7. If compute card bus locks: run `reset_gpu.x` from display card terminal
8. Once working at one DPM level, step up to next level and repeat

## Hardware Inventory
- 2x HD 7770 (GV-R777OC-1GD/F71, Southern Islands GCN 1.0)
- R9 290x cards (need PSU upgrade, 250W+ each)
- HD 7990 (need PSU upgrade, 375W dual-GPU)

## Files Referenced
```
TestCode/test_sclk_safe.ailang     — clock harness (USE THIS ONE)
TestCode/test_sclk.ailang          — old harness (DO NOT USE)
TestCode/test_sclk_readonly.ailang — read-only diagnostic
TestCode/test_sclk_decode.ailang   — SPLL decode
TestCode/reset_gpu.ailang          — GPU soft reset
TestCode/pci_reset.ailang          — PCI reset
TestCode/test_gpu_discover.ailang  — GPU enumeration
TestCode/test_crtc_blank.ailang    — CRTC blanking test
TestCode/test_crtc_scan.ailang     — CRTC scan test
Librarys/Drivers/AMDGPU/Library.AMDGPUDisplay.ailang    — DCE6 display helpers
Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Regs.ailang    — register definitions
Librarys/Accel/Library.AccelGCN.ailang                   — production SetSCLK (line 335)
WIP_SCLK_CLOCK_SETTING.md         — original WIP notes (still valid reference)
```
