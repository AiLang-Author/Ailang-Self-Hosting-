#!/usr/bin/env python3
"""
Extract the complete GPU init sequence from bus2_writes.txt mmiotrace.
Groups writes into distinct initialization phases using precise boundary detection.
"""

import re
import sys

INPUT = "/home/bob/Ailang-Self-Hosting-/bus2_writes.txt"
OUTPUT = "/home/bob/Ailang-Self-Hosting-/mmiotrace_init_sequence.txt"

LINE_RE = re.compile(
    r'^\s*(\d+)\s+\[b2\]\s+WR\s+(\S+)\s+=\s+(0x[0-9A-Fa-f]+)\s+\[([^\]]*)\]'
)

def parse_line(line):
    m = LINE_RE.match(line)
    if not m:
        return None
    return (int(m.group(1)), m.group(2), m.group(3), m.group(4))

# ---- Pass 1: Read all writes ----
print("Reading trace file...", file=sys.stderr)
writes = []
with open(INPUT, 'r') as f:
    for line in f:
        parsed = parse_line(line)
        if parsed:
            writes.append(parsed)

N = len(writes)
print(f"Parsed {N} writes", file=sys.stderr)

# ---- Pass 2: Find phase boundaries by scanning for landmark registers ----
# We use the array index (not sequence number) for boundaries.
# Strategy: find specific landmark writes, then define phases by index ranges.

def find_first(predicate, start=0, end=None):
    """Find first index where predicate(seq, reg, val, cat) is true."""
    if end is None:
        end = N
    for i in range(start, end):
        if predicate(*writes[i]):
            return i
    return None

def find_last(predicate, start=0, end=None):
    """Find last index where predicate is true."""
    if end is None:
        end = N
    result = None
    for i in range(start, end):
        if predicate(*writes[i]):
            result = i
    return result

# Landmark indices:
# First write
idx_first = 0

# First REG_0x0030 write (ATOM BIOS indirect register access start)
idx_atom_indirect = find_first(lambda s,r,v,c: r == 'REG_0x0030')

# First HDP_HOST_PATH_CNTL (seq ~130)
idx_hdp_first = find_first(lambda s,r,v,c: r == 'HDP_HOST_PATH_CNTL')

# First REG_0x12xxx block (display controller / MC init area, file line ~160)
idx_dc_mc_init = find_first(lambda s,r,v,c: r.startswith('REG_0x12'), idx_hdp_first)

# CG_SPLL_FUNC_CNTL_4 (SPLL setup start)
idx_spll = find_first(lambda s,r,v,c: r == 'CG_SPLL_FUNC_CNTL_4')

# First CG_SPLL_FUNC_CNTL write after SPLL_FUNC_CNTL_4 (last SPLL write)
# Actually, find end of SPLL block: first non-CG_SPLL register after idx_spll
idx_post_spll = idx_spll
while idx_post_spll < N and (writes[idx_post_spll][1].startswith('CG_SPLL') or writes[idx_post_spll][1] == 'CG_SPLL_FUNC_CNTL_3'):
    idx_post_spll += 1

# MC_VM_SYSTEM_APERTURE_LOW_ADDR (first occurrence)
idx_mc_vm_aperture = find_first(lambda s,r,v,c: r == 'MC_VM_SYSTEM_APERTURE_LOW_ADDR')

# MC_VM_MX_L1_TLB_CNTL (VM/TLB setup)
idx_vm_tlb = find_first(lambda s,r,v,c: r == 'MC_VM_MX_L1_TLB_CNTL')

# First VM_INVALIDATE_REQUEST after VM/TLB setup
idx_vm_invalidate_start = find_first(lambda s,r,v,c: r == 'VM_INVALIDATE_REQUEST', idx_vm_tlb)

# First REG_0x3e00 with seq > 300000 (SDMA engine setup, after the long MC training gap)
idx_sdma_setup = find_first(lambda s,r,v,c: r == 'REG_0x3e00' and s > 300000)

# GB_ADDR_CONFIG with seq > 300000 (second occurrence, the "real" GPU init)
idx_gb_addr_config_2 = find_first(lambda s,r,v,c: r == 'GB_ADDR_CONFIG' and s > 300000)

