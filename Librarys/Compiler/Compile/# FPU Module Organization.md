# FPU Module Organization

## Folder Structure

```
Librarys/Compiler/
├── Compile/
│   ├── Library.CCompileMain.ailang          ← Add FPU dispatch here
│   ├── Modules/
│   │   └── ...existing modules...
│   │
│   └── FPU/
│       ├── Library.FPUTypes.ailang          ← Shared constants (XMM, FloatOp, etc.)
│       │
│       ├── X86/
│       │   ├── Library.FPUEmitX86SSE.ailang      ← SSE2 float/vector byte emission
│       │   ├── Library.FPUEmitX86MemOps.ailang   ← SSE2 memory ops byte emission
│       │   ├── Library.FPUCompileX86SSE.ailang   ← Float_*, Vec2_* compilation
│       │   └── Library.FPUCompileX86MemOps.ailang ← MemSet/Copy/Compare/Chr compilation
│       │
│       ├── ARM/                                   ← Future
│       │   ├── Library.FPUEmitARMNEON.ailang
│       │   └── Library.FPUCompileARMNEON.ailang
│       │
│       └── SPIRV/                                 ← Future: GPU compute
│           └── Library.FPUSPIRVEmit.ailang
```

## Integration with CCompileMain

Add to `CCompileMain.ailang`:

```ailang
// At top - conditional import based on target
LibraryImport.Compiler.Compile.FPU.X86.FPUCompileX86SSE
LibraryImport.Compiler.Compile.FPU.X86.FPUCompileX86MemOps

// In Compile_FunctionCall, after existing module dispatch:

Function.Compile_FunctionCall {
    Input: node: Address
    Output: Integer
    Body: {
        // ... existing dispatch code ...
        
        // ─────────────────────────────────────────────────────────────────
        // FPU/SIMD Operations - ISA-specific dispatch
        // ─────────────────────────────────────────────────────────────────
        IfCondition EqualTo(Emit.target, Arch.X86_64) ThenBlock: {
            // Try float/vector ops
            result = FPUCompileX86_TryCompile(node)
            IfCondition EqualTo(result, 1) ThenBlock: {
                ReturnValue(1)
            }
            
            // Try memory ops (MemSet, MemCopy, etc.)
            result = FPUCompileX86MemOps_TryCompile(node)
            IfCondition EqualTo(result, 1) ThenBlock: {
                ReturnValue(1)
            }
        }
        
        // Future: ARM NEON
        // IfCondition EqualTo(Emit.target, Arch.ARM64) ThenBlock: {
        //     result = FPUCompileARMNEON_TryCompile(node)
        //     ...
        // }
        
        // ... rest of dispatch ...
    }
}
```

## Import Chain

```
CCompileMain
    └── FPUCompileX86SSE
            ├── FPUTypes (constants only)
            ├── FPUEmitX86SSE (byte emission)
            ├── CASTCore (for AST access)
            └── CEmitCore (for Emit_Byte, labels)
    └── FPUCompileX86MemOps
            ├── FPUTypes
            ├── FPUEmitX86MemOps
            ├── CASTCore
            └── CEmitCoreArch (for Emit_Jmp, Emit_Je, etc.)
```

## Key Design Points

1. **No FixedPools in emit/compile files** - All constants in FPUTypes.ailang

2. **Self-contained** - FPU folder can be tested without CCompileMain by:
   - Creating test harness that calls emit functions directly
   - Checking byte output against known-good sequences

3. **ISA selection in CCompileMain** - The `Emit.target` check happens once at dispatch level

4. **Clean separation**:
   - `FPUEmit*` = raw byte emission (no AST knowledge)
   - `FPUCompile*` = AST traversal + calls emit functions

5. **Future extensibility**:
   - Add `ARM/` folder for NEON
   - Add `SPIRV/` folder for GPU compute
   - CCompileMain just adds another target check

## Testing Standalone

```ailang
// test_fpu_emit.ailang - Test byte emission directly
SubRoutine.Main {
    // Initialize emit buffer
    Emit_Init()
    
    // Emit some SSE instructions
    X86_ADDSD_XMM0_XMM1()
    X86_MOVDQU_XMM0_DerefRSI()
    X86_BroadcastAL_XMM0()
    
    // Check Emit.code_size and dump bytes
    PrintMessage("Emitted bytes: ")
    PrintNumber(Emit.code_size)
    PrintMessage("\n")
    
    Emit_Free()
}
RunTask(Main)
```

## Operations Supported

### Float (scalar double)
- `Float_Add`, `Float_Sub`, `Float_Mul`, `Float_Div`
- `Float_Min`, `Float_Max`, `Float_Sqrt`
- `Float_FromInt`, `Float_ToInt`, `Float_Round`
- `Float_Eq`, `Float_Lt`, `Float_Gt`, `Float_Le`, `Float_Ge`

### Vec2 (packed 2x double)
- `Vec2_Add`, `Vec2_Sub`, `Vec2_Mul`
- `Vec2_Dot`

### Memory Operations (SSE2 accelerated)
- `MemorySet(dest, value, count)` - 16 bytes at a time
- `MemoryCopy(dest, src, count)` - 16 bytes at a time
- `MemCompare(addr1, addr2, len)` - parallel byte compare
- `MemChr(addr, byte, len)` - parallel byte search

All memory ops fall back to scalar for <16 byte remainder.