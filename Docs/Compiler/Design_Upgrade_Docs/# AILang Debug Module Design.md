# AILang Debug Module Design
## Self-Hosting Compiler Implementation

### Current Status

**Already Implemented:**
- ✅ Lexer tokens: `Token.DEBUG` (21), `Token.DEBUGASSERT` (22), `Token.DEBUGTRACE` (23), `Token.DEBUGBREAK` (24), `Token.DEBUGMEMORY` (25), `Token.DEBUGPERF` (26), `Token.DEBUGINSPECT` (27), `Token.DEBUGCONTROL` (28)
- ✅ Parser: `Parse_DebugBlock()`, `Parse_DebugAssert()`
- ✅ AST types: `AST.DEBUG_BLOCK` (900), `AST.DEBUG_ASSERT` (901), `AST.DEBUG_TRACE` (902), `AST.DEBUG_BREAK` (903)

**Missing (To Implement):**
- ❌ Debug state/level tracking
- ❌ Compile module for debug statements
- ❌ Emit support for debug instructions (RDTSC, INT3)
- ❌ Parser: level number conversion (currently hardcoded to 1)

---

### File Structure

```
Librarys/Compiler/
├── Debug/                              # NEW FOLDER
│   ├── Library.CDebugTypes.ailang      # Debug state, constants
│   ├── Library.CCompileDebug.ailang    # Compile DEBUG_* nodes
│   └── X86/
│       └── Library.CEmitDebugX86.ailang # RDTSC, INT3, debug emissions
```

---

### 1. Library.CDebugTypes.ailang

```ailang
// Debug state - tracks current debug level during compilation
FixedPool.Debug {
    "level": Initialize=0, CanChange=True       // 0-4, set by -D flag
    "perf_enabled": Initialize=0, CanChange=True // 1 if -P flag
    "initialized": Initialize=0, CanChange=True
    "assert_count": Initialize=0, CanChange=True
    "block_count": Initialize=0, CanChange=True
    "perf_count": Initialize=0, CanChange=True
}

// Debug level constants
FixedPool.DebugLevel {
    "NONE": Initialize=0        // Production - all debug stripped
    "BASIC": Initialize=1       // Assertions only
    "TRACE": Initialize=2       // + Debug blocks level 1-2
    "DETAILED": Initialize=3    // + Memory/detailed inspection
    "FULL": Initialize=4        // Everything including breakpoints
}

// Debug node data field indices (for AST_GetData*)
FixedPool.DebugField {
    "LABEL": Initialize=1       // Data1 = label string
    "LEVEL": Initialize=2       // Data2 = required level
}
```

---

### 2. Library.CCompileDebug.ailang

