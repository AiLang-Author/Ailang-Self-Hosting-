# AILang Self-Hosting Repository

Welcome to the **AILang Programming Language** — a self-hosted compiler and runtime system with a verb-first syntax paradigm for modern language design.

## Overview

This is the official self-hosting repository for **AILang**, featuring:
- **Self-hosted compiler** (`ailang.x`) — compiles AILang to machine code
- **Language server** (`ailang_lsp.ailang`) — IDE support with VS Code integration
- **Comprehensive standard libraries** — display rendering, UI components, and system utilities
- **Full development toolchain** — CLI tools, console, testing harness, and documentation
- **Desktop environment** — display server with window management, taskbar, and UI framework

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
├── Applications/                 # Sample applications
├── Demo Programs/                # Demonstration programs
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
├── Programming_Manual/             # Developer guide
├── Library Manuals/                # Library documentation
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
- **Self-hosted** — AILang compiler written in AILang
- **Static typing** — Compile-time type checking
- **Direct code generation** — Compiles to machine code via custom toolchain

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
- **VS Code Extension** — Syntax highlighting, snippets, language features
- **REPL Consoles** — Interactive AILang and AIMacro interpreters
- **Test Harness** — ECMAScript Test262 compatibility
- **Analyzer** — Code analysis and diagnostics

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

- **Language Specification** — `Language Docs BNF grammar etc/`
- **Programming Manual** — `Programming_Manual/`
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
- **Documentation:** See `Docs/` and manuals
- **Issues & Development:** See `Plans/` directory
- **Known quirks:** See `TEST_ODDITIES.md`

---

**AILang** — A modern programming language with verb-first syntax, built by the community for performance, clarity, and self-hosting capability.

*Last updated: May 2026*
