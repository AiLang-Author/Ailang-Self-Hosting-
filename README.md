# AILang Self-Hosting Repository

Welcome to the **AILang Programming Language** — a self-hosted compiler and runtime system with a verb-first syntax paradigm for modern language design.

## Overview

This is the official self-hosting repository for **AILang**, featuring:
- **Self-hosted compiler** (`ailang.x`) — compiles AILang to machine code
- **Language server** (`ailang_lsp.ailang`) — IDE support with VS Code integration
- **Comprehensive standard libraries** — display rendering, UI components, and system utilities
- **Full development toolchain** — CLI tools, console, testing harness, and documentation
- **Desktop environment** — display server with window management, taskbar, and UI framework
- **26 comprehensive programming manuals** — step-by-step guides for language mastery
- **150+ demo programs** — real-world examples covering all language features

## Quick Start

### Installation

Install the compiler and language server as system-wide symlinks:

```bash
sudo ./install_compiler.sh [install-dir]
```

Default install directory: `/usr/local/bin`

**Note:** The installation uses symlinks, so rebuilds of `ailang.x` and `analyzer.x` are immediately available without re-installation. The library directory (`Librarys/`) is resolved at runtime via `/proc/self/exe`.

To uninstall:
```bash
sudo rm /usr/local/bin/ailang.x /usr/local/bin/analyzer.x
```

## Learning AILang

### 📚 26 Programming Manuals

The `Programming_Manual/` directory contains **26 comprehensive guides** covering:

- **Language Fundamentals** — syntax, types, control flow, functions
- **Memory Management** — allocators, pointers, pools, lifetimes
- **Data Structures** — arrays, hashmaps, linked lists
- **System Programming** — syscalls, file I/O, process management
- **Concurrent Programming** — tasks, message passing, concurrency patterns
- **Graphics & UI** — display rendering, window management, event handling
- **Standard Library Deep Dives** — detailed exploration of each library module
- **Performance Optimization** — profiling, optimization techniques, benchmarking
- **Real-World Patterns** — idiomatic AILang code patterns and best practices

Each manual is structured as a hands-on guide with examples and exercises.

### 🎯 150+ Demo Programs

The `Demo Programs/` directory includes **over 150 runnable examples**:

- **Beginner Programs** — Hello World, basic arithmetic, string operations
- **Control Flow Examples** — conditionals, loops, pattern matching
- **Data Structure Usage** — working with arrays, pools, linked lists
- **Functional Programming** — functions, lambdas, combinators, recursion
- **Systems Programming** — file operations, process management, signals
- **Graphics Programs** — rendering, animation, UI components
- **Game Examples** — simple games demonstrating game loops and state management
- **Concurrency Examples** — tasks, message passing, synchronization
- **Compiler Examples** — parsing, ASTs, code generation
- **Complete Applications** — projects demonstrating full AILang capabilities

### Getting Started Recommendations

1. **Read First:** `Programming_Manual/01_Introduction_to_Ailang.md`
2. **Play With:** Start with demo programs in `Demo Programs/beginner/`
3. **Reference:** Consult manuals as needed for deeper topics
4. **Build:** Create your own programs using examples as templates

## Repository Structure

