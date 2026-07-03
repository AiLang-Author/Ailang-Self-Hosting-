# AILang AMD GPU Compute — Handoff (condensed 2026-07-02, post-§33)

**Target:** Cape Verde (GCN1 / Southern Islands), bus 2 = compute GPU.
**Goal:** get a compute dispatch to produce correct output (`dst[i]=src[i]+42`).

**Read this + `gpu-crash.md` (hard safety RULES) before editing.**
Full §8–§33 narrative history: `git show 7cf8eec2:RING1_GART_FIX_HANDOFF.md`.
References below like "archive §24" point there.

## 0. HARD RULES (summary — gpu-crash.md is authoritative)

1. NEVER touch the DISPLAY GPU (bus 1 / 01:00.0). Guards stay. Every run logs `using GPU N (bus 2)`.
2. HDP_HOST_PATH_CNTL (0x2C00) / HDP_MISC_CNTL (0x2F4C): kernel-verbatim replay values at
   kernel trace positions ONLY (amended 2026-07-02, §1b) — ad-hoc writes still deadlock.
3. NEVER write PCI config 0x7c (ASIC reset) — fabric hangs. gpu_reset.sh is deleted; do not recreate.
4. NEVER re-add SRBM_GFX_CNTL pokes (archive §16 — wedges fabric).
5. `gpu-mmiotrace.service` stays DISABLED (archive §32). Re-enable only to capture new traces on purpose.
6. Human executes all GPU tests, from SSH, with the fsync-per-line logger (§4 below). Cold reboot before each.

## 1. CURRENT STATE (2026-07-02 20:21 run, §33 — the first valid cold test since Jun 19)

The §30 replay harness (`test_replay_init`) replays the ENTIRE working kernel init
(22,752 records from the Jun 19 radeon trace: 21,553 writes, 1,185 read-oracles, 11 polls)
onto a true-cold card, verbatim, with 1 ms write pacing.

Result: **BAR0 MMIO replay is essentially perfect — and the chip still won't run.**
- A1 (power-on→ATOM→MC): 91 oracle mismatches, all on 2 calibration-class regs (0x728 early-ATOM bit0, MC_SEQ_IO_DEBUG_DATA training data). Benign.
- A2 (VM→RLC→CP→rings): 3 mismatches, all expected (HDP RULE-skip + the 2 failed ring-test reads).
- **THE lead: RLC_STAT (0xC34C) sticks at 0x6.** The kernel's own boot poll went 0x6→0x7 (bit0 = RLC core executing) right after RLC_CNTL=1; ours never leaves 0x6.
- All 3 kernel ring tests FAIL (SCRATCH_REG0 stays at our preset 0xCAFEDEAD). **The ME has never executed a single packet, ever** (also proven independently by archive §29/§31 probes: 8/8 landed=0).

Conclusion: the divergence from the working boot is NOT in BAR0 register writes.
It is in the only two channels mmiotrace cannot see — **memory-side content** (written
via the FB BAR / CPU) and **non-BAR0 device state** (PCI config space, POST side effects).

**Post-§33 incident (found 2026-07-02 late):** a second replay run ~20:33 was started
WITHOUT a cold reboot. Its log overwrote the §33 22,308-line log (only a 1,817-line
truncated file survives — the §33 numbers above live only in this doc now) and the run
froze the box mid-A1 at ~record 1731 (the CG_SPLL 0x600 block). The seq-7 oracle in that
log reads 0x400 = card was POSTed ⇒ warm-entry replay, §32's predicted freeze mode, now
twice-confirmed. The harness now refuses to start on a posted card (§34 guard below).

## 1b. §34 COLD RUN (2026-07-02 ~21:10) — threads (a)/(b)-as-built dead; trace re-read
## reveals the misread poll AND fingers the RULE-1 HDP skip as the last divergence

The §34 binary ran on a true cold boot, clean: cold guard passed, PCI COMMAND 0x0→0x6
(bus master enabled from cold — thread (c) closed for good), SR/CSB/ring content loaded,
BAR0 oracles clean (only MC training + strobe-port artifacts + ring-test reads).
**RLC_STAT still 0x6 after 2M paced reads; ring tests still fail.** With that, re-reading
bus2_all.txt raw produced three corrections that reshape the lead:

1. **The kernel never polled RLC_STAT 0x6→0x7.** Its FIRST read after RLC_CNTL=1
   (seq 333505) is already 0x7 — the working RLC is busy INSTANTLY. The "300k-read boot
   poll" is actually three 100,000-read timeout loops of
   `gfx_v6_0_enable_gui_idle_interrupt(enable=false)` waiting for RLC busy to CLEAR —
   they never succeed even on working hardware (0x7 forever) and time out harmlessly.
   RLC_BUSY=1 is the RLC's normal running state. Wall-clock (thread a) is dead forever.
