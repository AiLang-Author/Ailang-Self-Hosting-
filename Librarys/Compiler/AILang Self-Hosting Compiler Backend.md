# AILang Self-Hosting Compiler Backend Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐      │
│  │ CLexer  │───▶│ CParser │───▶│  AST    │───▶│Semantic │      │
│  │         │    │         │    │ Nodes   │    │Analysis │      │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ AST Tree
┌─────────────────────────────────────────────────────────────────┐
│                    COMPILE LAYER (CCompile*)                     │
│  ┌──────────────┐                                               │
│  │ CCompileMain │◀── Main dispatcher, state management          │
│  └──────┬───────┘                                               │
│         │ dispatches to                                         │
│         ▼                                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Compile Modules                         │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐        │  │
│  │  │CCompileIO  │ │CCompileArith│ │CCompileCompare │        │  │
│  │  └────────────┘ └────────────┘ └────────────────┘        │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐        │  │
│  │  │CCompileStmt│ │CCompileFunc│ │CCompileExpr    │        │  │
│  │  └────────────┘ └────────────┘ └────────────────┘        │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐        │  │
│  │  │CCompileLogic││CCompileBit │ │CCompileString  │        │  │
│  │  └────────────┘ └────────────┘ └────────────────┘        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Emit_* calls
┌─────────────────────────────────────────────────────────────────┐
│                 EMIT LAYER (Architecture Agnostic)               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ CEmitCore   │    │CEmitCoreArch│    │ CEmitTypes  │         │
│  │ - buffers   │    │ - Emit_*    │    │ - Reg, CC   │         │
│  │ - labels    │    │   wrappers  │    │ - FixupType │         │
│  │ - fixups    │    │             │    │ - constants │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ X86_* calls
┌─────────────────────────────────────────────────────────────────┐
│                    X86-64 TARGET LAYER                           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │CEmitX86Reg │ │CEmitX86Mem │ │CEmitX86Arith│ │CEmitX86Jump│   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │CEmitX86Cmp │ │CEmitX86Stack│ │CEmitX86Sys │ │CEmitX86Logic│  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Raw bytes
┌─────────────────────────────────────────────────────────────────┐
│                      OUTPUT LAYER                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ CELFTypes   │    │ CELFBuilder │    │  COutput    │         │
│  │ - constants │    │ - headers   │    │ - file I/O  │         │
│  │ - structs   │    │ - sections  │    │             │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### Frontend → Backend Interface

The frontend produces an AST tree. The backend entry point is:

```ailang
Compile_Program(ast)
```

This walks the AST and dispatches to appropriate handlers based on node type.

### CCompileMain - Central Dispatcher

**Location:** `Librarys/Compiler/Compile/Library.CCompileMain.ailang`

**Responsibilities:**
- Global compiler state (`FixedPool.Compile`)
- AST node type dispatch (`Compile_Node`)
- Function call dispatch (`Compile_FunctionCall`)
- Label management (`Compile_NewLabel`)
- Variable tracking
- Error handling

**Key Functions:**
```ailang
Compile_Init()           // Initialize compiler state
Compile_Program(ast)     // Main entry point
Compile_Node(node)       // Dispatch by AST node type
Compile_FunctionCall(node) // Dispatch by function name
Compile_Expression(node) // Expression evaluation
Compile_NewLabel()       // Create new jump label
```

**State Pool:**
```ailang
FixedPool.Compile {
    "ast": Initialize=0, CanChange=True
    "functions": Initialize=0, CanChange=True      // XArray
    "variables": Initialize=0, CanChange=True      // XArray
    "current_func": Initialize=0, CanChange=True
    "stack_offset": Initialize=0, CanChange=True
    "loop_stack": Initialize=0, CanChange=True     // XArray for break/continue
    "loop_depth": Initialize=0, CanChange=True
    "error": Initialize=0, CanChange=True
    "nodes_compiled": Initialize=0, CanChange=True
}
```

---

## Compile Modules

Each module handles a specific category of operations.

### Module Pattern

Every compile module follows this pattern:

```ailang
// 1. Imports
LibraryImport.Compiler.Frontend.AST.CASTTypes
LibraryImport.Compiler.Frontend.AST.CASTCore
LibraryImport.Compiler.CodeEmit.CEmitCoreArch

// 2. TryCompile Dispatcher
Function.CompileXXX_TryCompile {
    Input: node: Address
    Output: Integer  // 1 = handled, 0 = not our operation
    Body: {
        func_name = AST_GetData1(node)
        
        // String literal comparison - NO FIXEDPOOL!
        cmp = StringCompare(func_name, "OperationName")
        IfCondition EqualTo(cmp, 0) ThenBlock: {
            ReturnValue(CompileXXX_OperationName(node))
        }
        
        // Not our operation
        ReturnValue(0)
    }
}

// 3. Individual operation handlers
Function.CompileXXX_OperationName {
    Input: node: Address
    Output: Integer
    Body: {
        // Get arguments from AST
        // Compile sub-expressions
        // Emit machine code via Emit_* functions
        ReturnValue(1)
    }
}
```