# First GRBM_GFX_INDEX after GB_TILE_MODE31
idx_gb_tile_last = find_first(lambda s,r,v,c: r == 'GB_TILE_MODE31', idx_gb_addr_config_2)
idx_per_se_config = idx_gb_tile_last + 1

# RLC_CNTL = 0 (RLC halt, before RLC firmware load)
idx_rlc_halt = find_first(lambda s,r,v,c: r == 'RLC_CNTL' and v == '0x00000000' and s > 300000)

# RLC_GPM_UCODE_ADDR = 0 after RLC firmware load (RLC start)
# This is at file line 15070 (seq 333496)
idx_rlc_start = find_first(lambda s,r,v,c: r == 'RLC_GPM_UCODE_ADDR' and v == '0x00000000' and s > 333000)

# CP_ME_CNTL = halt (0x15000000)
idx_cp_halt = find_first(lambda s,r,v,c: r == 'CP_ME_CNTL' and v == '0x15000000')

# First REG_0xc168 = 0 (CP_PFP_UCODE_ADDR, PFP firmware load start)
idx_pfp_start = find_first(lambda s,r,v,c: r == 'REG_0xc168' and v == '0x00000000', idx_cp_halt)

# First REG_0xc15c = 0 (CP_CE_UCODE_ADDR, CE firmware load start)
idx_ce_start = find_first(lambda s,r,v,c: r == 'REG_0xc15c' and v == '0x00000000', idx_pfp_start)

# CP ring setup: starts with cleanup writes after CE firmware load
# Find the write to REG_0x85bc (first post-firmware register) - line 21520
idx_cp_ring_setup = find_first(lambda s,r,v,c: r == 'REG_0x85bc', idx_ce_start)

# CP_ME_CNTL = 0 (CP running)
idx_cp_running = find_first(lambda s,r,v,c: r == 'CP_ME_CNTL' and v == '0x00000000')

# SDMA ring setup (REG_0xd000 area, after CP rings)
idx_sdma_rings = find_first(lambda s,r,v,c: r == 'REG_0xd044', idx_cp_running)

# DPM/SMC init - SMC_IND_INDEX_0 after ring setup (seq > 440040)
idx_dpm_start = find_first(lambda s,r,v,c: r == 'SMC_IND_INDEX_0' and s > 440040)

# Post-DPM VM reconfigure (VM_CONTEXT0_CNTL second write, seq > 460000)
idx_post_dpm_vm = find_first(lambda s,r,v,c: r == 'VM_CONTEXT0_CNTL' and s > 460000)

# Final clock gating enable (RLC_CGCG_CGLS_CTRL, seq > 600000)
idx_final_cg = find_first(lambda s,r,v,c: r == 'RLC_CGCG_CGLS_CTRL' and s > 600000)

# Print landmarks for debugging
landmarks = {
    'idx_first': idx_first,
    'idx_atom_indirect': idx_atom_indirect,
    'idx_hdp_first': idx_hdp_first,
    'idx_dc_mc_init': idx_dc_mc_init,
    'idx_spll': idx_spll,
    'idx_post_spll': idx_post_spll,
    'idx_mc_vm_aperture': idx_mc_vm_aperture,
    'idx_vm_tlb': idx_vm_tlb,
    'idx_vm_invalidate_start': idx_vm_invalidate_start,
    'idx_sdma_setup': idx_sdma_setup,
    'idx_gb_addr_config_2': idx_gb_addr_config_2,
    'idx_per_se_config': idx_per_se_config,
    'idx_rlc_halt': idx_rlc_halt,
    'idx_rlc_start': idx_rlc_start,
    'idx_cp_halt': idx_cp_halt,
    'idx_pfp_start': idx_pfp_start,
    'idx_ce_start': idx_ce_start,
    'idx_cp_ring_setup': idx_cp_ring_setup,
    'idx_cp_running': idx_cp_running,
    'idx_sdma_rings': idx_sdma_rings,
    'idx_dpm_start': idx_dpm_start,
    'idx_post_dpm_vm': idx_post_dpm_vm,
    'idx_final_cg': idx_final_cg,
}

