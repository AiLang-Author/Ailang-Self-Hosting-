# Variable Support Changes Analysis
## Session: Week 1 Day 5 (December 28, 2025)
## Commit: 3a770c9 (BROKEN) vs db93efe (WORKING)

---

## Summary

Attempted to add variable support to the self-hosting compiler. Changes caused segfault at startup - crash occurred before even the first `PrintMessage` in ConsoleMain. Root cause: circular import dependencies and moving code between modules incorrectly.

---

## Working Baseline

**Commit:** `db93efe` - "PrintMessage working - unified function call dispatch"

**What works:**
- `PrintMessage("Hello World")` ✓
- `PrintNumber(42)` ✓
- `Add(10, 5)` → 15 ✓
- `Subtract(10, 3)` → 7 ✓
- `Multiply(6, 7)` → 42 ✓
- `Divide(100, 4)` → 25 ✓
- `Modulo(17, 5)` → 2 ✓
- ELF generation, code emission ✓
- Console application starts and runs ✓

---

## Changes Made (Broken Commit 3a770c9)

### Files Modified:
1. `Library.CCompileMain.ailang`
2. `Library.CCompileExpr.ailang`
3. `Library.CCompileFunc.ailang`
4. `Library.CCompileIO.ailang`
5. `Library.CCompileTypes.ailang`
6. `Library.CCompileCompare.ailang`
7. `Library.CCompileLogic.ailang`
8. `Library.CCompileBitwise.ailang`
9. `Library.CCompileMem.ailang`

---

## GOOD Changes (Cherry-Pick These Later)

### 1. Fixed Import Paths
Several modules had wrong import path for CCompileTypes:

```ailang
// WRONG (old)
LibraryImport.Compiler.Compile.CCompileTypes

// CORRECT (new)
LibraryImport.Compiler.Compile.Modules.CCompileTypes
```

**Files to fix:**
- CCompileBitwise.ailang
- CCompileCompare.ailang
- CCompileLogic.ailang
- CCompileMem.ailang

### 2. Fixed Emit Function Names
SETcc instruction wrappers had wrong names:

```ailang
// WRONG (old)
Emit_SetEAl()
Emit_SetNEAl()
Emit_SetLAl()
Emit_SetGAl()
Emit_SetLEAl()
Emit_SetGEAl()
Emit_SetZAl()

// CORRECT (new)
Emit_Sete()
Emit_Setne()
Emit_Setl()
Emit_Setg()
Emit_Setle()
Emit_Setge()
Emit_Setz()
```

**Files to fix:**
- CCompileCompare.ailang (lines 122-137)
- CCompileLogic.ailang (line 185)
- CCompileExpr.ailang (line 240)

### 3. Added Missing Pool Fields to CCompileTypes
Added stub functions and UnaryOp pool:

```ailang
Function.Compile_FindPool { ... }
Function.Compile_FindPoolField { ... }

FixedPool.UnaryOp {
    "NEGATE": Initialize=1, CanChange=False
    "NOT": Initialize=2, CanChange=False
    "BITNOT": Initialize=3, CanChange=False
}
```

---

## BAD Changes (Caused Segfault)

### 1. Deleted Compile_Expression from CCompileMain

**What happened:** Removed ~95 lines of `Compile_Expression` function from CCompileMain, planning to use the version in CCompileExpr instead.

**Why it broke:** CCompileExpr has broken imports and calls non-existent functions.

**Rule:** Keep `Compile_Expression` in CCompileMain. It's the central dispatcher.

### 2. CCompileExpr Imports CCompileFunc

```ailang
// ADDED (BAD)
LibraryImport.Compiler.Compile.Modules.CCompileFunc
```

**Why it broke:** Creates import dependency chain that leads to circular dependencies.

### 3. CCompileFunc Removed CCompileMain Import

```ailang
// REMOVED (BAD)
LibraryImport.Compiler.Compile.CCompileMain
```

**Why it broke:** CCompileFunc needs `Compile_Node` from CCompileMain to compile function bodies.