```
.
├── ailang.x                      # Self-hosted compiler (binary)
├── analyzer.x                    # Code analyzer (binary)
├── Main.ailang                   # Entry point — display server with taskbar
├── ailang_cli.ailang             # Command-line interface
├── ailang_console.ailang         # Interactive REPL console
├── ailang_lsp.ailang             # Language server protocol implementation
├── aimacro_cli.ailang            # AIMacro CLI tool
├── aimacro_console.ailang        # AIMacro REPL
│
├── Librarys/                     # Standard library modules
│   ├── Arena/                    # Memory arena allocator
│   ├── Arrays/                   # Array utilities
│   ├── Display/                  # Display rendering & UI
│   │   ├── Render/              # Graphics, fonts, framebuffer
│   │   ├── UI/                  # Auckland UI framework, dialogs
│   │   ├── Window/              # Window manager & toolbar
│   │   ├── Menu/                # Menu system & deskbar
│   │   ├── Content/             # HTML parsing, documents, pages
│   │   ├── Input/               # Cursor & input handling
│   │   ├── IPC/                 # Inter-process communication broker
│   │   └── System/              # Display server & event routing
│   ├── KeyMap/                  # Keyboard mapping
│   └── TextBuffer/              # Text buffer management
│
├── Programming_Manual/           # 26 comprehensive guides
│   ├── 01_Introduction_to_Ailang.md
│   ├── 02_Basic_Syntax_and_Types.md
│   ├── 03_Control_Flow.md
│   ├── ...
│   └── 26_Advanced_Techniques.md
│
├── Demo Programs/                # 150+ runnable example programs
│   ├── beginner/
│   ├── intermediate/
│   ├── advanced/
│   └── applications/
│
├── Applications/                 # Sample applications
├── TestCode/                     # Testing code examples
├── Tests/                        # Test suite & harness
│   └── Test262Harness.ailang    # ECMAScript Test262 harness
│
├── vscode-extension/             # VS Code extension
│   ├── extension.js             # Extension entry point
│   ├── package.json             # VS Code metadata
│   ├── syntaxes/                # TextMate grammar (syntax highlighting)
│   ├── snippets/                # Code snippets
│   └── License.md               # MIT License (extension only)
│
├── AiLang_CoreUtils/            # GNU CoreUtils reimplementation
├── AIMacro_Tests/               # AIMacro test suite
├── Benchmarks/                  # Performance benchmarks
├── C-64 basic intepreter/       # Commodore 64 BASIC interpreter
│
├── Language Docs BNF grammar etc/  # Language specification & grammar
├── Library Manuals/                # Library module documentation
├── Docs/                           # Additional documentation
│
├── Media/                       # Media assets
├── MediaCenter/                 # Media center application
├── fonts/                       # Custom fonts
├── icons/                       # Icon assets
├── alteix-sans-font/           # Alteix Sans font family
├── radix-icons/                 # Radix icon library
├── silver_system_atoms/         # System UI atoms
├── silver_system_atoms_tvg/     # TVG (Tiny Vector Graphics) atoms
│
├── kernel_module/               # Linux kernel module
├── tools/                       # Development tools
├── config/                      # Configuration files
├── Plans/                       # Development roadmap
├── Packager/                    # Package building utilities
├── dnd/                         # D&D game system files
├── dnd_game.ailang             # D&D game implementation
│
├── markup/                      # Markup language files
├── .claude/                     # Claude AI context files
├── .gitignore                  # Git ignore rules
├── .gitattributes              # Git attributes
├── .vscodeignore               # VS Code ignore rules
├── License.md                   # Sean Collins Software License (SCSL v1.0)
├── TEST_ODDITIES.md            # Known test quirks & issues
└── smoke_ailang_utils.sh       # Smoke test utility script
```

## Key Features

### Language & Compiler
- **Verb-first syntax** — Natural language-inspired programming paradigm
- **Self-hosted** — AILang compiler written in AILang (43,000+ lines across 75 files)
- **Static typing** — Compile-time type checking
- **Direct code generation** — Compiles to machine code via custom toolchain
- **Explicit semantics** — No hidden behavior, no implicit coercions

### Standard Library
- **Display & Rendering**
  - Framebuffer and surface drawing
  - Font rendering with multiple font families
  - Hardware-accelerated VIF (Video Interface)
  - Window compositing
  
- **UI Framework (Auckland)**
  - Event-driven window system
  - Dialog boxes (About, File dialogs)
  - Menu system with cascading support
  - Text regions with rich formatting
  - Window decorators and panes

- **System Components**
  - Display server with taskbar (deskbar)
  - IPC broker for inter-process communication
  - HTML parser and document renderer
  - Screenshot capture
  - Keyboard mapping and text buffer management

### Development Tools
- **Language Server** — Full IDE support via LSP
- **VS Code Extension** — Syntax highlighting, snippets, language features, connectome graph
- **REPL Consoles** — Interactive AILang and AIMacro interpreters
- **Test Harness** — ECMAScript Test262 compatibility
- **Analyzer** — Three-pass static analysis (memory, control flow, data flow)

