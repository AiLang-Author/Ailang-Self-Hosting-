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

### Fix Plan
1. Add `HDP_MEM_COHERENCY_FLUSH_CNTL=1` inside `GPU_VramRd32` before every
   VRAM read. If this fixes it, the problem is confirmed as HDP read cache.
2. If that doesn't work: try read-modify-write on `HDP_HOST_PATH_CNTL`
   (specific bits only, not zeroing the whole register).
3. If that doesn't work: try WC mapping without HDP_HOST_PATH_CNTL changes.

### Status: INVESTIGATING — next step is HDP flush in GPU_VramRd32

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
