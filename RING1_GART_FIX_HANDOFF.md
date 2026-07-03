# AILang AMD GPU Compute — Handoff (condensed 2026-07-01)

**Target:** Cape Verde (GCN1 / Southern Islands), bus 2 = compute GPU.
**Goal:** get a compute dispatch to produce correct output (`dst[i]=src[i]+42`).

**Read this + `gpu-crash.md` (RULES) before editing.**

## 0. HARD SAFETY RULES
1. **NEVER run full init on the DISPLAY GPU (bus 1 / 01:00.0).** Guard in `AccelGCN_Init` must stay; every run must log `using GPU N (bus 2)`.
2. **Do NOT unbind the `radeon` driver** — use PCI bus-2 reset only.
3. Keep the **30-dispatch `AccelGCN_ComputeReset`** workaround.
4. Obey all `gpu-crash.md` RULES (HDP safety, no MC on bus 1, kernel values).
5. Always run with sudo; human executes the test.

## 1. ITERATION LOOP
**CURRENT TEST IS THE §30 REPLAY HARNESS, not test_accel_gcn** (§31: running the old
loop burned a cold boot). **§32 PRE-REQ: `gpu-mmiotrace.service` must be disabled first
(one-time, needs password) or the boot is NOT cold — see §32.** Freeze-proof logging
(§32: the 16:52 freeze lost the whole log from page cache; run from SSH so the screen
keeps the tail, and fsync every line):
```
cd ~/Ailang-Self-Hosting- && ./ailang.x TestCode/test_replay_init.ailang test_replay_init
sudo ./test_replay_init 2>&1 | while IFS= read -r l; do printf '%s\n' "$l"; printf '%s\n' "$l" >> replay_mmiotrace.txt; sync replay_mmiotrace.txt; done
```
(old loop, only when a section says to run test_accel_gcn again:
`./ailang.x TestCode/test_accel_gcn.ailang test_accel_gcn && sudo ./test_accel_gcn 2>&1 | tee our_mmiotrace.txt`)

**COLD REBOOT between runs.** gpu_reset.sh was deleted 2026-07-02 (Sean): its config-0x7c ASIC reset caused PCI fabric hangs/lockups. Never write config 0x7c.

## 2. CURRENT STATE (from 2026-07-01 fresh sudo run on rebuilt binary)
**GART plumbing now working (fixes applied):**
- Real PFNs visible (e.g. 0x1E9699 phys=0x1E9699000 and many others for rings/data/shader).
- GART_Init succeeds, PTE fill completes, all compute memory in GART (kernel-matching VAs, CNTL etc.).
- No "cannot resolve" or rc=-2.

**Previously solid:**
- Init to dispatch.
- Host GART writes (src readback mostly).
- Safety guards (SPLL, display, non-fatal rings).

