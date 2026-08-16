# AILang Self-Hosting Repository

Welcome to the **AILang Programming Language** — a self-hosted compiler featuring explicit syntax, code efficiency, and a complete systems programming ecosystem.

## Overview

**Repo layout:** see [`WORKSPACE.md`](WORKSPACE.md). **Docs:** [`docs/README.md`](docs/README.md). **AMD GPU driver kit:** [`dev/amdgpu/`](dev/amdgpu/).

### Key Components

- **Self-hosted compiler** (3 MB) — Includes complete x86 instruction library (10k instructions), inline assembly support, and optimized code generation
- **57 POSIX CoreUtils** — Unix utility implementations with custom regex engine
- **Complete windowing system** (800 KB) — Display server with window manager and UI framework
- **Web browser** — JavaScript JVM (~69% test262 compliance), HTML/CSS in development
- **GPU computing** — Native GCN driver with support for legacy cards (GCN 1.0+)
- **Motion control library** — CNC machine programming and trajectory planning
- **Hardware driver ecosystem** — Memryx MX3 accelerator, generic device drivers
- **Multi-architecture IR backend** — x86_64 production-ready; ARM, RISC-V in development

## Quick Start

### Installation

```bash
sudo ./install_compiler.sh [install-dir]
```

Default install directory: `/usr/local/bin`. Uses symlinks for zero-rebuild installation overhead.

To uninstall:
```bash
sudo rm /usr/local/bin/ailang.x /usr/local/bin/analyzer.x
```

### Install AILang CoreUtils

```bash
cd AiLang_CoreUtils
./install_ailang_utils.sh
./bench_all_utils.sh  # Compare against GNU
```

## Learning AILang

- **26 Programming Manuals** — Step-by-step guides in `Programming_Manual/`
- **150+ Demo Programs** — Runnable examples in `Demo Programs/`
- **Getting Started:** Read `Programming_Manual/01_Introduction_to_Ailang.md`

## Language Features

### Design
- **Verb-first syntax** — Natural language-inspired, every operation is explicit
- **No operator precedence** — Eliminates hidden behavior
- **Static typing** — Compile-time checking with inference
- **Direct code generation** — Compiles to machine code via custom IR

### Performance
- **22 built-in string methods** — Most SSE2-optimized
- **SSE2 function library** — Vectorized operations
- **Direct syscalls** — Minimal abstraction
- **Smart optimizer** — Lean, efficient code generation
- **Inline assembly** — Direct assembly integration in AILang code

## Compiler Development

The compiler is actively developed with ongoing improvements:

- **Code Generation** — Continuous optimization of emitted machine code
- **Performance Tuning** — Refinements to compilation speed and output quality
- **x86 Instruction Support** — Complete 10k instruction library with full encoding/emit capabilities
- **HDL to Verilog Synthesis** — Early-stage hardware description language compilation for hardware development

## 57 POSIX CoreUtils

Production-grade Unix utilities, 50-71% smaller than GNU equivalents:

**Text Processing:** grep, sed, awk, cut, sort, uniq, head, tail, wc, tr, fold, paste, nl
**File Operations:** cat, cp, mv, rm, mkdir, find, ls, file, touch, ln
**System Info:** pwd, whoami, id, uname, env, printenv, date, uptime, df
**Data Processing:** diff, patch, cmp, od, xxd, base64, md5sum, sha256sum, tee, yes, seq
**Output:** echo, printf, less, more, col, expand, unexpand
**Advanced:** tar, gzip, gunzip, zip, unzip, basename, dirname, which, true, false, sleep

## Repository Structure

```
.
├── ailang.x                      # Self-hosted compiler
├── analyzer.x                    # Static analyzer
├── Main.ailang                   # Display server
├── ailang_cli.ailang             # CLI
├── ailang_console.ailang         # REPL
├── ailang_lsp.ailang             # Language server
├── Librarys/                     # Standard library
│   ├── Arena/                    # Memory allocator
│   ├── Arrays/                   # Array utilities
│   ├── Strings/                  # 22 string methods
│   ├── Display/                  # Windowing & UI
│   ├── GPU/                      # GPU computing
│   ├── Motion/                   # CNC control
│   ├── Hardware/                 # Device drivers
│   └── KeyMap/, TextBuffer/
├── AiLang_CoreUtils/             # 57 POSIX utilities
├── Programming_Manual/           # 26 guides
├── Demo Programs/                # 150+ examples
├── Browser/                      # Web browser
├── GPU/                          # GPU driver
├── Motion/                       # Motion control
├── Hardware/                     # Hardware integration
├── IR-Backend/                   # Multi-arch IR
├── Tests/                        # Test suite
├── vscode-extension/             # VS Code plugin
├── Docs/                         # Documentation
├── Media/, fonts/, icons/        # Assets
├── License.md                    # SCSL v1.0
├── TEST_ODDITIES.md              # Known issues
└── smoke_ailang_utils.sh         # Smoke tests
```

## Building & Compilation

Compile AILang source:
```bash
ailang.x your_program.ailang
```

### VS Code Integration
- `Ctrl+Shift+B` — Compile
- `F5` — Compile and run
- `Ctrl+Shift+A` — Static analysis

## Testing

```bash
./smoke_ailang_utils.sh          # Run smoke tests
ailang.x Test262Harness.ailang   # ECMAScript compliance
```

See `TEST_ODDITIES.md` for known issues.

## Documentation

- **Programming Manual (26 guides)** — `Programming_Manual/`
- **Demo Programs (150+)** — `Demo Programs/`
- **CoreUtils Docs** — `AiLang_CoreUtils/README.md`
- **Language Spec** — `Language Docs BNF grammar etc/`
- **Library Reference** — `Library Manuals/`

## Licensing

### Main Project
**Sean Collins Software License (SCSL v1.0)**
- Free for personal/academic use (non-commercial)
- Commercial use requires paid license: `smc.collins1977@gmail.com`
- Forking/redistribution prohibited
- No warranty

See `License.md` for full terms.

### VS Code Extension
**MIT License** (separate from compiler)

## Development

- **Compiler:** 3 MB, includes complete x86 instruction library and inline assembly support
- **Display Server:** 800 KB, complete windowing
- **Browser:** 2.3 MB with JS JVM
- **CoreUtils:** 57 utilities, 50-71% smaller than GNU
- **Libraries:** In `Librarys/`, auto-discovered at runtime

### Contributing
Modifications must be submitted upstream per SCSL. See module READMEs for guidelines.

## Support & Contact

- **License inquiries:** `smc.collins1977@gmail.com`
- **Learning:** Start with `Programming_Manual/01_Introduction_to_Ailang.md`
- **Examples:** Browse `Demo Programs/`
- **CoreUtils:** See `AiLang_CoreUtils/README.md`
- **Issues:** See `Plans/` directory

---

**AILang** — A self-hosted systems programming language with explicit syntax and a complete ecosystem for high-performance computing.

Built for performance. Built for clarity. Built entirely in itself.

*Last updated: August 2026*
