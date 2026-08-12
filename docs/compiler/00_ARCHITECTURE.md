# AILang Self-Hosting Compiler — Engineering Document Set

## Document Index

| # | Document | Description |
|---|----------|-------------|
| 00 | ARCHITECTURE.md | This index + top-level architecture |
| 01 | FRONTEND.md | Lexer → Parser → AST → Semantic |
| 02 | COMPILE_LAYER.md | CCompileMain dispatcher + all compile modules |
| 03 | EMIT_LAYER.md | CEmitCore, CEmitTypes, CEmitTags, CEmitCoreArch |
| 04 | X86_TARGET.md | X86-64 instruction encoding layer |
| 05 | OUTPUT_LAYER.md | ELF builder, COutput, file I/O |
| 06 | IMPORT_RESOLVER.md | Library import resolution, conflict prefixing |
| 07 | SUPPORT_SYSTEMS.md | Debug, Link, FPU, Optimizer, Syscall dispatch |
| 08 | DATA_FLOW.md | End-to-end data flow through the compiler |
| 09 | FUNCTION_CATALOG.md | Every function documented with signature, purpose, flow |
| **10** | **HDL_BACKEND.md** | **Netlist backend (ModulesHDL): IR, LUT tables, CLI `-hdl`, Yosys** |
| **11** | **HDL_LANGUAGE_COVERAGE.md** | **What AILang constructs lower to gates (matrix + ceiling)** |
| **12** | **HDL_TECHBLOCK.md** | **TechBlock = InlineAsm for gates (blackbox escape)** |
| **13** | **HDL_TANG_NANO_9K.md** | **Real silicon: Tang Nano 9K FOSS flow** |
| **14** | **HDL_BOARD_PROFILE.md** | **JSON board profiles (ailang.board/v1)** |

---

## 1. Top-Level Architecture

```
                     Source.ailang
                          │
                          ▼
  ┌───────────────────────────────────────────────────┐
  │                  FRONTEND                          │
  │   CLexer ───▶ CParser ───▶ AST Nodes ───▶ Semantic│
  │   (tokenize)   (parse)    (tree build)   (check)  │
  └───────────────────────────────────────────────────┘
                          │
                          ▼  AST (Address)
  ┌───────────────────────────────────────────────────┐
  │               COMPILE LAYER                        │
  │   CCompileMain (dispatcher)                        │
  │     ├─ Compile_Program(ast)                        │
  │     ├─ Compile_Node(node) — type dispatch          │
  │     ├─ Compile_FunctionCall(node) — name dispatch  │
  │     ├─ Compile_Expression(node)                    │
  │     └─ Module chain: 25 TryCompile modules         │
  └───────────────────────────────────────────────────┘
                          │
                          ▼  Emit_*() calls
  ┌───────────────────────────────────────────────────┐
  │               EMIT LAYER                           │
  │   CEmitCoreArch — arch-abstract wrappers           │
  │   CEmitCore — buffer, label, fixup, symbol mgmt    │
  │   CEmitTypes — constants, registers, structs       │
  │   CEmitTags — peephole optimizer tag tracking      │
  └───────────────────────────────────────────────────┘
                          │
                          ▼  X86_*() calls
  ┌───────────────────────────────────────────────────┐
  │             X86-64 TARGET LAYER                     │
  │   12 modules encoding raw x86-64 machine code      │
  │   Reg, Mem, Stack, Arith, Cmp, Jump, Sys, Logic,   │
  │   String, Macros, Helpers, Debug                   │
  └───────────────────────────────────────────────────┘
                          │
                          ▼  Raw bytes (Emit.code)
  ┌───────────────────────────────────────────────────┐
  │              OUTPUT LAYER                           │
  │   CELFTypes — constants, structures                │
  │   CELFBuilder — ELF64 header, PHDR, sections       │
  │   COutput — file I/O, write executable             │
  └───────────────────────────────────────────────────┘
                          │
                          ▼
                     executable.x (ELF64)
```

