# AILang Compiler — 02: Compile Layer (CCompileMain + Modules)

## Overview

The compile layer is the heart of the compiler. It walks the AST and emits machine code via the Emit_* abstraction layer. The central dispatcher (`CCompileMain`) routes each AST node to the appropriate compile module via type dispatch and string-based function name matching.

```
AST root ──▶ CCompileMain (dispatcher)
                 │
                 ├─ Compile_Node(type_dispatcher)
                 │     ├─ AST.FUNCTION → CompileFunc_*
                 │     ├─ AST.SUBROUTINE → CompileFunc_*
                 │     ├─ AST.POOL_* → CompilePool_*
                 │     ├─ AST.ASSIGNMENT → CompileStmt_Assignment
                 │     ├─ AST.IF → CompileStmt_If
                 │     ├─ AST.WHILE → CompileStmt_While
                 │     ├─ AST.RETURN → CompileStmt_Return
                 │     ├─ AST.BLOCK → CompileStmt_Block
                 │     ├─ AST.CALL → Compile_FunctionCall
                 │     ├─ AST.IDENTIFIER → load variable
                 │     ├─ AST.NUMBER → Emit_MovRaxImm64
                 │     ├─ AST.STRING → Emit_AddString + LEA
                 │     └─ ...more types
                 │
                 └─ Compile_FunctionCall(name_dispatcher)
                       ├─ CompileArith_TryCompile (Arith)
                       ├─ CompileCompare_TryCompile (Compare)
                       ├─ CompileIO_TryCompile (IO)
                       ├─ CompileStmt_TryCompile (Stmt)
                       ├─ CompileLogic_TryCompile (Logic)
                       ├─ CompileBitwise_TryCompile (Bitwise)
                       ├─ CompileString_TryCompile (String)
                       ├─ CompileMem_TryCompile (Mem)
                       ├─ CompileFile_TryCompile (File I/O)
                       ├─ CompileSystem_TryCompile (System)
                       ├─ CompileArray_TryCompile (Array)
                       ├─ CompileAtomic_TryCompile (Atomic)
                       └─ ...25 modules in dispatch chain
```

---

## 1. CCOMPILEMAIN — Central Dispatcher (48KB)

### 1.1 State (FixedPool.Compile)
```
ast: Address              — root AST node
functions: XArray         — compiled function entries
variables: XArray         — variable entries [name, offset, type, size, flags]
current_func: Address     — current function name string
stack_offset: Integer     — current stack frame offset (negative)
stack_size: Integer       — total stack space allocated
loop_stack: XArray        — [break_label, continue_label] pairs
loop_depth: Integer       — nesting depth of current loops
error: Integer            — error flag
error_msg: Address        — error message string
nodes_compiled: Integer   — counter
pending_pool_type: Address — pool type for next assignment
return_label: Integer     — function return label
current_return_label: Integer — current function's return target
```

### 1.2 Key Functions