### Module Dispatch Chain

In `Compile_FunctionCall`, modules are tried in order:

```ailang
// Arithmetic: Add, Subtract, Multiply, Divide, Modulo, Negate
result = CompileArith_TryCompile(node)
IfCondition EqualTo(result, 1) ThenBlock: { ReturnValue(1) }

// Comparison: EqualTo, NotEqual, LessThan, GreaterThan, etc.
result = CompileCompare_TryCompile(node)
IfCondition EqualTo(result, 1) ThenBlock: { ReturnValue(1) }

// I/O: PrintMessage, PrintNumber, PrintChar
result = CompileIO_TryCompile(node)
IfCondition EqualTo(result, 1) ThenBlock: { ReturnValue(1) }

// ... more modules ...
```

### Current Modules

| Module | Operations | Status |
|--------|-----------|--------|
| CCompileArith | Add, Subtract, Multiply, Divide, Modulo, Negate, Increment, Decrement | ✓ Working |
| CCompileCompare | EqualTo, NotEqual, LessThan, GreaterThan, LessEqual, GreaterEqual | ✓ Working |
| CCompileIO | PrintMessage, PrintNumber, PrintChar | ✓ Working |
| CCompileStmt | If, While, Assignment, Return, Block, Break, Continue | ✓ Working |
| CCompileFunc | Function, SubRoutine definitions | ✓ Working |
| CCompileExpr | Variable load/store, literals | ✓ Working |
| CCompileLogic | And, Or, Not | Stub |
| CCompileBitwise | BitwiseAnd, BitwiseOr, shifts | Stub |
| CCompileString | StringCompare, StringLength, StringCopy | Partial |
| CCompileMem | Allocate, Deallocate, StoreValue, Dereference | Stub |

---

## Emit Layer

### CEmitTypes - Constants and Structures

**Location:** `Librarys/Compiler/CodeEmit/Library.CEmitTypes.ailang`

Defines architecture-independent constants:

```ailang
// Register encoding (x86-64 specific but abstracted)
FixedPool.Reg {
    "RAX": Initialize=0
    "RCX": Initialize=1
    "RDX": Initialize=2
    "RBX": Initialize=3
    "RSP": Initialize=4
    "RBP": Initialize=5
    // ... etc
}

// Condition codes for jumps
FixedPool.CC {
    "E": Initialize=4      // Equal (ZF=1)
    "Z": Initialize=4      // Zero
    "NE": Initialize=5     // Not Equal
    "NZ": Initialize=5     // Not Zero
    "L": Initialize=12     // Less (signed)
    "G": Initialize=15     // Greater (signed)
    // ... etc
}

// Fixup types
FixedPool.FixupType {
    "REL8": Initialize=1   // 8-bit relative
    "REL32": Initialize=2  // 32-bit relative
    "ABS64": Initialize=4  // 64-bit absolute
}
```

### CEmitCore - Buffer and Label Management

**Location:** `Librarys/Compiler/CodeEmit/Library.CEmitCore.ailang`

Manages:
- Code buffer (dynamic, grows as needed)
- Data buffer (strings, constants)
- Labels (name → address mapping)
- Fixups (forward references to resolve)
- Symbols (for ELF output)

**Key Functions:**
```ailang
Emit_Init()              // Initialize buffers
Emit_Free()              // Cleanup

// Code emission
Emit_Byte(b)             // Emit single byte
Emit_Word(w)             // Emit 16-bit value
Emit_DWord(d)            // Emit 32-bit value
Emit_QWord(q)            // Emit 64-bit value

// Labels
Emit_CreateLabel()       // Create new label, returns ID
Emit_MarkLabel(id)       // Mark label at current position
Emit_AddFixup(label, type) // Add forward reference

// Data section
Emit_AddString(str)      // Add string to data, returns offset
Emit_AddDataReloc(pos, offset) // Track data address fixup

// Resolution
Emit_ResolveFixups()     // Resolve all forward references
```

### CEmitCoreArch - Architecture Abstraction

**Location:** `Librarys/Compiler/CodeEmit/Library.CEmitCoreArch.ailang`

This is the **abstraction layer** between compile modules and target architecture. Compile modules call `Emit_*` functions, which delegate to `X86_*` functions.

