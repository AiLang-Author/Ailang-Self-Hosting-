<p align="center">
  <img src="https://img.shields.io/badge/status-self--hosting%20milestone-brightgreen" alt="Status">
  <img src="https://img.shields.io/badge/platform-Linux%20x86__64-blue" alt="Platform">
  <img src="https://img.shields.io/badge/license-SCSL-orange" alt="License">
</p>

# AILang

**A systems programming language designed for clarity, safety, and self-hosting.**

AILang is a compiled language that produces native x86-64 Linux executables. It features explicit control flow, named operators, actor-based concurrency, and a pool-based memory model. The language is currently bootstrapped via Python and is actively working toward **complete self-hosting**.

---

## Why AILang?

```ailang
// Clear, readable syntax with named operators
score = Add(Multiply(base, 2), bonus)

// Explicit control flow - no hidden behavior
IfCondition GreaterThan(score, 100) ThenBlock: {
    PrintMessage("High score achieved!")
} ElseBlock: {
    PrintMessage("Keep trying!")
}
```

AILang rejects the ambiguity of C-style operators and implicit control flow. Every operation is explicit, every block is labeled, and the code reads like what it does.

---

## Quick Start

### Hello World

```ailang
// hello.ailang
PrintMessage("Hello, World!")
```

### Compile & Run

```bash
python3 main.py hello.ailang
./hello_exec
```

### A Real Example

```ailang
// factorial.ailang
Function.Math.Factorial {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessEqual(n, 1) ThenBlock: {
            ReturnValue(1)
        }
        
        result = 1
        i = 2
        WhileLoop LessEqual(i, n) {
            result = Multiply(result, i)
            i = Add(i, 1)
        }
        ReturnValue(result)
    }
}

fact5 = Math.Factorial(5)
PrintMessage("5! =")
PrintNumber(fact5)  // Output: 120
```

---

## Key Features

### Named Operators
No operator precedence confusion. Ever.

```ailang
// Instead of: a + b * c (is it a + (b * c) or (a + b) * c?)
result = Add(a, Multiply(b, c))  // Unambiguous
```

### Explicit Control Flow
Every branch is labeled. No dangling else.

```ailang
IfCondition EqualTo(status, "ready") ThenBlock: {
    ProcessRequest()
} ElseBlock: {
    QueueRequest()
}

WhileLoop LessThan(i, count) {
    ProcessItem(i)
    i = Add(i, 1)
}
```

### Pool-Based Memory
Deterministic memory management without garbage collection.

```ailang
FixedPool.GameState {
    "score": Initialize=0, CanChange=True
    "level": Initialize=1, CanChange=True
    "max_lives": Initialize=3, CanChange=False
}

// Access pool variables
GameState.score = Add(GameState.score, 100)
```

### Actor Concurrency Model
Safe concurrent programming through message passing.

```ailang
LoopActor.Worker {
    running = 1
    WhileLoop EqualTo(running, 1) {
        // Process work
        LoopYield()
    }
}
```

### Direct System Access
Full control when you need it.

```ailang
// System calls, file I/O, network operations
WriteTextFile("output.txt", "Data saved")
exists = FileExists("config.txt")
```

---

## Language Overview

### Types
| Type | Description | Example |
|------|-------------|---------|
| Integer | 64-bit signed | `42`, `-100` |
| Text | UTF-8 string | `"Hello"` |
| Boolean | True/False | `True`, `False` |
| Address | Memory pointer | `Allocate(1024)` |

### Operators
| Category | Functions |
|----------|-----------|
| Arithmetic | `Add`, `Subtract`, `Multiply`, `Divide`, `Modulo` |
| Comparison | `EqualTo`, `NotEqual`, `LessThan`, `GreaterThan`, `LessEqual`, `GreaterEqual` |
| Logical | `And`, `Or`, `Not` |
| Bitwise | `BitAnd`, `BitOr`, `BitXor`, `BitNot`, `Shl`, `Shr` |

### Control Flow
- `IfCondition ... ThenBlock: { } ElseBlock: { }`
- `WhileLoop condition { }`
- `ForEvery item in collection { }`
- `Fork condition TrueBlock: { } FalseBlock: { }`
- `Branch(value) { Case: ... Default: ... }`
- `TryBlock: { } CatchError: { } FinallyBlock: { }`

---

## Project Status: Self-Hosting Milestone

AILang is approaching a critical milestone: **the compiler will compile itself**.

### Current Architecture (Bootstrap)
```
AILang Source → Python Compiler → x86-64 Assembly → ELF Binary
```

