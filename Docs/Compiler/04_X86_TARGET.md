# AILang Compiler — 04: X86-64 Target Layer

## Overview

The X86-64 target layer encodes raw x86-64 machine code bytes. It is called exclusively through the `CEmitCoreArch` wrapper layer — compile modules never call `X86_*()` functions directly.

```
Emit_AddRaxRbx() ──▶ X86_AddRaxRbx() ──▶ Emit_Byte(0x48); Emit_Byte(0x01); Emit_Byte(0xD8)
     (CEmitCoreArch)      (CEmitX86Arith)      (CEmitCore)
```

---

## 1. MODULE ORGANIZATION (12 files)

| Module | Size | Purpose |
|--------|------|---------|
| CEmitX86Reg | 27KB | Register moves, immediate loads |
| CEmitX86Mem | 41KB | Memory access, addressing modes |
| CEmitX86Stack | 13KB | Push, pop, prologue, epilogue |
| CEmitX86Arith | 16KB | ADD, SUB, IMUL, IDIV, NEG |
| CEmitX86Cmp | 11KB | CMP, TEST, SETcc |
| CEmitX86Jump | 8KB | JMP, Jcc, CALL, RET |
| CEmitX86Sys | 8KB | SYSCALL, INT, SYSENTER |
| CEmitX86Logic | 12KB | AND, OR, XOR, NOT, SHL, SHR, SAR |
| CEmitX86String | 7KB | REP MOVSB, REP CMPSB, SCASB |
| CEmitX86Macros | 9KB | Pseudo-instructions expanded to real sequences |
| CEmitX86Helpers | 4KB | Address computation helpers |
| CEmitX86Debug | 8KB | Debug info (dwarf line programs) |

---

## 2. INSTRUCTION ENCODING PATTERN

Every `X86_*()` function follows this pattern:

```
Function.X86_AddRaxRbx {
    Body: {
        // ADD RAX, RBX = 48 01 D8
        Emit_Byte(0x48)   // REX.W prefix (64-bit operand size)
        Emit_Byte(0x01)   // ADD r/m64, r64 opcode
        Emit_Byte(0xD8)   // ModRM: mod=11, reg=RBX(3), r/m=RAX(0)
    }
}
```

### 2.1 REX Prefix Encoding
```
REX byte: 0 1 0 0 W R X B
  W=1: 64-bit operand size
  R=1: extends ModRM.reg field
  X=1: extends SIB.index field
  B=1: extends ModRM.r/m field or SIB.base
```

### 2.2 ModRM Byte Encoding
```
ModRM: mod(2) reg(3) r/m(3)
  mod=00: [register] indirect or [R/M] (no displacement unless r/m=101→disp32)
  mod=01: [register+disp8]
  mod=10: [register+disp32]
  mod=11: register direct
  reg: register operand (or opcode extension for some instructions)
  r/m: register or memory operand
```

### 2.3 Common Encoding Patterns
```
MOV Reg, Imm64:  REX.W B8+reg <8-byte imm>
MOV Reg, Reg:    REX.W 89 <ModRM: mod=11, reg=src, r/m=dst>
ADD Reg, Reg:    REX.W 01 <ModRM: mod=11, reg=src, r/m=dst>
CMP Reg, Reg:    REX.W 39 <ModRM: mod=11, reg=src, r/m=dst>
PUSH Reg:        50+reg  (no REX needed for REX.B offset)
POP Reg:         58+reg
JMP rel8:        EB <rel8>
Jcc rel8:        70+cc <rel8> for 8-bit offset
                0F 80+cc <rel32> for 32-bit offset
CALL rel32:     E8 <rel32>
RET:            C3
SYSCALL:        0F 05
NOP:            90
```

---

## 3. MODULE DETAILS

### 3.1 CEmitX86Reg — Register Operations (27KB)

**Direct register moves:**
```
X86_MovRaxRbx:   MOV RAX, RBX  = 48 89 D8
X86_MovRbxRax:   MOV RBX, RAX  = 48 89 C3
X86_MovRcxRax:   MOV RCX, RAX  = 48 89 C1
X86_MovRdxRax:   MOV RDX, RAX  = 48 89 C2
... (all 16×16 register combinations)
```