### 4. CCompileIO Imports CCompileExpr

```ailang
// ADDED (BAD)
LibraryImport.Compiler.Compile.Modules.CCompileExpr
```

**Why it broke:** Pulls broken CCompileExpr into the build chain.

### 5. Changed Identifier Handling

```ailang
// OLD (working)
IfCondition EqualTo(node_type, AST.IDENTIFIER) ThenBlock: {
    name = AST_GetData1(node)
    ReturnValue(CompileExpr_LoadVariable(name))
}

// NEW (broken)
IfCondition EqualTo(node_type, AST.IDENTIFIER) ThenBlock: {
    ReturnValue(CompileExpr_Identifier(node))
}
```

**Why it broke:** `CompileExpr_Identifier` doesn't exist in the working codebase. `CompileExpr_LoadVariable` is a stub that returns 0.

---

## The Circular Dependency Problem

### What I Created:
```
CCompileMain 
    → imports CCompileIO 
        → imports CCompileExpr 
            → imports CCompileFunc 
                → needs CCompileMain (CIRCULAR!)
```

### Correct Architecture:
```
CCompileMain (dispatcher)
    ├── imports CCompileIO      (no cross-imports)
    ├── imports CCompileArith   (no cross-imports)
    ├── imports CCompileFunc    (no cross-imports)
    ├── imports CCompileExpr    (no cross-imports)
    └── imports CCompileTypes   (shared state only)

Modules:
    └── import CCompileTypes (shared state)
    └── import CodeEmit layers
    └── DO NOT import other Compile modules
    └── DO NOT import CCompileMain
```

### Design Rule:
**Modules call STUBS defined in CCompileMain for cross-module calls.**
The stubs are forward declarations that get linked at compile time.

---

## How To Properly Add Variable Support

### Step 1: Keep Compile_Expression in CCompileMain
Don't move it. Modules dispatch TO it, it dispatches FROM it.

### Step 2: Implement CompileExpr_LoadVariable in CCompileMain
Currently a stub returning 0. Add actual implementation:

```ailang
Function.CompileExpr_LoadVariable {
    Input: name: Address
    Output: Integer
    Body: {
        // Look up variable in Compile.variables
        // If found, emit: MOV RAX, [RBP - offset]
        // Return 1 on success, 0 on failure
    }
}
```

### Step 3: Add Variable Registration
In `Compile_Node` for AST.ASSIGNMENT:
1. Check if variable exists
2. If not, allocate stack slot
3. Register in Compile.variables
4. Compile RHS expression
5. Store RAX to stack slot

### Step 4: Test Incrementally
After EACH change:
```bash
python3 main.py ailang_console.ailang
./ailang_console_exec
```

---

## Test Files Reference

**Working tests (use these to verify):**
- `test_msg.ailang` - PrintMessage test
- `test_min.ailang` - PrintNumber test  
- `test_arith.ailang` - All arithmetic ops
- `test_mod.ailang` - Modulo test

**Target test (currently broken):**
- `test_var.ailang` - Simple `x = 10; PrintNumber(x)`

---

## Commands to Restore Working State

```bash
# If on broken commit, restore working files:
git checkout db93efe -- Librarys/Compiler/Compile/

# Verify:
python3 main.py ailang_console.ailang
./ailang_console_exec
```

---

## Diff File Location

Full diff saved to: `my_broken_changes.diff`

View specific file changes:
```bash
git diff db93efe 3a770c9 -- Librarys/Compiler/Compile/Library.CCompileMain.ailang
```

---

## Lessons Learned

1. **Don't move functions between modules** - especially core dispatchers
2. **Modules must not cross-import** - leads to circular dependencies
3. **Test after EVERY change** - not after bulk edits
4. **Stubs are intentional** - they're placeholders for cross-module calls
5. **The architecture is: Main → Modules, never Modules → Main**

---

*Document created: December 28, 2025*
*Status: Working baseline restored at db93efe*