### Target Architecture (Self-Hosting)
```
AILang Source → AILang Compiler → x86-64 Assembly → ELF Binary
```

### What's Working
- ✅ Complete lexer and parser
- ✅ Type system with semantic analysis
- ✅ x86-64 code generation
- ✅ ELF binary output
- ✅ Functions, SubRoutines, FixedPools
- ✅ Control flow (if, while, for, try/catch)
- ✅ String operations
- ✅ File I/O
- ✅ Memory management (pools, allocate/deallocate)
- ✅ Actor-based concurrency primitives

### In Progress
- 🔄 Self-hosting compiler (AILang written in AILang)
- 🔄 Complete standard library in AILang
- 🔄 Expanded test coverage

### Planned
- 📋 ARM64 backend
- 📋 RISC-V backend
- 📋 Optimization passes
- 📋 Debug symbols (DWARF)

---

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Reference](docs/AILANG_Quick_Syntax_Reference.md) | Syntax cheat sheet |
| [Flow Control Manual](docs/AILANG_Flow_Control_Programming_Manual.md) | Control structures |
| [Concurrency Guide](docs/AILANG_Concurrency_and_Systems_Programming.md) | Actors and systems |
| [String Operations](docs/AILANG_String_Operations.md) | Text processing |
| [Memory Model](docs/AiLang_Pool_Memory_Model.md) | Pool-based memory |

---

## Building from Source

### Requirements
- Python 3.8+
- Linux x86-64

### Installation
```bash
git clone https://github.com/yourusername/ailang.git
cd ailang
```

### Compile a Program
```bash
python3 main.py yourprogram.ailang
./yourprogram_exec
```

### Debug Mode
```bash
python3 main.py -D yourprogram.ailang  # Enables debug assertions
```

---

## Examples

### String Processing
```ailang
first = "Hello"
second = "World"
greeting = StringConcat(StringConcat(first, ", "), second)
PrintMessage(greeting)  // "Hello, World"
```

### File Operations
```ailang
WriteTextFile("log.txt", "Application started")

IfCondition FileExists("config.txt") ThenBlock: {
    PrintMessage("Config found")
} ElseBlock: {
    PrintMessage("Using defaults")
}
```

### Memory Pools
```ailang
FixedPool.Config {
    "buffer_size": Initialize=4096, CanChange=False
    "timeout": Initialize=30, CanChange=True
}

buffer = Allocate(Config.buffer_size)
// Use buffer...
Deallocate(buffer, Config.buffer_size)
```

---

## Contributing

AILang is developed by Sean Collins at 2 Paws Machine and Engineering.

The project uses the **Sean Collins Software License (SCSL)**. See [LICENSE](LICENSE) for details on usage restrictions and permissions.

---

## Architecture

```
ailang/
├── main.py                    # Entry point
├── ailang_parser/             # Lexer, parser, AST
│   ├── compiler.py
│   ├── lexer.py
│   └── ailang_ast.py
├── ailang_compiler/           # Code generation
│   ├── ailang_compiler.py     # Main orchestrator
│   ├── assembler.py           # x86-64 assembler
│   ├── elf_generator.py       # ELF binary output
│   └── modules/               # Compiler modules
│       ├── arithmetic_ops.py
│       ├── control_flow.py
│       ├── memory_manager.py
│       ├── string_ops.py
│       └── ...
└── Libraries/                 # Standard library
    ├── Library.XArrays.ailang
    ├── Library.Signals.ailang
    └── ...
```

---

## Self-Hosting Compiler Design

The self-hosting compiler follows a clean separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Language Processing)                                  │
│  Lexer → Parser → AST                                           │
├─────────────────────────────────────────────────────────────────┤
│  Compiler Modules (Target-Agnostic)                             │
│  Emit: Asm_Mov, Asm_Add, Asm_Jmp, etc.                         │
├─────────────────────────────────────────────────────────────────┤
│  Assembler (Target-Specific: x86-64 / ARM64 / RISC-V)          │
│  Encode instructions to machine code                            │
├─────────────────────────────────────────────────────────────────┤
│  Output (ELF Generation)                                        │
│  Create executable binary                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle**: Compiler modules emit abstract instructions (`Asm_Mov_RR(RAX, RBX)`), never raw bytes. The assembler layer handles encoding. This makes adding new target architectures straightforward.

---

## License

Copyright © 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.

Licensed under the **Sean Collins Software License (SCSL)**. See [LICENSE](LICENSE) for terms and conditions.

---

<p align="center">
  <strong>AILang: Code that says what it means.</strong>
</p>
