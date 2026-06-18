# GPU Driver Crash Debug — Jun 16, 2026

## Tell Claude

"Read ~/Ailang-Self-Hosting-/gpu-crash.md — I'm testing the GPU driver after the SPLL init ordering fix. Here's what happened: [paste results]"

---

## Root Cause (FOUND)

Hard system lockup caused by **writing GRBM-domain registers before engine clocks are running**.

On fresh boot with radeon unbound from the compute GPU (02:00.0), the SPLL is in reset/bypass — no engine clock. GRBM-routed registers (CP_ME_CNTL, GRBM_SOFT_RESET, CP firmware load regs, etc.) require the engine clock to complete PCI transactions. Writing them without clocks stalls the PCI bus. Both GPUs share the RD990 root complex, so a stalled transaction on the compute GPU freezes the display GPU too — total hard lockup, no kernel panic, no log output.

The DPM/clocking test worked fine because it only touches always-on power domain registers (CG_SPLL_*, SMC) that run on the reference clock — never GRBM-domain registers.

## The Fix (APPLIED — TESTING)

Moved SPLL initialization before the first GRBM-domain register write. Matches the Linux kernel sequence where `radeon_clocks_init()` runs before `si_cp_resume()`.

### Old init order (CRASHED):
```
1. GPU_Discover -> BAR map
2. PM4_HaltCP -> InitMCBase -> SoftResetCP    <-- CRASH: no engine clock
3. CP/RLC firmware -> IH ring -> ring setup
...
9. AtomBIOS -> PP -> Volt -> DPM_SI_InitSPLL  <-- too late
```

### New init order (FIXED):
```
1. GPU_Discover -> BAR map
2. AtomBIOS -> PP -> Volt -> DPM_SI_InitSPLL  <-- engine clocks running
3. PM4_HaltCP -> InitMCBase -> SoftResetCP     <-- safe now
4. CP/RLC firmware -> IH ring -> ring setup -> CP start
5. SMC -> DPM_Init -> DPM_Enable -> Force HIGH
```

### Files modified:
- `Librarys/Accel/Library.AccelGCN.ailang` — moved AtomBIOS/PP/Volt/SPLL init block from after ring setup to before PM4_HaltCP
- `TestCode/test_gpu_stage2.ailang` — added SPLL init imports + init before CP ops; added PCI bus 2 GPU selection
- `TestCode/test_gpu_stage3.ailang` — same fix
- `TestCode/test_gpu_stage4.ailang` — same fix; removed duplicate AtomBIOS/PP/Volt/SPLL from DPM section

All binaries rebuilt Jun 16 19:12.

---

## Stage Tests

Five staged test binaries, each adding one more phase. Run in order.

```bash
cd ~/Ailang-Self-Hosting-
sudo ./test_gpu_stage1.x    # read-only BAR test
sudo ./test_gpu_stage2.x    # CP halt + reset + FW load (was crashing, now fixed)
sudo ./test_gpu_stage3.x    # ring setup + ring test (first CP command)
sudo ./test_gpu_stage4.x    # SMC + DPM enable + force HIGH
sudo ./test_gpu_stage5.x    # full compute dispatch (dst[gid]=src[gid]+42)
```

### Stage 1: `test_gpu_stage1.x` (153KB)
- GPU_Discover, BAR map, one MMIO read, one VRAM read. Zero writes.

### Stage 2: `test_gpu_stage2.x` (380KB)
- **Now includes SPLL init first.** Then PM4_HaltCP, InitMCBase, SoftResetCP, CP/RLC firmware, IH ring, CP misc regs. CP stays halted.

### Stage 3: `test_gpu_stage3.x` (570KB)
- Adds ring setup (all 3), CPStart, RingTest on all 3 rings, SCRATCH roundtrip.

### Stage 4: `test_gpu_stage4.x` (570KB)
- Adds SMC firmware, DPM_Init, DPM_Enable, force HIGH. DPM_Disable on cleanup.

### Stage 5: `test_gpu_stage5.x` (569KB)
- Full AccelGCN_Init, compute kernel build+dispatch, fence wait, readback verify.

---

## Key Architecture

- **Platform**: FX-8320 / RD990 chipset, no AMD-Vi, VFIO impossible
- **GPUs**: Two Cape Verde (GCN 1.0, Southern Islands) sharing PCIe root complex
  - 01:00.0 = display GPU (radeon driver) — NEVER TOUCH
  - 02:00.0 = compute GPU (userspace AILang driver, radeon unbound)
- **Driver**: Entirely userspace AILang. Maps BARs via sysfs, writes registers via mmap'd MMIO
- **VRAM layout**: 64MB base (0x4000000): Rings 0-2, RLC SR/CS, IH ring, shader (256KB), buf desc (4KB), IB scratch (4KB), DATA (rest)
- **DPM**: SMC-managed clock/voltage: boot 302 -> 399 -> 501 -> 1049 MHz
- **Dispatch**: PM4 ring buffer, IB with DISPATCH_DIRECT + CS_PARTIAL_FLUSH, double EOP fence
- **Known silicon bug**: Cape Verde compute event engine leaks dispatch slots after ~36 dispatches. Workaround: periodic full CP reset every 30 dispatches.

## Register Domains (why clocks matter)

- **SRBM-routed** (always-on): CG_SPLL_*, SMC registers, RLC_CGTT_*, MC_VM_*, BIF_FB_EN — these work on reference clock, safe to write anytime
- **GRBM-routed** (engine clock required): CP_ME_CNTL, GRBM_SOFT_RESET, CP_PFP_UCODE_*, CP_ME_RAM_*, SPI_*, SCRATCH_REG*, most GPU pipeline regs — need SPLL locked before writing

## Interpreting Test Results

