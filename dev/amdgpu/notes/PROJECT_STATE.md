# Project State — GCN SCLK Crash Fix Applied
## Saved: 2026-05-28

## STATUS: AccelGCN_SetSCLK REWRITTEN — READY TO TEST

The `attn.x` crash at `MODE0_INIT_PRE` was diagnosed and fixed. Root cause was
in `AccelGCN_SetSCLK` — the SPLL clock reprogramming code called during
`AccelGCN_Init`. The function had 4 critical hardware-level bugs. All 4 are now
fixed. `test_attn.x` has been rebuilt and compiles clean (434,428 bytes).

## ROOT CAUSE ANALYSIS

### The crash chain

`attn.x` → `ATTN_Init()` → `HAL_Init()` → `AccelGCN_Init()` → `AccelGCN_SetSCLK()`

The crash log (`attn_crash.txt`) showed:
```
ATTN_START
BACKEND=2
MODE=0
MODE0_INIT_PRE
```
— crash inside `AccelGCN_SetSCLK` during SPLL clock reprogramming.

### Bug 1: FBDIV written as plain integer into 12.14 fixed-point register (CRITICAL)

The `CG_SPLL_FUNC_CNTL_3` register bits[25:0] hold FBDIV in **12.14 fixed-point**
format — top 12 bits = integer multiplier, bottom 14 bits = fractional (÷16384).

**Old code** (`Library.AccelGCN.ailang:407`):
```
new_fbdiv = Divide(target_khz, ref_khz)    // = 300000/27000 = 11
cntl3_new = BitwiseOr(cntl3_new, new_fbdiv) // writes raw 11
```

Hardware interprets raw 11 as: integer = 11>>14 = **0**, frac = 11/16384 = **0.0007**.
VCO = 27 MHz × 0.0007 = **~0.018 MHz**. Engine clock destroyed.

**Fix**: `fbdiv_fixed = (vco_khz * refdiv * 16384) / ref_khz` — proper 12.14 encoding.
For 300 MHz target with PDIV=2: fbdiv_fixed ≈ 364088 (FBDIV_int=22, FBDIV_frac=3352).

### Bug 2: PDIV=1 hardcoded — VCO below 600 MHz minimum

Old code used `new_pdiv = 1` always. With target=300 MHz: VCO = 300×1 = 300 MHz.
The SI SPLL VCO valid range is **600-1200 MHz**. VCO at 300 MHz = unstable/no lock.

**Fix**: Scan PDIV 1..127, pick smallest where `target × PDIV` falls in [600,1200] MHz.

### Bug 3: No CRTC blanking during SPLL reprogram

Reprogramming SPLL while display actively scans can glitch the memory bus.

**Fix**: `DCE6_BlankAllActive(gpu)` before reprogram, `DCE6_UnblankAllActive(gpu)` after.

### Bug 4: No stabilization delays

After PLL lock and after bypass-disable, engine needs ~40-100 µs to stabilize.

**Fix**: `SpinDelay(gpu, 200)` at both points (200 MMIO reads ≈ 40-100 µs).

### Why test_attn.x sometimes passed despite this

The `attn_test_log2.txt` showed `[SCLK] PLL locked after 0 polls` — false positive
from stale `SPLL_CHG_STATUS` bit. Whether the mux actually switches from 27 MHz ref
to the broken PLL output is **non-deterministic**. Sometimes hardware protection kept
engine on ref clock (lucky, test passed at 27 MHz). Sometimes mux switched to garbage
PLL output → PCIe bus deadlock → hard crash.

## WHAT WAS CHANGED (2026-05-28, SCLK fix session)

### File modified: `Librarys/Accel/Library.AccelGCN.ailang`

Three edits to one file:

| Edit | Location | Description |
|------|----------|-------------|
| 1 | Line 32 | Added `LibraryImport.Drivers.AMDGPU.AMDGPUDisplay` |
| 2 | Lines 328-342 | Added `SpinDelay` helper function (MMIO-read spin delay) |
| 3 | Lines 344-703 | Complete rewrite of `AccelGCN_SetSCLK` |

### New AccelGCN_SetSCLK algorithm (ported from proven test_sclk_safe.ailang)

1. **DPM target selection** — walks PowerPlay DPM table, picks highest SCLK where
   VDDC ≤ boot_vddc (950 mV) and VDDC < 0xFF00 (skip SMC-only VID entries).
   Falls back to DEF_ENGINE_CLK if no DPM table.
2. **PDIV computation** — scans 1..127 for smallest PDIV keeping VCO in [600,1200] MHz
3. **FBDIV 12.14 fixed-point** — `fbdiv_fixed = (vco_khz * refdiv * 16384) / ref_khz`
4. **Current SCLK decode** — proper 12.14 split for accurate "already at target" check
5. **CRTC blank** — `DCE6_BlankAllActive(gpu)` before touching SPLL
6. **7-step SPLL reprogram** (matches Linux kernel radeon driver):
   - Disable spread spectrum
   - Enable bypass via HW handshake (BYPASS_EN + CTLREQ_CHG + poll + clear)
   - SPLL powerdown (SW_DIR_CONTROL + RESET + SLEEP + clear SW_DIR)
   - Program dividers (REFDIV, PDIV, FBDIV 12.14 in CNTL_3)
   - SPLL powerup (reverse of powerdown)
   - Poll PLL lock + **stabilization delay** + re-verify lock
   - Disable bypass via HW handshake + **post-bypass delay**
