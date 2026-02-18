# AILang Support for Visual Studio Code

Full-featured language support for AILang — the self-hosting, explicit-syntax systems programming language.

**Compiler + three-pass static analyzer + LSP + interactive code graph — all in ~500KB. Zero dependencies.**

**Publisher:** 2Paws · **Version:** 1.0.0 · **Requires:** VS Code 1.75+

---

## Getting Started

1. Install the extension from the VS Code Marketplace or load it from a `.vsix` file.
2. Open any `.ailang` file. The extension activates automatically.
3. The AILang icon appears in the Activity Bar on the left — click it to browse documentation.

### Requirements

**Platform:** x86-64 architecture only. The compiler and tools produce native Linux ELF64 binaries.

- **Linux (x86-64):** Works natively. Kernel 2.6.32 or newer (2006+). Uses basic syscalls only — no glibc dependency, no dynamic linking.
- **Windows (x86-64):** Works through WSL. Any WSL distro with an x86-64 userspace. The extension detects Windows automatically and routes all tool execution through WSL — no manual configuration needed.
- **macOS:** Not currently supported (ELF64 binary format, Linux syscall ABI).

**VS Code:** Version 1.75.0 or newer.

**No external dependencies.** The compiler, LSP, and all tools ship pre-compiled inside the extension. No npm packages, no CDN, no network calls, no runtime downloads. Everything is self-contained.

The extension looks for these binaries in your project directory:

| Binary | Purpose |
|--------|---------|
| `ailang.x` | Compiler — compiles `.ailang` to native x86-64 ELF executables |
| `ailang_lsp.x` | Language server — powers diagnostics, completions, symbols, and the connectome |

If your binaries are elsewhere, set the paths in Settings (see Configuration below).

---

## Features

### Syntax Highlighting

Full TextMate grammar for `.ailang` files, covering all keywords, pool types, builtins, control flow, string literals, numbers (decimal, hex, octal, binary), and comments.

### Compile and Run

Compile and run AILang programs directly from the editor.

| Command | Shortcut | What it does |
|---------|----------|--------------|
| **AILang: Compile File** | `Ctrl+Shift+B` | Compiles the current file to a `.x` executable |
| **AILang: Run File** | `F5` | Compiles and immediately runs the program |
| **AILang: Analyze File** | `Ctrl+Shift+A` | Runs static analysis and reports issues in the Problems panel |

A ▶ Run button also appears in the editor title bar for any `.ailang` file, and a CodeLens "Run" link appears above any `SubRoutine.Main` definition.

### Real-Time Diagnostics

The LSP runs three analysis passes automatically when you open or save an `.ailang` file:

- **Pass 1 (MEM)** — Memory lifecycle: leaks, double-free, use-after-free, unused variables
- **Pass 2 (CFG)** — Control flow: null dereference, unreachable code, infinite loops, missing else branches
- **Pass 3 (DFA)** — Data flow: read-before-write, variable shadowing, arena allocation in loops, recursion detection

Errors and warnings appear inline in the editor and in the Problems panel. Diagnostics are routed to the correct file with accurate line numbers, even across imported modules. No manual step required.

### IntelliSense and Completions

Start typing and the extension offers:

- **All AILang keywords** — `IfCondition`, `WhileLoop`, `FixedPool`, `Function`, etc.
- **All builtin functions** — `Add`, `Subtract`, `PrintMessage`, `Allocate`, `StringConcat`, and 100+ more.
- **File symbols** — functions, subroutines, pools, fields, imports, and variables from the current file, pulled from the LSP. File symbols sort first so your own code appears at the top.
- **Scope-aware detail** — each completion item shows its kind and parent scope (e.g., `Field (in MyPool)`).

Completions trigger on typing and also on `.` (for pool member access) and `@` (for pointer field access).

### Shorthand Aliases

Type abbreviated forms and the extension expands them to canonical AILang on accept. Disk files always contain the full canonical form — shorthands are purely an input accelerator.

**Examples:**