```ailang
// These are what compile modules call:
Function.Emit_MovRaxImm64 { Input: val: Integer Body: { X86_MovRaxImm64(val) } }
Function.Emit_AddRaxRbx { Body: { X86_AddRaxRbx() } }
Function.Emit_SubRaxRbx { Body: { X86_SubRaxRbx() } }
Function.Emit_PushRax { Body: { X86_PushRax() } }
Function.Emit_PopRax { Body: { X86_PopRax() } }
Function.Emit_Syscall { Body: { X86_Syscall() } }
Function.Emit_Jmp { Input: label: Integer Body: { X86_Jmp(label) } }
Function.Emit_Jz { Input: label: Integer Body: { X86_Jz(label) } }
// ... etc
```

**To add a new architecture:**
1. Create new `CEmitARM64*.ailang` files
2. Modify CEmitCoreArch to call `ARM64_*` instead of `X86_*`
3. Compile modules remain unchanged

---

## X86-64 Target Layer

### Module Organization

| Module | Purpose |
|--------|---------|
| CEmitX86Reg | Register moves, immediate loads |
| CEmitX86Mem | Memory access, addressing modes |
| CEmitX86Stack | Push, pop, prologue, epilogue |
| CEmitX86Arith | ADD, SUB, IMUL, IDIV, NEG |
| CEmitX86Cmp | CMP, TEST, SETcc |
| CEmitX86Jump | JMP, Jcc, CALL, RET |
| CEmitX86Sys | SYSCALL instruction |
| CEmitX86Logic | AND, OR, XOR, NOT, shifts |

### Instruction Encoding Pattern

```ailang
Function.X86_AddRaxRbx {
    Body: {
        // ADD RAX, RBX = 48 01 D8
        Emit_Byte(72)   // REX.W prefix (0x48)
        Emit_Byte(1)    // ADD opcode (0x01)
        Emit_Byte(216)  // ModRM: RBX → RAX (0xD8)
    }
}

Function.X86_MovRaxImm64 {
    Input: value: Integer
    Body: {
        // MOV RAX, imm64 = 48 B8 <8 bytes>
        Emit_Byte(72)   // REX.W
        Emit_Byte(184)  // MOV RAX opcode (0xB8)
        Emit_QWord(value)
    }
}
```

---

## Output Layer

### CELFBuilder

Constructs ELF64 executable:
- ELF header
- Program headers (LOAD segments)
- Code section (.text)
- Data section (.data)
- Entry point setup

### Key Functions

```ailang
ELF_Build()              // Assemble final executable
ELF_WriteHeader()        // 64-byte ELF header
ELF_WriteProgramHeaders() // Segment descriptors
ELF_WriteCode()          // .text section
ELF_WriteData()          // .data section
```

---

## Design Guidelines

### DO's ✓

1. **Use string literals for function dispatch**
   ```ailang
   // CORRECT
   cmp = StringCompare(func_name, "Add")
   ```

2. **Add bounds checks before array/pointer access**
   ```ailang
   IfCondition GreaterEqual(index, count) ThenBlock: {
       PrintMessage("[ERROR] Index out of bounds\n")
       ReturnValue(0)
   }
   ```

3. **Check for null before dereferencing**
   ```ailang
   IfCondition EqualTo(ptr, 0) ThenBlock: {
       PrintMessage("[ERROR] Null pointer\n")
       ReturnValue(0)
   }
   ```

4. **Use `Emit_*` functions in compile modules, not `X86_*` directly**
   - Keeps compile modules architecture-independent

5. **Return 1 for success, 0 for failure consistently**

6. **Add debug output at phase boundaries**
   ```ailang
   PrintMessage("[PHASE] Starting X...\n")
   ```

7. **Keep state in `FixedPool.Compile` or `FixedPool.Emit`**
   - Centralized, easy to track

8. **Use `Compile_NewLabel()` which calls `Emit_CreateLabel()`**
   - Creates actual label entry, not just counter

### DON'Ts ✗

1. **DON'T use FixedPool for function name constants in modules**
   ```ailang
   // WRONG - causes pool collisions, segfaults
   FixedPool.ArithName {
       "ADD": Initialize="Add"
   }
   cmp = StringCompare(func_name, ArithName.ADD)
   
   // CORRECT
   cmp = StringCompare(func_name, "Add")
   ```

2. **DON'T duplicate function definitions across files**
   - If `CompileStmt_Block` exists in CCompileStmt, remove stub from CCompileMain

3. **DON'T create labels without allocating them**
   ```ailang
   // WRONG
   label = counter
   counter = Add(counter, 1)
   
   // CORRECT
   label = Emit_CreateLabel()
   ```

