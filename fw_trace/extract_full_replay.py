#!/usr/bin/env python3
# extract_full_replay.py — §30: extract the ENTIRE kernel init (bus2_all.txt)
# into a verbatim replay table with READ ORACLES.
#
# Rationale (handoff §29/§30): 17 cold-reboot iterations of selective window
# diffing never moved RPTR past ~60, and twice the instrumentation itself was
# wrong. The trace contains ~49k writes AND ~310k reads with the values the
# working hardware returned. This extractor emits ALL of it:
#   - every WR as a replay record (verbatim value)
#   - every isolated RD as an ORACLE (replay compares our readback vs kernel's)
#   - >=3 consecutive RDs of one reg compressed to a POLL (spin until value
#     matches kernel's final read; timeout -> log last value, continue)
#
# Window A: seq 0..439996 = power-on ATOM init, MC train, golden regs, VM/GART,
# RLC fw+start, CP fw, ring 0/1/2 setup, unhalt, kernel ring scratch tests.
# If the replayed scratch test lands (SCRATCH_REG0: CAFEDEAD -> DEADBEEF via
# ring packet... note: the DEADBEEF lands via CP execution, so oracle @439972
# passing == ME EXECUTES), cold init is solved.
#
# Record format (12 bytes LE): op u32, addr u32, val u32
#   op 1 = REG_WR      MMIO write addr=val (indirect ports replayed raw:
#                      SMC_IND_INDEX/DATA, MC seq ports are just registers)
#   op 4 = RD_ORACLE   read addr once; mismatch vs val -> log, continue
#   op 5 = POLL        read addr until == val; 2M reads max; timeout -> log
#   op 6 = SKIP_NOTE   addr=offset val=count — forbidden reg skipped (marker)
#
# Skips (each emitted as op 6 + listed in report):
#   HDP_HOST_PATH_CNTL 0x2C00, HDP_MISC_CNTL 0x2F4C (gpu-crash.md RULE 1 —
#   deadlock RD990 from CPU side).
# Address-bearing regs are NOT skipped: kernel layout is ADOPTED (GART VA
# 0xFF00000000 rebase — GARTConf change, handoff §30). PTE contents + host
# allocations remain ours; every register value replays verbatim.
import re, struct, sys
from collections import Counter

TRACE = sys.argv[1] if len(sys.argv) > 1 else "../bus2_all.txt"
WIN_END = int(sys.argv[2]) if len(sys.argv) > 2 else 439996

