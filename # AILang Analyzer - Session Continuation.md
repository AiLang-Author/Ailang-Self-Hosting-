# AILang Analyzer - Session Continuation
## January 10, 2026 - Static Analysis Tool Complete (v1.0)

---

## What Was Accomplished

### Self-Contained Analyzer Tool ✅
- **Location:** `Librarys/Library.Analyzer.ailang`
- **Architecture:** Owns its own pipeline (Load → Resolve → Lex → Parse → Walk AST)
- **Integration:** Console commands `analyze <file>` and `analyze` (loaded source)
- **No dependency on compiler state** - completely standalone operation

### Checks Implemented

| Check | Category | Status | Notes |
|-------|----------|--------|-------|
| Memory leak detection | Memory | ✅ | Allocate without Deallocate |
| Return value skip | Memory | ✅ | No warning if allocation returned |
| FixedPool skip | Memory | ✅ | Pool.member allocations ignored (global) |
| Missing ReturnValue | Control | ✅ | Function has Output but no return |
| Unused variable | Variables | ✅ | Assigned but never read |
| Pool member skip | Variables | ✅ | Ignores `Pool.field` assignments |
| Single char skip | Variables | ✅ | Ignores i, j, k (loop counters) |
| Underscore skip | Variables | ✅ | Ignores `_var` (intentional) |
| Undefined function | Functions | ✅ | Called but not defined |
| Unused function | Functions | ✅ | Defined but never called |
| Entry point skip | Functions | ✅ | Ignores Main, Init, Run*, Test* |
| Builtin skip | Functions | ✅ | Ignores Add, PrintMessage, etc. |
| Too many params | Style | ✅ | >6 parameters |
| Deep nesting | Style | ✅ | Block depth >5 |

### Console Integration
```
ailang> analyze <file>     # Analyze specific file
ailang> analyze            # Analyze loaded source
ailang> analyzer verbose   # Show trace during analysis
ailang> analyzer quiet     # Hide trace
```

---

## Outstanding Issues

### Line Numbers Show 0
**Problem:** AST nodes don't have line info populated.

**Root Cause:** Parser uses `AST_Create()` instead of `AST_CreateAt(type, line, col)`.

**Fix Location:** `Librarys/Compiler/Frontend/Parser/` - all Parse_* functions.

**Pattern to fix:**
```ailang
// Current (loses line info):
node = AST_Create(AST.ASSIGNMENT)

// Fixed (preserves line info):
node = AST_CreateAt(AST.ASSIGNMENT, PParser.p_current_line, PParser.p_current_col)
```

**Scope:** ~50-100 places in parser need updating.

### Deallocation Excess Warning
Shows "+18 deallocation excess" - likely due to:
- Deallocate calls that don't have matching in-function Allocate (params, globals)
- This is informational, not necessarily a bug

---

## Architecture Overview

```
Analyzer.AnalyzeFile(filename)
    │
    ├── [1] Load file (direct syscall)
    │
    ├── [2] Import_ResolveAll() - inline all imports
    │
    ├── [3] Lex_Init() + Lex_Tokenize()
    │
    ├── [4] Parse_Init() + Parse_Program() → AST
    │
    ├── [5] Analyzer.Init() + WalkNode(ast) + PostAnalysis()
    │       │
    │       ├── Per-function tracking:
    │       │   - EnterFunction() - clear state, record definition
    │       │   - Track assignments, usages, allocs, deallocs, returns
    │       │   - ExitFunction() - run all per-function checks
    │       │
    │       └── PostAnalysis():
    │           - Check undefined functions (called but not defined)
    │           - Check unused functions (defined but not called)
    │
    ├── [6] Analyzer.Report() - print findings
    │
    └── [7] Cleanup everything
```

---

## How to Add New Checks

### Pattern 1: Per-Function Check (runs at function exit)

Add tracking in `WalkNode`, check in `ExitFunction`:

```ailang
// In Analyzer state:
"func_something": Initialize=0, CanChange=True

// In EnterFunction - reset:
Analyzer.func_something = 0

// In WalkNode - track:
IfCondition EqualTo(node_type, AST.SOMETHING) ThenBlock: {
    Analyzer.func_something = Add(Analyzer.func_something, 1)
}

// In ExitFunction - check:
IfCondition GreaterThan(Analyzer.func_something, threshold) ThenBlock: {
    msg = StringConcat("Too many somethings in '", Analyzer.current_func)
    msg = StringConcat(msg, "'")
    Analyzer.AddWarning(msg)
}
```

### Pattern 2: Global Check (runs after all functions)

Track globally, check in `PostAnalysis`:

