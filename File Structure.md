# AILang Self-Hosting Compiler - File Structure

```
Librarys/
├── XArrays.ailang                    # Dynamic array library
│
└── Compiler/
    │
    ├── Frontend/                     # Lexer, Parser, AST
    │   │
    │   ├── Lexer/
    │   │   ├── Library.CLexerTypes.ailang
    │   │   ├── Library.CLexerCore.ailang
    │   │   ├── Library.CLexerKeywords.ailang
    │   │   ├── Library.CLexerStrings.ailang
    │   │   ├── Library.CLexerNumbers.ailang
    │   │   ├── Library.CLexerOperators.ailang
    │   │   ├── Library.CLexerIdentifiers.ailang
    │   │   └── Library.CLexerMain.ailang
    │   │
    │   ├── Parser/
    │   │   ├── Library.CParserTypes.ailang
    │   │   ├── Library.CParserCore.ailang
    │   │   ├── Library.CParserExpressions.ailang
    │   │   ├── Library.CParserStatements.ailang
    │   │   ├── Library.CParserDeclarations.ailang
    │   │   └── Library.CParserMain.ailang
    │   │
    │   └── AST/
    │       ├── Library.CASTTypes.ailang
    │       ├── Library.CASTCore.ailang
    │       ├── Library.CASTNodes.ailang
    │       ├── Library.CASTDebug.ailang
    │       └── Library.CSemanticCore.ailang
    │
    ├── Compile/                      # AST → Instructions (architecture-agnostic)
    │   │
    │   ├── Library.CCompileMain.ailang       # Main dispatcher ✓
    │   ├── Library.CCompileTypes.ailang      # Compile state, VarEntry, etc.
    │   │
    │   └── Modules/                  # One file per primitive group
    │       ├── Library.CCompileFunc.ailang       # Function, SubRoutine, UserCall
    │       ├── Library.CCompileStmt.ailang       # If, While, Assignment, Return
    │       ├── Library.CCompileExpr.ailang       # Expressions, operators
    │       ├── Library.CCompileArith.ailang      # Add, Subtract, Multiply, Divide
    │       ├── Library.CCompileCompare.ailang    # EqualTo, LessThan, GreaterThan
    │       ├── Library.CCompileLogic.ailang      # And, Or, Not
    │       ├── Library.CCompileBitwise.ailang    # BitAnd, BitOr, ShiftLeft
    │       ├── Library.CCompileIO.ailang         # PrintMessage, PrintNumber
    │       ├── Library.CCompileString.ailang     # String operations
    │       ├── Library.CCompileMem.ailang        # Allocate, StoreValue, Dereference
    │       ├── Library.CCompileArray.ailang      # ArrayCreate, ArrayGet, ArraySet
    │       ├── Library.CCompileXArray.ailang     # XArray operations
    │       └── Library.CCompileSystem.ailang     # SystemCall, Exit
    │
    ├── CodeEmit/                     # Instructions → Bytes (architecture-specific)
    │   │
    │   ├── Library.CEmitTypes.ailang         # Emit state, Reg enum, CC enum ✓
    │   ├── Library.CEmitCore.ailang          # Buffer mgmt, labels, fixups ✓
    │   │
    │   ├── X86/                      # x86-64 target
    │   │   ├── Library.CEmitX86Reg.ailang    # MOV reg,reg / MOV reg,imm ✓
    │   │   ├── Library.CEmitX86Mem.ailang    # Load/store, addressing modes ✓
    │   │   ├── Library.CEmitX86Stack.ailang  # PUSH, POP, prologue/epilogue ✓
    │   │   ├── Library.CEmitX86Arith.ailang  # ADD, SUB, MUL, DIV, NEG ✓
    │   │   ├── Library.CEmitX86Logic.ailang  # AND, OR, XOR, NOT, shifts ✓
    │   │   ├── Library.CEmitX86Cmp.ailang    # CMP, TEST, SETcc ✓
    │   │   ├── Library.CEmitX86Jump.ailang   # JMP, Jcc, CALL, RET ✓
    │   │   └── Library.CEmitX86Sys.ailang    # SYSCALL, NOP, misc ✓
    │   │
    │   └── RISCV/                    # RISC-V target (future)
    │       ├── Library.CEmitRISCV.ailang
    │       └── Library.CEmitRISCVSys.ailang
    │
    ├── Assembler/                    # Low-level assembly utilities
    │   └── (reserved for future use)
    │
    ├── Output/                       # Binary output generation
    │   ├── Library.CELFTypes.ailang          # ELF constants, header structs
    │   ├── Library.CELFBuilder.ailang        # ELF executable builder
    │   ├── Library.CRelocate.ailang          # Relocation handling
    │   └── Library.COutput.ailang            # File writing
    │
    └── Modules/                      # Shared/utility modules
        └── (reserved for future use)
```

## Import Paths

```ailang
// Frontend
LibraryImport.Compiler.Frontend.Lexer.CLexerMain
LibraryImport.Compiler.Frontend.Parser.CParserMain
LibraryImport.Compiler.Frontend.AST.CASTCore

// Compile
LibraryImport.Compiler.Compile.CCompileMain
LibraryImport.Compiler.Compile.Modules.CCompileArith

// CodeEmit
LibraryImport.Compiler.CodeEmit.CEmitCore
LibraryImport.Compiler.CodeEmit.X86.CEmitX86

// Output
LibraryImport.Compiler.Output.CELFBuilder
```

## Build Status

### Phase 1: Foundation ✓
- [x] Lexer (complete)
- [x] Parser (complete)
- [x] AST module (complete)
- [x] CEmitTypes (complete)
- [x] CEmitCore (complete) - includes label/fixup management
- [x] CEmitX86* (complete) - all 8 instruction files

### Phase 2: Minimal Compiler (CURRENT)
- [x] CCompileMain - dispatcher skeleton
- [ ] CCompileArith - Add, Subtract, Multiply, Divide
- [ ] CCompileIO - PrintMessage, PrintNumber
- [ ] CCompileExpr - expression evaluation
- [ ] CCompileFunc - Function compilation

**Test Target**: `PrintNumber(Add(1, 2))`

### Phase 3: Output
- [ ] CELFTypes - ELF constants
- [ ] CELFBuilder - ELF generation
- [ ] COutput - File writing

**Test Target**: Generate working ELF executable

### Phase 4: Statements & Control Flow
- [ ] CCompileStmt - Assignment, Return, Block
- [ ] CCompileStmt - If, While
- [ ] Loop context (break, continue)

### Phase 5: Memory & Pools
- [ ] CCompileMem - Allocate, StoreValue, Dereference
- [ ] CCompilePool - FixedPool access

### Phase 6: Full Compiler
- [ ] CCompileCompare, CCompileLogic, CCompileBitwise
- [ ] CCompileString, CCompileArray, CCompileXArray
- [ ] CCompileSystem

### Phase 7: Self-Hosting
- [ ] Compile the compiler with itself!

---
*Last Updated: December 25, 2025*
