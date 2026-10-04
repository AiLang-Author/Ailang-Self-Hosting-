#!/usr/bin/env python3
"""Insert Listing_Open/Close around leaf emitters in CEmitKeep.

Idempotent. Wrappers that only call another X86_* helper are left alone,
so a JE still records once, inside X86_Jcc. Re-run after adding a helper.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEP = ROOT / "Librarys/Compiler/CodeEmit/X86/Library.CEmitKeep.ailang"

OPCODES = [
    "MOVZX", "MOVSXD", "MOVSX", "IMUL", "IDIV", "SYSCALL", "CPUID",
    "RDTSC", "RDTSCP", "CQO", "RET", "NOP", "PUSH", "POP", "CALL", "JMP",
    "LEA", "TEST", "CMP", "ADD", "SUB", "XOR", "AND", "OR", "NOT", "NEG",
    "MUL", "DIV", "INC", "DEC", "SHL", "SHR", "SAR", "INT3", "CLD", "STD",
    "MOV", "XCHG", "REP",
]
REGS = [
    "R15", "R14", "R13", "R12", "R11", "R10", "R9", "R8",
    "RAX", "RBX", "RCX", "RDX", "RSI", "RDI", "RBP", "RSP",
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP",
    "AX", "BX", "CX", "DX", "AL", "BL", "CL", "DL", "AH", "BH", "CH", "DH",
    "XMM0", "XMM1", "XMM2", "XMM3",
]
EMIT_MARKS = ("Emit_Byte", "Emit_Word", "Emit_DWord", "Emit_QWord", "Emit_AddFixup")


def parse_name(name: str) -> str | None:
    body = name[4:] if name.startswith("X86_") else name
    up = body.upper()
    op = None
    rest = ""
    for cand in OPCODES:
        if up.startswith(cand):
            op = cand
            rest = body[len(cand):]
            break
    if op is None:
        return None
    toks: list[str] = []
    s = rest
    while s:
        hit = None
        for r in REGS:
            if s.upper().startswith(r):
                toks.append(r.lower())
                s = s[len(r):]
                hit = r
                break
        if hit:
            continue
        for imm in ("Imm64", "Imm32", "Imm8", "Imm"):
            if s.startswith(imm):
                toks.append("IMM")
                s = s[len(imm):]
                hit = imm
                break
        if hit:
            continue
        if s.startswith("DataOffset"):
            toks.append("DATA")
            s = s[len("DataOffset"):]
            continue
        if s.startswith("Label"):
            toks.append("LABEL")
            s = s[len("Label"):]
            continue
        if s.startswith("RegReg"):
            toks.append("R1")
            toks.append("R2")
            s = s[len("RegReg"):]
            continue
        break
    if s:
        return None
    if not toks:
        return op
    parts = [op]
    for i, t in enumerate(toks):
        if i == 0:
            parts.append(" ")
        else:
            parts.append(", ")
        parts.append(t)
    return "".join(parts)


def clean_comment(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    if not s.startswith("//"):
        return None
    s = s[2:].strip()
    if not s or s.startswith("=") or set(s) <= {"=", "-", " "}:
        return None
    if "=" in s:
        s = s.split("=", 1)[0].strip()
    if not s or "(" in s:
        return None
    tok = s.split()[0].strip(",")
    if not tok or not tok[0].isalpha():
        return None
    if tok.upper() != tok:
        return None
    return s


# Comments above these helpers often describe the previous function.
# The name is the mnemonic. The comment is only a last resort.
SPECIAL = {
    "X86_SysInstr": "SYSCALL",
    "X86_AndRspAlignment": "AND rsp, -16",
    "X86_Cld": "CLD",
    "X86_Std": "STD",
    "X86_Cpuid": "CPUID",
    "X86_Rdtsc": "RDTSC",
    "X86_Rdtscp": "RDTSCP",
    "X86_Int3": "INT3",
    "X86_Nop": "NOP",
    "X86_Mfence": "MFENCE",
    "X86_Sfence": "SFENCE",
    "X86_Lfence": "LFENCE",
    "X86_Leave": "LEAVE",
    "X86_Cqo": "CQO",
    "X86_Cdq": "CDQ",
    "X86_RepMovsb": "REP MOVSB",
    "X86_RepStosb": "REP STOSB",
    "X86_RepMovsq": "REP MOVSQ",
}


def mnemonic(name: str, comment: str | None) -> str:
    if name in SPECIAL:
        return SPECIAL[name]
    parsed = parse_name(name)
    if parsed:
        return parsed
    cleaned = clean_comment(comment)
    if cleaned:
        return cleaned
    return name[4:]


def quote_text(text: str) -> str:
    return text.replace('"', "'")


def open_block(name: str, params: list[str], comment: str | None) -> list[str]:
    """AILANG lines, 8-space indent, that leave the mnemonic in mtxt."""
    if name == "X86_Jcc":
        return [
            '        cname = Listing_CcName(cc)',
            '        nstr = NumberToString(label_id)',
            '        mtxt = StringConcat(cname, " .L")',
            '        mtxt = StringConcat(mtxt, nstr)',
            '        Listing_Open(mtxt)',
        ]
    if "DataOffset" in name or name.endswith("LoadDataAddress") or "DataAddress" in name:
        text = mnemonic(name, comment).replace("DATA", "data")
        if "data" not in text.lower():
            text = text + ", data"
        text = quote_text(text)
        return [
            f'        mtxt = "{text}"',
            '        Listing_Open(mtxt)',
        ]
    if params == ["label_id"]:
        base = mnemonic(name, comment)
        op = base.split()[0]
        if op == "LEA":
            return [
                '        nstr = NumberToString(label_id)',
                '        mtxt = StringConcat("LEA rax, .L", nstr)',
                '        Listing_Open(mtxt)',
            ]
        return [
            f'        nstr = NumberToString(label_id)',
            f'        mtxt = StringConcat("{op} .L", nstr)',
            '        Listing_Open(mtxt)',
        ]
    reg_params = [p for p in params if p in ("dst", "src", "reg1", "reg2")]
    if len(params) == 2 and len(reg_params) == 2:
        op = mnemonic(name, comment).split()[0]
        a, b = params[0], params[1]
        return [
            f'        rd = Listing_RegName({a})',
            f'        rs = Listing_RegName({b})',
            f'        mtxt = StringConcat("{op} ", rd)',
            '        mtxt = StringConcat(mtxt, ", ")',
            '        mtxt = StringConcat(mtxt, rs)',
            '        Listing_Open(mtxt)',
        ]
    imm_params = [p for p in params if p in ("imm", "offset", "val", "value", "disp", "stack_size")]
    if len(params) == 1 and len(imm_params) == 1:
        base = parse_name(name)
        if base and "IMM" in base:
            prefix = base.replace("IMM", "").rstrip(", ").rstrip()
            if not prefix.endswith(","):
                prefix = prefix + ", "
            else:
                prefix = prefix + " "
            return [
                f'        nstr = NumberToString({imm_params[0]})',
                f'        mtxt = StringConcat("{prefix}", nstr)',
                '        Listing_Open(mtxt)',
            ]
    text = quote_text(mnemonic(name, comment))
    return [
        f'        mtxt = "{text}"',
        '        Listing_Open(mtxt)',
    ]


def match_brace(text: str, open_at: int) -> int:
    depth = 0
    i = open_at
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise RuntimeError(f"unbalanced brace at {open_at}")


def main() -> None:
    text = KEEP.read_text()
    if "LibraryImport.Compiler.CodeEmit.CListing" not in text:
        text = text.replace(
            "LibraryImport.Compiler.CodeEmit.CEmitCore\n",
            "LibraryImport.Compiler.CodeEmit.CEmitCore\n"
            "LibraryImport.Compiler.CodeEmit.CListing\n",
            1,
        )
    starts = [m.start() for m in re.finditer(r"^Function\.X86_", text, re.M)]
    # Insert from the bottom so offsets stay valid.
    for start in reversed(starts):
        brace = text.find("{", start)
        end = match_brace(text, brace)
        header = text[start:brace]
        name = header.split()[0][len("Function."):]
        body = text[brace:end + 1]
        if "Listing_Open(" in body:
            continue
        if not any(mark in body for mark in EMIT_MARKS):
            continue
        params = re.findall(r"Input:\s*([A-Za-z0-9_]+)\s*:", body)
        # Comment is the nearest // line above the function, skipping blanks.
        prev = text.rfind("\n", 0, start)
        comment = None
        scan = prev
        while scan > 0:
            line_start = text.rfind("\n", 0, scan) + 1
            line = text[line_start:scan].strip()
            scan = line_start - 1
            if not line:
                continue
            if line.startswith("//"):
                comment = line
            break
        lines = open_block(name, params, comment)
        block = "\n".join(lines) + "\n"
        body_key = text.find("Body:", start, end)
        body_brace = text.find("{", body_key)
        # Insert open just after Body's brace.
        insert_at = body_brace + 1
        if text[insert_at:insert_at + 1] == "\n":
            text = text[:insert_at + 1] + block + text[insert_at + 1:]
        else:
            text = text[:insert_at] + "\n" + block + text[insert_at:]
        # Close before Body's brace, so the call is inside the function.
        body_key = text.find("Body:", start)
        body_brace = text.find("{", body_key)
        body_end = match_brace(text, body_brace)
        close = "        Listing_Close()\n"
        text = text[:body_end] + close + text[body_end:]
    KEEP.write_text(text)
    print(f"wrote {KEEP}")


if __name__ == "__main__":
    main()
