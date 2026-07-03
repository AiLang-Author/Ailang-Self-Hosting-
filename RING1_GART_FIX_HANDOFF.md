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
amended (kernel-verbatim values at kernel positions only).

## 1c. §35 COLD RUN (2026-07-02 21:43) — zero-divergence replay STILL fails;
## HDP verbatim confirmed safe; the BAR0 channel is now fully closed

Log: `replay_mmiotrace.txt` (22,308 lines; §34 log preserved as `replay_mmiotrace_s34.txt`).
Cold guard passed, PCI COMMAND 0x0→0x6.

- **HDP writes executed verbatim** (records 57/58 = seq 130/131, echo at 329374) —
  no wedge, run completed. RULE 1's danger does NOT extend to kernel-verbatim replay.
  The 0x2C00 oracle at seq 329373 now matches (mismatch gone, as predicted).
- **RLC_STAT still 0x6** (poll seq 333505: want 0x7, got 0x6 after 2M paced reads).
  The HDP skip was NOT the RLC story.
- **Ring tests still fail** (0x8500 poll got=0xCAFEDEAD; SCRATCH_REG0=0xCAFEDEAD).
  ME lifetime execution count remains zero.
- A1 mismatches=38: 24× 0x2A48 (MC_SEQ_IO_DEBUG_DATA training, benign), 9× 0x728
  (strobe artifact, benign), 3× 0x610 + 1× 0x614 (CG_SPLL block, seq 2527–2684 —
  lock/status bits, same sample-timing pattern as 0x728; the 0x614 polls DID hit),
  1× 0x28A4C (seq 3670: kernel=0 ours=0x46000000 — single, unexplained, low priority).
- A2 mismatches=2 = the two ring-test oracle reads ONLY.

**Conclusion: a 100%-verbatim, zero-intentional-divergence BAR0 MMIO replay does not
bring the chip up.** The divergence is definitively in memory-side content or
non-BAR0 device state.