```ailang
LibraryImport.Compiler.Debug.CDebugTypes
LibraryImport.Compiler.Frontend.AST.CASTTypes
LibraryImport.Compiler.Frontend.AST.CASTCore
LibraryImport.Compiler.CodeEmit.CEmitCore
LibraryImport.Compiler.CodeEmit.CEmitCoreArch
LibraryImport.Compiler.Debug.X86.CEmitDebugX86

// =============================================================================
// INITIALIZATION
// =============================================================================
Function.Debug_Init {
    Input: level: Integer
    Input: perf: Integer
    Body: {
        Debug.level = level
        Debug.perf_enabled = perf
        Debug.assert_count = 0
        Debug.block_count = 0
        Debug.perf_count = 0
        Debug.initialized = 1
    }
}

// =============================================================================
// TRY COMPILE - Called from CCompileMain dispatcher
// =============================================================================
Function.CompileDebug_TryCompile {
    Input: node: Address
    Output: Integer
    Body: {
        node_type = AST_GetType(node)
        
        IfCondition EqualTo(node_type, AST.DEBUG_BLOCK) ThenBlock: {
            CompileDebug_Block(node)
            ReturnValue(1)
        }
        
        IfCondition EqualTo(node_type, AST.DEBUG_ASSERT) ThenBlock: {
            CompileDebug_Assert(node)
            ReturnValue(1)
        }
        
        IfCondition EqualTo(node_type, AST.DEBUG_TRACE) ThenBlock: {
            CompileDebug_Trace(node)
            ReturnValue(1)
        }
        
        IfCondition EqualTo(node_type, AST.DEBUG_BREAK) ThenBlock: {
            CompileDebug_Break(node)
            ReturnValue(1)
        }
        
        ReturnValue(0)  // Not a debug node
    }
}

// =============================================================================
// DEBUG BLOCK
// Debug("label", level=N) { ... }
// Compiles body only if Debug.level >= block's required level
// =============================================================================
Function.CompileDebug_Block {
    Input: node: Address
    Body: {
        label = AST_GetData1(node)
        required_level = AST_GetData2(node)
        
        // Check if this block should compile
        IfCondition LessThan(Debug.level, required_level) ThenBlock: {
            // Below required level - emit NOP and skip
            Emit_Nop()
            ReturnValue(0)
        }
        
        Debug.block_count = Add(Debug.block_count, 1)
        
        // Compile the body
        body = AST_GetChild(node, 0)
        Compile_Statement(body)
    }
}

// =============================================================================
// DEBUG ASSERT
// DebugAssert(condition, "message")
// If condition false: print message and exit
// =============================================================================
Function.CompileDebug_Assert {
    Input: node: Address
    Body: {
        // Only compile if debug level >= 1
        IfCondition LessThan(Debug.level, 1) ThenBlock: {
            Emit_Nop()
            ReturnValue(0)
        }
        
        Debug.assert_count = Add(Debug.assert_count, 1)
        
        // Get condition and optional message
        condition = AST_GetChild(node, 0)
        child_count = AST_GetChildCount(node)
        
        // Compile condition -> RAX
        Compile_Expression(condition)
        
        // Test RAX
        Emit_TestRaxRax()
        
        // Jump over failure if true (non-zero)
        pass_label = Compile_NewLabel()
        Emit_Jne(pass_label)
        
        // Assertion failed - print message
        IfCondition GreaterEqual(child_count, 2) ThenBlock: {
            message = AST_GetChild(node, 1)
            // Print "ASSERTION FAILED: "
            Compile_PrintLiteral("ASSERTION FAILED: ")
            Compile_Expression(message)
            Compile_PrintString()
        } ElseBlock: {
            Compile_PrintLiteral("ASSERTION FAILED\n")
        }
        
        // Exit with code 1
        Emit_MovRdiImm(1)
        Emit_MovRaxImm(Syscall.EXIT)
        Emit_Syscall()
        
        // Pass label - continue execution
        Emit_Label(pass_label)
    }
}

// =============================================================================
// DEBUG BREAK
// DebugBreak("label")
// Emits INT3 instruction for debugger
// =============================================================================
Function.CompileDebug_Break {
    Input: node: Address
    Body: {
        // Only compile at level 4 (full debug)
        IfCondition LessThan(Debug.level, 4) ThenBlock: {
            Emit_Nop()
            ReturnValue(0)
        }
        
        // Emit INT3 (0xCC)
        X86_Int3()
    }
}

// =============================================================================
// DEBUG PERF (future)
// DebugPerf.Start("label") / DebugPerf.End("label")
// Uses RDTSC for cycle counting
// =============================================================================
Function.CompileDebug_PerfStart {
    Input: node: Address
    Body: {
        IfCondition EqualTo(Debug.perf_enabled, 0) ThenBlock: {
            Emit_Nop()
            ReturnValue(0)
        }
        
        // RDTSC -> EDX:EAX, store to perf slot
        X86_Rdtsc()
        // TODO: Store timestamp
    }
}
```

---

### 3. Library.CEmitDebugX86.ailang