for name, val in landmarks.items():
    if val is not None:
        seq, reg, v, cat = writes[val]
        print(f"  {name:30s} = idx {val:>6d}  seq {seq:>8d}  {reg} = {v}", file=sys.stderr)
    else:
        print(f"  {name:30s} = NOT FOUND", file=sys.stderr)

# ---- Define phases ----
phases = []

def add_phase(name, start_idx, end_idx):
    """Add phase covering writes[start_idx:end_idx]"""
    if start_idx is None or end_idx is None:
        print(f"  WARNING: Skipping phase '{name}' - boundary not found", file=sys.stderr)
        return
    if start_idx >= end_idx:
        print(f"  WARNING: Skipping phase '{name}' - empty range [{start_idx}:{end_idx}]", file=sys.stderr)
        return
    phases.append((name, writes[start_idx:end_idx]))

add_phase("PHASE 1: Early SMC/SPLL Setup (First Writes)",
          idx_first, idx_atom_indirect)

add_phase("PHASE 2: ATOM BIOS Indirect Register Configuration",
          idx_atom_indirect, idx_hdp_first)

add_phase("PHASE 3: HDP Init + Early GPU Block Configuration",
          idx_hdp_first, idx_dc_mc_init)

add_phase("PHASE 4: Display Controller + Memory Controller Init (AtomBIOS AsicInit)",
          idx_dc_mc_init, idx_spll)

add_phase("PHASE 5: SPLL/PLL Clock Domain Setup",
          idx_spll, idx_post_spll)

add_phase("PHASE 6: GPU Block Configuration + Golden Registers (First Pass)",
          idx_post_spll, idx_mc_vm_aperture)

add_phase("PHASE 7: MC VM Aperture + MC Sequencer Training",
          idx_mc_vm_aperture, idx_vm_tlb)

add_phase("PHASE 8: VM/TLB Setup (L1, L2, GART Page Tables)",
          idx_vm_tlb, idx_vm_invalidate_start)

add_phase("PHASE 9: VM Invalidate + HDP Flush Cycles + MC Calibration",
          idx_vm_invalidate_start, idx_sdma_setup)

add_phase("PHASE 10: SDMA Engine Config + GRBM/BIF Setup",
          idx_sdma_setup, idx_gb_addr_config_2)

add_phase("PHASE 11: GB_ADDR_CONFIG Broadcast + GB_TILE_MODE[0..31] Programming",
          idx_gb_addr_config_2, idx_per_se_config)

add_phase("PHASE 12: Per-SE/SH Configuration + Golden Registers (Second Pass)",
          idx_per_se_config, idx_rlc_halt)

add_phase("PHASE 13: RLC Halt + GRBM Soft Reset + RLC Firmware Load",
          idx_rlc_halt, idx_rlc_start)

add_phase("PHASE 14: RLC Start + RLC Post-Init",
          idx_rlc_start, idx_cp_halt)

add_phase("PHASE 15a: CP Halt + CP ME Firmware Load",
          idx_cp_halt, idx_pfp_start)

add_phase("PHASE 15b: CP PFP Firmware Load",
          idx_pfp_start, idx_ce_start)

add_phase("PHASE 15c: CP CE Firmware Load",
          idx_ce_start, idx_cp_ring_setup)

add_phase("PHASE 16: CP Ring Buffer Setup + CP Start",
          idx_cp_ring_setup, idx_sdma_rings)

add_phase("PHASE 17: DMA/SDMA Ring Setup",
          idx_sdma_rings, idx_dpm_start)

add_phase("PHASE 18: DPM / Power Management Init (SMC + MC Arbitration)",
          idx_dpm_start, idx_post_dpm_vm)

add_phase("PHASE 19: Post-DPM VM Reconfigure + Clock Gating Enable",
          idx_post_dpm_vm, idx_final_cg)

add_phase("PHASE 20: Final Clock Gating + Display Engine Config + Steady-State Entry",
          idx_final_cg, N)

print(f"Defined {len(phases)} phases", file=sys.stderr)

# ---- Generate output ----
def format_write(seq, reg, val, cat):
    return f"  {seq:>8d}  WR {reg:<45s} = {val}  [{cat}]"

