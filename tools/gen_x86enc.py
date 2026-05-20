#!/usr/bin/env python3
"""
gen_x86enc.py — Generate Library.CEmitX86Enc.ailang from Maratyszcza/Opcodes x86_64.xml

Design: pure code-emitter, zero external dependencies.
  - No PERF_Hash, no XArrays, no Arena import.
  - Encoding data embedded directly in 124 dispatch/leaf functions.
  - Lookup dispatches on mnemonic characters (trie-style).
  - Each leaf has at most 400 entries (linear StringCompare chain).
  - Register lookup: two pure StringCompare chains (RegType, RegNum).

Descriptor word A bit layout (64-bit):
  bits  0- 7  opcode byte 1
  bits  8-15  opcode byte 2  (0 = unused)
  bits 16-23  opcode byte 3  (0 = unused)
  bits 24-25  num_opcodes    (1-3)
  bits 26-33  legacy prefix  (0 = none)
  bit     34  REX.W
  bits 35-36  REX.R source   (0=none, 1=op0, 2=op1, 3=op2)
  bits 37-38  REX.B source
  bits 39-40  REX.X source
  bit     41  has_modrm
  bits 42-43  ModRM mode
  bit     44  ModRM mode is from operand
  bits 45-47  ModRM reg
  bit     48  ModRM reg is from operand
  bits 49-51  ModRM rm
  bit     52  ModRM rm is literal
  bits 53-55  opcode addend  (0=none, 1=op0, 2=op1, 3=op2)
  bits 56-59  immediate size (0=none,1=1B,2=2B,3=4B,4=8B)
  bits 60-61  immediate op index
  bits 62-63  encoding type  (0=simple,1=VEX,3=EVEX)

Descriptor word B (VEX/EVEX, stored in X86EncResult.desc_b):
  bits  0- 1  pp
  bits  2- 6  m-mmmm
  bit      7  W
  bits  8- 9  L/LL
  bits 10-12  vvvv source
  bits 13-15  aaa source
  bit     16  z
  bit     17  b
"""

import sys
import os
sys.path.insert(0, '/tmp/opcodes')
from opcodes import x86_64
from collections import defaultdict

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def op_src(operands, obj):
    if obj is None or isinstance(obj, int):
        return -1
    for i, op in enumerate(operands):
        if op is obj:
            return i
    return -1


def encode_word_a(form, enc):
    ops = form.operands
    prefix = 0; rex_W = 0; rex_R = 0; rex_B = 0; rex_X = 0
    opcodes = []; addend_op = 0
    has_modrm = 0; modrm_mode = 0; modrm_mode_is_op = 0
    modrm_reg = 0; modrm_reg_is_op = 0; modrm_rm = 0; modrm_rm_is_lit = 0
    imm_size = 0; imm_op = 0; enc_type = 0

    for comp in enc.components:
        t = type(comp).__name__
        if t == 'Prefix':
            prefix = comp.byte
        elif t == 'REX':
            rex_W = int(comp.W) if isinstance(comp.W, int) else 0
            r = op_src(ops, comp.R); rex_R = (r+1) if r >= 0 else 0
            r = op_src(ops, comp.B); rex_B = (r+1) if r >= 0 else 0
            r = op_src(ops, comp.X); rex_X = (r+1) if r >= 0 else 0
        elif t == 'Opcode':
            if comp.addend is not None:
                i = op_src(ops, comp.addend)
                addend_op = (i+1) if i >= 0 else 0
            opcodes.append(comp.byte)
        elif t == 'ModRM':
            has_modrm = 1
            if isinstance(comp.mode, int):
                modrm_mode = comp.mode & 0x3; modrm_mode_is_op = 0
            else:
                i = op_src(ops, comp.mode)
                modrm_mode = i if i >= 0 else 0; modrm_mode_is_op = 1
            if isinstance(comp.reg, int):
                modrm_reg = comp.reg & 0x7; modrm_reg_is_op = 0
            else:
                i = op_src(ops, comp.reg)
                modrm_reg = i if i >= 0 else 0; modrm_reg_is_op = 1
            if isinstance(comp.rm, int):
                modrm_rm = comp.rm & 0x7; modrm_rm_is_lit = 1
            else:
                i = op_src(ops, comp.rm)
                modrm_rm = i if i >= 0 else 0; modrm_rm_is_lit = 0
        elif t == 'Immediate':
            sz_map = {1:1, 2:2, 4:3, 8:4}
            imm_size = sz_map.get(comp.size, 0)
            i = op_src(ops, comp.value)
            imm_op = i if i >= 0 else 0
        elif t == 'VEX':
            enc_type = 1
        elif t == 'EVEX':
            enc_type = 3

    n = min(len(opcodes), 3)
    o = (opcodes + [0, 0, 0])[:3]
    w  = (o[0] & 0xFF)
    w |= (o[1] & 0xFF)          << 8
    w |= (o[2] & 0xFF)          << 16
    w |= (n    & 0x3)           << 24
    w |= (prefix & 0xFF)        << 26
    w |= (rex_W & 0x1)          << 34
    w |= (rex_R & 0x3)          << 35
    w |= (rex_B & 0x3)          << 37
    w |= (rex_X & 0x3)          << 39
    w |= (has_modrm & 0x1)      << 41
    w |= (modrm_mode & 0x3)     << 42
    w |= (modrm_mode_is_op & 1) << 44
    w |= (modrm_reg & 0x7)      << 45
    w |= (modrm_reg_is_op & 1)  << 48
    w |= (modrm_rm & 0x7)       << 49
    w |= (modrm_rm_is_lit & 1)  << 52
    w |= (addend_op & 0x7)      << 53
    w |= (imm_size & 0xF)       << 56
    w |= (imm_op & 0x3)         << 60
    w |= (enc_type & 0x3)       << 62
    return w