#### Initialization & Entry
```
Compile_Init() → Integer
    Initialize all compile state, zero counters, create XArrays

Compile_Free() → void
    Deallocate all resources

Compile_Program(ast) → Integer
    MAIN ENTRY POINT. Walk AST children (declarations), compile each:
    - POOL nodes first (FixedPool, DynamicPool, etc.)
    - FUNCTION nodes second
    - SUBROUTINE nodes third
    - Then compile Main/entry code (RunTask calls)
    Returns 1 on success

Compile_Node(node) → Integer
    TYPE DISPATCHER. Switch on AST_GetType(node):
    AST.FUNCTION → CompileFunc_Define
    AST.SUBROUTINE → CompileFunc_Define
    AST.POOL_FIXED+ → CompilePool_Define
    AST.ASSIGNMENT → CompileStmt_Assignment
    AST.IF → CompileStmt_If
    AST.WHILE → CompileStmt_While
    AST.FOR_EVERY → CompileStmt_ForEvery
    AST.SWITCH/BRANCH → CompileStmt_Switch
    AST.FORK → CompileStmt_Fork
    AST.RETURN → CompileStmt_Return
    AST.BLOCK → CompileStmt_Block
    AST.EXIT_LOOP → CompileStmt_Break
    AST.CONTINUE_LOOP → CompileStmt_Continue
    AST.CALL → Compile_FunctionCall
    AST.IDENTIFIER → CompileExpr_LoadVariable
    AST.NUMBER → Emit_MovRaxImm64(StringToNumber(value))
    AST.STRING → Emit_AddString + Emit_LeaRaxRbpOffset(data_offset)
    AST.BINARY_OP → CompileExpr_BinaryOp (fallback)
    AST.UNARY_OP → CompileExpr_UnaryOp
    AST.LIBRARY_IMPORT → skip (handled by import resolver)
    Returns 0 on error, 1 on success

Compile_FunctionCall(node) → Integer
    NAME DISPATCHER. Module chain:
    result = CompileArith_TryCompile(node)
    if result==1: return 1
    
    result = CompileCompare_TryCompile(node)
    if result==1: return 1
    
    result = CompileIO_TryCompile(node)
    ... etc for all 25 modules ...
    
    // If no module handled it, treat as user function call
    result = CompileFunc_Call(node)
    return result

Compile_Expression(node) → Integer
    Evaluate expression, leave result in RAX
    Dispatches to Compile_Node for each sub-expression type
    Handles: literals, variables, binary/unary ops, function calls,
             member access, index access, pointer field access

Compile_NewLabel() → Integer
    Create new label via Emit_CreateLabel(), return label ID

Compile_PushLoop(break_label, continue_label) → void
    Push break/continue labels onto loop_stack

Compile_PopLoop() → void
    Pop break/continue labels from loop_stack

Compile_Error(msg) → void
    Set error flag, print message

Compile_RegisterLocal(name, offset) → void
    Add variable entry to Compile.variables

Compile_AddVariable(name, type, size, flags) → Integer
    Allocate variable entry, push to variables array
    Returns stack offset of variable
```

### 1.3 Compile_Program Flow

```
Compile_Program(ast)
    │
    ├─ Phase 1: Collect and compile all POOL definitions
    │   for each child:
    │     if AST.POOL_*: CompilePool_Define(child)
    │
    ├─ Phase 2: Compile all FUNCTION definitions
    │   for each child:
    │     if AST.FUNCTION: CompileFunc_Define(child)
    │     if AST.SUBROUTINE: CompileFunc_Define(child)
    │
    ├─ Phase 3: Compile entry code
    │   Find RunTask("Main") or SubRoutine.Main
    │   Generate ELF entry point:
    │     Emit_AddSymbol("_start", ELFSymType.FUNC)
    │     CompileFunc_Call("Main") or compile SubRoutine body
    │     Emit_MovRdiRax()  // exit code
    │     Emit_MovRaxImm64(60)  // sys_exit
    │     Emit_Syscall()
    │
    └─ Emit_PrintStats()
```

---

## 2. COMPILE MODULE PATTERN

Every compile module follows this exact pattern:

```
LibraryImport.Compiler.Frontend.AST.CASTTypes
LibraryImport.Compiler.Frontend.AST.CASTCore
LibraryImport.Compiler.CodeEmit.CEmitCoreArch

// DISPATCHER
Function.CompileMod_TryCompile {
    Input: node: Address
    Output: Integer    // 1=handled, 0=pass
    Body: {
        func_name = AST_GetData1(node)
        
        cmp = StringCompare(func_name, "OperationName")
        IfCondition EqualTo(cmp, 0) ThenBlock: {
            ReturnValue(CompileMod_OperationName(node))
        }
        
        // More operations...
        
        ReturnValue(0)  // Not handled by this module
    }
}

// OPERATION HANDLER
Function.CompileMod_OperationName {
    Input: node: Address
    Output: Integer
    Body: {
        args = AST_GetChildren(node)
        
        // Compile arguments (result in RAX)
        // Manipulate stack/registers
        // Emit machine code
        
        ReturnValue(1)
    }
}
```