- **Stage 1 locks up**: mmap of compute GPU BAR is the problem. Check if radeon is still bound to 02:00.0.
- **Stage 2 locks up**: SPLL init failed or a new GRBM-domain write is happening before clocks. Check SPLL output.
- **Stage 3 locks up**: CP command execution (ring buffer / NOP / CLEAR_STATE) is the problem.
- **Stage 4 locks up**: SMC/DPM interaction after CP is running.
- **Stage 5 locks up**: Compute dispatch. Check breadcrumbs BC0-BC4 in VRAM fence dump.
- **All pass**: Driver is working.

---

## Crash #2: HDP + WC BAR0 Lockup — Jun 16, 2026 ~20:20 EDT

### Symptom
Hard system lockup during `test_accel_gcn.x` or `test_gpu_stage5.x` run.
Required hard power reset. No dmesg/journal logs survived (PCI fabric deadlock
freezes the entire system including journald).

### Root Cause (SUSPECTED)
Two changes in combination deadlocked the PCI bus:

1. **`HDP_HOST_PATH_CNTL` zeroed** (`PM4_InitMCBase` in `Library.AMDGPUPM4Ring.ailang`)
   — blindly writing 0 to `HDP_HOST_PATH_CNTL` (0x2C00) destroys the BIOS-configured
   HDP routing. The Linux kernel does a read-modify-write on specific bits, never a
   blind zero. This misconfigures how CPU writes through BAR0 reach VRAM.

2. **BAR0 opened without `O_SYNC`** (`GPU_BAR_MapVRAM` in `Library.AMDGPUBAR.ailang`)
   — removing `O_SYNC` switches BAR0 from UC (uncacheable) to WC (write-combining).
   WC stores are buffered and reordered by the CPU. With HDP routing broken, the
   SFENCE + HDP flush sequence cannot correctly drain these writes. The GPU reads
   VRAM directly and sees stale/zero data, or worse, the HDP stalls waiting for a
   completion that never comes — deadlocking the PCI fabric.

Also added but less likely to cause lockup alone:
- `HDP_NONSURFACE_BASE/INFO/SIZE` register writes (removed with HDP_HOST_PATH_CNTL)
- Page fault-in loops (DWORD read per 4KB page) in `AccelGCN_VramWrite`/`VramRead`
- `HDP_MEM_COHERENCY_FLUSH_CNTL` flushes in VramWrite/VramRead/Upload (kept — these are correct)

### Original Problem These Changes Tried to Fix
Trash/garbage values when reading VRAM after GPU compute dispatch. Shader results
were not visible to CPU reads through BAR0. Suspected cause: HDP read cache serving
stale data, or UC mapping silently dropping SSE2 stores.

### Fix Applied
- **Removed** all HDP register writes from `PM4_InitMCBase` (HOST_PATH_CNTL,
  NONSURFACE_BASE/INFO/SIZE) — keep BIOS defaults
- **Restored** `O_SYNC` on BAR0 VRAM mapping — back to UC
- **Kept** HDP flush calls (`HDP_MEM_COHERENCY_FLUSH_CNTL = 1`) in VramWrite/VramRead/Upload
- **Kept** page fault-in loops (harmless under UC)
- **Kept** PCIe read-back barriers after flushes

### Files Modified
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Ring.ailang` — commented out HDP register writes in PM4_InitMCBase
- `Librarys/Drivers/AMDGPU/Library.AMDGPUBAR.ailang` — restored `O_SYNC` flag in GPU_BAR_MapVRAM

### If Trash Values Recur
The HDP flush (`HDP_MEM_COHERENCY_FLUSH_CNTL = 1`) should handle CPU→GPU coherency
under UC mapping without touching `HDP_HOST_PATH_CNTL`. If values are still wrong:
1. Verify HDP flush is happening BEFORE GPU reads (in VramWrite) and AFTER GPU writes (in VramRead)
2. Try read-modify-write on `HDP_HOST_PATH_CNTL` instead of zeroing it
3. Try WC mapping (`O_SYNC` removed) WITHOUT any HDP_HOST_PATH_CNTL changes
4. Check if the issue is actually on the GPU side (V# descriptor, MC aperture, VM config)

### Status: REVERTED — crash fix confirmed, trash values remain

---

## Issue #3: Trash Values (0xFFFFFFFF) After Compute Dispatch — Jun 16, 2026

### Symptom
Compute dispatch completes (fence fires), but all 64 results read back as
0xFFFFFFFF instead of correct values. Post-dispatch, **both src AND dst** read
as 0xFFFFFFFF — even though the compute kernel only writes to dst.

Pre-dispatch VRAM verify shows correct data (src[0]=0, src[1]=1, dst=0x0).
So the data is in VRAM before dispatch but reads wrong after.

### Test output
```
VRAM write method test:
  Wr32(0xDEADBEEF) -> Rd32=0xFFFFFFFF   (first write reads wrong!)
  Wr32(0xCAFEBABE) -> Rd32=0xCAFEBABE   (second write OK)

