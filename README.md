# AILang

<p align="center">
  <img src="https://img.shields.io/badge/status-SELF--HOSTING-brightgreen?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/version-1.0.0--beta-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/platform-Linux%20x86__64-blue?style=for-the-badge" alt="Platform">
  <img src="https://img.shields.io/badge/license-SCSL-orange?style=for-the-badge" alt="License">
</p>

<p align="center"><strong>Where every operation states its intent.</strong></p>

---

## 🚀 1.0.0 Beta — VS Code Extension Release

**The compiler now ships inside the VS Code extension. No separate downloads. No PATH configuration. Install the extension, open a `.ailang` file, and everything works.**

### What's in the box

The extension bundles the complete self-hosting compiler toolchain:

- **Compiler** (`ailang.x`) — builds native Linux ELF64 executables
- **LSP** (`ailang_lsp.x`) — powers all IDE features with multi-file analysis
- **Three-pass static analyzer** — memory safety, control flow, data flow analysis
- **Interactive code graph** — force-directed connectome visualization

### Requirements

| Requirement | Details |
|---|---|
| **VS Code** | 1.75 or later |
| **Windows** | WSL (Windows Subsystem for Linux) must be installed with a default distribution |
| **Linux** | Native — works directly, no extra setup |
| **Architecture** | x86-64 only — the compiler produces Linux ELF64 binaries |
| **macOS** | Not currently supported |

> **Windows users:** The extension handles WSL path translation automatically. All compilation, analysis, and LSP operations run transparently inside WSL. Just have WSL installed — no manual configuration needed.

### Install

