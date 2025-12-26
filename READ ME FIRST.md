# AILANG Self-Hosting Compiler - Common Fuckups and How to Fix Them

## CRITICAL: Don't Break Shit Checklist

### 1. AST Function Names - USE THE CORRECT ONES
**THE PROBLEM:** Helper functions like `AST_GetNodeType`, `AST_GetFunctionName`, `AST_GetAssignTarget` **DO NOT EXIST**.

**THE SOLUTION:** Use the actual API:
- `AST_GetType(node)` - get node type
- `AST_GetData1(node)` - get first data field (names, values, etc.)
- `AST_GetData2/3/4(node)` - other data fields
- `AST_GetChild(node, index)` - get child by index
- `AST_GetChildCount(node)` - get number of children

**Common mistakes:**
```ailang
// WRONG - these don't exist
AST_GetNodeType(node)
AST_GetFunctionName(node)
AST_GetAssignTarget(node)
AST_GetAssignValue(node)

// RIGHT
AST_GetType(node)
AST_GetData1(node)  // function names, identifiers, etc.
AST_GetChild(node, 0)  // first child
```

### 2. Node Type Constants - Use AST.* not NodeType.*
**THE PROBLEM:** `NodeType.ASSIGNMENT`, `NodeType.FOR` etc. don't exist.

**THE SOLUTION:** Use `AST.ASSIGNMENT`, `AST.WHILE`, `AST.FOR_EVERY`, etc.

**Location:** Defined in `Librarys/Compiler/Frontend/AST/Library.CASTTypes.ailang`
```bash
# Find what's actually defined:
grep "Initialize=" Librarys/Compiler/Frontend/AST/Library.CASTTypes.ailang
```

### 3. Child Node Access - CHECK THE FUCKING COUNT FIRST
**THE PROBLEM:** Accessing `AST_GetChild(node, 2)` when node only has 2 children (indices 0, 1) = **SEGFAULT**.

**THE SOLUTION:** 
```ailang
// WRONG - blindly access child
else_block = AST_GetChild(node, 2)  // CRASH if no else!

// RIGHT - check first
child_count = AST_GetChildCount(node)
else_block = 0
IfCondition GreaterThan(child_count, 2) ThenBlock: {
    else_block = AST_GetChild(node, 2)
}
```

**Common offenders:**
- If statements without else blocks (2 children, not 3)
- Optional parameters

### 4. AST Node Structures - RTFM
**Know the layout before you code:**
```ailang
// Assignment: target=DATA1, value=child[0]
node = AST_Create(AST.ASSIGNMENT)
AST_SetData1(node, target_name)
AST_AddChild(node, value_expr)

// If: condition=child[0], then=child[1], else=child[2] (OPTIONAL)
node = AST_Create(AST.IF)
AST_AddChild(node, condition)
AST_AddChild(node, then_block)
IfCondition NotEqual(else_block, 0) ThenBlock: {
    AST_AddChild(node, else_block)  // Optional!
}

// While: condition=child[0], body=child[1]
node = AST_Create(AST.WHILE)
AST_AddChild(node, condition)
AST_AddChild(node, body)

// ForEvery: var=DATA1, iterable=child[0], body=child[1]
node = AST_Create(AST.FOR_EVERY)
AST_SetData1(node, var_name)
AST_AddChild(node, iterable)
AST_AddChild(node, body)
```

**Find the truth:** `Librarys/Compiler/Frontend/AST/Library.CASTNodes.ailang` - search for `AST_Make*`

### 5. Architecture Separation - Compile vs Emit
**THE RULE:** Compile modules call `Emit_*` functions, NOT `X86_*` functions.
```ailang
// WRONG - compile module calling X86 directly
X86_Jmp(label)

// RIGHT - compile module calling IR layer
Emit_JumpToLabel(label, CC.ALWAYS)
```

**If `Emit_*` function doesn't exist:** Add it to `Library.CEmitCore.ailang` as a wrapper.

### 6. Duplicate Functions = Name Mangling Hell
**THE PROBLEM:** Two functions named `Compile_Init` → compiler renames one to `NS9F3VVN_Compile_Init`.

**THE SOLUTION:** 
1. Find duplicates: `grep -rn "^Function.Compile_Init" Librarys/`
2. Rename or delete the redundant one
3. Keep the modern/complete version

### 7. Missing Imports = "Unknown function"
**THE PROBLEM:** `CEmitCore` calling `X86_Jmp` but not importing `CEmitX86Jump`.

**THE SOLUTION:** Add the import:
```ailang
LibraryImport.Compiler.CodeEmit.X86.CEmitX86Jump
```

### 8. Condition Codes - Use CC.ALWAYS not hardcoded values
**CC enum location:** `Library.CEmitTypes.ailang`
```ailang
// Unconditional jump
Emit_JumpToLabel(label, CC.ALWAYS)

// Conditional jumps
Emit_JumpToLabel(label, CC.Z)    // Jump if zero
Emit_JumpToLabel(label, CC.NZ)   // Jump if not zero
Emit_JumpToLabel(label, CC.L)    // Jump if less
Emit_JumpToLabel(label, CC.GE)   // Jump if greater/equal
```

## Quick Fix Commands
```bash
# Find wrong AST function names
grep -rn "AST_GetNodeType\|AST_GetFunctionName\|AST_GetAssignTarget" Librarys/

# Find wrong node type references
grep -rn "NodeType\." Librarys/

# Find duplicate functions
grep -rn "^Function.YourFunctionName" Librarys/

# Check AST node structures
grep -A 10 "Function.AST_Make" Librarys/Compiler/Frontend/AST/Library.CASTNodes.ailang
```

## Bootstrap Process Notes

**Current state:** Python compiler compiles AILANG compiler → generates binary that segfaults.

**Working test:** `test_min.ailang` compiles and runs successfully.

**The goal:** AILANG compiler compiling itself without segfaults.

**Don't forget:** When changing library code, you're changing what gets COMPILED INTO THE BINARY by the Python compiler. Runtime errors = your library code has bugs.

---
*Last updated: December 26, 2025*
*Note: We're all retarded. Read this before you break shit again.*