def encode_word_b(form, enc):
    ops = form.operands
    pp = 0; mmmmm = 0; W = 0; L = 0; vvvv_src = 7
    aaa_src = 0; z_src = 0; b_src = 0

    def parse_bits(v):
        if v is None: return 0
        if isinstance(v, int): return v
        try: return int(str(v), 2)
        except: return 0

    for comp in enc.components:
        t = type(comp).__name__
        if t == 'VEX':
            pp    = parse_bits(getattr(comp,'pp',0))
            mmmmm = parse_bits(getattr(comp,'m_mmmm',0) or getattr(comp,'mmmmm',0))
            W     = parse_bits(getattr(comp,'W',0))
            L     = parse_bits(getattr(comp,'L',0))
            v = getattr(comp,'vvvv',None)
            if v is not None:
                i = op_src(ops, v); vvvv_src = i if i >= 0 else 7
        elif t == 'EVEX':
            pp    = parse_bits(getattr(comp,'pp',0))
            mmmmm = parse_bits(getattr(comp,'mmm',0) or getattr(comp,'mmmmm',0))
            W     = parse_bits(getattr(comp,'W',0))
            L     = parse_bits(getattr(comp,'LL',0) or getattr(comp,'L',0))
            v = getattr(comp,'vvvv',None)
            if v is not None:
                i = op_src(ops, v); vvvv_src = i if i >= 0 else 7
            for attr in ['aaa','z','b']:
                val = getattr(comp, attr, None)
                if val is not None:
                    i = op_src(ops, val)
                    if attr == 'aaa': aaa_src = i if i >= 0 else 0
                    elif attr == 'z': z_src   = i if i >= 0 else 0
                    else:             b_src   = i if i >= 0 else 0

    w  = (pp       & 0x3)
    w |= (mmmmm    & 0x1F) << 2
    w |= (W        & 0x1)  << 7
    w |= (L        & 0x3)  << 8
    w |= (vvvv_src & 0x7)  << 10
    w |= (aaa_src  & 0x7)  << 13
    w |= (z_src    & 0x1)  << 16
    w |= (b_src    & 0x1)  << 17
    return w


def form_key(name, form):
    return name + '_' + '_'.join(o.type for o in form.operands)


# ---------------------------------------------------------------------------
# register tables
# ---------------------------------------------------------------------------

R64  = ['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi',
        'r8','r9','r10','r11','r12','r13','r14','r15']
R32  = ['eax','ecx','edx','ebx','esp','ebp','esi','edi',
        'r8d','r9d','r10d','r11d','r12d','r13d','r14d','r15d']
R16  = ['ax','cx','dx','bx','sp','bp','si','di',
        'r8w','r9w','r10w','r11w','r12w','r13w','r14w','r15w']
R8   = ['al','cl','dl','bl','ah','ch','dh','bh',
        'r8b','r9b','r10b','r11b','r12b','r13b','r14b','r15b',
        'spl','bpl','sil','dil']
XMM  = [f'xmm{i}' for i in range(32)]
YMM  = [f'ymm{i}' for i in range(32)]
ZMM  = [f'zmm{i}' for i in range(64)]
MM   = [f'mm{i}'  for i in range(8)]
BND  = [f'bnd{i}' for i in range(4)]
KREG = [f'k{i}'   for i in range(8)]
SEG  = ['es','cs','ss','ds','fs','gs']
CTRL = [f'cr{i}'  for i in range(16)]
DBG  = [f'dr{i}'  for i in range(16)]
ST   = [f'st({i})' for i in range(8)] + ['st']

REG_ENTRIES = []  # list of (name, num, type_str)
def _add(lst, typ):
    for i, n in enumerate(lst):
        REG_ENTRIES.append((n, i, typ))
_add(R64, 'r64'); _add(R32, 'r32'); _add(R16, 'r16'); _add(R8, 'r8')
_add(XMM, 'xmm'); _add(YMM, 'ymm'); _add(ZMM, 'zmm')
_add(MM, 'mm'); _add(BND, 'bnd'); _add(KREG, 'k')
_add(SEG, 'sreg'); _add(CTRL, 'cr'); _add(DBG, 'dr'); _add(ST, 'st')
# fixed special
for n in ['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi']:
    if not any(e[0] == n for e in REG_ENTRIES):
        REG_ENTRIES.append((n, R64.index(n), 'r64'))
REG_ENTRIES.append(('al',  0,  'al'))
REG_ENTRIES.append(('cl',  1,  'cl'))
REG_ENTRIES.append(('rip', 16, 'rip'))

# deduplicate
seen = set()
REGS = []
for e in REG_ENTRIES:
    if e[0] not in seen:
        seen.add(e[0])
        REGS.append(e)


# ---------------------------------------------------------------------------
# lookup tree builder
# ---------------------------------------------------------------------------

MAX_LEAF = 400  # max entries in a leaf function

def get_mnem(key):
    i = key.find('_')
    return key[:i] if i >= 0 else key

def mnem_char(key, depth):
    m = get_mnem(key)
    return m[depth] if depth < len(m) else ''

def func_name_for(prefix):
    return 'X86Enc_Lookup' + (f'_{prefix}' if prefix else '')

