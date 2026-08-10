# AILang Compiler — 03: Emit Layer (Code Emission Infrastructure)

## Overview

The emit layer provides architecture-agnostic code emission infrastructure. It manages code/data buffers, labels, forward-reference fixups, data relocations, symbols, and a peephole optimization pass. Compile modules never touch raw bytes — they call `Emit_*()` functions which delegate to architecture-specific (`X86_*()`) implementations.

```
Compile Modules ──▶ Emit_*() wrappers (CEmitCoreArch)
                         │
                         ├─ Emit.target==X86_64 → X86_*() (CEmitX86*)
                         │
                         ▼
                    CEmitCore (buffer/label/fixup mgmt)
                         │
                         ├─ Emit_Byte(b) → writes to Emit.code[]
                         ├─ Emit_CreateLabel() → allocates label entry
                         ├─ Emit_AddFixup(label, type) → records forward ref
                         └─ Emit_ResolveFixups() → patches code buffer
                              │
                    CEmitTags (peephole optimizer)
                         │
                         ├─ EmitTag_Add(pos, len, class, operand)
                         └─ EmitTag_Optimize() → NOP redundant loads
```

---

## 1. CEMITTYPES — Constants and State (10KB)

### 1.1 Emit State
```
FixedPool.Emit {
    target: 1=X86_64, 2=ARM64, 3=RISCV
    os: 1=Linux, 2=Haiku, 3=BSD, 4=macOS
    code, code_size, code_capacity    — code buffer (starts 64KB)
    data, data_size, data_capacity    — data buffer (starts 16KB)
    bss_size
    labels, label_count, label_capacity
    fixups, fixup_count, fixup_capacity
    relocs, reloc_count
    data_relocs, data_reloc_count
    code_base_addr, data_base_addr
    symbols, symbol_count
    strings, string_count
    current_section: 1=TEXT, 2=DATA, 3=RODATA, 4=BSS
    stack_depth
    error, error_msg, instructions_emitted
}
```

### 1.2 Register Encoding
```
FixedPool.Reg {
    RAX=0, RCX=1, RDX=2, RBX=3, RSP=4, RBP=5, RSI=6, RDI=7
    R8=8, R9=9, R10=10, R11=11, R12=12, R13=13, R14=14, R15=15
}
```

### 1.3 Condition Codes (for Jcc/SETcc)
```
CC.E=4 (Z=4), CC.NE=5 (NZ=5), CC.L=12, CC.G=15,
CC.LE=14, CC.GE=13, CC.B=2, CC.A=7, CC.S=8, CC.NS=9
```

### 1.4 Fixup Types
```
FixupType.REL8=1, REL32=2, ABS32=3, ABS64=4, RIP_REL32=5
```

### 1.5 Label Entry (32 bytes)
```
LabelField.NAME=0, ADDRESS=8, RESOLVED=16, SECTION=24
LabelField.ENTRY_SIZE=32
```

### 1.6 Fixup Entry (32 bytes)
```
FixupField.POSITION=0, LABEL_ID=8, TYPE=16, SIZE=24
FixupField.ENTRY_SIZE=32
```

### 1.7 Data Reloc Entry (16 bytes)
```
CodeRelocField.CODE_POSITION=0, DATA_OFFSET=8
CodeRelocField.ENTRY_SIZE=16
```

---

## 2. CEMITCORE — Buffer/Label/Fixup Management (28KB)

### 2.1 Lifecycle
```
Emit_Init() → void
    Free old buffers if reinitializing
    Allocate code buffer (64KB), data buffer (16KB)
    Create label XArray (1024), fixup XArray (2048)
    Create reloc, symbol, string XArrays
    Initialize data relocation system
    Clear all counters, error state

Emit_Free() → void
    Deallocate code buffer, data buffer
    Free all label entries, fixup entries, data reloc entries
    Destroy all XArrays
    Zero all counters
```

### 2.2 Code Emission
```
Emit_Byte(b) → void
    Write single byte to Emit.code[Emit.code_size]
    Auto-grows buffer if full (doubles capacity, max 16MB)

Emit_Word(w) → void
    Little-endian 16-bit: low byte, then high byte

Emit_DWord(d) → void
    Little-endian 32-bit: 4 bytes

Emit_QWord(q) → void
    Little-endian 64-bit: DWord(low32), DWord(high32)

Emit_Bytes(ptr, count) → void
    Copy count bytes from memory to code buffer

Emit_GetPosition() → Integer
    Return Emit.code_size (current write position)

Emit_PatchByte(position, value) → void
    Overwrite byte at given code position

Emit_PatchDWord(position, value) → void
    Overwrite 4 bytes at given code position

Emit_PatchQWord(position, value) → void
    Overwrite 8 bytes at given code position
```

### 2.3 Data Section
```
Emit_AddString(str) → Integer
    Copy string (with null terminator) to data section
    Track in strings XArray
    Return data offset

Emit_AddData(ptr, size) → Integer
    Copy raw bytes to data section
    Return data offset

Emit_DataByte(b) → void
    Write byte to data section, auto-grow if needed
```