def summarize_bulk(phase_writes, i, data_reg, label):
    """Summarize a run of consecutive writes to data_reg. Returns (output_lines, new_i)."""
    lines = []
    count = 0
    j = i
    first_data = phase_writes[j][2]
    first_seq = phase_writes[j][0]
    while j < len(phase_writes) and phase_writes[j][1] == data_reg:
        count += 1
        j += 1
    last_data = phase_writes[j-1][2]
    last_seq = phase_writes[j-1][0]
    if count > 10:
        lines.append(f"  {first_seq:>8d}  WR {data_reg:<45s} = {first_data}  [{label}]  (first word)")
        lines.append(f"           ... {count} firmware data words written to {data_reg} ...")
        lines.append(f"  {last_seq:>8d}  WR {data_reg:<45s} = {last_data}  [{label}]  (last word)")
        return lines, j
    else:
        for k in range(i, j):
            lines.append(format_write(*phase_writes[k]))
        return lines, j

print("Generating output...", file=sys.stderr)

out = []
out.append("=" * 100)
out.append("AMDGPU (Southern Islands / SI) COMPLETE INIT SEQUENCE")
out.append("Extracted from mmiotrace: bus2_writes.txt")
out.append(f"Total register writes in trace: {N}")
out.append("Bus: [b2] (discrete GPU)")
out.append("")
out.append("Format: SEQ_NUM  WR  REGISTER_NAME                                  = VALUE       [CATEGORY]")
out.append("")
out.append("Notes:")
out.append("  - Sequence numbers may have gaps (reads between writes are not shown)")
out.append("  - Large sequence number gaps indicate driver polling/wait loops")
out.append("  - Firmware data bulk writes are summarized (exact word count noted)")
out.append("  - Register names are preserved EXACTLY as they appear in the trace")
out.append("  - REG_0xXXXX  = register at MMIO offset 0xXXXX (unnamed in trace)")
out.append("  - MC_0xXXXX   = memory controller register accessed via MC indirect port")
out.append("  - SMC_*       = System Management Controller registers")
out.append("=" * 100)
out.append("")