**Immediate loads:**
```
X86_MovRaxImm64(val):  48 B8 <val:8>     (MOV RAX, imm64 — 10 bytes)
X86_MovRbxImm64(val):  48 BB <val:8>
X86_MovRcxImm64(val):  48 B9 <val:8>
X86_MovRdxImm64(val):  48 BA <val:8>
X86_MovRdiImm64(val):  48 BF <val:8>
X86_MovRsiImm64(val):  48 BE <val:8>
X86_MovR8Imm64(val):   49 B8 <val:8>     (REX.B for R8-R15)
X86_MovR9Imm64(val):   49 B9 <val:8>
X86_MovR10Imm64(val):  49 BA <val:8>
```

**Zeroing (optimized – no immediate):**
```
X86_XorRaxRax:  48 31 C0          (3 bytes, better than MOV RAX,0 = 7 bytes)
X86_XorRbxRbx:  48 31 DB
X86_XorRcxRcx:  48 31 C9
X86_XorRdxRdx:  48 31 D2
```

### 3.2 CEmitX86Mem — Memory Operations (41KB)

**Memory-indirect loads:**
```
X86_MovRaxDerefRax():   48 8B 00     MOV RAX, [RAX]
X86_MovRaxDerefRbx():   48 8B 03     MOV RAX, [RBX]
X86_MovRaxDerefRbpOffset(off):
    If off fits in 8 bits:  48 8B 45 <off:1>
    Else:                   48 8B 85 <off:4>

X86_MovRbpOffsetRax(off):           // [RBP+off] = RAX
    If off fits in 8 bits:  48 89 45 <off:1>
    Else:                   48 89 85 <off:4>

X86_MovDerefRdiRax():     48 89 07     MOV [RDI], RAX
X86_MovDerefRdiAl():      88 07        MOV [RDI], AL

X86_MovAlDerefRdi():      8A 07        MOV AL, [RDI]
X86_MovAlDerefRsi():      8A 06        MOV AL, [RSI]
X86_MovBlDerefRsi():      8A 1E        MOV BL, [RSI]
```

**RSP-relative (stack peeking):**
```
X86_MovRaxDerefRsp():     48 8B 04 24  MOV RAX, [RSP]
```

**Indexed addressing:**
```
X86_MovRaxDerefRbxRcxScaled(scale):   // MOV RAX, [RBX + RCX*scale]
    Scale must be 1,2,4,8
    Encodes via SIB byte
```

**Byte operations:**
```
X86_MovByteDerefRdiZero():  C6 07 00     MOV BYTE [RDI], 0
X86_MovByteDerefRdiImm8(v): C6 07 <v>    MOV BYTE [RDI], imm8
```

### 3.3 CEmitX86Stack — Stack Operations (13KB)

```
X86_PushRax:  50      (1 byte)
X86_PushRbx:  53
X86_PushRcx:  51
X86_PushRdx:  52
X86_PushRbp:  55
X86_PushRsi:  56
X86_PushRdi:  57
X86_PushR12:  41 54   (2 bytes, REX prefix)
X86_PushR13:  41 55
X86_PushR14:  41 56
X86_PushR15:  41 57

X86_PopRax:   58
X86_PopRbx:   5B
(etc.)

X86_MovRbpRsp:  48 89 E5   MOV RBP, RSP
X86_MovRspRbp:  48 89 EC   MOV RSP, RBP
X86_SubRaxImm8(val):  48 83 E8 <val>   SUB RAX, imm8

X86_LeaRaxRbpOffset(off):
    48 8D 85 <off:4>   LEA RAX, [RBP+off]

X86_LeaRspRbpOffset(off):
    48 8D A5 <off:4>   LEA RSP, [RBP+off]
```

### 3.4 CEmitX86Arith — Arithmetic (16KB)

```
X86_AddRaxRbx:   48 01 D8     ADD RAX, RBX
X86_AddRaxRcx:   48 01 C8     ADD RAX, RCX
X86_AddRaxR12:   4C 01 E0     ADD RAX, R12
X86_AddRaxR13:   4C 01 E8     ADD RAX, R13
X86_AddRaxImm32: 48 05 <v:4>  ADD RAX, imm32
X86_AddRaxImm8:  48 83 C0 <v> ADD RAX, imm8

X86_SubRaxRbx:   48 29 D8     SUB RAX, RBX
X86_SubRaxR8:    4C 29 C0     SUB RAX, R8

X86_ImulRaxRbx:  48 0F AF C3  IMUL RAX, RBX
X86_IdivRbx:     48 F7 FB     IDIV RBX (uses RDX:RAX as dividend)
X86_Cqo:         48 99        CQO (sign-extend RAX → RDX:RAX)
X86_NegRax:      48 F7 D8     NEG RAX

X86_IncRax:      48 FF C0     INC RAX
X86_IncRbx:      48 FF C3     INC RBX
X86_IncRcx:      48 FF C1     INC RCX
X86_IncRdi:      48 FF C7     INC RDI
X86_IncRsi:      48 FF C6     INC RSI
X86_DecRax:      48 FF C8     DEC RAX
```