### 1.1 HDL / netlist path (fork after frontend)

```
  Same frontend AST
        │
        ▼  -hdl (ailang_cli)
  Compile/ModulesHDL/*     — circuit generators (no Emit_Byte / ELF)
        │
        ▼
  netlist IR → structural Verilog + JSON
```

See **[10_HDL_BACKEND.md](10_HDL_BACKEND.md)**. Does not modify x86 `Compile/Modules`.

---

## 2. File Map (84 .ailang files)

```
Librarys/Compiler/
├── Frontend/                    [18 files]
│   ├── Lexer/                   [8 files]
│   │   ├── CLexerTypes.ailang        — token type constants
│   │   ├── CLexerCore.ailang         — character buffer, advance
│   │   ├── CLexerKeywords.ailang     — keyword→token mapping
│   │   ├── CLexerIdentifiers.ailang  — identifier tokenizing
│   │   ├── CLexerStrings.ailang      — string literal tokenizing
│   │   ├── CLexerNumbers.ailang      — number literal tokenizing
│   │   ├── CLexerOperators.ailang    — operator/delimiter tokenizing
│   │   └── CLexerMain.ailang         — main tokenization loop
│   ├── Parser/                  [5 files]
│   │   ├── CParserCore.ailang         — parser state, advance, match
│   │   ├── CParserExpressions.ailang  — expression parsing (Pratt)
│   │   ├── CParserStatements.ailang   — statement parsing
│   │   ├── CParserDeclarations.ailang — function/pool/import parsing
│   │   └── CParserMain.ailang         — entry: Parse_Program
│   └── AST/                     [5 files]
│       ├── CASTTypes.ailang    — AST node type constants (200+)
│       ├── CASTCore.ailang     — node create/get/set/add
│       ├── CASTNodes.ailang    — typed node constructors
│       ├── CASTDebug.ailang    — AST dump/print
│       └── CSemanticCore.ailang — semantic analysis
│
├── Compile/                     [26 files]
│   ├── CCompileMain.ailang       — **CENTRAL DISPATCHER** (48KB)
│   ├── CCompileFile.ailang       — file I/O compilation (22KB)
│   ├── FPU/X86/                   [6 files: SSE, MemOps, String, Trans]
│   └── Modules/                 [24 files]
│       ├── CCompileArith.ailang      — + - * / % ++ --
│       ├── CCompileArray.ailang      — array operations
│       ├── CCompileAtomic.ailang     — atomic operations
│       ├── CCompileBitwise.ailang    — & | ^ << >>
│       ├── CCompileCompare.ailang    — == != < > <= >=
│       ├── CCompileExpr.ailang       — load/store, member, index
│       ├── CCompileFunc.ailang       — function/subroutine defs (44KB)
│       ├── CCompileIO.ailang         — print/read
│       ├── CCompileLogic.ailang      — && || !
│       ├── CCompileMem.ailang        — allocate/deallocate
│       ├── CCompilePool.ailang       — FixedPool/DynamicPool (49KB)
│       ├── CCompileScope.ailang      — scope save/restore, resolve
│       ├── CCompileScopebu.ailang    — scope backup
│       ├── CCompileStmt.ailang       — if/while/switch/for/return (29KB)
│       ├── CCompileString*.ailang    — string ops (6 files)
│       ├── CCompileSystem.ailang     — system calls
│       ├── CCompilerOptimizer.ailang — peephole optimizer
│       ├── COptimizeHoist.ailang     — loop hoisting (31KB)
│       ├── CSysDispatch.ailang       — OS-portable syscall dispatch (285KB)
│       └── CSyscallTable.ailang      — syscall number tables
│
├── CodeEmit/                    [17 files]
│   ├── CEmitBuffer.ailang       — code buffer abstraction (54KB)
│   ├── CEmitCore.ailang         — buffer, label, fixup mgmt (28KB)
│   ├── CEmitCoreArch.ailang     — arch-abstract wrappers (79KB)
│   ├── CEmitTags.ailang         — instruction tagging & peephole (9KB)
│   ├── CEmitTypes.ailang        — type constants/pools (10KB)
│   └── X86/                     [12 files]
│       ├── CEmitX86Reg.ailang   — register moves, immediate loads
│       ├── CEmitX86Mem.ailang   — memory access, addressing (41KB)
│       ├── CEmitX86Stack.ailang — push, pop, prologue, epilogue
│       ├── CEmitX86Arith.ailang — ADD, SUB, IMUL, IDIV, NEG
│       ├── CEmitX86Cmp.ailang   — CMP, TEST, SETcc
│       ├── CEmitX86Jump.ailang  — JMP, Jcc, CALL, RET
│       ├── CEmitX86Sys.ailang   — SYSCALL instruction
│       ├── CEmitX86Logic.ailang — AND, OR, XOR, NOT, shifts
│       ├── CEmitX86String.ailang— string operations
│       ├── CEmitX86Macros.ailang— pseudo-instruction macros
│       └── CEmitX86Helpers.ailang — address computations
│
├── Import/                      [4 files]
│   ├── CAutoImport.ailang       — automatic import discovery
│   ├── CCoreRegistry.ailang     — core module registry
│   ├── CFileMap.ailang          — source file path mapping
│   └── CImportResolver.ailang   — conflict-prefix resolver (60KB)
│
├── Output/                      [3 files]
│   ├── CELFTypes.ailang         — ELF constants, structures
│   ├── CELFBuilder.ailang       — ELF64 executable construction
│   └── COutput.ailang           — file output, statistics
│
├── Link/                        [5 files]
│   ├── Dispatch.ailang          — link-time dispatch
│   ├── Core/RelocTable.ailang   — relocation table
│   ├── Core/SymbolTable.ailang  — symbol table
│   └── OS/Linux/ELFKernelModule.ailang + KernelABI.ailang
│
└── Debug/                       [3 files]
    ├── CCompileDebug.ailang     — debug info generation (29KB)
    ├── CDebugTypes.ailang       — debug type constants
    └── X86/CEmitDebugX86.ailang — x86 debug emission
```