4. **DON'T access XArray without checking return value**
   ```ailang
   entry = XArray.XGet(array, index)
   // Always check: entry could be 0
   ```

5. **DON'T emit RET inside statement blocks**
   - Only `CompileStmt_Return` should emit RET
   - Use jumps to function exit label instead

6. **DON'T mix compile-time and emit-time label counters**
   - Use one system: `Emit_CreateLabel()` for everything

---

## Adding a New Operation

Example: Adding `BitwiseAnd(a, b)`

### 1. Create/Update Module File

`Library.CCompileBitwise.ailang`:

```ailang
LibraryImport.Compiler.Frontend.AST.CASTCore
LibraryImport.Compiler.CodeEmit.CEmitCoreArch

Function.CompileBitwise_TryCompile {
    Input: node: Address
    Output: Integer
    Body: {
        func_name = AST_GetData1(node)
        
        cmp = StringCompare(func_name, "BitwiseAnd")
        IfCondition EqualTo(cmp, 0) ThenBlock: {
            ReturnValue(CompileBitwise_And(node))
        }
        
        ReturnValue(0)
    }
}

Function.CompileBitwise_And {
    Input: node: Address
    Output: Integer
    Body: {
        arg0 = AST_GetChild(node, 0)
        arg1 = AST_GetChild(node, 1)
        
        // Compile first arg → RAX
        Compile_Expression(arg0)
        Emit_PushRax()
        
        // Compile second arg → RAX
        Compile_Expression(arg1)
        Emit_MovRegReg(Reg.RBX, Reg.RAX)
        Emit_PopRax()
        
        // AND RAX, RBX
        Emit_AndRaxRbx()
        
        ReturnValue(1)
    }
}
```

### 2. Add Emit Wrapper (if needed)

In `CEmitCoreArch`:
```ailang
Function.Emit_AndRaxRbx { Body: { X86_AndRaxRbx() } }
```

### 3. Add X86 Implementation

In `CEmitX86Logic`:
```ailang
Function.X86_AndRaxRbx {
    Body: {
        // AND RAX, RBX = 48 21 D8
        Emit_Byte(72)   // REX.W
        Emit_Byte(33)   // AND opcode (0x21)
        Emit_Byte(216)  // ModRM
    }
}
```

### 4. Update Dispatch in CCompileMain

Ensure the module is imported and called in `Compile_FunctionCall`.

---

## File Organization

```
Librarys/Compiler/
├── Frontend/
│   ├── Lexer/
│   │   ├── Library.CLexerTypes.ailang
│   │   ├── Library.CLexerKeywords.ailang
│   │   └── Library.CLexerMain.ailang
│   ├── Parser/
│   │   ├── Library.CParserMain.ailang
│   │   ├── Library.CParserStatements.ailang
│   │   └── Library.CParserDeclarations.ailang
│   └── AST/
│       ├── Library.CASTTypes.ailang
│       ├── Library.CASTCore.ailang
│       └── Library.CASTNodes.ailang
├── Compile/
│   ├── Library.CCompileMain.ailang      ← Central dispatcher
│   └── Modules/
│       ├── Library.CCompileArith.ailang
│       ├── Library.CCompileCompare.ailang
│       ├── Library.CCompileIO.ailang
│       ├── Library.CCompileStmt.ailang
│       ├── Library.CCompileFunc.ailang
│       ├── Library.CCompileExpr.ailang
│       └── ... more modules
├── CodeEmit/
│   ├── Library.CEmitTypes.ailang        ← Constants
│   ├── Library.CEmitCore.ailang         ← Buffer/label management
│   ├── Library.CEmitCoreArch.ailang     ← Architecture abstraction
│   └── X86/
│       ├── Library.CEmitX86Reg.ailang
│       ├── Library.CEmitX86Mem.ailang
│       ├── Library.CEmitX86Stack.ailang
│       ├── Library.CEmitX86Arith.ailang
│       ├── Library.CEmitX86Cmp.ailang
│       ├── Library.CEmitX86Jump.ailang
│       ├── Library.CEmitX86Sys.ailang
│       └── Library.CEmitX86Logic.ailang
└── Output/
    ├── Library.CELFTypes.ailang
    ├── Library.CELFBuilder.ailang
    └── Library.COutput.ailang
```

---

## Testing Pattern

Create test files that exercise specific features:

```ailang
// test_arith.ailang - Test arithmetic
SubRoutine.Main {
    result = Add(10, 5)
    PrintNumber(result)
    PrintMessage(" (expect 15)\n")
}
RunTask(Main)
```

Build and run:
```bash
./ailang_console_exec
load test_arith.ailang
build test_arith.x
quit
./test_arith.x
```

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Author: AILang Self-Hosting Compiler Team*