### 3.5 CEmitX86Cmp — Comparison (11KB)

```
X86_CmpRaxRbx:   48 39 D8     CMP RAX, RBX
X86_CmpRaxRcx:   48 39 C8     CMP RAX, RCX
X86_CmpRbxRax:   48 39 C3     CMP RBX, RAX

X86_TestRaxRax:  48 85 C0     TEST RAX, RAX
X86_TestRbxRbx:  48 85 DB     TEST RBX, RBX

X86_TestAlAl:    84 C0        TEST AL, AL
X86_CmpAlBl:     38 D8        CMP AL, BL
```

### 3.6 CEmitX86Jump — Control Flow (8KB)

```
X86_Jmp(label):      E9 <rel32>     JMP rel32 [+ fixup REL32]
X86_JmpRel8(label):  EB <rel8>      JMP rel8 [+ fixup REL8]
X86_Je(label):       0F 84 <rel32>  JE rel32
X86_Jz(label):       0F 84 <rel32>  JZ rel32
X86_Jne(label):      0F 85 <rel32>  JNE rel32
X86_Jl(label):       0F 8C <rel32>  JL rel32
X86_Jle(label):      0F 8E <rel32>  JLE rel32
X86_Jg(label):       0F 8F <rel32>  JG rel32
X86_Jge(label):      0F 8D <rel32>  JGE rel32
X86_Js(label):       0F 88 <rel32>  JS rel32

X86_Call(label):     E8 <rel32>     CALL rel32
X86_Ret():           C3             RET
```

### 3.7 CEmitX86Sys — System Instructions (8KB)

```
X86_Syscall():  0F 05    SYSCALL
```

### 3.8 CEmitX86Logic — Bitwise Logic (12KB)

```
X86_AndRaxRbx:   48 21 D8     AND RAX, RBX
X86_OrRaxRbx:    48 09 D8     OR RAX, RBX
X86_XorRaxRbx:   48 31 D8     XOR RAX, RBX
X86_NotRax:      48 F7 D0     NOT RAX

X86_ShlRaxImm8(v):  48 C1 E0 <v>   SHL RAX, imm8
X86_ShlRcxImm8(v):  48 C1 E1 <v>   SHL RCX, imm8
X86_SarRaxCl:       48 D3 F8        SAR RAX, CL
```

---

## 4. FUNCTION PROLOGUE/EPILOGUE PATTERN

Generated by CompileFunc_Define:

```
PROLOGUE:
    55                   PUSH RBP
    48 89 E5             MOV RBP, RSP
    48 83 EC <size>      SUB RSP, <stack_size>

    // Load parameters from registers to stack slots
    48 89 7D <off0>      MOV [RBP+off0], RDI   (param 1)
    48 89 75 <off1>      MOV [RBP+off1], RSI   (param 2)
    48 89 55 <off2>      MOV [RBP+off2], RDX   (param 3)
    48 89 4D <off3>      MOV [RBP+off3], RCX   (param 4)

    ... body code ...

EPILOGUE:
    48 89 EC             MOV RSP, RBP
    5D                   POP RBP
    C3                   RET
```

---

## 5. SYSCALL CONVENTION (Linux x86-64)

```
RAX = syscall number
RDI = arg1, RSI = arg2, RDX = arg3, R10 = arg4, R8 = arg5, R9 = arg6
RCX and R11 are clobbered by SYSCALL
Return value in RAX

Example — write(1, "hello", 5):
    48 C7 C0 01 00 00 00    MOV RAX, 1        (sys_write)
    48 C7 C7 01 00 00 00    MOV RDI, 1        (stdout)
    48 8D 35 <data_off>     LEA RSI, [RIP+data_offset]
    48 C7 C2 05 00 00 00    MOV RDX, 5        (count)
    0F 05                   SYSCALL
```

---

*Document 04 of 10 — X86-64 Target Layer*