### 2.4 Label Management
```
Emit_CreateLabel() → Integer
    Allocate 32-byte label entry: [name=0, address=0, resolved=0, section=current]
    Push to labels XArray, increment label_count
    Return label_id (index)

Emit_CreateNamedLabel(name) → Integer
    Create label, set name field

Emit_MarkLabel(label_id) → void
    Set label address to current code position
    Set resolved=1
    ALSO emits CEmitTags LABEL marker (zero-length tag)
    This prevents peephole optimizer from fusing across potential jump targets

Emit_GetLabelAddress(label_id) → Integer
    Return label address if resolved, 0 if not

Emit_IsLabelResolved(label_id) → Integer
    Return resolved flag

Emit_FindLabel(name) → Integer
    Linear search by name, return label_id or -1
```

### 2.5 Fixup Management (Forward References)
```
Emit_AddFixup(label_id, fixup_type) → void
    Record fixup at CURRENT code position
    Entry: [position=Emit.code_size, label_id, type, size]
    Size determined by type: REL8=1, REL32=4, ABS64=8

Emit_AddFixupAt(position, label_id, fixup_type) → void
    Record fixup at specific position

Emit_ResolveFixups() → void
    For each fixup entry:
        Get label address (must be resolved)
        Compute offset based on fixup type:
        - REL8: offset = target - (position+1), patch 1 byte
        - REL32: offset = target - (position+4), patch 4 bytes
        - RIP_REL32: offset = target - (position+4), patch 4 bytes
        - ABS32: patch target (4 bytes)
        - ABS64: patch target (8 bytes)
    Warn if label unresolved
```

### 2.6 Data Relocation System
```
Emit_InitDataRelocs() → void
    Create data_relocs XArray

Emit_AddDataReloc(code_position, data_offset) → void
    Record that code at code_position references data at data_offset
    Entry: [code_position, data_offset]

Emit_SetBaseAddresses(code_addr, data_addr) → void
    Set base addresses (called by ELF builder after layout calculation)

Emit_ApplyDataRelocations() → void
    For each data reloc entry:
        final_addr = data_base_addr + data_offset
        Patch 8 bytes at code_position with final_addr
    Must be called BEFORE code is written to ELF

Emit_FreeDataRelocs() → void
    Free all data reloc entries, destroy XArray
```

### 2.7 Symbol Management
```
Emit_AddSymbol(name, sym_type) → Integer
    Create symbol entry at current code position
    Entry: [name, address=code_size, type, section=current, size=0]
```

### 2.8 Statistics
```
Emit_PrintStats() → void
    Print: code_size, data_size, label_count, fixup_count,
           symbol_count, string_count, instructions_emitted

Emit_DumpCode(max_bytes) → void
    Print hex dump of first max_bytes of code buffer
```

---

## 3. CEMITCOREARCH — Architecture Abstraction Layer (79KB)

This is the **critical interface** between compile modules and target architecture. It provides ~200+ `Emit_*()` wrapper functions that each dispatch on `Emit.target`.

### 3.1 Pattern
Every function follows this exact pattern:
```
Function.Emit_MovRaxImm64 {
    Input: value: Integer
    Body: {
        IfCondition EqualTo(Emit.target, Arch.X86_64) ThenBlock: {
            X86_MovRaxImm64(value)
        }
        // Future: ARM64, RISCV branches
    }
}
```

### 3.2 Function Categories

```
IMMEDIATE LOADS (~20 functions):
    Emit_MovRaxImm64, Emit_MovRbxImm64, Emit_MovRcxImm64,
    Emit_MovRdxImm64, Emit_MovRdiImm64, Emit_MovRsiImm64,
    Emit_MovR8Imm64, Emit_MovR9Imm64, Emit_MovR10Imm64

REGISTER MOVES (~50 functions):
    Emit_MovRbxRax, Emit_MovRcxRax, Emit_MovRdxRax,
    Emit_MovRaxRbx → Emit_MovR15Rax,
    Emit_MovR12Rbx, Emit_MovR13Rcx, Emit_MovR14Rsp, etc.

PUSH/POP (~25 functions):
    Emit_PushRax through Emit_PushR15
    Emit_PopRax through Emit_PopR15
    Emit_PopR8, Emit_PopR9, Emit_PopR10

XOR/ZERO (~10 functions):
    Emit_XorRaxRax, Emit_XorRbxRbx, Emit_XorRcxRcx,
    Emit_XorRdxRdx, Emit_XorRdiRdi, Emit_XorRsiRsi,
    Emit_XorR8R8, Emit_XorR9R9, Emit_XorR10R10

ARITHMETIC (~20 functions):
    Emit_AddRaxRbx, Emit_SubRaxRbx, Emit_ImulRaxRbx, Emit_IdivRbx,
    Emit_Cqo, Emit_NegRax, Emit_IncRax, Emit_IncRbx, Emit_IncRcx,
    Emit_IncRdi, Emit_IncRsi, Emit_DecRax, Emit_AddRaxR12,
    Emit_AddRaxR13, Emit_AddRaxR14, Emit_AddRaxImm32, Emit_AddRaxImm8

LOGIC (~8 functions):
    Emit_AndRaxRbx, Emit_OrRaxRbx, Emit_XorRaxRbx, Emit_NotRax,
    Emit_ShlRaxCl, Emit_ShlRaxImm8, Emit_ShlRcxImm8, Emit_SarRaxCl

COMPARE/TEST (~10 functions):
    Emit_CmpRaxRbx, Emit_CmpRaxRcx, Emit_TestRaxRax,
    Emit_TestRbxRbx, Emit_TestRcxRcx, Emit_TestRdiRdi

BYTE OPERATIONS (~20 functions):
    Emit_MovAlDerefRdi, Emit_MovBlDerefRsi, Emit_TestAlAl,
    Emit_CmpAlBl, Emit_MovDerefRdiAl, Emit_MovByteDerefRdiZero,
    Emit_MovzxRaxBytePtrRsi

STACK FRAME (~5 functions):
    Emit_MovRbpRsp, Emit_MovRspRbp, Emit_LeaRspRbpOffset,
    Emit_MovRbpOffsetRax, Emit_MovRaxRbpOffset,
    Emit_MovRaxDerefRsp

SYSCALL WRAPPER:
    Emit_SysInstr() → X86_Syscall()
```