---

## 3. COMPILE MODULE CATALOG (24 modules)

### 3.1 CCompileArith — Arithmetic Operations
**Functions:** `Add, Subtract, Multiply, Divide, Modulo, Negate, Increment, Decrement`
**Size:** 18KB
```
CompileArith_Add(node)
    Compile left arg → RAX → push
    Compile right arg → RAX → RBX
    pop RAX
    Emit_AddRaxRbx()

CompileArith_Subtract(node)
    Same pattern: push right, compile left to RBX, pop to RAX, Emit_SubRaxRbx()

CompileArith_Multiply(node)
    push right, compile left to RBX, pop RAX, Emit_ImulRaxRbx()

CompileArith_Divide(node)
    push right, compile left to RBX, test for zero
    pop RAX, Emit_Cqo(), Emit_IdivRbx()

CompileArith_Modulo(node)
    Same as divide but return RDX (remainder)

CompileArith_Negate(node)
    compile operand → RAX, Emit_NegRax()

CompileArith_Increment(node)
    compile target, Emit_IncRax(), store back

CompileArith_Decrement(node)
    compile target, Emit_DecRax(), store back
```

### 3.2 CCompileCompare — Comparison Operations
**Functions:** `EqualTo, NotEqual, LessThan, GreaterThan, LessEqual, GreaterEqual`
**Size:** 5.6KB
```
Pattern for all comparisons:
    compile left → RAX, push
    compile right → RAX → RBX, pop RAX
    Emit_CmpRaxRbx()
    Emit_Setcc(AL)         // SETcc based on comparison type
    Emit_MovzxRaxAl()      // zero-extend to 64-bit

Comparison mapping:
    EqualTo → SETE, NotEqual → SETNE
    LessThan → SETL, GreaterThan → SETG
    LessEqual → SETLE, GreaterEqual → SETGE
```

### 3.3 CCompileIO — I/O Operations
**Functions:** `PrintMessage, PrintNumber, PrintString, PrintChar, ReadLine, ReadChar`
**Size:** 17KB
```
CompileIO_PrintMessage(node)
    compile string arg → RAX (pointer to data section)
    Emit_MovRsiRax()         // buf = string pointer
    strlen inline loop       // compute length → RDX
    Emit_MovRdiImm64(1)      // fd = 1 (stdout)
    Sys_Write()

CompileIO_PrintNumber(node)
    compile number → RAX
    int-to-string conversion (inline)
    then PrintMessage

CompileIO_PrintString(node)
    compile string → RAX
    Emit_MovRsiRax()
    strlen → RDX, RDI=1, Sys_Write()
```

### 3.4 CCompileStmt — Statement Compilation (29KB)
This is the most complex module. See detailed breakdown:

```
CompileStmt_Assignment(node)
    Check for pointer field write (ptr@field = value)
    Else: compile RHS → RAX, store to variable

CompileStmt_Return(node)
    Compile return value → RAX
    Jump to function exit label (Compile.current_return_label)
    Or Emit_Ret() if no exit label

CompileStmt_If(node)
    condition = child[0], then_block = child[1], else_block = child[2]?
    Compile condition → RAX
    Emit_TestRaxRax(), Emit_Jz(else_label)
    Compile then_block
    If else exists: Emit_Jmp(end_label)
    Mark else_label, compile else_block (if any)
    Mark end_label

CompileStmt_While(node)
    loop_start = new label, loop_end = new label
    PushLoop(loop_end, loop_start)
    Mark loop_start
    Compile condition → RAX
    Emit_TestRaxRax(), Emit_Jz(loop_end)
    Compile body
    Emit_Jmp(loop_start)
    Mark loop_end
    PopLoop()

CompileStmt_ForEvery(node)
    Allocate 4 stack slots: [var, index, length, array]
    Register loop variable
    Compile iterable → RAX
    Store array ptr, get length (array[0])
    Loop: compare index < length
    Load element: array + 8 + index*8
    Compile body
    Increment index, jump to start

CompileStmt_Block(node)
    Iterate children, compile each with Compile_Node()

CompileStmt_Break(node)
    Get break_label from loop_stack top
    Emit_Jmp(break_label)

CompileStmt_Continue(node)
    Get continue_label from loop_stack top
    Emit_Jmp(continue_label)

CompileStmt_Switch(node) [FAST PATH + SLOW PATH]
    Pre-scan cases: if all values are AST.NUMBER literals → FAST PATH
    FAST: compile expr once → RAX, CMP RAX,imm32; JE case_body per case
    SLOW: compile expr, push to stack, peek+compare per case, pop at landing
    Default support with fallback

CompileStmt_Fork(node)
    Same pattern as IfCondition

CompileStmt_Try(node)
    try body, catch jump target, finally block
    Catch label: jumped to on error
    Finally label: always runs before end
```

### 3.5 CCompileExpr — Expression Compilation (15KB)
```
CompileExpr_LoadVariable(name)
    offset = Scope_Resolve(name)
    If pool var: Emit_MovRaxR15Offset(pool_offset)
    If local: Emit_MovRaxRbpOffset(offset)
    If resolve_type==0: error "Variable not found"

CompileExpr_StoreVariable(name)
    offset = Scope_Resolve(name)
    If not found: auto-create variable (Compile.stack_offset += 8)
    If pool: Emit_MovR15OffsetRax(pool_offset)
    Else: Emit_MovRbpOffsetRax(offset)

CompileExpr_MemberAccess(node)
    member_name = data1, base = child[0]
    Load base as variable
    Load first field (dereference pointer)

CompileExpr_PointerFieldAccess(node)  // base@field
    Delegate to CompilePool_FieldReadSimple(base_var, field_name)

CompileExpr_IndexAccess(node)  // array[index]
    Compile base (load pointer)
    Compile index (constant or expression)
    Load [RAX + index*8]
```

### 3.6 CCompileFunc — Function Definition Compilation (44KB)
```
CompileFunc_Define(node)
    Save scope: Scope_SaveAndClear(func_name)
    Allocate parameters (load from RDI, RSI, RDX, RCX, R8, R9)
    Create prologue: PushRbp, MovRbpRsp, SubRsp(stack_size)
    Compile function body
    Create function return label
    Emit return_label, epilogue: MovRspRbp, PopRbp, Ret
    Restore scope: Scope_Restore()

CompileFunc_Call(node)
    Push caller-saved registers
    Compile arguments (evaluate right to left, push)
    Emit_Call(function_label)
    Clean up stack (pop arguments)
    Pop caller-saved registers
    Result in RAX

CompileFunc_HandleReturnLabel(node)
    Create return label for current function
```

### 3.7 CCompilePool — Pool Definition Compilation (49KB)
**Handles:** FixedPool, DynamicPool, TemporalPool, NeuralPool, KernelPool, ActorPool, SecurityPool, ConstrainedPool, FilePool, LinkagePool
```
CompilePool_Define(node)
    For each pool type, create R15-based memory layout
    Allocate pool data block
    Store initial values
    Register pool variables with high-bit offsets

CompilePool_FieldReadSimple(base_var, field_name)
    Load field from LinkagePool structure
    Compute field offset, Emit_MovRaxR15Offset(offset)

CompilePool_FieldWriteSimple(base_var, field_name)
    Store RAX to LinkagePool field
    Compute field offset, Emit_MovR15OffsetRax(offset)
```