7. **CRTC unblank** — `DCE6_UnblankAllActive(gpu)`

### Error recovery

Every failure path: re-enables bypass (engine stays on 27 MHz ref), unblanks CRTCs,
returns negative error code. Caller in `AccelGCN_Init` treats any negative as
non-fatal ("continuing at boot clocks"). Return codes: 0=success, -1=no AtomBIOS
data, -2=PLL lock/mux timeout, -3=no valid PDIV, -4=no safe DPM entry.

### Binary rebuilt

| Binary | Size | Build command |
|--------|------|---------------|
| `test_attn.x` | 434,428 | `./ailang.x TestCode/test_attn.ailang -o test_attn.x` |

## AFTER REBOOT — IF IT CRASHES AGAIN

### 1. Check the crash logs

```bash
cat ~/Ailang-Self-Hosting-/attn_crash.txt          # if attn.x was run
cat ~/Ailang-Self-Hosting-/attn_test_crash.txt      # if test_attn.x was run
```

### 2. What to look for in SCLK output

If it gets past init, stdout should now show lines like:
```
[SCLK] DPM entries: N, boot VDDC=950 mV
[SCLK] best DPM: XXX MHz @ YYY mV
[SCLK] current=300 MHz, target=XXX MHz (PDIV=N VCO=ZZZ FBDIV=0xABCDEF)
[SCLK] blanked 1 CRTCs
[SCLK] PLL locked after N polls
[SCLK] engine clock now ~XXX MHz (PDIV=N blanked/unblanked=1/1)
```

If you see `[SCLK] already at target, skipping reprogram` — the boot BIOS clock
matches the DPM target (no reprogram needed, no crash risk).

If you see `[SCLK] no safe DPM entry, using DEF_ENGINE_CLK=300 MHz` — DPM table
had no entries within boot voltage. The 300 MHz target with proper PDIV=2 and
12.14 FBDIV should still work correctly (unlike before).

### 3. If crash still at MODE0_INIT_PRE

The SCLK fix is non-fatal — if SCLK fails, AccelGCN_Init continues at boot clocks.
If it still crashes at MODE0_INIT_PRE, the problem is elsewhere in AccelGCN_Init
(ring setup, CP firmware, etc.). Check `attn_crash.txt` for the exact breadcrumb.

### 4. Key diagnostic: does test_attn.x pass?

```bash
sudo ./test_attn.x 2>&1 | tee attn_test_log3.txt
```

If test_attn.x passes all 15 stages AND shows correct SCLK output, the fix works.
Then rebuild and test attn.x:
```bash
./ailang.x ATTN.ailang -o attn.x
sudo ./attn.x
```

## REFERENCE: Previous crash-safe logging (still present)

Both `test_attn.ailang` and `ATTN.ailang` still have the fdatasync breadcrumb
logging from the previous session. Log files: `attn_test_crash.txt`, `attn_crash.txt`.

## HOW TO REBUILD

```bash
cd ~/Ailang-Self-Hosting-
./ailang.x TestCode/test_attn.ailang -o test_attn.x    # test binary
./ailang.x ATTN.ailang -o attn.x                        # full ATTN binary
```

## KEY FILES

| File | Role |
|------|------|
| `Librarys/Accel/Library.AccelGCN.ailang` | **MODIFIED** — AccelGCN_SetSCLK rewritten, SpinDelay added, AMDGPUDisplay imported |
| `TestCode/test_sclk_safe.ailang` | Reference implementation — proven working SCLK reprogram with all safety measures |
| `TestCode/test_attn.ailang` | 15-stage GPU compute stress test with crash-safe logging |
| `ATTN.ailang` | Main attention model — crashes at MODE0_INIT_PRE (should be fixed now) |
| `Librarys/Drivers/AMDGPU/Library.AMDGPUDisplay.ailang` | DCE6 CRTC blank/unblank functions (newly imported by AccelGCN) |
| `Librarys/Drivers/AMDGPU/Library.AMDGPUAtomBIOS.ailang` | AtomBIOS ROM parsing, DPM table, GetField/GetDPMEntry/GetDPMCount |

## All Log Files

| File | Contents |
|------|----------|
| `attn_crash.txt` | Last run: `MODE0_INIT_PRE` = crash in AccelGCN_SetSCLK (the bug we just fixed) |
| `attn_test_crash.txt` | Breadcrumb log from test_attn.x |
| `attn_test_log.txt` | Previous successful test_attn.x run (no SCLK, pre-fix) |
| `attn_test_log2.txt` | Previous test_attn.x run WITH buggy SCLK (passed by luck — 27 MHz ref fallback) |
| `attn_log.txt` | Previous successful attn.x run (no SCLK, pre-fix) |
| `sclk_safe_log.txt` | test_sclk_safe.x breadcrumbs |

## Hardware

- GPU: Cape Verde XT (GCN 1.0, Southern Islands), 10 CUs
- BIOS: GV-R777OC-1GD/F71 (Gigabyte HD 7770)
- Ref clock: 27 MHz
- Boot VDDC: 950 mV
- Boot SCLK: 300 MHz (PDIV=4, FBDIV=44.xxxx in 12.14, VCO≈1200 MHz)
- Driver: radeon/amdgpu blacklisted, using VESA framebuffer
- Display: CRTC 0 active (single monitor)