---

## 3. FixedPool State Architecture

### Compile State
```
FixedPool.Compile {
    ast, functions, variables, current_func,
    stack_offset, stack_size, loop_stack, loop_depth,
    error, error_msg, nodes_compiled, pending_pool_type,
    return_label, current_return_label
}
```

### Emit State
```
FixedPool.Emit {
    target(ISA), os,            // ISA + OS selection
    code, code_size, code_capacity, // code buffer
    data, data_size, data_capacity, // data buffer
    bss_size,
    labels, label_count,        // label table
    fixups, fixup_count,        // forward references
    relocs, reloc_count,        // relocations
    data_relocs, data_reloc_count, // data address patches
    code_base_addr, data_base_addr,
    symbols, symbol_count,
    strings, string_count,
    current_section, stack_depth,
    error, error_msg,
    instructions_emitted
}
```

### ELF State
```
FixedPool.ELF {
    buffer, buffer_size, buffer_capacity,
    base_addr, entry_addr, text_addr, data_addr,
    text_offset, text_size, data_offset, data_size,
    bss_size, phdr_count, shdr_count,
    shstrtab, shstrtab_size,
    error, error_msg
}
```

---

## 4. Compilation Pipeline (end to end)

```
1. SOURCE LOADING
   Source file → ReadTextFile → source buffer in memory

2. LEXING
   Lex_Init(source, filename) → Lex_Tokenize() → Lex.token_count tokens
   ~8 specialized lexer modules: strings, numbers, operators, keywords, identifiers

3. PARSING
   Parse_Init(token_count) → Parse_Program() → AST root node (AST.PROGRAM)
   ~5 parser modules: expressions (Pratt), statements, declarations, core

4. IMPORT RESOLUTION
   Import_Init() → scan Program for LibraryImport nodes
   → Import_ResolveAll() → detect symbol conflicts
   → generate prefixed names → rewrite AST

5. COMPILATION
   Compile_Init() → Compile_Program(ast)
   → CCompileMain walks AST nodes, dispatches to modules
   → Each module emits via Emit_*() wrappers
   → CEmitCoreArch routes to X86_*() based on Emit.target
   → X86 layer encodes raw bytes into Emit.code buffer

6. OPTIMIZATION
   EmitTag_Optimize() → peephole pass on tagged instructions
   CompileOptimizer passes on compile-time patterns

7. FIXUP RESOLUTION
   Emit_ResolveFixups() → patch forward references in code buffer

8. ELF OUTPUT
   ELF_Init() → ELF_Build(code, code_size, data, data_size)
   → Emit_ApplyDataRelocations()
   → ELF_WriteHeader() + ELF_WriteProgramHeader() + code + data
   → Output_WriteExecutable(filename) → ELF64 file on disk

9. CLEANUP
   Compile_Free() → Emit_Free() → ELF_Free()
```