### 3.3 Future Architecture Support
To add ARM64:
1. Create `CEmitARM64*.ailang` files (Reg, Mem, Stack, Arith, etc.)
2. In CEmitCoreArch, add `IfCondition EqualTo(Emit.target, Arch.ARM64)` branches
3. Compile modules need NO changes — they call Emit_*() only

---

## 4. CEMITTAGS — Peephole Optimizer Tag System (9KB)

### 4.1 Purpose
Tracks emitted instructions so the optimizer can find and eliminate redundant loads. Without tags, the optimizer can't safely determine which bytes belong to which instruction.

### 4.2 State
```
FixedPool.EmitTag {
    tags: XArray      — tag entries (initially 8192 capacity)
    enabled: 1        — optimization toggle
    patched: Integer  — count of patched instructions
}

FixedPool.TagClass {
    NONE=0, STORE_LOCAL=1, LOAD_LOCAL=2, LABEL=3
}
```

### 4.3 Tag Entry (32 bytes)
```
[0]  code_pos  : byte offset into Emit.code
[8]  byte_len  : instruction length in bytes
[16] tag_class : TagClass.*
[24] operand   : class-specific payload (RBP offset for STORE/LOAD)
```

### 4.4 Functions
```
EmitTag_Init() → void
    Create tags XArray with 8192 capacity

EmitTag_Add(code_pos, byte_len, tag_class, operand) → void
    Register tagged instruction. Called by X86 layer
    after emitting instruction bytes.

EmitTag_MarkLabel(code_pos) → void
    Register zero-length LABEL tag. Critical for correctness:
    prevents fusing across potential back-edge jump targets.

EmitTag_CanFuseStoreLoad(entry, next) → Integer
    CORRECTNESS PREDICATE. Returns 1 iff:
    (a) entry is STORE_LOCAL, next is LOAD_LOCAL
    (b) byte-contiguous: next starts where entry ends
    (c) same operand: both same RBP offset

EmitTag_Optimize() → void
    Walk tag list. For each (STORE_LOCAL, LOAD_LOCAL) adjacent pair
    where CanFuseStoreLoad==1:
        NOP out the LOAD bytes (single-byte 0x90 NOPs)
        Mark load tag as TagClass.NONE
        Increment patched counter
    Label tags serve as fuse blockers — a LABEL between
    STORE and LOAD prevents fusing (the LOAD could be a jump target).

EmitTag_NopBytes(pos, len) → void
    Overwrite byte range with 0x90 (NOP)
    Single-byte NOPs are jump-target-safe.

EmitTag_Dump() → void
    Print all tags for debugging
```

### 4.5 Optimization Pattern
```
Before:  MOV [RBP-8], RAX    ← STORE_LOCAL
         MOV RAX, [RBP-8]    ← LOAD_LOCAL  (REDUNDANT!)
After:   MOV [RBP-8], RAX    ← STORE_LOCAL
         NOP NOP NOP NOP     ← LOAD patched out

But NOT fused if:
         MOV [RBP-8], RAX    ← STORE_LOCAL
         CALL other_func     ← untagged instruction (gaps tag positions)
         MOV RAX, [RBP-8]    ← LOAD_LOCAL  (NOT adjacent in code)

And NOT fused if:
         MOV [RBP-8], RAX    ← STORE_LOCAL
         LABEL target:       ← TagClass.LABEL blocks fusion
         MOV RAX, [RBP-8]    ← LOAD_LOCAL  (potential jump target)
```

---

## 5. CEMITBUFFER — Code Buffer Abstraction (54KB)

Higher-level buffer abstractions for specific emission patterns:
- Section switching (.text ↔ .data)
- Alignment padding
- Patch tables for linker relocations
- Multi-instruction sequence emission helpers

---

*Document 03 of 10 — Emit Layer*
