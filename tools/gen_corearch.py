#!/usr/bin/env python3
"""Generate CEmitCoreArch.ailang.

Class A Emit_* wrappers call X86Enc_Assemble.
Class B/C (mem, labels, composites, runtime-reg) keep X86_* calls.

Do not hand-edit the generated CoreArch. Re-run this script.
Does not modify CEmitX86Enc.ailang.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Frozen pre-wrap CoreArch (X86_* bodies). Never overwrite this from the generator.
SRC = ROOT / "Librarys/Compiler/CodeEmit/Library.CEmitCoreArch.hand.ailang"
OUT = ROOT / "Librarys/Compiler/CodeEmit/Library.CEmitCoreArch.ailang"

OPCODES = [
    "MOVZX", "MOVSXD", "MOVSX", "IMUL", "IDIV", "CMOVE", "CMOVNE",
    "CMOVL", "CMOVG", "CMOVLE", "CMOVGE", "PUSHFQ", "POPFQ",
    "RDTSCP", "RDTSC", "CPUID", "MFENCE", "LFENCE", "SFENCE",
    "SYSCALL", "CQO", "CDQE", "CDQ", "LEAVE", "RET", "NOP",
    "PUSH", "POP", "CALL", "JMP", "LEA", "TEST", "CMP",
    "ADD", "SUB", "XOR", "AND", "OR", "NOT", "NEG", "MUL", "DIV",
    "INC", "DEC", "SHL", "SHR", "SAR", "ROL", "ROR", "BT", "BTS", "BTR",
    "INT3", "INT", "UD2", "CLC", "STC", "CMC", "CLD", "STD", "LAHF", "SAHF",
    "MOV", "XCHG",
]

REGS = [
    "R15", "R14", "R13", "R12", "R11", "R10", "R9", "R8",
    "RAX", "RBX", "RCX", "RDX", "RSI", "RDI", "RBP", "RSP",
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP",
    "AX", "BX", "CX", "DX", "AL", "BL", "CL", "DL", "AH", "BH", "CH", "DH",
    "XMM0", "XMM1", "XMM2", "XMM3",
]


def split_camel(rest: str) -> list[str]:
    """Split X86_AddRaxRbx remainder after opcode into reg/imm tokens."""
    tokens = []
    s = rest
    while s:
        hit = None
        for r in REGS:
            if s.upper().startswith(r):
                # original casing length
                hit = s[: len(r)]
                tokens.append(hit.lower() if hit.upper() == r else hit)
                s = s[len(r) :]
                break
        if hit:
            continue
        if s.startswith("Imm64") or s.startswith("Imm32") or s.startswith("Imm8"):
            tokens.append("IMM")
            s = s[5:] if s.startswith("Imm6") or s.startswith("Imm3") else s[4:]
            if s.startswith("4") or s.startswith("2") or s.startswith("8"):
                # Imm64 consumed as Imm + 64 leftover
                pass
            continue
        if s.startswith("Neg1"):
            tokens.append("-1")
            s = s[4:]
            continue
        if s[0].isdigit():
            tokens.append(s[0])
            s = s[1:]
            continue
        # unknown
        tokens.append(s)
        break
    return tokens


def parse_x86_name(x86: str) -> tuple[str, list[str]] | None:
    if not x86.startswith("X86_"):
        return None
    body = x86[4:]
    up = body.upper()
    op = None
    for cand in OPCODES:
        if up.startswith(cand):
            op = cand
            rest = body[len(cand) :]
            break
    if op is None:
        return None
    toks = split_camel(rest) if rest else []
    # fix Imm64 split: Imm + leftover 4 from Imm64 if we used Imm8 logic badly
    cleaned = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "IMM":
            cleaned.append("IMM")
        else:
            cleaned.append(t)
        i += 1
    return op, cleaned


KEEP_SUBSTR = (
    "Deref", "Offset", "Rip", "Label", "Prologue", "Epilogue",
    "Volatile", "CalleeSaved", "DataAddress", "Fixup", "Scaled",
    "Byte", "Word", "Dword", "Sized", "JumpTo", "Align", "NopN",
    "RegReg", "RegImm", "NegReg", "NotReg", "IncReg", "DecReg",
    "IdivReg", "DivReg", "Store", "Load", "AllocStack", "FreeStack",
    "Lock", "Xchg", "Macro", "SETUP", "SAVE", "RESTORE", "COMPARE",
    "INCREMENT", "RETURN", "Broadcast", "PushXMM", "PopXMM",
)


def should_keep(emit_name: str, x86: str, inputs: list[str]) -> bool:
    if "label" in " ".join(inputs).lower() or "label_id" in inputs:
        return True
    if emit_name.startswith("Emit_Rep"):
        return True
    # Enc zero-operand keys are "SYSCALL_" / "RET_"; Assemble("SYSCALL") looks up "SYSCALL"
    if emit_name in ("Emit_Ret", "Emit_Syscall", "Emit_SysInstr", "Emit_Cqo"):
        return True
    # Enc table is SHL_r64_cl; Assemble("SHL rax, cl") builds SHL_r64_r8
    if emit_name.endswith("RaxCl") or emit_name.endswith("Cl"):
        if "Shl" in emit_name or "Shr" in emit_name or "Sar" in emit_name:
            return True
    # AND RSP, imm8 0xF0 is sign-extended -16. Assemble("AND rsp, 240") zero-extends.
    if "AndRsp" in emit_name:
        return True
    if any(s in emit_name for s in (
        "Jmp", "Je", "Jne", "Jz", "Jnz", "Jl", "Jle", "Jg", "Jge",
        "Jb", "Jbe", "Ja", "Jae", "Js", "Jns", "Jo", "Jno", "Call",
        "Prologue", "Epilogue", "LeaRaxRip", "LeaRsiRip", "LeaRdiRip",
        "LeaRaxLabel", "LoadData", "JumpToLabel",
        "AddRegReg", "MovRegReg", "XorRegReg", "CmpRegReg", "TestRegReg",
        "MovRegImm", "AddRegImm", "SubRegImm",
        "NegReg", "NotReg", "IncReg", "DecReg", "IdivReg", "DivReg",
        "Store", "LoadSized", "LoadByte", "StoreByte", "StoreSized",
        "AllocStack", "FreeStack", "PushVolatile", "PopVolatile",
        "PushCallee", "PopCallee", "AlignCode", "NopN",
    )):
        if emit_name in ("Emit_CallRax", "Emit_JmpRax", "Emit_Ret"):
            return False
        if emit_name.startswith("Emit_J") or emit_name == "Emit_Call" or emit_name == "Emit_Prologue":
            return True
        if "RegReg" in emit_name or "RegImm" in emit_name:
            return True
        if emit_name in (
            "Emit_NegReg", "Emit_NotReg", "Emit_IncReg", "Emit_DecReg",
            "Emit_IdivReg", "Emit_DivReg", "Emit_JumpToLabel",
            "Emit_AllocStack", "Emit_FreeStack",
        ):
            return True
        if "Store" in emit_name or "LoadByte" in emit_name or "LoadSized" in emit_name:
            return True
        if "Rip" in emit_name or "DataAddress" in emit_name or "Label" in emit_name:
            return True
        if "Volatile" in emit_name or "Callee" in emit_name or "Epilogue" in emit_name:
            return True
    if "Deref" in emit_name or "Offset" in emit_name:
        return True
    if "Byte" in emit_name and "Imm" in emit_name:
        return True
    return False


def asm_for(x86: str, inputs: list[str]) -> str | None:
    parsed = parse_x86_name(x86)
    if not parsed:
        # zero-operand known
        special = {
            "X86_Sete": "SETE al",
            "X86_Setne": "SETNE al",
            "X86_Setl": "SETL al",
            "X86_Setle": "SETLE al",
            "X86_Setg": "SETG al",
            "X86_Setge": "SETGE al",
            "X86_Setz": "SETZ al",
            "X86_Setnz": "SETNZ al",
            "X86_Setb": "SETB al",
            "X86_Setbe": "SETBE al",
            "X86_Seta": "SETA al",
            "X86_Setae": "SETAE al",
            "X86_Sets": "SETS al",
            "X86_Setns": "SETNS al",
            "X86_SysInstr": "SYSCALL",
            "X86_CallRax": "CALL rax",
            "X86_JmpRax": "JMP rax",
            "X86_Cld": "CLD",
            "X86_RepMovsb": "REP MOVSB",
            "X86_RepStosb": "REP STOSB",
            "X86_RepMovsq": "REP MOVSQ",
            "X86_RepStosq": "REP STOSQ",
            "X86_RepeCmpsb": "REPE CMPSB",
            "X86_RepneScasb": "REPNE SCASB",
            "X86_Mfence": "MFENCE",
            "X86_Cqo": "CQO",
            "X86_Ret": "RET",
            "X86_Leave": "LEAVE",
            "X86_Nop": "NOP",
            "X86_Int3": "INT3",
            "X86_Ud2": "UD2",
            "X86_Clc": "CLC",
            "X86_Stc": "STC",
            "X86_Cmc": "CMC",
            "X86_Cld": "CLD",
            "X86_Std": "STD",
            "X86_Lahf": "LAHF",
            "X86_Sahf": "SAHF",
            "X86_Pushfq": "PUSHFQ",
            "X86_Popfq": "POPFQ",
            "X86_Cpuid": "CPUID",
            "X86_Rdtsc": "RDTSC",
            "X86_Rdtscp": "RDTSCP",
            "X86_Mfence": "MFENCE",
            "X86_Lfence": "LFENCE",
            "X86_Sfence": "SFENCE",
            "X86_Syscall": "SYSCALL",
        }
        return special.get(x86)
    op, toks = parsed
    # filter leftover garbage
    if any(len(t) > 4 and t not in ("IMM",) and t.upper() not in [r.lower() for r in REGS] and t not in ("-1",) and not t.isdigit() for t in toks):
        # might still be ok if IMM only extra
        if not all(t in ("IMM", "-1") or t.isdigit() or t.lower() in [r.lower() for r in REGS] for t in toks):
            return None
    regs = [t for t in toks if t not in ("IMM",) and not t.isdigit() and t != "-1"]
    imms = [t for t in toks if t in ("IMM", "-1") or t.isdigit()]
    parts = [op]
    if regs:
        parts.append(", ".join(regs))
    if imms:
        # template
        if any(t == "IMM" for t in imms):
            if not inputs:
                return None
            if regs:
                return f"{op} {', '.join(regs)}, {{IMM}}"
            return f"{op} {{IMM}}"
        # literal 1 / -1
        lit = imms[0]
        if regs:
            return f"{op} {', '.join(regs)}, {lit}"
        return f"{op} {lit}"
    if len(regs) == 1 and op in ("PUSH", "POP", "INC", "DEC", "NEG", "NOT", "MUL", "DIV", "IDIV", "CALL", "JMP"):
        return f"{op} {regs[0]}"
    if len(regs) == 2:
        return f"{op} {regs[0]}, {regs[1]}"
    if len(regs) == 0 and op in (
        "CQO", "RET", "NOP", "LEAVE", "CDQE", "CLD", "STD", "CLC", "STC",
        "CMC", "LAHF", "SAHF", "PUSHFQ", "POPFQ", "CPUID", "RDTSC", "RDTSCP",
        "MFENCE", "LFENCE", "SFENCE", "SYSCALL", "INT3", "UD2",
    ):
        return op
    if len(regs) == 1 and op == "MOV" and not imms:
        return None
    return None


def emit_assemble_body(asm: str, inputs: list[str], indent: str) -> str:
    lines = []
    i = indent
    lines.append(f"{i}IfCondition EqualTo(Emit.target, 1) ThenBlock: {{")
    if "{IMM}" in asm:
        pre, _, _ = asm.partition("{IMM}")
        # pre includes trailing space after comma
        lines.append(f'{i}    asm = "{pre}"')
        arg = inputs[0]
        lines.append(f"{i}    nstr = NumberToString({arg})")
        lines.append(f"{i}    asm = StringConcat(asm, nstr)")
        lines.append(f"{i}    X86Enc_Assemble(asm)")
    else:
        lines.append(f'{i}    X86Enc_Assemble("{asm}")')
    lines.append(f"{i}}}")
    return "\n".join(lines)


def split_functions(text: str) -> tuple[str, list[str]]:
    idx = text.find("\nFunction.")
    if idx < 0:
        raise SystemExit("no functions")
    header = text[: idx + 1]
    rest = text[idx + 1 :]
    chunks = re.split(r"(?=^Function\.)", rest, flags=re.M)
    return header, [c for c in chunks if c.strip()]


def fn_meta(chunk: str) -> tuple[str, list[str], str]:
    m = re.match(r"Function\.(\w+)", chunk)
    name = m.group(1) if m else ""
    inputs = re.findall(r"Input:\s+(\w+)", chunk)
    xs = re.findall(r"(X86_\w+)\(", chunk)
    x86 = xs[0] if xs else ""
    return name, inputs, x86


def main() -> None:
    text = SRC.read_text()
    header, chunks = split_functions(text)
    # inject Enc import if missing
    if "CEmitX86Enc" not in header:
        header = header.replace(
            "LibraryImport.Compiler.CodeEmit.X86.CEmitX86Helpers\n",
            "LibraryImport.Compiler.CodeEmit.X86.CEmitX86Helpers\n"
            "LibraryImport.Compiler.CodeEmit.X86.CEmitX86Enc\n",
        )
    header = header.replace("Library.CEmitCoreArch.hand.ailang", "Library.CEmitCoreArch.ailang")
    if "AUTO-GENERATED" not in header:
        header = (
            "// AUTO-GENERATED by tools/gen_corearch.py — DO NOT HAND-EDIT.\n"
            "// Class A → X86Enc_Assemble. Class B/C → CEmitKeep X86_* helpers.\n"
            + header
        )

    stats = {"assemble": 0, "keep": 0, "unmapped": 0}
    out_chunks = []
    log = []
    for chunk in chunks:
        name, inputs, x86 = fn_meta(chunk)
        keep = should_keep(name, x86, inputs)
        asm = None if keep or not x86 else asm_for(x86, inputs)
        if keep or not asm:
            if not keep and x86:
                stats["unmapped"] += 1
                log.append(f"KEEP-UNMAPPED {name} {x86}")
            else:
                stats["keep"] += 1
                log.append(f"KEEP {name}")
            out_chunks.append(chunk if chunk.endswith("\n") else chunk + "\n")
            continue
        stats["assemble"] += 1
        log.append(f"ASM {name} => {asm}")
        # rebuild function from original signature lines
        # take everything up to Body: { then replace body inner if-target block
        m = re.search(r"(Function\.\w+[^{]*\{.*?Body:\s*\{)", chunk, re.S)
        if not m:
            out_chunks.append(chunk)
            stats["assemble"] -= 1
            stats["keep"] += 1
            continue
        prefix = m.group(1)
        body = emit_assemble_body(asm, inputs, "        ")
        new = prefix + "\n" + body + "\n    }\n}\n\n"
        out_chunks.append(new)

    OUT.write_text(header + "".join(out_chunks))
    print("wrote", OUT)
    print(stats)
    Path("/tmp/gen_corearch.log").write_text("\n".join(log))
    print("log /tmp/gen_corearch.log lines", len(log))


if __name__ == "__main__":
    main()