```ailang
LibraryImport.Compiler.CodeEmit.CEmitCore

// =============================================================================
// INT3 - Software Breakpoint
// Opcode: 0xCC
// =============================================================================
Function.X86_Int3 {
    Body: {
        Emit_Byte(0xCC)
        Emit.instructions_emitted = Add(Emit.instructions_emitted, 1)
    }
}

// =============================================================================
// RDTSC - Read Time Stamp Counter
// Opcode: 0x0F 0x31
// Result: EDX:EAX = 64-bit cycle count
// =============================================================================
Function.X86_Rdtsc {
    Body: {
        Emit_Byte(0x0F)
        Emit_Byte(0x31)
        Emit.instructions_emitted = Add(Emit.instructions_emitted, 1)
    }
}

// =============================================================================
// RDTSCP - Read Time Stamp Counter and Processor ID
// Opcode: 0x0F 0x01 0xF9
// Result: EDX:EAX = cycle count, ECX = processor ID
// More serializing than RDTSC
// =============================================================================
Function.X86_Rdtscp {
    Body: {
        Emit_Byte(0x0F)
        Emit_Byte(0x01)
        Emit_Byte(0xF9)
        Emit.instructions_emitted = Add(Emit.instructions_emitted, 1)
    }
}

// =============================================================================
// NOP - No Operation (for stripped debug)
// Opcode: 0x90
// =============================================================================
Function.X86_Nop {
    Body: {
        Emit_Byte(0x90)
        Emit.instructions_emitted = Add(Emit.instructions_emitted, 1)
    }
}

// =============================================================================
// Multi-byte NOPs for alignment (optional)
// =============================================================================
Function.X86_Nop2 {
    Body: {
        // 66 90 = 2-byte NOP
        Emit_Byte(0x66)
        Emit_Byte(0x90)
    }
}

Function.X86_Nop3 {
    Body: {
        // 0F 1F 00 = 3-byte NOP
        Emit_Byte(0x0F)
        Emit_Byte(0x1F)
        Emit_Byte(0x00)
    }
}
```

---

### Integration with CCompileMain

Add to `Compile_Statement()` dispatch:

```ailang
// In CCompileMain.ailang, add import:
LibraryImport.Compiler.Debug.CCompileDebug

// In Compile_Statement(), add cases:
IfCondition EqualTo(node_type, AST.DEBUG_BLOCK) ThenBlock: {
    CompileDebug_Block(node)
    ReturnValue(1)
}

IfCondition EqualTo(node_type, AST.DEBUG_ASSERT) ThenBlock: {
    CompileDebug_Assert(node)
    ReturnValue(1)
}
```

Add to `Compile_Init()`:

```ailang
// Initialize debug system with level 0 (production default)
Debug_Init(0, 0)
```

---

### Parser Fix Needed

In `Library.CParserStatements.ailang`, the `Parse_DebugBlock` function has a TODO:

```ailang
// Current code:
IfCondition EqualTo(PParser.p_current_type, PToken.P_NUMBER) ThenBlock: {
    // TODO: Convert string to int
    level = 1  // <-- HARDCODED!
    Parse_Advance()
}

// Fix needed - use StringToInt:
IfCondition EqualTo(PParser.p_current_type, PToken.P_NUMBER) ThenBlock: {
    level_str = PParser.p_current_value
    level = Str_ToInt(level_str)
    Parse_Advance()
}
```

---

### Command Line Integration

The console/compiler needs to parse `-D` and `-P` flags:

```ailang
// In ailang_console.ailang or main compiler:
IfCondition StringEquals(arg, "-D") ThenBlock: {
    Debug_Init(1, 0)
}
IfCondition StringEquals(arg, "-D2") ThenBlock: {
    Debug_Init(2, 0)
}
IfCondition StringEquals(arg, "-D3") ThenBlock: {
    Debug_Init(3, 0)
}
IfCondition StringEquals(arg, "-D4") ThenBlock: {
    Debug_Init(4, 0)
}
IfCondition StringEquals(arg, "-P") ThenBlock: {
    Debug.perf_enabled = 1
}
```

---

### Testing Plan

1. **Basic test** - Debug block at level 1:
```ailang
Debug("test", level=1) {
    PrintMessage("Debug level 1\n")
}
RunTask(Main)
```
Compile with `-D` → should print
Compile without `-D` → should be silent

2. **Assert test**:
```ailang
x = 5
DebugAssert(GreaterThan(x, 0), "x must be positive")
DebugAssert(LessThan(x, 3), "x must be less than 3")  // Should fail
```

3. **Performance test** (future):
```ailang
DebugPerf.Start("loop")
i = 0
WhileLoop LessThan(i, 1000) {
    i = Add(i, 1)
}
DebugPerf.End("loop")
```

---

### Priority Order

1. **CDebugTypes.ailang** - Create state pool
2. **CEmitDebugX86.ailang** - INT3, RDTSC, NOP
3. **CCompileDebug.ailang** - Block and Assert compilation
4. **Parser fix** - StringToInt for level
5. **CCompileMain integration** - Add dispatch
6. **Console integration** - Parse -D flags
7. **Test suite** - Verify all levels work