def gen_leaf(prefix, entries, W):
    name = func_name_for(prefix)
    W(f'Function.{name} {{')
    W('    Input: key: Address')
    W('    Output: Integer')
    W('    Body: {')
    for key, wa, wb in sorted(entries, key=lambda x: x[0]):
        W(f'        IfCondition EqualTo(StringCompare(key, "{key}"), 0) ThenBlock: {{')
        W(f'            X86EncResult.desc_a = {wa}')
        W(f'            X86EncResult.desc_b = {wb}')
        W(f'            ReturnValue(1)')
        W(f'        }}')
    W('        ReturnValue(0)')
    W('    }')
    W('}')
    W('')

def gen_dispatch(prefix, sub_groups, depth, W):
    name = func_name_for(prefix)
    W(f'Function.{name} {{')
    W('    Input: key: Address')
    W('    Output: Integer')
    W('    Body: {')
    W(f'        c = GetByte(key, {depth})')
    for c in sorted(sub_groups.keys()):
        if c == '':
            # mnemonic complete — call the leaf for this sub-prefix
            sub_name = func_name_for(prefix + '_end')
            W(f'        IfCondition EqualTo(c, 95) ThenBlock: {{ ReturnValue({sub_name}(key)) }}')
        else:
            code = ord(c)
            sub_name = func_name_for(prefix + c)
            W(f'        IfCondition EqualTo(c, {code}) ThenBlock: {{ ReturnValue({sub_name}(key)) }}')
    W('        ReturnValue(0)')
    W('    }')
    W('}')
    W('')

def gen_tree(prefix, entries, depth, W):
    """Recursively generate lookup tree functions."""
    if len(entries) <= MAX_LEAF:
        gen_leaf(prefix, entries, W)
        return

    # Split by mnemonic character at depth
    sub = defaultdict(list)
    for e in entries:
        c = mnem_char(e[0], depth)
        sub[c].append(e)

    # If no character variation (all same mnemonic), force leaf
    if len(sub) == 1:
        gen_leaf(prefix, entries, W)
        return

    # Generate sub-trees first (so functions are defined before callers)
    for c in sorted(sub.keys()):
        sub_prefix = (prefix + '_end') if c == '' else (prefix + c)
        gen_tree(sub_prefix, sub[c], depth + 1, W)

    # Generate dispatch
    gen_dispatch(prefix, sub, depth, W)


# ---------------------------------------------------------------------------
# main generator
# ---------------------------------------------------------------------------

