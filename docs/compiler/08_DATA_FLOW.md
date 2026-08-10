# AILang Compiler — 08: End-to-End Data Flow

## Overview

This document traces the complete data flow through the compiler, following a simple AILang source file from text to executable. Each phase shows what data enters, what transformation occurs, and what data exits.

---

## PHASE 0: Source Input

```
INPUT:  "Hello.ailang" on disk
        │
        ▼
        Source = ReadTextFile("Hello.ailang")
        │
        ▼
OUTPUT: Source string in memory:
        "SubRoutine.Main {\n  PrintMessage(\"Hello World\\n\")\n}\nRunTask(Main)\n"
```

---

## PHASE 1: Lexing

```
INPUT:  Source string (Address), Filename (Address)
        │
        ▼
        Lex_Init(source, "Hello.ailang")
        Lex_Tokenize()
        │
        ├─ pos=0: 'S' → Lex_TokenizeIdentifier()
        │   → "SubRoutine" → keyword check → Token.SUBROUTINE
        │
        ├─ pos=10: '.' → Lex_TokenizeOperator()
        │   → Token.DOT
        │
        ├─ pos=11: 'M' → Lex_TokenizeIdentifier()
        │   → "Main" → not keyword → Token.IDENTIFIER(value="Main")
        │
        ├─ pos=15: ' ' → Lex_SkipWhitespace()
        ├─ pos=16: '{' → Lex_TokenizeOperator() → Token.LBRACE
        ├─ pos=17: '\n' → Token.NEWLINE
        │
        ├─ pos=18: ' ' ' ' → Lex_SkipWhitespace()
        ├─ pos=20: 'P' → Lex_TokenizeIdentifier()
        │   → "PrintMessage" → not keyword → Token.IDENTIFIER(value="PrintMessage")
        ├─ pos=32: '(' → Token.LPAREN
        ├─ pos=33: '"' → Lex_TokenizeString()
        │   → reads "Hello World\n" → Token.STRING(value="Hello World\n")
        ├─ pos=46: ')' → Token.RPAREN
        ├─ pos=47: '\n' → Token.NEWLINE
        │
        ├─ pos=48: '}' → Token.RBRACE
        ├─ pos=49: '\n' → Token.NEWLINE
        │
        ├─ pos=50: 'R' → "RunTask" → Token.IDENTIFIER(value="RunTask")
        ├─ pos=57: '(' → Token.LPAREN
        ├─ pos=58: 'M' → "Main" → Token.IDENTIFIER(value="Main")
        ├─ pos=62: ')' → Token.RPAREN
        ├─ pos=63: '\n' → Token.NEWLINE
        ├─ pos=64: 0 → Token.EOF
        │
        ▼
OUTPUT: Lex.token_count = 16 tokens
        Tokens XArray: [SUBROUTINE, DOT, IDENTIFIER("Main"), LBRACE, NEWLINE,
                        IDENTIFIER("PrintMessage"), LPAREN, STRING("Hello World\n"),
                        RPAREN, NEWLINE, RBRACE, NEWLINE,
                        IDENTIFIER("RunTask"), LPAREN, IDENTIFIER("Main"),
                        RPAREN, NEWLINE, EOF]
```

---

## PHASE 2: Parsing

```
INPUT:  16 tokens from lexer
        │
        ▼
        Parse_Init(16)
        Parse_Program()
        │
        ├─ Token 0: SUBROUTINE → Parse_SubRoutine()
        │   ├─ Read name: "Main" (IDENTIFIER)
        │   ├─ Read LBRACE
        │   ├─ Parse body statements:
        │   │   └─ Parse_Statement()
        │   │       ├─ IDENTIFIER("PrintMessage") → Parse_FunctionCall()
        │   │       │   ├─ Read LPAREN
        │   │       │   ├─ Parse_Expression() → STRING("Hello World\n")
        │   │       │   └─ Read RPAREN
        │   │       └─ Returns AST.CALL node:
        │   │           type=CALL, data1="PrintMessage"
        │   │           children=[AST.STRING node: data1="Hello World\n"]
        │   └─ Read RBRACE
        │   └─ Returns AST.SUBROUTINE node:
        │       type=SUBROUTINE, data1="Main"
        │       children=[AST.BLOCK node: children=[AST.CALL node]]
        │
        ├─ Token 12: IDENTIFIER("RunTask") → Parse_Statement()
        │   ├─ "RunTask" → Parse_FunctionCall()
        │   │   ├─ Read LPAREN
        │   │   ├─ Parse_Expression() → IDENTIFIER("Main")
        │   │   └─ Read RPAREN
        │   └─ Returns AST.CALL node:
        │       type=CALL, data1="RunTask"
        │       children=[AST.IDENTIFIER node: data1="Main"]
        │
        ▼
OUTPUT: AST tree:
        AST.PROGRAM
        ├── AST.SUBROUTINE (data1="Main")
        │   └── AST.BLOCK
        │       └── AST.CALL (data1="PrintMessage")
        │           └── AST.STRING (data1="Hello World\n")
        └── AST.CALL (data1="RunTask")
            └── AST.IDENTIFIER (data1="Main")
```