**RESOLVED (readback 21:52, `vram_readback_s35.txt`): the content LANDED INTACT.**
`test_vram_readback` on the same boot: SR @0x201000 218/218 dw exact, CSB @0x202000
972/972 dw exact (header 0xF4/0x202100/0x38C correct). Two consequences:
- **CPU→FB-BAR→VRAM works with HDP configured**, and FB-BAR readback is trustworthy
  (a perfect 1,190-dw match can't be luck) — Known Issue 2 era is probably over.
- **Thread (b) is dead as an explanation:** correct SR/CSB content was sitting in VRAM
  and the RLC still never set busy. Note the §1b theory was always shaky here: on SI
  the RLC fetches the CSB at CLEAR_STATE/context-switch time, not at RLC_CNTL=1 —
  RLC busy should assert from ucode execution start, before any memory access.
The PTE dump at VRAM 0 shows uninitialized garbage — EXPECTED (skip-bulk fill: head
slots are never-walked VRAM-range VAs we never write; do not read it as corruption).

With BAR0 verbatim (§35), ucode verified in SRAM (§23-FWVER), clocks/CG/SMC replayed
(§25–§27), HDP configured, and memory content now proven present and intact: **the RLC
microcontroller refuses to start executing with every observable input identical to the
working boot. The remaining channels are PCI config space / non-BAR0 device state (c),
and the kernel's true memory-side writes (FB-BAR capture) as the audit of our
reconstruction.**

## 1d. §37 COLD RUN (2026-07-02 ~22:35) — COMMAND=0x7 mirrored, NOT the story;
## every captured channel is now verbatim and the RLC still refuses to start

Log: `replay_mmiotrace.txt` (§37 only; §35 run + the warm-abort attempt preserved in
`replay_mmiotrace_s35.txt`). The §34 posted-card guard fired correctly on a first
warm attempt this evening — its second live save.

- **COMMAND 0x0→0x7 from cold** (I/O decode bit mirrored, the one change vs §35). No effect:
- **RLC_STAT still 0x6** (poll seq 333505: want 0x7, got 0x6, 2M paced reads, hit=0).
- **Ring tests still fail** (0x8500 poll got=0xCAFEDEAD; SCRATCH_REG0=0xCAFEDEAD).
  ME lifetime execution count remains zero.
- A1 mismatches=38, exactly the §35 benign classes (24× 0x2A48 MC training, 9× 0x728
  strobe, 3× 0x610 + 1× 0x614 SPLL sample-timing, 1× 0x28A4C seq 3670 ours=0x46000000 —
  same value as §35, so it's deterministic, not noise). A2=2 (the ring-test reads only).
  Clean apples-to-apples with §35.

**The pre-registered §37-fails conclusion is now in force: every observable channel —
BAR0 writes+reads+widths, VRAM content, GPU config space minus MSI — is
verbatim-identical to a working boot, and the RLC does not start. The §3 rule
"do not go looking in register writes again" now extends to ALL captured channels.**

## 1e. §38 CAPTURE BOOT (2026-07-02 23:00–23:13) — root port NEVER touched;
## the working boot's entire config-space story is COMMAND 0x407 + MSI

`capture_working_pci.sh` was interrupted mid-`sleep 25` (log stops there; pre-bind
snapshots only), but amdgpu was still bound to bus 2 on the same boot — the working
state was live, and `finish_capture_working_pci.sh` (23:13) rescued it. Bringup
verified from the journal: `Initialized amdgpu 3.64.0 for 0000:02:00.0` + 88 MSI
interrupts on IRQ 58. (NOTE for future greps: modern amdgpu prints NO "ring test
succeeded" lines — that's radeon-era. The capture script's RINGOK count reads 0 on
success; use the Initialized line.) All files in `pci_working_boot/`.

- **Root port (00:03.0): prebind vs working BYTE-IDENTICAL** (full 4K config as
  root). The kernel never writes the root port. Its visible state also matches our
  post-replay snapshot (`lspci_rootport_post_s37.txt`, first 77 lines; the rest is
  BIOS-stable by the prebind==working proof). Bridge channel CLOSED.
- **Audio (02:00.1): prebind vs working identical** — amdgpu bringup doesn't touch
  it either. (Also: `lspci_bus2f1_post_s37.txt` turned out EMPTY, 0 bytes — the §38
  note citing it stands on the /proc/interrupts evidence, not that file.)
- **GPU (02:00.0): the complete working-boot delta across the entire 4K config
  space is exactly two registers:**
  - COMMAND `0x0000 → 0x0407` — I/O+ Mem+ BusMaster+ **DisINTx+**. Bit 10 is set by
    the kernel as part of MSI enable; our §37 mirror wrote 0x0007, never 0x0407.
  - MSI cap @0xa0: ctrl `0x0081` (Enable, 64-bit), **Address `0x00000000FEE15000`,
    Data `0x0022`**. No AMD-Vi/IR on RD990 ⇒ plain xAPIC: dest APIC 0x15 = CPU5
    (FX-8320 IDs run 0x10–0x17; matches IRQ 58 landing on CPU5), vector 0x22,
    edge/fixed. Replay risk on a future boot = one bounded stray vector on CPU5.
- Unbind teardown (gpu_postunbind.txt): clears BusMaster + DisINTx + MSI, leaves 0x3.

**§39 ARMED: MSI mirror with the captured exact values.** `GPU_BAR_EnableMSI`
(Library.AMDGPUBAR.ailang) writes addr/data → DisINTx → enable (msi_capability_init
order), cap-ID sanity check, display-GPU lockout. Called at the A1/A2 boundary of
`test_replay_init` (radeon_irq_kms_init position: after device init, before
si_startup). Binary rebuilt. This is the LAST captured-channel delta; after §39
only de-pace (last resort) remains.

## 2. LIVE THREADS (everything else is §3)

**(c) PCI config space / non-BAR0 device state — AUDITED OFFLINE 2026-07-02 late;
much smaller than feared but not empty.** Findings (snapshots: `lspci_bus2_post_s35.txt`
= our post-replay state, `lspci_bus1_vbios_ref.txt` = VBIOS-posted reference; note bus 1
is NOT a working-compute reference — no radeon ever bound, and VBIOS POST doesn't start
the RLC either):
- `si_pcie_gen3_enable` EARLY-RETURNED on the working boot — proven from the trace:
  seq 13819-13821 selects port-indirect 0xA4 (LC_SPEED_CNTL), READS 0x074C2D23, then
  moves on; none of the speed-change writes follow. Link already gen2 (5GT/s x8 on both
  cards now). So NO LNKCTL/LNKCTL2/HAWD config writes ever happened. Dead.
- Remaining real config-space deltas of the working boot vs ours: **MSI Enable+**
  (radeon_irq_kms_init, which runs BEFORE rlc start in the radeon init order) and
  **COMMAND I/O bit** (pci_enable_device sets I/O+ since the card has an I/O BAR;
  working boot COMMAND=0x7, ours=0x6). Both weak as RLC gates, both trivial to mirror.
- **Port I/O channel: KILLED (2026-07-02 late).** `fw_trace/scan_atom_io.py` walked the
  VBIOS (`vbios_bus2.rom`, dumped 22:08) ASIC_Init + all 38 reachable called tables with
  kernel-atom.c-exact operand sizes: zero desyncs, 52 SETPORTs, ALL ATI-mode (port 0=MM,
  2/3/4=IIO programs — MMIO register pairs, trace-visible). No PCI/SYSIO port switch
  exists. ATOM never does port I/O on this card.
- **COMMAND 0x7 CONFIRMED from the working boot:** `mmiotrace_boot/dmesg_amdgpu.txt`
  line 93: `enabling device (0006 -> 0007)` — the kernel enables I/O decode. (With ATOM
  port-I/O dead, this bit likely decodes nothing anyone accesses — mirror it anyway,
  it's one write.)

**Extractor audit (2026-07-02 late): CLEAN.** Every event in window A maps — 0 unmapped
names, 0 dropped writes, all reads kept (isolated→oracle, run≥3→poll). The BAR0 replay
is complete at the extraction level as well.

**(§36, 2026-07-02 ~22:20) FB-BAR DIFF DONE — memory-side channel CLOSED, zero
actionable divergences.** `fw_trace/extract_fbbar.py` parsed the 61 MB amdgpu raw log
(mmiotrace hooks ALL ioremaps — only the bus2_all.txt parser filtered to the reg BAR;
map id 9 = bus 2 FB BAR full 256 MB @0xb0000000; that boot was a WORKING bringup —
UVD (IP block 7) init success ⇒ gfx_v6_0 (block 3) hw_init passed its ring tests).
Findings:
- Kernel VRAM writes before ring tests = GART table (0x2000-0x4928) + SR @0x201000 +
  CSB @0x202000 (same offsets as radeon) + a 2.5 MB region @0x435A18 (t=23.09-23.72 =
  sw_init phase, presumed UVD fw staging — post-ring-test-irrelevant). Nothing else.
  We write all of the relevant set, and the §35 readback proved ours lands.
- **SR content: kernel matches our blob 218/218. CSB: 971/972.** The one divergent
  dword (stream pos 903, PA_SC_RASTER_CONFIG value): amdgpu bakes 0 into the CSB
  because get_csb_buffer runs at sw_init BEFORE rb_config[0][0].raster_config is
  computed (gfx_v6_0.c:2938) — and boots fine, proving the dword irrelevant to
  bringup. The MMIO reg gets the real value (0x124a early, 0x1240 final = radeon's
  value = ours). NO change to our blob needed.
- Width audit: every bus-2 reg-BAR access in the working boot is 32-bit
  (49,160 W / 309,594 R, all width 4). No 64-bit register writes we'd be splitting.
- amdgpu wrote RLC_CLEAR_STATE_RESTORE_BASE (0xC30C) = 0 at rlc-resume (radeon wrote
  0xF4002020); works either way — CSB base value is not the RLC-start gate.
Kernel dump asset: `fw_trace/KERNEL_SR_CSB.bin` ([0x201000,0x203000) reconstruction).
Caveat that stands: mmiotrace can NEVER see GTT/host-RAM writes (plain RAM, not
ioremap) — GART ring content stays source-reconstructed, and is irrelevant to
RLC-busy.

**(§38 CANDIDATES — post-§37 decision point.) SUPERSEDED by §1e: the capture ran
2026-07-02 23:13, root-port/audio channels closed, §39 MSI mirror armed with exact
values. Kept for context; de-pace (item 3) is the only candidate left after §39:**
1. **Offline audits (no boot, no risk) — partially done 2026-07-02 23:xx:**
   - **Mapping attributes: CLOSED.** Reg BAR = resource2 plain (UC, same as kernel
     ioremap). VRAM = resource0 + O_SYNC (UC) vs kernel ioremap_wc — known, already
     tried the other way (resource0_wc hangs the PCI bus on RD990 from userspace,
     comment at Library.AMDGPUBAR.ailang:918), and content-proven irrelevant by the
     §35 readback. UC is strictly more ordered than WC. Nothing left here.
   - Bridge/root-port (00:03.0) config space: mmiotrace sees NO PCI config writes,
     and the (c) audit covered the GPU's OWN header only. Unprivileged snapshots
     taken (`lspci_rootport_post_s37.txt`, caps hidden) — re-run as root for the full
     dump. **`capture_working_pci.sh` (written 2026-07-02 night) fills the gap in ONE
     boot:** cold boot → `sudo bash capture_working_pci.sh` → modprobes amdgpu
     si_support=1 (the proven capture-boot mechanism, no mmiotrace), verifies ring
     tests in dmesg, snapshots root port + GPU + audio config space WHILE BOUND
     (incl. the GPU's live MSI address/data — makes thread 2 exact instead of
     invented), then unbinds bus 2. Card is POSTed afterward: cold reboot before
     any replay run.
   - NOTED, symmetric, no action: 02:00.1 (GPU audio function) is owned by
     snd_hda_intel on EVERY boot incl. cold test boots (D0/active, BusMaster+, MSI).
     Same kernel/driver as the working boot, so not a divergence — but it is the one
     kernel agent touching the chip pre-harness (`lspci_bus2f1_post_s37.txt`).
2. **MSI enable — the last GPU-config-space delta.** Weak as an RLC gate (an on-chip
   microcontroller needs no interrupt plumbing to execute ucode from SRAM), and
   mirroring it from userspace means inventing an MSI address/data (APIC-risky
   mid-replay). One cold run if we decide it's worth it.
3. **Pacing (1 ms/write vs native speed)** — unfalsifiable without removing pacing,
   which froze the box twice (§32). If ever attempted, de-pace ONLY the RLC-start
   neighborhood (a few hundred records), not the full replay. Last resort.

**(b) Memory-side content — WRITTEN AND VERIFIED PRESENT (readback 21:52), but unused
by the chip so far:** kept here only as reference for what the harness loads. Details:
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

(Bus master itself is CLOSED — §34 cold run logged `COMMAND before: 0x0 → after: 0x6`.)

Parked symptom: CP→GART RPTR writeback never lands in host RAM (archive §28.5) — rechecks
itself for free once ring tests ever pass.

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

**Killed by the offline audits (2026-07-02 late):**
- ATOM port-I/O channel: scan_atom_io.py — no PCI/SYSIO SETPORT reachable from
  ASIC_Init (52 SETPORTs, all ATI/MMIO-mode, zero walk desyncs).
- PCIe-gen config writes: si_pcie_gen3_enable early-returned on the working boot
  (trace seq 13819-13821: LC_SPEED_CNTL read, no speed-change writes follow).
- "Need a new capture boot for FB-BAR data": the 16:56 Jul 2 amdgpu raw log already
  contains the full FB BAR (map id 9) from a working bringup.
- Extractor completeness: 0 unmapped events in window A; all kernel reads kept as
  oracle/poll.

**Killed by the §35 readback (2026-07-02 21:52, `vram_readback_s35.txt`):**
- "SR/CSB content never lands in VRAM / CPU→VRAM still broken": 1,190/1,190 dwords
  exact on the §35 boot. CPU→FB-BAR→VRAM works with HDP configured, and FB-BAR
  readback is trustworthy on a posted card.
- "RLC halts reading a garbage clear-state descriptor" (§1b theory): content was
  intact and RLC still never set busy — and on SI the CSB isn't even fetched at
  RLC_CNTL=1. The RLC ucode never STARTS; it doesn't get far enough to consume memory.
- VRAM-0 PTE-head garbage as a corruption signal: those slots are never written
  (skip-bulk fill) — uninitialized VRAM is the expected content there.

**Killed by the §35 cold run (2026-07-02 21:43):**
- The HDP RULE-1 skip as the RLC/ring blocker: HDP written kernel-verbatim at seq
  130/131 + 329374 echo, zero intentional divergences left — RLC still 0x6, ME still
  zero packets. (HDP may still matter for CPU→VRAM quality — that's the READBACK test —
  but it is not what keeps the RLC parked.)
- "Verbatim HDP replay might wedge like ad-hoc writes did": ran clean twice through
  seq 130/131 and 329374. RULE 1 as amended stands.
- The entire BAR0 MMIO channel, now including the last skipped writes: 21,556-write
  zero-divergence replay, A2 oracles clean except the 2 ring-test reads. Do not go
  looking for the bug in register writes again — it is not there.

**Killed by the §37 cold run (2026-07-02 ~22:35):**
- COMMAND I/O decode bit as the RLC/ring gate: mirrored 0x0→0x7 from cold; outcome
  identical to §35 (RLC_STAT 0x6, ring tests fail, same 38+2 benign mismatch classes).
- With it, the entire GPU config-space channel minus MSI. Combined with §35 (BAR0)
  and §36 (memory content): no captured channel contains the divergence. Do not
  re-audit BAR0 regs, read/widths, VRAM content, or the GPU config header.

**Killed by the §38 capture boot (2026-07-02 23:13, `pci_working_boot/`):**
- Root-port/bridge (00:03.0) config as a channel: prebind vs working byte-identical
  (full 4K, as root) — the kernel never writes it, and BIOS state is boot-stable.
- Audio function (02:00.1) config as a divergence: prebind vs working identical.
- "Invented MSI values" risk: live working values captured (addr 0xFEE15000,
  data 0x0022, ctrl 0x0081, COMMAND 0x0407). Nothing about the MSI mirror needs
  to be guessed anymore.
- "ring test succeeded" dmesg lines as a bringup check for amdgpu: radeon-era
  format; amdgpu prints none on success. Use the `Initialized amdgpu ... for
  0000:02:00.0` line.

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

**NEXT ACTION — §39 MSI-MIRROR COLD RUN (armed 2026-07-02 23:30).** The card is
POSTed from the §38 capture boot: **cold reboot first**, then the standard §4 run
above. The rebuilt harness prints `[§39] MSI mirrored (addr 0xFEE15000 data 0x0022,
COMMAND 0x407)` between A1 and A2 — if that line is missing the binary is stale.
Expected readouts: RLC_STAT poll at seq 333505 (0x7 = RLC started, the lead moves)
and the ring-test SCRATCH_REG0 lines. If §39 fails identically, the only remaining
lever is partial de-pace of the RLC-start neighborhood (last resort, §38 item 3);
watch dmesg afterward for a stray vector-0x22 report on CPU5 (bounded, expected
harmless).

dst=42 remains the endgame metric (separate dispatch test after replay-init succeeds).

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