2. **The 0x728 A1 mismatches are a pacing artifact, fully benign:** 0x728 is a
   self-clearing strobe port (ATOM writes value|1, bit0 drops on completion). The
   kernel's fast read-after-write catches bit0 still set; our 1 ms-paced oracle read
   sees it already clear. Same data, different sample time. Dead.
3. **The ONLY remaining intentional divergence was the RULE-1 HDP skip — and it is
   load-bearing.** The VBIOS writes HDP_HOST_PATH_CNTL=0x0F200029 + HDP_MISC_CNTL=
   0x00121FE0 at trace seq 130/131, i.e. the working boot configures the CPU→VRAM host
   path 130 writes into POST; the kernel echoes 0x2C00 at seq 329374 (read-modify-
   rewrite in gfx_v6_0_gpu_init). We skipped all three writes, so OUR HDP has been at
   power-on state in every run ever — explaining the entire historic CPU→VRAM
   corruption family (VRAM diag garbage, PTE readback FFFF, Known Issue 2), and it
   means the §34 SR/CSB content was likely written through a broken path and never
   landed intact — the RLC would halt reading a garbage clear-state descriptor, which
   is exactly RLC_BUSY=0.

**§35 (Sean-approved 2026-07-02): the HDP skip is removed.** extract_full_replay.py
FORBIDDEN list emptied, tables regenerated (WR 21553→21556, SKIP 0), gpu-crash.md RULE 1
amended (kernel-verbatim values at kernel positions only). The next cold run is the
first 100%-verbatim replay with zero intentional divergences — and the first fair test
of the (b) content, since CPU→VRAM writes may finally land intact.

## 2. LIVE THREADS (everything else is §3)

**(§35) HDP un-skip — THE armed experiment.** See §1b. Tables regenerated with the three
HDP writes verbatim; binary already on disk needs no rebuild (tables load at runtime).
One cold run answers: does a zero-divergence replay with a configured HDP host path bring
the RLC up (busy on first read) and let the CSB/SR/ring content land?

**(b) Memory-side content — in the harness (§34), but untested until §35 lands:** the
content writes go CPU→FB-BAR→VRAM, the exact path the HDP skip has been corrupting; the
§34 run's "content loaded" prints prove the CPU-side writes happened, not that VRAM holds
them. Re-judged on the §35 run. Details:
the replay wrote the kernel's RLC_SAVE_AND_RESTORE_BASE / RLC_CLEAR_STATE_RESTORE_BASE
register values (0xF4002010/0xF4002020, A2 seq 329387/329388) but populated NOTHING at
those addresses. Now: `fw_trace/extract_rlc_content.py` generates from the kernel source
(gfx_v6_0.c + clearstate_si.h; sizes cross-check the archive §23 numbers exactly):
- `RLC_SR_CONTENT.bin` — 218-dword verde save/restore list → VRAM 0x201000
- `RLC_CSB_CONTENT.bin` — 256-byte descriptor header (hi/lo of base+256, size=908) +
  908-dword clear-state stream → VRAM 0x202000 (PA_SC_RASTER_CONFIG=0x1240 from trace)
