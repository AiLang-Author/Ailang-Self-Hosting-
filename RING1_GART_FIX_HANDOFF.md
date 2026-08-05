# AILang AMD GPU Compute — Handoff (condensed 2026-07-02; §42 done 2026-07-03: ZERO stations executed — H1 no-execute vs H2 writes-never-land fork)

**Target:** Cape Verde (GCN1 / Southern Islands), bus 2 = compute GPU.
**Goal:** get a compute dispatch to produce correct output (`dst[i]=src[i]+42`).

**Read this + `gpu-crash.md` (hard safety RULES) before editing.**
Archives: §8–§33 narrative `git show 7cf8eec2:RING1_GART_FIX_HANDOFF.md`;
§34–§39 narrative `git show 1f7ce115:RING1_GART_FIX_HANDOFF.md`.
References like "archive §24" point there.

## 0. HARD RULES (summary — gpu-crash.md is authoritative)

1. NEVER touch the DISPLAY GPU (bus 1 / 01:00.0). Guards stay. Every run logs `using GPU N (bus 2)`.
2. HDP_HOST_PATH_CNTL (0x2C00) / HDP_MISC_CNTL (0x2F4C): kernel-verbatim replay values at
   kernel trace positions ONLY (amended 2026-07-02) — ad-hoc writes still deadlock.
3. NEVER write PCI config 0x7c (ASIC reset) — fabric hangs. gpu_reset.sh is deleted; do not recreate.
4. NEVER re-add SRBM_GFX_CNTL pokes (archive §16 — wedges fabric).
5. `gpu-mmiotrace.service` stays DISABLED (archive §32). Re-enable only to capture new traces on purpose.
6. Human executes all GPU tests, from SSH, with the fsync-per-line logger (§4). Cold reboot before each.

## 1. CURRENT STATE (2026-07-03 13:23 — §42 cold run DONE: ZERO stations executed; §41's "wedge mid default-state" dead; H1-vs-H2 fork open)

The §30 replay harness (`test_replay_init`) replays the ENTIRE working kernel init
(fw_trace/FULL_REPLAY_A1+A2, from the Jun 19 radeon trace `bus2_all.txt`: 21,556
writes, 1,185 read-oracles, 11 polls) onto a true-cold card, verbatim, plus the
kernel's memory-side content (GART table, RLC SR/CSB, ring images). As of §40:
A1 paced 1 ms/write, A2 UNPACED (seq 12088–439996, MMIO_WR log suppressed in-window).

**§42 RAN COLD 2026-07-03 13:23 (`replay_mmiotrace_s42.txt`): both §42 questions
answered.** Mechanics clean: cold guard passed, all markers fired, RLC_STAT 0x7
FIRST read at seq 333505 (de-pace→RLC-start now 3-for-3), A1 38 benign
mismatches (same taxonomy), A2 mismatches = the 2 ring-test oracles only.
- **(a) FROZEN, not crawling:** all three RPTR samples identical across 2 s
  (RB0 0x600, RB1 0x100, RB2 0x100). Hard wedge, not a timeout-class problem.
- **(b) `SCRATCH_REG1=0x0` (baseline 0x0): ZERO stations executed — not even
  station 01, immediately after ME_INITIALIZE.** Neither replay table ever
  touches 0x8504 (grep-checked post-run), so no clobber: **no ME-issued
  register write landed all run.** §41's "wedge mid default-state at dw 208"
  was a FETCH-position artifact — voided (§3).