### 3.8 CCompileScope — Scope Management (17KB)
```
Scope_Init() → Integer
    Create saved_scopes XArray, func_params XArray

Scope_SaveAndClear(func_name)
    Save current variables to scope record
    Preserve pool variables
    Clear local variables
    Reset stack_offset to 0

Scope_Restore()
    Pop scope record
    Free current local variables
    Restore saved variables and stack state

Scope_Resolve(name) → Integer
    Resolve variable: params first, then variables
    Sets Scope.resolve_type: 0=not found, 1=param, 2=local, 3=pool
    Returns offset

Scope_AddParameter(name, offset)
    Register parameter for current function

Scope_GetVarPoolType(name) → Address
    Look up pool type for variable (e.g., "LinkagePool.X")
```

### 3.9 Remaining Modules
```
CCompileFile (22KB)    — FileOpen, FileRead, FileWrite, FileClose, FileSeek,
                          FileGetSize, FileExists, ReadTextFile, WriteTextFile,
                          ReadBinaryFile
CCompileLogic (6KB)    — And, Or, Not (logical)
CCompileBitwise (8.5KB)— BitwiseAnd, BitwiseOr, BitwiseXor, BitwiseNot, LShift, RShift
CCompileMem (23KB)     — Allocate, Deallocate, StoreValue, LoadValue, Dereference
CCompileString (34KB)  — StringCompare, StringLength, StringCopy, StringConcat,
                          StringSubstring, StringToNumber, SetByte, GetByte
                          (6 files: Core + Convert + Manip + Search + main)
CCompileArray (8KB)    — XArray.XCreate, XPush, XPop, XGet, XSet, XSize, XDestroy
CCompileAtomic (8KB)   — AtomicAdd, AtomicSub, AtomicXchg, AtomicCmpXchg
CCompileSystem (7.5KB) — Syscall invocation, inline assembly
CSysDispatch (285KB)   — 300+ Sys_*() functions, each dispatches on Emit.os
                          e.g., Sys_Read() → Linux: syscall 0, Haiku: syscall 140
CCompilerOptimizer (20KB) — Compile-time peephole: constant folding, dead store elimination
COptimizeHoist (31KB)  — Loop-invariant code motion hoisting
CCompileScopebu (14KB) — Scope backup/restore utility
```

---

## 4. MODULE DISPATCH CHAIN ORDER

In `Compile_FunctionCall`, modules are tried in THIS ORDER:

```
1.  CompileArith_TryCompile      — arithmetic ops
2.  CompileCompare_TryCompile    — comparison ops
3.  CompileLogic_TryCompile      — logical ops (And, Or, Not)
4.  CompileBitwise_TryCompile    — bitwise ops
5.  CompileIO_TryCompile         — I/O ops
6.  CompileString_TryCompile     — string ops
7.  CompileMem_TryCompile        — memory ops
8.  CompileArray_TryCompile      — array ops
9.  CompileAtomic_TryCompile     — atomic ops
10. CompileFile_TryCompile       — file I/O ops
11. CompileSystem_TryCompile     — system ops
    ...
    If none match → CompileFunc_Call (user-defined function)
```

---

## 5. COMPILE-TIME VALUE REPRESENTATION

| Source Type | Compile Result |
|-------------|---------------|
| Integer literal `42` | `Emit_MovRaxImm64(42)` → RAX |
| String literal `"hello"` | `Emit_AddString("hello")` → data section offset |
| Identifier `x` | `Emit_MovRaxRbpOffset(offset_of_x)` → RAX |
| Pool variable `Pool.field` | `Emit_MovRaxR15Offset(pool_offset)` → RAX |
| Function call `f(a,b)` | Push args, `Emit_Call(f_label)`, result in RAX |
| Binary op `a+b` | Sub-expressions → registers, `Emit_AddRaxRbx()` |
| `Allocate(n)` | `Emit_MovRdiImm64(n)`, `Sys_Mmap()` |

---

*Document 02 of 10 — Compile Layer*