| You Type | Inserts |
|----------|---------|
| `GT` | `GreaterThan` |
| `LT` | `LessThan` |
| `EQ` | `EqualTo` |
| `NE` | `NotEqual` |
| `FN` | `Function` |
| `SR` | `SubRoutine` |
| `IC` | `IfCondition` |
| `RV` | `ReturnValue` |
| `LP` | `LinkagePool` |
| `FP` | `FixedPool` |
| `DP` | `DynamicPool` |
| `ALLOC` | `Allocate` |
| `PM` | `PrintMessage` |
| `SCAT` | `StringConcat` |
| `BA` | `BitwiseAnd` |

Over 60 aliases are built in. When browsing the completion list, keywords and builtins show their shorthand in the detail line (e.g., `GreaterThan` shows `Shorthand: GT`).

**Format-on-save safety net:** If a shorthand somehow survives into your source (pasted code, skipped completion), it's automatically expanded to canonical form on save. String literals and comments are left untouched.

### Scaffold Templates

Type a keyword followed by `.` and accept the completion to insert a full skeleton with tab stops.

| You Type | Scaffold |
|----------|----------|
| `Function.` | Function with Input, Output, Body, ReturnValue |
| `SubRoutine.` | SubRoutine with Input, Body |
| `Combinator.` | Combinator with Input, Output, Body, Where |
| `Lambda.` | Lambda with Input, Output, Body |
| `FixedPool.` | FixedPool with fields |
| `DynamicPool.` | DynamicPool with fields |
| `LinkagePool.` | LinkagePool with fields |
| `ConstrainedPool.` | ConstrainedPool with fields and Where clause |
| `IfCondition.` | If/Then/Else block |
| `WhileLoop.` | While loop |
| `ForEvery.` | For-each loop |
| `ChoosePath.` | Switch/case with CaseOption and DefaultOption |
| `TryBlock.` | Try/Catch/Finally |
| `LoopMain.` | Main event loop |
| `LoopActor.` | Actor event loop |
| `LibraryImport.` | Import statement |
| `AcronymDefinitions.` | Acronym definition block |

Scaffolds also work with shorthands — `FN.` expands to the full Function skeleton.

Press `Tab` to jump between placeholders and fill in names, types, and logic.

### Symbol Outline

The editor's Outline view (sidebar) shows all symbols in the current file organized hierarchically — functions contain their parameters, pools contain their fields. Powered by the LSP, so it's always up to date.

### Go to Definition

`F12` or `Ctrl+Click` on any symbol jumps to its definition within the file.

### Hover Information

Hover over any symbol to see its kind, scope, line number, and — for functions — parameters, return type, and call graph (who calls it, what it calls). Pool hovers show their fields.

### Connectome — Interactive Code Graph

Open the connectome with `Ctrl+Shift+P` → **AILang: Show Flow Graph** (or the command palette).

A force-directed, interactive graph opens in a side panel showing the structure of your code:

**Nodes** represent symbols, colored by type:
- 🔴 Red — Imports
- 🔵 Blue — Pools (Fixed, Dynamic, Linkage, etc.)
- 🟣 Purple — Functions, Combinators, Lambdas
- 🟠 Orange — SubRoutines
- 🟢 Green — Loops

**Edges** show relationships:
- Solid arrows — call graph (function A calls function B)
- Dashed lines — scope containment (field belongs to pool)

**Interactions:**
- **Pan** — drag the background
- **Zoom** — scroll wheel
- **Drag nodes** — rearrange the layout
- **Hover** — tooltip with kind, connections, scope
- **Click** — opens a detail panel showing calls out, called by, and contained children. Every connection in the panel is clickable and pans the camera to that node.
- **Double-click** — jumps to that symbol's line in the editor
- **"Open File" button** — appears on Import nodes. Click it to open the imported `.ailang` source file.

**Filtering:**
- Top bar has toggle buttons for each symbol group (Imports, Pools, Functions, SubRoutines, Loops). Click to show/hide.
- Search box filters nodes by name or kind in real time.
- When a node is selected, unconnected nodes dim so the subgraph stands out.

The connectome auto-refreshes on save and on text changes (debounced) — no need to close and reopen it.

Runs entirely self-contained inside the VS Code webview. No CDN, no external scripts, no network calls.

### Documentation Sidebar