- **Fetch ran FULL this run: RB0 RPTR=WPTR=0x600**, including the ring test at
  dw 0x500 that §41 never fetched; RB2 also hit WPTR (0x100 vs §41's 0x48).
  Fetch depth varies run-to-run with content/timing — RPTR position carries NO
  information about the execution wedge (calibration §3).
- **NEW SIGNAL: `GRBM_STATUS=0xA24C3028` ≠ this box's documented normal
  0xA0003028 — first deviation ever observed on this box.** Delta decoded vs
  `gfx_6_0_sh_mask.h`: **IA_BUSY_NO_DMA | IA_BUSY | SPI_BUSY | PA_BUSY** — gfx
  front-end pipeline blocks busy. §41 (same stream minus tracers) read the
  normal value at the same harness position. `CP_ME_CNTL=0x0` (no halt bits).
- Still failing: SCRATCH_REG0 stayed 0xCAFEDEAD (2M-read poll @439970) — the
  kernel-verbatim ring test never landed either.
- dmesg stray-vector check for THIS boot pending (needs sudo; class already
  closed by §41 — low priority).

**The fork the tracer cannot split (both fit every §42 fact):**
- **H1 — ME executes nothing:** never retires even packet 0 (or wedges INSIDE
  ME_INITIALIZE — station 01 can't distinguish). Busy bits = wedge signature.
- **H2 — ME executes but its register writes never land:** SET_CONFIG_REG
  writes (tracer stations AND the kernel-verbatim ring test — same packet
  type) vanish on the CP→register path. Explains the busy bits as genuinely
  engaged pipeline state from an executed default-state stream, and re-frames
  the failure as a write-path problem, not an execution problem.
§43 (§2 thread 1) is the discriminator.

**§38 capture (`pci_working_boot/`)** — working-boot PCI reference (root port
byte-identical prebind-vs-working; GPU config delta = COMMAND 0x407 + MSI
fee15000/0022/ctrl 0x81; details archive §38). §39 mirrored it cold: no effect
(config space closed in full).

## 2. LIVE THREADS (everything else is §3)

1. **§43 ARMED 2026-07-03 13:41 (binary rebuilt, `grep -ac '§43'` = 8): split
   H1 vs H2 with context-register readbacks — pure readout, zero new
   divergence (readout-only edit; ring content untouched vs §42).** The
   default-state stream is hundreds of SET_CONTEXT_REG writes with known
   values; if the ME executed the stream, the context registers hold them.
   Four anchors, each read pre-A2 (`[§43] anchor baseline` line, power-on
   values) and at the verdict (`[§43] anchor 0x... want=0x...` lines +
   computed `anchors matching stream: N/4` call). All four: distinctive
   stream value + NEVER MMIO-written by A1/A2 (grep-checked); offsets
   re-derived from RB0_DEFAULT_STATE.bin 2026-07-03:
   - **0x28230 PA_SC_EDGERULE = 0xAA99AAAA** (pkt 2, ds[144] — primary)
   - **0x28810 = 0x00090000** (pkt 5, 0xA200-span)
   - **0x28BDC = 0x00001000** (pkt 8, 0xA2A5-span, near stream end)
   - **0x28C58 = 0x0000000E** (final pkt 0xA316 — stream-done marker; note
     the 0xA2A5-span also writes it mid-stream, same value)
   - ANY anchor == stream value ⇒ ME EXECUTED ⇒ **H2** (register write-path
     is the loss; §42 busy bits = real pipeline state). Self-proving: only
     the CP could have written those offsets.
   - All at baseline ⇒ leans **H1**, NOT conclusive: CP-write→MMIO-read
     visibility on SI UNCONFIRMED (context regs ARE plain-MMIO readable —
     gfx_v6_0.c:1513, trace oracles 0x28350/0x28A4C — but the trace has ZERO
     post-ring-kick context reads; bank/context-select semantics open).
   - `[§43] GRBM_STATUS resample=` prints next to the anchors: track whether
     the §42 deviation (0xA24C3028, IA|SPI|PA busy) reproduces.
   Context-reg MMIO reads are trace-proven safe (A1 oracle-reads 0x28350 @seq
   3672 mid-A1). One cold boot, doc §4, mv log to `_s43.txt`.
   Keep the §42 tracer + RPTR resample in the binary (baseline now). Station
   map for reading 0x420000NN: 01 after ME_INITIALIZE, 02 after SET_BASE,
   03 after PREAMBLE-begin, 04–0A after SET_CONTEXT_REG 0xA000/0xA0D8/0xA1F5/
   0xA200/0xA2A1/0xA2A3/0xA2A5, 0B after PREAMBLE-end, 0C after CLEAR_STATE,
   0D after SET_CONTEXT_REG 0xA316 (stream done). Tracers shift SET_BASE to
   ring dw 10 (chunk 1 not byte-identical to kernel's; §41 layout is one
   `git show 1f7ce115` + rebuild away if ever needed).
2. **Bisect the pacing sensitivity (cheap; knowledge the real driver needs).**
   §40 de-paced all 10,764 A2 writes at once; the timing-sensitive region is
   unknown. Natural suspect: the RLC fw upload → RLC_CNTL=1 gap (2048 UCODE
   writes × 1 ms ≈ 2 s stall mid-handshake). One boot per bisection step,
   only after thread 1 stops producing.
3. ~~dmesg stray-vector check~~ CLOSED 2026-07-03: §41-boot dmesg clean (no
   stray vector / do_IRQ lines; §39/§40 buffers lost to reboots but §41 ran
   the identical MSI mirror — same-config witness).

Reference (closed but harness-relevant): the replay loads kernel-verbatim memory
content — GART table @VRAM 0x2000, RLC SR @0x201000 (218 dw), CSB @0x202000
(hdr+972 dw), RB0 default-state stream (906 dw @ dw 256) — generated by
`fw_trace/extract_rlc_content.py` from gfx_v6_0.c/clearstate_si.h, landing verified
intact by the §35 readback (1,190/1,190 dw) and matching the kernel's own FB-BAR
writes (§36: SR 218/218, CSB 971/972 — the one delta is amdgpu baking
PA_SC_RASTER_CONFIG=0 into the CSB, boots fine, irrelevant). mmiotrace can NEVER
see GTT/host-RAM writes — GART ring content stays source-reconstructed, irrelevant
to RLC-busy.

Parked symptom: CP→GART RPTR writeback never lands in host RAM (archive §28.5) —
rechecks itself for free once ring tests ever pass.

## 3. RULED OUT — do not re-litigate (evidence in parentheses)

**Init sequence / register level:**
- The entire BAR0 MMIO init sequence (§33+§35: 21,556-write zero-divergence replay,
  1,185 oracles clean except benign classes + the 2 ring-test reads). Includes the
  once-skipped HDP writes: §35 ran them kernel-verbatim (seq 130/131 + 329374 echo),
  clean, twice — RULE 1 as amended stands. Do not go looking in register writes again.
- RLC firmware image/version/upload (trace-extracted fw §21; §23-FWVER full 2048-word SRAM readback: 0 mismatches).
- RLC register offsets/sequence (§18, §23 full pre-start reconciliation vs kernel: identical).
- CP PFP/CE/ME ucode images, ports, load order (§24 rotation fix + tail verify 0x7/0x2/0xF0601).
- Clock gating state (§22, §25: kernel's exact post-DPM CG transition replicated).
- SMC firmware + DPM protocol (§26/§27: verbatim latch/message replay, all 73 msgs resp 0x1).
- Golden regs, tile modes, IIO, CGTS table, CP_PERFMON (Jun 22 fixes, in trace replay anyway).
- GART plumbing: GPU-side page walk of our PTEs works (§20 CP prefetch streamed ring bytes; §19 disproven). Skip-bulk + 64-bit PTE writes stay.
- **"CP never fetches from GART cold" (§41: RPTR moved on all 3 rings from a
  true-cold boot — RB0 0x1D0, RB1 0x100, RB2 0x48; the CP walked our PTEs and
  streamed our reconstructed ring images).** §28.5 (RPTR WRITEBACK to host RAM
  never lands) is a separate symptom and stays parked.
- Ring image content/placement (§41a offline diff: dw-for-dw vs gfx_v6_0.c,
  WPTR ground truth matches; §41 cold run: WPTRs read the trace finals).
- VM aperture/context values, PAGE_TABLE_START fix #12 (§23; deliberate divergence, CP fetch works).
- Shader payload/code, buffer descriptors, IB encoding, PM4 encoding, ring choice (pre-§8).
- Duplicate ME_INIT emit (§19), FW-order theories (§24).

**Memory-side content (§35 readback + §36 FB-BAR diff):**
- "SR/CSB never lands / CPU→VRAM broken": 1,190/1,190 dw exact readback on the §35
  boot. CPU→FB-BAR→VRAM works with HDP configured; FB-BAR readback trustworthy posted.
- "RLC halts reading garbage clear-state": content intact, RLC still never set busy —
  and on SI the CSB isn't fetched at RLC_CNTL=1; the ucode never STARTS.
- VRAM-0 PTE-head garbage as corruption signal: never-written skip-bulk slots, expected.
- Kernel writes nothing else relevant pre-ring-test (§36: GART + SR + CSB + a
  post-irrelevant 2.5 MB UVD staging region; all bus-2 reg accesses 32-bit wide).
- CSB base value (0xC30C): amdgpu writes 0, radeon 0xF4002020 — works either way.

**Config space / non-BAR0 device state:**
- MSI + COMMAND DisINTx (§39: exact captured values — addr 0xFEE15000, data
  0x0022, ctrl 0x81, COMMAND 0x407 — mirrored at the radeon_irq_kms_init
  position from cold; RLC_STAT still 0x6, rings dead, outcome identical to
  §35/§37). Config space is now closed IN FULL.
- COMMAND I/O decode bit as the gate (§37: 0x0→0x7 from cold, outcome identical to §35).
- PCI bus master (§34: enabled from cold, logged 0x0→0x6, replay still fails).
- Root-port/bridge (00:03.0) config (§38: prebind==working byte-identical, kernel
  never writes it; BIOS state boot-stable). Audio function (02:00.1) likewise.
- ATOM port-I/O channel (scan_atom_io.py over vbios_bus2.rom ASIC_Init + 38 tables:
  52 SETPORTs all ATI/MMIO-mode, zero desyncs — no PCI/SYSIO port switch exists).
- PCIe-gen config writes (si_pcie_gen3_enable early-returned on the working boot:
  trace seq 13819-13821 reads LC_SPEED_CNTL, no speed-change writes follow).
- Mapping attributes (reg BAR = resource2 plain UC both sides; VRAM UC-vs-WC known,
  content-proven irrelevant by §35 readback; resource0_wc hangs the bus from
  userspace — comment at Library.AMDGPUBAR.ailang:918).
- "Invented MSI values" risk (§38 captured live: fee15000/0022/0x81 — nothing guessed).

**Extractor / instrumentation validity:**
- Extractor completeness (audit: 0 unmapped events in window A, 0 dropped writes,
  all kernel reads kept as oracle/poll).
- "The kernel boot-polls RLC_STAT 0x6→0x7": never existed — first read after
  RLC_CNTL=1 is already 0x7; the "300k-read poll" = three 100k wait-for-idle timeout
  loops that fail on working hardware too. RLC wall-clock theories dead forever.
- 0x728 / SPLL A1 mismatches: self-clearing strobe + pacing sample-time artifact.
- "ring test succeeded" dmesg lines as an amdgpu bringup check: radeon-era format,
  amdgpu prints none — use the `Initialized amdgpu ... for 0000:02:00.0` line.

**Experiments that actively hurt — never repeat:**
- SRBM_GFX_CNTL writes before compute SET_SH (§16: fabric wedge).
- PCI config 0x7c ASIC reset (caused the lockups it was meant to fix; deleted).
- Unpaced full-speed MMIO replay OF A1 (§32 froze the box; 1 ms pacing cured it).
  AMENDED by §40: A2 unpaced is safe AND REQUIRED — pacing A2 prevents RLC start.
  Current shape (A1 paced, A2 unpaced) is proven on hardware; don't un-pace A1.
- Warm/posted-card replay (froze the box twice — §32 + the 20:33 Jul 2 incident;
  §34 guard hard-aborts on CONFIG_MEMSIZE≠0, two live saves already).
- 11.8M bulk dummy-PTE fill (WC overflow, PTE corruption; bind used ranges only).
- §18's pre-RLC-start CG-disable block.

**Whole narratives voided by instrumentation bugs — do not resurrect:**
- "ME wedges mid default-state at ring dw 0x1D0 / stream dw 208" (§41 §1):
  RPTR was the FETCH pointer again — §42 fetched RB0 to full WPTR 0x600 with
  ZERO stations executed. Fetch position never localizes execution.
- "Execution is crawling / timeout-class" (§42a: three RPTR samples over 2 s,
  all identical on all three rings — hard freeze).
- "Wedges at first compute SET_SH" (§12–§28): RPTR is the FETCH pointer, not
  retirement; the pin at 60-64 is the prefetch FIFO filling (§31).
- "RLC dead / SH bus dead" (§20–§22): reads were 0xC350 not 0xC34C (off-by-4 typo).
- "GART PTEs corrupt GPU-side" (§19): cold BAR0 readback of VRAM was the liar.
- Every conclusion from boots between Jun 19 and §32: gpu-mmiotrace.service
  amdgpu-inited bus 2 every boot — no test in §8–§31 was cold.

**Instrumentation false signals (calibration for reading future logs):**
- RPTR==WPTR ≠ executed. PM4_WaitIdle idle=1 is a fetch-position false positive.
  NOW PROVEN COLD (§41): RB1 prefetched to WPTR=0x100 with its scratch packet at
  dw 0 never executed. Also §41: per-ring prefetch depth is inconsistent (RB1
  ran to WPTR, RB2 froze at 0x48) — don't infer FIFO depth from one ring.
  REINFORCED §42: fetch depth also varies run-to-run (RB0 0x1D0→0x600, RB2
  0x48→0x100 across two cold boots, same stream ± tracers).
- GRBM_STATUS 0xA0003028 is this box's rings-dead-but-normal value (§41,
  gpu-crash.md) — but §42 read 0xA24C3028 (adds IA_BUSY_NO_DMA|IA_BUSY|
  SPI_BUSY|PA_BUSY per gfx_6_0_sh_mask.h): DEVIATIONS from 0xA0003028 are
  signal; the value itself matching normal is not.
- CP_STAT=0x800001E3 has NO kernel baseline; busy-bits can mean parked OR wedged.
- SH-space MMIO readback 0 proves nothing (kernel does zero SH-space reads all boot).
  0xB020 reads a STABLE 0xA7B3F7EB across cold boots — deterministic, unexplained.
- GART WB shadow reads 0 all run — use MMIO RPTR only.
- The §33 harness verdict block was hardcoded text (fixed; recompute from
  SCRATCH_REG0 raw lines when reading old logs).
- 1 ms write pacing is NOT transparent to the hardware (§40): paced A2 → RLC
  never starts; unpaced A2 → RLC_STAT 0x7 first read. Any future "add pacing
  for safety" change must re-prove RLC start. Poll pacing (15 µs) unaffected —
  §40 succeeded with it in place.

**Tooling:** no deployable register-level SI simulator exists (researched 2026-07-02:
Multi2Sim ISA-only/dead, gem5 GPUFS gfx9+/behavioral CP, AMD's RTL model internal).
The kernel tree (`/home/bob/linux`) + traces + replay harness ARE the substitute.

## 4. TEST PROTOCOL (one cold boot must answer every armed thread)

Rebuild: `cd ~/Ailang-Self-Hosting- && ./ailang.x TestCode/test_replay_init.ailang test_replay_init`
(§43 binary built 2026-07-03 13:41 — §40 de-pace + §41 RPTR readouts + §42
tracer/resample + §43 anchor readbacks all in. Startup banner must show
`[§43] anchors armed: 4 context-reg readbacks` — missing = stale binary.)

Log naming: one `replay_mmiotrace_sNN.txt` per section; the runner creates
`replay_mmiotrace.txt` fresh — mv it to `_sNN.txt` after each run. Current set:
`_s34 _s35 _s37 _s39 _s40 _s41 _s42` + `_s37s39_combined` (raw appended file, kept).
NOTE 2026-07-03 00:16: the §40 log was briefly mis-mv'd onto `_s37.txt`;
fixed — `_s40.txt` is the §40 run, `_s37.txt` re-extracted from the combined
file (lines 1–22308; verified: old signature got=0x6, no §39/§40 markers).

Run (from SSH; screen survives freezes):
```
sudo ./test_replay_init 2>&1 | while IFS= read -r l; do printf '%s\n' "$l"; printf '%s\n' "$l" >> replay_mmiotrace.txt; sync replay_mmiotrace.txt; done
```
- Cold reboot first; service stays disabled; nothing touches bus 2 before the run.
- Harness HARD-ABORTS on a posted card (CONFIG_MEMSIZE must read 0). An abort means
  the boot wasn't cold — reboot; do not work around the guard.
- §40 markers: `[§40] de-pace armed: A2 window seq 12088-439996` in the startup
  banner (prints even on a guard abort — missing = stale binary), then
  `[§40] de-pace ON` right after the A2 banner and `[§40] de-pace OFF (table end)`
  before the verdict. §39's `[§39] MSI mirrored` line stays (now baseline).
- §41 readouts (now baseline): four `[§41]` lines right before the verdict —
  RB0/1/2 `RPTR=… WPTR=…` + `CP_ME_CNTL/GRBM_STATUS`. WPTR should read
  0x600/0x100/0x100; §41 answered the RPTR question (moved — see §1).
- §42 readouts (now baseline): `[§42] SCRATCH_REG1 baseline=` (pre-A2), three
  `[§42] RPTR sample N` lines (1 s apart), and `[§42] SCRATCH_REG1=` —
  0x420000NN = last executed station (map in §2.1). §42 ran 2026-07-03 13:23:
  0x0, frozen — see §1. The ring test sits at dw 0x500 in the traced layout.
- §43 readouts: `[§43] anchor baseline 0x28230=… 0x28810=… 0x28BDC=… 0x28C58=…`
  (pre-A2), then at the verdict four `[§43] anchor … want=…` lines,
  `[§43] GRBM_STATUS resample=`, and the computed `anchors matching stream:
  N/4` call (N>0 ⇒ H2; 0/4 ⇒ leans H1 — cross-check baselines). Anchor values
  in §2.1. mv the log to `_s43.txt`.
- Readouts: RLC_STAT poll seq 333505 (0x7 = the lead moves) + SCRATCH_REG0 lines.
  A2 runs in seconds with NO per-write MMIO_WR lines (deliberate — logging
  re-paces writes); breadcrumbs/MIS/POLL lines still print.
  Afterward check dmesg for a stray vector-0x22/CPU5 report (bounded, expected
  harmless; the §39 run's check is still pending — needs sudo).
- Freeze localization: last `[§30-AT]` breadcrumb (every 100 records) → look the seq
  range up in `fw_trace/FULL_REPLAY_A1/2.txt` BEFORE any new theory.

dst=42 remains the endgame metric (separate dispatch test after replay-init succeeds).

## 5. KEY ASSETS

- `fw_trace/` — extractors + replay tables (.bin regenerable from .txt/scripts; gitignored).
  FULL_REPLAY_A1/A2, DPM_REPLAY_*, TRACE_VERDE_* (trace-exact fw), extract_rlc_content.py
  (SR/CSB/RB0 blobs), extract_fbbar.py (§36), scan_atom_io.py, KERNEL_SR_CSB.bin.
- `bus2_all.txt` — seq-only kernel mmiotrace of the working radeon cold init (Jun 19). The oracle.
- `mmiotrace_boot/mmiotrace_raw.log` — 61 MB timestamped amdgpu cold init (Jul 2 16:56,
  working bringup; full FB BAR = map id 9). Candidate future replay source.
- `pci_working_boot/` — §38 working-boot PCI reference: root port/GPU/audio config
  (prebind + working + postunbind), live MSI values, dmesg, /proc/interrupts.
  `capture_working_pci.sh` + `finish_capture_working_pci.sh` regenerate it.
- `/home/bob/linux/drivers/gpu/drm/amd/amdgpu/` — gfx_v6_0.c, clearstate_si.h, si.c:
  the reference model for anything the trace can't show.
- `Library.AMDGPUReplay.ailang` + `TestCode/test_replay_init.ailang` — the harness
  (1 ms write pacing, 15 µs poll pacing, breadcrumbs, cold guard, computed verdict,
  §39 GPU_BAR_EnableMSI in Library.AMDGPUBAR.ailang).
- Logs: `replay_mmiotrace_s34/_s35/_s37/_s39/_s40.txt` (naming notes in §4),
  `vram_readback_s35.txt` (+ `test_vram_readback` tool).
- Layout/VRAM/GART constants: gpu-crash.md; kernel-VA GART map archive §30
  (WB 0xFF00401000, IH 0xFF00609000, RB0/1/2 0xFF00619000/1D/1F).
- `vbios_bus2.rom` — bus 2 VBIOS dump (Jul 2 22:08).
- Old dispatch-path test: `test_accel_gcn` — superseded; only rerun when a section says so.

## 6. HISTORY

Jun 16–22: bringup + crashes + GART relocation (gpu-crash.md). Jun 19: working radeon
trace. Jul 1–2: seventeen "cold" iterations on contaminated boots (archive §8–§29);
method change to verbatim replay + oracles (§30), contamination found (§32), first true
cold test (§33), then §34–§39: every captured channel closed one by one — BAR0, memory
content, config space, root port, MSI. Jul 3 §40: de-paced A2 → **RLC starts (0x7
first read); pacing was the RLC blocker**; rings/ME still dead. Jul 3 §41: ring
reconstruction offline-verified clean, then cold run → **RPTR moved on all 3 rings —
CP→GART fetch works**. Jul 3 §42: 13-station scratch tracer cold run → **ZERO
stations executed, RPTR hard-frozen, fetch ran to full WPTR** (§41's dw-208
localization was fetch-position, voided) + first-ever GRBM_STATUS deviation
(IA|SPI|PA busy) → fork: H1 ME-executes-nothing vs H2 ME-executes-but-register-
writes-never-land → §43 = context-reg readback discriminator. Archives:
7cf8eec2 (§8–§33), 1f7ce115 (§34–§39).

**Update this doc after every run: move findings to §3 when killed, keep §2 to the live few.**