def gen(out_path):
    iset = x86_64.read_instruction_set()

    # Build all entries: (key, word_a, word_b)
    all_entries = []
    errors = 0
    for instr in iset:
        for form in instr.forms:
            if not form.encodings:
                continue
            enc = form.encodings[0]
            key = form_key(instr.name, form)
            try:
                wa = encode_word_a(form, enc)
                et = (wa >> 62) & 0x3
                wb = encode_word_b(form, enc) if et in (1, 3) else 0
                all_entries.append((key, wa, wb))
            except Exception as e:
                errors += 1

    print(f"Total entries: {len(all_entries)}, errors: {errors}", file=sys.stderr)

    lines = []
    W = lines.append

    W("// Library.CEmitX86Enc.ailang")
    W("// Auto-generated from Maratyszcza/Opcodes x86_64.xml")
    W("// Pure x86-64 instruction encoding lookup + emitter.")
    W("// Zero external dependencies — DO NOT EDIT.")
    W("// Run tools/gen_x86enc.py to regenerate.")
    W(f"// {len(all_entries)} instruction forms, full ISA including SSE/AVX/AVX-512")
    W("")

    # -------------------------------------------------------------------------
    # State pools
    # -------------------------------------------------------------------------
    W("FixedPool.X86AsmParse {")
    W('    "op0":  Initialize=0, CanChange=True')
    W('    "op1":  Initialize=0, CanChange=True')
    W('    "op2":  Initialize=0, CanChange=True')
    W('    "op3":  Initialize=0, CanChange=True')
    W('    "nops": Initialize=0, CanChange=True')
    W("}")
    W("")
    W("FixedPool.X86EncResult {")
    W('    "desc_a": Initialize=0, CanChange=True')
    W('    "desc_b": Initialize=0, CanChange=True')
    W("}")
    W("")

    # -------------------------------------------------------------------------
    # Bit helper
    # -------------------------------------------------------------------------
    W("Function.X86Enc_Bits {")
    W("    Input: val: Integer")
    W("    Input: shift: Integer")
    W("    Input: mask: Integer")
    W("    Output: Integer")
    W("    Body: { ReturnValue(BitwiseAnd(RightShift(val, shift), mask)) }")
    W("}")
    W("")

    # -------------------------------------------------------------------------
    # Operand value selector
    # -------------------------------------------------------------------------
    W("Function.X86Enc_OpVal {")
    W("    Input: idx: Integer")
    W("    Input: op0: Integer")
    W("    Input: op1: Integer")
    W("    Input: op2: Integer")
    W("    Input: op3: Integer")
    W("    Output: Integer")
    W("    Body: {")
    W("        IfCondition EqualTo(idx, 1) ThenBlock: { ReturnValue(op0) }")
    W("        IfCondition EqualTo(idx, 2) ThenBlock: { ReturnValue(op1) }")
    W("        IfCondition EqualTo(idx, 3) ThenBlock: { ReturnValue(op2) }")
    W("        IfCondition EqualTo(idx, 4) ThenBlock: { ReturnValue(op3) }")
    W("        ReturnValue(0)")
    W("    }")
    W("}")
    W("")

    # -------------------------------------------------------------------------
    # Register type lookup
    # -------------------------------------------------------------------------
    W("Function.X86Enc_RegType {")
    W("    Input: name: Address")
    W("    Output: Address")
    W("    Body: {")
    for reg_name, _, typ in REGS:
        W(f'        IfCondition EqualTo(StringCompare(name, "{reg_name}"), 0) ThenBlock: {{ ReturnValue("{typ}") }}')
    W("        ReturnValue(0)")
    W("    }")
    W("}")
    W("")

    # -------------------------------------------------------------------------
    # Register number lookup
    # -------------------------------------------------------------------------
    W("Function.X86Enc_RegNum {")
    W("    Input: name: Address")
    W("    Output: Integer")
    W("    Body: {")
    for reg_name, num, _ in REGS:
        W(f'        IfCondition EqualTo(StringCompare(name, "{reg_name}"), 0) ThenBlock: {{ ReturnValue({num}) }}')
    W("        ReturnValue(-1)")
    W("    }")
    W("}")
    W("")

    # -------------------------------------------------------------------------
    # Instruction lookup tree (generates ~124 functions)
    # -------------------------------------------------------------------------
    # Split by first character for top-level dispatch
    first_groups = defaultdict(list)
    for e in all_entries:
        c = mnem_char(e[0], 0)
        first_groups[c].append(e)

    # Generate sub-trees per first letter
    for c in sorted(first_groups.keys()):
        gen_tree(c, first_groups[c], 1, W)

    # Top-level dispatch on key[0]
    W("Function.X86Enc_Lookup {")
    W("    Input: key: Address")
    W("    Output: Integer")
    W("    Body: {")
    W("        X86EncResult.desc_a = 0")
    W("        X86EncResult.desc_b = 0")
    W("        c = GetByte(key, 0)")
    for c in sorted(first_groups.keys()):
        code = ord(c)
        sub_name = func_name_for(c)
        W(f"        IfCondition EqualTo(c, {code}) ThenBlock: {{ ReturnValue({sub_name}(key)) }}")
    W("        ReturnValue(0)")
    W("    }")
    W("}")
    W("")

    # -------------------------------------------------------------------------
    # Asm string parser
    # Parses "MNEM op1, op2, ..." — builds key, fills X86AsmParse.op*
    # Uses only builtins: StringLength, GetByte, SetByte, Allocate,
    #                     StringCompare, StringToNumber, X86Enc_RegType/Num
    # -------------------------------------------------------------------------
    W("Function.X86Enc_ParseAsm {")
    W("    Input: src: Address")
    W("    Output: Address")
    W("    Body: {")
    W("        X86AsmParse.nops = 0")
    W("        X86AsmParse.op0 = 0")
    W("        X86AsmParse.op1 = 0")
    W("        X86AsmParse.op2 = 0")
    W("        X86AsmParse.op3 = 0")
    W("        len = StringLength(src)")
    W("        // Find mnemonic end (first space/tab or end)")
    W("        mi = 0")
    W("        WhileLoop LessThan(mi, len) {")
    W("            mc = GetByte(src, mi)")
    W("            IfCondition EqualTo(mc, 32) ThenBlock: { BreakLoop }")
    W("            IfCondition EqualTo(mc, 9)  ThenBlock: { BreakLoop }")
    W("            mi = Add(mi, 1)")
    W("        }")
    W("        // Build key buffer (256 bytes max)")
    W("        key_buf = Allocate(256)")
    W("        kpos = 0")
    W("        // Copy mnemonic uppercase")
    W("        ki = 0")
    W("        WhileLoop LessThan(ki, mi) {")
    W("            kc = GetByte(src, ki)")
    W("            IfCondition And(GreaterEqual(kc,97), LessEqual(kc,122)) ThenBlock: {")
    W("                kc = Subtract(kc, 32)")
    W("            }")
    W("            SetByte(key_buf, kpos, kc)")
    W("            kpos = Add(kpos, 1)")
    W("            ki = Add(ki, 1)")
    W("        }")
    W("        // Parse operands")
    W("        i = mi")
    W("        op_idx = 0")
    W("        WhileLoop LessThan(i, len) {")
    W("            c = GetByte(src, i)")
    W("            // Skip spaces, commas")
    W("            IfCondition Or(EqualTo(c,32), Or(EqualTo(c,9), EqualTo(c,44))) ThenBlock: {")
    W("                i = Add(i, 1)")
    W("                ContinueLoop")
    W("            }")
    W("            // Read token: stop at space, comma")
    W("            tok_start = i")
    W("            WhileLoop LessThan(i, len) {")
    W("                c2 = GetByte(src, i)")
    W("                IfCondition Or(EqualTo(c2,32), Or(EqualTo(c2,9), EqualTo(c2,44))) ThenBlock: { BreakLoop }")
    W("                i = Add(i, 1)")
    W("            }")
    W("            tok_len = Subtract(i, tok_start)")
    W("            // Copy token lowercase to scratch")
    W("            tok = Allocate(Add(tok_len, 1))")
    W("            tj = 0")
    W("            WhileLoop LessThan(tj, tok_len) {")
    W("                tc = GetByte(src, Add(tok_start, tj))")
    W("                IfCondition And(GreaterEqual(tc,65), LessEqual(tc,90)) ThenBlock: { tc = Add(tc,32) }")
    W("                SetByte(tok, tj, tc)")
    W("                tj = Add(tj, 1)")
    W("            }")
    W("            SetByte(tok, tok_len, 0)")
    W("            // Extract base register name (stop at '{', '[', '+')")
    W("            base_len = 0")
    W("            WhileLoop LessThan(base_len, tok_len) {")
    W("                bc = GetByte(tok, base_len)")
    W("                IfCondition EqualTo(bc, 123) ThenBlock: { BreakLoop }")  # '{'
    W("                IfCondition EqualTo(bc, 91)  ThenBlock: { BreakLoop }")  # '['
    W("                IfCondition EqualTo(bc, 43)  ThenBlock: { BreakLoop }")  # '+'
    W("                base_len = Add(base_len, 1)")
    W("            }")
    W("            base = Allocate(Add(base_len, 1))")
    W("            bj = 0")
    W("            WhileLoop LessThan(bj, base_len) {")
    W("                SetByte(base, bj, GetByte(tok, bj))")
    W("                bj = Add(bj, 1)")
    W("            }")
    W("            SetByte(base, base_len, 0)")
    W("            // Register or immediate?")
    W("            rtype = X86Enc_RegType(base)")
    W("            IfCondition NotEqual(rtype, 0) ThenBlock: {")
    W("                // Register — scan decorators in tok for {k} and {z}")
    W("                has_mask = 0")
    W("                has_zero = 0")
    W("                di = base_len")
    W("                WhileLoop LessThan(di, tok_len) {")
    W("                    dc = GetByte(tok, di)")
    W("                    IfCondition EqualTo(dc, 123) ThenBlock: {")  # '{'
    W("                        // read until '}'")
    W("                        dec_start = Add(di, 1)")
    W("                        di = Add(di, 1)")
    W("                        WhileLoop LessThan(di, tok_len) {")
    W("                            ec = GetByte(tok, di)")
    W("                            IfCondition EqualTo(ec, 125) ThenBlock: { BreakLoop }")  # '}'
    W("                            di = Add(di, 1)")
    W("                        }")
    W("                        dec_len = Subtract(di, dec_start)")
    W("                        // Check if it's 'z' (zeroing) or a k register (mask)")
    W("                        IfCondition EqualTo(dec_len, 1) ThenBlock: {")
    W("                            zc = GetByte(tok, dec_start)")
    W("                            IfCondition EqualTo(zc, 122) ThenBlock: { has_zero = 1 }")  # 'z'
    W("                        } ElseBlock: {")
    W("                            // k0..k7 -> mask register")
    W("                            kc2 = GetByte(tok, dec_start)")
    W("                            IfCondition EqualTo(kc2, 107) ThenBlock: { has_mask = 1 }")  # 'k'
    W("                        }")
    W("                    }")
    W("                    di = Add(di, 1)")
    W("                }")
    W("                // Build full type string in key")
    W("                rtype_len = StringLength(rtype)")
    W("                SetByte(key_buf, kpos, 95)")  # '_'
    W("                kpos = Add(kpos, 1)")
    W("                rtj = 0")
    W("                WhileLoop LessThan(rtj, rtype_len) {")
    W("                    SetByte(key_buf, kpos, GetByte(rtype, rtj))")
    W("                    kpos = Add(kpos, 1)")
    W("                    rtj = Add(rtj, 1)")
    W("                }")
    W("                IfCondition EqualTo(has_mask, 1) ThenBlock: {")
    W("                    SetByte(key_buf, kpos, 123)")
    W("                    kpos = Add(kpos, 1)")
    W("                    SetByte(key_buf, kpos, 107)")
    W("                    kpos = Add(kpos, 1)")
    W("                    SetByte(key_buf, kpos, 125)")
    W("                    kpos = Add(kpos, 1)")
    W("                }")
    W("                IfCondition EqualTo(has_zero, 1) ThenBlock: {")
    W("                    SetByte(key_buf, kpos, 123)")
    W("                    kpos = Add(kpos, 1)")
    W("                    SetByte(key_buf, kpos, 122)")
    W("                    kpos = Add(kpos, 1)")
    W("                    SetByte(key_buf, kpos, 125)")
    W("                    kpos = Add(kpos, 1)")
    W("                }")
    W("                rnum = X86Enc_RegNum(base)")
    W("                IfCondition EqualTo(op_idx, 0) ThenBlock: { X86AsmParse.op0 = rnum }")
    W("                IfCondition EqualTo(op_idx, 1) ThenBlock: { X86AsmParse.op1 = rnum }")
    W("                IfCondition EqualTo(op_idx, 2) ThenBlock: { X86AsmParse.op2 = rnum }")
    W("                IfCondition EqualTo(op_idx, 3) ThenBlock: { X86AsmParse.op3 = rnum }")
    W("            } ElseBlock: {")
    W("                // Immediate — parse as decimal/hex number")
    W("                imm_val = StringToNumber(tok)")
    W("                imm_type_str = \"imm32\"")
    W("                imm_type_len = 5")
    W("                IfCondition And(GreaterEqual(imm_val,-128), LessEqual(imm_val,127)) ThenBlock: {")
    W("                    imm_type_str = \"imm8\"")
    W("                    imm_type_len = 4")
    W("                } ElseBlock: {")
    W("                    IfCondition Or(LessThan(imm_val,-2147483648), GreaterThan(imm_val,2147483647)) ThenBlock: {")
    W("                        imm_type_str = \"imm64\"")
    W("                        imm_type_len = 5")
    W("                    }")
    W("                }")
    W("                SetByte(key_buf, kpos, 95)")  # '_'
    W("                kpos = Add(kpos, 1)")
    W("                itj = 0")
    W("                WhileLoop LessThan(itj, imm_type_len) {")
    W("                    SetByte(key_buf, kpos, GetByte(imm_type_str, itj))")
    W("                    kpos = Add(kpos, 1)")
    W("                    itj = Add(itj, 1)")
    W("                }")
    W("                IfCondition EqualTo(op_idx, 0) ThenBlock: { X86AsmParse.op0 = imm_val }")
    W("                IfCondition EqualTo(op_idx, 1) ThenBlock: { X86AsmParse.op1 = imm_val }")
    W("                IfCondition EqualTo(op_idx, 2) ThenBlock: { X86AsmParse.op2 = imm_val }")
    W("                IfCondition EqualTo(op_idx, 3) ThenBlock: { X86AsmParse.op3 = imm_val }")
    W("            }")
    W("            op_idx = Add(op_idx, 1)")
    W("        }")
    W("        SetByte(key_buf, kpos, 0)")
    W("        X86AsmParse.nops = op_idx")
    W("        ReturnValue(key_buf)")
    W("    }")
    W("}")
    W("")

    # -------------------------------------------------------------------------
    # Emitter: reads X86EncResult.desc_a/desc_b, X86AsmParse.op*, emits bytes
    # -------------------------------------------------------------------------
    W("Function.X86Enc_Emit {")
    W("    Input: key: Address")
    W("    Output: Integer")
    W("    Body: {")
    W("        found = X86Enc_Lookup(key)")
    W("        IfCondition EqualTo(found, 0) ThenBlock: {")
    W("            PrintMessage(\"[X86Enc] Unknown instruction: \")")
    W("            PrintMessage(key)")
    W("            PrintMessage(\"\\n\")")
    W("            ReturnValue(0)")
    W("        }")
    W("        desc_a = X86EncResult.desc_a")
    W("        desc_b = X86EncResult.desc_b")
    W("        op0 = X86AsmParse.op0")
    W("        op1 = X86AsmParse.op1")
    W("        op2 = X86AsmParse.op2")
    W("        op3 = X86AsmParse.op3")
    W("        enc_type = X86Enc_Bits(desc_a, 62, 3)")
    W("")
    W("        // --- VEX prefix ---")
    W("        IfCondition EqualTo(enc_type, 1) ThenBlock: {")
    W("            pp_val    = X86Enc_Bits(desc_b, 0, 3)")
    W("            mmmmm_val = X86Enc_Bits(desc_b, 2, 31)")
    W("            vex_W     = X86Enc_Bits(desc_b, 7, 1)")
    W("            vex_L     = X86Enc_Bits(desc_b, 8, 3)")
    W("            vvvv_src  = X86Enc_Bits(desc_b, 10, 7)")
    W("            rex_R_src = X86Enc_Bits(desc_a, 35, 3)")
    W("            rex_B_src = X86Enc_Bits(desc_a, 37, 3)")
    W("            rex_X_src = X86Enc_Bits(desc_a, 39, 3)")
    W("            r_reg = X86Enc_OpVal(rex_R_src, op0,op1,op2,op3)")
    W("            b_reg = X86Enc_OpVal(rex_B_src, op0,op1,op2,op3)")
    W("            x_reg = X86Enc_OpVal(rex_X_src, op0,op1,op2,op3)")
    W("            vvvv_reg = 0")
    W("            IfCondition LessThan(vvvv_src, 7) ThenBlock: {")
    W("                vvvv_reg = X86Enc_OpVal(Add(vvvv_src,1), op0,op1,op2,op3)")
    W("            }")
    W("            can_2byte = 1")
    W("            IfCondition NotEqual(mmmmm_val, 1) ThenBlock: { can_2byte = 0 }")
    W("            IfCondition NotEqual(vex_W,     0) ThenBlock: { can_2byte = 0 }")
    W("            IfCondition GreaterThan(x_reg,  7) ThenBlock: { can_2byte = 0 }")
    W("            IfCondition GreaterThan(b_reg,  7) ThenBlock: { can_2byte = 0 }")
    W("            IfCondition EqualTo(can_2byte, 1) ThenBlock: {")
    W("                r_bit = 1")
    W("                IfCondition GreaterThan(r_reg, 7) ThenBlock: { r_bit = 0 }")
    W("                vvvv_inv = BitwiseAnd(BitwiseXor(vvvv_reg, 15), 15)")
    W("                byte2 = BitwiseOr(BitwiseOr(BitwiseOr(LeftShift(r_bit,7),LeftShift(vvvv_inv,3)),LeftShift(vex_L,2)),pp_val)")
    W("                Emit_Byte(0xC5)")
    W("                Emit_Byte(byte2)")
    W("            } ElseBlock: {")
    W("                r_bit = 1")
    W("                IfCondition GreaterThan(r_reg,7) ThenBlock: { r_bit = 0 }")
    W("                x_bit = 1")
    W("                IfCondition GreaterThan(x_reg,7) ThenBlock: { x_bit = 0 }")
    W("                b_bit = 1")
    W("                IfCondition GreaterThan(b_reg,7) ThenBlock: { b_bit = 0 }")
    W("                vvvv_inv = BitwiseAnd(BitwiseXor(vvvv_reg,15),15)")
    W("                b1 = BitwiseOr(BitwiseOr(BitwiseOr(LeftShift(r_bit,7),LeftShift(x_bit,6)),LeftShift(b_bit,5)),mmmmm_val)")
    W("                b2 = BitwiseOr(BitwiseOr(BitwiseOr(LeftShift(vex_W,7),LeftShift(vvvv_inv,3)),LeftShift(vex_L,2)),pp_val)")
    W("                Emit_Byte(0xC4)")
    W("                Emit_Byte(b1)")
    W("                Emit_Byte(b2)")
    W("            }")
    W("        }")
    W("")
    W("        // --- EVEX prefix ---")
    W("        IfCondition EqualTo(enc_type, 3) ThenBlock: {")
    W("            pp_val    = X86Enc_Bits(desc_b, 0, 3)")
    W("            mmmmm_val = X86Enc_Bits(desc_b, 2, 31)")
    W("            evex_W    = X86Enc_Bits(desc_b, 7, 1)")
    W("            evex_LL   = X86Enc_Bits(desc_b, 8, 3)")
    W("            vvvv_src  = X86Enc_Bits(desc_b, 10, 7)")
    W("            aaa_src   = X86Enc_Bits(desc_b, 13, 7)")
    W("            z_src     = X86Enc_Bits(desc_b, 16, 1)")
    W("            b_src_f   = X86Enc_Bits(desc_b, 17, 1)")
    W("            rex_R_src = X86Enc_Bits(desc_a, 35, 3)")
    W("            rex_B_src = X86Enc_Bits(desc_a, 37, 3)")
    W("            rex_X_src = X86Enc_Bits(desc_a, 39, 3)")
    W("            r_reg = X86Enc_OpVal(rex_R_src, op0,op1,op2,op3)")
    W("            b_reg = X86Enc_OpVal(rex_B_src, op0,op1,op2,op3)")
    W("            x_reg = X86Enc_OpVal(rex_X_src, op0,op1,op2,op3)")
    W("            vvvv_reg = 0")
    W("            IfCondition LessThan(vvvv_src,7) ThenBlock: {")
    W("                vvvv_reg = X86Enc_OpVal(Add(vvvv_src,1),op0,op1,op2,op3)")
    W("            }")
    W("            aaa_val = 0")
    W("            IfCondition NotEqual(aaa_src,0) ThenBlock: {")
    W("                aaa_val = BitwiseAnd(X86Enc_OpVal(aaa_src,op0,op1,op2,op3),7)")
    W("            }")
    W("            R1 = 1")
    W("            IfCondition GreaterThan(r_reg,7) ThenBlock: { R1 = 0 }")
    W("            R2 = 1")
    W("            IfCondition GreaterThan(r_reg,15) ThenBlock: { R2 = 0 }")
    W("            X1 = 1")
    W("            IfCondition GreaterThan(x_reg,7) ThenBlock: { X1 = 0 }")
    W("            B1 = 1")
    W("            IfCondition GreaterThan(b_reg,7) ThenBlock: { B1 = 0 }")
    W("            V2 = 1")
    W("            IfCondition GreaterThan(vvvv_reg,15) ThenBlock: { V2 = 0 }")
    W("            vvvv_inv = BitwiseAnd(BitwiseXor(vvvv_reg,15),15)")
    W("            p1 = BitwiseOr(BitwiseOr(BitwiseOr(BitwiseOr(LeftShift(R1,7),LeftShift(X1,6)),LeftShift(B1,5)),LeftShift(R2,4)),mmmmm_val)")
    W("            p2 = BitwiseOr(BitwiseOr(BitwiseOr(LeftShift(evex_W,7),LeftShift(vvvv_inv,3)),4),pp_val)")
    W("            p3 = BitwiseOr(BitwiseOr(BitwiseOr(BitwiseOr(BitwiseOr(LeftShift(z_src,7),LeftShift(evex_LL,5)),LeftShift(b_src_f,4)),LeftShift(V2,3)),aaa_val),0)")
    W("            Emit_Byte(0x62)")
    W("            Emit_Byte(p1)")
    W("            Emit_Byte(p2)")
    W("            Emit_Byte(p3)")
    W("        }")
    W("")
    W("        // --- Legacy prefix ---")
    W("        pfx = X86Enc_Bits(desc_a, 26, 255)")
    W("        IfCondition NotEqual(pfx, 0) ThenBlock: { Emit_Byte(pfx) }")
    W("")
    W("        // --- REX byte (non-VEX/EVEX) ---")
    W("        IfCondition EqualTo(enc_type, 0) ThenBlock: {")
    W("            rex_W     = X86Enc_Bits(desc_a, 34, 1)")
    W("            rex_R_src = X86Enc_Bits(desc_a, 35, 3)")
    W("            rex_B_src = X86Enc_Bits(desc_a, 37, 3)")
    W("            rex_X_src = X86Enc_Bits(desc_a, 39, 3)")
    W("            r_reg = X86Enc_OpVal(rex_R_src, op0,op1,op2,op3)")
    W("            b_reg = X86Enc_OpVal(rex_B_src, op0,op1,op2,op3)")
    W("            x_reg = X86Enc_OpVal(rex_X_src, op0,op1,op2,op3)")
    W("            need_rex = rex_W")
    W("            IfCondition GreaterThan(r_reg, 7) ThenBlock: { need_rex = 1 }")
    W("            IfCondition GreaterThan(b_reg, 7) ThenBlock: { need_rex = 1 }")
    W("            IfCondition GreaterThan(x_reg, 7) ThenBlock: { need_rex = 1 }")
    W("            IfCondition EqualTo(need_rex, 1) ThenBlock: {")
    W("                rex_byte = 0x40")
    W("                IfCondition EqualTo(rex_W, 1)     ThenBlock: { rex_byte = BitwiseOr(rex_byte, 8) }")
    W("                IfCondition GreaterThan(r_reg, 7) ThenBlock: { rex_byte = BitwiseOr(rex_byte, 4) }")
    W("                IfCondition GreaterThan(x_reg, 7) ThenBlock: { rex_byte = BitwiseOr(rex_byte, 2) }")
    W("                IfCondition GreaterThan(b_reg, 7) ThenBlock: { rex_byte = BitwiseOr(rex_byte, 1) }")
    W("                Emit_Byte(rex_byte)")
    W("            }")
    W("        }")
    W("")
    W("        // --- Opcode bytes ---")
    W("        n   = X86Enc_Bits(desc_a, 24, 3)")
    W("        o1  = X86Enc_Bits(desc_a,  0, 255)")
    W("        o2  = X86Enc_Bits(desc_a,  8, 255)")
    W("        o3  = X86Enc_Bits(desc_a, 16, 255)")
    W("        add = X86Enc_Bits(desc_a, 53, 7)")
    W("        IfCondition GreaterEqual(n, 1) ThenBlock: {")
    W("            IfCondition And(EqualTo(n,1), NotEqual(add,0)) ThenBlock: {")
    W("                av = BitwiseAnd(X86Enc_OpVal(add,op0,op1,op2,op3), 7)")
    W("                Emit_Byte(BitwiseOr(o1, av))")
    W("            } ElseBlock: { Emit_Byte(o1) }")
    W("        }")
    W("        IfCondition GreaterEqual(n, 2) ThenBlock: {")
    W("            IfCondition And(EqualTo(n,2), NotEqual(add,0)) ThenBlock: {")
    W("                av = BitwiseAnd(X86Enc_OpVal(add,op0,op1,op2,op3), 7)")
    W("                Emit_Byte(BitwiseOr(o2, av))")
    W("            } ElseBlock: { Emit_Byte(o2) }")
    W("        }")
    W("        IfCondition GreaterEqual(n, 3) ThenBlock: {")
    W("            IfCondition And(EqualTo(n,3), NotEqual(add,0)) ThenBlock: {")
    W("                av = BitwiseAnd(X86Enc_OpVal(add,op0,op1,op2,op3), 7)")
    W("                Emit_Byte(BitwiseOr(o3, av))")
    W("            } ElseBlock: { Emit_Byte(o3) }")
    W("        }")
    W("")
    W("        // --- ModRM ---")
    W("        IfCondition EqualTo(X86Enc_Bits(desc_a,41,1), 1) ThenBlock: {")
    W("            mode_is_op = X86Enc_Bits(desc_a, 44, 1)")
    W("            mode_val   = X86Enc_Bits(desc_a, 42, 3)")
    W("            IfCondition EqualTo(mode_is_op, 1) ThenBlock: { mode_val = 0 }")
    W("            reg_is_op  = X86Enc_Bits(desc_a, 48, 1)")
    W("            reg_f      = X86Enc_Bits(desc_a, 45, 7)")
    W("            rm_is_lit  = X86Enc_Bits(desc_a, 52, 1)")
    W("            rm_f       = X86Enc_Bits(desc_a, 49, 7)")
    W("            reg_val = reg_f")
    W("            IfCondition EqualTo(reg_is_op, 1) ThenBlock: {")
    W("                reg_val = BitwiseAnd(X86Enc_OpVal(Add(reg_f,1),op0,op1,op2,op3), 7)")
    W("            }")
    W("            rm_val = rm_f")
    W("            IfCondition EqualTo(rm_is_lit, 0) ThenBlock: {")
    W("                rm_val = BitwiseAnd(X86Enc_OpVal(Add(rm_f,1),op0,op1,op2,op3), 7)")
    W("            }")
    W("            modrm = BitwiseOr(BitwiseOr(LeftShift(mode_val,6),LeftShift(reg_val,3)),rm_val)")
    W("            Emit_Byte(modrm)")
    W("        }")
    W("")
    W("        // --- Immediate ---")
    W("        isz = X86Enc_Bits(desc_a, 56, 15)")
    W("        IfCondition NotEqual(isz, 0) ThenBlock: {")
    W("            iop = X86Enc_Bits(desc_a, 60, 3)")
    W("            iv  = X86Enc_OpVal(Add(iop,1), op0,op1,op2,op3)")
    W("            IfCondition EqualTo(isz, 1) ThenBlock: {")
    W("                Emit_Byte(BitwiseAnd(iv, 255))")
    W("            }")
    W("            IfCondition EqualTo(isz, 2) ThenBlock: {")
    W("                Emit_Byte(BitwiseAnd(iv, 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv, 8), 255))")
    W("            }")
    W("            IfCondition EqualTo(isz, 3) ThenBlock: {")
    W("                Emit_Byte(BitwiseAnd(iv, 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv,  8), 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv, 16), 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv, 24), 255))")
    W("            }")
    W("            IfCondition EqualTo(isz, 4) ThenBlock: {")
    W("                Emit_Byte(BitwiseAnd(iv, 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv,  8), 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv, 16), 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv, 24), 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv, 32), 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv, 40), 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv, 48), 255))")
    W("                Emit_Byte(BitwiseAnd(RightShift(iv, 56), 255))")
    W("            }")
    W("        }")
    W("        ReturnValue(1)")
    W("    }")
    W("}")
    W("")

    # -------------------------------------------------------------------------
    # Top-level: parse then emit
    # -------------------------------------------------------------------------
    W("Function.X86Enc_Assemble {")
    W("    Input: asm_str: Address")
    W("    Output: Integer")
    W("    Body: {")
    W("        key = X86Enc_ParseAsm(asm_str)")
    W("        ReturnValue(X86Enc_Emit(key))")
    W("    }")
    W("}")
    W("")

    with open(out_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"Written: {out_path}", file=sys.stderr)
    print(f"Lines: {len(lines)}", file=sys.stderr)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else \
        '/mnt/c/Users/Sean/Documents/AILangSH/Librarys/Compiler/CodeEmit/X86/Library.CEmitX86Enc.ailang'
    gen(out)
