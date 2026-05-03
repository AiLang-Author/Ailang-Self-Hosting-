# AILang Compiler — 06: Import Resolution System

## Overview

The import resolver processes `LibraryImport` directives in source files, loads referenced library modules, detects symbol name conflicts, and generates unique prefixes for conflicting symbols. The system is designed to minimize name mangling — only symbols that actually conflict get prefixed.

```
Source AST (with LibraryImport nodes)
    │
    ▼
Import_Init() → scan imports
    │
    ▼
Import_ResolveAll()
    │
    ├─ Phase 1: Load all imported files
    │     Recursively resolve LibraryImport statements
    │     Parse loaded files into ASTs
    │     Record all symbols per module
    │
    ├─ Phase 2: Detect conflicts
    │     Import_DetectConflicts()
    │     For each symbol, check if defined in multiple modules
    │
    ├─ Phase 3: Assign prefixes
    │     Import_AssignPrefixes()
    │     Generate NSxx_ prefix only for modules with conflicts
    │
    ├─ Phase 4: Build rewrite map
    │     Import_BuildRewriteMap()
    │     Map: (symbol, module) → prefixed_name
    │
    └─ Phase 5: Rewrite AST
          Replace symbol references with prefixed versions
```

---

## 1. FILE MAP

```
Import/
├── CAutoImport.ailang       (18KB) — automatic import discovery
├── CCoreRegistry.ailang     (11KB) — core module registry
├── CFileMap.ailang          (8KB)  — source file path mapping
└── CImportResolver.ailang   (60KB) — conflict-prefix resolver (MAIN)
```

---

## 2. IMPORT RESOLVER (CImportResolver, 60KB)

### 2.1 State Structure (80 bytes)
```
[0]:   loaded_paths      - XArray of file path hashes
[8]:   loaded_content    - XArray of file content pointers
[16]:  loaded_names      - XArray of module name pointers
[24]:  symbol_names      - XArray of all symbol names
[32]:  symbol_modules    - XArray of module index for each symbol
[40]:  conflict_symbols  - XArray of symbols that have conflicts
[48]:  module_prefixes   - XArray of prefix per module (0 if no conflicts)
[56]:  prefix_counter    - Counter for generating prefixes
[64]:  error_count
[72]:  lib_base          - "Librarys" string
```

### 2.2 Key Functions

```
Import_Init() → Address
    Allocate 80-byte state structure
    Create XArrays for all fields
    Set prefix_counter=1, lib_base="Librarys"

Import_ResolveAll(ast) → Integer
    MAIN ENTRY POINT
    Walk AST to find all LibraryImport nodes
    For each import: resolve file path, load content, parse, record symbols
    Run conflict detection
    Assign prefixes
    Build rewrite map
    Rewrite AST with prefixed names
    Store state in Import.last_state

Import_RecordSymbol(state, symbol, module_idx) → void
    Push symbol name and module index to tracking arrays

Import_DetectConflicts(state) → void
    For each symbol:
        Check if same symbol exists in different module
        If conflict: add to conflict_symbols array
    Prints conflict count

Import_AssignPrefixes(state) → void
    Initialize module_prefixes with zeros (one per module + 1)
    For each conflicting symbol:
        Find modules that contain it
        Assign NSxx_ prefix to those modules (if not already assigned)
    Non-conflicting modules keep prefix=0

Import_BuildRewriteMap(state) → Address
    Build XArray: [symbol, module_idx, prefixed_name] triplets
    For each conflicting symbol in each module:
        Create prefixed name: prefix + "_" + symbol (e.g., "NS01_MyFunc")
    Return rewrite map

Import_GetPrefixedFor(rewrite_map, symbol, module_idx) → Address
    Look up prefixed name for a symbol
    If symbol is in rewrite map, return prefixed version
    Otherwise return 0 (no rewriting needed)

Import_GenPrefix(state) → Address
    Generate unique prefix: "NS" + base36(counter)
    Counter starts at 1: NS01, NS02, NS03, ...
    Maximum 6 characters: NSxxxxxx
```

### 2.3 String Helpers
```
Import_CopyStr(str) → Address
    Allocate copy of null-terminated string

Import_StrEqual(a, b) → Integer
    Wrapper for StringCompare returning 0/1

Import_HashString(str) → Integer
    DJB2 hash (hash*33 + c) for path deduplication

Import_BuildPrefixed(prefix, symbol) → Address
    Concatenate: prefix + "_" + symbol
    e.g., BuildPrefixed("NS01", "MyFunc") → "NS01_MyFunc"
```

### 2.4 Symbol Type Detection
```
Import_GetSymbolType(source, start, len) → Integer
    Check prefix to determine declaration type:
    "Function."     → 1
    "SubRoutine."   → 2
    "FixedPool."    → 3
    "DynamicPool."  → 4
    "TemporalPool." → 5
    "NeuralPool."   → 6
    "KernelPool."   → 7
    "ActorPool."    → 8
    "SecurityPool." → 9
    "ConstrainedPool." → 10
    "FilePool."     → 11
    "LinkagePool."  → 12
    (none matched)  → 0

Import_MatchPrefix(source, start, pattern) → Integer
    Compare pattern against source at start position
    Returns 1 if matches
```

### 2.5 Import Path Resolution
```
Library path resolution follows this pattern:
    LibraryImport.Compiler.Frontend.AST.CASTTypes
        │
        ▼
    Look up: Librarys/Compiler/Frontend/AST/Library.CASTTypes.ailang
    Hash path for deduplication
    Load source: ReadTextFile(path)
    Parse: Lex → Tokenize → Parse_Program
    Merge AST into current program
```

---

## 3. CAUTOIMPORT — Automatic Import Discovery (18KB)

Discovers and imports commonly used library modules automatically:
- XArrays (always needed for dynamic arrays)
- Core language runtime functions
- Standard library modules referenced but not explicitly imported

### Pattern:
```
CAutoImport_Scan(ast) → void
    Walk AST for function calls
    Check if function references a known library symbol
    If not already imported, add LibraryImport node
```

---

## 4. CCOREREGISTRY — Core Module Registry (11KB)

Maps standard library module names to file paths:
```
"XArrays" → "Librarys/XArrays/Library.XArrays.ailang"
"Arena" → "Librarys/Arena/Library.Arena.ailang"
...
```

Also tracks dependencies between modules (e.g., CCompileMain depends on CCompileScope, which depends on XArrays).

---

## 5. CFILEMAP — Source File Path Mapping (8KB)

Maps `LibraryImport` dotted paths to filesystem paths:
```
LibraryImport.Compiler.Frontend.AST.CASTTypes
    → Librarys/Compiler/Frontend/AST/Library.CASTTypes.ailang

LibraryImport.XArrays
    → Librarys/XArrays/Library.XArrays.ailang
```

Handles:
- Module name → file path resolution
- Path deduplication (same file imported twice → loaded once)
- Recursive import chains
- Circular import detection

---

## 6. CONFLICT PREFIXING EXAMPLE

```
File A imports: XArrays → symbol "XCreate"
File B imports: MyArray → symbol "XCreate"
Both define "XCreate" → CONFLICT!

Resolution:
    module 0 (self):  prefix=0 (no prefix)
    module 1 (XArrays): prefix=0 (no conflict — only one version)
    module 2 (MyArray): prefix="NS01" (conflict with XArrays)

Rewrites:
    All calls to "XCreate" from MyArray → "NS01_XCreate"
    All calls to "XCreate" from XArrays → "XCreate" (unchanged)
```

---

*Document 06 of 10 — Import Resolution System*