---

## PHASE 3: Import Resolution

```
INPUT:  AST tree
        │
        ▼
        Import_ResolveAll(ast)
        │
        ├─ Scan for LibraryImport nodes → none in this example
        ├─ No imports to resolve
        │
        ▼
OUTPUT: Unchanged AST (no imports)
```

---

## PHASE 4: Compilation

### 4.1 Initialization
```
INPUT:  AST tree
        │
        ▼
        Compile_Init()
            Emit_Init() → code buffer (64KB), data buffer (16KB)
            EmitTag_Init() → tag tracking array
            Scope_Init() → scope stack
        │
        ▼
        Compile_Program(ast)
```

### 4.2 Phase 4a: Process Pools
```
        ├─ Walk children for pool definitions → none in this example
```

### 4.3 Phase 4b: Process Functions/Subroutines
```
        ├─ Child 0: AST.SUBROUTINE "Main"
        │   │
        │   ▼ CompileFunc_Define(node)
        │   │
        │   ├─ Scope_SaveAndClear("Main")
        │   ├─ Emit_AddSymbol("Main", ELFSymType.FUNC)
        │   │
        │   ├─ PROLOGUE:
        │   │   Emit_PushRbp()          → 55
        │   │   Emit_MovRbpRsp()       → 48 89 E5
        │   │   Emit_SubRaxImm8(0)     → (no stack used)
        │   │
        │   ├─ BODY: CompileStmt_Block(child[0])
        │   │   │
        │   │   └─ AST.CALL "PrintMessage"
        │   │       │
        │   │       ▼ Compile_FunctionCall(call_node)
        │   │       │
        │   │       ├─ Try module chain: Arith? No. Compare? No.
        │   │       │   ... IO? YES!
        │   │       │
        │   │       ▼ CompileIO_PrintMessage(call_node)
        │   │       │
        │   │       ├─ Get arg: AST.STRING "Hello World\n"
        │   │       ├─ Compile string: Emit_AddString("Hello World\n") → data_offset=0
        │   │       ├─ Emit_LeaRaxRbpOffset(data_offset)   → 48 8D 05 <data_reloc>
        │   │       ├─ Emit_AddDataReloc(position, 0)       → record for later patching
        │   │       ├─ Emit_MovRsiRax()                     → 48 89 C6  (buf = string)
        │   │       ├─ strlen inline (loop over bytes)      → RDX = 12
        │   │       ├─ Emit_MovRdiImm64(1)                  → 48 BF 01 00 00 00 00 00 00 00
        │   │       ├─ Emit_MovRdxRcx()                     → (strlen → RDX)
        │   │       ├─ Emit_MovRaxImm64(1)                  → 48 B8 01 00 00 00 00 00 00 00
        │   │       ├─ Emit_Syscall()                       → 0F 05
        │   │       └─ Return RAX contents
        │   │
        │   ├─ EPILOGUE:
        │   │   Emit_MovRspRbp()       → 48 89 EC
        │   │   Emit_PopRbp()          → 5D
        │   │   Emit_Ret()             → C3
        │   │
        │   ├─ Scope_Restore()
```

### 4.4 Phase 4c: Entry Point
```
        ├─ Child 1: AST.CALL "RunTask"
        │   │
        │   ▼ Check: is it RunTask? Yes!
        │   │
        │   ├─ Emit_AddSymbol("_start", ELFSymType.FUNC)
        │   ├─ CompileFunc_Call("Main")
        │   │   Emit_Call(main_label)    → E8 <rel32_fixup>
        │   ├─ Emit_MovRdiRax()          → 48 89 C7  (exit code)
        │   ├─ Emit_MovRaxImm64(60)      → 48 B8 3C 00 00 00 00 00 00 00
        │   ├─ Emit_SysInstr()           → 0F 05  (sys_exit)
        │
        ▼
        Emit.code_size = ~120 bytes
        Emit.data_size = 13 bytes ("Hello World\n\0")
        Emit.label_count = 4
        Emit.fixup_count = 3
```

---

## PHASE 5: Peephole Optimization

```
INPUT:  Emit.code (120 bytes), EmitTag.tags
        │
        ▼
        EmitTag_Optimize()
        │
        ├─ Walk tag list
        ├─ Find (STORE_LOCAL, LOAD_LOCAL) adjacent pairs → fuse them
        │   (0 found in this simple example)
        │
        ├─ EmitTag.patched = 0
        │
        ▼
OUTPUT: Emit.code unchanged (no optimizable patterns)
```

---