NAMED = {
    'GRBM_CNTL': 0x8000, 'GRBM_STATUS': 0x8010, 'GRBM_SOFT_RESET': 0x8020,
    'GRBM_GFX_INDEX': 0x802C,
    'CP_RB0_CNTL': 0xC104, 'CP_RB0_BASE': 0xC100, 'CP_RB0_RPTR_ADDR': 0xC10C,
    'CP_RB0_RPTR_ADDR_HI': 0xC110, 'CP_RB0_WPTR': 0xC114,
    'CP_RB1_CNTL': 0xC184, 'CP_RB1_BASE': 0xC180, 'CP_RB1_RPTR_ADDR': 0xC188,
    'CP_RB1_RPTR_ADDR_HI': 0xC18C, 'CP_RB1_WPTR': 0xC190,
    'CP_RB2_CNTL': 0xC198, 'CP_RB2_BASE': 0xC194, 'CP_RB2_RPTR_ADDR': 0xC19C,
    'CP_RB2_RPTR_ADDR_HI': 0xC1A0, 'CP_RB2_WPTR': 0xC1A4,
    'CP_ME_CNTL': 0x86D8,
    'MC_VM_FB_LOCATION': 0x2024,
    'MC_VM_AGP_TOP': 0x2028, 'MC_VM_AGP_BOT': 0x202C, 'MC_VM_AGP_BASE': 0x2030,
    'MC_VM_SYSTEM_APERTURE_LOW_ADDR': 0x2034,
    'MC_VM_SYSTEM_APERTURE_HIGH_ADDR': 0x2038,
    'MC_VM_SYSTEM_APERTURE_DEFAULT_ADDR': 0x203C,
    'MC_VM_MX_L1_TLB_CNTL': 0x2064,
    'VM_L2_CNTL': 0x1400, 'VM_L2_CNTL2': 0x1404, 'VM_L2_CNTL3': 0x1408,
    'VM_CONTEXT0_CNTL': 0x1410, 'VM_CONTEXT0_CNTL2': 0x1430,
    'VM_CONTEXT1_CNTL': 0x1414, 'VM_CONTEXT1_CNTL2': 0x1434,
    'VM_CONTEXT0_PAGE_TABLE_BASE_ADDR': 0x153C,
    'VM_CONTEXT1_PAGE_TABLE_BASE_ADDR': 0x1540,
    'VM_CONTEXT0_PAGE_TABLE_START_ADDR': 0x1440,
    'VM_CONTEXT1_PAGE_TABLE_START_ADDR': 0x1444,
    'VM_INVALIDATE_REQUEST': 0x1478,
    'HDP_MEM_COHERENCY_FLUSH_CNTL': 0x5480,
    'HDP_HOST_PATH_CNTL': 0x2C00, 'HDP_MISC_CNTL': 0x2F4C,
    'HDP_ADDR_CONFIG': 0x2F48, 'HDP_NONSURFACE_BASE': 0x2C04,
    'VGA_HDP_CONTROL': 0x0328, 'VGA_RENDER_CONTROL': 0x0300,
    'RLC_CNTL': 0xC300, 'RLC_SAVE_AND_RESTORE_BASE': 0xC310,
    'RLC_GPM_UCODE_ADDR': 0xC32C, 'RLC_GPM_UCODE_DATA': 0xC330,
    'RLC_CGCG_CGLS_CTRL': 0xC404, 'RLC_CGTT_MGCG_OVERRIDE': 0xC400,
    'GB_ADDR_CONFIG': 0x98F8, 'DMIF_ADDR_CONFIG': 0x0BD4,
    'DMIF_ADDR_CALC': 0x0C00, 'DMA_TILING_CONFIG': 0xD0B8,
    'SX_DEBUG_1': 0x9060, 'SPI_CONFIG_CNTL_1': 0x913C,
    'SPI_CONFIG_CNTL': 0x9100,
    'SQ_CONFIG': 0x8C00, 'PA_SC_RASTER_CONFIG': 0x28350,
    'BIF_FB_EN': 0x5490, 'SCRATCH_UMSK': 0x8540, 'SCRATCH_REG0': 0x8500,
    'MC_SEQ_SUP_CNTL': 0x28C8,
    'HDP_NONSURFACE_INFO': 0x2C08, 'HDP_NONSURFACE_SIZE': 0x2C0C,
    'IH_RB_CNTL': 0x3E00, 'IH_RB_BASE': 0x3E04, 'IH_RB_RPTR': 0x3E08,
    'IH_RB_WPTR': 0x3E0C, 'IH_RPTR_ADDR_HI': 0x3E10,
    'IH_RPTR_ADDR_LO': 0x3E14, 'IH_CNTL': 0x3E18,
    'INTERRUPT_CNTL': 0x5468, 'INTERRUPT_CNTL2': 0x546C,
    'IH_RB_WPTR_ADDR_LO': 0x3E20, 'IH_RB_WPTR_ADDR_HI': 0x3E24,
    'CG_SPLL_FUNC_CNTL': 0x600, 'CG_SPLL_FUNC_CNTL_2': 0x604,
    'CG_SPLL_FUNC_CNTL_3': 0x608, 'CG_SPLL_FUNC_CNTL_4': 0x60C,
    'CG_SPLL_SPREAD_SPECTRUM': 0x610, 'CG_SPLL_SPREAD_SPECTRUM_2': 0x614,
    'CGTS_SM_CTRL_REG': 0x9150,
    'CONFIG_MEMSIZE': 0x5428,
    'MC_ARB_RAMCFG': 0x2760, 'MC_SEQ_MISC0': 0x2A00,
    'MC_SEQ_TRAIN_WAKEUP_CNTL': 0x28E8,
    'MC_SHARED_BLACKOUT_CNTL': 0x20AC, 'MC_SHARED_CHMAP': 0x2004,
    'SMC_IND_INDEX_0': 0x200, 'SMC_IND_DATA_0': 0x204, 'SMC_MSG_ARG': 0x884,
    'SRBM_STATUS': 0x0E50,
    'TA_CNTL_AUX': 0x9508,
    'TCP_ADDR_CONFIG': 0xAC14,   # verified vs gpu_probe_fullstate.py
    'TCP_CHAN_STEER_HI': 0xAC10, 'TCP_CHAN_STEER_LO': 0xAC0C,  # verified vs gpu_probe_fullstate.py
    'D2_CRTC_CONTROL': 0x6980,   # UNVERIFIED — only used at seq 670146 (window B); verify before extracting B
}
for i in range(32):
    NAMED[f'GB_TILE_MODE{i}'] = 0x9910 + i * 4

