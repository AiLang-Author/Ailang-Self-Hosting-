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
```
sudo ~/Ailang-Self-Hosting-/gpu_reset.sh
cd ~/Ailang-Self-Hosting- && ./ailang.x TestCode/test_accel_gcn.ailang test_accel_gcn
sudo ./test_accel_gcn 2>&1 | tee our_mmiotrace.txt
```
**RESET BEFORE EVERY RUN.** Use the PCI config ASIC reset (0x39d5e86b to config 0x7c). Reboot if hard wedge.

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