```ailang
// In Analyzer state:
"global_list": Initialize=0, CanChange=True

// In Init:
Analyzer.global_list = XArray.XCreate(64)

// In WalkNode - collect:
XArray.XPush(Analyzer.global_list, item)

// In PostAnalysis - analyze:
count = XArray.XSize(Analyzer.global_list)
// ... check for patterns, duplicates, etc.

// In Cleanup:
XArray.XDestroy(Analyzer.global_list)
```

### Pattern 3: AST Node Type Check

```ailang
// In WalkNode, add a new node type handler:
IfCondition EqualTo(node_type, AST.YOUR_NODE) ThenBlock: {
    // Extract data
    data1 = AST_GetData1(node)
    child = AST_GetChild(node, 0)
    
    // Check something
    IfCondition /* bad condition */ ThenBlock: {
        Analyzer.AddWarning("Problem found")
    }
    
    // Continue walking
    Analyzer.WalkChildren(node)
    ReturnValue(0)
}
```

---

## Checks To Add (Priority Order)

### High Priority

| Check | Description | Difficulty |
|-------|-------------|------------|
| **Unreachable code** | Code after ReturnValue/BreakLoop/ExitLoop | Medium |
| **Missing else** | IfCondition without ElseBlock (style) | Easy |
| **Empty block** | Empty Body, ThenBlock, etc. | Easy |
| **Infinite loop** | WhileLoop with no exit condition | Medium |
| **Double assignment** | Variable assigned twice without read between | Medium |

### Medium Priority

| Check | Description | Difficulty |
|-------|-------------|------------|
| **Magic numbers** | Literal numbers that should be constants | Easy |
| **Duplicate strings** | Same string literal repeated | Medium |
| **Long function** | Function > N lines | Easy (need line tracking) |
| **Deep call chain** | A calls B calls C calls D... | Hard |
| **Cyclic calls** | A calls B calls A | Hard |

### Advanced (Future)

| Check | Description | Difficulty |
|-------|-------------|------------|
| **Type inference** | Track what type a variable holds | Hard |
| **Null check** | Use before assignment | Hard |
| **Lifetime tracking** | Cross-function pointer validity | Very Hard |
| **Dead store** | Write then overwrite without read | Medium |

---

## Implementation Notes for Specific Checks

### Unreachable Code
```ailang
// Track "code after return" flag
"saw_return_in_block": Initialize=0, CanChange=True

// In RETURN handler:
Analyzer.saw_return_in_block = 1

// In statement handler after RETURN:
IfCondition EqualTo(Analyzer.saw_return_in_block, 1) ThenBlock: {
    Analyzer.AddWarning("Unreachable code after ReturnValue")
}

// Reset at block exit
```

### Magic Numbers
```ailang
// In NUMBER literal handler:
IfCondition EqualTo(node_type, AST.NUMBER) ThenBlock: {
    value = AST_GetData1(node)
    is_magic = Analyzer.IsMagicNumber(value)
    IfCondition EqualTo(is_magic, 1) ThenBlock: {
        // Track it
    }
}

Function.Analyzer.IsMagicNumber {
    Input: num: Integer
    Output: Integer
    Body: {
        // Allow: 0, 1, -1, 2, 8, 16, 32, 64, 128, 256, etc.
        // Flag: 42, 1337, 86400, etc.
    }
}
```

### Empty Block
```ailang
IfCondition EqualTo(node_type, AST.BLOCK) ThenBlock: {
    child_count = AST_GetChildCount(node)
    IfCondition EqualTo(child_count, 0) ThenBlock: {
        Analyzer.AddWarning("Empty block")
    }
}
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `Librarys/Library.Analyzer.ailang` | Main analyzer implementation |
| `ailang_console.ailang` | Console integration (analyze commands) |
| `Librarys/Compiler/Frontend/AST/Library.CASTTypes.ailang` | AST node type constants |
| `Librarys/Compiler/Frontend/AST/Library.CASTCore.ailang` | AST access functions |
| `Librarys/Compiler/Frontend/Parser/Library.CParser*.ailang` | Parser (fix line numbers here) |

---

## Quick Commands

```bash
# Analyze the compiler itself
./stuff.x
ailang> analyze ailang_console.ailang

# Analyze specific library
ailang> analyze Librarys/Library.Arena.ailang

# Verbose mode (see what's being tracked)
ailang> analyzer verbose
ailang> analyze ailang_console.ailang

# Dump combined source for line reference
ailang> load ailang_console.ailang
ailang> dump
# Creates combined_source.ailang
```

---

## Test the Analyzer On Itself

The analyzer can analyze its own code:
```
ailang> analyze Librarys/Library.Analyzer.ailang
```

Good dogfooding test!

---

*Session: January 10, 2026*
*Status: Analyzer v1.0 complete, ready for enhancement*
*Next: Fix line numbers in parser, add more checks*