Download the `.vsix` from the [Releases](https://github.com/AiLang-Author/Ailang-Self-Hosting-/releases) page, then:

```
Ctrl+Shift+P → "Extensions: Install from VSIX..." → select the .vsix file
```

Or from the command line:

```bash
code --install-extension ailang-support-beta-1.0.0.vsix
```

### IDE Features

| Feature | Description |
|---|---|
| **Syntax Highlighting** | Full grammar coverage — pools, functions, control flow, operators, strings |
| **Autocomplete** | Keywords, builtins, shorthand aliases, and symbols from the current file |
| **Diagnostics** | Real-time error and warning reporting in the Problems panel |
| **Multi-file Analysis** | Import resolution — tracks issues across all imported modules |
| **Symbol Outline** | Hierarchical view of functions, pools, fields, imports |
| **Go to Definition** | `F12` / `Ctrl+Click` — works within files and across imports |
| **Connectome** | Interactive force-directed code graph with call relationships |
| **Snippets** | Scaffolding for functions, pools, control flow, loops |
| **Code Lens** | Run button appears above Main subroutines |
| **Shorthand Expansion** | Type abbreviations, they expand to full keywords on save |
| **Documentation Sidebar** | Built-in language manuals accessible from the activity bar |
| **Compile** | `Ctrl+Shift+B` — compiles to native executable |
| **Run** | `F5` — compile and run in integrated terminal |
| **Analyze** | `Ctrl+Shift+A` — run static analysis |

### Static Analysis

The LSP runs three analysis passes on every save:

- **Pass 1 (MEM)** — Memory lifecycle: leaks, double-free, use-after-free, unused variables
- **Pass 2 (CFG)** — Control flow: null dereference, unreachable code, infinite loops, missing else branches
- **Pass 3 (DFA)** — Data flow: read-before-write, variable shadowing, arena allocation in loops, recursion detection

All diagnostics are routed to the correct file with accurate line numbers, even across imported modules.

### 👁️ Semantic Shorthand Display Mode

AILang promotes explicit, readable canonical code (e.g., `IfCondition`, `ThenBlock`, `Function`). However, we know that typing and reading verbose keywords can slow you down if you are used to C-style languages. 

The **Semantic Shorthand Display Mode** solves this by letting you read and write using standard conventions, while keeping the saved file strictly canonical.

#### Features
* **1-Click Toggle**: Turn it on or off instantly using the `👁 AILang: SHORTHAND ON/OFF` button in the VS Code Status Bar (bottom right) or via the Command Palette.
* **Zero-Width Collapse**: When enabled, the verbose canonical text completely vanishes and is replaced by standard syntax highlights. 
* **Standard Control Flow**: Read your AILang code using familiar constructs:
  * `IfCondition` → `IF`
  * `ThenBlock` → `THEN`
  * `ElseBlock` → `ELSE`
  * `WhileLoop` → `WHILE`
  * `ForEvery` → `FOR`
  * `Branch` → `Branch` << this is a AILANG exclusive flow control design
  * `Fork` → `Fork` << this is a AILANG exclusive flow control design
  * And More, current plugin is not 100% in sync with syntax, when in doubt disable shorthand and check programming manuals. 

#### Format-on-Save Expansion
You don't even have to type the long versions! Type the shorthand (like `IF` or `FN`), and when you save your file (`Ctrl+S`), the extension will automatically expand it back to its canonical form (e.g., `IfCondition` or `Function`) to ensure your code complies with the AILang compiler, while keeping the visual shorthand perfectly intact in your editor.

#### Customization
Want to map a specific keyword differently? You can override the default shorthands in your VS Code `settings.json`:
```json
{
  "ailang.editor.shorthandCustomMap": {
    "Function": "func",
    "StringSubstring": "sub"
  }
}
```

---

## Compiler.x — Self-Hosting Achieved

**43,000+ lines. 75+ files. ~300 primitives. 43 days.**

```
Python Bootstrap → compiler.x → compiler2.x → compiler3.x ═══ compiler4.x
                                                    │              │
                                                    └──────────────┘
                                                       BYTE-IDENTICAL
```

The compiler builds itself across generations and produces byte-identical binaries — the definition of a fixed-point self-hosting compiler.

---

## Design Philosophy

### Inspirations

**COBOL** — Self-documenting verbosity. Programs from 1965 still run because the code says what it does.

**Ada** — Rigorous contracts. Strictness prevents bugs. AILang wants Ada's discipline without the tooling pain.

**Forth** — Direct hardware access, minimal runtime. Systems-level control without abstraction theater.

The goal: COBOL's clarity + Ada's rigor + Forth's directness.

### Core Principle: Comprehension Over Convenience

Code is read 10x more than it's written. AILang optimizes for the reader.

### The Problem with Implicit Languages

C's operator precedence was copied from B without questioning if it made sense. C++ layered templates and implicit conversions on top. The result: code that hides behavior.

```c
result = a << 2 + b * c & mask;  // What's the order? Most get it wrong.
```

**AILang rejects implicit behavior.**

---

## Side-by-Side: AILang vs C vs Python

**Ambiguous math:**
```c
// C: What does this mean?
result = a << 2 + b * c & mask;

// AILang: Explicit nesting IS the precedence
result = BitwiseAnd(LeftShift(a, Add(2, Multiply(b, c))), mask)
```

**Hidden dependencies:**
```python
# Python: Where do counter and scale come from?
def process():
    return counter * scale

# AILang: Dependencies are parameters
Function.Process {
    Input: counter: Integer
    Input: scale: Integer
    Output: Integer
    Body: { ReturnValue(Multiply(counter, scale)) }
}
```

**Dangling else:**
```c
// C: Is doSomethingElse() in the if? Indentation lies.
if (x > 0)
    doSomething();
    doSomethingElse();

// AILang: Braces mandatory, structure enforced
IfCondition GreaterThan(x, 0) ThenBlock: {
    DoSomething()
    DoSomethingElse()
}
```

---

## Key Design Decisions

### Named Operators
The nesting IS the precedence. You can't get it wrong.

### Scientific Infix Math
For math-heavy code, AILang supports infix inside parentheses — scientific notation, not C notation:
```ailang
velocity = ((initial_v * t) + (0.5 * a * (t ^ 2)))  // Infix when math IS the point
distance = Add(Multiply(initial_v, t), ...)           // Named when clarity matters
```
Both compile identically. Choose based on context.

### No Global Variables
All state lives in pools (FixedPool, DynamicPool, LinkagePool) or function locals. Dependencies are always explicit.

### LinkagePool: Structured Memory with the @ Operator
```c
// C: Manual everything, cast soup, lifetime chaos
Customer* c = (Customer*)malloc(sizeof(Customer));
c->name = strdup("Alice");
free(c->name);  // Did we remember?
free(c);        // Double-free?
```

```ailang
// AILang: Semantic structure, type-safe @ access
LinkagePool.Customer {
    "name": Initialize=0
    "balance": Initialize=0
    "account": Initialize=0, PointerTo=LinkagePool.Account
}

customer = AllocateLinkage(LinkagePool.Customer)
customer@name = "Alice"
customer@balance = 100
customer@account@routing = 12345   // Chained access — compiler tracks types
FreeLinkage(customer, LinkagePool.Customer)
```

**Why `@` instead of dot?** The dot is overloaded (`FixedPool.X.field`, `Library.Module`, `LinkagePool.Type`). The `@` operator is unambiguous, grep-friendly (`grep "@"` finds all dereferences), and self-documenting ("at this address").

**Type propagation:** `PointerTo=` lets the compiler track types through pointer chains. `customer@account@routing` works because the compiler knows `account` points to a `LinkagePool.Account`.

Influenced by COBOL's LINKAGE SECTION — data structures with clear contracts.

### Functions vs Subroutines
**Functions** — Computation with contracts (Input/Output/Body). Stack-based locals. Unit of reasoning.

**Subroutines** — Imperative coordination. Shared state via pools. About *doing*, not computing.

### Formal Grammar
AILang has a complete BNF specification — not informal docs, but a real grammar definition covering all constructs: pools, functions, control flow, expressions, operators, and the 50+ math/bit primitives. The parser implements this grammar directly.

### Import System
```ailang
// Library imports — pull from Librarys/ directory
LibraryImport.JSON
LibraryImport.Compiler.Frontend.Lexer.CLexerMain

// Local imports — pull from the same folder as your file
Import.Utils
Import.GameLogic
Import.Renderer
```
No headers. No forward declarations. No include guards. Conflict resolution at import time.

**Two forms:** `LibraryImport` resolves from the `Librarys/` directory tree. `Import` resolves from the current file's directory — perfect for splitting large programs into manageable pieces. Create a folder, split your code across files, and `Import.FileName` pulls them in. This also makes AI-assisted development easier: hand an LLM one file at a time instead of a 3,000-line monolith.

### Primitives vs Libraries

**Primitives (in compiler):** ~300 built-in operations you'd otherwise rewrite in every project:
- 22+ string operations (`StringConcat`, `StringLength`, `StringCompare`, `StringToUpper`...)
- Memory operations (`Allocate`, `Deallocate`, `MemoryCopy`, `GetByte`, `SetByte`...)
- Math operations (`Add`, `Multiply`, `Power`, `SquareRoot`, `Sin`, `Cos`...)
- File I/O (`ReadTextFile`, `WriteTextFile`, `FileExists`...)
- Bitwise operations (`BitwiseAnd`, `LeftShift`, `RightShift`...)

**Libraries (opt-in):** Complex abstractions that not everyone needs — `Library.OOP`, `Library.HashMap`, `Library.JSON`, `Library.SQL`, `Library.PostgreSQL`.

You don't pay for OOP if you don't use it, but you never have to write `StringConcat` yourself.

---

## The Compiler

A complete development environment:

- **Console** — Interactive REPL, load/parse/compile/run from one interface
- **Built-in Editor** — Nano-style with syntax highlighting
- **Static Analysis** — Three-pass analyzer: memory, control flow, data flow
- **Debug Primitives** — Zero overhead in production:

```ailang
DebugAssert(GreaterThan(balance, 0), "Balance must be positive")
Debug("trace", level=2) { PrintMessage("Entering critical section\n") }
```
At `-D0`, these compile to NOPs. Full functionality at higher debug levels.

### Multi-Architecture Design
Built for multiple backends from day one:
```
CodeEmit/
├── CEmitCore.ailang       # Architecture-agnostic
├── X86/                   # x86-64 (complete)
└── RISCV/                 # Future target
```
Adding architectures means implementing backend functions — compiler logic stays unchanged.

---

## Compiler Capabilities

### Fully Working

| Category | Features |
|----------|----------|
| **Arithmetic** | Add, Subtract, Multiply, Divide, Modulo, Power, Negate, Increment, Decrement |
| **Comparisons** | EqualTo, NotEqual, LessThan, GreaterThan, LessEqual, GreaterEqual |
| **Logical** | And, Or, Not |
| **Bitwise** | BitwiseAnd, BitwiseOr, BitwiseXor, BitwiseNot, LeftShift, RightShift |
| **I/O** | PrintMessage, PrintNumber, PrintChar, PrintString |
| **Strings** | StringLength, StringCompare, StringEquals, StringCopy, StringConcat |
| **Arrays** | ArrayCreate, ArrayGet, ArraySet, ArrayLength, ArrayDestroy |
| **Dynamic Arrays** | XArray.XCreate, XPush, XGet, XSet, XSize, XDestroy |
| **Memory** | Allocate, Deallocate, StoreValue, Dereference, GetByte, SetByte, MemoryCopy, MemorySet |
| **LinkagePool** | AllocateLinkage, FreeLinkage, `@` field access, PointerTo chaining, Type embedding |
| **Control Flow** | IfCondition/ThenBlock/ElseBlock, WhileLoop, ForEach, ExitLoop, ContinueLoop, Branch/Case |
| **Functions** | Function/SubRoutine definitions, parameters (6 registers), locals, nested calls, ReturnValue |
| **File I/O** | WriteTextFile, ReadTextFile, FileExists, GetFileSize |
| **Import System** | Multi-file compilation, library imports, symbol conflict detection |
| **Code Generation** | x86-64 native instructions, ELF64 executables, data relocations |

---

## Quick Start

### Using the VS Code Extension (Recommended)

1. Install the `.vsix` (see Install section above)
2. Open any `.ailang` file — syntax highlighting and diagnostics activate automatically
3. `F5` to compile and run
4. `Ctrl+Shift+A` to run static analysis
5. `Ctrl+Shift+P` → "AILang: Show Flow Graph" for the interactive connectome

### From the Command Line

```bash
git clone https://github.com/AiLang-Author/Ailang-Self-Hosting-.git
cd Ailang-Self-Hosting-

# The compiler builds itself
./compiler.x
ailang> load ailang_console.ailang
ailang> build compiler2.x
ailang> quit

# Verify self-hosting (should produce identical binary)
./compiler2.x
ailang> load ailang_console.ailang
ailang> build compiler3.x
ailang> quit

cmp compiler2.x compiler3.x  # No output = identical!
```

### Compile a Program

```bash
./compiler.x
ailang> load myprogram.ailang
ailang> build myprogram.x
ailang> quit

./myprogram.x
```

### Hello World
```ailang
SubRoutine.Main {
    PrintMessage("Hello, World!\n")
}
RunTask(Main)
```

---

## Language Examples

### Functions with Contracts
```ailang
Function.Factorial {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessEqual(n, 1) ThenBlock: {
            ReturnValue(1)
        }
        result = Multiply(n, Factorial(Subtract(n, 1)))
        ReturnValue(result)
    }
}
```

### Multi-File Projects
```ailang
// Split a big program across files in the same folder:
//   myproject/
//     main.ailang        ← this file
//     Utils.ailang
//     GameLogic.ailang
//     Renderer.ailang

Import.Utils
Import.GameLogic
Import.Renderer

// Or pull shared libraries from Librarys/
LibraryImport.JSON
LibraryImport.HashMap

SubRoutine.Main {
    data = JSON.Parse(ReadTextFile("config.json"))
    GameLogic_Init(data)
    Renderer_Start()
}
RunTask(Main)
```

### Memory Management
```ailang
buffer = Allocate(1024)
SetByte(buffer, 0, 65)      // Write 'A'
char = GetByte(buffer, 0)   // Read back
Deallocate(buffer, 1024)
```

### LinkagePool with @ Operator
```ailang
LinkagePool.Node {
    "value": Initialize=0
    "next": Initialize=0, PointerTo=LinkagePool.Node
}

node = AllocateLinkage(LinkagePool.Node)
node@value = 42
node@next = AllocateLinkage(LinkagePool.Node)
node@next@value = 100    // Chained access works!
```

---

## The Self-Hosting Story

**Dec 15, 2025 → Jan 27, 2026. 43 days.**

**What this proves:**
1. **Expressiveness** — Lexing, parsing, AST, code generation, symbol tables, scope management — all in AILang
2. **AI collaboration velocity** — Clear syntax means AI suggestions are correct more often. Structure catches bugs earlier
3. **Verbosity ≠ bloat** — Deep primitives reduce glue code. Structure reduces error handling

**Compare to TCC (Tiny C Compiler):** TCC needs ~100,000 lines of C for ANSI C89/C99. AILang needs ~43,000 lines for ~300 primitives PLUS integrated tooling.

### Subsystem Breakdown

| Subsystem | Lines | Files |
|-----------|-------|-------|
| Frontend | 8,827 | 18 |
| Compile | 14,447 | 29 |
| CodeEmit | 10,162 | 15 |
| Import | 2,601 | 3 |
| Output | 1,111 | 3 |
| Debug | 1,016 | 3 |
| Console | 1,653 | 1 |
| Core Libs | 3,232 | 3 |
| **Total** | **~43,000** | **75** |

---

## Why These Choices Matter

| Decision | Problem | Benefit |
|----------|---------|---------|
| Named operators | Precedence bugs | Unambiguous by construction |
| Scientific infix | Math readability | Domain experts read domain code |
| No globals | Hidden dependencies | All state flows explicit |
| LinkagePool | Pointer ambiguity | `@` operator — unambiguous, grep-friendly |
| PointerTo= | Lost type info | Compiler tracks types through chains |
| Primitives vs Libs | Boilerplate vs bloat | 300 built-ins, OOP optional |
| Functions vs Subroutines | Confused intent | Computation vs coordination |
| Library imports | Header hell | No redundancy, no circular deps |
| Built-in debug | Tooling fragmentation | Zero-overhead, always available |
| Multi-arch design | Platform lock-in | Add targets, keep logic |
| Formal BNF grammar | Informal specs | Parser matches spec exactly |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       SOURCE CODE                            │
│                    (*.ailang files)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND                                                    │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │ Lexer   │───▶│ Parser  │───▶│   AST   │                  │
│  │(CLexer) │    │(CParser)│    │         │                  │
│  └─────────┘    └─────────┘    └─────────┘                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  COMPILER (CCompile* modules)                                │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │  Arith   │ Compare  │   I/O    │  String  │  Memory  │   │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┤   │
│  │  Logic   │ Bitwise  │  Stmt    │  Func    │  Array   │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  CODE EMITTER (CEmitX86*)                                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │   Reg    │   Mem    │  Stack   │  Arith   │   Jump   │   │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┤   │
│  │   Cmp    │  Logic   │  String  │   Sys    │  Macros  │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              ELF64 Builder (CELFBuilder)            │    │
│  │     Native Linux x86-64 Executable (.x files)       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
AILangSH/
├── ailang_console.ailang      # Self-hosting compiler source
├── compiler.x                 # Compiled self-hosting compiler
├── ailang_lsp.ailang          # LSP server source (also self-hosting)
│
├── Librarys/
│   ├── Compiler/
│   │   ├── Frontend/
│   │   │   ├── Lexer/         # CLexer — tokenization
│   │   │   ├── Parser/        # CParser — AST generation
│   │   │   └── AST/           # AST types and operations
│   │   ├── Compile/
│   │   │   └── Modules/       # CCompile* — compilation
│   │   ├── CodeEmit/
│   │   │   └── X86/           # CEmitX86* — x86-64 code gen
│   │   ├── Import/            # Import resolution + FileMap
│   │   └── Output/            # ELF builder
│   │
│   ├── Library.XArrays.ailang # Dynamic arrays
│   ├── Library.JSON.ailang    # JSON serialization
│   ├── Library.OOP.ailang     # Optional OOP support
│   └── Library.HashMap.ailang # Hash tables
│
├── vscode-extension/          # VS Code extension source
│   ├── extension.js           # Extension logic
│   ├── package.json           # Extension manifest
│   └── resources/             # Icons
│
└── TestCode/                  # Test programs
```

---

## What AILang Is For

- Systems programming with memory/hardware control
- Code that must be obviously correct by inspection
- Long-lived codebases where maintenance dominates
- AI-assisted development (explicit structure = better suggestions)
- COBOL modernization preserving semantic clarity

**Not for:** Quick scripts, C/C++ interop, code golf.

---

## Roadmap

- [x] Self-hosting compiler (byte-identical across generations)
- [x] Hex/octal/binary literals
- [x] Float support (SSE)
- [x] Three-pass static analysis (MEM/CFG/DFA)
- [x] VS Code extension with bundled toolchain
- [x] Multi-file import resolution in LSP
- [x] Interactive connectome visualization
- [ ] RISC-V backend
- [ ] Multi-platform support
- [ ] Debug stepping integration

---

## License

**Sean Collins Software License (SCSL)**

Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.

See [LICENSE](LICENSE) for full terms.

---

<p align="center">
  <strong>AILang: Written in itself. Compiling itself. Analyzing itself.</strong>
</p>