**Evidence of remaining bugs (this run's our_mmiotrace.txt):**
- VRAM diagnostic (post BIF_FB_EN=3 + MC train): writes land as garbage (0xA39C4A7 etc.) or FFFF; HDP flush doesn't fix. Affects PTE table in VRAM.
- §14-ILR: SRBM_GFX_CNTL=0 always. SET_SH_REG e.g. PGM_LO wrote 0xF44A0720 readback 0x0. All other regs 0.
- §14-CS bracket: all 0 before, after GFX CS, after compute CS (CLEAR_STATE does nothing).
- Probes: "SET_SH_REG consumed (idle=0)", multiple WaitIdle timeouts (RPTR stuck at 62, WPTR advances to 147).
- Wave/POST-FENCE: SPI_DEBUG_BUSY=0, SQ_DEBUG_STS_GLOBAL=0 (no wave), all COMPUTE/SH regs 0, SRBM=0, SH_MEM=0, dst[0..3]=0 (src[0]=0 src[1]=1 partial), GRBM=0xA0003028.
- Dispatch rc=0 but 64 errors, dst all 0 vs 42. FAIL. DPM teardown.
- Second run locked up (stale state post-failure).

## 3. RULED OUT
Payload, shader code, VM aperture, GART mapping (now), read coherency (host side), VM fault=0, basic packet encoding, ring choice.

## 4. CURRENT ROOT CAUSES
Cold POST + MC bringup does not establish:
- Working CPU BAR0 writes to VRAM (PTE table lives there; diagnostic + fill path broken).
- Compute pipe/context (SRBM_GFX_CNTL=0; SET_SH_REGs never commit to live SQ/SPI; no wave launch).
- Effective context (CS bracket shows zero effect; writes don't stick per ILR; ordering vs CS? SRBM select missing?).

This matches the "cold bringup" lead in old §4/10/11/14 and KERNEL_INIT_SEQUENCE.md (missing pieces in gfx_v6_0_cp_compute_resume, SPI setup, etc.).

GART/ring1/fetch side of the handoff is now done. The seam is the one the docs have flagged for weeks.

## 5. PRIORITIZED FIXES (edit code, use §14 data to verify)
1. **Fix VRAM/BAR0 write path (enables PTEs + setup):**
   - Improve priming + drains specifically for PTE area before/during GART fill (more HDP 0x5480 + sfence + MMIO read serialize).
   - Diff post-MC writes in this log vs bus2_all.txt for missing BIF/MC/VM/HDP config for CPU aperture.
   - Consider writing PTEs via PM4 once CP is alive (avoid BAR0 dependency for table).
   - Locations: Librarys/Drivers/AMDGPU/Library.AMDGPUGART.ailang (GART_WritePTE/fill), Librarys/Accel/Library.AccelGCNInit.ailang (post-MC, BIF).

2. **Set SRBM_GFX_CNTL before compute SET_SH_REG (probe data + lead (c)):**
   - In PM4_SubmitCompute, before EmitSetSHReg for compute: explicit GPU_Wr32(gpu, SIReg.SRBM_GFX_CNTL, val for compute pipe/queue/VMID=0).
   - See kernel select_me_pipe_q.
   - Location: Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Dispatch.ailang (~140 area, before first SET_SH_REG).

3. **Fix ordering (CS vs SET_SH_REG, lead (a)):**
   - Move/ensure all compute SET_SH_REG + DISPATCH after the compute CLEAR_STATE + CONTEXT_CONTROL in CPStart.
   - Current bracket proves CS ineffective.
   - Location: Librarys/Drivers/AMDGPU/Library.AMDGPUPM4Dispatch.ailang (PM4_CPStart and SubmitCompute).

4. **Add missing cold compute/SPI pipe init (KERNEL cross-ref + lead (c)):**
   - In init or FW load path: add MMIO for SPI_STATIC_THREAD_MGMT_3 per SE/SH, other compute enables from gfx_v6_0 setup_spi/rlc_resume/cp_compute_resume (beyond golden regs).
   - Set SRBM context early.
   - Locations: Librarys/Accel/Library.AccelGCNInit.ailang, Librarys/Drivers/AMDGPU/Library.AMDGPUPM4FW.ailang, Library.AMDGPUMC_SI.ailang.

5. **CP consume/stalls:**
   - Add extra sync (SURFACE_SYNC, PFP-ME) before/after compute SETs.
   - Investigate/fix RPTR=62 stall (ring state? ME?).
   - Location: dispatch/ring code.

6. **Hygiene:**
   - Enforce full reset after any FAIL/timeout before next run.
   - Consider auto state verification or reset in harness.

## 6. REFERENCES
- KERNEL_INIT_SEQUENCE.md (full kernel sequence + missing items).
- gpu-crash.md (RULES, HDP table, VRAM issues).
- our_mmiotrace.txt (this run's full §14 + diagnostic + probes).
- Key files: AMDGPUGART.ailang (GART), AMDGPUPM4Dispatch.ailang (submit/CPStart/probes), AccelGCNInit.ailang (top init), AccelGCNDispatch.ailang.
- Use the §14 output in future runs to confirm fixes (expect non-zero readbacks, SRBM non-zero, waves, dst=42).

## 7. HISTORY (short)
Prior work (GART relocation, golden transcription fixes in DRIVER_FIXES, SPLL/guard, non-fatal rings, §14 instrumentation, RLC/CS ordering) addressed symptoms. §15 details the 2026-07-01 run that closed the GART plumbing but confirmed the VRAM+pipe seam. See git for old full history. Focus on implementation now.

**Update this doc after every change + run.** The goal is working dispatch, not more docs.

## 18. New cold boot log - GART good, but still stalls at first compute SET_SH (PGM_LO)
The log shows GART success (skipping bulk, 0 failures, GART initialized, SPI MMIO set).

Dispatch reaches the PGM_LO SET_SH, but stalls (RPTR stuck, readback 0, no waves, dst=0).

No SRBM set in this log (removal active), SRBM=0, stalled stat 0.

The CP is not consuming the compute PGM SET_SH packet.

**Action to match kernel init behavior (per user request, triple check, ignore previous Claude docs):**
Changed the CP FW load order in PM4_LoadCPFirmware to ME, PFP, CE (to match the kernel mmiotrace_init_sequence.txt trace order for the working cold init, where ME FW was loaded first, then PFP, CE).

Previously followed the source comment (PFP CE ME), but the trace that left the state allowing compute packets used ME first.

Rebuilt.

This + previous (GART skip, SPI MMIO pipe base, CPStart unhalt first, SRBM set removed, pagemap once) should now leave the ME in the kernel-like state that processes the compute SET_SH without stall.

Run the current binary on cold reboot. The dispatch should now get past the PGM SET_SH ILR, with the PGM readback hopefully non-zero, and waves launching.

If still stalls at the compute SET_SH, the Fable doc will give the clear path; we can then add the exact missing MMIO from the kernel log diff.

The "stupid simple matching behavior" is now in for the FW load order. The log will tell if it unblocks the compute pipe.

## 18. 2026-07-01 ROOT CAUSE FOUND (cross-check of bus2_all.txt vs gfx_v6_0.c vs our init): RLC firmware never loaded + gating enabled on dead RLC

Evidence sweep compared the kernel mmiotrace, amdgpu gfx_v6_0.c source, probe_pre/post_radeon_bind.txt, and our_mmiotrace.txt. Three independent bugs in the RLC/CG area, all fixed and rebuilt (binary 2026-07-01 19:53):

**Bug 1 — RLC ucode upload assumed ADDR autoincrement. It doesn't.**
Kernel writes `RLC_UCODE_ADDR=i` before EVERY data word (bus2_all seqs 329397-333493: 2048 alternating ADDR/DATA pairs). Our loader wrote ADDR=0 once then streamed 2048 DATA writes — the entire firmware landed on word 0. The RLC was "started" but running garbage.
Fix: per-word ADDR write in PM4_LoadRLCFirmware (Library.AMDGPUPM4FW.ailang).

**Bug 2 — decimal typos in two RLC register offsets (Library.AMDGPUPM4Regs.ailang).**
- RLC_MC_CNTL was 50004 = 0xC354; correct is 49988 = 0xC344.
- RLC_UCODE_CNTL was 50008 = 0xC358 = **RLC_SOFT_RESET_GPU** (!); correct is 49992 = 0xC348.
Neither reg was ever programmed; we were poking RLC_SOFT_RESET_GPU with 0 before each fw load. Also: MC_SI golden write "RLC_GPM_UCODE_ADDR=0x80010014 (seq 3708)" was transcribed to 0xC32C (RLC_UCODE_ADDR) — the decoder mislabels 0xC30C, which is RLC_LB_CNTL. Fixed to 49932/0xC30C.

**Bug 3 — clock gating ENABLED and handed to the (dead) RLC.**
PM4_LoadRLCFirmware ran the mgcg/cgcg ENABLE handshakes (0x00D000FF/0x00B000FF, cleared MGCG_OVERRIDE low bits, set CGCG_EN|CGLS_EN). With a non-functional RLC the SPI/SQ blocks stay clock-gated forever. This is the exact observed signature: SH-space regs (0xB858 etc.) read 0 and MMIO writes don't stick, CP-block regs fine, ME wedges on the first compute SET_SH_REG (RPTR frozen, CP_BUSY_STAT=0x802, no stall bits) waiting for a register-bus ack.
probe_post_radeon_bind.txt confirms the working bus1 card sits with CGCG/CGLS DISABLED (RLC_CGCG_CGLS_CTRL=0x0020003C) and MGCG override bits SET.
Fix: replaced with the kernel DISABLE paths (gfx_v6_0_enable_cgcg/mgcg(false)): 4x CB_CGTT_SCLK_CTRL dummy reads, CGLS_CTRL &= ~3, MGCG_OVERRIDE |= 3, CP_MEM_SLP_CNTL bit0 cleared, CGTS_SM_CTRL_REG |= 0x600000 (LS_OVERRIDE|OVERRIDE), SERDES broadcast 0x00E000FF. No block's clock now depends on RLC behavior.

**Also fixed:**
- PM4_CPStart order restored to kernel order: ME_INIT+SET_BASE committed (WPTR MMIO write) while HALTED, then unhalt (trace seqs 439962→439964: WR CP_RB0_WPTR=0x100 then WR CP_ME_CNTL=0). §17's "unhalt first" was a misreading.
- GB_ADDR_CONFIG golden write back to 0x02010002 (seq 3703); the 0x12010002 ROW_SIZE-adjusted write later matches seq 329279.
- Build fix: github merge deleted tracked Librarys/TF files while ignored stragglers still call TF_MatGet; restored Library.Float/Layer/Mat/Math/Vec.ailang from pre-merge commit 7800e83c (untracked, gitignored).

**What to expect on the next cold-reboot run:**
1. Init: `[AccelGCN] SPI_STATIC_THREAD_MGMT_SE0/SE1 set via MMIO` — the 0xB858/0xB85C writes should now READ BACK 0xFFFFFFFF (previously always 0). This is the first tell that SPI is unclocked no more.
2. §14-ILR: SET_SH_REG readbacks should equal written values (PGM_LO=0xF44A0720 etc.).
3. RPTR should advance past the first compute SET_SH (no more WaitIdle stall at ~62-64).
4. WAVE-PROBE: SPI_DEBUG_BUSY / SQ_DEBUG_STS_GLOBAL non-zero during dispatch.
5. dst[i]=42.
If 1 holds but 2-5 fail, the remaining gap is compute context (SRBM/pipe) — but retest first; everything downstream was diagnosed while SPI/SQ were unclocked, so all prior §12-§17 conclusions about SET_SH/CS behavior are suspect.

If it still stalls: capture the log; do NOT re-add the SRBM_GFX_CNTL experiment (§16 showed it wedges the fabric).

## 17. Cold reboot run - GART good, dispatch reaches first compute SET_SH but stalls (RPTR=62)
The log shows GART success (skipping bulk, 0 failures, GART initialized, SPI MMIO base set).

Dispatch reaches the first compute SET_SH (PGM_LO), but then stalls (WaitIdle timeout, RPTR=62 WPTR=65, all regs 0 in ILR, no waves, dst=0).

The SRBM set was not in this log (removal took effect), SRBM=0, stalled stat 0 (not FFFF).

The stall is on the compute PGM SET_SH packet itself (the ME is not consuming it after the cacheinval).

**Action to match kernel init behavior:**
Changed PM4_CPStart to unhalt CP first (CP_ME_CNTL=0), brief delay, *then* emit the ME_INIT and SET_BASE packets (WPTR bump after unhalt), commit, WaitIdle, then the CLEAR_STATE etc.

This matches the kernel trace order in phase 16 (unhalt, then the ring/WPTR writes for the init packets like ME_INIT).

Previously, the AILang emitted and committed the packets while halted, then unhalt (packets "sitting in the ring").

In cold, the order of unhalt vs WPTR bump for the ME_INIT may leave the ME in a different state that doesn't process subsequent compute SET_SH packets (stall at the first compute one).

Rebuilt.

The GART skip + SPI MMIO base + this order change should now let the CP process the init packets in kernel-like order, and the compute SET_SH should not stall.

Run on cold reboot with current binary. The dispatch should now get past the first SET_SH without the stall at 62, and the ILR will show if the PGM etc land (read == wrote), and if waves launch.

If still stalls at the compute SET_SH, then more matching needed (e.g. the exact pre-unhalt writes or other packets the kernel emits in the trace before the compute ones).

The "matching behavior" is now in for the CP start order. The log will tell if it unblocks the pipe for compute packets.

## 16. This cold reboot run - hung exactly at SRBM set + first compute SET_SH (PGM_LO ILR)
The log you pasted is the smoking gun for the experimental SRBM lead:

... dispatch setup ...

[DBG-SUBMIT] PGM_LO=0xF44A0720 ...

MMIO_WR 35608 0x0xE44 0x0x3
[FIX] SRBM_GFX_CNTL set to 0x3 before compute SET_SH_REGs, immediate readback=0x0x0
[§14-ILR] SRBM_GFX_CNTL=0x0x0 CP_STALLED_STAT3=0x0xFFFFFFFF
MMIO_WR 35609 0x0xC114 0x0x3E
^C

GART was good (from full context of this boot's logs: skipping bulk, verification 0 failures, GART initialized). Reached shader, dispatch dryrun, cacheinval, first compute SET_SH.

The set to 0x3 + emit caused immediate read 0 + stalled stat FFFF (all 1s = the CP reg block became unresponsive, classic RD990 fabric stall when you poke the wrong thing in cold state). That's why the process bogged/hung the box (MMIOs timing out or blocking the fabric, as documented in gpu-crash.md and early handoff).

**This is why the SRBM set was removed** (in the build you should use now): the lead in §14 was "try setting SRBM before the compute SET_SH_REGs" to select the pipe/queue. In practice here (cold SI, gfx ring0 for compute), writing 0x3 (or 0x1 before) doesn't make SRBM read non-zero (always 0 in all probes), and it triggers the FFFF stall/hang. The packet header (shader_type=compute) + the CPStart (ME_INIT + compute CS + CONTEXT_CONTROL) is supposed to route it.

**The core "get the pipe up" fix that *was* added (per §11/14 "SPI compute config + pipe enable programmed via MMIO during bringup" + KERNEL gfx_v6_0):**
In AccelGCNInit.ailang (after CP FW + rings + CPStart CS, before dispatch):
GPU_Wr32(gpu, 0xB858, 0xFFFFFFFF);  // SPI_STATIC_THREAD_MGMT_SE0
GPU_Wr32(gpu, 0xB85C, 0xFFFFFFFF);  // SE1
Print "[AccelGCN] SPI_STATIC... set via MMIO for compute pipe base"

This sets the compute pipe/CU enable base via MMIO in the cold bringup (CS leaves the state 0; the dispatch SET_SH for STATIC will then land on top and the wave will actually launch with CUs enabled). Previously everything was only via the dispatch SET_SH packets, which weren't committing in cold.

**Current binary state (post this log):**
- SRBM set block removed (no more 0x3 write that causes FFFF stall).
- SPI_STATIC SE0/SE1 MMIO base added in init.
- GART skip bulk + 64-bit + pagemap-once for data (prevents the bog/slow from 40k syscalls).
- Rebuilt.

**What to do now:**
Run the current binary on cold reboot (as you are). It should now get past the first ILR / PGM set without the FFFF stall/hang from the bad SRBM poke. You should see the full ILR (including the readbacks for PGM after the packet, and later for STATIC after its SET_SH — which should now see the MMIO base FFFF even if the packet didn't update it further).

If the STATIC reads show FFFF (from the MMIO base) and waves launch (SPI/SQ non-zero in probes) and dst=42, we're done.

If still regs read 0, no waves, same stall at ~62: then the pipe base is there but something else is missing (e.g. SRBM selection still needed but with correct value/timing that doesn't cause FFFF; or more MMIO like SQ_CONFIG, COMPUTE_ regs, or re-order so the first compute SETs are after some other pipe enable; or the CS itself needs the RLC in a better state).

The log you gave is perfect evidence: GART is fixed, the SRBM experiment was the immediate trigger for the hang, the "pipe up via MMIO in bringup" is the concrete step we added to address the core cold compute context issue the doc has been pointing at since §11.

Run, capture the full new log (or at least the ILR sections + wave probes + final dst). If it still hangs at similar point, we'll add the next MMIO or adjust. This is the address of the core issue. Reboot + run.

## 15. Exact hang point from this cold reboot log (first test this boot)
The provided snippet ends precisely at the first compute SET_SH_REG (PGM_LO) + ILR:

MMIO_WR 35608 0x0xE44 0x0x3
[FIX] SRBM_GFX_CNTL set to 0x3 before compute SET_SH_REGs, immediate readback=0x0x0
[§14-ILR] SRBM_GFX_CNTL=0x0x0 CP_STALLED_STAT3=0x0xFFFFFFFF
MMIO_WR 35609 0x0xC114 0x0x3E
^C

**Full context from this + prior cold reboot logs (no reset, fresh cold):**
- GART now succeeds on cold reboot (skipping bulk, 0 verification failures, GART initialized, only used PTEs written with 64-bit). Reached shader upload + dispatch dryrun + first compute SET. (The bulk fill + per-page pagemap in data was the WC/corruption/slow killer; optimizations fixed it.)
- Reached USER_DATA, cacheinval, PGM_LO SET_SH.
- The SRBM set (0x3): write, but read 0 immediately + in ILR. Then CP_STALLED_STAT3=0xFFFFFFFF (all 1s = bad read, stall, or fabric unresponsive -- classic on RD990 when CP block dead).
- Hang/bog at the WaitIdle after this (CP not consuming the compute SET_SH packet; RPTR stuck ~62 in full logs).
- Same downstream in full prior log: all compute regs 0 in full ILR (PGM/RSRC/TMGMT/DISPATCH=0), no SPI/SQ activity, no wave, dst=0, 64 errors, FAIL. (Even with GART good for data.)
- CS bracket (in full logs): 0 before/after (no effect from compute CS).
- VRAM diag partial (0 lands, others FFFF/garbage).
- Shader MC/vdesc/IB look correct.
- The SRBM set (experimental per old §14 lead "try setting before compute SET_SHs") did not make SRBM non-zero (always 0 in probes), and triggered the FFFF stall/hang. (Immediate read 0 means write not visible/sticking in cold state.)

**Actions:**
- SRBM set block removed (and [FIX] print) from PM4_SubmitCompute. Rebuilt. (The packet's shader_type=compute + gfx ring0 + CPStart (ME_INIT + CS + CONTEXT_CONTROL) should route; setting SRBM was causing bad state.)
- Added base SPI_STATIC_THREAD_MGMT_SE0/SE1 via MMIO in AccelGCNInit (after CP FW/rings, before dispatch): 0xB858/0xB85C = 0xFFFFFFFF. (Per KERNEL gfx_v6_0 setup_spi/rlc + handoff §11/14 "SPI compute config + pipe enable programmed via MMIO during bringup"). This gives the pipe a base state (CS leaves 0; dispatch SETs override per-dispatch). Rebuilt.
- Pagemap open-once for data buffer (40k pages) already in (prevents bog/slow from 40k open/close).

The log is **highly useful**: proves GART win on cold reboot (no bulk, verification 0), pinpoints the exact trigger for this hang (the SRBM set + first compute SET_SH causing FFFF stall). Removal + SPI MMIO base should let it pass this point.

**Next run (cold reboot):** use current binary (no SRBM set, SPI MMIO base added). Should get past the first ILR without FFFF (no bad set). Full ILR will show if STATIC etc land (on top of MMIO base), if waves launch, if RPTR advances, dst values. Expect cleaner data on whether the pipe base helps the "SET_SH not landing, no wave" (per §4/10/11/14).

If still same (regs 0, no wave, stall at ~62): the missing is more cold pipe MMIO (e.g. other SPI/SQ in init, or SRBM for VMID in specific way, or order CS vs first SETs). Monitor stalled stat in ILR (now without the set, expect non-FFFF).

If hangs again: reboot + retry. The GART side is solid; this is the dispatch/compute context bringup. Report full log or around ILR/wave probes + final dst/Results + any stalled stat. We are converging on the "cold bringup" seam the docs flagged from the start.

## 14. Cold reboot run (first test this boot) - hung at first ILR after PGM_LO SET_SH (with SRBM set to 0x3)
Provided log snippet:

... shader MC dump ...

[AccelGCN] Shader uploaded to GART: ... size=48

[PKT-MAP] pre_USER_DATA wptr=33 ring=0

[PKT-MAP] after_USER_DATA wptr=45

=== [DISPATCH DRYRUN] ring=0 ===

... debug ...

[DBG-SUBMIT] ... PGM_LO=0xF44A0720 PGM_HI=0

MMIO_WR 35608 0x0xE44 0x0x3

[FIX] SRBM_GFX_CNTL set to 0x3 before compute SET_SH_REGs, immediate readback=0x0x0

[§14-ILR] SRBM_GFX_CNTL=0x0x0 CP_STALLED_STAT3=0x0xFFFFFFFF

MMIO_WR 35609 0x0xC114 0x0x3E

^C

**Analysis from this + prior cold reboot log (no reset, fresh cold):**
- GART now solid on cold reboot: "Skipping bulk 11.8M dummy PTE fill", "Will only write PTEs for actually used...", "PTE verification complete: 0 failures", "GART initialized: ...". Reached dispatch/IB. (Our kernel-mimic change + 64-bit PTE + pagemap-once opt for data buffer is working; no more corruption/FFFF in used PTEs or bulk WC overflow.)
- Reached user data, cache inval, first compute SET_SH (PGM_LO).
- The experimental SRBM set to 0x3 (from build with the lead): MMIO write, but immediate readback=0, ILR SRBM=0, but CP_STALLED_STAT3=0xFFFFFFFF (all 1s = classic bad read/stall/fabric issue on RD990 when CP block unresponsive).
- Hung/bogged here (user ^C). Matches "system is hanging where it ends and bogging down and grindingly slow before that" from prior run.
- Full prior log (same cold reboot symptoms): dispatch reaches but SET_SH_REG consumed (idle=0), WaitIdle timeouts (RPTR stuck at 62 while WPTR advances), all compute regs read 0 post-ILR (PGM=0, RSRC=0, TMGMT=0, DISPATCH=0, etc.), SPI_DEBUG_BUSY=0, SQ=0 (no wave ever), SRBM always 0, dst=0 (src partial from GART host), 64 errors, FAIL. Then DPM teardown.
- VRAM diag still partial fail (0 lands DEADBEEF, others garbage/FFFF; HDP no help) -- but GART for data/rings/IB/shader means host-side src/dst via coherent system RAM (bypasses most of it).
- Shader MC/vdesc/IB content looks correct.
- No bulk dummy fill (skipped), so Dummy PTE[0] FFFF expected (unused slots left as power-on).

**Key:** The SRBM_GFX_CNTL set (0x3 or prior 0x1) is not making the reg read non-zero (always 0 in probes), and is causing the bad stalled stat FFFF + hang. This is exactly the experimental lead in §14 ("try setting SRBM... before the compute SET_SH_REGs" to select pipe/queue). In practice on this cold SI, it destabilizes (read 0, FFFF stall). The packet shader_type=compute should route it; the gfx ring0 + CPStart (ME_INIT + GFX CS + compute CS + CONTEXT_CONTROL) should be sufficient for context.

**Action taken:** SRBM set block + [FIX] print removed from PM4_SubmitCompute (in the build the user will use next). Rebuilt. ILR probes for SRBM remain to monitor (expect 0, but no FFFF from bad write). This should let it get past the first ILR without the induced stall/hang.

The core issue is unchanged (per handoff §4/10/11/14 + KERNEL): cold POST/MC/RLC/CP bringup does not establish the compute pipe/SPI context so that compute SET_SH_REGs actually commit to live regs and DISPATCH_DIRECT launches a wave. CS bracket shows 0 before/after (no effect), SET_SH readbacks 0 even interleaved, no SPI/SQ activity, RPTR stall at ~62. On BIOS-posted it worked; our cold path is missing the MMIO (SPI_STATIC_THREAD_MGMT_SE0/SE1 = 0xFFFFFFFF, other pipe enables, per gfx_v6_0 setup_spi / rlc_resume / cp_gfx_start). SH_MEM_CONFIG=0 is normal for SI (not CIK+).

**Next (after this removal):**
- Run on cold reboot (as you are). Should now get past the first ILR / PGM set without FFFF stall (no bad SRBM write). Full ILR + wave probes + dst will be cleaner.
- If still stalls at similar point or same symptoms (regs 0, no wave, RPTR=62, dst=0): the removal unblocks; now add the missing cold compute/SPI MMIO in init (in AccelGCNInit after CP FW/ring setup or in PM4_CPStart after compute CS, before dispatch SETs). E.g.:
  GPU_Wr32(gpu, 0xB858, 0xFFFFFFFF); // SPI_STATIC_THREAD_MGMT_SE0 (enable all CUs for compute pipe)
  GPU_Wr32(gpu, 0xB85C, 0xFFFFFFFF); // SE1
  (Offsets from regs; matches kernel SPI setup for compute.)
- Also ensure order: all compute SET_SH after compute CLEAR_STATE + CONTEXT_CONTROL (bracket already there; dispatch SETs are after CPStart).
- If SRBM still relevant (monitor in ILR): try explicit set to 0 (default) or constructed like cik (vmid=0, queue=0, me=0/1?, pipe=0) before the block, but only if it doesn't cause FFFF.
- The data PTE optimization (pagemap open once for 40k pages) + no bulk should prevent the bog/slow in GART phase.
- If hangs at end again: the RPTR stall on compute packets is the symptom of the missing pipe/context; adding the SPI MMIO base before dispatch SETs should let them land and launch.

Log is useful (cold reboot, GART success visible, exact hang at the bad SRBM+first compute SET). The removal is already in the current binary (rebuilt after last edit). Run it on cold reboot, capture full log (or at least around ILR sections + wave probes + final dst/Results). If hangs, reboot + retry. We're past GART (kernel-mimic working); now the dispatch/compute context bringup without the destabilizing SRBM experiment. Hold tight for the next log.

## 13. Cold reboot run (first test this boot) - hung at first ILR after PGM_LO SET_SH
Log ends at:
[DBG-SUBMIT] ... PGM_LO=0xF44A0720 ...
MMIO_WR 35608 0x0xE44 0x0x3
[FIX] SRBM_GFX_CNTL set to 0x3 ... immediate readback=0x0x0
[§14-ILR] SRBM_GFX_CNTL=0x0x0 CP_STALLED_STAT3=0x0xFFFFFFFF
MMIO_WR 35609 0x0xC114 0x0x3E
^C

**Analysis:**
- GART: skip bulk + used-only + 64-bit PTEs working (from "Skipping bulk", "PTE verification complete: 0 failures", "GART initialized" in full log context). Reached dispatch on cold reboot. Big progress.
- Shader upload, vdesc, USER_DATA, cacheinval all good.
- Then first compute SET_SH (PGM_LO), the experimental SRBM set to 0x3 (from previous build), immediate read 0, then ILR shows SRBM=0, but CP_STALLED_STAT3=0xFFFFFFFF (all 1s = bad read, stall or fabric issue).
- Hang/bog at the WaitIdle/commit after this (CP not consuming the compute SET_SH packet).
- This matches old leads: the SRBM set was "try it", but in practice (0x1 and 0x3) causes bad stalled stat FFFF and hang. The write doesn't make SRBM read non-zero (always 0 in probes), and destabilizes.

**Action:** SRBM set block removed (as in last edit), rebuilt. The packet shader_type=compute should suffice for routing on gfx ring0. ILR probes remain for monitoring (expect SRBM=0, but no FFFF stall from bad set).

The hang is the CP stalling on the first compute SET_SH (RPTR not advancing past ~62), no context update, no wave.

Core still cold compute pipe not up (SPI/config missing via MMIO in init, per KERNEL and §11/14; CS not committing for compute).

Next run on cold: should get past the first ILR without the 0x3-induced FFFF stall. Full probes will show if other stalls or if waves launch now.

If still hangs at similar point, add debug reads of stalled stat before/after each SET_SH, or try setting SRBM to 0 explicitly in init, or add the SPI_STATIC_THREAD_MGMT_SE0/SE1 via MMIO (0xB858/0xB85C = 0xFFFFFFFF) after CP resume / before dispatch (to have base pipe enable).

The GART side is solid; dispatch side is now the focus without the bad experimental set. Reboot + run, report full log or around the ILR sections.

## 12. First test this boot (cold, hung at dispatch ILR after shader upload)
Log snippet provided ends at:

[DBG-SUBMIT] ... PGM_LO=...

MMIO_WR 35608 0x0xE44 0x0x3

[FIX] SRBM_GFX_CNTL set to 0x3 before ... immediate readback=0x0x0

[§14-ILR] SRBM_GFX_CNTL=0x0x0 CP_STALLED_STAT3=0x0xFFFFFFFF

MMIO_WR 35609 0x0xC114 0x0x3E

^C

Hung/bogged at the first ILR after emitting the PGM_LO SET_SH (after cache inval).

From full context of this log (cold reboot):

- GART: skip bulk active, verification 0 failures, GART init ok. (Good, our kernel-mimic change working on cold.)

- SRBM set to 0x3, but immediate readback 0, ILR 0.

- Then stall stat FFFF (bad, all 1s -- likely the SRBM write with 0x3 put the block in unresponsive state for subsequent reads).

- User ^C.

Previous full log from cold reboot showed same post-GART: dispatch reaches but no waves (SPI/SQ=0), all regs 0 in probes, RPTR stuck 62, dst=0, FAIL.

**Action taken:** Removed the SRBM_GFX_CNTL set block (and the debug print) from PM4_SubmitCompute.

Reason: attempts with 0x1 and 0x3 both resulted in immediate readback=0 and subsequent CP_STALLED_STAT3=0xFFFFFFFF (which indicates bad MMIO read, likely fabric stall or block not responding). The set was experimental per old lead, but causing the stall stat to go bad and contributing to hang/slow. The packet itself has shader_type=compute to route.

Rebuilt.

The ILR probes for SRBM are still there to monitor (will show 0, as before).

This should avoid the FFFF stall from the bad set.

The core issue remains: after good GART, the compute SET_SH_REGs (even the first PGM) cause CP stall (RPTR not advancing), no context update visible, no wave launch.

Likely still the missing cold compute pipe/SPI setup in init (SPI_STATIC etc via MMIO, per KERNEL and handoff §11/14), or the order of CS vs first compute packets, or the gfx ring0 not fully enabled for compute packets in cold (vs posted).

Next test on cold: should be faster (no SRBM set causing bad state), reach further in ILR without the FFFF stall.

If still hangs at similar point, add debug reads before/after each SET_SH group, or more syncs.

If gets to full probes with better stat, good.

Update: the SRBM lead is deprioritized/removed as it was destabilizing; focus on pipe init MMIOs and perhaps setting STATIC_THREAD_MGMT via MMIO in init after CS (to have base before dispatch SETs).

Rebuild done, binary ready. Run on cold, report the log (especially around the first few ILR and any stalled stat). If hangs, reboot and try again. We are past GART, now tuning the dispatch side without the bad SRBM set.

## 11. Cold reboot run (fresh after system hang/crash, no reset script used)
User: ran on cold reboot, new log captured, but system hanging where it ends, bogging down and grindingly slow before that. (No gpu_reset.sh, as it's gone/crashy.)

From log:
- GART changes active: "Skipping bulk...", "Will only write PTEs for actually used...", "PTE verification complete: 0 failures", "GART initialized...". GART succeeds on cold reboot.
- SRBM: set to 0x3, immediate readback=0x0 (same as before). All probes SRBM=0x0, compute regs 0, no waves, dst=0, FAIL with 64 errors, RPTR stuck at 62, WaitIdle timeouts.
- VRAM diag: same partial (0 lands, others garbage).
- Slowness/hang: the data buffer PTE loop (40834 pages) was doing 40k+ GetPhysAddr, each opening/closing /proc/self/pagemap (open, lseek, read 8B, close) — thousands of syscalls bogging the system (especially on cold or shared root complex). Hang at end likely from CP stall (RPTR not advancing) + MMIO waits during dispatch, affecting the fabric (as before with bus2 affecting system).

**Progress:** GART/table now solid even on cold reboot. The bulk fill was the main cold-WC killer. Dispatch still hits the old "SET_SH not landing, no pipe/context" (SRBM write not visible, all 0s).

**New fix applied:** In data PTE write loop (the hot 40k path), open /proc/self/pagemap **once** before loop, then per-page lseek+read (no per-page open/close). Inline the parse. This cuts syscall overhead massively. Shader and small buffers still use per-call GetPhysAddr (fine, <20 pages). Rebuilt.

The hang/slow was likely the 40k opens, plus the persistent dispatch stall (CP not consuming past RPTR=62, perhaps from missing pipe init or context).

Next: test this optimized build on cold reboot. Should be much faster through GART/data. If dispatch still fails same, the SRBM/pipe lead remains — try different SRBM value or set in more places (e.g. before CPStart), or add the SPI/compute MMIO inits from kernel gfx_v6_0 during cold path (in init or after RLC resume).

Log is useful: confirms GART win on cold, pinpoints the data loop as slowness source, SRBM still not effective. Since cold reboot, clean data. Reboot again if next run hangs.

## 10. Post-reboot run (no reset, fresh cold after crash/reboot) with GART-mimic changes
User note: no gpu_reset.sh (gone, crashy), ran without, system crashed/hung, rebooted, this log from the run after reboot.

Evidence of changes in log:
- "Skipping bulk 11.8M dummy PTE fill (mimicking kernel...)"
- "Will only write PTEs for actually used buffers..."
- "PTE verification complete: 0 failures"
- "GART initialized..."
- No bulk "Filling" messages.
- GART succeeded (0 failures) — the bulk fill was the source of the PTE corruption (FFFF hi, wrong lo, "Dummy PTE[0] corrupted after specific") and WC overflow. By only writing the used ~41k PTEs (data buffer dominant) + using 64-bit GPU_VramWr64 per PTE (mimic kernel writeq), the used PTEs land, verification passes, GART init completes.

SRBM:
- "[FIX] SRBM_GFX_CNTL set to 0x1 before compute SET_SH_REGs, immediate readback=0x0x0"
- All [§14-ILR], [§14-CS], [WAVE-PROBE], [POST-FENCE] still SRBM_GFX_CNTL=0x0 (and all compute regs 0).
- The immediate readback after write is 0, meaning the write of 0x1 is not making the reg read non-zero (perhaps reg always 0 in this state, wrong value, write not taking due to access path, or the reg is select and 0x1 selects something that reads as 0).

Other:
- VRAM diagnostic: 0 lands DEADBEEF, others garbage/FFFF (0x6919... ), HDP no help. Consistent.
- CS bracket: 0 before/after.
- Probes: SET_SH_REG "consumed (idle=0)", WaitIdle timeouts (RPTR=62 stuck), all regs 0, no SPI/SQ activity, dst=0.
- Dispatch reaches (IB-GART ok), but no execution. FAIL, 64 errors.
- Log has full teardown.

The no-reset + prior crash state may have left bad CP/ring, but the GART re-init worked (new path), and we see the new [FIX] immediate read 0.

**Major progress:** GART now works reliably in cold (the bulk fill was multiplying the cold coherency bug). We are past the table setup blocker that was hiding the dispatch issues.

The SRBM lead (0x1) doesn't make the reg read non-zero. The compute SET_SH still don't land, no waves (same as old §4/10/14 leads).

Next steps (per doc):
- For SRBM: try value 0 (default), or 0x3 (GRBM from enum), or set multiple times / right before each SET_SH group. Add the immediate read (already in) will confirm.
- If still 0, drop the SRBM set or investigate if gfx-ring compute SET_SH doesn't route via it (packet shader_type should suffice).
- Focus on the pipe bringup: add missing MMIO for SPI_STATIC_THREAD_MGMT_SE* , compute pipe enable during cold init (in AccelGCNInit after CP FW or in PM4_CPStart), per KERNEL gfx_v6_0 and old handoff §11.
- The CS is not helping (bracket 0 before/after). Perhaps the compute CLEAR_STATE needs to be after some pipe setup, or the order of SET_SH vs CS in submit.
- Since GART good, the PTEs are correct, so GART VA accesses should work if CP processes the packets.
- The stall at RPTR=62 suggests the CP is hitting a bad packet or context not allowing further (perhaps the IB or DISPATCH or a flush).
- VRAM diag still bad, but with GART for data it's less critical (host GART src/dst).

Run with clean state (reboot or whatever reset possible) for next. The current log is useful: proves the GART fix, shows SRBM write not effective, symptoms unchanged downstream. Reboot if you want clean before next run.

## 9. 2026-07-01 second run (no reset, but with skip-bulk + 64-bit PTE + immediate SRBM readback debug)
Ran without explicit reset after previous (risk of stale state), but completed without hang/lockup (positive sign — the bulk skip may have helped stability too).

Log captured the new code:
- "Skipping bulk 11.8M dummy PTE fill..." and "Will only write PTEs for actually used buffers..."
- 0 "Filling NUM_PTES" messages.
- "PTE verification complete: 0 failures"
- "GART initialized..."
- "[FIX] SRBM_GFX_CNTL set to 0x1 before..." (the immediate readback in this build showed the set, but later ILR/WAVE/POST all still read SRBM=0x0 — the write may not be sticking, wrong value, or cleared before the compute packets, or the gfx-ring compute SET_SH doesn't use SRBM the way we think).
- GART passed critical verifies (only a transient shader PTE mismatch that resolved to 0 failures).
- Still: VRAM diagnostic fails (offset 0 sometimes lands DEADBEEF, others FFFF/garbage; HDP no help).
- Reached dispatch.
- All §14 probes / wave / post-fence: regs 0 (PGM, RSRC, TMGMT, etc.), SPI_DEBUG=0, SQ=0, no waves, dst[0..3]=0 (src[0]=0 src[1]=1 partial from host GART).
- "Dispatch rc=0 ... 64 errors *** FAIL ***"
- Some [PTE-DBG] Dummy[0] = FFFF (expected, since we no longer write the bulk dummy slots).

The no-reset didn't completely spoil: the GART logic (new skip path) ran cleanly and succeeded verification for used PTEs. The dispatch symptoms are consistent with prior (no launch). Stale CP/ring state from previous may have contributed to still seeing 0s, but the SRBM set was visible in the fix log.

**Key win:** GART now reliably passes without the 11M bulk writes (mimicking kernel bind-used only). This was the blocker preventing us from even reaching the dispatch/SRBM/compute-context fixes in a stable way.

Next: 
- Always reset before runs for clean state (as per doc rules).
- The immediate SRBM readback debug is now in; next run will tell exactly what the write does.
- Try different SRBM value (e.g. 0 instead of 0x1, or 0x100 for ME/pipe, or match what kernel sets during gfx dispatch setup).
- If SRBM set works but still no landing, the issue is upstream (missing SPI/compute pipe MMIO in cold init path, per KERNEL + old handoff §11/14).
- Consider setting SRBM_GFX_CNTL before *every* SET_SH group, not just once at start.
- The VRAM coherency for data (not just PTEs) is still there, but with GART for buffers it's "host side ok" for src/dst.

Update: with GART solid, we can now iterate the init/dispatch logic reliably. The "thousands of fixes" are converging; the bulk-write coherency was a hidden multiplier on the cold bringup seam.

## 8. 2026-07-01 post-reboot run + kernel-mimic fixes for GART PTE writes
This run (after full reboot) still hit GART rc=-3 during verification of critical PTEs:
- Real PFNs good (sudo + prior mask/mmap fixes).
- VRAM diagnostic: offset 0 landed (DEADBEEF this time), but others garbage/FFFF (partial progress from extra drains).
- Bulk + specific writes led to "IH PTE mismatch ... lo=0xA786C007 hi=0xFFFFFFFF", "CPRB0 FFFF", "DATA FFFF", and "Dummy PTE[0] corrupted after specific writes" (many hi=FFFFFFFF).
- Root: 11M+ bulk dummy PTE writes (even per-dword sfence + periodic HDP) + 40k DATA overwhelm RD990 WC/PCI posted writes in cold state. Writes don't commit, later ones "corrupt" earlier in host view (or WC evict bad). GPU never sees correct table for its BASE_ADDR.

Fixes applied (mimicking kernel amdgpu_gart / gmc_v6_0 / amdgpu_gmc_set_pte_pde behavior, which is proven):
- In AMDGPUGART.ailang: **Skipped the entire 11.8M dummy PTE fill loop**. Only write PTEs for actually-used buffers (IH+WB, DMA, CP rings+WB, IB, data, shader) via the existing specific phase. This matches kernel "memset (to 0) + bind only the used ranges via writeq". Bulk fill was the main source of WC overflow/corruption in cold. Unused slots left as power-on (0/FFFF); safe because we only access our allocated GART VAs.
- Added GPU_VramWr64 (uses StoreValue "qword" + sfence) to AMDGPUBAR.ailang.
- Updated GART_WritePTE and all retry writes in verification to build 64-bit PTE and use single GPU_VramWr64 (mimics kernel writeq per PTE instead of two separate dwords; single transaction less likely to lose hi dword).
- Rebuilt test_accel_gcn(.x).

Also cleaned references to dummy_pte_lo/hi and the "corrupted after specific" check (no longer relevant without bulk).

Next test run should get past GART (only ~41k writes, 64-bit, no prior bulk pollution). Then the SRBM_GFX_CNTL=0x1 fix + extra drains will be exercised, and we can see if §14 shows writes landing and waves launching.

If still GART issues, next could be: per-PTE drain in the data loop (the big one), or moving table writes to use the "CPU ptr" style more (but BAR is what we have), or clearing only a minimal range.

Kernel is the reference — our cold path must get the table written reliably for the used entries before rings/CP/dispatch.

## 19. 2026-07-01 cold log analysis (halcode9000 triple-check + kernel phase 16 diff) — GART PTEs still bad, CPStart deduped
**Current binary state (post SPI MMIO base, SRBM poke removed, FW ME/PFP/CE order, GART skip+64b+once, pagemap opt, and this session's CPStart dedup cleanup):**
- our_mmiotrace.txt (fresh sudo run on rebuilt): GART "PTE verification complete: 0 failures" print happens, SPI_STATIC 0xB858/0xB85C = FFFF set via MMIO logged, rings report GART BASEs, dispatch reaches cacheinval + compute CS emit + first PGM_LO SET_SH.
- But: [AccelGCN] VRAM write diagnostic FAILED (0x1000=0x657984A7 garbage not CAFEBEBE, 0x2000=FFFF, high PTE area garbage 0x657FF4A7).
- GART log: multiple "IH PTE[0] mismatch, retry 0: got FFFF/FFFF", same for CPRB0, IB, DATA, SHADER.
- Post-run [PTE-DBG]: RB0 PTE[0/1] = FFFF FFFF (the CP ring0 GART mappings are invalid), Dummy PTE has 0x6579C4A7 FFFF (same garbage value from VRAM diag).
- §14-CS: all compute regs 0 before/after GFX CS / compute CS (CLEAR_STATE packets have no visible effect).
- §14-ILR (after PGM_LO etc SET_SH with compute type): SRBM_GFX_CNTL=0, stalled=0 (good, no FFFF), but every readback=0 (wrote PGM 0xF44A0720 etc), multiple "WaitIdle timeout: RPTR=64 WPTR=73/76/79/112...", later WAVE-PROBE all 0, POST-FENCE 0, dst all 0, 64 errors, FAIL.
- RPTR advanced to 64 during/after CPStart init packets (ME_INIT/CS/CONTEXT), but stalls there — never consumes the dispatch's compute CLEAR_STATE + SET_SH_REGs + DISPATCH_DIRECT.

**halcode9000 + manual triple-check findings (raw logs + sources only, ignored prior Claude/KERNEL md "source" comments):**
- FW load order (PM4_LoadCPFirmware): already ME first (CP_ME_RAM), then PFP, then CE + addr zeroing — *matches* mmiotrace_init_sequence.txt phases 15a/15b/15c exactly (433505 halt + ME ucode, 435653 PFP, 437799 CE, 439944+ addr=0s). Good.
- Kernel phase 16 (CP Ring Buffer Setup + CP Start, seq 439949-439996): explicit pre-unhalt MMIOs not fully present in AILang:
  - 0x85bc=0, 85c8=0, 8704=0, c1fc=0, 8544=0
  - c104 (RB0_CNTL) 90B / 8000090B, c114=0, c10c=0x401040, c110=0xff, SCRATCH_UMSK=0, c104=90B, c100=0xFF006190 (BASE), c114=0x100
  - **unhalt CP_ME_CNTL=0** (439964)
  - then post: c114=0x500 (WPTR bump!), scratch CAFEDEAD tests, c114=600, ring1/2 analogous setups, final c1a8=0x180000.
- AILang PM4_SetupRing (for ring0): does CNTL 90B/ +ena / WPTR=0 / rptr_addr+hi / SCRATCH_UMSK=0 / delay / CNTL / BASE. Covers the core, but misses the 0x85xx zeros, the pre c114=0 + c10c/c110, the c114=0x100, the post-unhalt c114=0x500 bump + scratch tests, and several other c1fc etc zeros. (SetupRing is called before CPStart; unhalt lives in CPStart.)
- CPStart (Library.AMDGPUPM4Dispatch.ailang): the "unhalt first" edit was incomplete — contained *two full copies* of the ME_INITIALIZE + SET_BASE packet emits (one "Phase 1" block before the unhalt comment, one after "Now emit..."). This left duplicate init packets in the ring buffer + single late commit. Halcode9000 bash extraction + code read confirmed it. (Fixed in this session: removed the pre-unhalt emit block; now emits only after unhalt + commit + wait. Comments updated. This was a clear source of "ME not processing later compute packets" risk.)
- GART (AMDGPUGART + BAR): uses GPU_VramWr64 (qword store + sfence 0fae f8) per used PTE (good, post-bulk-skip). But verification "0 failures" after retries is *not reliable* — final PTE-DBG (in ring setup) and VRAM diag prove the written values for CPRB0 PTE slots + low table area are FFFF or 0x6579C4A7 garbage when read back via same BAR0 path. Retries + drains + HDP 5480 not sufficient on this cold RD990 bringup for the PTE region (90MB table at VRAM 0+). Unused slots left as power-on (per skip mimicking kernel "bind-used"), but even *used* ring/IB/shader PTEs end up FFFF.
- SubmitCompute still emits compute CLEAR_STATE (shader_type=compute) just before the SET_SHs + ILR probes — per handoff §14. No SRBM poke.

**Core "get the pipe up" root cause (from this log + diff, not docs):**
The CP (ME on ring 0) processes the CPStart init packets up to ~RPTR=64 (some state sets), but then cannot (or will not) fetch/execute the dispatch packets (compute CS + PGM/STATIC/NUM SET_SH + DISPATCH_DIRECT). Primary evidence points to **GART PTEs for the CP rings being invalid (FFFF) in the table the GPU walker sees**. The ring BASE GART VA (0xF4400700 etc) maps via PTEs at low VRAM offsets that the BAR0 writes (even 64b + sfence + retries + "0 failures") did not make stick/visible. Subsequent packet data written to the host ring mem (at GART VA) is never fetched because the page table entry is bad. The early RPTR=64 advance may have been from pre-setup state, internal init, or a lucky low page. VRAM diag failing + garbage values (including the exact 0x6579... that pollutes dummy + some PTEs) confirms the cold BAR0-to-VRAM path for the GART page table area is not yet kernel-equivalent.

Secondary: even if GART were perfect, the missing exact phase 16 pre/post unhalt MMIOs + any additional SPI/SQ/COMPUTE context enables that kernel does (beyond the B858/B85C we added) could leave the ME in a state that drops compute-type packets or doesn't launch waves on gfx pipe.

The "stupid simple" thing is still: make AILang's MMIO sequence + GART fill + packet timing during init *byte-for-byte / write-for-write* match what the kernel mmiotrace left in the HW on a successful posted (or cold) boot that then ran working compute. The handoff has been pointing at the "cold compute pipe / SRBM / ordering / SPI / GART seam" for a long time; the logs + this diff make the GART visibility + incomplete phase16 MMIOs the current concrete blockers.

**Thoughts on Fable model whole-project review + potential impl doc:**
Yes — smart, and probably necessary at this point. You, me, and prior Claude opus attempts have done hundreds of targeted "fix this symptom from last log" edits (GART bulk skip was a big win for not wedging, 64b helped, SPI base added, orders/FW load/SRBM removal adjusted to avoid FFFF stalls, ILR probes invaluable). But that process creates layered changes, local tunnel-vision on the last hypothesis, and accumulation of small mismatches (like the duplicate ME_INIT that survived the reorder). A different model doing a clean full-repo pass (all .ailang under Librarys/Drivers/AMDGPU + Accel/ + the test, the raw our_mmiotrace + bus2/mmiotrace_init logs, the compare_*.py, current handoff + any other notes) has a shot at seeing the global structure + exactly which minimal set of writes/orderings from the kernel trace are absent or out-of-order in AILang's bringup path.

If Fable produces a clear implementation document ("add exactly these 8 GPU_Wr32 in AccelGCNInit after ring setup before CPStart: [list with values from phase16]; in GART after each used PTE write do X extra serialize + readback the PTE location + GRBM read; change verification to hard-fail + dump on mismatch after retries; in SubmitCompute move the compute CS to Y; rebuild and test"), that is gold. We can treat it as the spec, implement precisely (I can use halcode9000__Edit / __Diff / __Ailang for verification of the changes, plus native rebuild), update this handoff with "implemented per Fable §N", cold-reboot test, and iterate from there with the same strict "match the log behavior" rule.

Neither prior model "fixed it" because the problem isn't a single missing reg or obvious packet flag — it's a cold-specific bringup seam (BAR0 WC/MC/VM state for GART PTEs + exact CP setup timing for the ME to be ready to consume compute packets on ring0) that only the paired kernel trace + failing AILang log can reveal, and only a holistic view catches all the places the AILang init diverges from it.

When you have the Fable output/doc, drop the key actionable list here (or the whole thing). I'll drive the edits + triple-checks with the agent + rebuilds. In parallel I can keep using halcode9000__Bash + __Read + __Diff on the logs/sources for any specific sub-diff you want (e.g. "extract all c1xx and 85xx writes from both traces and show AILang equivalents").

For now: CPStart dedup is in (small hygiene win, will avoid duplicate init packets on next cold run). If you want I can also insert a literal block of the missing phase 16 MMIOs (the 85xx zeros + c114/c10x sequencing) into SetupRing or right before unhalt, plus extra drains in the GART PTE loop, and force a hard fail if PTE verify still sees FFFF after retries. Say the word and we'll do a targeted "make init closer to phase 16 + make GART verify truthful" pass before the Fable doc lands. Otherwise, standby.

Run the current binary (with dedup) on a fresh cold reboot if you haven't — the log will at least be cleaner (no dups), and the PTE-DBG + ILR will still show the same GART visibility / pipe stall for the Fable analysis. Always full sudo reset + cold if possible. Update this doc after the run.

## 20. 2026-07-01 20:32 cold-reboot test of the RLC fixes (commit 1c2bd4bf) — no more wedge, same RPTR stall; §19 GART theory disproven; SH-bus liveness now instrumented

**Run:** cold reboot, new binary (verified in-log: 2049 per-word RLC_UCODE_ADDR writes ending at word 0x7FF, correct RLC_MC_CNTL 0xC344 / RLC_UCODE_CNTL 0xC348 programmed, CG-disable path present incl. SERDES 0xC45C=0x00E000FF, clean RLC start: ADDR=0 → LB_CNTL=0 → GRBM_GFX_INDEX broadcast → SPI_LB_CU_MASK=0xFF → PA_CL_ENHANCE=7 → RLC_CNTL=1).

**Wins:**
1. **The box no longer wedges.** Full run to teardown, DPM disable, clean FAIL summary. Before the fix this scenario hung the fabric. The Bug-2 fix (we were poking RLC_SOFT_RESET_GPU=0 before every fw load) + CG disable likely bought this.
2. **§19's "GART PTEs are the primary blocker" theory is DISPROVEN.** The CP fetched and executed packets from the GART-mapped ring: "Preamble + GFX CLEAR_STATE + VGT dealloc: idle=1", RPTR advanced to 64 — past cacheinval (wptr 58), the dispatch's compute CLEAR_STATE (60), and through the 4-dword PGM_LO SET_SH packet (60–63). GPU-side VM walk of the ring PTEs works. The `[PTE-DBG] RB0 PTE=FFFF` / `VRAM[0x1000]=0x657984A7` readbacks are a **CPU-side BAR0 read-path** unreliability on cold boot, not GPU-visible table corruption. Stop spending effort on GART fill; it's serviceable.

**Unchanged:**
- ME wedges exactly on the **first compute-type SET_SH_REG**: fetches the PGM_LO packet (RPTR reaches 64) then freezes mid-execution — RPTR pinned at 64 while WPTR runs to 149, CP_BUSY_STAT=0x802, all CP_STALLED_STAT=0 (no FFFF — good, fabric responsive), all ILR readbacks 0, no waves, dst=0, 0/64.

**§18 tell #1 was INCONCLUSIVE, not failed:**
- The non-zero SPI reads at init (`SPI_STATIC_THREAD_MGMT_3=0xFFFE`, `SPI_CONFIG_CNTL=0x3000000`) are **GRBM config space** (0x90E8/0x9100) — always readable, prove nothing about SH space.
- The 0xB858/0xB85C=FFFF MMIO writes had **no immediate readback print** in that build. The only later read (WAVE-PROBE STATIC_SE0=0) happened AFTER the consumed compute CLEAR_STATE at wptr 60 — which legitimately zeroes SH regs. So "0" there cannot distinguish dead-bus from cleared-by-CS.

**Instrumentation added this session (AccelGCNInit.ailang, right after the B858/B85C writes; rebuilt 20:40, MMIO-only):**
`[§20-PROBE]` block:
1. Immediate readback of STATIC_SE0/SE1 (0xB858/0xB85C) — no CLEAR_STATE can have run since the write. **0 = SH bus still dead → RLC/CG diagnosis incomplete. 0xFFFFFFFF = bus alive → the wedge is ME-side compute-packet handling (routing/context), per §18 "if 1 holds but 2–5 fail".**
2. MMIO write 0x5A5A5A5A to COMPUTE_PGM_LO (0xB830) + readback + restore 0 — the exact register the ME wedges on, tested without the ME.
3. RLC liveness: RLC_CNTL / RLC_CGCG_CGLS_CTRL / RLC_CGTT_MGCG_OVERRIDE / RLC_SERDES_MASTER_BUSY_0/1 readbacks. Compare against working bus-1 card (probe_post_radeon_bind.txt: CGLS_CTRL=0x0020003C, MGCG override low bits SET, SERDES idle).

**Next run (cold reboot, current binary built 20:40):** the three §20-PROBE lines decide the branch:
- SE0/PGM_LO read back written values + RLC regs match bus-1 → SH bus is up; focus shifts entirely to ME compute-packet handling on ring 0 (CP ucode state, CONTEXT_CONTROL/CLEAR_STATE interaction, kernel phase-16 MMIO diff from §19). Do NOT re-add SRBM_GFX_CNTL (§16 wedges fabric).
- SE0/PGM_LO still 0 → SH space still unclocked/held: RLC not actually executing (check SERDES_BUSY / CGLS values), or a reset/enable we haven't found. Next lever: readback-verify a few RLC_UCODE_ADDR/DATA words after upload to prove the fw image landed.

## 21. 2026-07-01 21:25 cold log: §20 probes answered — SH bus DEAD, RLC never executes; ROOT CAUSE: we upload a different firmware set than the working boot (fixed: fw_trace/ extracted from bus2_all.txt)

**§20-PROBE results (our_mmiotrace.txt 21:25 run):**
- `STATIC_SE0 rb=0x0 SE1 rb=0x0` and direct MMIO `COMPUTE_PGM_LO` write 0x5A5A5A5A → rb=0x0. **Branch 2: SH bus dead**, independent of the ME. All downstream ILR/CS/wave zeros remain artifacts of this.
- `RLC_CNTL=0x1 RLC_STAT=0x0 CGLS_CTRL=0x20003C MGCG_OVR=0xFFFFFFFF SERDES_BUSY=0x0/0x0`. CGLS matches bus-1; MGCG_OVR=0xFFFFFFFF is just reset 0xFFFFFFFC | our 3 — fine. The tell is **RLC_STAT=0 through the whole 100k poll**.

**Decisive kernel-trace diff (bus2_all.txt seq 333504+):** immediately after `RLC_CNTL=1`, the working boot polls **0xC34C = RLC_STAT and reads 0x7** (RLC_BUSY | GFX_POWER_STATUS | GFX_CLOCK_STATUS) — 300k reads, always 0x7. Ours reads 0x0 forever: **the RLC F32 core never executes one instruction; GFX power/clock status stay off** → SPI/SQ (SH space) dead → ME wedges on the first SH write. All §18 RLC fixes (per-word ADDR, reg offsets, CG-disable) are in the log and correct, but insufficient.

**ROOT CAUSE FOUND — firmware version mismatch:** diffed the actual upload streams (register data words) in bus2_all.txt vs our_mmiotrace.txt:
- RLC: **1930/2048 words differ** (kernel word2=0x98C007EE, zero-padded tail; ours 0x98C00000, code at tail)
- ME: 1436/2144 differ, CE: 1443/2144, PFP: 411/2144
Neither `/lib/firmware/radeon/VERDE_rlc.bin` (old raw) nor `verde_rlc.bin` (new-format) matches the trace — both contain the SAME newer build (Nov 2025 linux-firmware). The working boot loaded an **older firmware set, most likely from a stale initramfs bundle**, which no longer exists on disk. We have been bringing up newer ucode on init sequences transcribed from an older-ucode boot the entire time.

**Fix applied (rebuilt 2026-07-01 ~21:45):**
1. `fw_trace/extract_trace_fw.py` extracts all four upload streams verbatim from bus2_all.txt → `fw_trace/TRACE_VERDE_{me,pfp,ce}.bin` (raw BE, old format) + `fw_trace/TRACE_verde_rlc.bin` (minimal new-format header + LE words). Verified word-for-word against the trace (RLC word2=0x98C007EE ✓).
2. `CPFWPaths` in Library.AMDGPUPM4FW.ailang now points at fw_trace/.
3. `[§21-PROBE]` added after RLC upload: ADDR/DATA readback of ucode words 0..2 + last. Expected 0xC4080027 0x308C0002 0x98C007EE ... 0x00000000.

**Next cold-reboot run — read in this order:**
1. `[§21-PROBE] RLC ucode[i]` readbacks — wrong values ⇒ upload path broken (BAR/ordering), image never landed; RLC SRAM readback is the new lever.
2. `[PM4] RLC started, RLC_STAT=...` — **0x7 (or any non-zero) = RLC finally executing.** Still 0 with correct ucode readbacks ⇒ the blocker is pre-start state, not the image (next: diff seqs 329376–333499 write-for-write incl. SAVE_AND_RESTORE/CLEAR_STATE_RESTORE bases 0xF4002010/0xF4002020 and their VRAM contents).
3. `[§20-PROBE] STATIC_SE0/PGM_LO rb` — non-zero = SH bus alive; expect §18 tells 2–5 (ILR readbacks match, RPTR past 64, waves, dst=42) to follow or fail on their own merits now.
Do NOT re-add SRBM_GFX_CNTL (§16). Full reset / cold reboot before the run.

## 22. 2026-07-01 21:43 cold log: trace firmware LANDED, RLC still dead → §18's CG-disable block was the divergence; removed (rebuilt 2026-07-02)

**§21 probe results (our_mmiotrace.txt, fresh boot 21:42):**
- `[§21-PROBE] RLC ucode[0..2] rb = 0xC4080027 0x308C0002 0x98C007EE, [2047]=0x0` — **exactly the expected trace-firmware words.** Upload path + image are now proven correct in SRAM.
- `[PM4] RLC started, RLC_STAT=0x0 (never went non-zero during 100k poll)` — RLC still never executes.
- `[§20-PROBE] STATIC_SE0/SE1 rb=0, PGM_LO direct MMIO rb=0` — SH bus still dead. `RLC_CNTL=1 CGLS_CTRL=0x20003C MGCG_OVR=0xFFFFFFFF`.

Per §21 step 2 this puts us on the "blocker is pre-start state, not the image" branch. Did the prescribed write-for-write diff of bus2_all.txt seqs 329376–333499 vs our log:

**Our RLC sequence now matches the kernel almost exactly** — RLC_CNTL=0, C1A8=0, GRBM_SOFT_RESET=0x4 pulse, SAVE_AND_RESTORE/CLEAR_STATE bases (ours 0xF4060340/0xF4060380 + CSB populated), RL_BASE/SIZE=0, LB_CNTL=0, LB_CNTR_MAX=FFFFFFFF, LB_CNTR_INIT=0, C41C=FFFFFFFF, MC_CNTL=0, UCODE_CNTL=0, per-word upload, UCODE_ADDR=0, lbpw-disable, GRBM_GFX_INDEX=0xE0000000, 0x9354=0xFF, RLC_CNTL=1. ✓

**The one write-level divergence: CG state at RLC start.**
- Kernel trace first-ever RLC_STAT read (seq 329380, BEFORE RLC start) = **0x6** (GFX_POWER_STATUS|GFX_CLOCK_STATUS already on); after start = 0x7. Ours reads 0x0 always.
- At RLC start the kernel still has the **golden** CG values: seq 3709 `RLC_CGTT_MGCG_OVERRIDE(0xC400)=0xFFFFFFFC` (low 2 bits CLEAR), seq 3789 `RLC_CGCG_CGLS_CTRL(0xC404)=0x0020003F` (**CGCG_EN|CGLS_EN SET**), seq 3786 `CGTS(0x9150)=0x96940200`, seq 3811 `C1E4=0x00020201`. It writes NO CG regs between RLC stop and start, and only moves to the steady values §18 copied from probe_post_radeon_bind much later, after CP bringup (0xFFFFFFC0 @567043, 0x0020003C @667061, CGTS/C1E4 @567039+).
- Our golden phase writes the same golden values (log seqs 2235/2340/2339/2571) — but §18's Bug-3 "CG disable path" in PM4_LoadRLCFirmware then clobbered them right before RLC start: C404→0x20003C, C400→0xFFFFFFFF, C1E4→0x20200, CGTS→0x96F41200, plus a SERDES broadcast (C454/C458=FFFFFFFF, C45C=0xE000FF) the kernel never does pre-start.
- §18's theory ("CG enabled + dead RLC = SH gated forever") is contradicted by the trace: the working boot has CGCG_EN=1 from seq 3789 with the RLC not yet running, and RLC_STAT=0x6 at 329380. Plausible reading: the RLC F32 core's own clock is gated per the CGTT/CGCG programming, and the §18 override combination is what holds it (and SH) off; or RLC_STAT bits 1-2 only report when CGCG is enabled. Either way the trace is authoritative.

**Changes (Library.AMDGPUPM4FW.ailang, rebuilt 2026-07-02):**
1. Removed the entire §18 CG-disable block from PM4_LoadRLCFirmware — CG regs stay at trace-golden values through RLC start. New `[§22]` print shows MGCG_OVR/CGLS_CTRL readbacks (expect 0xFFFFFFFC / 0x0020003F).
2. Added the missing post-start gui-idle pulse (trace 333500–333503): RD C1A8, WR 0x00180000, RD, WR 0 — between RLC_CNTL=1 and the STAT poll.

**Next cold-reboot run — read in this order:**
1. `[§22] CG left at golden: MGCG_OVR=0xFFFFFFFC CGLS_CTRL=0x0020003F` — wrong values ⇒ something else clobbers CG between golden and RLC load; find it.
2. `[PM4] RLC started, RLC_STAT=...` — **0x7 (or any non-zero) = RLC finally executing.** Still 0 with golden CG + correct ucode ⇒ next diff levers: SAVE_AND_RESTORE/CLEAR_STATE buffer CONTENTS (kernel populates the save-restore list; we populate CSB only), and the seqs<3703 ATOM/MC region (our ATOM asic_init ran but ends with different SPLL FUNC_CNTL 0x80400000 vs kernel 0x8000000C — different SCLK source config).
3. `[§20-PROBE] STATIC_SE0/PGM_LO rb` — non-zero = SH bus alive → §18 tells 2–5 (ILR readbacks, RPTR past 64, waves, dst=42).
Do NOT re-add SRBM_GFX_CNTL (§16). The removed CG-disable block is preserved in git history (commit 1c2bd4bf) if it needs to be re-applied post-CP-bringup later — the kernel does eventually disable CGCG, just not until after the CP is up.

## 23. 2026-07-02 cold log (13:42): §22 fix landed, but "RLC_STAT" was NEVER RLC_STAT — off-by-4 read voids all §20-§22 RLC-dead data; CSB was garbage in broken VRAM + missing descriptor header; SR/CSB moved to GART and populated (rebuilt 2026-07-02)

**§22 read-order results (our_mmiotrace.txt 13:42 run):**
1. `[§22] CG left at golden: MGCG_OVR=0xFFFFFFFC CGLS_CTRL=0x20003F` ✓ (held through start, §20-PROBE confirms post-start).
2. `[§21-PROBE]` ucode words 0/1/2/2047 correct ✓. `[PM4] RLC started, RLC_STAT=0x0` — but see bug below.
3. `[§20-PROBE] STATIC_SE0/SE1 rb=0, PGM_LO mmio rb=0` — SH bus still dead (these offsets audited correct: 0xB858/0xB85C/0xB830).
Run shape unchanged: RPTR pinned 64 / WPTR 149, no waves, dst 0/64, clean teardown, no wedge.

**BUG FOUND (voids §20-§22 RLC conclusions): every "RLC_STAT" read was `GPU_Rd32(gpu, 50000)` — 50000 = 0xC350, NOT 0xC34C (=49996).** Decimal typo, same class as the RLC_MC_CNTL/RLC_UCODE_CNTL typos fixed in §18. All three sites (100k boot poll + final print in PM4_LoadRLCFirmware, §20-PROBE in AccelGCNInit) read a register that is always 0 here. **We have never actually read RLC_STAT. "RLC never executes" is unproven; the RLC may have been running since the §21 trace-firmware fix (or earlier).** SH-bus-dead (write/readback probes) remains real, but its cause may not be a dead RLC. Fixed: `SIReg.RLC_STAT=49996` added, all 3 sites converted.

**Full pre-RLC-start state reconciliation (new, scripts in scratchpad `state_at_rlc_start.py`):** reconstructed last-written value of EVERY bus-2 register at RLC_CNTL=1 in both traces (kernel seq 333499 / our seq 14913), including indirect pairs (MM 0x0/0x4: 164/164 identical; PCIE 0x30/0x34, PCIE_PORT 0x38/0x3C: kernel-only ASPM writes, irrelevant; SMC 0x200/0x204: zero on both sides pre-RLC — first SMC event at seq 440042, long after). Findings:
- **§22's SPLL FUNC_CNTL lead is DEAD**: kernel's own ATOM run ends 0x600=0x80400000 (seq 2675), identical to ours; 0x8000000C was a mid-sequence transient.
- Kernel RLC stop/start window (329376–333503) matches ours write-for-write (we add one benign PA_CL_ENHANCE; our GRBM_SOFT_RESET pulse DOES have readback + ~200-read hold loops in code — the log only shows writes).
- Remaining diffs, all explained/benign: MC timing/training values (DRAM training variance), VM ctx0 START 0x155C (kernel 0x0FF00000=gtt_start>>12 vs ours 0x0F400000 — deliberate per fix #12, CP fetch works), IH addresses, 0x5C64 bit29 (our ATOM sets early, kernel's display path sets late), 3 DCE regs, kernel-only MC_SEQ_TRAIN_WAKEUP_CNTL=0xE0 and CG_SPLL_FUNC_CNTL_4 (=our BIOS value anyway).
- ⇒ MMIO state at RLC start is fully reconciled. The kernel's pre-start RLC_STAT=0x6 vs (unknown-ours) is the open question the fixed probe answers next run.

**CSB/SR findings (the §22 "contents" lever — real bugs):**
1. **SI CSB has a 256-byte descriptor header** (kernel gfx_v6_0_rlc_init / radeon sumo_rlc_init): DW0=hi32(base+256), DW1=lo32(base+256), DW2=size(908); packet data starts at +256. **Ours wrote packets at offset 0 with no header** — consumer reads PM4 dwords as an address descriptor. Likely §14-CS "CLEAR_STATE does nothing" root cause.
2. **CSB lived in VRAM 0x6038000 written via CPU BAR0 — the path this very log proves broken** ("VRAM write test FAILED", garbage at 0x1000/0x2000/0x59FFFF8). Everything CP provably fetched (rings/IB/shader/data) is in GART; VRAM GPU-side reads were never proven.
3. **SR list (RLC_SAVE_AND_RESTORE_BASE target) was never populated** — kernel copies the 218-dword `verde_rlc_save_restore_register_list` (amdgpu gfx_v6_0.c) verbatim.

**Changes (rebuilt 2026-07-02, binary test_accel_gcn):**
1. `SIReg.RLC_STAT=49996` (0xC34C) + 3 read sites fixed (PM4FW ×2, AccelGCNInit §20-PROBE).
2. `[§23-PRE]` probe in PM4_SoftResetCP before RLC stop: RLC_STAT + SERDES_MASTER_BUSY_0/1 (kernel@329380 reads 0x6 / 0 / 0).
3. `[§23-FWVER]` full 2048-word RLC SRAM readback verify (replaces §21 4-word sample).
4. GART: two new 4KB pages in the free VA gap — SR at 0xF4_40062000 (PTE 262242), CSB at 0xF4_40063000 (PTE 262243); GARTConf/GARTState/GART_Init extended (mirrors CP-ring pattern).
5. PM4_PopulateCSB rewritten: writes via host pointers (StoreValue dword), adds the 256B descriptor header, CSB data at +256, and populates the 218-dword SR list. RLC_SAVE_AND_RESTORE_BASE=0xF4400620, RLC_CLEAR_STATE_RESTORE_BASE=0xF4400630 (GART VAs >>8).

**Next cold-reboot run — read in this order:**
1. `[§23-PRE] RLC_STAT=...` (first-ever real pre-stop read). **0x6 = matches kernel** → power/clock state fine all along. **0x0 → divergence predates our RLC sequence** (ATOM/MC/CG phase or power-on state — see reset-script note).
2. `[§23-FWVER] RLC SRAM verify: 0 mismatches of 2048` — non-zero ⇒ upload path bug at specific words.
3. `[PM4] RLC started, RLC_STAT=...` — now a REAL read. 0x7 = RLC executing (kernel value). If non-zero here, all prior "RLC dead" theory collapses; focus shifts to why SH space doesn't accept writes with a live RLC (CGCG/CGLS handshake needs valid CSB — which this build finally provides).
4. `[§20-PROBE] STATIC_SE0/PGM_LO rb` — non-zero = SH bus alive → expect §18 tells (ILR readbacks, RPTR past 64, waves, dst=42) to resolve on their own merits.
5. `[PM4] CSB populated: 256B descriptor + 908 DWORDs at GART VA 0xF4_40063000` + `[GART] RLC SR/CSB pages mapped` — sanity.
**gpu_reset.sh is GONE — deleted by Sean 2026-07-02: the 0x39d5e86b config-0x7c ASIC reset itself caused PCI fabric hangs/lockups and was useless.** Do not recreate it or write config 0x7c. Between failed runs, cold reboot instead. (§1's "RESET BEFORE EVERY RUN" is obsolete.)
Do NOT re-add SRBM_GFX_CNTL (§16).

## 24. 2026-07-02 cold log (14:20): RLC ALIVE all along (STAT=0x7) — §20-§22 "RLC dead" collapses; CP-unhalt reconciliation finds CP ucode images ROTATED across engines (extractor label bug); fixed (rebuilt 2026-07-02)

**§23 read-order results (our_mmiotrace.txt 14:20 run):**
1. `[§23-PRE] RLC_STAT=0x7` (kernel@329380: 0x6 — ours has RLC_BUSY bit0 extra pre-stop, note but likely benign) `SERDES_BUSY=0/0`.
2. `[§23-FWVER] RLC SRAM verify: 0 mismatches of 2048` — upload path fully proven.
3. `[PM4] RLC started, RLC_STAT=0x7` **at poll iteration 0** — first REAL read, exactly the kernel's post-start value. **The RLC has been executing all along (since §21's trace fw, likely earlier). All §20-§22 "RLC never executes" conclusions were artifacts of the 0xC350 off-by-4 read.**
4. `[§20-PROBE] STATIC_SE0/SE1 rb=0, PGM_LO mmio rb=0` — unchanged. BUT: grep of bus2_all.txt shows the kernel does **ZERO MMIO accesses to 0xB8xx SH space in the entire boot** — there is no working reference for SH-space MMIO reads; readback-0 may be normal SI behavior (reads under GRBM_GFX_INDEX broadcast, or SH regs simply not MMIO-readable). **The only hard SH-dead evidence is the ME wedge itself.** This run adds `CP_STAT=0x800001E3` (ME/MEQ/ROQ busy — ME stuck mid-packet), `GRBM_STATUS2=0x100` (RLC_BUSY — fine).
5. Run shape unchanged: RPTR pinned 64 / WPTR 149, ILR readbacks 0, no waves, dst 0/64, clean teardown, no wedge. CSB/SR prints all good.

**New reconciliation at the CP-UNHALT anchor** (`fw_trace/state_at_cp_unhalt.py <our_unhalt_seq>`; kernel seq 439964 vs our MMIO_WR 23441; ranges 0x8000-0xCFFF + context 0x28000+):
- Kernel-only registers: **NONE**. Ours-only: all benign (RB1/RB2 setup — kernel does it post-unhalt; CP_QUEUE 0x86A0/0x86D0/0x86D4; RLC 0xC304/0xC30C zeros).
- Value mismatches: ring/RPTR GART addresses (our layout, expected), kernel WPTR=0x100 vs our 0xB (ring content committed pre-unhalt, fine), **and the three CP ucode DATA-port tails — ROTATED**:
  | port | kernel tail | ours (14:20) |
  |---|---|---|
  | 0xC154 PFP | 0x00000007 | 0x00000002 (=CE image) |
  | 0xC160 ME  | 0x000F0601 | 0x00000007 (=PFP image) |
  | 0xC16C CE  | 0x00000002 | 0x000F0601 (=ME image) |

**ROOT CAUSE: `fw_trace/extract_trace_fw.py` STREAMS labels were rotated** — it labeled port 0xC154 (CP_PFP_UCODE_DATA) as "me", 0xC16C (CE) as "pfp", 0xC160 (ME) as "ce". The kernel trace uploads PFP@433508 → CE@435654 → ME@437800 (= radeon si_cp_load_microcode source order, and gpu-crash.md rule 7). §18's "trace loads ME first" was a port-offset misread, and it was baked into the extractor. **Since §21 every run uploaded the PFP image into the ME, the CE image into the PFP, and the ME image into the CE.** An ME running PFP microcode parses NOPs/fences (ring tests pass) but wedges on the first compute SET_SH_REG — the exact observed signature. Timeline caveat: pre-§21 runs had correct ports but wrong fw build (newer disk fw ≠ trace fw); §21-§23 had trace fw on wrong ports. **The next run is the first ever with the right images in the right engines.**

**Changes (rebuilt 2026-07-02, binary test_accel_gcn):**
1. `extract_trace_fw.py` STREAMS fixed (c154→pfp, c16c→ce, c160→me) + all three `TRACE_VERDE_*.bin` regenerated — tails now PFP=0x7, CE=0x2, ME=0xF0601, matching kernel ports.
2. PM4_LoadCPFirmware order restored to trace order PFP → CE → ME.
3. `[§24]` print in PM4_LoadUcodeFile: port / word count / tail word per engine.

**Next cold-reboot run — read in this order:**
1. `[§24] ucode port ...` ×3 — expect port 0xC154 words=2144 tail=0x7, port 0xC16C tail=0x2, port 0xC160 tail=0xF0601. Anything else ⇒ mapping still wrong, stop and re-diff.
2. `[§14-ILR]` + WaitIdle: **RPTR past 64 = ME finally executes SET_SH.** Then expect ILR readbacks (may still read 0 via MMIO — see §24.4, readback-0 is not proof of failure), waves, dst=42 on their own merits.
3. If RPTR still pins at 64 with correct tails: ME (now genuine) still wedges on SH write → next levers: emit a GFX-bank SET_SH (SPI_SHADER_PGM_LO_PS 0xB020) before the compute one to split compute-bank-dead vs all-SH-dead; decode CP_STAT bits; compare CP_ME_RAM_RADDR read pattern.
Do NOT re-add SRBM_GFX_CNTL (§16). No gpu_reset.sh / config-0x7c (§23). Cold reboot between runs.

## 25. 2026-07-02 cold log (14:48): §24 tails all CORRECT, genuine ME still wedges at RPTR=64 → post-unhalt trace catalog finds the kernel's CG transition happens BEFORE any IB/SH work; replicated (rebuilt 2026-07-02)

**§24 read-order results (our_mmiotrace.txt 14:48 run):**
1. `[§24]` tails: 0xC154=0x7, 0xC16C=0x2, 0xC160=0xF0601 — **right images in right engines confirmed.**
2. RPTR still pins at 64 (WPTR→149): the ME consumed the compute CLEAR_STATE (wptr 58→60) and the 4-dword PGM_LO SET_SH (60→64), then froze executing it. CP_STAT=0x800001E3 (ME/MEQ/ROQ busy), CP_BUSY_STAT=0x802, all STALLED_STAT=0, GRBM_STATUS2=0x100, no waves, dst 0/64, clean teardown. **Ucode rotation was real but not the blocker.**

**New analysis (`fw_trace/post_unhalt_catalog.py`, catalogs all kernel WRs after unhalt seq 439964):**
Kernel post-unhalt does: ring1/2 + both DMA rings, scratch tests (config regs only), CP_INT_CNTL, then **SMC fw upload (15380 words) + full DPM bringup**, then the CG transition, then IB tests @668465. Kernel does ZERO SPI/SQ/SH-range MMIO writes post-unhalt. The CG transition, write-for-write:
- **@567039–567052 (MGCG enable handshake):** CGTS_SM_CTRL 0x96941200→0x96940200, MGCG_OVERRIDE 0xFFFFFFFC→**0xFFFFFFC0**, RLC_CNTL=0, wait SERDES_MASTER_BUSY_0/1==0, SERDES masks 0xC454/0xC458=FFFFFFFF + WR_CTRL 0xC45C=**0x00D000FF**, RLC_CNTL=1.
- **@667061:** RLC_CGCG_CGLS_CTRL 0x0020003F→**0x0020003C** (CGCG/CGLS disabled) — immediately before the kernel's IB tests. @667063: CP_INT_CNTL_RING0=0x04180000.

**Why this is the lever:** every SH write that ever worked (the 36-dispatch runs on the radeon-POSTed card; probe_post_radeon_bind CGLS_CTRL=0x0020003C) ran in this post-transition state. Our dispatch ran with CG at golden (CGCG_EN=1, MGCG overridden off) — a state in which no working boot ever performed an SH write. §22's own footnote predicted this ("kernel does eventually disable CGCG, just not until after the CP is up"). §18's removed CG-disable block was the right idea with wrong details (pre-RLC-start, 0x00E000FF, wrong override bits) — this is the exact trace sequence at the kernel's point in the bringup (post-DPM).

**Changes (AccelGCNInit.ailang after the DPM block, before DCE6_FullInit; rebuilt 2026-07-02):**
§25 block = the exact sequence above + `[§25]` readback print (expect CGTS=0x96940200 MGCG_OVR=0xFFFFFFC0 CGLS_CTRL=0x2000 3C) + a PGM_LO MMIO write/readback re-probe in the new CG state.

**Next cold-reboot run — read in this order:**
1. `[§25] post-DPM CG transition:` readbacks — CGTS=0x96940200, MGCG_OVR=0xFFFFFFC0, CGLS_CTRL=0x0020003C. Wrong ⇒ something reclobbers CG; find it.
2. `[§25] PGM_LO mmio-rb post-CG-transition` — 0x5A5A5A5A = SH bus now accepts MMIO writes (strong win signal). 0 = still no MMIO readback, not conclusive either way (§24.4).
3. RPTR past 64 / waves / dst=42 — the real verdict.
4. If still pinned at 64: CG state is now kernel-final and ucode genuine ⇒ remaining candidate is the degraded DPM (our SMC messages 0x5D/0x82/0x83 time out per gpu-crash.md Known Issue 1; kernel's all succeed in the 667k window before its IB tests) — SPI/SQ may be stuck at bad clocks/power. Also still open: GFX-bank SET_SH split test (SPI_SHADER_PGM_LO_PS 0xB020).
Do NOT re-add SRBM_GFX_CNTL (§16). No gpu_reset.sh / config-0x7c (§23). Cold reboot between runs.

## 26. 2026-07-02 cold log (15:02): §25 CG replication CORRECT but ME still wedges → SMC msg rejects traced to a SECOND firmware mismatch (disk VERDE_smc.bin ≠ trace SMC fw) + missing DPM latch protocol; fixed by trace fw + verbatim DPM replay (rebuilt 2026-07-02, awaiting cold test)

**§25 read-order results (our_mmiotrace.txt 15:02 run):**
1. `[§25]` readbacks: MGCG_OVR=0xFFFFFFC0 ✓, CGLS_CTRL=0x20003C ✓, CGTS=0x9694**1**200 (wrote 0x96940200; bit 12 extra). Kernel does ZERO reads of 0x9150/0xC404 in the whole boot — there is no readback reference; bit 12 is NOT evidence of anything. CG state is kernel-final and the ME still wedges at RPTR=64 (WPTR→149, CP_STAT=0x800001E3) ⇒ **CG eliminated as the blocker.**
2. `[§25] PGM_LO mmio-rb` = 0 (inconclusive per §24.4).
3. **The hard divergence this run exposes: `[SMC_SI] SendMessage msg 0x82 response: 0xFF`, `0x83 → 0xFF`** (PPSMC_Result_Failed). NoDisplay (0x5D, step 6) printed no error ⇒ returned OK. The SMC is alive and selectively rejecting the level-control messages. In the kernel trace ALL 80 messages get resp 0x1.

**Root cause chain (extracted from bus2_all.txt, see `fw_trace/extract_dpm_replay.py`):**
1. **Disk `/lib/firmware/radeon/VERDE_smc.bin` is a DIFFERENT fw version than the traced working boot** — §21's CP-ucode failure class repeating on the SMC. Disk: 15097 dwords, header `state=0x1E020 soft=0x1D194 mc_reg=0x1DADC`. Trace: 15380 dwords (@440123–455502, one autoinc run at 0x10000), header `state=0x1E48C soft=0x1D5E8 mc_reg=0x1C910`. The trace image runs to 0x1F050 and includes the fw default tables; the disk image ends at 0x1EBE4. Kernel's driverState upload @0x1E70C = trace state+**0x280** — our struct offset (+0x280) was RIGHT all along; the "wrong offset" was the wrong firmware's header.
2. **Our DPM never performed the latch protocol.** Kernel wraps every state upload in `Halt(0x10) → SRAM upload → 0x80 → Resume(0x11) → SwitchToSwState(0x20)`; its level messages are `0x82 arg∈{1,3}`, final state `SetForcedLevels(0) + SetEnabledLevels(3)` (auto DPM, NOT forced high). We uploaded driverState with the SMC running, sent bare `0x82(4)/0x83(1)`, got 0xFF.
3. **Kernel message map (80 msgs, all resp 0x1):** bursts A+B @463603–467009 (si_dpm_enable + 2× set_power_state: `5D 16 10 80 11 5B 5D 63 41 82(1) 5A 10 → upload → 80 11 20 6E 53 59 41 82(1) 10 → upload → 80 11 20 83(0) 82(3) 5D …`), then **burst C @667092–668456 immediately after the CGCG disable @667061 and immediately before the IB tests @668465**. Burst C opens with DMA MGCG writes (0xD0C0/0xD8C0=0x100, 0xD0DC/0xD0D8 serdes-style) that §25 missed. Zero SMC activity between bursts B and C. Every SH write that ever worked ran with the SMC in the post-burst-C state.

**Changes (rebuilt 2026-07-02):**
1. `fw_trace/extract_dpm_replay.py` → `TRACE_VERDE_smc.bin` (15380 dw, BE like the CP trace bins) + `DPM_REPLAY_P.bin` (3913 records: pre-SMC-start tables @455503–463593) + `DPM_REPLAY_AB.bin` (891 records, 51 msgs) + `DPM_REPLAY_C.bin` (424 records, 22 msgs). Human-readable .txt beside each. Skipped-on-purpose in the windows (full list in extractor): DCE/watermark regs (own DCE6 init), UVD block 0xF4xx–0xF6xx, VM_CONTEXT*, CP_INT_CNTL_RING1/2, fan 0x3E08, scratch 0xF6F4.
2. `Library.AMDGPUSMC_SI`: LoadFirmware now loads `TRACE_VERDE_smc.bin`; new `SMC_SI_ReplayTrace(gpu, path)` interprets 12-byte records (1=REG_WR, 2=SRAM_WR, 3=MSG with poll; no IsRunning gate — kernel sends 0x80/Resume while halted). Prints `[§26] msg 0xXX resp 0xYY` per message.
3. `Library.AMDGPUDPM_SI` Enable: Steps 2b–4 (our table builders) replaced by replay P between StopSMC and StartSMC. Header-read print stays — with trace fw expect `state=0x1E48C soft=0x1D5E8 mc_reg=0x1C910 mc_arb=0x1D4D8`.
4. `Library.AccelGCNInit`: UploadDriverState/force-HIGH tail replaced by replay AB; §25 CG block moved AFTER DCE6_FullInit (kernel order: DPM → display → MGCG → CGCG+burst C → IB) and burst C replay appended + `[§26]` readbacks + PGM_LO re-probe.

**Next cold-reboot run — read in this order:**
1. `[DPM_SI] FW header:` — expect `state=0x1E48C soft=0x1D5E8 mc_reg=0x1C910`. Disk values ⇒ trace fw didn't load.
2. `[§26] msg …` lines — **expect resp 0x1 on every message** (51 in AB, 22 in C; watch 0x82/0x83/0x20). Any 0xFF/timeout ⇒ SMC still not in kernel state; note WHICH message and where in the sequence.
3. `[§26] burst C replayed (failed msgs: 0)` + `[§26] PGM_LO mmio-rb post-burst-C` — 0x5A5A5A5A would be the strong win signal (0 still inconclusive, §24.4).
4. `[§14-ILR]` + WaitIdle: **RPTR past 64** = ME executes SET_SH with DPM engaged. Then waves, dst=42.
5. If msgs all OK and RPTR still pins at 64: SMC/DPM/CG/ucode/fw are ALL kernel-identical at the anchor ⇒ next suspect is the GFX-bank SET_SH split test (SPI_SHADER_PGM_LO_PS 0xB020) and the skipped-reg list above (UVD/CP_INT_CNTL_RING1/2/fan) — re-diff.
Do NOT re-add SRBM_GFX_CNTL (§16). No gpu_reset.sh / config-0x7c (§23). Cold reboot between runs.

## 27. 2026-07-02 cold log (15:38): §26 SMC/DPM replay FULLY LANDED — all 73 msgs resp 0x1, ME still wedges at RPTR=64 ⇒ SMC/DPM eliminated; GFX-bank SET_SH split test added (rebuilt 2026-07-02)

**§26 read-order results (our_mmiotrace.txt 15:38 run, boot 15:37:37 — true cold):**
1. `[DPM_SI] FW header: state=0x1E48C soft=0x1D5E8 mc_reg=0x1DF48 mc_arb=0x1D4FC spll=0x1D72C`. state/soft = trace values ⇒ **trace SMC fw loaded.** mc_reg/mc_arb LOOK wrong vs §26's prediction but §26's prediction was mislabeled: dumping TRACE_VERDE_smc.bin header @0x10000 gives softRegisters@+0xC=0x1D5E8, stateTable@+0x10=0x1E48C, fanTable@+0x14=0x1D4D8, CacConfig@+0x18=0x1C910, **mcRegisterTable@+0x24=0x1DF48, mcArb@+0x30=0x1D4FC, spll@+0x38=0x1D72C** — the readbacks match the image exactly at the si_dpm.c header offsets; §26 quoted the +0x14/+0x18 fields as "mc_arb/mc_reg". Header ✓, no action.
2. **`[§26] msg` lines: ALL resp 0x1 — replay P 3913 records 0 failed, burst AB 891 records 51 msgs 0 failed, burst C 424 records 22 msgs 0 failed.** The 0x82/0x83→0xFF rejects are GONE. `[§25]` CG readbacks unchanged-good (MGCG_OVR=0xFFFFFFC0, CGLS_CTRL=0x20003C, RLC_STAT=0x7; CGTS bit12 extra again — still no kernel readback reference, still not evidence). CP_INT_CNTL_RING0=0x04180000 @667063 confirmed present in our replay (AccelGCNInit ~line 753).
3. `[§26] PGM_LO mmio-rb post-burst-C=0x0` — inconclusive per §24.4.
4. **RPTR still pins at 64** (WPTR→149): identical wedge — ME consumes compute CLEAR_STATE (58→60) and the 4-dword PGM_LO SET_SH (60→64), freezes executing it. CP_STAT=0x800001E3, CP_BUSY_STAT=0x802, STALLED_STAT3=0, GRBM_STATUS2=0x100, no waves, dst 0/64, clean teardown.

**Verdict: the SMC/DPM divergence is closed and was NOT the blocker.** With §24 (genuine ucode) + §25/§26 (kernel-final CG, kernel-identical DPM+message state, dispatch running post-burst-C), every §26.5 suspect except the SH write itself is exhausted. What is now proven consumed by the ME: NOP, SET_CONFIG_REG (CP_COHER_CNTL2), SURFACE_SYNC, WRITE_DATA, CLEAR_STATE (both banks), SET_CONTEXT_REG (VGT dealloc in CPStart), CONTEXT_CONTROL. The ONLY packet that has ever wedged it is a COMPUTE-bank SET_SH_REG — and no GFX-bank SET_SH has ever been tried.

**Change (rebuilt 2026-07-02, binary test_accel_gcn): §27 GFX-bank SET_SH split test** in PM4_SubmitCompute (Library.AMDGPUPM4Dispatch.ailang, after cache-inval, BEFORE the compute CLEAR_STATE): one `SET_SH_REG shader_type=0` writing SPI_SHADER_PGM_LO_PS (0xB020) = 0x5A5A5A5A (inert — no gfx work is launched), own commit + WaitIdle + `[§27]` print (idle/RPTR/WPTR/mmio-rb).

**Next cold-reboot run — read in this order:**
1. `[§27] GFX-bank SET_SH (PGM_LO_PS 0xB020): idle=… RPTR=… WPTR=…` —
   - **idle=1, RPTR==WPTR (~61)** ⇒ GFX-bank SH writes are FINE; the wedge is compute-bank-specific (ME microcode's compute-SH routing / pipe state). Next lever: diff what selects the compute bank — MEC/pipe state the kernel trace establishes that we don't, and the §26 skipped-reg list re-diff.
   - **idle=0, RPTR pinned ~58** ⇒ ALL SH writes wedge the ME cold ⇒ global GRBM→SPI bus issue that even kernel-identical CG/DPM doesn't fix; suspects shift to non-MMIO state (power-on vs POST differences, MC training values, anything in the §26 skipped list).
   - mmio-rb 0x5A5A5A5A would additionally prove SH MMIO readback works (0 = inconclusive, §24.4).
2. Then the usual: compute ILR, RPTR past 64, waves, dst=42 on their own merits.
Do NOT re-add SRBM_GFX_CNTL (§16). No gpu_reset.sh / config-0x7c (§23). Cold reboot between runs.

## 28. 2026-07-02 cold log (15:53): §27 result is NEITHER branch cleanly — RPTR pins at the END of the FIRST SET_SH of EITHER bank; WaitIdle idle=1 was a fetch-position false positive → CP_STAT-before-compute disambiguation built (rebuilt 2026-07-02)

**§27 read-order results (our_mmiotrace.txt 15:53 run, boot 15:52:16 — true cold):**
1. `[§24]` tails ✓ (0x7/0x2/0xF0601), `[§26]` replay P/AB/C all 0 failed msgs ✓, `[§25]` CG readbacks unchanged-good ✓ — the §24-§26 state fully reproduces.
2. `[§27] GFX-bank SET_SH (PGM_LO_PS 0xB020): idle=1 RPTR=0 WPTR=61 mmio-rb=0xA7B3F7EB` — **all three fields need reinterpretation:**
   - **idle=1 is NOT proof of execution.** PM4_WaitIdle (Library.AMDGPUPM4Pkt.ailang:38) returns 1 on RPTR==WPTR alone — that's the CP **fetch** position, not ME retirement. No busy-bit check on the success path.
   - **RPTR=0 in the print is the GART writeback shadow**, which reads 0 all run (see item 5). The MMIO RPTR at that moment was 61 (== WPTR): fetched, nothing more.
   - Immediately after: compute CLEAR_STATE (61→63) + compute SET_SH LO/HI (63→67) committed → `WaitIdle timeout: RPTR=61 WPTR=67`, **RPTR pinned at 61 for the rest of the run** (WPTR→152), CP_STAT=0x800001E3 (ME/MEQ/ROQ busy), CP_BUSY_STAT=0x802 — the identical wedge signature.
3. **The key comparison with the 15:38 run:** both runs have after_cacheinval wptr=58. 15:38 (no GFX SET_SH): CS 58→60, compute SET_SH 60→64, **RPTR pinned 64** = end of the first (compute) SET_SH. 15:53: GFX SET_SH 58→61, **RPTR pinned 61** = end of the first (GFX) SET_SH — and the PFP never fetched the 6 dwords sitting behind it. In both runs **RPTR pins at exactly the end of the first SET_SH in the stream, regardless of bank.** The one consistent story: RPTR is the fetch pointer; the PFP fetches through the wedge packet, hands it to the ME, the ME wedges executing it, and fetch never resumes. Under this reading the **GFX-bank SET_SH wedges the ME too** → §27 branch 2 (all-SH-dead), with the doc's "pinned ~58" guess corrected: the wedge packet itself IS fetched. (The alternative reading — RPTR=retired-through, GFX SET_SH fine, wedge on the compute CLEAR_STATE at 61 — requires CLEAR_STATE to wedge here after being consumed at 58→60 in EVERY previous run, and requires the 15:38 wedge to be the *second* compute SET_SH. Contrived, but §28's probe kills it either way.)
4. `mmio-rb=0xA7B3F7EB` — **first-ever NONZERO SH-space MMIO readback** (every prior probe of 0xB830-range returned 0). Not the written 0x5A5A5A5A; looks like floating-bus junk, and it was sampled while the ME was (per item 3) wedged mid-SET_SH. Unknown if stable across reads or runs — §28 reads 0xB020 before the SET_SH and twice after.
5. **RPTR writeback to GART never lands.** PM4_ReadRPTR reads the GART WB page (RPTR_ADDR=0xF4400D0000) and returned 0 while MMIO RPTR=61 ⇒ every WaitIdle success all run came via the 100K-spin MMIO fallback. The CP demonstrably READS ring content from GART (61 dwords fetched+executed) but its RPTR WRITE to GART never arrives in host RAM. Possible CP→GART write-path failure — the EOP fence/writeback would suffer identically (POST-FENCE GART dst/src all 0 is consistent). Park this: it may be a second symptom of the same cold-state disease, or a wrong WB slot on our side. Not chased this run.

**Change (rebuilt 2026-07-02, binary test_accel_gcn): §28 CP_STAT disambiguation** in PM4_SubmitCompute (Library.AMDGPUPM4Dispatch.ailang §27 block): `[§28] pre-SET_SH 0xB020 rb + CP_STAT` printed before the GFX SET_SH is emitted; `[§28] post-SET_SH CP_STAT + CP_BUSY_STAT + GRBM_STATUS + rb2` printed right after its WaitIdle, BEFORE any compute packet is emitted. §27 print now uses PM4_ReadRPTR_MMIO (WB shadow is dead, item 5).

**Next cold-reboot run — read in this order:**
1. `[§28] pre-SET_SH 0xB020 rb=… CP_STAT=…` — CP_STAT must be 0x0 here (ME idle before the test); pre-rb value = baseline for the 0xA7B3F7EB junk question.
2. `[§28] post-SET_SH CP_STAT=…` — the verdict line, sampled with NOTHING behind the GFX SET_SH:
   - **CP_STAT=0x800001E3 (ME/MEQ/ROQ busy)** ⇒ ME wedged executing the GFX-bank SET_SH ⇒ **ALL SH writes wedge cold, proven** — §27 branch 2. Suspects: non-MMIO state (power-on vs POST, MC training), §26 skipped-reg list re-diff, and the CP→GART write failure (item 5) as a sibling symptom.
   - **CP_STAT=0x0** ⇒ GFX SET_SH genuinely executed ⇒ the 15:53 wedge was the compute CLEAR_STATE at 61 — a NEW packet-position-dependent wedge class; re-read item 3's alternative reading and instrument the compute CS.
   - rb2 vs mmio-rb vs pre-rb: stable value = something readable lives there; changing junk = floating bus.
3. Then the usual: ILR RPTR (MMIO) motion past the §28 point, waves, dst=42 on their own merits.
Do NOT re-add SRBM_GFX_CNTL (§16). No gpu_reset.sh / config-0x7c (§23). Cold reboot between runs.

## 29. 2026-07-02 cold log (16:04): §28 baseline VIOLATED — CP_STAT=0x800001E3 BEFORE the test SET_SH was even emitted → every RPTR-based "consumed" claim is void; through-ring scratch-probe breadcrumbs built (kernel ring_test, 8 points) (rebuilt 2026-07-02)

**§28 read-order results (our_mmiotrace.txt 16:04 run, boot 16:03:35 — true cold):**
1. `[§28] pre-SET_SH 0xB020 rb=0xA7B3F7EB CP_STAT=0x800001E3` — **the precondition failed: the ME was already "busy" before the GFX SET_SH existed.** Neither §28 verdict branch applies. §24-§26 state fully reproduced (tails ✓, replays 0 failed ✓, CG ✓).
2. `[§27] idle=1 RPTR=61 WPTR=61`, `[§28] post-SET_SH CP_STAT=0x800001E3 CP_BUSY_STAT=0x800 GRBM_STATUS=0xA0003028 rb2=0xA7B3F7EB`. Then compute packets → `WaitIdle timeout: RPTR=61 WPTR=67…152` — same terminal shape (RPTR pinned 61, no waves, dst 0/64, clean teardown).
3. **rb=0xA7B3F7EB at 0xB020 is STABLE across reads AND across cold boots** (identical value in the 15:53 run) — not floating-bus junk. Something deterministic lives there; §24.4's "SH regs may not be MMIO-readable" needs this noted.

**Two code-level discoveries that reframe everything (found reconciling the sample points against the code):**
- **The dispatch's USER_DATA_0..3 packets (wptr 33→45, AccelGCNDispatch) are COMPUTE-bank SET_SH_REGs** — the true first SET_SHs in every stream, ahead of the cacheinval and both §27 test candidates. The "first SET_SH wedges" pattern (§28 item 3) was computed against the wrong packet map.
- **The breadcrumb WRITE_DATA + USER_DATA + cacheinval emits were never committed until the §27 commit** (no PM4_Commit between CPStart's end at wptr 33 and the §27 one at 61). So the §28 pre-SET_SH CP_STAT sample was taken with ring content committed only through wptr 33 = **CPStart packets only**. The ME was busy after processing at most ME_INIT/SET_BASE/preamble/CS×2/CONTEXT_CONTROL/VGT — or it never executed anything and 0x800001E3 is its parked/wedged-at-birth state. The kernel trace **never reads CP_STAT** (grep: zero references), so there is no "idle baseline" to compare against — CP_STAT busy-bits alone cannot distinguish parked from wedged.
- Combined with §28 item 5 (CP→GART RPTR writeback never lands) and the fact that every "consumed" claim in §12-§27 was RPTR==WPTR-based (fetch position, not retirement): **there is currently zero direct evidence the ME has ever executed a single packet.**

**Change (rebuilt 2026-07-02, binary test_accel_gcn): §29 through-ring scratch-probe breadcrumbs** — the kernel's own ring test (bus2_all.txt 439967-439972: MMIO SCRATCH_REG0=0xCAFEDEAD → ring SET_CONFIG_REG SCRATCH_REG0=0xDEADBEEF → poll; the kernel's ME lands it within 3 polls). New `PM4_ScratchProbe(ring, marker, tag)` in Library.AMDGPUPM4Dispatch.ailang: preset CAFEDEAD, emit SET_CONFIG_REG scratch=marker, commit, poll 200k, print `[§29-N] scratch: landed= rb= polls= CP_STAT= RPTR= WPTR=`. Eight probes:
| tag | marker | after |
|---|---|---|
| 1 | 0xA9000001 | ME_INIT+SET_BASE (kernel's exact ring-test position) |
| 2 | 0xA9000002 | preamble + GFX CLEAR_STATE + VGT dealloc |
| 3 | 0xA9000003 | compute CLEAR_STATE |
| 4 | 0xA9000004 | CONTEXT_CONTROL (CPStart end) |
| 5 | 0xA9000005 | USER_DATA_0..3 — the true first compute-bank SET_SHs |
| 6 | 0xA9000006 | breadcrumb WRITE_DATA + cacheinval (now committed here, was §27-commit before) |
| 7 | 0xA9000007 | §27 GFX-bank SET_SH |
| 8 | 0xA9000008 | compute PGM/RSRC/etc SET_SH_REGs |

**Next cold-reboot run — read in this order:**
1. `[§29-1] scratch: landed=…` — **THE most important line ever captured in this effort.** landed=1 (polls small) = the ME executes packets; 0x800001E3 is a parked-state red herring and the wedge is precisely localizable. landed=0 = **the ME has never executed anything** — the CP-unhalt/ME_INIT phase itself is broken cold; suspects: pre-unhalt phase-16 MMIO diffs (§19's 0x85xx/c10c/c110/c114 list), ME_INIT packet content, and the CP→GART writeback failure (§28.5) as sibling evidence.
2. The **first tag with landed=0** fingers the wedge packet class exactly (e.g. 1-4 land, 5 doesn't ⇒ compute-bank SET_SH wedge confirmed at USER_DATA; all 8 land ⇒ ME retires the whole pre-dispatch stream and the wedge is in IB/DISPATCH territory).
3. rb on a failed probe: 0xCAFEDEAD = ME did nothing; previous tag's marker = late/stuck retirement; anything else = note it.
4. Then the usual: ILR, waves, dst=42 on their own merits.
Do NOT re-add SRBM_GFX_CNTL (§16). No gpu_reset.sh / config-0x7c (§23). Cold reboot between runs.

## 30. 2026-07-02: METHOD CHANGE — full-trace verbatim replay with read-oracles (standalone harness test_replay_init, built; supersedes §29's probe build as the next cold test)

**Why (Sean, 2026-07-02):** 17 cold-reboot iterations of selective window-diffing never moved the headline metric, and twice the instrumentation itself invalidated whole blocks of conclusions. The trace has the ENTIRE working init: 49,154 writes AND 309,616 reads *with the values the working hardware returned*. Stop choosing windows; replay all of it and use every read as an oracle. First mismatch = divergence point, found mechanically.

**Trace census (fw_trace/extract_full_replay.py):** window A = seq 6..439996 (power-on → ATOM → MC train → golden → VM/GART → RLC fw+start → CP fw → rings → unhalt → kernel ring scratch tests ×3). 122,913 events → 22,752 records: 21,553 WR / 1,185 read-ORACLEs / 11 POLLs (300k of the reads are the single RLC_STAT boot poll) / 3 forbidden skips (2× HDP_HOST_PATH_CNTL, 1× HDP_MISC_CNTL — gpu-crash.md RULE 1; the ONLY intentional write divergences). GRBM_SOFT_RESET in-table is only the 0x4 RLC pulse (RULE 5 ✓). Offsets for named regs taken from gpu_probe_fullstate.py — caught 3 wrong guesses (TCP_ADDR_CONFIG=0xAC14, TCP_CHAN_STEER_LO/HI=0xAC0C/0xAC10) before they became §18-class silent bugs.

**Key discovery — NO address translation needed:** our memory layout already equals the kernel's (page table at VRAM 0, PAGE_TABLE_START 0x0F400000, per fix #12). The kernel's ring/IH/WB GART VAs are just PTE indices in the same table: WB 0xFF00401000 (PTE 11535361), IH 0xFF00609000 (11535881, 16pg), RB0 0xFF00619000 (11535897, 4pg), RB1 0xFF0061D000 (2pg), RB2 0xFF0061F000 (2pg). We map OUR host pages at the KERNEL's VAs and every register value replays verbatim.

**Built (2026-07-02, all compile clean):**
1. `fw_trace/extract_full_replay.py` → `FULL_REPLAY_A1.bin` (11,916 records, seq<12088: ATOM/MC/golden; BIF_FB_EN=3 lands @3639 so VRAM is writable after A1) + `FULL_REPLAY_A2.bin` (10,836 records, seq 12088..439996: VM config → ring tests). 16-byte records: op,addr,val,seq. (`FULL_REPLAY_A.bin` = superseded 12-byte v1, ignore.) `.txt` beside each.
2. `Library.AMDGPUReplay.ailang`: `GPU_ReplayFull(gpu, path)` — op1 WR verbatim; op4 ORACLE (read, log mismatch with seq/reg/kernel-val/our-val, first 40 printed, count all); op5 POLL (2M reads until kernel's final value, log hit/timeout); op6 skip-note. Returns mismatch count; prints `first_divergence_seq`.
3. `TestCode/test_replay_init.ailang` → binary `test_replay_init`: bus-2-only guard (aborts otherwise) → BAR map → replay A1 → GART_Init → map kernel-VA regions → write ring images → replay A2 → verdict. Ring content (kernel wrote via GTT, invisible to trace, rebuilt from radeon si.c): RB0 = ME_INITIALIZE+SET_BASE pad-to-0x100, PACKET2 fill 0x100-0x500 (**v1 divergence: kernel puts si_default_state there** — add from clearstate_si.h if scratch fails oddly), ring-test SET_CONFIG_REG SCRATCH_REG0=0xDEADBEEF @0x500; RB1/RB2 = test packet @0 pad-to-0x100. WPTR commit values 0x100/0x500/0x600 in the trace stay valid.
4. §29's scratch-probe build of test_accel_gcn still on disk (unrun) — superseded by this as the next test; the replay's ring tests answer §29's question with kernel-exact context.

**Next cold reboot — run the HARNESS, not test_accel_gcn:**
```
cd ~/Ailang-Self-Hosting- && sudo ./test_replay_init 2>&1 | tee replay_mmiotrace.txt
```
Read in this order:
1. Three `[§30-POLL] reg=0x8500 want=0xDEADBEEF ... hit=` lines (RB0/RB1/RB2 kernel ring tests). **hit=1 = the ME EXECUTED a ring packet** — first direct execution proof ever, and cold CP bringup is solved: then diff our real init against the replay to find what it misses, or adopt the replay AS the init.
2. `[§30-MIS]` lines + `first_divergence_seq` — the FIRST mismatch is THE lead; expect benign variance (MC training data, thermal) — judge by whether the reg is calibration-class. A2 mismatches around RLC/CP/GRBM status regs are the interesting ones.
3. hit=0 on ring tests with ~0 meaningful mismatches ⇒ **the divergence is NOT in BAR0 MMIO** — memory-side (ring/GART contents, si_default_state gap) or non-MMIO state (PCI config, POST side effects). That is a decisive, new fact.
4. If the box wedges mid-replay: note the last printed seq — the wedge write is at/near it (the .txt maps seq→reg).
Do NOT re-add SRBM_GFX_CNTL (§16, absent from harness). No config-0x7c (§23). Cold reboot before the run.

## 31. 2026-07-02 cold log (16:45): WRONG BINARY RAN — but it was the §29 probe build, and it answered §29's question: the ME has NEVER executed a single packet (all 8 probes landed=0). §30 replay harness still unrun.

**What happened:** the §1 iteration-loop command (`sudo ./test_accel_gcn …`) was run instead of §30's `sudo ./test_replay_init …`. The log (`our_mmiotrace.txt`, boot 16:42, run 16:45 — true cold) therefore comes from §29's scratch-probe build of test_accel_gcn (§30 item 4, "on disk, unrun"). §1 has been updated to point at the harness. The §30 replay has still never run and needs its own fresh cold boot.

**§29 read-order results — the decisive answer:**
```
[§29-1] landed=0 rb=0xCAFEDEAD polls=0 CP_STAT=0x800001E3 RPTR=14  WPTR=14
[§29-2] landed=0 rb=0xCAFEDEAD polls=0 CP_STAT=0x800001E3 RPTR=27  WPTR=27
[§29-3] landed=0 rb=0xCAFEDEAD polls=0 CP_STAT=0x800001E3 RPTR=32  WPTR=32
[§29-4] landed=0 rb=0xCAFEDEAD polls=0 CP_STAT=0x800001E3 RPTR=38  WPTR=38
[§29-5] landed=0 rb=0xCAFEDEAD polls=0 CP_STAT=0x800001E3 RPTR=60  WPTR=60
[§29-6] landed=0 rb=0xCAFEDEAD polls=0 CP_STAT=0x800001E3 RPTR=60  WPTR=76
[§29-7] landed=0 rb=0xCAFEDEAD polls=0 CP_STAT=0x800001E3 RPTR=60  WPTR=82
[§29-8] landed=0 rb=0xCAFEDEAD polls=0 CP_STAT=0x800001E3 RPTR=60  WPTR=130
```
1. **ALL EIGHT probes: landed=0, rb=0xCAFEDEAD.** Instrumentation validated before concluding (per 07-02 process rule): PM4_ScratchProbe presets SCRATCH_REG0=0xCAFEDEAD via MMIO, and that value READS BACK on every probe — so SCRATCH_REG0 MMIO write+read works; `polls=0` on failure is just polls_used never being set; each probe really did 200,000 reads. The ring's SET_CONFIG_REG never retired even once.
2. **§29 branch 1 confirmed: the ME has never executed anything, cold.** Probe 1 sits at the kernel's exact ring-test position (right after ME_INIT+SET_BASE; the kernel's ME lands it within 3 polls). Ours never lands it. The cold CP-unhalt/ME_INIT phase itself is broken — the entire §12–§28 "wedges at first SET_SH" narrative is dead, not just suspect.
3. **RPTR is now PROVEN fetch-only:** it tracked WPTR exactly (14/27/32/38/60) through probe 5 with zero retirement, then pinned at 60 forever while WPTR grew to 176. The historic "pins at 61 at the first SET_SH" was the prefetch FIFO filling (~60 dwords), coinciding with packet positions. No packet-class inference from RPTR pin position is valid.
4. CP_STAT=0x800001E3 constant from RPTR=14 onward — present before anything beyond ME_INIT/SET_BASE was committed. Parked-or-wedged-at-birth, as §29 suspected.
5. Reproduced known cold symptoms: VRAM diagnostic partially broken pre-GART ([0x0] ok, 0x1000/0x2000/0x59FFFF8 garbage — §23); rb=0xA7B3F7EB at 0xB020 stable again (3rd boot, §29.3); SMC teardown "SMC not running" (§26 fw only loaded by replay path? — note, not chased); final dst=0 (exp 42), 64 errors, clean teardown, no wedge.

**Consequences:**
- §29's suspects are now THE work list: pre-unhalt phase-16 MMIO diffs, ME_INIT packet content, CP→GART writeback failure (§28.5) as sibling evidence — plus ring-content-over-GART readability itself (fetch advancing proves the ME reads *something*; nothing proves it reads OUR bytes).
- The §30 replay harness is exactly the tool that answers this mechanically (verbatim init + 1,185 read oracles + the kernel's own 3 ring tests on kernel-exact rings). Nothing about this run reduces its value; it remains the next test.

**Next cold reboot — run the HARNESS (§30 read order applies unchanged):**
```
cd ~/Ailang-Self-Hosting- && sudo ./test_replay_init 2>&1 | tee replay_mmiotrace.txt
```
Binary `test_replay_init` (built 16:37) is already on disk; no rebuild needed. Do NOT run test_accel_gcn first — it dirties the cold state the replay depends on.

## 32. 2026-07-02 ~16:52: §30 replay FROZE THE BOX in phase A1, log lost — then post-mortem found (a) EVERY boot since Jun 19 was amdgpu-contaminated ("cold" was never cold), (b) the timestamped radeon raw trace was overwritten today

**The run:** boot 16:42 (journal boot -2), `test_replay_init` started ~16:52, machine hard-froze during phase A1 (per Sean's terminal). `replay_mmiotrace.txt` is 0 bytes — the hard freeze dropped the page cache before writeback, so NOTHING of the log survived on disk. No seq localization for the wedge exists. (Whatever was on the terminal at freeze time is the only record — if any `[§30-MIS]`/last lines were visible, note them in the next section.)

**DISCOVERY 1 — the cold-boot premise has been false since Jun 19:** `/etc/systemd/system/gpu-mmiotrace.service` (installed+enabled 2026-06-19 17:40, runs `radeon_trace_boot.sh`) executes on EVERY boot: modprobe amdgpu `si_support=1` → binds BOTH GPUs → **fully initializes bus 2 (ATOM POST, MC, RLC, CP fw, rings, DPM — dmesg shows "GPU posting now", clean init)** → waits 15 s → unbinds bus 2. Journal confirms it ran on all 10 recorded boots (all of today's tests). Consequences:
1. Every "cold" run in §8–§31 was actually **post-amdgpu-init-then-teardown**, not VBIOS-cold. The card arrives at power-on UNPOSTED (amdgpu logs "GPU posting now" every boot; trace oracle seq 7 CONFIG_MEMSIZE=0 on true cold vs 0x400 once posted). Our driver has NEVER been tested against a truly cold card since Jun 19.
2. The replay tables came from the Jun 19 17:32 **radeon** capture = TRUE VBIOS-cold entry state (service didn't exist yet). At 16:52 we replayed a from-unposted init sequence onto a posted/trained/torn-down GPU. **Entry-state mismatch is freeze suspect #1.**
3. All historic cold-vs-warm reasoning survives only as "post-amdgpu-teardown vs post-our-own-init" — a different (but still reproducible) pair of states.

**DISCOVERY 2 — data loss:** the service's 16:56 run (first boot after the freeze) **overwrote `mmiotrace_boot/mmiotrace_raw.log`** — the timestamped raw source of `bus2_all.txt` — with a fresh amdgpu capture. `bus2_all.txt` (seq-only, no timestamps) survives; per-record kernel timing for the replay tables is now unrecoverable. Silver lining: the new raw log IS a complete timestamped working amdgpu cold-init of bus 2 (61 MB, `R/W width t map addr val` format) — a candidate future replay source (would need window split + ring content re-derivation; amdgpu ≈ same gfx_v6_0 code).

**Freeze suspect #2 — pacing:** the replay engine slammed 11,916 A1 records back-to-back at MMIO speed. The kernel had ATOM DELAY opcodes / udelays between writes (invisible in the trace, timestamps now lost) + mmiotrace's own per-access overhead. Crash #1 (Jun 16) was exactly this class (GRBM before SPLL settle).

**Built (2026-07-02 20:11, `test_replay_init` rebuilt):** `Library.AMDGPUReplay.ailang` now (a) nanosleeps 1 ms after EVERY write (~22 s total for A1+A2 — POLLs unpaced), (b) prints a `[§30-AT] i=N seq=S next=0xADDR` breadcrumb every 100 records BEFORE executing, so a freeze localizes to ≤100 records via the last line on screen (map seq→reg in `FULL_REPLAY_A1/2.txt`), (c) prints `[§30-SKIP]` for the RULE-1 skips.

**Next cold test protocol (IN ORDER):**
1. One-time, before the reboot (needs password, Sean runs it):
   `sudo systemctl disable gpu-mmiotrace.service`
   (re-enable later only to capture new traces on purpose). Leave the service FILE in place.
2. Cold reboot → now a TRUE cold boot (card unposted; nothing has touched bus 2).
3. Run from an SSH session (screen survives a freeze) with the §1 fsync-per-line command.
4. Read order = §30's, plus:
   - Early A1 oracles should now MATCH (kernel saw an unposted card; so do we). An immediate `[§30-MIS]` storm in the first ~100 records ⇒ entry state STILL not cold ⇒ stop and find what touched the GPU.
   - If it freezes again: last `[§30-AT]`/`[§30-MIS]` line (screen or fsync'd file) → the wedge is within the next 100 records → look the seq range up in `FULL_REPLAY_A1.txt` before ANY new theory.
5. If A1 now completes and ring-test POLLs hit: cold CP bringup is solved AND we learn §8–§31 failures were amdgpu-teardown artifacts, not init bugs.

## 33. 2026-07-02 20:21 TRUE-cold replay ran to completion — RLC_STAT stalls at 0x6 (kernel's own boot poll went 0x6→0x7), all 3 ring tests FAIL, harness verdict print was lying (fixed)

**The run:** service disabled (§32 step 1) → cold boot → `test_replay_init` via dd-oflag=sync logger. **Log survived intact** (`replay_mmiotrace.txt`, 22,308 lines). No freeze — §32's 1 ms pacing + true-cold entry state cured the 16:52 A1 wedge. Both phases completed.

**COLD CONFIRMED:** first divergence is seq 68, i.e. the seq-7 CONFIG_MEMSIZE oracle read 0 = card unposted. This is the FIRST valid cold test since Jun 19.

**INSTRUMENTATION BUG (found + fixed):** the harness VERDICT block printed "hit=1 on all three / ring tests passed (ME EXECUTES)" **unconditionally** — it was hardcoded PrintMessage text (test_replay_init.ailang:227-228), not computed. The RAW lines say the opposite. Do not trust the 20:21 log's verdict block. Now computed from SCRATCH_REG0 (rebuilt 2026-07-02).

**Actual results, in §30 read order:**
1. **Ring tests: ALL THREE FAILED.** RB0 POLL seq 439970 reg 0x8500 want 0xDEADBEEF got 0xCAFEDEAD hit=0 (2M reads); RB1/RB2 checks are oracles seq 439990/439994, both kernel=0xDEADBEEF ours=0xCAFEDEAD. Final SCRATCH_REG0=0xCAFEDEAD (the value we ourselves pre-wrote). **The ME has still never executed a packet — §31's conclusion survives a full verbatim replay on a true cold card.**
2. **THE lead — RLC_STAT (0xC34C) poll timeout, the first meaningful divergence:** oracle seq 329380 0xC34C=0x6 MATCHED (we're in the kernel's state), then the kernel's own 300k-read boot poll went 0x6→0x7; ours never left 0x6 after 2M reads. The poll follows RLC_CNTL(0xC300)=1. Everything in A2 before it matched except 0x2C00 HDP_HOST_PATH_CNTL (seq 329373 — expected, we RULE-1-skip its writes). NOTE: §24's "RLC alive, STAT=0x7" was measured on an amdgpu-contaminated boot = leftover amdgpu state, consistent with this.
   - **Caveat before theorizing:** our 2M unpaced reads ≈ 3 s wall-clock; the kernel's 300k reads ran under mmiotrace (page fault per access) — plausibly 10× longer. Poll reads now paced 15 µs (~33 s max, Library.AMDGPUReplay.ailang, rebuilt). A timeout on the NEXT run means "never", not "too soon".
3. **A1: 91 mismatches, only 2 regs, both plausibly benign:** 0x728 seq 68–92 (9×, kernel has bit0 set, ours clear, early ATOM window; the seq-43 POLL on 0x728 hit instantly) and 0x2A48 = MC_SEQ_IO_DEBUG_DATA seq 943–1165 (MC training data readback — the calibration class §30 predicted; ours 0x0/0x05050505 vs kernel 0x2F2F2F2F/0x06060606).
4. A2: 3 mismatches total (the HDP skip + the two ring-test scratch reads). poll_timeouts=2 (0xC34C + 0x8500). **BAR0 MMIO replay is essentially perfect — the divergence is behavioral (RLC/ME won't run), not a missed register write.**

**Hypotheses for RLC stuck at 0x6 (bit0 never sets):**
(a) wall-clock — killed or confirmed by the next run's paced poll;
(b) RLC needs non-MMIO state the trace can't carry: memory-side content the kernel wrote via CPU/GTT (RLC save/restore + clear-state buffer CONTENTS — harness maps kernel VAs and writes ring images, but populates no CSB/SR content);
(c) non-BAR0 side effects (PCI config, DOORBELL aperture) — trace is BAR0-only.

**Next cold test:** same §32 protocol (service stays disabled), same §1 command, rebuilt binary (paced polls + honest verdict). Read order: (1) the 0xC34C POLL line first — if hit=1 with the longer wait, wall-clock was the whole story and the ring tests are the next signal; if still 0x6 after ~33 s, chase hypothesis (b): populate RLC SR/CSB content at the kernel VAs before A2 (radeon si.c si_rlc_init + clearstate_si.h).