---

## 5. X86-64 Register Convention

```
RAX   — primary accumulator, expression results, return values
RBX   — callee-saved scratch, temporary value holder
RCX   — counter, temporary, 4th syscall argument (kernel uses R10)
RDX   — temporary, 3rd syscall argument, IMUL/IDIV high bits
RSI   — 2nd syscall argument, source pointer
RDI   — 1st syscall argument, destination pointer
RBP   — frame pointer (stack frame base)
RSP   — stack pointer
R8    — 5th syscall argument, temporary
R9    — 6th syscall argument, temporary
R10   — 4th syscall argument (kernel uses R10 not RCX)
R11   — clobbered by SYSCALL instruction
R12   — callee-saved, compile module depth-0 temp
R13   — callee-saved, compile module depth-1 temp
R14   — callee-saved, reserved for future use
R15   — pool base register (FixedPool/DynamicPool base address)
```

---

## 6. Key Design Decisions

1. **String-based function dispatch**: Function calls in compile modules use `StringCompare(func_name, "Add")` literal comparison, NOT FixedPool constants (avoids pool collision segfaults).

2. **Architecture abstraction at Emit_* level**: Compile modules call `Emit_AddRaxRbx()`, never `X86_AddRaxRbx()`. CEmitCoreArch checks `Emit.target` and dispatches. Adding ARM64 = new ARM64 emit files only.

3. **OS-portable syscalls at compile time**: `Sys_Read()` checks `Emit.os` at compile time and emits the correct syscall number. No runtime branches in generated code.

4. **Peephole optimizer with tag tracking**: CEmitTags tags each emitted instruction. EmitTag_Optimize scans for (STORE_LOCAL, LOAD_LOCAL) adjacent pairs and NOPs the redundant load. Label tags break fusion to preserve correctness.

5. **Scope isolation via SaveAndClear/Restore**: Entering a function saves entire variable scope, clears locals, preserves pool vars. Exiting restores everything. Stack offsets reset per function.

6. **Conflict-only import prefixing**: Symbols without conflicts are imported as-is. Only conflicting symbols get auto-generated NSxx_ prefixes. Minimizes name mangling.

7. **No section headers in ELF output**: Only program headers (PT_LOAD) are emitted. Section headers are deliberately omitted for simplicity.

8. **Single-pass compilation**: No intermediate representation. AST is walked once, emitting code directly. Labels/fixups handle forward references.

---

## 7. Concurrency & Safety

- **No threads in compiler**: Single-pass, single-threaded compilation
- **No SUDO**: All file output is to user-writable paths
- **Bounds checks**: XArray.XGet returns checked; null pointer guards on all dereferences
- **Error propagation**: Compile.error flag checked after each sub-compilation
- **Memory**: Dynamic allocations via Allocate()/Deallocate(); pools via FixedPool/DynamicPool

---

*Document 00 of 10 — Architecture Overview*
