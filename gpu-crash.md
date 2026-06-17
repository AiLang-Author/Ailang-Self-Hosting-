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
   - ❌ **MISSING — this is the critical step**
3. **`si_mc_program()`** — Programs MC aperture:
   - `MC_VM_FB_LOCATION`, `MC_VM_SYSTEM_APERTURE_*`, `MC_VM_AGP_*`
   - `HDP_NONSURFACE_BASE/INFO/SIZE`
   - `VGA_HDP_CONTROL = VGA_MEMORY_DISABLE`
   - Wrapped in `evergreen_mc_stop()` / `evergreen_mc_resume()` (BIF_FB_EN blackout)
   - ❌ **MISSING — we only READ MC_VM_FB_LOCATION, never WRITE it**
4. **`si_gpu_init()`** — Engine config:
   - `BIF_FB_EN = FB_READ_EN | FB_WRITE_EN`
   - `GB_ADDR_CONFIG` (Verde golden = 0x12010002)
   - `HDP_MISC_CNTL |= HDP_FLUSH_INVALIDATE_CACHE`
   - `HDP_HOST_PATH_CNTL` read-modify-write
   - ❌ **PARTIALLY MISSING**

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
- [ ] New file: `Library.AMDGPUMC_SI.ailang` — MC firmware load + VRAM training
- [ ] New function: `MC_SI_Program` — write MC_VM_FB_LOCATION, aperture, HDP, AGP
- [ ] New function: `MC_SI_InitEngine` — BIF_FB_EN, GB_ADDR_CONFIG, HDP init
- [ ] Wire into AccelGCN_Init between DPM_SI_InitSPLL and PM4_HaltCP
- [ ] Test on bus 2 compute GPU

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

### Status: STEP 1 DONE (registers added), IMPLEMENTING MC FIRMWARE LOAD

---

## Full Dispatch Trace (AccelGCN_Init)

1. GPU_Discover -> GPU_BAR_MapMMIO -> GPU_BAR_MapVRAM
2. AtomBIOS_LoadROM -> Parse -> PP_Parse -> Volt_Parse -> DPM_SI_InitSPLL
3. PM4_HaltCP -> PM4_InitMCBase -> PM4_SoftResetCP -> PM4_HaltCP
4. PM4_LoadCPFirmware -> PM4_LoadRLCFirmware -> PM4_SetupIHRing
5. PM4_SetupRing(0) -> PM4_CPStart (unhalt) -> PM4_RingTest(0)
6. PM4_SetupRing(1) -> PM4_RingTest(1)
7. PM4_SetupRing(2) -> PM4_RingTest(2)
8. SCRATCH_UMSK=0xFF, roundtrip check
9. SMC_LoadFirmware -> DPM_Init -> DPM_Enable -> Force HIGH
10. CIR_Begin -> build kernel -> CIR_Lower_GCN -> upload to VRAM
11. AccelGCN_Dispatch (PM4_SubmitCompute + fence wait + readback)