Pre-dispatch: src[0]=0 src[1]=1 src[2]=2, dst=0x00000000   (correct)
Post-dispatch: dst[0]=0xFFFFFFFF, src[0]=0xFFFFFFFF         (both wrong)
Results: 0/64 correct, 64 errors
```

### Analysis
The fact that **src is also "corrupted"** (the kernel never writes to src) plus
the first-write-reads-wrong anomaly strongly suggests **HDP read cache** is
returning stale data rather than actual VRAM corruption.

- `GPU_VramRd32` does a raw DWORD read with **no HDP flush** — the HDP read
  cache may hold stale pre-init VRAM values (0xFF) for those addresses.
- `AccelGCN_Dispatch` does `HDP_MEM_COHERENCY_FLUSH_CNTL=1` after the fence,
  and `AccelGCN_VramRead` also does an HDP flush — but these may only flush
  the HDP **write** cache, not invalidate the **read** cache on this hardware.
- The "first write reads wrong, second works" pattern matches HDP read cache:
  the first read pulls a stale cache line, the write updates VRAM but not
  the HDP cache. The second access (adjacent DWORD) works because the cache
  line was refreshed by the first read.

### Fix Plan (SUPERSEDED — see Fix #3 below)
1. ~~Add `HDP_MEM_COHERENCY_FLUSH_CNTL=1` inside `GPU_VramRd32`~~ — only flushes write cache, not read cache
2. ~~CPU-side read-modify-write on `HDP_HOST_PATH_CNTL`~~ — DEADLOCKS PCI bus every time
3. ~~WC mapping without HDP_HOST_PATH_CNTL changes~~ — not attempted, WC causes other issues

### Status: FIX #3 APPLIED — extended by Fix #4 (PFP ENGINE_SEL + HDP_MISC_CNTL) — TESTING

---

## Fix #3: GPU-Side HDP Read-Cache Invalidation — Jun 16, 2026

### Problem
CPU-side writes to `HDP_HOST_PATH_CNTL` (the documented way to invalidate the HDP
read cache on SI) deadlock the PCI bus when done post-dispatch.  Every variation
tried (zeroing, read-modify-write, immediate, delayed) caused a hard system lockup
requiring power cycle.  The HDP read cache holds stale VRAM values from pre-dispatch
reads, causing all post-dispatch VRAM reads through BAR0 to return 0xFFFFFFFF.

### Root Cause (WHY CPU-side deadlocks)
After compute dispatch + fence, the HDP is in a state where a CPU-initiated write
to `HDP_HOST_PATH_CNTL` stalls the PCI fabric.  Likely cause: the HDP read cache
is trying to drain/invalidate entries that reference in-flight or recently-completed
MC transactions, and the CPU write creates a circular dependency on the PCI bus
that the shared RD990 root complex cannot resolve.

### Fix (APPLIED)
Do the `HDP_HOST_PATH_CNTL` write-back from the **GPU side** via a PM4 `WRITE_DATA`
packet (DST_SEL=0, register target).  This is emitted as part of the PM4 command
stream, AFTER `SURFACE_SYNC` flushes GPU L2/K$/I$ to VRAM, but BEFORE the EOP
fence write.  The GPU's ME engine performs the register write while the CP is still
active (clocks running, no idle-state race).  By the time the CPU sees the fence
fire, the HDP read cache is already invalidated.

### Sequence in PM4_SubmitCompute (after this fix):
```
1. Cache invalidation (I$/K$)
2. Shader program setup (PGM_LO/HI, RSRC1/2, thread counts)
3. DISPATCH_DIRECT via IB
4. SURFACE_SYNC (all caches, full range) — GPU writes reach VRAM
5. WRITE_DATA → HDP_MEM_COHERENCY_FLUSH_CNTL = 1   ← HDP write cache flush
6. WRITE_DATA → HDP_HOST_PATH_CNTL = <BIOS value>  ← HDP read cache invalidate
7. Double EVENT_WRITE_EOP (dummy + real fence)
--- CPU sees fence here, BAR0 reads now return correct VRAM data ---
```

### Files Modified
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Ring.ailang`
  - Added `hdp_hpc_val` field to `PM4State`
  - `PM4_InitMCBase` now snapshots `HDP_HOST_PATH_CNTL` BIOS value at init
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Pkt.ailang`
  - Added `PM4_EmitWriteDataReg` function (WRITE_DATA DST_SEL=0 for MMIO register)
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Dispatch.ailang`
  - `PM4_SubmitCompute`: emit HDP flush + invalidate after SURFACE_SYNC, before EOP
  - Bumped `needed` ring space from 140 → 150 DWORDs

### If This Still Deadlocks
The GPU-side WRITE_DATA to a register should NOT deadlock because:
- The ME engine does the write, not the CPU
- The CP is still active (not idle/gated)
- SURFACE_SYNC has already drained all GPU→VRAM traffic

If it DOES deadlock, the problem is deeper than HDP timing:
1. Check if `PM4State.hdp_hpc_val` is 0 (meaning the read at init failed)
2. Try removing ONLY the `HDP_HOST_PATH_CNTL` WRITE_DATA, keep the flush
3. Try moving both WRITE_DATA packets to BEFORE the SURFACE_SYNC
4. Nuclear option: disable HDP read caching entirely at init by setting
   bit 25 (HDP_READ_CACHE_DISABLE) in `HDP_HOST_PATH_CNTL` via CPU at
   init time (before any GRBM/dispatch activity)

### How to Revert If Broken
```bash
cd ~/Ailang-Self-Hosting-
git checkout -- Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Ring.ailang
git checkout -- Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Pkt.ailang
git checkout -- Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Dispatch.ailang
```
This reverts to the last committed state (pre-fix, no HDP invalidation, trash values
but no deadlock).

---

## Fix #4: PFP ENGINE_SEL + HDP_MISC_CNTL GPU-Side Flush — Jun 16, 2026 ~22:23 EDT

### Context
Fix #3 stopped the hard lockups from **CPU-side** `HDP_HOST_PATH_CNTL` writes, but
`test_accel_gcn.x` still returned 0xFFFFFFFF for all post-dispatch BAR0 reads (src and
dst both wrong — classic HDP read-cache staleness, not shader corruption).

Deep dive against local kernel tree (`~/linux`):
- Legacy **radeon** `si_fence_ring_emit`: SURFACE_SYNC + EOP only — no per-fence HDP
  invalidate in the PM4 stream.
- **`r600_mmio_hdp_flush`**: only `HDP_MEM_COHERENCY_FLUSH_CNTL` (write cache).
- **Evergreen init** (`si.c` ~3323): `HDP_MISC_CNTL |= HDP_FLUSH_INVALIDATE_CACHE` then
  read-modify-write `HDP_HOST_PATH_CNTL`.
- **`radeon` WRITE_DATA for HDP regs**: `ENGINE_SEL(1)` = **PFP**, not ME (`si.c` ~5076).
- **amdgpu SI** goes further: per-IB `si_flush_hdp` + `si_invalidate_hdp` via
  **`HDP_DEBUG0 = 1`** at offset `0x2F30` — **not yet implemented** in AILang.

### What Changed (Fix #4 on top of Fix #3)