for phase_name, phase_writes in phases:
    out.append("")
    out.append("-" * 100)
    out.append(f"  {phase_name}")
    out.append(f"  Writes: {len(phase_writes)}  |  Seq range: {phase_writes[0][0]} .. {phase_writes[-1][0]}")
    out.append("-" * 100)
    out.append("")

    i = 0
    pw = phase_writes
    while i < len(pw):
        seq, reg, val, cat = pw[i]

        # --- RLC firmware addr/data pairs (REG_0xc32c addr, REG_0xc330 data) ---
        if reg == 'REG_0xc32c' and i + 1 < len(pw) and pw[i+1][1] == 'REG_0xc330':
            count = 0
            j = i
            first_addr = val
            first_data = pw[i+1][2]
            while j + 1 < len(pw) and pw[j][1] == 'REG_0xc32c' and pw[j+1][1] == 'REG_0xc330':
                count += 1
                j += 2
            if count > 10:
                last_addr = pw[j-2][2]
                last_data = pw[j-1][2]
                out.append(f"  {seq:>8d}  WR REG_0xc32c (RLC ucode addr)                  = {first_addr}  [RLC]  (first)")
                out.append(f"           WR REG_0xc330 (RLC ucode data)                  = {first_data}  [RLC]")
                out.append(f"           ... {count} RLC firmware addr/data pairs (REG_0xc32c/REG_0xc330) ...")
                out.append(f"  {pw[j-2][0]:>8d}  WR REG_0xc32c (RLC ucode addr)                  = {last_addr}  [RLC]  (last)")
                out.append(f"           WR REG_0xc330 (RLC ucode data)                  = {last_data}  [RLC]")
                i = j
                continue
            # else fall through to output individually

        # --- CP ME firmware: 0xc150 (WADDR) then bulk 0xc154 (DATA) ---
        if reg == 'REG_0xc150':
            out.append(format_write(seq, reg, val, cat) + "  # CP_ME_RAM_WADDR")
            i += 1
            if i < len(pw) and pw[i][1] == 'REG_0xc154':
                lines, i = summarize_bulk(pw, i, 'REG_0xc154', 'CP ME ucode')
                out.extend(lines)
            continue

        # --- CP PFP firmware: 0xc168 (ADDR) then bulk 0xc16c (DATA) ---
        if reg == 'REG_0xc168':
            out.append(format_write(seq, reg, val, cat) + "  # CP_PFP_UCODE_ADDR")
            i += 1
            if i < len(pw) and pw[i][1] == 'REG_0xc16c':
                lines, i = summarize_bulk(pw, i, 'REG_0xc16c', 'CP PFP ucode')
                out.extend(lines)
            continue

        # --- CP CE firmware: 0xc15c (ADDR) then bulk 0xc160 (DATA) ---
        if reg == 'REG_0xc15c':
            out.append(format_write(seq, reg, val, cat) + "  # CP_CE_UCODE_ADDR")
            i += 1
            if i < len(pw) and pw[i][1] == 'REG_0xc160':
                lines, i = summarize_bulk(pw, i, 'REG_0xc160', 'CP CE ucode')
                out.extend(lines)
            continue

        # --- Standalone bulk 0xc154, 0xc16c, 0xc160 runs (shouldn't normally happen) ---
        if reg in ('REG_0xc154', 'REG_0xc16c', 'REG_0xc160'):
            label_map = {
                'REG_0xc154': 'CP ME ucode',
                'REG_0xc16c': 'CP PFP ucode',
                'REG_0xc160': 'CP CE ucode',
            }
            lines, i = summarize_bulk(pw, i, reg, label_map[reg])
            out.extend(lines)
            continue

        # --- HDP flush + VM invalidate pairs (can be repetitive) ---
        if reg == 'HDP_MEM_COHERENCY_FLUSH_CNTL' and i + 1 < len(pw) and pw[i+1][1] == 'VM_INVALIDATE_REQUEST':
            # Count consecutive pairs
            j = i
            count = 0
            while j + 1 < len(pw) and pw[j][1] == 'HDP_MEM_COHERENCY_FLUSH_CNTL' and pw[j+1][1] == 'VM_INVALIDATE_REQUEST':
                count += 1
                j += 2
            if count > 4:
                out.append(f"  {seq:>8d}  WR HDP_MEM_COHERENCY_FLUSH_CNTL                  = {val}  [HDP]")
                out.append(f"           WR VM_INVALIDATE_REQUEST                       = {pw[i+1][2]}  [VM/TLB]")
                out.append(f"           ... {count} HDP_FLUSH + VM_INVALIDATE pairs (seq {seq}..{pw[j-1][0]}) ...")
                out.append(f"  {pw[j-2][0]:>8d}  WR HDP_MEM_COHERENCY_FLUSH_CNTL                  = {pw[j-2][2]}  [HDP]  (last)")
                out.append(f"           WR VM_INVALIDATE_REQUEST                       = {pw[j-1][2]}  [VM/TLB]")
                i = j
                continue

        # --- MC indirect register pairs (MC_0x2a44 addr / MC_0x2a48 data) ---
        # These are common during MC training but we list each one individually
        # (they carry different address/data values, so each is meaningful)

        # --- Regular write ---
        out.append(format_write(seq, reg, val, cat))
        i += 1

# ---- Phase Summary ----
out.append("")
out.append("")
out.append("=" * 100)
out.append("PHASE SUMMARY")
out.append("=" * 100)
out.append("")
total = 0
for phase_name, phase_writes in phases:
    n = len(phase_writes)
    total += n
    out.append(f"  {phase_name}")
    out.append(f"    Writes: {n:>6d}  |  Seq: {phase_writes[0][0]:>8d} .. {phase_writes[-1][0]:>8d}")
    out.append("")

out.append(f"TOTAL WRITES IN INIT SEQUENCE: {total}")
out.append("=" * 100)

# ---- Write output ----
with open(OUTPUT, 'w') as f:
    f.write('\n'.join(out) + '\n')

print(f"Written to {OUTPUT}", file=sys.stderr)
print(f"Total output lines: {len(out)}", file=sys.stderr)