FORBIDDEN = {0x2C00, 0x2F4C}

rx = re.compile(r'^\s*(\d+)\s+\[b2\]\s+(RD|WR)\s+(\S+)\s+=\s+0x([0-9A-Fa-f]+)')
prot = re.compile(r'HDP_PROT_BUF(\d+)\+0x([0-9a-fA-F]+)')

def off_of(name):
    if name in NAMED: return NAMED[name]
    m = re.match(r'(?:REG|MC)_0x([0-9A-Fa-f]+)$', name)
    if m: return int(m.group(1), 16)
    m = prot.match(name)
    if m: return 0x2C14 + int(m.group(1)) * 0x18 + int(m.group(2), 16)
    return None

events = []           # (seq, op, off, val, name)
unknown = Counter()
for line in open(TRACE):
    m = rx.match(line)
    if not m: continue
    seq = int(m.group(1))
    if seq > WIN_END: break
    op, name, val = m.group(2), m.group(3), int(m.group(4), 16)
    off = off_of(name)
    if off is None:
        unknown[name] += 1
        continue
    events.append((seq, op, off, val, name))

# compress read runs + classify
records = []          # (op, off, val, seq)
skipped = Counter()
i = 0
n_wr = n_oracle = n_poll = 0
while i < len(events):
    seq, op, off, val, name = events[i]
    if op == 'WR':
        if off in FORBIDDEN:
            skipped[name] += 1
            records.append((6, off, val, seq))
        else:
            records.append((1, off, val, seq)); n_wr += 1
        i += 1
        continue
    # RD: count run of same reg
    j = i
    while j < len(events) and events[j][1] == 'RD' and events[j][2] == off:
        j += 1
    run = j - i
    final_val = events[j-1][3]
    if run >= 3:
        records.append((5, off, final_val, seq)); n_poll += 1
    else:
        for k in range(i, j):
            records.append((4, off, events[k][3], events[k][0])); n_oracle += 1
    i = j

# 16-byte records v2: op, addr, val, seq (seq = kernel trace seq for divergence
# reporting). Split at seq 12088 (first VM_CONTEXT reg): A1 = ATOM/MC/golden
# (before GART table exists), A2 = VM config .. CP scratch tests. The harness
# fills GART PTEs + ring content between the two.
SPLIT = 12088
for name, sel in (('FULL_REPLAY_A1', lambda s: s < SPLIT),
                  ('FULL_REPLAY_A2', lambda s: s >= SPLIT)):
    part = [r for r in records if sel(r[3])]
    with open(name + '.bin', 'wb') as f:
        for op, off, val, seq in part:
            f.write(struct.pack('<IIII', op, off, val, seq))
    with open(name + '.txt', 'w') as f:
        for op, off, val, seq in part:
            opn = {1:'WR',4:'ORACLE',5:'POLL',6:'SKIP'}[op]
            f.write(f'{seq:8d} {opn:6s} 0x{off:05X} = 0x{val:08X}\n')
    print(f'{name}: {len(part)} records, {len(part)*16} bytes')

print(f'events parsed: {len(events)} (window 0..{WIN_END})')
print(f'records: {len(records)}  WR={n_wr} ORACLE={n_oracle} POLL={n_poll} SKIP={sum(skipped.values())}')
print(f'binary: {len(records)*12} bytes')
if skipped:
    print('skipped (forbidden):', dict(skipped))
if unknown:
    print('UNMAPPED NAMES (must fix before trusting the table):')
    for n, c in unknown.most_common(): print(f'  {n} x{c}')