### Educational Resources
- **26 Programming Manuals** — Structured learning path from beginner to advanced
- **150+ Demo Programs** — Runnable examples for every language feature
- **Library Manuals** — In-depth documentation for each standard library module
- **BNF Grammar** — Formal language specification

### Applications & Examples
- **C64 BASIC Interpreter** — Vintage computer emulation
- **CoreUtils Reimplementation** — Unix utilities in AILang
- **Fantasy Forge Engine** — Data-driven RPG engine
- **D&D Game System** — Interactive game framework
- **HalCode9000** — AI-assisted coding tools (separate repo)

## Building & Compilation

Compile AILang source files:
```bash
ailang.x your_program.ailang
```

The compiler generates an executable binary. Library imports are resolved at compile-time from the `Librarys/` directory.

### Compile and Run from VS Code

**Keyboard shortcuts:**
- `Ctrl+Shift+B` — Compile current file
- `F5` — Compile and run
- `Ctrl+Shift+A` — Run static analysis

Binaries are output to the current directory (configurable).

## Testing

Run the test suite:
```bash
./smoke_ailang_utils.sh
```

Run specific test harness:
```bash
ailang.x Test262Harness.ailang
```

See `TEST_ODDITIES.md` for known test quirks and edge cases.

## Documentation

- **Programming Manual (26 guides)** — `Programming_Manual/`
- **Demo Programs (150+)** — `Demo Programs/`
- **Language Specification** — `Language Docs BNF grammar etc/`
- **Library Reference** — `Library Manuals/`
- **Technical Docs** — `Docs/`

## Licensing

### Main Project
Licensed under **Sean Collins Software License (SCSL v1.0)**

- **Free for personal/academic use** (non-commercial)
- **Commercial use requires a paid license** — Contact: `smc.collins1977@gmail.com`
- **Forking/redistribution prohibited** — Modifications must be submitted upstream
- **No warranty** — Use at your own risk

See `License.md` for full terms.

### VS Code Extension
Licensed under **MIT License** (separate from compiler)

The VS Code extension (`vscode-extension/`) is MIT-licensed and includes:
- `extension.js`, `package.json`
- TextMate grammar (`syntaxes/`)
- Snippets and documentation

The AILang compiler, language server, and all `.ailang` source code remain under SCSL.

## Development

### Project Structure Notes
- Compiler binaries: `ailang.x`, `analyzer.x`
- Main entry point: `Main.ailang` (display server)
- Libraries are in `Librarys/` and auto-discovered at runtime
- Font assets: `fonts/`, `alteix-sans-font/`
- Icon assets: `icons/`, `radix-icons/`, `silver_system_atoms/`

### Contributing
- Modifications must be submitted upstream for review (per SCSL)
- See individual module READMEs in `Librarys/` for development guidelines
- Test coverage via `Test262Harness.ailang` and `AIMacro_Tests/`
- Learning resources in `Programming_Manual/` and `Demo Programs/` welcome community contributions

## Related Projects

- **AILang HDL** — Hardware description in AILang
- **AIMacro Language** — Python-like macro language for AILang
- **AiLang-Public-Library** — Community libraries
- **CoreUtils** — GNU utilities reimplementation
- **Fantasy-Forge-Engine** — RPG game engine
- **HalCode9000** — AI coding assistant (built in AILang)
- **OlympusRepo** — Self-hosted version control system

## Support & Contact

- **License inquiries:** `smc.collins1977@gmail.com`
- **Learning:** Start with `Programming_Manual/01_Introduction_to_Ailang.md`
- **Examples:** Browse `Demo Programs/` for runnable code
- **Issues & Development:** See `Plans/` directory
- **Known quirks:** See `TEST_ODDITIES.md`

---

## Project Statistics

- **Compiler Size:** 43,000+ lines of AILang code
- **Self-hosting:** Achieved in 43 days
- **Programming Manuals:** 26 comprehensive guides
- **Demo Programs:** 150+ runnable examples
- **Standard Library:** Modular, hierarchical organization
- **Test Coverage:** Extensive with Test262 harness
- **Zero external dependencies:** Fully self-contained

---

**AILang** — A modern programming language with verb-first syntax, built for performance, clarity, and self-hosting capability. Learn by reading manuals and experimenting with 150+ demo programs.

*Last updated: May 2026*
