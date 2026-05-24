#!/usr/bin/env python3
"""
gen_gcn_enc.py — Generate Library.GCNEnc.ailang from gcn1_isa.json

Design v2: O(1) lookup via FixedPool.GCN integer constants.
  - Every instruction mnemonic becomes a FixedPool entry with its packed descriptor.
  - Usage:  desc = GCN.V_MUL_LO_U32   (single memory load, zero search)
  - All emit functions use ≤6 arguments (SystemV ABI register-only).
  - Modifier/flag fields packed into single integer args.

Generated output structure:
  FixedPool.GCNEnc      — encoding format + group constants
  FixedPool.GCN         — all 528 instruction descriptors as named constants
  FixedPool.GCNEncState — assembler state (desc, word0, word1)
  Function.GCNEnc_Opcode/EncFmt/Group/Is64Bit/NumOps — descriptor extractors
  Function.GCNEnc_RegNum     — register name → encoding number
  Function.GCNEnc_Emit_SOP2  — emit SOP2 instruction (4 args)
  Function.GCNEnc_Emit_SOP1  — emit SOP1 instruction (3 args)
  ... (one per encoding format, all ≤6 args)
  Convenience wrappers (S_ENDPGM, S_WAITCNT, etc.)

Descriptor word layout (per instruction):
  bits  0- 8   opcode (up to 9 bits for VOP3)
  bits  9-12   encoding format ID (0-13)
  bits 13-15   functional group (SALU=0,VALU=1,SMEM=2,VMEM=3,LDS=4,FLOW=5,SYNC=6,EXPORT=7)
  bit     16   is_64bit_encoding (0=32-bit, 1=64-bit)
  bits 17-19   num_explicit_operands (0-7)
  bits 20-31   reserved

Packed modifier layouts (for emit functions with >6 logical operands):
  VOP3 mods:   clamp[0] | abs[3:1] | neg[6:4] | omod[8:7]
  MUBUF flags: offset[11:0] | offen[12] | idxen[13] | glc[14] | addr64[15] | slc[22]
  DS offsets:  offset0[7:0] | offset1[15:8] | gds[16]
  EXP flags:   en[3:0] | compr[4] | done[5] | vm[6]
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ISA_JSON = os.path.join(SCRIPT_DIR, "gcn1_isa.json")
OUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR),
                       "Librarys", "Drivers", "AMDGPU")

# Encoding format IDs (must match FixedPool.GCNEnc)
ENC_IDS = {
    "SOP2":  0,
    "SOPK":  1,
    "SOP1":  2,
    "SOPC":  3,
    "SOPP":  4,
    "SMRD":  5,
    "VOP2":  6,
    "VOP1":  7,
    "VOPC":  8,
    "VOP3":  9,
    "MUBUF": 10,
    "MTBUF": 11,
    "DS":    12,
    "EXP":   13,
}

# 64-bit encodings
ENC_64BIT = {"VOP3", "MUBUF", "MTBUF", "DS", "EXP"}

# Functional group IDs
GROUP_IDS = {
    "SALU":   0,
    "VALU":   1,
    "SMEM":   2,
    "VMEM":   3,
    "LDS":    4,
    "FLOW":   5,
    "SYNC":   6,
    "EXPORT": 7,
    "SOPP":   5,   # map SOPP to FLOW by default
    "OTHER":  0,
}


def pack_descriptor(instr):
    """Pack instruction info into a single integer descriptor."""
    enc = instr["encoding"]
    opcode = instr["opcode"] & 0x1FF
    enc_id = ENC_IDS.get(enc, 0) & 0xF
    grp = GROUP_IDS.get(instr.get("functional_group", "OTHER"), 0) & 0x7
    is_64 = 1 if enc in ENC_64BIT else 0
    n_ops = min(len([o for o in instr.get("operands", [])
                     if not o.get("implicit", False)]), 7)

    desc = opcode
    desc |= enc_id << 9
    desc |= grp << 13
    desc |= is_64 << 16
    desc |= n_ops << 17
    return desc


def gen(out_path):
    """Main generator."""
    with open(ISA_JSON) as f:
        isa = json.load(f)

    instructions = isa["instructions"]

    # Build lookup entries: (mnemonic, descriptor)
    all_entries = []
    for instr in instructions:
        desc = pack_descriptor(instr)
        all_entries.append((instr["name"], desc))

    # Deduplicate (same mnemonic can appear if we have VOP2+VOP3 forms etc.)
    seen = {}
    deduped = []
    for mnem, desc in all_entries:
        if mnem not in seen:
            seen[mnem] = desc
            deduped.append((mnem, desc))
    all_entries = deduped

    print(f"Total entries: {len(all_entries)}", file=sys.stderr)

    lines = []
    W = lines.append

    W("// Library.GCNEnc.ailang")
    W("// Auto-generated from gcn1_isa.json (LLVM AMDGPU TableGen)")
    W("// GCN 1.0 (Southern Islands / gfx600-gfx602) instruction encoder.")
    W("// Zero external dependencies — DO NOT EDIT.")
    W("// Run tools/gen_gcn_enc.py to regenerate.")
    W(f"// {len(all_entries)} instructions, 14 encoding formats")
    W("//")
    W("// Lookup: O(1) via FixedPool.GCN integer constants.")
    W("//   desc = GCN.V_MUL_LO_U32    // single memory load")
    W("//   op   = GCNEnc_Opcode(desc)  // extract opcode field")
    W("//")
    W("// All emit functions use ≤6 arguments (SystemV ABI safe).")
    W("// Modifier fields packed into single integers:")
    W("//   VOP3 mods:   clamp[0] | abs[3:1] | neg[6:4] | omod[8:7]")
    W("//   MUBUF flags: offset[11:0] | offen[12] | idxen[13] | glc[14] | addr64[15] | slc[22]")
    W("//   DS offsets:  offset0[7:0] | offset1[15:8] | gds[16]")
    W("//   EXP flags:   en[3:0] | compr[4] | done[5] | vm[6]")
    W("")

    # =========================================================================
    # Encoding format + group constants
    # =========================================================================
    W("FixedPool.GCNEnc {")
    for enc_name, enc_id in sorted(ENC_IDS.items(), key=lambda x: x[1]):
        W(f'    "ENC_{enc_name}": Initialize={enc_id}, CanChange=False')
    W('    "GRP_SALU":   Initialize=0, CanChange=False')
    W('    "GRP_VALU":   Initialize=1, CanChange=False')
    W('    "GRP_SMEM":   Initialize=2, CanChange=False')
    W('    "GRP_VMEM":   Initialize=3, CanChange=False')
    W('    "GRP_LDS":    Initialize=4, CanChange=False')
    W('    "GRP_FLOW":   Initialize=5, CanChange=False')
    W('    "GRP_SYNC":   Initialize=6, CanChange=False')
    W('    "GRP_EXPORT": Initialize=7, CanChange=False')
    W("}")
    W("")

    # =========================================================================
    # Instruction descriptor constants — O(1) lookup
    # =========================================================================
    W("// FixedPool.GCN — every instruction mnemonic → packed descriptor")
    W("// Usage: desc = GCN.S_ADD_U32")
    W("//        op   = GCNEnc_Opcode(desc)   // → 0")
    W("//        enc  = GCNEnc_EncFmt(desc)    // → 0 (SOP2)")
    W("FixedPool.GCN {")
    for mnem, desc in sorted(all_entries, key=lambda x: x[0]):
        W(f'    "{mnem}": Initialize={desc}, CanChange=False')
    W("}")
    W("")

    # =========================================================================
    # Encoding bit layout comments
    # =========================================================================
    W("// Encoding identifier bits (top bits of first DWORD)")
    W("// SOP2:  [31:30] = 10")
    W("// SOPK:  [31:28] = 1011")
    W("// SOP1:  [31:23] = 101111101")
    W("// SOPC:  [31:23] = 101111110")
    W("// SOPP:  [31:23] = 101111111")
    W("// SMRD:  [31:27] = 11000")
    W("// VOP2:  [31]    = 0, [30:25] != 0x3F/0x3E")
    W("// VOP1:  [31:25] = 0111111")
    W("// VOPC:  [31:25] = 0111110")
    W("// VOP3:  [31:26] = 110100")
    W("// MUBUF: [31:26] = 111000")
    W("// MTBUF: [31:26] = 111010")
    W("// DS:    [31:26] = 110110")
    W("// EXP:   [31:26] = 110001")
    W("")

    # =========================================================================
    # Assembler state
    # =========================================================================
    W("FixedPool.GCNEncState {")
    W('    "desc":   Initialize=0, CanChange=True')
    W('    "word0":  Initialize=0, CanChange=True')
    W('    "word1":  Initialize=0, CanChange=True')
    W("}")
    W("")

    # =========================================================================
    # Descriptor field extractors
    # =========================================================================
    W("Function.GCNEnc_Opcode {")
    W("    Input: desc: Integer")
    W("    Output: Integer")
    W("    Body: { ReturnValue(BitwiseAnd(desc, 511)) }")
    W("}")
    W("")
    W("Function.GCNEnc_EncFmt {")
    W("    Input: desc: Integer")
    W("    Output: Integer")
    W("    Body: { ReturnValue(BitwiseAnd(RightShift(desc, 9), 15)) }")
    W("}")
    W("")
    W("Function.GCNEnc_Group {")
    W("    Input: desc: Integer")
    W("    Output: Integer")
    W("    Body: { ReturnValue(BitwiseAnd(RightShift(desc, 13), 7)) }")
    W("}")
    W("")
    W("Function.GCNEnc_Is64Bit {")
    W("    Input: desc: Integer")
    W("    Output: Integer")
    W("    Body: { ReturnValue(BitwiseAnd(RightShift(desc, 16), 1)) }")
    W("}")
    W("")
    W("Function.GCNEnc_NumOps {")
    W("    Input: desc: Integer")
    W("    Output: Integer")
    W("    Body: { ReturnValue(BitwiseAnd(RightShift(desc, 17), 7)) }")
    W("}")
    W("")

    # =========================================================================
    # Register name lookup (still string-based — register names are user input)
    # =========================================================================
    W("// GCNEnc_RegNum: register name → encoding number")
    W("// v0-v255 → 256-511, s0-s103 → 0-103")
    W("// Special: vcc_lo=106, vcc_hi=107, exec_lo=126, exec_hi=127, m0=124")
    W("// Inline constants: 0=128, 1-64=129-192, -1-(-16)=193-208")
    W("// 0.5=240, -0.5=241, 1.0=242, -1.0=243, 2.0=244, -2.0=245, 4.0=246, -4.0=247")
    W("// literal=255")
    W("Function.GCNEnc_RegNum {")
    W("    Input: name: Address")
    W("    Output: Integer")
    W("    Body: {")
    # Special registers
    for sname, sval in [("vcc_lo", 106), ("vcc_hi", 107), ("vcc", 106),
                        ("exec_lo", 126), ("exec_hi", 127), ("exec", 126),
                        ("m0", 124), ("scc", 253), ("literal", 255),
                        ("null", 125)]:
        W(f'        IfCondition EqualTo(StringCompare(name, "{sname}"), 0) ThenBlock: {{ ReturnValue({sval}) }}')
    # SGPRs s0-s103
    for i in range(104):
        W(f'        IfCondition EqualTo(StringCompare(name, "s{i}"), 0) ThenBlock: {{ ReturnValue({i}) }}')
    # VGPRs v0-v255
    for i in range(256):
        W(f'        IfCondition EqualTo(StringCompare(name, "v{i}"), 0) ThenBlock: {{ ReturnValue({256 + i}) }}')
    W("        ReturnValue(-1)")
    W("    }")
    W("}")
    W("")

    # =========================================================================
    # Emit functions — one per encoding format, ALL ≤6 args
    # =========================================================================

    # --- SOP2: ENCODING[31:30]=10 OP[29:23] SDST[22:16] SSRC1[15:8] SSRC0[7:0]
    # 4 args: op, sdst, ssrc0, ssrc1
    W("Function.GCNEnc_Emit_SOP2 {")
    W("    Input: op: Integer")
    W("    Input: sdst: Integer")
    W("    Input: ssrc0: Integer")
    W("    Input: ssrc1: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        w = ssrc0")
    W("        w = BitwiseOr(w, LeftShift(ssrc1, 8))")
    W("        w = BitwiseOr(w, LeftShift(sdst, 16))")
    W("        w = BitwiseOr(w, LeftShift(op, 23))")
    W("        w = BitwiseOr(w, LeftShift(2, 30))")
    W("        GCNEncState.word0 = w")
    W("        ReturnValue(4)")
    W("    }")
    W("}")
    W("")

    # --- SOP1: ENCODING[31:23]=0x17D OP[15:8] SDST[22:16] SSRC0[7:0]
    # 3 args: op, sdst, ssrc0
    W("Function.GCNEnc_Emit_SOP1 {")
    W("    Input: op: Integer")
    W("    Input: sdst: Integer")
    W("    Input: ssrc0: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        w = ssrc0")
    W("        w = BitwiseOr(w, LeftShift(op, 8))")
    W("        w = BitwiseOr(w, LeftShift(sdst, 16))")
    W("        w = BitwiseOr(w, LeftShift(381, 23))")  # 0x17D
    W("        GCNEncState.word0 = w")
    W("        ReturnValue(4)")
    W("    }")
    W("}")
    W("")

    # --- SOPC: ENCODING[31:23]=0x17E OP[22:16] SSRC1[15:8] SSRC0[7:0]
    # 3 args: op, ssrc0, ssrc1
    W("Function.GCNEnc_Emit_SOPC {")
    W("    Input: op: Integer")
    W("    Input: ssrc0: Integer")
    W("    Input: ssrc1: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        w = ssrc0")
    W("        w = BitwiseOr(w, LeftShift(ssrc1, 8))")
    W("        w = BitwiseOr(w, LeftShift(op, 16))")
    W("        w = BitwiseOr(w, LeftShift(382, 23))")  # 0x17E
    W("        GCNEncState.word0 = w")
    W("        ReturnValue(4)")
    W("    }")
    W("}")
    W("")

    # --- SOPK: ENCODING[31:28]=0xB SDST[22:16] OP[27:23] SIMM16[15:0]
    # 3 args: op, sdst, simm16
    W("Function.GCNEnc_Emit_SOPK {")
    W("    Input: op: Integer")
    W("    Input: sdst: Integer")
    W("    Input: simm16: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        w = BitwiseAnd(simm16, 65535)")
    W("        w = BitwiseOr(w, LeftShift(sdst, 16))")
    W("        w = BitwiseOr(w, LeftShift(op, 23))")
    W("        w = BitwiseOr(w, LeftShift(11, 28))")  # 1011
    W("        GCNEncState.word0 = w")
    W("        ReturnValue(4)")
    W("    }")
    W("}")
    W("")

    # --- SOPP: ENCODING[31:23]=0x17F OP[22:16] SIMM16[15:0]
    # 2 args: op, simm16
    W("Function.GCNEnc_Emit_SOPP {")
    W("    Input: op: Integer")
    W("    Input: simm16: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        w = BitwiseAnd(simm16, 65535)")
    W("        w = BitwiseOr(w, LeftShift(op, 16))")
    W("        w = BitwiseOr(w, LeftShift(383, 23))")  # 0x17F
    W("        GCNEncState.word0 = w")
    W("        ReturnValue(4)")
    W("    }")
    W("}")
    W("")

    # --- SMRD: ENCODING[31:27]=0x18 OP[26:22] SDST[21:15] SBASE[14:9] IMM[8] OFFSET[7:0]
    # 5 args: op, sdst, sbase, offset, imm
    W("Function.GCNEnc_Emit_SMRD {")
    W("    Input: op: Integer")
    W("    Input: sdst: Integer")
    W("    Input: sbase: Integer")
    W("    Input: offset: Integer")
    W("    Input: imm: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        w = BitwiseAnd(offset, 255)")
    W("        w = BitwiseOr(w, LeftShift(BitwiseAnd(imm, 1), 8))")
    W("        w = BitwiseOr(w, LeftShift(BitwiseAnd(sbase, 63), 9))")
    W("        w = BitwiseOr(w, LeftShift(BitwiseAnd(sdst, 127), 15))")
    W("        w = BitwiseOr(w, LeftShift(op, 22))")
    W("        w = BitwiseOr(w, LeftShift(24, 27))")  # 11000
    W("        GCNEncState.word0 = w")
    W("        ReturnValue(4)")
    W("    }")
    W("}")
    W("")

    # --- VOP1: ENCODING[31:25]=0x3F OP[16:9] VDST[24:17] SRC0[8:0]
    # 3 args: op, vdst, src0
    W("Function.GCNEnc_Emit_VOP1 {")
    W("    Input: op: Integer")
    W("    Input: vdst: Integer")
    W("    Input: src0: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        w = BitwiseAnd(src0, 511)")
    W("        w = BitwiseOr(w, LeftShift(op, 9))")
    W("        w = BitwiseOr(w, LeftShift(vdst, 17))")
    W("        w = BitwiseOr(w, LeftShift(63, 25))")  # 0111111
    W("        GCNEncState.word0 = w")
    W("        ReturnValue(4)")
    W("    }")
    W("}")
    W("")

    # --- VOP2: ENCODING[31]=0 OP[30:25] VDST[24:17] VSRC1[16:9] SRC0[8:0]
    # 4 args: op, vdst, src0, vsrc1
    W("Function.GCNEnc_Emit_VOP2 {")
    W("    Input: op: Integer")
    W("    Input: vdst: Integer")
    W("    Input: src0: Integer")
    W("    Input: vsrc1: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        w = BitwiseAnd(src0, 511)")
    W("        w = BitwiseOr(w, LeftShift(vsrc1, 9))")
    W("        w = BitwiseOr(w, LeftShift(vdst, 17))")
    W("        w = BitwiseOr(w, LeftShift(op, 25))")
    W("        // bit 31 = 0 (implicit)")
    W("        GCNEncState.word0 = w")
    W("        ReturnValue(4)")
    W("    }")
    W("}")
    W("")

    # --- VOPC: ENCODING[31:25]=0x3E OP[24:17] SRC0[8:0] VSRC1[16:9]
    # 3 args: op, src0, vsrc1
    W("Function.GCNEnc_Emit_VOPC {")
    W("    Input: op: Integer")
    W("    Input: src0: Integer")
    W("    Input: vsrc1: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        w = BitwiseAnd(src0, 511)")
    W("        w = BitwiseOr(w, LeftShift(vsrc1, 9))")
    W("        w = BitwiseOr(w, LeftShift(op, 17))")
    W("        w = BitwiseOr(w, LeftShift(62, 25))")  # 0111110
    W("        GCNEncState.word0 = w")
    W("        ReturnValue(4)")
    W("    }")
    W("}")
    W("")

    # --- VOP3: 64-bit encoding — NOW 6 ARGS (was 9)
    # word0: VDST[7:0] ABS[10:8] CLAMP[11] OP[25:17] ENCODING[31:26]=0x34
    # word1: SRC0[8:0] SRC1[17:9] SRC2[26:18] OMOD[28:27] NEG[31:29]
    #
    # Packed mods: clamp[0] | abs[3:1] | neg[6:4] | omod[8:7]
    W("// GCNEnc_Emit_VOP3: 6 args (was 9)")
    W("// mods = clamp[0] | abs[3:1] | neg[6:4] | omod[8:7]")
    W("// Helper: GCNEnc_VOP3Mods(clamp, abs, neg, omod) packs for you")
    W("Function.GCNEnc_Emit_VOP3 {")
    W("    Input: op: Integer")
    W("    Input: vdst: Integer")
    W("    Input: src0: Integer")
    W("    Input: src1: Integer")
    W("    Input: src2: Integer")
    W("    Input: mods: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        clamp = BitwiseAnd(mods, 1)")
    W("        abs_bits = BitwiseAnd(RightShift(mods, 1), 7)")
    W("        neg_bits = BitwiseAnd(RightShift(mods, 4), 7)")
    W("        omod = BitwiseAnd(RightShift(mods, 7), 3)")
    W("        w0 = BitwiseAnd(vdst, 255)")
    W("        w0 = BitwiseOr(w0, LeftShift(abs_bits, 8))")
    W("        w0 = BitwiseOr(w0, LeftShift(clamp, 11))")
    W("        w0 = BitwiseOr(w0, LeftShift(op, 17))")
    W("        w0 = BitwiseOr(w0, LeftShift(52, 26))")  # 110100
    W("        GCNEncState.word0 = w0")
    W("        w1 = BitwiseAnd(src0, 511)")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(src1, 511), 9))")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(src2, 511), 18))")
    W("        w1 = BitwiseOr(w1, LeftShift(omod, 27))")
    W("        w1 = BitwiseOr(w1, LeftShift(neg_bits, 29))")
    W("        GCNEncState.word1 = w1")
    W("        ReturnValue(8)")
    W("    }")
    W("}")
    W("")

    # VOP3 modifier packer helper (4 args → 1 packed int)
    W("Function.GCNEnc_VOP3Mods {")
    W("    Input: clamp: Integer")
    W("    Input: abs_bits: Integer")
    W("    Input: neg_bits: Integer")
    W("    Input: omod: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        m = BitwiseAnd(clamp, 1)")
    W("        m = BitwiseOr(m, LeftShift(BitwiseAnd(abs_bits, 7), 1))")
    W("        m = BitwiseOr(m, LeftShift(BitwiseAnd(neg_bits, 7), 4))")
    W("        m = BitwiseOr(m, LeftShift(BitwiseAnd(omod, 3), 7))")
    W("        ReturnValue(m)")
    W("    }")
    W("}")
    W("")

    # --- MUBUF: 64-bit encoding — NOW 5 ARGS (was 11)
    # word0: OFFSET[11:0] OFFEN[12] IDXEN[13] GLC[14] ADDR64[15] LDS[16] OP[24:18] ENC[31:26]=0x38
    # word1: VADDR[7:0] VDATA[15:8] SRSRC[20:16] SLC[22] TFE[23] SOFFSET[31:24]
    #
    # Packed flags: offset[11:0] | offen[12] | idxen[13] | glc[14] | addr64[15] | slc[22]
    # (flags go directly into word0 lower bits + slc into word1)
    W("// GCNEnc_Emit_MUBUF: 6 args (was 11)")
    W("// flags = offset[11:0] | offen[12] | idxen[13] | glc[14] | addr64[15] | slc[22]")
    W("// Helper: GCNEnc_MUBUFFlags(offset, offen, idxen, glc, addr64, slc) packs for you")
    W("Function.GCNEnc_Emit_MUBUF {")
    W("    Input: op: Integer")
    W("    Input: vdata: Integer")
    W("    Input: vaddr: Integer")
    W("    Input: srsrc: Integer")
    W("    Input: soffset: Integer")
    W("    Input: flags: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        // Extract flag fields")
    W("        offset = BitwiseAnd(flags, 4095)")
    W("        offen = BitwiseAnd(RightShift(flags, 12), 1)")
    W("        idxen = BitwiseAnd(RightShift(flags, 13), 1)")
    W("        glc = BitwiseAnd(RightShift(flags, 14), 1)")
    W("        addr64 = BitwiseAnd(RightShift(flags, 15), 1)")
    W("        slc = BitwiseAnd(RightShift(flags, 22), 1)")
    W("        w0 = offset")
    W("        w0 = BitwiseOr(w0, LeftShift(offen, 12))")
    W("        w0 = BitwiseOr(w0, LeftShift(idxen, 13))")
    W("        w0 = BitwiseOr(w0, LeftShift(glc, 14))")
    W("        w0 = BitwiseOr(w0, LeftShift(addr64, 15))")
    W("        w0 = BitwiseOr(w0, LeftShift(op, 18))")
    W("        w0 = BitwiseOr(w0, LeftShift(56, 26))")  # 111000
    W("        GCNEncState.word0 = w0")
    W("        w1 = BitwiseAnd(vaddr, 255)")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(vdata, 255), 8))")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(srsrc, 31), 16))")
    W("        w1 = BitwiseOr(w1, LeftShift(slc, 22))")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(soffset, 255), 24))")
    W("        GCNEncState.word1 = w1")
    W("        ReturnValue(8)")
    W("    }")
    W("}")
    W("")

    # MUBUF flags packer helper (6 args → 1 packed int)
    W("Function.GCNEnc_MUBUFFlags {")
    W("    Input: offset: Integer")
    W("    Input: offen: Integer")
    W("    Input: idxen: Integer")
    W("    Input: glc: Integer")
    W("    Input: addr64: Integer")
    W("    Input: slc: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        f = BitwiseAnd(offset, 4095)")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(offen, 1), 12))")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(idxen, 1), 13))")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(glc, 1), 14))")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(addr64, 1), 15))")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(slc, 1), 22))")
    W("        ReturnValue(f)")
    W("    }")
    W("}")
    W("")

    # --- MTBUF: 64-bit encoding — 6 ARGS
    # word0: OFFSET[11:0] OFFEN[12] IDXEN[13] GLC[14] OP[18:16] DFMT[22:19] NFMT[25:23] ENC[31:26]=0x3A
    # word1: VADDR[7:0] VDATA[15:8] SRSRC[20:16] SLC[22] TFE[23] SOFFSET[31:24]
    #
    # Packed flags: offset[11:0] | offen[12] | idxen[13] | glc[14] | dfmt[22:19] | nfmt[25:23] | slc[26]
    W("// GCNEnc_Emit_MTBUF: 6 args")
    W("// flags = offset[11:0] | offen[12] | idxen[13] | glc[14] | dfmt[22:19] | nfmt[25:23] | slc[26]")
    W("Function.GCNEnc_Emit_MTBUF {")
    W("    Input: op: Integer")
    W("    Input: vdata: Integer")
    W("    Input: vaddr: Integer")
    W("    Input: srsrc: Integer")
    W("    Input: soffset: Integer")
    W("    Input: flags: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        offset = BitwiseAnd(flags, 4095)")
    W("        offen = BitwiseAnd(RightShift(flags, 12), 1)")
    W("        idxen = BitwiseAnd(RightShift(flags, 13), 1)")
    W("        glc = BitwiseAnd(RightShift(flags, 14), 1)")
    W("        dfmt = BitwiseAnd(RightShift(flags, 19), 15)")
    W("        nfmt = BitwiseAnd(RightShift(flags, 23), 7)")
    W("        slc = BitwiseAnd(RightShift(flags, 26), 1)")
    W("        w0 = offset")
    W("        w0 = BitwiseOr(w0, LeftShift(offen, 12))")
    W("        w0 = BitwiseOr(w0, LeftShift(idxen, 13))")
    W("        w0 = BitwiseOr(w0, LeftShift(glc, 14))")
    W("        w0 = BitwiseOr(w0, LeftShift(op, 16))")
    W("        w0 = BitwiseOr(w0, LeftShift(dfmt, 19))")
    W("        w0 = BitwiseOr(w0, LeftShift(nfmt, 23))")
    W("        w0 = BitwiseOr(w0, LeftShift(58, 26))")  # 111010
    W("        GCNEncState.word0 = w0")
    W("        w1 = BitwiseAnd(vaddr, 255)")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(vdata, 255), 8))")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(srsrc, 31), 16))")
    W("        w1 = BitwiseOr(w1, LeftShift(slc, 22))")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(soffset, 255), 24))")
    W("        GCNEncState.word1 = w1")
    W("        ReturnValue(8)")
    W("    }")
    W("}")
    W("")

    # --- DS: 64-bit encoding — NOW 5 ARGS (was 8)
    # word0: OFFSET0[7:0] OFFSET1[15:8] GDS[17] OP[25:18] ENCODING[31:26]=0x36
    # word1: ADDR[7:0] DATA0[15:8] DATA1[23:16] VDST[31:24]
    #
    # Packed offsets: offset0[7:0] | offset1[15:8] | gds[16]
    W("// GCNEnc_Emit_DS: 5 args (was 8)")
    W("// offsets = offset0[7:0] | offset1[15:8] | gds[16]")
    W("// Helper: GCNEnc_DSOffsets(offset0, offset1, gds) packs for you")
    W("Function.GCNEnc_Emit_DS {")
    W("    Input: op: Integer")
    W("    Input: addr: Integer")
    W("    Input: data0: Integer")
    W("    Input: vdst: Integer")
    W("    Input: offsets: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        offset0 = BitwiseAnd(offsets, 255)")
    W("        offset1 = BitwiseAnd(RightShift(offsets, 8), 255)")
    W("        gds = BitwiseAnd(RightShift(offsets, 16), 1)")
    W("        data1 = BitwiseAnd(RightShift(offsets, 17), 255)")
    W("        w0 = offset0")
    W("        w0 = BitwiseOr(w0, LeftShift(offset1, 8))")
    W("        w0 = BitwiseOr(w0, LeftShift(gds, 17))")
    W("        w0 = BitwiseOr(w0, LeftShift(op, 18))")
    W("        w0 = BitwiseOr(w0, LeftShift(54, 26))")  # 110110
    W("        GCNEncState.word0 = w0")
    W("        w1 = BitwiseAnd(addr, 255)")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(data0, 255), 8))")
    W("        w1 = BitwiseOr(w1, LeftShift(data1, 16))")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(vdst, 255), 24))")
    W("        GCNEncState.word1 = w1")
    W("        ReturnValue(8)")
    W("    }")
    W("}")
    W("")

    # DS offsets packer helper (3 args + optional data1 → 1 packed int)
    W("Function.GCNEnc_DSOffsets {")
    W("    Input: offset0: Integer")
    W("    Input: offset1: Integer")
    W("    Input: gds: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        f = BitwiseAnd(offset0, 255)")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(offset1, 255), 8))")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(gds, 1), 16))")
    W("        ReturnValue(f)")
    W("    }")
    W("}")
    W("")

    # DS with data1 packer (4 args → 1 packed int)
    W("Function.GCNEnc_DSOffsetsD1 {")
    W("    Input: offset0: Integer")
    W("    Input: offset1: Integer")
    W("    Input: gds: Integer")
    W("    Input: data1: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        f = BitwiseAnd(offset0, 255)")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(offset1, 255), 8))")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(gds, 1), 16))")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(data1, 255), 17))")
    W("        ReturnValue(f)")
    W("    }")
    W("}")
    W("")

    # --- EXP: 64-bit encoding — NOW 6 ARGS (was 9)
    # word0: EN[3:0] TGT[9:4] COMPR[10] DONE[11] VM[12] ENCODING[31:26]=0x31
    # word1: VSRC0[7:0] VSRC1[15:8] VSRC2[23:16] VSRC3[31:24]
    #
    # Packed flags: en[3:0] | compr[4] | done[5] | vm[6]
    W("// GCNEnc_Emit_EXP: 6 args (was 9)")
    W("// flags = en[3:0] | compr[4] | done[5] | vm[6]")
    W("Function.GCNEnc_Emit_EXP {")
    W("    Input: tgt: Integer")
    W("    Input: vsrc0: Integer")
    W("    Input: vsrc1: Integer")
    W("    Input: vsrc2: Integer")
    W("    Input: vsrc3: Integer")
    W("    Input: flags: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        en = BitwiseAnd(flags, 15)")
    W("        compr = BitwiseAnd(RightShift(flags, 4), 1)")
    W("        done = BitwiseAnd(RightShift(flags, 5), 1)")
    W("        vm = BitwiseAnd(RightShift(flags, 6), 1)")
    W("        w0 = en")
    W("        w0 = BitwiseOr(w0, LeftShift(BitwiseAnd(tgt, 63), 4))")
    W("        w0 = BitwiseOr(w0, LeftShift(compr, 10))")
    W("        w0 = BitwiseOr(w0, LeftShift(done, 11))")
    W("        w0 = BitwiseOr(w0, LeftShift(vm, 12))")
    W("        w0 = BitwiseOr(w0, LeftShift(49, 26))")  # 110001
    W("        GCNEncState.word0 = w0")
    W("        w1 = BitwiseAnd(vsrc0, 255)")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(vsrc1, 255), 8))")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(vsrc2, 255), 16))")
    W("        w1 = BitwiseOr(w1, LeftShift(BitwiseAnd(vsrc3, 255), 24))")
    W("        GCNEncState.word1 = w1")
    W("        ReturnValue(8)")
    W("    }")
    W("}")
    W("")

    # EXP flags packer helper
    W("Function.GCNEnc_EXPFlags {")
    W("    Input: en: Integer")
    W("    Input: compr: Integer")
    W("    Input: done: Integer")
    W("    Input: vm: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        f = BitwiseAnd(en, 15)")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(compr, 1), 4))")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(done, 1), 5))")
    W("        f = BitwiseOr(f, LeftShift(BitwiseAnd(vm, 1), 6))")
    W("        ReturnValue(f)")
    W("    }")
    W("}")
    W("")

    # =========================================================================
    # Convenience emit wrappers (common patterns)
    # =========================================================================

    # Emit S_ENDPGM
    W("Function.GCNEnc_Emit_S_ENDPGM {")
    W("    Output: Integer")
    W("    Body: { ReturnValue(GCNEnc_Emit_SOPP(1, 0)) }")
    W("}")
    W("")

    # Emit S_WAITCNT
    W("Function.GCNEnc_Emit_S_WAITCNT {")
    W("    Input: vmcnt: Integer")
    W("    Input: expcnt: Integer")
    W("    Input: lgkmcnt: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        // SI: simm16 = vmcnt[3:0] | expcnt[6:4] | lgkmcnt[12:8]")
    W("        imm = BitwiseAnd(vmcnt, 15)")
    W("        imm = BitwiseOr(imm, LeftShift(BitwiseAnd(expcnt, 7), 4))")
    W("        imm = BitwiseOr(imm, LeftShift(BitwiseAnd(lgkmcnt, 31), 8))")
    W("        ReturnValue(GCNEnc_Emit_SOPP(12, imm))")
    W("    }")
    W("}")
    W("")

    # Emit S_BARRIER
    W("Function.GCNEnc_Emit_S_BARRIER {")
    W("    Output: Integer")
    W("    Body: { ReturnValue(GCNEnc_Emit_SOPP(10, 0)) }")
    W("}")
    W("")

    # Emit S_NOP
    W("Function.GCNEnc_Emit_S_NOP {")
    W("    Input: count: Integer")
    W("    Output: Integer")
    W("    Body: { ReturnValue(GCNEnc_Emit_SOPP(0, count)) }")
    W("}")
    W("")

    # Emit V_MOV_B32
    W("Function.GCNEnc_Emit_V_MOV_B32 {")
    W("    Input: vdst: Integer")
    W("    Input: src0: Integer")
    W("    Output: Integer")
    W("    Body: { ReturnValue(GCNEnc_Emit_VOP1(1, vdst, src0)) }")
    W("}")
    W("")

    # Emit S_MOV_B32
    W("Function.GCNEnc_Emit_S_MOV_B32 {")
    W("    Input: sdst: Integer")
    W("    Input: ssrc0: Integer")
    W("    Output: Integer")
    W("    Body: { ReturnValue(GCNEnc_Emit_SOP1(3, sdst, ssrc0)) }")
    W("}")
    W("")

    # Emit S_LOAD_DWORD (SMRD, immediate offset)
    W("Function.GCNEnc_Emit_S_LOAD_DWORD_IMM {")
    W("    Input: sdst: Integer")
    W("    Input: sbase_pair: Integer")
    W("    Input: byte_offset: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        // SMRD: sbase = SGPR pair number / 2")
    W("        ReturnValue(GCNEnc_Emit_SMRD(0, sdst, Divide(sbase_pair, 2), byte_offset, 1))")
    W("    }")
    W("}")
    W("")

    # Emit BUFFER_LOAD_DWORD (common pattern: offen mode, no index)
    W("Function.GCNEnc_Emit_BUFFER_LOAD_DWORD {")
    W("    Input: vdst: Integer")
    W("    Input: vaddr: Integer")
    W("    Input: srsrc_x4: Integer")
    W("    Input: soffset: Integer")
    W("    Input: inst_offset: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        // srsrc field = SGPR number / 4")
    W("        // flags: offset=inst_offset, offen=1, idxen=0, glc=0, addr64=0, slc=0")
    W("        flags = BitwiseOr(BitwiseAnd(inst_offset, 4095), LeftShift(1, 12))")
    W("        ReturnValue(GCNEnc_Emit_MUBUF(12, vdst, vaddr, Divide(srsrc_x4, 4), soffset, flags))")
    W("    }")
    W("}")
    W("")

    # Emit BUFFER_STORE_DWORD
    W("Function.GCNEnc_Emit_BUFFER_STORE_DWORD {")
    W("    Input: vdata: Integer")
    W("    Input: vaddr: Integer")
    W("    Input: srsrc_x4: Integer")
    W("    Input: soffset: Integer")
    W("    Input: inst_offset: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        flags = BitwiseOr(BitwiseAnd(inst_offset, 4095), LeftShift(1, 12))")
    W("        ReturnValue(GCNEnc_Emit_MUBUF(28, vdata, vaddr, Divide(srsrc_x4, 4), soffset, flags))")
    W("    }")
    W("}")
    W("")

    # =========================================================================
    # Write output
    # =========================================================================
    out_text = '\n'.join(lines) + '\n'
    with open(out_path, 'w') as f:
        f.write(out_text)

    n_funcs = sum(1 for l in lines if l.startswith('Function.'))
    n_pools = sum(1 for l in lines if l.startswith('FixedPool.'))
    print(f"Written {out_path}", file=sys.stderr)
    print(f"  {len(all_entries)} instructions in FixedPool.GCN", file=sys.stderr)
    print(f"  {n_pools} FixedPools, {n_funcs} functions", file=sys.stderr)
    print(f"  {len(lines)} lines", file=sys.stderr)


if __name__ == "__main__":
    out = os.path.join(OUT_DIR, "Library.GCNEnc.ailang")
    if len(sys.argv) > 1:
        out = sys.argv[1]
    gen(out)
