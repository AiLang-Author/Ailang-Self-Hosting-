# AILang AMD GPU Compute — Handoff (condensed 2026-07-02, post-§33)

**Target:** Cape Verde (GCN1 / Southern Islands), bus 2 = compute GPU.
**Goal:** get a compute dispatch to produce correct output (`dst[i]=src[i]+42`).

**Read this + `gpu-crash.md` (hard safety RULES) before editing.**
Full §8–§33 narrative history: `git show 7cf8eec2:RING1_GART_FIX_HANDOFF.md`.
References below like "archive §24" point there.

## 0. HARD RULES (summary — gpu-crash.md is authoritative)

1. NEVER touch the DISPLAY GPU (bus 1 / 01:00.0). Guards stay. Every run logs `using GPU N (bus 2)`.
2. NEVER write HDP_HOST_PATH_CNTL (0x2C00) / HDP_MISC_CNTL (0x2F4C) — RD990 fabric deadlock.
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

## 2. LIVE THREADS (everything else is §3)

**(a) RLC poll wall-clock** — our 2M unpaced reads ≈ 3 s; the kernel's 300k reads ran under
mmiotrace (pagefault per access), plausibly much longer. Poll reads now paced 15 µs (~33 s max)
and the harness verdict print is now computed, not hardcoded (archive §33 bug). Binary rebuilt.
A timeout on the next run means "never", not "too soon".

**(b) Memory-side content the trace can't carry.** The replay writes the kernel's
RLC_SAVE_AND_RESTORE_BASE / RLC_CLEAR_STATE_RESTORE_BASE register values but populates
NOTHING at those addresses; the kernel populates the 218-dword verde SR list + CSB
(256-byte descriptor header + clear-state dwords) via CPU→VRAM before RLC start.
Same class: RB0 ring bytes 0x100–0x500 hold PACKET2 filler where the kernel has the
si_default_state PM4 stream. Sources: `/home/bob/linux/drivers/gpu/drm/amd/amdgpu/`
gfx_v6_0.c (`gfx_v6_0_rlc_init`, `gfx_v6_0_get_csb_buffer`, `gfx_v6_0_cp_gfx_start`,
`verde_rlc_save_restore_register_list`) + clearstate_si.h. Fully derivable offline.

**(c) Non-BAR0 device state.** mmiotrace captures BAR0 only. The kernel also:
- sets PCI **bus master** (`pci_set_master`) — without COMMAND bit 2 the GPU cannot DMA:
  no ring fetch from GART, no RPTR writeback, no fence writes. Our sysfs BAR-map path may
  never set it on a true-cold boot; every pre-§32 boot had it set by the service's amdgpu bind.
  **This one bit could explain the parked ME (§28.5's "RPTR writeback never lands" is a
  DMA write that never arrives) — check FIRST.**
- other config-space writes (si_pcie_gen3_enable, MSI) — likely optional, audit anyway.

Parked symptom, probably (c): CP→GART RPTR writeback never lands in host RAM (archive §28.5).

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
- Freeze localization: last `[§30-AT]` breadcrumb (every 100 records) → look seq range up in `fw_trace/FULL_REPLAY_A1/2.txt` BEFORE any new theory.
- Cold entry sanity: seq-7 CONFIG_MEMSIZE oracle must read 0 (unposted). A mismatch storm in the first ~100 records ⇒ boot wasn't cold; stop.

**Read order for the next log:**
1. PCI COMMAND print (thread c): was bus master already set? did we set it?
2. `RLC_STAT 0xC34C` POLL line (threads a+b): hit=1 ⇒ RLC solved — read on. Still 0x6 after ~33 s paced ⇒ "never", and (a) is dead too.
3. Three ring-test lines `reg=0x8500 want=0xDEADBEEF hit=` — hit=1 = first ME execution ever = cold CP bringup solved.
4. `[§30-MIS]` lines + first_divergence_seq — judge by register class (calibration regs are noise).
5. dst=42 remains the endgame metric (separate dispatch test after replay-init succeeds).

## 5. KEY ASSETS

- `fw_trace/` — extractors + replay tables (.bin regenerable from .txt/scripts; `*.bin` gitignored).
  FULL_REPLAY_A1/A2 (init), DPM_REPLAY_P/AB/C (SMC), TRACE_VERDE_* (trace-exact firmware).
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
