#!/usr/bin/env python3
# extract_rlc_content.py — §34 thread (b): generate the memory-side content the
# kernel writes via CPU->VRAM / GTT, which BAR0 mmiotrace cannot capture.
#
# Sources (reference model, /home/bob/linux = 6.18 tree; amdgpu gfx_v6_0.c is
# the direct port of the radeon si.c code that produced the Jun 19 trace):
#   - verde_rlc_save_restore_register_list  (gfx_v6_0.c)
#   - si_cs_data / si_SECT_CONTEXT_def_*    (clearstate_si.h)
#   - gfx_v6_0_rlc_init: CSB = 256-byte descriptor header + get_csb_buffer()
#   - gfx_v6_0_cp_gfx_start: ring default-state PM4 stream (RB0 dw 0x100..)
#
# Trace anchors (fw_trace/FULL_REPLAY_A2.txt):
#   seq 329387  WR 0xC330 = 0xF4002010  -> SR  content at VRAM offset 0x201000
#   seq 329388  WR 0xC320 = 0xF4002020  -> CSB content at VRAM offset 0x202000
#   seq 329324  WR 0x28350 = 0x00001240 -> PA_SC_RASTER_CONFIG working value
#
# Outputs (LE dwords):
#   RLC_SR_CONTENT.bin   save/restore register list (kernel copies it verbatim)
#   RLC_CSB_CONTENT.bin  64-dword header (hi/lo of base+256, size) + CSB stream
#   RB0_DEFAULT_STATE.bin ring stream for RB0 dwords 0x100..0x100+len (pad rest)
import re, struct, sys

KSRC = "/home/bob/linux/drivers/gpu/drm/amd/amdgpu"
CSB_GPU_ADDR   = 0xF400202000          # 0xF4002020 << 8 (trace value)
RASTER_CONFIG  = 0x1240                # trace seq 329324
PA_SC_RASTER_CONFIG_DW = 0x28350 // 4  # 0xA0D4
SET_CONTEXT_REG_START  = 0xA000

def packet3(op, n): return (0x3 << 30) | ((n & 0x3FFF) << 16) | ((op & 0xFF) << 8)
OP_CLEAR_STATE, OP_CONTEXT_CONTROL, OP_PREAMBLE_CNTL, OP_SET_CONTEXT_REG = 0x12, 0x28, 0x4A, 0x69
PREAMBLE_BEGIN, PREAMBLE_END = 2 << 28, 3 << 28

def read(path):
    with open(path) as f: return f.read()

def parse_u32_array(text, name):
    m = re.search(r"static const u32 %s\[\]\s*=\s*\{(.*?)\};" % name, text, re.S)
    if not m: sys.exit("array %s not found" % name)
    vals = []
    for line in m.group(1).splitlines():
        line = line.split("//")[0].strip().rstrip(",")
        if not line: continue
        vals.append(eval(line.replace("0X", "0x")))  # forms: 0x..., (a<<16)|(b>>2)
    return vals

# ---- SR list ----
gfx = read(KSRC + "/gfx_v6_0.c")
sr = parse_u32_array(gfx, "verde_rlc_save_restore_register_list")

# ---- clear state extents ----
cs = read(KSRC + "/clearstate_si.h")
defs = {n: parse_u32_array(cs, "si_SECT_CONTEXT_def_%s" % n) for n in "1234567"}
ext_m = re.findall(r"\{si_SECT_CONTEXT_def_(\d),\s*(0x[0-9a-fA-F]+),\s*(\d+)\s*\}", cs)
extents = [(defs[d], int(idx, 16), int(cnt)) for d, idx, cnt in ext_m]
for arr, idx, cnt in extents:
    assert len(arr) == cnt, "extent %x: array %d != count %d" % (idx, len(arr), cnt)

def emit_extents(out):
    for arr, idx, cnt in extents:
        out.append(packet3(OP_SET_CONTEXT_REG, cnt))
        out.append(idx - SET_CONTEXT_REG_START)
        out.extend(arr)

# ---- CSB stream (gfx_v6_0_get_csb_buffer) ----
csb = [packet3(OP_PREAMBLE_CNTL, 0), PREAMBLE_BEGIN,
       packet3(OP_CONTEXT_CONTROL, 1), 0x80000000, 0x80000000]
emit_extents(csb)
csb += [packet3(OP_SET_CONTEXT_REG, 1), PA_SC_RASTER_CONFIG_DW - SET_CONTEXT_REG_START, RASTER_CONFIG]
csb += [packet3(OP_PREAMBLE_CNTL, 0), PREAMBLE_END, packet3(OP_CLEAR_STATE, 0), 0]

# ---- CSB descriptor header (gfx_v6_0_rlc_init) ----
hdr = [0] * 64
hdr[0] = (CSB_GPU_ADDR + 256) >> 32
hdr[1] = (CSB_GPU_ADDR + 256) & 0xFFFFFFFF
hdr[2] = len(csb)

# ---- ring default-state stream (gfx_v6_0_cp_gfx_start, post-SET_BASE part) ----
ring = [packet3(OP_PREAMBLE_CNTL, 0), PREAMBLE_BEGIN]
emit_extents(ring)
ring += [packet3(OP_PREAMBLE_CNTL, 0), PREAMBLE_END, packet3(OP_CLEAR_STATE, 0), 0,
         packet3(OP_SET_CONTEXT_REG, 2), 0x316, 0xE, 0x10]

def dump(path, dwords):
    with open(path, "wb") as f: f.write(struct.pack("<%dI" % len(dwords), *dwords))
    with open(path.replace(".bin", ".txt"), "w") as f:
        for i, d in enumerate(dwords): f.write("%5d 0x%08X\n" % (i, d))
    print("%s: %d dwords (%d bytes)" % (path, len(dwords), len(dwords) * 4))

dump("RLC_SR_CONTENT.bin", sr)
dump("RLC_CSB_CONTENT.bin", hdr + csb)
dump("RB0_DEFAULT_STATE.bin", ring)
print("SR entries=%d, CSB stream=%d (expect 908), ring stream=%d (expect 906, fits 0x100..0x500=%s)"
      % (len(sr), len(csb), len(ring), len(ring) <= 1024))
assert len(csb) == 908 and len(ring) == 906 and len(ring) <= 1024