1. **`PM4_EmitWriteDataReg` ENGINE_SEL → PFP (1)**
   - Was ME (0). Kernel radeon uses PFP for HDP register targets via WRITE_DATA;
     ME may not route to HDP registers correctly.

2. **Added `HDP_MISC_CNTL` (0x2F4C / byte offset 12108)**
   - New `SIReg.HDP_MISC_CNTL` in `Library.AMDGPUPM4Regs.ailang`.
   - `PM4_InitMCBase` snapshots BIOS value into `PM4State.hdp_misc_val` (alongside
     existing `hdp_hpc_val` snapshot).

3. **Three GPU-side WRITE_DATA packets after SURFACE_SYNC (before EOP)**
   ```
   WRITE_DATA → HDP_MEM_COHERENCY_FLUSH_CNTL = 1        (drain HDP write cache)
   WRITE_DATA → HDP_MISC_CNTL = hdp_misc_val | 1       (FLUSH_INVALIDATE_CACHE)
   WRITE_DATA → HDP_HOST_PATH_CNTL = hdp_hpc_val         (read-modify-write back to BIOS value)
   ```
   Ring space `needed` bumped 150 → **155** DWORDs.

### How This Differs From the Deadlocking CPU-Side Flushes

| Approach | Who writes HDP regs | When | Result |
|----------|---------------------|------|--------|
| CPU `HDP_HOST_PATH_CNTL` post-dispatch | CPU via BAR0 MMIO | After fence, CP idle-ish | **Hard PCI deadlock** (Crash #2 / Fix #3 analysis) |
| CPU `HDP_MEM_COHERENCY_FLUSH_CNTL` in VramRead | CPU via BAR0 | Every BAR0 read | Safe but only flushes **write** cache |
| GPU WRITE_DATA in PM4 stream (Fix #3/#4) | PFP via CP command | After SURFACE_SYNC, **before** EOP fence | Should not stall PCI — ME/PFP does write while CP active |

Key distinction: we never touch HDP routing registers from the CPU after dispatch.
Init still only **reads** HDP regs (snapshot BIOS values). All post-dispatch HDP
work is three DWORDs in the PM4 IB, executed by the GPU before the fence signals
the CPU.

### Files Modified (Fix #4)
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Pkt.ailang` — `ENGINE_SEL=1` (PFP) in `PM4_EmitWriteDataReg`
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Regs.ailang` — `HDP_MISC_CNTL` register constant
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Ring.ailang` — `hdp_misc_val` field + init snapshot
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Dispatch.ailang` — third WRITE_DATA for `HDP_MISC_CNTL`; `needed=155`

### Test
```bash
cd ~/Ailang-Self-Hosting-
sudo ./test_accel_gcn.x
```
Expect: `Results: 64/64 correct` with dst[i] = src[i]+42. If still 0xFFFFFFFF but no
lockup, HDP read cache is still stale — next try is amdgpu-style **`HDP_DEBUG0=1`**
(`0x2F30`) as a fourth GPU-side WRITE_DATA after the misc flush.

### If This Deadlocks
Unlikely (same GPU-side mechanism as Fix #3, one extra register write). If it does:
1. Remove only the `HDP_MISC_CNTL` WRITE_DATA (keep flush + HOST_PATH_CNTL)
2. Verify `hdp_misc_val` and `hdp_hpc_val` are non-zero at init (BC0–BC4 breadcrumbs)
3. Revert Fix #4 entirely (see below) — returns to Fix #3 behavior (trash values, no deadlock)

### How to Revert Fix #4 Only
```bash
cd ~/Ailang-Self-Hosting-
git checkout -- Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Pkt.ailang
git checkout -- Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Regs.ailang
git checkout -- Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Ring.ailang
git checkout -- Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Dispatch.ailang
./ailang.x TestCode/test_accel_gcn.ailang test_accel_gcn.x
```

### Status: APPLIED — AWAITING TEST (binary rebuilt Jun 16 22:23)

---

## Issue #5: Compute GPU (bus 2) Not VBIOS POSTed — VRAM Uninitialized — Jun 17, 2026

### Symptom
GPU 0 (display GPU, bus 1:0.0) passes all compute tests — `test_accel_gcn` returns
64/64 correct when targeting bus 1. GPU 1 (compute GPU, bus 2:0.0) returns
0xFFFFFFFF / 0xFFDFFF7F alternating for all post-dispatch VRAM reads. Pre-dispatch
writes appear to land (verified via BAR0 readback) but GPU-side reads see garbage.

PCI COMMAND register starts at 0x0 on bus 2 (driver enables it to 0x6), confirming
the system BIOS never POSTed the second GPU.

### Root Cause (CONFIRMED)
The compute GPU on bus 2 was **never VBIOS POSTed by the system BIOS**. The system
BIOS only POSTs the primary/display GPU (bus 1). An un-POSTed GPU has:

- **No VRAM training** — the DDR PHY hasn't been calibrated, MC doesn't know
  timing parameters. VRAM reads return 0xFF / garbage.
- **No MC firmware** — the memory controller sequencer microcode hasn't been loaded.
- **MC_VM_FB_LOCATION = 0** — the VRAM aperture mapping is wrong.
- **CONFIG_MEMSIZE = 0** — no VRAM size detected.

`AtomExec_AsicInit` (table 0) brings up the SPLL and engine clocks, but does NOT
perform full MC initialization or VRAM training. The 0xFFFFFFFF reads are NOT an
HDP cache staleness issue (Fixes #3/#4 were chasing a red herring for this GPU) —
the memory controller itself isn't functional.

**Evidence:** The display GPU (bus 1) works perfectly because the system BIOS already
ran the full VBIOS POST sequence including MC firmware load and VRAM training.

### What the Linux Kernel Does (that we don't)
Compared `si_init()` / `si_startup()` in `~/linux/drivers/gpu/drm/radeon/si.c`:

1. **`atom_asic_init()`** — table 0, same as our `AtomExec_AsicInit`. ✅ We do this.
2. **`si_mc_load_microcode()`** — Loads MC firmware (`VERDE_mc2.bin`) via:
   - `MC_SEQ_IO_DEBUG_INDEX/DATA` — 36 IO MC register pairs (verde_io_mc_regs)
   - `MC_SEQ_SUP_PGM` — MC sequencer microcode words
   - `MC_SEQ_SUP_CNTL` — reset(0x08) → write(0x10) → load → reset(0x08) → run(0x04) → start(0x01)
   - Polls `MC_SEQ_TRAIN_WAKEUP_CNTL` for `TRAIN_DONE_D0` (bit 30) and `TRAIN_DONE_D1` (bit 31)
   - ✅ **DONE** (Step 2, commit f3abda25) — `MC_SI_LoadMicrocode()` in `Library.AMDGPUMC_SI.ailang`
   - Skips if MC sequencer already running (POSTed GPU)
   - VRAM training: TRAIN_DONE_D0 + TRAIN_DONE_D1 both pass, CONFIG_MEMSIZE=1024MB
3. **`si_mc_program()`** — Programs MC aperture:
   - `MC_VM_FB_LOCATION`, `MC_VM_SYSTEM_APERTURE_*`, `MC_VM_AGP_*`
   - `HDP_NONSURFACE_BASE/INFO/SIZE`
   - `VGA_HDP_CONTROL = VGA_MEMORY_DISABLE`
   - Wrapped in `evergreen_mc_stop()` / `evergreen_mc_resume()` (BIF_FB_EN blackout)
   - ✅ **DONE** (Step 3, commit fabcc45c) — `MC_SI_Program()` in `Library.AMDGPUMC_SI.ailang`
   - Uses `vram_start=0` (kernel default for SI via `radeon_vram_location(rdev, mc, 0)`)
   - Simplified blackout: no CRTC blanking (headless compute GPU, no display engine)
   - Runs unconditionally — normalizes FB_LOCATION to base=0 on every init
   - Result: `MC_VM_FB_LOCATION=0x003F0000`, `mc_fb_base=0x0`, aperture low=0x0 high=0x3FFFF
   - Garbage pattern changed post-dispatch (MC aperture affecting address routing)
   - Still 0/64 correct — need GB_ADDR_CONFIG next
4. **`si_gpu_init()`** — Engine config:
   - `BIF_FB_EN = FB_READ_EN | FB_WRITE_EN` — already done in MC_SI_Program un-blackout
   - `GB_ADDR_CONFIG` (Verde golden = 0x12010002) — ❌ **NOT YET DONE**
   - `GRBM_CNTL = GRBM_READ_TIMEOUT(0xFF)` — ❌ **NOT YET DONE**
   - `HDP_MISC_CNTL |= HDP_FLUSH_INVALIDATE_CACHE` — ⚠️ **SKIP: CPU-side HDP MMIO writes deadlock PCI bus on RD990 + WC BAR0** (see Fix #2)
   - `HDP_HOST_PATH_CNTL` read-modify-write — ⚠️ **SKIP: same deadlock risk** (see Fix #2)
   - ❌ **IN PROGRESS — Step 4**

### Fix Plan (IN PROGRESS)

New init order (additions marked with **NEW**):
```
1. GPU_Discover -> BAR map
2. AtomBIOS -> PP -> Volt -> DPM_SI_InitSPLL         (engine clocks)
3. **NEW** MC_LoadMicrocode -> MC VRAM training        (DRAM PHY calibration)
4. **NEW** MC_Program -> FB_LOCATION, aperture, HDP    (VRAM aperture setup)
5. **NEW** GPU_InitEngine -> BIF_FB_EN, GB_ADDR_CONFIG (engine config)
6. PM4_HaltCP -> PM4_InitMCBase -> PM4_SoftResetCP
7. CP/RLC firmware -> IH ring -> ring setup -> CP start
8. SMC -> DPM_Init -> DPM_Enable -> Force HIGH
9. Compute dispatch
```

### Implementation Steps
- [x] Add MC register constants to PM4Regs (MC_SEQ_*, CONFIG_MEMSIZE, MC_VM_AGP_*, etc.)
- [x] New file: `Library.AMDGPUMC_SI.ailang` — MC firmware load + VRAM training
- [x] New function: `MC_SI_Program` — write MC_VM_FB_LOCATION, aperture, HDP, AGP
- [ ] New function: `MC_SI_GpuInit` — GRBM_CNTL, GB_ADDR_CONFIG (skip HDP MMIO — deadlock risk)
- [x] Wire into AccelGCN_Init between DPM_SI_InitSPLL and PM4_HaltCP
- [ ] Test on bus 2 compute GPU — verify 64/64 correct

### Key Files
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Regs.ailang` — register constants (done)
- `Librarys/Drivers/AMDGPU/Library.AMDGPUMC_SI.ailang` — new MC init module
- `Librarys/Accel/Library.AccelGCN.ailang` — init sequence wiring

### Verde IO MC Register Table (36 pairs for MC_SEQ_IO_DEBUG)
```
{0x6f,0x03044000} {0x70,0x0480c018} {0x71,0x00000040} {0x72,0x01000000}
{0x74,0x000000ff} {0x75,0x00143400} {0x76,0x08ec0800} {0x77,0x040000cc}
{0x79,0x00000000} {0x7a,0x21000409} {0x7c,0x00000000} {0x7d,0xe8000000}
{0x7e,0x044408a8} {0x7f,0x00000003} {0x80,0x00000000} {0x81,0x01000000}
{0x82,0x02000000} {0x83,0x00000000} {0x84,0xe3f3e4f4} {0x85,0x00052024}
{0x87,0x00000000} {0x88,0x66036603} {0x89,0x01000000} {0x8b,0x1c0a0000}
{0x8c,0xff010000} {0x8e,0xffffefff} {0x8f,0xfff3efff} {0x90,0xfff3efbf}
{0x94,0x00101101} {0x95,0x00000fff} {0x96,0x00116fff} {0x97,0x60010000}
{0x98,0x10010000} {0x99,0x00006000} {0x9a,0x00001000} {0x9f,0x00a37400}
```

### MC Firmware
- File: `/lib/firmware/radeon/VERDE_mc2.bin` (31500 bytes)
- Format: raw 32-bit words, `size / 4 = 7875` DWORDs loaded via MC_SEQ_SUP_PGM
- Also available: `verde_mc.bin` (symlink to amdgpu), `VERDE_mc.bin` (symlink to PITCAIRN)

### Step 3 Test Results (bus 2 un-POSTed compute GPU)
```
MC_SI_Program ran unconditionally:
  MC_VM_FB_LOCATION = 0x003F0000  (base=0, top=63, 1024MB)
  SYSTEM_APERTURE: low=0x0 high=0x3FFFF
  mc_fb_base = 0x0  (was 0xF400000000 from stale MC firmware state)
  gpu_data_addr = 0x4082000  (direct VRAM offset, correct for base=0)

Pre-dispatch VRAM verify:  src[0]=0 src[1]=1 src[2]=2, dst all zero  ✅
Post-dispatch: dst[0]=0xFF000100  (garbage, not 42)  ❌
Wr32/Rd32 BAR test:  first DWORD returns 0xFFFFFFFF, second works  ⚠️

Key observation: MC_SI_LoadMicrocode returned 0 (already running from
previous test run). The MC firmware persists across process invocations
because MC_SEQ_SUP_CNTL RUN bit stays set. MC_VM_FB_LOCATION had stale
0xF43FF400 from the MC firmware's internal init. MC_SI_Program overwrites
it to base=0 which is correct per kernel si_mc_program + radeon_vram_location(0).

Still 0/64 — likely need GB_ADDR_CONFIG (address decode mismatch between
GPU shader engines and MC). Without correct GB_ADDR_CONFIG, the GPU's
address interleaving doesn't match what the MC expects, causing scattered
reads/writes to wrong VRAM locations.
```

### Status: STEPS 1-4 DONE, TESTING DUAL-GPU COMPARISON

---

## Crash #3: Display Blanking on Bus 1 (MC_SI_Program) — Jun 17, 2026

### Symptom
Running `test_accel_gcn` (dual-GPU comparison test) blanked the display and
forced a hard reboot. The test runs `RunOnGPU(1)` first (display GPU), then
`RunOnGPU(2)` (compute GPU). The display died during bus 1 init.

### Root Cause (CONFIRMED)
`MC_SI_Program()` was running unconditionally on BOTH GPUs. On the display GPU
(bus 1, POSTed, VESA framebuffer active), this function:

1. **`BIF_FB_EN = 0`** — kills CPU access to VRAM. VESA can no longer read or
   write the framebuffer. Screen goes black immediately.
2. **`MC_SHARED_BLACKOUT_CNTL |= 1`** — MC blackout, blocks all memory ops.
3. **`VGA_HDP_CONTROL = VGA_MEMORY_DISABLE`** — disables VGA memory aperture.
4. **Reprograms `MC_VM_FB_LOCATION`** to `vram_start=0` — stomps the BIOS-
   configured aperture that the VESA driver depends on.

Even after un-blackout (`BIF_FB_EN = 3`), the aperture addresses are wrong
relative to what VESA expects, so the display stays dead.

Additionally, `MC_SI_GpuInit()` overwrites `DMIF_ADDR_CONFIG` (Display Memory
Interface address decode), which corrupts the scanout engine's address mapping.

None of these functions existed in the old working code (commit `ed2fbcce` and
earlier). They were added for Issue #5 (un-POSTed bus 2 GPU), but applied
unconditionally to both GPUs.

### Fix (APPLIED)
Gate all three MC functions behind `GPU_BAR_IsDisplayGPU()` in `AccelGCN_Init`:

```ailang
is_display = GPU_BAR_IsDisplayGPU(gpu)
IfCondition EqualTo(is_display, 0) ThenBlock: {
    mc_rc = MC_SI_LoadMicrocode(gpu)
    mc_prog_rc = MC_SI_Program(gpu)
    mc_gpu_rc = MC_SI_GpuInit(gpu)
}
IfCondition EqualTo(is_display, 1) ThenBlock: {
    PrintMessage("[AccelGCN] display GPU — skipping MC init (BIOS already configured)\n")
}
```

The display GPU is already fully POSTed by the BIOS — MC firmware loaded,
VRAM trained, aperture configured, `GB_ADDR_CONFIG` set. Running these
functions on it is unnecessary and destructive.

### Files Modified
- `Librarys/Accel/Library.AccelGCN.ailang` — MC init gated by `is_display` check
- `TestCode/test_accel_gcn.ailang` — header comments updated with safety note

### If Display Still Blanks
If the screen still dies after this fix, the remaining suspects are:
1. `DPM_SI_InitSPLL` — touches SPLL/engine clocks, could disrupt display PLL
2. `PM4_SoftResetCP` — GRBM_SOFT_RESET might reset display-related blocks
3. `PM4_HaltCP` — halting the CP shouldn't affect display, but worth checking

To revert:
```bash
git checkout -- Librarys/Accel/Library.AccelGCN.ailang
git checkout -- TestCode/test_accel_gcn.ailang
```

### Status: FIX APPLIED — AWAITING TEST

---

## Fix #5: Defense-in-Depth Display GPU Guards in MC_SI Functions — Jun 17, 2026

### Problem
Crash #3 fix gated MC init at the caller level (`AccelGCN_Init`), but the three
MC functions themselves (`MC_SI_LoadMicrocode`, `MC_SI_Program`, `MC_SI_GpuInit`)
had no internal display GPU check. Any new caller or test that invoked them
directly without checking `GPU_BAR_IsDisplayGPU()` would kill the VESA
framebuffer and blank the screen — same as Crash #3.

Other BAR-layer functions (`GPU_BAR_MapMMIO`, `GPU_BAR_Reset`, `GPU_BAR_Unbind`,
etc.) already follow a defense-in-depth pattern with internal display GPU guards.
The MC functions did not.

### Fix (APPLIED)
Added `GPU_BAR_IsDisplayGPU(gpu)` guard at the top of all three functions in
`Library.AMDGPUMC_SI.ailang`:

- **`MC_SI_LoadMicrocode`** — returns 0 with `REFUSED` message
- **`MC_SI_Program`** — returns 0 with `REFUSED` message
- **`MC_SI_GpuInit`** — returns 0 with `REFUSED` message

Each prints `[MC_SI] <func>: REFUSED — display GPU (BIOS already configured)`
so the refusal is visible in test output.  Combined with the existing caller-side
gate in `AccelGCN_Init`, there are now two layers of protection.

### Files Modified
- `Librarys/Drivers/AMDGPU/Library.AMDGPUMC_SI.ailang` — internal guards added

### Status: APPLIED — TESTING

---

## Crash #4: Display Kill from PM4_SoftResetCP on Bus 1 — Jun 18, 2026

### Symptom
Running `test_accel_gcn` (dual-GPU test) killed the display during bus 1
(display GPU) init.  Hard reboot required.  Test results for bus 2 lost.

### Root Cause
`PM4_SoftResetCP` and `PM4_HaltCP` ran unconditionally on both GPUs.
On the display GPU (bus 1, radeon driver, VESA framebuffer active),
`PM4_SoftResetCP` does:

1. `BIF_FB_EN = 0` — kills CPU access to VRAM / framebuffer
2. `MC_SHARED_BLACKOUT_CNTL |= 1` — blackouts memory controller
3. `VGA_RENDER_CONTROL = 0` — disables VGA rendering
4. `GRBM_SOFT_RESET` full pipeline (CP, CB, DB, PA, SC, SPI, SX, etc.)
5. `SRBM_SOFT_RESET` (HDP + GRBM)

Even though BIF_FB_EN and MC blackout are saved/restored, the
GRBM_SOFT_RESET wipes the display engine's pipeline state.  The VESA
framebuffer never recovers.

The MC_SI functions (Fix #5) were properly gated, but these PM4
functions predated the dual-GPU test and had no display GPU guards.

### Fix (APPLIED)
Added `GPU_BAR_IsDisplayGPU(gpu)` guard at the top of both functions:

- **`PM4_SoftResetCP`** — returns immediately with `REFUSED` message
- **`PM4_HaltCP`** — returns immediately with `REFUSED` message

With these guards, `AccelGCN_Init` on bus 1 will fail cleanly downstream
(can't set up rings without halting CP first) instead of killing the
display.  Bus 2 init proceeds normally.

### Files Modified
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4FW.ailang` — PM4_SoftResetCP guard
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Ring.ailang` — PM4_HaltCP guard

### Status: APPLIED — TESTING

### Fix #2: Removed display GPU from test_accel_gcn entirely
`test_accel_gcn.ailang` Main now only calls `RunOnGPU(2)` (compute GPU).
Bus 1 (display GPU) is never touched.  If the display still dies, the
problem is in a shared path that doesn't check GPU index, or the bus 2
init is somehow stomping bus 1 via the shared RD990 root complex.

**If display dies after this change, check:**
1. `GPU_Discover` — does it write to bus 1 MMIO during enumeration?
2. `AtomBIOS_LoadROM` — does it read the wrong ROM (bus 1 instead of bus 2)?
3. Any PCI config space write that hits both buses
4. RD990 root complex lockup from bus 2 stall (same as original crash #1)

---

## Investigation #5: GRBM_GFX_INDEX / GB_ADDR_CONFIG "MISMATCH" — Jun 18, 2026

### Symptom
`MC_SI_GpuInit` reported `GB_ADDR_CONFIG readback = 0x10000000 MISMATCH!`
and `GRBM_GFX_INDEX = 0x0 (expect 0xE0000000)`.  Appeared to be a total
init failure — GRBM-domain register writes not sticking.

### Root Cause: FALSE ALARM — Write-Only Registers
Both `GB_ADDR_CONFIG` and `GRBM_GFX_INDEX` are **write-only** on SI.
Readback returns power-on defaults (0x10000000 / 0x0), NOT the value
written.  The Linux kernel (si.c:si_gpu_init) **never reads either
register back** — it writes and trusts.

Evidence: CP ring tests pass (require working GRBM), all 3 ring NOP
tests succeed, and the CP processes ME_INITIALIZE + CLEAR_STATE correctly.
The writes are landing; the readback is just misleading.

### Fixes Applied
1. **Removed readback MISMATCH check** for GB_ADDR_CONFIG
2. **Removed readback check** for GRBM_GFX_INDEX
3. **Fixed false PM4 aperture warning** — `aperture LOW=0` is correct
   when VRAM starts at MC address 0 (MC_VM_FB_LOCATION BASE=0x0000)

### Init Ordering Fixes (defense-in-depth, matches kernel si_gpu_init)
Even though writes were landing, the ordering was wrong vs kernel:

**Before (our code):**
```
MGCG_OVERRIDE → GRBM_GFX_INDEX → GRBM_CNTL → BIF_FB_EN → GB_ADDR_CONFIG
```

**After (matches kernel si_gpu_init):**
```
MGCG_OVERRIDE + CGCG_CGLS + CGTS_SM → HDP zero → GRBM_CNTL → BIF_FB_EN → GB_ADDR_CONFIG → GRBM_GFX_INDEX
```

Changes:
- **Added CGCG/CGLS disable** (RLC_CGCG_CGLS_CTRL=0)
- **Added CGTS_SM_CTRL_REG** override (0x600000)
- **Added HDP protection buffer zeroing** (32 entries × 5 regs)
- **Moved GRBM_GFX_INDEX** to AFTER GRBM_CNTL, BIF_FB_EN, GB_ADDR_CONFIG

### Remaining Issue
Compute dispatch still returns 0xFFFFFFFF for all outputs.  Init is clean,
ring tests pass, but shader execution produces garbage.  Separate issue
from register initialization.

### Status: RESOLVED (false alarm) + init ordering improved

---

## Fix #6: AtomBIOS IIO Opcode Swap (MOVE_ATTR/MOVE_DATA) — Jun 18, 2026

### Problem
`AE_IIO_Execute` in `Library.AMDGPUAtomExecIO.ailang` had **IIO opcodes 7 and 8
swapped**. The kernel defines `ATOM_IIO_MOVE_ATTR=7` (uses `io_attr`) and
`ATOM_IIO_MOVE_DATA=8` (uses `data` parameter). Our code had opcode 7 using
`data` and opcode 8 using `io_attr` — exactly backwards.

The comment (line 135) correctly listed `7=MOVE_ATTR, 8=MOVE_DATA`, but the
implementation bodies were swapped.

### Impact
IIO programs are used for indirect register access during ASIC_INIT (VBIOS POST).
When the IIO program uses opcode 7 to inject `io_attr` bits into a register value,
our code was injecting `data` bits instead (and vice versa). This corrupts indirect
register programming during MC sequencer training, PLL configuration, and any
IIO-routed register writes — potentially leaving the GPU memory controller in an
incorrect state after POST.

### Fix
Swapped the bodies: opcode 7 now reads from `io_attr` (MOVE_ATTR), opcode 8 now
reads from `data` (MOVE_DATA). Matches kernel `atom_iio_execute()` in `atom.c`.

### Files Modified
- `Librarys/Drivers/AMDGPU/Library.AMDGPUAtomExecIO.ailang` — lines 196-218

### Status: APPLIED — TESTING

---

## Fix #7: AtomBIOS Delay Timing Too Short — Jun 18, 2026

### Problem
`AE_OpDelay` busy-wait loop was too fast. Microsecond path did 1 MMIO read per
count unit (~200-500ns actual vs 1µs requested). Millisecond path did `count*1000`
reads (~0.2-0.5ms actual vs 1ms requested) — **2-5x too short**.

POST relies on precise delays for PLL lock times and MC VRAM training. If the
VBIOS requests 5ms for PLL stabilization and we only wait ~1ms, PLLs may not lock
and subsequent register reads return garbage.

### Fix
- Microsecond path: 5 MMIO reads per count unit (≈1-2.5µs, conservative overshoot)
- Millisecond path: 5000 MMIO reads per count unit (≈1-2.5ms, conservative overshoot)

Overshooting is safe for POST (just slower init). Undershooting causes failures.

### Files Modified
- `Librarys/Drivers/AMDGPU/Library.AMDGPUAtomExecOps.ailang` — AE_OpDelay

### Status: APPLIED — TESTING

---

## Fix #8: Missing Verde Golden Registers (TC Pipeline) — Jun 18, 2026

### Problem
The BIOS programs chip-specific "golden registers" during POST via
`si_init_golden_registers()` in the kernel. Our code never programmed these for
the un-POSTed compute GPU (bus 2). The critical missing registers control the
**texture cache (TC) pipeline** that `buffer_load_dword` uses on GCN:

| Register | Address | Value | Purpose |
|---|---|---|---|
| `TA_CNTL_AUX` | 0x9508 | bit 16 | TA unit control for buffer ops |
| `TCP_ADDR_CONFIG` | 0xAC14 | 0x3 | 4 TCC blocks (matches Verde channels) |
| `TCP_CHAN_STEER_LO` | 0xAC0C | 0x1032 | Channel steering |
| `TCP_CHAN_STEER_HI` | 0xAC10 | 0x0 | Upper steering (2 pipes) |
| `SPI_CONFIG_CNTL` | 0x9100 | 0x03000000 | GPR_WRITE_PRIORITY for wave dispatch |
| `SX_DEBUG_1` | 0x9060 | 0x20 | Shader export debug bit 5 |

Without `TCP_ADDR_CONFIG` matching the memory channel config, the TC pipeline
misroutes requests to non-existent channels → 0xFFFFFFFF returns.

### Fix
Added golden register programming as Step 0b in `MC_SI_GpuInit`, right after
clock gating disable. Uses read-modify-write with masks matching the kernel's
`radeon_program_register_sequence()` pattern.

Also added register constants to PM4Regs: `TA_CNTL_AUX`, `TCP_CHAN_STEER_LO`,
`TCP_CHAN_STEER_HI`, `TCP_ADDR_CONFIG`.

### Files Modified
- `Librarys/Drivers/AMDGPU/Library.AMDGPUMC_SI.ailang` — golden regs in GpuInit
- `Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Regs.ailang` — new register constants

### Status: APPLIED — TESTING

---

## Full Dispatch Trace (AccelGCN_Init)

1. GPU_Discover -> GPU_BAR_MapMMIO -> GPU_BAR_MapVRAM
2. AtomBIOS_LoadROM -> Parse -> PP_Parse -> Volt_Parse -> DPM_SI_InitSPLL
3. **MC_SI_LoadMicrocode** -> **MC_SI_Program** -> **MC_SI_GpuInit** *(un-POSTed GPUs only; SKIPPED on display GPU)*
4. **PM4_HaltCP** -> PM4_InitMCBase -> **PM4_SoftResetCP** -> **PM4_HaltCP** *(SKIPPED on display GPU)*
5. PM4_LoadCPFirmware -> PM4_LoadRLCFirmware -> PM4_SetupIHRing
6. PM4_SetupRing(0) -> PM4_CPStart (unhalt) -> PM4_RingTest(0)
7. PM4_SetupRing(1) -> PM4_RingTest(1)
8. PM4_SetupRing(2) -> PM4_RingTest(2)
9. SCRATCH_UMSK=0xFF, roundtrip check
10. SMC_LoadFirmware -> DPM_Init -> DPM_Enable -> Force HIGH
11. CIR_Begin -> build kernel -> CIR_Lower_GCN -> upload to VRAM
12. AccelGCN_Dispatch (PM4_SubmitCompute + fence wait + readback)