## PHASE 6: Fixup Resolution

```
INPUT:  Emit.code (with placeholder bytes)
        Emit.fixups (3 entries)
        Emit.labels (4 resolved)
        │
        ▼
        Emit_ResolveFixups()
        │
        ├─ Fixup 0: REL32 at pos=10, label_id=2 (main_code)
        │   target = 64, position = 10
        │   offset = 64 - (10+4) = 50
        │   PatchDWord(10, 50)
        │
        ├─ Fixup 1: REL32 at pos=80, label_id=0 (main_label)
        │   target = 32, position = 80
        │   offset = 32 - (80+4) = -52
        │   PatchDWord(80, -52)
        │
        ├─ Fixup 2: RIP_REL32 at pos=65, data_offset=0
        │   (patched later by Emit_ApplyDataRelocations)
        │
        ▼
OUTPUT: Emit.code: forward references resolved
```

---

## PHASE 7: ELF Build

```
INPUT:  Emit.code (120 bytes), Emit.data (13 bytes)
        │
        ▼
        ELF_Init()
        ELF_Build(code, 120, data, 13)
        │
        ├─ Layout calculation:
        │   elf_hdr_size = 64
        │   phdr_offset = 64
        │   phdr_total = 2 * 56 = 112
        │   text_offset = align16(176) = 176
        │   data_offset = align_page(176+120) = 4096
        │   text_vaddr = 0x400000 + 176 = 0x4000B0
        │   data_vaddr = 0x400000 + 4096 = 0x401000
        │   entry_vaddr = 0x4000B0
        │
        ├─ Emit_SetBaseAddresses(0x4000B0, 0x401000)
        ├─ Emit_ApplyDataRelocations()
        │   Data reloc 0: code_pos=65, data_offset=0
        │   final = 0x401000 + 0 = 0x401000
        │   PatchQWord(65, 0x401000)
        │
        ├─ Write ELF header (64 bytes)
        ├─ Write PT_LOAD .text (56 bytes): offset=176, vaddr=0x4000B0, size=120, flags=RX
        ├─ Write PT_LOAD .data (56 bytes): offset=4096, vaddr=0x401000, size=13, flags=RW
        ├─ Pad to text offset with zeros (176-120=56 bytes)
        ├─ Write 120 bytes of code
        ├─ Pad to data offset (4096-296=3800 bytes of zeros)
        ├─ Write 13 bytes of data
        │
        ▼
OUTPUT: ELF.buffer = 4109 bytes, ELF.buffer_size = 4109
```

---

## PHASE 8: File Output

```
INPUT:  ELF.buffer (4109 bytes), filename "Hello.x"
        │
        ▼
        Output_WriteExecutable("Hello.x")
        │
        ├─ FileOpen("Hello.x", 577, 493) → fd=3
        ├─ FileWrite(3, ELF.buffer, 4109) → written=4109
        ├─ FileClose(3)
        │
        ▼
OUTPUT: "Hello.x" file on disk (4109 bytes, ELF64 executable)
```

---

## PHASE 9: Execution

```
$ ./Hello.x
        │
        ├─ Linux ELF loader maps segments:
        │   .text at 0x4000B0 (RX)
        │   .data at 0x401000 (RW)
        │
        ├─ Jumps to entry 0x4000B0 (_start)
        │
        ├─ CALL Main:
        │   push RBP
        │   mov RBP, RSP
        │   lea RSI, [0x401000]      ← "Hello World\n"
        │   mov RDX, 12              ← strlen
        │   mov RDI, 1               ← stdout
        │   mov RAX, 1               ← sys_write
        │   syscall                  → writes "Hello World\n" to stdout
        │   mov RSP, RBP
        │   pop RBP
        │   ret
        │
        ├─ mov RDI, RAX              ← exit code
        ├─ mov RAX, 60               ← sys_exit
        ├─ syscall                   → process exits
        │
        ▼
OUTPUT on terminal: "Hello World\n"
```

---

## COMPLETE DATA FLOW SUMMARY

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Source  │ ──▶ │  Lexer   │ ──▶ │  Parser  │ ──▶ │  Import  │
│  String  │     │  Tokens  │     │   AST    │     │ Resolver │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                        │
                                                        ▼
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  ELF64   │ ◀── │   ELF    │ ◀── │  Emit    │ ◀── │ Compile  │
│   File   │     │ Builder  │     │ Buffer   │     │  Layer   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘

Data sizes at each phase:
  Source:    ~100 bytes (string)
  Tokens:    16 × 32 = 512 bytes
  AST:       ~10 nodes × 64 = 640 bytes
  Emit.code: 120 bytes (raw x86-64)
  Emit.data: 13 bytes
  ELF:       4109 bytes (with headers and padding)
  File:      4109 bytes on disk
```

---

*Document 08 of 10 — End-to-End Data Flow*
