# AILang Self-Hosting Compiler

<p align="center">
  <img src="https://img.shields.io/badge/status-SELF--HOSTING-brightgreen?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/platform-Linux%20x86__64-blue?style=for-the-badge" alt="Platform">
  <img src="https://img.shields.io/badge/license-SCSL-orange?style=for-the-badge" alt="License">
</p>

<p align="center">
  <strong>A systems programming language that compiles itself.</strong><br>
  Written in AILang. Compiling AILang. Producing native x86-64 Linux executables.
</p>

---

## 🎉 Milestone: Self-Hosting Achieved

**January 5, 2026** - The AILang compiler has reached its primary goal: **true self-hosting**.

```
Python Bootstrap → compiler.x → compiler2.x → compiler3.x ═══ compiler4.x
                                                    │              │
                                                    └──────────────┘
                                                       BYTE-IDENTICAL
```

The compiler builds itself across multiple generations and produces **byte-identical binaries** - the definition of a fixed-point self-hosting compiler.

---

## What is AILang?

AILang is a systems programming language designed for:
- **Clarity**: Named operators, explicit control flow, no hidden behavior
- **Self-hosting**: The compiler is written in itself
- **Direct compilation**: Source → native x86-64 ELF executables (no intermediate steps)
- **Minimal dependencies**: Only needs Linux syscalls

```ailang
// Clear, explicit syntax
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

SubRoutine.Main {
    PrintMessage("5! = ")
    PrintNumber(Factorial(5))
    PrintMessage("\n")
}

RunTask(Main)
```

---

## Compiler Capabilities

### ✅ Fully Working

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
| **Control Flow** | IfCondition/ThenBlock/ElseBlock, WhileLoop, ForEach, ExitLoop, ContinueLoop, Branch/Case |
| **Functions** | Function/SubRoutine definitions, parameters (6 registers), locals, nested calls, ReturnValue |
| **File I/O** | WriteTextFile, ReadTextFile, FileExists, GetFileSize |
| **Import System** | Multi-file compilation, library imports, symbol conflict detection |
| **Code Generation** | x86-64 native instructions, ELF64 executables, data relocations |

### 🔄 In Development

| Feature | Status |
|---------|--------|
| Hex literals (`0xNN`) | Needs lexer support |
| NumberToString | Needs implementation |
| StringToNumber | Needs implementation |
| Static checker | Testing |
| Debug output cleanup | Planned |

---

## Quick Start

### Prerequisites
- Linux x86-64
- Python 3.x (for initial bootstrap only)

### Bootstrap the Compiler

```bash
# Clone the repository
git clone https://github.com/AiLang-Author/Ailang-Self-Hosting-.git
cd Ailang-Self-Hosting-

# Bootstrap: Python builds the first compiler
python3 main.py ailang_console.ailang
mv ailang_console_exec compiler.x

# Now the compiler builds itself
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
ailang> build myprogram
ailang> quit

./myprogram
```

### Hello World

```ailang
// hello.ailang
SubRoutine.Main {
    PrintMessage("Hello, World!\n")
}
RunTask(Main)
```

---

## Language Features

### Named Operators
No operator precedence confusion - every operation is explicit:
```ailang
// Instead of: result = a * b + c * d
result = Add(Multiply(a, b), Multiply(c, d))
```

### Explicit Control Flow
```ailang
IfCondition GreaterThan(score, 100) ThenBlock: {
    PrintMessage("High score!\n")
} ElseBlock: {
    PrintMessage("Keep trying\n")
}

WhileLoop LessThan(i, 10) {
    PrintNumber(i)
    i = Add(i, 1)
}
```

### Functions with Contracts
```ailang
Function.SafeDivide {
    Input: a: Integer
    Input: b: Integer
    Output: Integer
    Body: {
        IfCondition EqualTo(b, 0) ThenBlock: {
            PrintMessage("Error: Division by zero\n")
            ReturnValue(0)
        }
        ReturnValue(Divide(a, b))
    }
}
```

### Multi-File Projects
```ailang
// main.ailang
Import.utils
Import.math

SubRoutine.Main {
    result = Math_Add(10, 20)
    Utils_PrintResult(result)
}
RunTask(Main)
```

### Memory Management
```ailang
// Direct memory control
buffer = Allocate(1024)
SetByte(buffer, 0, 65)      // Write 'A'
char = GetByte(buffer, 0)   // Read back
Deallocate(buffer, 1024)
```

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
├── main.py                    # Python bootstrap compiler
├── ailang_console.ailang      # Self-hosting compiler source
├── compiler.x                 # Compiled self-hosting compiler
│
├── Librarys/
│   ├── Compiler/
│   │   ├── Frontend/
│   │   │   ├── Lexer/         # CLexer - tokenization
│   │   │   ├── Parser/        # CParser - AST generation
│   │   │   └── AST/           # AST types and operations
│   │   │
│   │   ├── Compile/
│   │   │   └── Modules/       # CCompile* - compilation
│   │   │       ├── CCompileArith.ailang
│   │   │       ├── CCompileIO.ailang
│   │   │       ├── CCompileStmt.ailang
│   │   │       └── ...
│   │   │
│   │   ├── CodeEmit/
│   │   │   └── X86/           # CEmitX86* - x86-64 code gen
│   │   │
│   │   └── Output/            # ELF builder
│   │
│   ├── Library.XArrays.ailang # Dynamic arrays
│   └── Library.FileIO.ailang  # File operations
│
└── tests/                     # Test programs
```

---

## Roadmap

### v0.3.0 (Next)
- [ ] Hex literal support in lexer
- [ ] Remove debug output
- [ ] NumberToString / StringToNumber implementation

### v0.4.0
- [ ] Static checker integration
- [ ] Additional string functions
- [ ] Performance optimizations

### v0.5.0
- [ ] Float support
- [ ] Struct types
- [ ] Enhanced error messages

### v1.0.0
- [ ] Complete standard library
- [ ] Documentation
- [ ] Multi-platform support

---

## License

**Sean Collins Software License (SCSL)**

Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.

See [LICENSE](LICENSE) for full terms.

---

## Acknowledgments

AILang is a solo project demonstrating that self-hosting compilers can be built from scratch with clear, explicit language design principles.

---

<p align="center">
  <strong>AILang: Written in itself. Compiling itself. Running itself.</strong>
</p>