- `RB0_DEFAULT_STATE.bin` — 906-dword cp_gfx_start stream → RB0 dw 0x100 (closes §30's
  "si_default_state" divergence; geometry fits the trace's WPTR 0x100→0x500 commits)
The harness writes SR/CSB after GART_Init (those VRAM bytes double as never-walked
PTE slots that GART_Init's fill sweeps). Caveat: source is the amdgpu port, trace was
radeon — same origin code, but if something's off it shows here.

**(c) remnant — config-space long shots** (si.c pcie-gen switching, MSI, VGA routing):
only if §35 comes back clean and RLC is still dead. Bus master itself is CLOSED — §34 cold
run logged `COMMAND before: 0x0 → after: 0x6`.

Parked symptom: CP→GART RPTR writeback never lands in host RAM (archive §28.5) — rechecks
itself for free once ring tests re-run after §35.

**If §35 fails too:** the last unexplored channel is memory-side capture — re-enable
gpu-mmiotrace.service ONCE with the FB BAR also traced (mmiotrace hooks all ioremaps;
check whether the amdgpu capture script filtered to the reg BAR), giving the kernel's
VRAM-side writes verbatim instead of source-reconstructed. Note: the 61 MB timestamped
amdgpu raw log referenced in archive §32 is NOT in mmiotrace_boot/ anymore — locate or
recapture before relying on it.

## 3. RULED OUT — do not re-litigate (evidence in parentheses)

**Init sequence / register level:**
- The entire BAR0 MMIO init sequence as the divergence (§33 verbatim replay + 1,185 oracles).
- RLC firmware image, version, upload path (trace-extracted fw §21; §23-FWVER full 2048-word SRAM readback: 0 mismatches).
- RLC register offsets/sequence (§18 fixed per-word UCODE_ADDR + two decimal-typo offsets; §23 full pre-RLC-start state reconciliation vs kernel: identical).
- CP PFP/CE/ME ucode images, ports, load order (§24: extractor rotation found+fixed, tails verified 0x7/0x2/0xF0601; §25 wedge unchanged with genuine ucode).
- Clock gating state (§22 removed pre-start CG-disable; §25 replicated the kernel's exact post-DPM CG transition; wedge unchanged).
- SMC firmware version + DPM protocol (§26: trace SMC fw + verbatim latch/message replay; §27: all 73 msgs resp 0x1; wedge unchanged). SMC/DPM fully eliminated.
- Golden regs, tile modes, IIO, CGTS table, CP_PERFMON (Jun 22 fixes, present in trace replay anyway).
- GART plumbing: GPU-side page walk of our PTEs (§20: CP prefetch streamed ring bytes from GART; §19's "PTEs are the blocker" disproven). Skip-bulk + 64-bit PTE writes are correct and stay.
- VM aperture/context values, PAGE_TABLE_START fix #12 (reconciled §23; deliberate divergence, CP fetch works).
- Shader payload, shader code, buffer descriptors, IB encoding, basic PM4 packet encoding, ring choice (pre-§8).
- Duplicate ME_INIT emit (§19 dedup), FW-order theories (§18 "ME first" was a port-offset misread — §24).

**Experiments that actively hurt — never repeat:**
- SRBM_GFX_CNTL writes before compute SET_SH (§16: immediate CP_STALLED_STAT3=0xFFFFFFFF, fabric wedge).
- PCI config 0x7c ASIC reset (gpu_reset.sh: caused the lockups it was meant to fix; deleted 2026-07-02).
- Unpaced full-speed MMIO replay (§32 freeze; 1 ms pacing cured it).
- 11.8M bulk dummy-PTE fill (WC overflow, PTE corruption; kernel binds used ranges only).
- §18's pre-RLC-start CG-disable block (the one real write-level divergence found in §22).

**Whole narratives voided by instrumentation bugs — do not resurrect their conclusions:**
- "Wedges at first compute SET_SH" (§12–§28): RPTR is the FETCH pointer, not retirement (§31 proved it tracks WPTR through ~60 with zero execution; the pin at 60-64 is the prefetch FIFO filling).
- "RLC dead / SH bus dead" (§20–§22): every "RLC_STAT" read was 0xC350, not 0xC34C (off-by-4 decimal typo). §24: RLC_STAT=0x7 on contaminated boots. (On TRUE cold it's 0x6 — §33; that's the live lead, not these.)
- "GART PTEs corrupt GPU-side" (§19): CPU BAR0 *readback* of VRAM is unreliable cold; GPU-side walk was fine.
- Every conclusion from any boot between Jun 19 and §32: `gpu-mmiotrace.service` amdgpu-inited bus 2 on EVERY boot — no test in §8–§31 was cold. They were "post-amdgpu-teardown" tests (a different, still-reproducible state).

**Killed by the §34 cold run + trace re-read (2026-07-02 late):**
- RLC poll wall-clock: kernel RLC is busy on its FIRST read after RLC_CNTL=1 (seq 333505 = 0x7); no boot poll ever existed. 2M paced reads on ours never left 0x6.
- PCI bus master: enabled from cold by GPU_BAR_Enable (logged 0x0→0x6), replay still fails.
- 0x728 A1 mismatches: self-clearing strobe port + our 1 ms pacing = sample-time artifact.
- "300k-read RLC_STAT poll": three 100k-read wait-for-idle timeout loops (gfx_v6_0_enable_gui_idle_interrupt(false)) that never succeed on ANY hardware — extractor's POLL-until-0x7 semantic was wrong but harmless.

**Instrumentation false signals (calibration for reading future logs):**
- RPTR==WPTR ≠ executed (fetch position). PM4_WaitIdle idle=1 is a fetch-position false positive.
- CP_STAT=0x800001E3 has NO kernel baseline (kernel never reads it); busy-bits can mean parked OR wedged.
- SH-space MMIO readback 0 proves nothing (kernel does zero SH-space MMIO accesses all boot; no reference). 0xB020 reads a STABLE 0xA7B3F7EB across cold boots — deterministic, unexplained, not floating bus.
- GART WB shadow reads 0 all run (writeback never lands) — use MMIO RPTR only.
- The §33 harness verdict block was hardcoded text (fixed; recompute from SCRATCH_REG0 raw lines when reading old logs).

**Tooling dead end (researched 2026-07-02):** there is no deployable register-level SI simulator.
Multi2Sim = ISA/OpenCL only, dead since ~2017. gem5 GPUFS runs the real amdgpu driver but gfx9+
only, behavioral CP (doesn't execute real ME/RLC fw). AMD's register-accurate model is internal
Palladium RTL emulation (amdgpu `emu_mode` is its vestige) — never released. **The kernel source
tree (`/home/bob/linux`) + the traces + the replay harness ARE the simulator substitute.**

## 4. TEST PROTOCOL (one cold boot must answer every armed thread)

Rebuild: `cd ~/Ailang-Self-Hosting- && ./ailang.x TestCode/test_replay_init.ailang test_replay_init`
Run (from SSH; screen survives freezes):
```
sudo ./test_replay_init 2>&1 | while IFS= read -r l; do printf '%s\n' "$l"; printf '%s\n' "$l" >> replay_mmiotrace.txt; sync replay_mmiotrace.txt; done
```
- Service stays disabled; cold reboot first; nothing touches bus 2 before the run (no test_accel_gcn).
- The harness HARD-ABORTS on a posted card (§34 guard: CONFIG_MEMSIZE must read 0).
  An abort means the boot wasn't cold — reboot; do not work around the guard.
- Freeze localization: last `[§30-AT]` breadcrumb (every 100 records) → look seq range up in `fw_trace/FULL_REPLAY_A1/2.txt` BEFORE any new theory.

**Read order for the next log (§35 run: same binary, regenerated tables with HDP verbatim):**
1. `[§34] cold entry confirmed` + `PCI COMMAND before: 0x0 after: 0x6` — entry sane.
2. A1 record ~97-98 region (seq 130/131): the HDP writes now execute — if the box wedges
   HERE, RULE 1's ad-hoc-write danger extends to verbatim replay too; last breadcrumb
   localizes it. (Not expected: VBIOS does this write on every boot of this box.)
3. **`RLC_STAT 0xC34C` POLL — expect hit=1 with reads≈0 if HDP was the story**
   (kernel is busy on its first read). Any hit=1 ⇒ RLC solved; still 0x6 ⇒ HDP wasn't
   it either ⇒ go to §2 "if §35 fails" (FB-BAR capture).
4. Three ring-test lines `reg=0x8500 want=0xDEADBEEF hit=` — hit=1 = first ME execution
   ever = cold CP bringup solved.
5. `[§30-MIS]` count — expect the 0x2C00 oracle mismatch at seq 329373 to DISAPPEAR
   (we now write it). Remaining noise: 0x728 strobe artifacts, MC training data.
6. dst=42 remains the endgame metric (separate dispatch test after replay-init succeeds).

## 5. KEY ASSETS

- `fw_trace/` — extractors + replay tables (.bin regenerable from .txt/scripts; `*.bin` gitignored).
  FULL_REPLAY_A1/A2 (init), DPM_REPLAY_P/AB/C (SMC), TRACE_VERDE_* (trace-exact firmware),
  extract_rlc_content.py → RLC_SR/RLC_CSB/RB0_DEFAULT_STATE content blobs (§34, from kernel source).
- `bus2_all.txt` — seq-only kernel mmiotrace of the working radeon cold init (Jun 19). The oracle.
- `mmiotrace_boot/mmiotrace_raw.log` — 61 MB timestamped **amdgpu** cold init (captured 16:56 Jul 2; the radeon-timestamped original was overwritten — archive §32 DISCOVERY 2). Candidate future replay source.
- `/home/bob/linux/drivers/gpu/drm/amd/amdgpu/` — gfx_v6_0.c, clearstate_si.h, si.c: the reference model for anything the trace can't show (memory contents, config space, timing).
- `Library.AMDGPUReplay.ailang` + `TestCode/test_replay_init.ailang` — the harness (1 ms write pacing, 15 µs poll pacing, breadcrumbs, RULE-1 skips, computed verdict).
- Layout/VRAM/GART constants: gpu-crash.md; kernel-VA GART map in archive §30 (WB 0xFF00401000, IH 0xFF00609000, RB0/1/2 0xFF00619000/1D/1F).
- Old dispatch-path test: `test_accel_gcn` (§29 probe build) — superseded; only rerun when a section says so.

## 6. HISTORY

Jun 16–22: bringup + crashes + GART relocation (gpu-crash.md). Jun 19: working radeon trace captured.
Jul 1–2: seventeen "cold" iterations chasing RLC/CP/CG/SMC ghosts — all on contaminated boots
(archive §8–§29). Jul 2: method change to full-trace verbatim replay with read-oracles (§30),
contamination discovered + service disabled (§32), first true-cold test (§33) → current state.

**Update this doc after every run: move findings to §3 when killed, keep §2 to the live few.**
