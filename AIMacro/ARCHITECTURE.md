# AIMacro Architecture

## End-to-end path (current — AOT mode)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SOURCE: *.aim                                                          │
│  Python-ish syntax with explicit `end` terminators                      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LEXER — Library.AIMacroLexer.ailang                                    │
│  Token stream → FixedPool.Token (DEF, END, IF, FOR, CLASS, IMPORT, …)   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PARSER                                                                 │
│  • Library.AIMacroParserCore.ailang — statements, expressions, control  │
│  • Library.AIMacroParserOOP.ailang    — class, method, self, super      │
│  AST nodes → FixedPool.Node (PROGRAM, FUNCTION, CLASS_DEF, TRY_STMT, …) │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  CODE GENERATOR (emits AILang source text)                              │
│  • CodeGen1 — program structure, functions, imports header              │
│  • CodeGen2 — statements (if/while/for, assign, break/continue)         │
│  • CodeGen3 — binary/unary ops, string tracking, control flow           │
│  • CodeGen4 — calls, builtins, methods, packed args (>6 params)         │
│  • CodeGenOOP — classes, instances, isinstance, super                 │
│  • CodeGenDict — dict literals, subscript, len dispatch                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  OUTPUT: *.ailang                                                       │
│  LibraryImport.AIMacro.AIMacro (+ String, Types, Dict as needed)        │
│  User functions → Function.<name> { … }                                 │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  AILANG COMPILER — ailang.x (self-hosting, ~760 KB)                     │
│  Static ELF64 Linux binary, syscall-native, no dynamic linking          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  NATIVE BINARY — runs on Linux / WSL                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### CLI pipeline (`aimacro_cli.ailang`)

```
CLI_Open → read source
Lex_Init → Lex_Tokenize
Parse_Init → Parse_Program → AST
Gen_Init → Gen_Program → Gen_GetOutput (AILang string)
write stdout or output file
```

Debug output from lexer/parser/codegen goes to **stderr** (stdout redirected during compile).

### Console (`aimacro_console.ailang`)

Same pipeline with TUI, multiline input, optional token/AST display, file compile mode.

---

## Runtime library (`Library.AIMacro.ailang`)

Transpiled code calls into **AIMacro.*** builtins, not raw AILang for Python semantics.

| Category | Examples |
|----------|----------|
| Containers | `SmartLen`, `SmartGet`, `SmartPush`, typed list helpers |
| Strings | via `AIMacroString` + method dispatch in codegen |
| Dicts | `AIMacroDict` + `Hash.*` via `CodeGenDict` |
| Types | `AIMacroTypes` — `isinstance`, `TypeOf`, `TypeID.*` |
| Math | `Math.Power`, `Math.FloorDiv`, `AIMacro.Range`, trig |
| I/O | `AIMacro.Print`, `AIMacro.Input`, `AIMacro.Open` (partial) |
| CLI | `AIMacro.GetCommandLineArgs`, `AIMacro.Exit` |

Codegen maps Python names in `Gen_MapBuiltin` (`Library.AIMacroCodeGen4.ailang`).

Special-cased in `Gen_CallExpr`: `print`, `input`, `len`, `isinstance`, `type`,
class instantiation (`OOPGen_*`), packed calls (`Gen_PackedCall`).

---

## Library inventory (`Librarys/AIMacro/`)

| File | Role |
|------|------|
| `Library.AIMacroCore.ailang` | Tokens, nodes, lex state, parse state, gen state |
| `Library.AIMacroLexer.ailang` | Tokenization |
| `Library.AIMacroParserCore.ailang` | Core parser |
| `Library.AIMacroParserOOP.ailang` | OOP parser extensions |
| `Library.AIMacroTypeAnnotations.ailang` | Type hint parsing |
| `Library.AIMacroCodeGen1.ailang` | Codegen: program/functions |
| `Library.AIMacroCodeGen2.ailang` | Codegen: statements |
| `Library.AIMacroCodeGen3.ailang` | Codegen: expressions, strings |
| `Library.AIMacroCodeGen4.ailang` | Codegen: calls, builtins, methods |
| `Library.AIMacroCodeGenOOP.ailang` | Codegen: classes |
| `Library.AIMacroCodeGenDict.ailang` | Codegen: dicts |
| `Library.AIMacro.ailang` | **Runtime builtins** (~1900 lines) |
| `Library.AIMacroString.ailang` | String helpers |
| `Library.AIMacroDict.ailang` | Dict runtime |
| `Library.AIMacroTypes.ailang` | Runtime type checking |
| `Library.PAST*.ailang` | PAST AST (alternate/experimental parse tree) |

---

## Target architecture (VM mode — Phase 3)

Mirror the browser JS stack:

```
JSParser → JSCompiler → bytecode + const pool
JSRuntime → JSValue, objects, coercion
JSVM      → stack, frames, dispatch loop (~50 opcodes)
```

### Proposed AIMacro VM stack

```
Library.AIMacroLexer          (exists)
Library.AIMacroParser*        (exists)
Library.AIMacroCompiler       (NEW) — emit AIMacroOp bytecode
Library.AIMacroRuntime        (NEW) — AIMValue: int, str, list, dict, object
Library.AIMacroVM             (NEW) — stack, call frames, global table
Library.AIMacroVM.Builtins    (NEW) — opcode CALL_BUILTIN → AIMacro.*
Library.AIMacroVM.Dispatch    (NEW) — branch-dispatch loop (like JSVMDispatch)
```

### Dual-mode execution

| Mode | When | Output |
|------|------|--------|
| **AOT** | Production, benchmarks, OS tooling | Static binary via AILang compiler |
| **VM** | REPL, fast iteration, future embedding | Interpret bytecode in-process |

`aimacro_console.ailang` should eventually host the VM REPL instead of re-transpiling
every submission.

---

## Codegen → AILang conventions

- Functions become `Function.<name>` with explicit `Input`/`Output`/`Body`
- `main()` or script entry → `SubRoutine.Main` or explicit call from Main
- String variables tracked via `Gen_MarkStringVar` / `IsStringVar` for concat codegen
- Dict vars tracked via `Gen_IsDictVar` for `len`, subscript, methods
- String equality uses `StringCompare` → `Node.STR_EQ` / `STR_NE`, not raw `==`
- More than 6 call arguments use `Gen_PackedCall` + `Array.Create` pack buffer

---

## Dependencies on core AILang

| AILang module | Used for |
|---------------|----------|
| `Array` / `Arrays` | Lists, codegen temps, packed args |
| `Hash` | Dict storage |
| `StringUtils` | String ops |
| `FixedPointTrig` | Math builtins |

Transpiled programs **do not** require the full OS/display stack — only linked
libraries referenced in generated `LibraryImport` lines.