Click the AILang icon in the Activity Bar to open the documentation browser. It lists all `.md` files in the extension's `docs/` folder. Click any manual to open it in VS Code's Markdown preview.

**Recommended reading order:**
1. `Programming Intro to Ailang.md` — start here
2. `AILANG Quick Syntax Reference.md` — cheat sheet
3. `Basic Flow Control Guide.md` — control flow patterns
4. `Memory Management Reference Manual.md` — Allocate, Deallocate, pointers
5. `BNF grammar.md` — formal language spec

---

## Commands

All commands are available through the Command Palette (`Ctrl+Shift+P`):

| Command | Shortcut | Description |
|---------|----------|-------------|
| `AILang: Compile File` | `Ctrl+Shift+B` | Compile current file to `.x` |
| `AILang: Run File` | `F5` | Compile and run |
| `AILang: Analyze File` | `Ctrl+Shift+A` | Run static analysis |
| `AILang: Show Flow Graph` | — | Open interactive connectome |
| `AILang: Open Documentation` | — | Browse manuals |

---

## Configuration

Open VS Code Settings and search for "AILang" to configure paths:

| Setting | Default | Description |
|---------|---------|-------------|
| `ailang.compilerPath` | `./ailang.x` | Path to the compiler binary |
| `ailang.lspPath` | `./ailang_lsp.x` | Path to the LSP binary |
| `ailang.analyzerPath` | `./analyzer.x` | Path to the static analyzer |
| `ailang.frontendPath` | `./frontend.x` | Path to the frontend tool |
| `ailang.defaultOutputDir` | `.` | Output directory for compiled binaries |

Relative paths (starting with `./`) are resolved relative to the workspace folder, or the document's directory if no workspace is open.

---

## Windows + WSL

AILang compiles to Linux ELF64 binaries. On Windows, the extension runs all tools through WSL transparently:

- Paths are converted automatically (`C:\Users\Sean\project\` → `/mnt/c/Users/Sean/project/`)
- Compile, run, analyze, and LSP commands all execute inside WSL
- No manual WSL configuration needed — just have WSL installed with a default distribution

---

## File Associations

The extension registers `.ailang` as a recognized file type. Opening any `.ailang` file activates syntax highlighting, diagnostics, completions, and all other features automatically.

---

## Troubleshooting

**"No Symbols Found" in the connectome**
The LSP binary isn't being found. Check `ailang.lspPath` in settings, or place `ailang_lsp.x` in the same directory as your `.ailang` files.

**Diagnostics not appearing**
Make sure the LSP binary exists and is executable. On WSL, the extension runs `chmod +x` automatically, but if the binary is on an NTFS drive the permissions might not stick — try copying it to the WSL filesystem.

**Compile/Run terminal opens but nothing happens**
Check that `ailang.x` (the compiler) exists at the configured path. The terminal runs inside WSL on Windows, so paths need to be accessible from the Linux side.

**Completions don't show file symbols**
File symbols come from the LSP cache, which populates on open and save. Try saving the file once to trigger the LSP, or run `AILang: Analyze File`.

---

## About AILang

AILang is a self-hosting systems programming language designed around radical explicitness. Every operation is a named function call — no operator precedence, no implicit behavior, no hidden control flow. The language is designed so that source code reads unambiguously by humans and machines alike.

The compiler is written in AILang itself — 43,000+ lines across 75 files, achieving byte-identical self-hosting in 43 days. It compiles AILang source to native x86-64 Linux executables through a pipeline of lexing, parsing, AST construction, compilation, x86 code emission, and ELF64 binary output.

For more information, see the [GitHub repository](https://github.com/AiLang-Author/Ailang-Self-Hosting-).

---

## License

This extension uses a **dual license** structure:

**VS Code extension** (extension.js, package.json, TextMate grammar, snippets, documentation) — [MIT License](LICENSE). Free to use, modify, and redistribute.

**AILang compiler and tools** (ailang.x, ailang_lsp.x, and all AILang source code) — [Sean Collins Software License (SCSL)](LICENSE-COMPILER.md). Free for personal and academic use. Commercial use requires a paid license. Forking and redistribution of source code is not permitted.

Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.