# AILang JavaScript Engine — Engineering Design Document

**Revision:** 1.0  
**Date:** 2026-05-16  
**Author:** Sean Collins, 2 Paws Machine and Engineering  
**License:** SCSL  
**Test262 Compliance:** 12,567 / 23,899 (52.6%)

---

## Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [JSLexer — Tokenizer](#2-jslexer--tokenizer)
3. [JSParser — Recursive-Descent Parser](#3-jsparser--recursive-descent-parser)
4. [JSValidate — Truth-Table Validator](#4-jsvalidate--truth-table-validator)
5. [JSCompiler — AST-to-Bytecode Compiler](#5-jscompiler--ast-to-bytecode-compiler)
6. [JSRuntime — Value System & Type Coercion](#6-jsruntime--value-system--type-coercion)
7. [JSVM — Bytecode Virtual Machine](#7-jsvm--bytecode-virtual-machine)
8. [JSBridge — DOM Bindings](#8-jsbridge--dom-bindings)
9. [JSEngine — Orchestrator](#9-jsengine--orchestrator)
10. [Integration — cc_js_ipc & Test262 Harness](#10-integration--cc_js_ipc--test262-harness)
11. [Roadmap & Future Work](#11-roadmap--future-work)

---

## 1. Overview & Architecture

### 1.1 System Purpose

The AILang JavaScript Engine is a native, ahead-of-time-compiled JavaScript implementation embedded within the AILang ecosystem. It provides:

- **Full JS-to-bytecode compilation** via a classic lex→parse→compile→execute pipeline
- **Stack-based bytecode VM** modeled after CPU6502's dispatch loop
- **DOM integration** for browser scripting (document, console, event listeners)
- **MCP tool interface** (`cc_js_ipc`) for LLM orchestrator access
- **Test262 harness** for ECMAScript conformance validation

### 1.2 High-Level Pipeline

```
Source Text
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  JSLexer (Tokenizer)                                  │
│  • Character-by-character scan                        │
│  • Produces flat token stream (~45 token types)       │
│  • Handles: identifiers, numbers, strings,            │
│    operators, keywords, comments, regex literals      │
└────────────────────────┬─────────────────────────────┘
                         │ token stream
                         ▼
┌──────────────────────────────────────────────────────┐
│  JSParser (Recursive Descent + Pratt Precedence)     │
│  • Consumes token stream                              │
│  • Builds AST with linked-list children               │
│  • ~55 AST node types, 80-byte nodes                  │
│  • Pratt climbing for binary ops (no precedence table) │
└────────────────────────┬─────────────────────────────┘
                         │ AST root
                         ▼
┌──────────────────────────────────────────────────────┐
│  JSCompiler (Tree-Walk Code Generator)                │
│  • Walks AST, emits flat bytecode + constant pool    │
│  • ~75 opcodes, 1-byte + 0-2 byte operands           │
│  • Jump patching, scope resolution, loop management   │
└────────────────────────┬─────────────────────────────┘
                         │ bytecode + constants
                         ▼
┌──────────────────────────────────────────────────────┐
│  JSVM (Stack-Based Bytecode Interpreter)              │
│  • Branch-dispatch over opcodes                       │
│  • Value stack (4096 max), call frames (256 max)      │
│  • Global variable hash (XSHash)                      │
│  • Step counter with configurable limit               │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
                    JSValue (result)
```

### 1.3 Source File Inventory

| File | Lines | Responsibility |
|------|-------|---------------|
| `Library.JSLexer.ailang` | 1,477 | Character→token conversion |
| `Library.JSParser.ailang` | 4,967 | Token→AST construction |
| `Library.JSValidate.ailang` | 209 | Truth-table validation tables |
| `Library.JSCompiler.ailang` | 3,927 | AST→bytecode emission |
| `Library.JSRuntime.ailang` | 3,370 | Values, types, coercion, natives |
| `Library.JSVM.ailang` | 2,297 | Bytecode interpreter |
| `Library.JSBridge.ailang` | 2,073 | DOM bindings, events, timers |
| `Library.JSEngine.ailang` | 902 | Orchestrator, page loading |
| **Total** | **19,222** | |

### 1.4 Dependency Graph

```
JSEngine (orchestrator)
  ├── JSLexer      (tokenizer)
  ├── JSParser     (AST builder)
  │     └── JSValidate (truth tables)
  ├── JSCompiler   (code generator)
  ├── JSRuntime    (values, types)
  │     ├── Arena
  │     ├── XArrays
  │     ├── StringUtils
  │     └── HashMap (XSHash for globals)
  ├── JSVM         (interpreter)
  │     ├── JSRuntime
  │     ├── JSCompiler  (for bytecode constants)
  │     └── HashMap
  └── JSBridge     (DOM bindings)
        ├── HTMLDom
        └── JSRuntime
```

### 1.5 Design Principles

1. **No GC — Arena Allocation.** All memory is managed via the `Arena` library. Values, AST nodes, tokens, and bytecode are allocated linearly and freed in bulk on reset. No garbage collection.

2. **Clobber Safety.** The AILang compiler uses global `FixedPool` temporaries that can be overwritten by recursive function calls. Every function saves inputs to locals on the first line of Body. Each subsystem maintains its own push/pop stack for saving temporaries across calls.

3. **Integer-Only Arithmetic.** The runtime currently uses integer math only (no floats). IEEE 754 double support is planned (Phase 4 of roadmap).

4. **Stack-Based VM.** No register allocation. All operations push/pop from a value stack. Call frames track return addresses, local variable tables, and scope chains.

5. **Native Function Dispatch.** Built-in functions (console.log, setTimeout, Math.abs, etc.) are registered in a dispatch table keyed by negative bytecode offsets, avoiding name-based lookups.

### 1.6 Memory Layout Philosophy

All pools are pre-allocated at init time:

| Pool | Size | Max Entries | Entry Size |
|------|------|-------------|------------|
| Token Stream | ~256 KB | ~8,192 tokens | 32 bytes |
| AST Nodes | ~1.28 MB | 16,384 nodes | 80 bytes |
| Bytecode | ~256 KB | ~65,536 ops | 1-3 bytes/op |
| Constant Pool | ~512 KB | 4,096 entries | ~128 bytes |
| JSValues | ~128 KB | 8,192 values | 16 bytes |
| VM Value Stack | ~32 KB | 4,096 entries | 8 bytes (pointer) |
| VM Call Frames | ~10 KB | 256 frames | 40 bytes |
| Native Table | ~1.5 KB | 64 entries | 24 bytes |
| Timer Queue | ~1 KB | 32 timers | 32 bytes |
| DOM Wrappers | ~8 KB | 512 entries | 16 bytes |
| Event Listeners | ~6 KB | 256 entries | 24 bytes |

### 1.7 Execution Model

The engine supports three execution modes:

1. **Page Load** (`JSEngine_LoadPage`): DOM tree walk → extract `<script>` tags → execute each in document order. Bridge initialized with DOM root. Globals registered.

2. **Eval String** (`JSEngine_EvalString`): Execute arbitrary JS string at any time. Used for console input, bookmarklets, and the MCP tool.

3. **Per-Frame Tick** (`JSEngine_Tick`): Called from browser main loop. Dispatches expired setTimeout/setInterval callbacks. Returns number of timers fired.

---

## 2. JSLexer — Tokenizer

### 2.1 Overview

`Library.JSLexer.ailang` (1,477 lines) performs character-by-character lexical analysis of JavaScript source text. It converts a raw byte buffer into a flat token stream consumed by the parser.

### 2.2 Token Type Enumeration

The lexer recognizes ~45 token types, organized into categories:

#### Literals
| Token | Value | Description |
|-------|-------|-------------|
| IDENT | 1 | Identifier (variable name, keyword) |
| NUMBER | 2 | Numeric literal (integer only) |
| STRING | 3 | String literal (single/double quoted) |

#### Punctuation
| Token | Value | Description |
|-------|-------|-------------|
| LPAREN | 10 | `(` |
| RPAREN | 11 | `)` |
| LBRACE | 12 | `{` |
| RBRACE | 13 | `}` |
| LBRACKET | 14 | `[` |
| RBRACKET | 15 | `]` |
| SEMI | 16 | `;` |
| COMMA | 17 | `,` |
| DOT | 18 | `.` |
| COLON | 19 | `:` |
| QUESTION | 20 | `?` |

#### Operators
| Token | Value | Description |
|-------|-------|-------------|
| PLUS | 30 | `+` |
| MINUS | 31 | `-` |
| STAR | 32 | `*` |
| SLASH | 33 | `/` |
| PERCENT | 34 | `%` |
| ASSIGN | 35 | `=` |
| EQ | 36 | `==` |
| STRICT_EQ | 37 | `===` |
| NEQ | 38 | `!=` |
| STRICT_NEQ | 39 | `!==` |
| LT | 40 | `<` |
| GT | 41 | `>` |
| LTE | 42 | `<=` |
| GTE | 43 | `>=` |
| AND | 44 | `&&` |
| OR | 45 | `\|\|` |
| NOT | 46 | `!` |
| AMP | 47 | `&` |
| PIPE | 48 | `\|` |
| CARET | 49 | `^` |
| TILDE | 50 | `~` |
| SHL | 51 | `<<` |
| SHR | 52 | `>>` |
| USHR | 59 | `>>>` |

#### Compound Assignment
| Token | Value | Description |
|-------|-------|-------------|
| PLUS_ASSIGN | 53 | `+=` |
| MINUS_ASSIGN | 54 | `-=` |
| STAR_ASSIGN | 55 | `*=` |
| SLASH_ASSIGN | 56 | `/=` |
| PERCENT_ASSIGN | 60 | `%=` |
| AMP_ASSIGN | 61 | `&=` |
| PIPE_ASSIGN | 62 | `\|=` |
| CARET_ASSIGN | 63 | `^=` |
| SHL_ASSIGN | 64 | `<<=` |
| SHR_ASSIGN | 65 | `>>=` |
| USHR_ASSIGN | 66 | `>>>=` |
| AND_ASSIGN | 114 | `&&=` |
| OR_ASSIGN | 115 | `\|\|=` |
| NULLISH_ASSIGN | 113 | `??=` |

#### Increment/Decrement/Spread
| Token | Value | Description |
|-------|-------|-------------|
| PLUS_PLUS | 57 | `++` |
| MINUS_MINUS | 58 | `--` |
| DOT3 | 59 | `...` (spread/rest — note: shares value 59 with USHR in some contexts) |
| ARROW | 67 | `=>` |
| STAR_STAR | 110 | `**` (exponentiation) |
| STAR_STAR_ASSIGN | 111 | `**=` |
| NULLISH | 112 | `??` |

#### Keywords
| Token | Value | Description |
|-------|-------|-------------|
| KW_VAR | 70 | `var` |
| KW_LET | 71 | `let` |
| KW_CONST | 72 | `const` |
| KW_FUNCTION | 73 | `function` |
| KW_RETURN | 74 | `return` |
| KW_IF | 75 | `if` |
| KW_ELSE | 76 | `else` |
| KW_WHILE | 77 | `while` |
| KW_FOR | 78 | `for` |
| KW_BREAK | 79 | `break` |
| KW_CONTINUE | 80 | `continue` |
| KW_TRUE | 81 | `true` |
| KW_FALSE | 82 | `false` |
| KW_NULL | 83 | `null` |
| KW_UNDEFINED | 84 | `undefined` |
| KW_NEW | 85 | `new` |
| KW_THIS | 86 | `this` |
| KW_TYPEOF | 87 | `typeof` |
| KW_VOID | 88 | `void` |
| KW_DELETE | 89 | `delete` |
| KW_IN | 90 | `in` |
| KW_DO | 91 | `do` |
| KW_SWITCH | 92 | `switch` |
| KW_CASE | 93 | `case` |
| KW_DEFAULT | 94 | `default` |
| KW_TRY | 95 | `try` |
| KW_CATCH | 96 | `catch` |
| KW_FINALLY | 97 | `finally` |
| KW_THROW | 98 | `throw` |
| KW_INSTANCEOF | 100 | `instanceof` |
| KW_YIELD | 101 | `yield` |
| KW_CLASS | 102 | `class` |
| KW_EXTENDS | 103 | `extends` |
| KW_SUPER | 104 | `super` |
| KW_STATIC | 105 | `static` |

#### Special
| Token | Value | Description |
|-------|-------|-------------|
| EOF | 199 | End of input |

### 2.3 Token Structure

Each token occupies 32 bytes in the token pool:

```
Offset 0:  type    (8 bytes, integer — one of the JSTokType values)
Offset 8:  start   (8 bytes, integer — byte offset in source)
Offset 16: length  (8 bytes, integer — token byte length)
Offset 24: extra   (8 bytes, integer — for NUMBER: integer value; for STRING: string length)
```

### 2.4 Lexing Algorithm

The lexer operates via a single-pass character scanner:

1. **Skip whitespace and comments** — single-line (`//`), multi-line (`/* */`)
2. **Identify token class** by first character:
   - Letter/`_`/`$` → scan identifier or keyword
   - Digit → scan number
   - `'` or `"` → scan string
   - Operator character → scan operator (1-3 char lookahead for `===`, `>>>=`, etc.)
   - Punctuation → single-char token
3. **Keyword lookup** — identifiers are checked against a sorted keyword table
4. **Store token** in token pool, advance position

### 2.5 Key Functions

| Function | Purpose |
|----------|---------|
| `JSLex_Init()` | Allocate token pool (8,192 × 32 bytes) and string buffer |
| `JSLex_Reset()` | Clear token count and position for re-lexing |
| `JSLex_Tokenize(src, len)` | Main entry point — returns token count |
| `JSLex_GetType(idx)` | Return token type at position `idx` |
| `JSLex_GetStart(idx)` | Return byte offset of token at `idx` |
| `JSLex_GetLen(idx)` | Return byte length of token at `idx` |
| `JSLex_GetExtra(idx)` | Return extra data (number value or string length) |
| `JSLex_GetText(idx)` | Return pointer to token text in source buffer (null-terminated) |
| `JSLex_Peek()` | Return type of current token without advancing |
| `JSLex_Advance()` | Move to next token, return its type |
| `JSLex_Expect(type)` | Assert current token type, advance if matched |
| `JSLex_Match(type)` | Check if current token matches type |

### 2.6 Limitations

- Numbers are integer-only (no decimal, no exponent notation yet — IEEE 754 doubles planned)
- No template literal token type (backtick strings — planned Phase 1D)
- No private field token (`#ident` — planned Phase 3A)
- No async/await tokens (planned Phase 2)
- Regex literals not yet tokenized (planned Phase 5F)
- No BigInt or Symbol tokens

---

## 3. JSParser — Recursive-Descent Parser

### 3.1 Overview

`Library.JSParser.ailang` (4,967 lines) is the largest component. It consumes the flat token stream from JSLexer and constructs an Abstract Syntax Tree (AST) using recursive descent with Pratt precedence climbing for expressions.

### 3.2 AST Node Types (~55)

| Type | Value | Description |
|------|-------|-------------|
| PROGRAM | 1 | Root of every parse tree |
| BLOCK | 2 | `{ ... }` block statement |
| VAR_DECL | 3 | Variable declaration (var/let/const) |
| FUNC_DECL | 4 | Function declaration |
| RETURN_STMT | 5 | `return expr` |
| IF_STMT | 6 | `if (cond) body [else alt]` |
| WHILE_STMT | 7 | `while (cond) body` |
| FOR_STMT | 8 | `for (init; test; update) body` |
| BREAK_STMT | 9 | `break` |
| CONTINUE_STMT | 10 | `continue` |
| EXPR_STMT | 11 | Expression statement |
| ASSIGN | 12 | `lhs = rhs` (and compound) |
| BINARY_OP | 13 | `a + b`, `a * b`, etc. |
| UNARY_OP | 14 | `!expr`, `-expr`, `typeof expr` |
| CALL | 15 | `f(args)` |
| MEMBER_DOT | 16 | `obj.prop` |
| MEMBER_BRACKET | 17 | `obj[expr]` |
| IDENT | 18 | Identifier reference |
| NUMBER_LIT | 19 | Numeric literal |
| STRING_LIT | 20 | String literal |
| BOOL_LIT | 21 | `true` / `false` |
| NULL_LIT | 22 | `null` |
| UNDEF_LIT | 23 | `undefined` |
| OBJECT_LIT | 24 | `{ key: val, ... }` |
| ARRAY_LIT | 25 | `[elem, ...]` |
| PROPERTY | 26 | Key-value pair in object literal |
| FUNC_EXPR | 27 | Function expression |
| TERNARY | 28 | `cond ? then : else` |
| UPDATE_EXPR | 29 | `++x` / `x++` / `--x` / `x--` |
| TYPEOF_EXPR | 30 | `typeof expr` |
| NEW_EXPR | 31 | `new Constructor(args)` |
| THIS_EXPR | 32 | `this` |
| DO_WHILE | 33 | `do body while (cond)` |
| SWITCH_STMT | 34 | `switch (expr) { cases }` |
| CASE_CLAUSE | 35 | `case val:` / `default:` |
| TRY_STMT | 36 | `try { } catch(e) { } finally { }` |
| THROW_STMT | 37 | `throw expr` |
| COMPUTED_PROP | 38 | `[expr]: value` in object literal |
| GETTER_PROP | 39 | `get name() { ... }` |
| SETTER_PROP | 40 | `set name(val) { ... }` |
| FOR_IN_STMT | 41 | `for (key in obj) body` |
| ARRAY_PATTERN | 42 | Destructuring array pattern |
| OBJECT_PATTERN | 43 | Destructuring object pattern |
| REST_ELEMENT | 44 | `...rest` in destructuring |
| LABELED_STMT | 45 | `label: statement` |
| SPREAD_ELEMENT | 46 | `...expr` in array/object/call |
| ARROW_EXPR | 47 | `(params) => body` |
| YIELD_EXPR | 48 | `yield [expr]` |
| GEN_FUNC_DECL | 49 | `function* name()` |
| GEN_FUNC_EXPR | 50 | `function*()` |
| CLASS_DECL | 51 | `class Name { ... }` |
| CLASS_EXPR | 52 | `class { ... }` |
| SUPER_EXPR | 53 | `super()` / `super.prop` |
| FOR_OF_STMT | 54 | `for (val of iterable) body` |
| CLASS_FIELD | 55 | Class field declaration |

### 3.3 AST Node Structure (80 bytes)

```
Offset  0: type       (8 bytes — ASTType value)
Offset  8: op         (8 bytes — operator token type for BINARY_OP/ASSIGN/UNARY_OP)
Offset 16: left       (8 bytes — left child node index or 0)
Offset 24: right      (8 bytes — right child node index or 0)
Offset 32: cond       (8 bytes — condition/init/extra child)
Offset 40: body       (8 bytes — body/update/alternate child)
Offset 48: name_ptr   (8 bytes — pointer to identifier name string)
Offset 56: name_len   (8 bytes — length of identifier name)
Offset 64: value      (8 bytes — numeric value or general-purpose)
Offset 72: next       (8 bytes — next sibling in linked list)
```

Nodes are allocated from a pool of 16,384 entries (1.28 MB). Children are linked via indices into this pool. The `next` field forms a singly-linked list of siblings within a parent (e.g., statements in a block, elements in an array).

### 3.4 Pratt Precedence Climbing

Binary expression parsing uses **Pratt precedence climbing** rather than a traditional precedence table. This is implemented as a recursive function that:

1. Parses a prefix expression (atom, unary, grouping)
2. Enters a loop: while the current token is a binary operator with precedence ≥ the minimum:
   - Consume the operator
   - Recursively parse the right-hand side at higher precedence
   - Combine left and right into a BINARY_OP node

Precedence levels are hardcoded as integer thresholds in the algorithm:

```
Precedence levels (higher number = tighter binding):
  1:  Assignment (=, +=, -=, etc.) — right-associative
  2:  Conditional (?:)
  3:  Nullish coalescing (??)
  4:  Logical OR (||)
  5:  Logical AND (&&)
  6:  Bitwise OR (|)
  7:  Bitwise XOR (^)
  8:  Bitwise AND (&)
  9:  Equality (==, !=, ===, !==)
  10: Relational (<, >, <=, >=, instanceof, in)
  11: Bitwise shift (<<, >>, >>>)
  12: Additive (+, -)
  13: Multiplicative (*, /, %)
  14: Exponentiation (**) — right-associative
  15: Prefix (unary -, !, ~, typeof, void, delete)
  16: Postfix (++, --)
  17: Member access (., [])
  18: Call (())
```

### 3.5 Statement Parsing

The parser uses a classic recursive-descent approach for statements:

```
ParseStatement():
  match token:
    KW_VAR/KW_LET/KW_CONST → ParseVariableDeclaration()
    KW_FUNCTION            → ParseFunctionDeclaration()
    KW_IF                  → ParseIfStatement()
    KW_WHILE               → ParseWhileStatement()
    KW_FOR                 → ParseForStatement()
    KW_DO                  → ParseDoWhile()
    KW_SWITCH              → ParseSwitch()
    KW_TRY                 → ParseTry()
    KW_THROW               → ParseThrow()
    KW_RETURN              → ParseReturn()
    KW_BREAK               → ParseBreak()
    KW_CONTINUE            → ParseContinue()
    KW_CLASS               → ParseClassDeclaration()
    LBRACE                 → ParseBlock()
    SEMI                   → empty statement
    IDENT (followed by :)  → ParseLabeledStatement()
    default                → ParseExpressionStatement()
```

### 3.6 Clobber Safety

The parser uses `ASTTmp` — a global pool of temporaries that are overwritten by recursive calls. An `ASTStack` push/pop mechanism saves and restores critical values:

```
Before recursive call:
  AST__Push(ASTTmp.idx)
  AST__Push(ASTTmp.node)
  result = ParseSubExpression()
  ASTTmp.node = AST__Pop()
  ASTTmp.idx = AST__Pop()
```

The push/pop stack uses 8-byte entries allocated from a pooled buffer.

### 3.7 Key Functions

| Function | Purpose |
|----------|---------|
| `JSParse_Init()` | Allocate AST node pool (16,384 × 80 bytes) and push/pop stack |
| `JSParse_Parse()` | Main entry point — returns root PROGRAM node index |
| `JSParse_HasError()` | Check parse error flag |
| `JSParse_GetType(node)` | Return AST node type |
| `JSParse_GetOp(node)` | Return operator token type for operator nodes |
| `JSParse_GetLeft(node)` | Return left child index |
| `JSParse_GetRight(node)` | Return right child index |
| `JSParse_GetName(node)` | Return name pointer for IDENT/FUNC_DECL/etc. |
| `JSParse_GetNameLen(node)` | Return name length |

### 3.8 Limitations

- No destructuring in parameters (3,552 test failures — planned Phase 1)
- No private field parsing (`#field` — planned Phase 3A)
- No async/await syntax (planned Phase 2)
- No template literal parsing (planned Phase 1D)
- No module syntax (`import`/`export` — planned Phase 5D)
- Class field declarations partially supported (parser handles but compiler doesn't)

---

## 4. JSValidate — Truth-Table Validator

### 4.1 Overview

`Library.JSValidate.ailang` (209 lines) implements a "watcher" that runs alongside the parser, providing zero-branch O(1) lookup validation via flat byte arrays indexed by token type or AST node type. This replaces what would otherwise be cascading `if/else` chains or `switch` statements.

### 4.2 Truth Tables

Four flat byte arrays, each 0 = illegal, 1 = legal:

#### Table 1: `assign_target` — Valid Assignment LHS (AST node types)

| AST Type | Value | Valid |
|----------|-------|-------|
| IDENT | 18 | Yes |
| MEMBER_DOT | 16 | Yes |
| MEMBER_BRACKET | 17 | Yes |
| ARRAY_LIT | 25 | Yes (cover grammar → ARRAY_PATTERN) |
| OBJECT_LIT | 24 | Yes (cover grammar → OBJECT_PATTERN) |
| ARRAY_PATTERN | 42 | Yes |
| OBJECT_PATTERN | 43 | Yes |

All other node types return 0 (not a valid L-value).

#### Table 2: `postfix_target` — Valid ++/-- Targets

Same as assign_target but restricted to: IDENT, MEMBER_DOT, MEMBER_BRACKET (types 18, 16, 17). Destructuring patterns cannot be postfix targets.

#### Table 3: `stmt_start` — Tokens That Can Begin a Statement

Covers keywords (`var`, `let`, `const`, `function`, `return`, `if`, `while`, `for`, `break`, `continue`, `do`, `switch`, `try`, `throw`, `delete`, `typeof`, `void`, `new`, `class`), punctuation (`{`, `;`), and expression starters (IDENT, NUMBER, STRING, `(`, `[`, `-`, `+`, `!`, `~`, `++`, `--`, `true`, `false`, `null`, `undefined`, `this`).

#### Table 4: `expr_start` — Tokens That Can Start an Expression

Covers all expression-starting atoms and prefix operators: IDENT, NUMBER, STRING, `true`, `false`, `null`, `undefined`, `this`, unary operators (`-`, `+`, `!`, `~`, `++`, `--`, `typeof`, `void`, `delete`), `new`, `(`, `[`, `{`, `function`, `class`, `super`.

### 4.3 Lookup Algorithm

```
validate = GetByte(table_ptr, token_type_or_node_type)
if validate == 1: legal
else:             illegal → set parse error
```

The byte arrays are sized to 256 entries (token types) or 64 entries (AST types) and initialized in `JSValidate_Init()`.

### 4.4 Public API

| Function | Signature | Purpose |
|----------|-----------|---------|
| `JSValidate_Init()` | `→ Integer` | Allocate and populate all four tables |
| `JSValidate_IsLValue(ntype)` | `Integer → Integer` | Check if AST node type is valid assignment target |
| `JSValidate_IsPostfixTarget(ntype)` | `Integer → Integer` | Check if AST node type is valid ++/-- target |
| `JSValidate_CanStartExpr(tok)` | `Integer → Integer` | Check if token type can start expression |
| `JSValidate_CanStartStmt(tok)` | `Integer → Integer` | Check if token type can start statement |

---

## 5. JSCompiler — AST-to-Bytecode Compiler

### 5.1 Overview

`Library.JSCompiler.ailang` (3,927 lines) walks the AST produced by JSParser and emits a flat bytecode stream plus a constant pool. The target is a stack-based virtual machine — there is no register allocation. Each opcode is 1 byte, followed by 0-2 bytes of big-endian operands.

### 5.2 Opcode Set (~75 opcodes)

#### Stack Operations

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| HALT | 0 | — | Stop execution |
| PUSH_CONST | 1 | → val | Push constant from pool (2-byte index) |
| PUSH_UNDEF | 2 | → undef | Push undefined |
| PUSH_NULL | 3 | → null | Push null |
| PUSH_TRUE | 4 | → true | Push true |
| PUSH_FALSE | 5 | → false | Push false |
| POP | 6 | val → | Discard top of stack |
| DUP | 7 | val → val,val | Duplicate top of stack |
| CONCAT | 62 | s1,s2 → s | Concatenate two strings |
| NOP | 99 | — | No operation |

#### Variable Operations

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| GET_LOCAL | 10 | → val | Load local variable (1-byte slot) |
| SET_LOCAL | 11 | val → | Store to local variable (1-byte slot) |
| GET_GLOBAL | 12 | → val | Load global by name (2-byte const index) |
| SET_GLOBAL | 13 | val → | Store to global by name (2-byte const index) |

#### Property Operations

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| GET_PROP | 16 | obj → val | Property access by name (2-byte const index) |
| SET_PROP | 17 | obj,val → | Property store by name (2-byte const index) |
| GET_ELEM | 18 | obj,key → val | Computed property access |
| SET_ELEM | 19 | obj,key,val → | Computed property store |
| SET_PROP_COMPUTED | 63 | obj,key,val → | Computed property definition |

#### Arithmetic Operations

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| ADD | 20 | a,b → a+b | Addition |
| SUB | 21 | a,b → a-b | Subtraction |
| MUL | 22 | a,b → a*b | Multiplication |
| DIV | 23 | a,b → a/b | Integer division |
| MOD | 24 | a,b → a%b | Modulo |
| NEG | 25 | a → -a | Unary negation |
| EXP | 26 | a,b → a**b | Exponentiation (integer) |

#### Comparison Operations

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| EQ | 30 | a,b → bool | Abstract equality (==) |
| NEQ | 31 | a,b → bool | Abstract inequality (!=) |
| LT | 32 | a,b → bool | Less than |
| GT | 33 | a,b → bool | Greater than |
| LTE | 34 | a,b → bool | Less than or equal |
| GTE | 35 | a,b → bool | Greater than or equal |
| STRICT_EQ | 36 | a,b → bool | Strict equality (===) |
| STRICT_NEQ | 37 | a,b → bool | Strict inequality (!==) |

#### Logic and Bitwise

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| NOT | 40 | a → !a | Logical NOT |
| BIT_AND | 41 | a,b → a&b | Bitwise AND |
| BIT_OR | 42 | a,b → a\|b | Bitwise OR |
| BIT_XOR | 43 | a,b → a^b | Bitwise XOR |
| BIT_NOT | 44 | a → ~a | Bitwise NOT |
| SHL | 45 | a,b → a<<b | Left shift |
| SHR | 46 | a,b → a>>b | Signed right shift |
| USHR | 48 | a,b → a>>>b | Unsigned right shift |
| TYPEOF | 47 | a → string | Typeof operator |
| IN | 38 | a,b → bool | `in` operator |
| INSTANCEOF | 49 | a,b → bool | `instanceof` operator |

#### Control Flow

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| JMP | 50 | — | Unconditional jump (2-byte offset) |
| JMP_FALSE | 51 | cond → | Jump if false (2-byte offset) |
| JMP_TRUE | 52 | cond → | Jump if true (2-byte offset) |
| JMP_NULLISH | 53 | val → val | Jump if null/undefined, keep on stack (??) |
| RETURN | 56 | val → | Return from function |
| HALT | 0 | — | Implicit return (end of code) |

#### Function Operations

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| CALL | 55 | fn,args... → result | Call function (1-byte arg count) |
| CALL_SPREAD | 69 | fn,arr → result | Call with spread arguments |
| CLOSURE | 57 | → fn | Create closure (2-byte func index) |
| GEN_CLOSURE | 74 | → gen | Create generator closure |
| YIELD | 73 | val → | Yield from generator |

#### Object Operations

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| NEW_OBJECT | 60 | → obj | Create empty object |
| NEW_ARRAY | 61 | → arr | Create empty array |
| SET_PROP_COMPUTED | 63 | obj,key,val → | Computed property assignment |
| DEF_GETTER | 64 | obj,name,fn → | Define getter |
| DEF_SETTER | 65 | obj,name,fn → | Define setter |
| DEF_GETTER_COMPUTED | 76 | obj,key,fn → | Computed getter |
| DEF_SETTER_COMPUTED | 77 | obj,key,fn → | Computed setter |
| OBJ_KEYS | 66 | obj → arr | Object.keys() |
| ARR_APPEND | 67 | arr,val → arr | Append to array |
| ARR_EXTEND | 68 | arr1,arr2 → arr1 | Extend array with another |

#### Exception Handling

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| TRY_PUSH | 70 | handler_addr → | Push exception handler |
| TRY_POP | 71 | → | Pop exception handler |
| THROW | 72 | val → | Throw exception |

#### Iteration

| Opcode | Value | Stack Effect | Description |
|--------|-------|-------------|-------------|
| TO_ARRAY | 75 | iterable → arr | Convert iterable to array (eager) |

### 5.3 Bytecode Format

Instructions are variable-length:

- **1 byte:** Opcode only (e.g., HALT, ADD, POP, RETURN)
- **2 bytes:** Opcode + 1-byte operand (e.g., GET_LOCAL slot, CALL arity)
- **3 bytes:** Opcode + 2-byte big-endian operand (e.g., PUSH_CONST index, JMP offset, GET_GLOBAL const_index, CLOSURE func_index)

The bytecode is stored as a flat byte array. The constant pool stores string values, number values, and function bytecode references.

### 5.4 Compilation Passes

#### Pass 1: AST Walk (JSComp_Compile)
Recursive tree walk of the AST. Each node type has a handler that emits the appropriate opcode sequence:

```
JSComp_Compile(node):
  switch (node_type):
    PROGRAM:        compile each child statement in order
    BLOCK:          compile each child; emit scope management
    VAR_DECL:       compile initializer; emit SET_LOCAL/SET_GLOBAL
    FUNC_DECL:      compile function body into separate bytecode; register in constant pool
    RETURN_STMT:    compile expression; emit RETURN
    IF_STMT:        compile condition; emit JMP_FALSE with patch; compile then/else; patch jump
    WHILE_STMT:     mark loop start; compile condition; JMP_FALSE to exit; compile body; JMP to start; patch exit
    FOR_STMT:       compile init; mark start; compile test; JMP_FALSE to exit; compile body; compile update; JMP to start; patch exit
    ASSIGN:         compile rhs; compile lhs as target; emit SET_LOCAL/SET_GLOBAL/SET_PROP/SET_ELEM
    BINARY_OP:      compile left; compile right; emit arithmetic/comparison opcode
    UNARY_OP:       compile operand; emit NEG/NOT/BIT_NOT/TYPEOF
    CALL:           compile args; compile callee; emit CALL
    MEMBER_DOT:     compile object; emit GET_PROP
    MEMBER_BRACKET: compile object; compile key; emit GET_ELEM
    IDENT:          resolve scope; emit GET_LOCAL or GET_GLOBAL
    NUMBER_LIT:     store in constant pool; emit PUSH_CONST
    STRING_LIT:     store in constant pool; emit PUSH_CONST
    OBJECT_LIT:     emit NEW_OBJECT; for each property: compile key, compile value, emit SET_PROP/DEF_GETTER/DEF_SETTER
    ARRAY_LIT:      emit NEW_ARRAY; for each element: compile value, emit ARR_APPEND
    TERNARY:        compile condition; emit JMP_FALSE; compile then; JMP to end; patch JMP_FALSE; compile else; patch end
    ...
```

#### Pass 2: Jump Patching
After the initial walk, forward jump targets are resolved. During compilation, placeholder offsets are emitted and stored in a patch table. After the full bytecode is emitted, all jump offsets are back-patched with correct positions.

#### Pass 3: Scope Resolution
Variables are resolved to local slots or global names. The compiler maintains a scope chain stack with local variable tables for each block/function scope.

### 5.5 Scoped Variable Resolution

The compiler maintains scope information using XSHash tables:

- **Global scope:** Variables declared at the top level or without `var`/`let`/`const` go into the global hash. Emitted as GET_GLOBAL/SET_GLOBAL with constant pool index for the name.
- **Local scope:** Variables declared with `var` (function-scoped) or `let`/`const` (block-scoped) are assigned sequential slot indices within the current function/block. Emitted as GET_LOCAL/SET_LOCAL with slot indices.

Functions receive their own scope, and closures capture variables from enclosing scopes.

### 5.6 Function Compilation

Each function (declaration or expression) is compiled as a separate bytecode unit:

1. The function body is compiled independently
2. Parameters become local slots (0, 1, 2, ...)
3. The compiled bytecode is stored in the constant pool
4. At runtime, `CLOSURE` or `GEN_CLOSURE` creates a function object referencing this bytecode
5. When called, `CALL` pushes a new call frame and begins executing the function's bytecode

### 5.7 Key API

| Function | Signature | Purpose |
|----------|-----------|---------|
| `JSComp_Init()` | `→ Integer` | Allocate bytecode buffer, constant pool, patch table |
| `JSComp_Reset()` | `→` | Clear all compilation state |
| `JSComp_Compile(ast_root)` | `Integer → Integer` | Compile AST → bytecode (returns 1 on success) |
| `JSComp_GetCode()` | `→ Address` | Get compiled bytecode pointer |
| `JSComp_GetCodeLen()` | `→ Integer` | Get bytecode length |
| `JSComp_GetConst(idx)` | `Integer → Address` | Get constant pool entry |
| `JSComp_GetConstCount()` | `→ Integer` | Get constant pool entry count |

---

## 6. JSRuntime — Value System & Type Coercion

### 6.1 Overview

`Library.JSRuntime.ailang` (3,370 lines) manages all JavaScript values: creation, type checking, coercion (ToNumber, ToString, ToBool), comparison semantics (strict and abstract equality), native function dispatch, and the timer queue. It is the runtime backbone that JSVM calls into for all value-manipulation operations.

### 6.2 Type System

Nine value types, encoded as integers:

| Type | Value | Description |
|------|-------|-------------|
| UNDEFINED | 0 | Single `undefined` sentinel |
| NULL | 1 | Single `null` sentinel |
| BOOLEAN | 2 | `true` or `false` |
| NUMBER | 3 | Integer (IEEE 754 double planned) |
| STRING | 4 | UTF-8 byte sequence |
| OBJECT | 5 | Property bag (XSHash) |
| FUNCTION | 6 | Callable with bytecode + captured scope |
| ARRAY | 7 | Indexed collection with length |
| GENERATOR | 8 | Suspendable function with saved state |

### 6.3 JSValue Structure (16 bytes)

All values are represented by 16-byte records allocated from a pool of 8,192 entries:

```
Offset  0: type    (8 bytes, JSType value)
Offset  8: payload (8 bytes, type-dependent)
```

Payload interpretation by type:

| Type | Payload Contents |
|------|-----------------|
| UNDEFINED | Unused (0) |
| NULL | Unused (0) |
| BOOLEAN | 0 = false, 1 = true |
| NUMBER | Integer value |
| STRING | Pointer to null-terminated byte string |
| OBJECT | Pointer to XSHash (property hash map) |
| FUNCTION | Pointer to function descriptor (48 bytes) |
| ARRAY | Pointer to XArray (dynamic array of JSValues) |
| GENERATOR | Pointer to generator state block (104 bytes) |

### 6.4 Sentinel Values

Five canonical values are pre-allocated at init and never freed:

| Sentinel | Purpose |
|----------|---------|
| `JSRTState.undef_val` | The `undefined` value |
| `JSRTState.null_val` | The `null` value |
| `JSRTState.true_val` | The `true` boolean |
| `JSRTState.false_val` | The `false` boolean |
| `JSRT_Undefined()` | Public accessor for undefined sentinel |

### 6.5 Function Descriptor (48 bytes)

```
Offset  0: bc_ptr    (8 bytes — pointer to bytecode)
Offset  8: bc_len    (8 bytes — bytecode length)
Offset 16: name_ptr  (8 bytes — function name string)
Offset 24: name_len  (8 bytes — name length)
Offset 32: scope     (8 bytes — captured scope XSHash pointer)
Offset 40: arity     (8 bytes — parameter count)
```

### 6.6 Generator State Block (104 bytes)

```
Offset  0:  pc       (8 bytes — saved program counter)
Offset  8:  sp       (8 bytes — saved value stack pointer)
Offset 16:  fp       (8 bytes — saved frame pointer)
Offset 24:  locals   (8 bytes — pointer to saved local variable array)
Offset 32:  stack    (8 bytes — pointer to saved value stack)
Offset 40:  frames   (8 bytes — pointer to saved call frames)
Offset 48:  state    (8 bytes — 0=suspended, 1=executing, 2=closed)
Offset 56:  ret_val   (8 bytes — last yielded value)
Offset 64-103:       Reserved
```

### 6.7 Type Coercion

#### ToBoolean
```
undefined → false
null      → false
boolean   → as-is
number    → 0 is false, everything else true
string    → "" is false, everything else true
object    → true
array     → true
function  → true
```

#### ToNumber
```
undefined → 0
null      → 0
boolean   → 0 or 1
number    → as-is
string    → integer parse (decimal only currently)
```

#### ToString
```
undefined → "undefined"
null      → "null"
boolean   → "true" or "false"
number    → decimal string representation
string    → as-is
object    → "[object Object]"
array     → comma-joined elements
function  → "function name() { ... }"
```

### 6.8 Strict Equality (===)

Algorithm:
1. If types differ → false
2. If type is UNDEFINED or NULL → true
3. If type is BOOLEAN → compare values
4. If type is NUMBER → compare integers
5. If type is STRING → byte-by-byte comparison
6. If type is OBJECT/ARRAY/FUNCTION → compare pointers (reference identity)

### 6.9 Abstract Equality (==)

Algorithm (ECMAScript-style):
1. If types are the same → delegate to strict equality
2. If null == undefined → true
3. If number == string → ToNumber(string) then compare
4. If boolean == anything → ToNumber(boolean) then compare
5. If object/array/function == string/number → ToPrimitive(object) then compare

### 6.10 Native Function Dispatch

Up to 64 native functions can be registered in the `native_table`. Each entry is 24 bytes:

```
Offset  0: name_ptr  (8 bytes — function name)
Offset  8: handler   (8 bytes — native handler index/ID)
Offset 16: arity     (8 bytes — expected argument count)
```

Native functions are invoked by the VM via `JSRT_CallNative(handler_id, arg_count, args...)`. The negative bytecode offset convention is: `bc_off = -(handler_id + 1)`, allowing the VM to distinguish native calls from bytecode calls with a single sign check.

Built-in natives (registered in `JSVM_InstallBuiltins`):

| Native | Handler ID |
|--------|-----------|
| console.log | 0 |
| Math.abs | 1 |
| Math.max | 2 |
| Math.min | 3 |
| Math.floor | 4 |
| Math.random | 5 |
| isNaN | 6 |
| parseInt | 7 |
| parseFloat | 8 |
| isFinite | 9 |
| String.fromCharCode | 10 |
| Date.now | 11 |
| JSON.stringify | 12 |
| JSON.parse | 13 |
| Array.prototype.push | 14 |
| Array.prototype.pop | 15 |
| Array.prototype.shift | 16 |
| Array.prototype.unshift | 17 |
| Array.prototype.slice | 18 |
| Array.prototype.splice | 19 |
| String.prototype.charAt | 20 |
| String.prototype.indexOf | 21 |

### 6.11 Timer Queue

Up to 32 timer entries, each 32 bytes:

```
Offset  0: id         (8 bytes — timer ID, assigned sequentially from 1)
Offset  8: callback   (8 bytes — JSValue function pointer)
Offset 16: fire_at    (8 bytes — absolute millisecond time to fire)
Offset 24: interval   (8 bytes — 0 = setTimeout, >0 = setInterval repeat ms)
```

Functions:
- `JSRT_SetTimeout(callback, delay_ms)` → timer ID
- `JSRT_SetInterval(callback, interval_ms)` → timer ID
- `JSRT_ClearTimer(id)` → 1 if found, 0 if not
- `JSRT_GetExpiredTimers(current_ms)` → array of expired timer callbacks

---

## 7. JSVM — Bytecode Virtual Machine

### 7.1 Overview

`Library.JSVM.ailang` (2,297 lines) is a stack-based bytecode interpreter. It maintains a value stack, a call frame stack, a global variable hash, and executes compiled bytecode from JSCompiler. Its dispatch loop is patterned after the CPU6502 emulator in the same codebase — a branch (switch) dispatch over ~75 opcodes.

### 7.2 VM State

```
JSVMState:
  stack        → value stack buffer (4096 entries × 8 bytes = 32 KB)
  sp           → stack pointer (index into stack)
  frames       → call frame buffer (256 frames × 40 bytes = ~10 KB)
  fp           → frame pointer (index into frames)
  code         → pointer to current bytecode
  code_len     → length of current bytecode
  pc           → program counter (byte offset into code)
  const_pool   → pointer to constant pool
  const_count  → number of constants
  globals      → pointer to global XSHash
  halted       → 1 when execution stopped
  error        → 1 when runtime error occurred
  steps        → instruction counter
  max_steps    → execution limit (default 1,000,000)
  exc_stack    → exception handler stack
  exc_sp       → exception handler stack pointer
```

### 7.3 Value Stack

The value stack holds JSValue pointers (8 bytes each). Maximum depth is 4,096 entries. Operations:

| Function | Effect |
|----------|--------|
| `JSVM__Push(val)` | sp++; stack[sp] = val |
| `JSVM__Pop()` | return stack[sp--] |
| `JSVM__Peek(n)` | return stack[sp - n] (0 = top) |
| `JSVM__Drop(n)` | sp -= n |

All arithmetic, comparison, and logic operations pop their operands from the stack and push results back.

### 7.4 Call Frames (40 bytes each)

```
Offset  0: return_pc    (8 bytes — saved program counter after call)
Offset  8: return_sp    (8 bytes — saved stack pointer before args were pushed)
Offset 16: func_obj     (8 bytes — pointer to function JSValue)
Offset 24: locals       (8 bytes — pointer to local variable array)
Offset 32: scope        (8 bytes — pointer to closure scope XSHash)
```

When a function is called:
1. Arguments are already on the value stack
2. A new frame is allocated at `frames[fp]`
3. `fp` is incremented
4. Local slots are extracted from the stack arguments
5. `pc` is set to the function's bytecode start

When a function returns:
1. Return value is left on the value stack (after cleaning locals)
2. `fp` is decremented
3. `pc` is restored to `return_pc`
4. Execution continues in the caller

### 7.5 Dispatch Loop

The core execution loop (simplified):

```
While halted == 0 AND steps < max_steps:
  opcode = code[pc]
  pc++
  steps++
  
  switch (opcode):
    case PUSH_CONST:
      index = read_uint16_be(code + pc); pc += 2
      push(const_pool[index])
    
    case ADD:
      b = pop(); a = pop()
      push(JSRT_Add(a, b))
    
    case GET_LOCAL:
      slot = code[pc]; pc++
      push(JSRT_GetLocal(current_frame, slot))
    
    case SET_LOCAL:
      slot = code[pc]; pc++
      val = pop()
      JSRT_SetLocal(current_frame, slot, val)
    
    case CALL:
      arity = code[pc]; pc++
      fn = stack[sp - arity]  // function is below its arguments
      if is_native(fn):
        result = JSRT_CallNative(fn, arity, &stack[sp - arity + 1])
        sp -= arity  // pop args
        push(result)
      else:
        // Set up new call frame, transfer control
        push_frame(fn, arity)
    
    case JMP:
      offset = read_int16_be(code + pc); pc += 2
      pc += offset
    
    case JMP_FALSE:
      offset = read_int16_be(code + pc); pc += 2
      cond = pop()
      if JSRT_ToBool(cond) == false: pc += offset
    
    case RETURN:
      val = pop()
      pop_frame()
      push(val)
    
    case HALT:
      halted = 1

    // ... ~65 more cases

  // Exception handler check after each opcode
```

### 7.6 Exception Handling

The VM supports try/catch via an exception handler stack:

- `TRY_PUSH handler_offset`: Push a handler address onto `exc_stack`
- `TRY_POP`: Pop the current handler
- `THROW`: Pop the exception value, then:
  1. Walk `exc_stack` to find the nearest handler
  2. Restore `sp` to pre-try state
  3. Push the exception value
  4. Jump to the handler address

### 7.7 Generator Execution

Generators use a snapshot/restore mechanism:

- `GEN_CLOSURE`: Creates a generator function object
- On first `.next()`: Execute normally until `YIELD`
- `YIELD`: Save entire VM state (pc, sp, fp, locals, stack, frames) into the generator state block, return the yielded value to caller
- On subsequent `.next()`: Restore VM state from generator state block, resume execution after the YIELD opcode
- On `return` from generator body: Set generator state to "closed"

Generator state tracking is done via `JSVMGen`:

```
JSVMGen:
  active_gs      → pointer to currently executing generator state
  active_genval  → the generator JSValue
  caller_pc      → saved PC of the caller who invoked .next()
  caller_sp      → saved stack pointer of caller
  caller_fp      → saved frame pointer of caller
  is_gen_exec    → 1 when generator body is running on the VM stack
```

### 7.8 Step Limit

A safety mechanism prevents infinite loops:

- `max_steps` defaults to 1,000,000 (overridable via JSVM_SetMaxSteps)
- Before each opcode execution, `steps` is checked against `max_steps`
- If exceeded, `error` is set to 1 and execution halts
- The MCP tool exposes this as the `max_steps` parameter (default 5,000,000)

### 7.9 Global Variables

The `globals` XSHash maps string names to JSValue pointers. Operations:

| Function | Purpose |
|----------|---------|
| `JSVM_SetGlobal(name, value)` | Define or overwrite a global variable |
| `JSVM_GetGlobal(name)` | Look up a global by name |
| `JSVM_HasGlobal(name)` | Check if global exists |
| `JSVM_InstallBuiltins()` | Register all built-in natives and objects |

### 7.10 Key API

| Function | Signature | Purpose |
|----------|-----------|---------|
| `JSVM_Init()` | `→ Integer` | Allocate stacks, frames, global hash, exception stack |
| `JSVM_Reset()` | `→` | Clear stacks, frames, halt/error flags, step counter |
| `JSVM_Load(code, len, const_pool, const_count)` | `A,I,A,I →` | Load bytecode for execution |
| `JSVM_Run()` | `→ Address` | Execute until HALT or error, return top-of-stack value |
| `JSVM_Eval(source, len)` | `A,I → Address` | Lex→Parse→Compile→Load→Run in one call |
| `JSVM_GetError()` | `→ Integer` | Check if runtime error occurred |
| `JSVM_GetSteps()` | `→ Integer` | Get executed instruction count |
| `JSVM_SetMaxSteps(n)` | `I →` | Set execution step limit |
| `JSVM_SetGlobal(name, val)` | `A,A →` | Register a global variable |
| `JSVM_GetGlobal(name)` | `A → Address` | Look up a global variable |
| `JSVM_InstallBuiltins()` | `→` | Register all native functions and objects |

---

## 8. JSBridge — DOM Bindings

### 8.1 Overview

`Library.JSBridge.ailang` (2,073 lines) connects the JSVM to the HTML DOM system. It creates JavaScript wrapper objects for DOM elements, registers native functions that the VM can call, dispatches native calls to the appropriate DOM/Runtime functions, manages event listeners, and provides timer integration.

### 8.2 Architecture

```
JS Code (VM)
    │
    │ calls like: document.getElementById('foo')
    │             console.log('hello')
    │             element.addEventListener('click', handler)
    ▼
JSBridge (native dispatch)
    │
    │ routes by NativeID to:
    ▼
┌─────────────────────────────────────────────┐
│  HTMLDom functions                           │
│  DOM_GetByID, DOM_GetAttr, DOM_SetAttr,     │
│  DOM_AppendChild, DOM_GetInnerHTML, etc.     │
└─────────────────────────────────────────────┘
```

### 8.3 Native Function IDs (Handler 22+)

JSRuntime built-ins use handlers 0-21. Bridge natives start at 22:

| Native ID | Constant | Description |
|-----------|----------|-------------|
| 22 | CONSOLE_LOG | console.log(msg) |
| 23 | DOC_GET_BY_ID | document.getElementById(id) |
| 24 | DOC_QUERY_SEL | document.querySelector(sel) |
| 25 | DOC_CREATE_ELEM | document.createElement(tag) |
| 26 | ELEM_GET_ATTR | element.getAttribute(name) |
| 27 | ELEM_SET_ATTR | element.setAttribute(name, val) |
| 28 | ELEM_ADD_LISTENER | element.addEventListener(ev, cb) |
| 29 | ELEM_INNER_HTML_GET | element.innerHTML (getter) |
| 30 | ELEM_INNER_HTML_SET | element.innerHTML = val (setter) |
| 31 | ELEM_TEXT_CONTENT | element.textContent |
| 32 | ELEM_APPEND_CHILD | element.appendChild(child) |
| 33 | ELEM_REMOVE_CHILD | element.removeChild(child) |
| 34 | ELEM_STYLE_SET | element.style.prop = val |
| 35 | SET_TIMEOUT | setTimeout(cb, delay) |
| 36 | SET_INTERVAL | setInterval(cb, delay) |
| 37 | CLEAR_TIMEOUT | clearTimeout(id) |
| 38 | PARSE_INT | parseInt(str) |
| 39 | MATH_ABS | Math.abs(n) |
| 40 | MATH_MAX | Math.max(a, b) |
| 41 | MATH_MIN | Math.min(a, b) |
| 42 | MATH_FLOOR | Math.floor(n) |
| 43 | OBJ_DEFINE_PROP | Object.defineProperty() |
| 44 | OBJ_KEYS | Object.keys(obj) |
| 45 | OBJ_CREATE | Object.create(proto) |
| 46 | OBJ_GET_OWN_PROP_DESC | Object.getOwnPropertyDescriptor() |
| 47 | OBJ_GET_PROTO_OF | Object.getPrototypeOf() |
| 48 | OBJ_ASSIGN | Object.assign() |
| 49 | OBJ_FREEZE | Object.freeze() |
| 50 | OBJ_IS | Object.is() |
| 51 | OBJ_DEF_PROPERTIES | Object.defineProperties() |
| 52 | OBJ_ENTRIES | Object.entries() |
| 53 | OBJ_VALUES | Object.values() |
| 54 | OBJ_HAS_OWN_PROP | Object.hasOwnProperty() |
| 55 | ARR_IS_ARRAY | Array.isArray() |
| 56 | ARR_FROM | Array.from() |

### 8.4 DOM Node Wrapping

DOM nodes (integer indices into the HTMLDom tree) are wrapped in JS objects for use in script. The mapping is maintained in a DOM wrapper table:

```
Wrap entry (16 bytes):
  Offset 0: dom_idx  (8 bytes — DOM node index)
  Offset 8: js_obj   (8 bytes — JS object JSValue pointer)
```

Up to 512 DOM nodes can be wrapped simultaneously. Lookup is O(n) linear scan. When a JS object property represents a DOM element, the bridge unwraps it back to a DOM node index for native operations.

### 8.5 Event Listener System

Event listeners are registered via `addEventListener` and stored in a listener table:

```
Listener entry (24 bytes):
  Offset  0: dom_node       (8 bytes — DOM node index)
  Offset  8: event_name_ptr (8 bytes — pointer to event name string e.g. "click")
  Offset 16: callback_jsval (8 bytes — JS function JSValue pointer)
```

Up to 256 listeners can be registered. When a DOM event fires (`JSEngine_FireDOMEvent`):

1. Search the listener table for matching (dom_node, event_name) entries
2. For each match, push the callback onto the VM's execution stack
3. Execute via `JSVM_Run()` (wrapping the callback in a call expression)
4. The VM invokes the JavaScript handler function

### 8.6 Timer Integration

Timers registered through `setTimeout`/`setInterval` in JS code flow through:

```
JS: setTimeout(fn, 500)
  → JSBridge native dispatch (SET_TIMEOUT / SET_INTERVAL)
  → JSRT_SetTimeout(fn, 500) / JSRT_SetInterval(fn, 500)
  → Timer stored in JSRT timer_pool with fire_at = current_ms + delay

Browser main loop:
  → JSEngine_Tick(current_ms)
  → JSBridge_TickTimers(current_ms)
  → JSRT_GetExpiredTimers(current_ms)
  → For each expired timer:
      1. Push callback onto VM stack
      2. Invoke via JSVM (executing the callback with 0 args)
      3. If setInterval: re-register with fire_at += interval
      4. If setTimeout: remove from pool
```

### 8.7 Key API

| Function | Signature | Purpose |
|----------|-----------|---------|
| `JSBridge_Init(dom_root)` | `I → I` | Initialize bridge with DOM root |
| `JSBridge_GetDocObj()` | `→ A` | Get `document` JS object |
| `JSBridge_GetConsoleObj()` | `→ A` | Get `console` JS object |
| `JSBridge_GetMathObj()` | `→ A` | Get `Math` JS object |
| `JSBridge_TickTimers(ms)` | `I → I` | Dispatch expired timers |
| `JSBridge_FireEvent(node, name)` | `I,A → I` | Fire a DOM event |
| `JSBridge__CreateNativeFunc(id, name, arity)` | `I,A,I → A` | Create native function JSValue |
| `JSBridge__DispatchNative(handler_id, arg_count, args)` | `I,I,A → A` | Dispatch native call |

---

## 9. JSEngine — Orchestrator

### 9.1 Overview

`Library.JSEngine.ailang` (902 lines) is the top-level controller. It wires together all JS subsystems (JSLexer, JSParser, JSCompiler, JSRuntime, JSVM, JSBridge), extracts `<script>` tags from the DOM tree, feeds each through the compilation pipeline, provides per-frame timer dispatch, and handles DOM events.

### 9.2 Initialization

`JSEngine_Init()` performs initialization in strict dependency order:

```
1. Allocate script pool    (32 × 16 = 512 bytes)
2. Allocate string buffer  (64 KB)
3. Allocate DFS stack      (512 × 8 = 4,096 bytes)
4. Allocate push/pop stack (1,024 × 8 = 8,192 bytes)
5. JSLex_Init()
6. JSParse_Init()
7. JSValidate_Init()
8. JSComp_Init()
9. JSRT_Init()
10. JSVM_Init()
→ Note: JSBridge_Init NOT called here — needs DOM root from page load
```

### 9.3 Page Loading Pipeline

`JSEngine_LoadPage(dom_root)` executes the full page lifecycle:

```
1. Store dom_root
2. JSBridge_Init(dom_root)        → bridge_ready = 1
3. JSVM_InstallBuiltins()         → register core natives (console, Math, etc.)
4. JSEngine__RegisterBridgeGlobals() → document, setTimeout, setInterval, etc.
5. JSEngine__FindScripts(dom_root) → iterative DFS DOM walk
     ├── For each ELEMENT node:
     │   ├── Check if tag == "script" (byte-by-byte: 115,99,114,105,112,116)
     │   ├── Find first TEXT child
     │   ├── Copy text into str_buf
     │   └── Record in script_pool: [ptr, len]
     └── Push non-script children onto DFS stack
6. For each discovered script (in document order):
     JSEngine_Run(script_ptr, script_len)
       ├── JSLex_Reset(), JSComp_Reset(), JSVM_Reset()
       ├── JSVM_InstallBuiltins()
       ├── Re-register bridge globals
       ├── JSLex_Tokenize()
       ├── JSParse_Parse()
       ├── JSComp_Compile()
       ├── JSVM_Load() + JSVM_Run()
       └── Return result JSValue
```

### 9.4 Script Discovery (DFS Walk)

Scripts are discovered via an iterative depth-first search of the DOM tree, avoiding recursion to prevent stack overflow on deeply nested DOMs:

1. Push `dom_root` onto DFS stack
2. While DFS stack not empty:
   - Pop node
   - If ELEMENT node with tag "script":
     - Find first TEXT child
     - Copy text content into `str_buf`
     - Record `[pointer, length]` in `script_pool`
     - Skip recursion into script children (already extracted)
   - Else:
     - Collect all children into temporary buffer
     - Push children in reverse order (so first child is processed first)
3. Scripts are executed in discovery order (document order)

### 9.5 Script Execution

`JSEngine_Run(source, src_len)` executes a single script:

1. Reset lexer, compiler, VM state
2. Re-install built-in globals
3. Re-register bridge globals (if bridge ready)
4. Tokenize → Parse → Compile → Load → Run
5. Check for errors at each stage
6. Return result JSValue or `undefined` on error

### 9.6 Eval String

`JSEngine_EvalString(js_str, js_len)` provides a convenience path for executing arbitrary JS at runtime:

- Validates that the engine is initialized
- Auto-computes actual string length (validates against caller-supplied length)
- Delegates to `JSEngine_Run`
- Used by the MCP tool (`cc_js_ipc`) for LLM-orchestrated execution

### 9.7 Per-Frame Tick

`JSEngine_Tick(current_ms)` is called from the browser main loop each frame:

- Delegates to `JSBridge_TickTimers(current_ms)`
- Returns number of expired timers that were dispatched

### 9.8 DOM Event Dispatch

`JSEngine_FireDOMEvent(dom_node, event_name)` handles user interactions:

- Validates bridge is ready
- Delegates to `JSBridge_FireEvent(dom_node, event_name)`
- Returns 1 if a handler was invoked, 0 if no matching listener found

### 9.9 Key API

| Function | Signature | Purpose |
|----------|-----------|---------|
| `JSEngine_Init()` | `→ I` | Initialize all JS subsystems |
| `JSEngine_Reset()` | `→ I` | Clear runtime state for new page |
| `JSEngine_LoadPage(root)` | `I → I` | Load and execute all scripts on a page |
| `JSEngine_Run(src, len)` | `A,I → A` | Execute a single JS string |
| `JSEngine_EvalString(str, len)` | `A,I → A` | Convenience eval |
| `JSEngine_Tick(ms)` | `I → I` | Per-frame timer dispatch |
| `JSEngine_FireDOMEvent(node, name)` | `I,A → I` | Fire a DOM event |
| `JSEngine_GetError()` | `→ I` | Get error flag |
| `JSEngine_GetScriptCount()` | `→ I` | Get discovered script count |
| `JSEngine_IsInitialized()` | `→ I` | Check init status |
| `JSEngine_Shutdown()` | `→ I` | Release resources |

---

## 10. Integration — cc_js_ipc & Test262 Harness

### 10.1 cc_js_ipc — MCP Native JavaScript Tool

`cc_js_ipc.ailang` (source in `cc_tools/cc_js_ipc.ailang`, compiled to `cc_js_ipc.x`) exposes the JS engine as a tool accessible to the LLM orchestrator (HalCode9000). It runs as a Unix domain socket server.

#### 10.1.1 Socket Architecture

```
Path: /tmp/ailang_cctools/@halcode/JS
Protocol: Unix domain stream socket
Schema: IPC-based tool descriptor (UtilArgs)
```

#### 10.1.2 Tool Schema

```json
{
  "name": "JS",
  "description": "Execute JavaScript code natively on the internal high-performance VM. Returns console output or the final evaluated value.",
  "fields": [
    {
      "name": "code",
      "type": "string",
      "required": true,
      "description": "The JavaScript code to execute."
    },
    {
      "name": "max_steps",
      "type": "int",
      "required": false,
      "description": "Maximum VM steps to execute (default 5000000). Increase for heavy workloads."
    }
  ]
}
```

#### 10.1.3 Request/Response Protocol

**Request:**
```json
{
  "method": "call",
  "id": "optional-request-id",
  "args": {
    "code": "console.log('hello'); 42",
    "max_steps": "5000000"
  }
}
```

**Success Response:**
```json
{
  "method": "result",
  "id": "optional-request-id",
  "ok": true,
  "content": "42"
}
```

**Error Response:**
```json
{
  "method": "result",
  "id": "optional-request-id",
  "ok": false,
  "error": "VM ERROR: Execution failed. Step limit exceeded or runtime exception."
}
```

**Schema Request:**
```json
{
  "method": "schema"
}
```

#### 10.1.4 Execution Flow

```
1. Receive "call" request
2. Validate args → extract "code" (required) and "max_steps" (optional)
3. Set JSVM step limit from max_steps param
4. JSVM_Eval(js_code, code_len)
5. If result is valid:
     JSRT_ToString(result) → extract string payload
6. If result is null/error:
     Check JSVM_GetError() → return error message or "undefined"
7. Send result response
```

#### 10.1.5 Initialization

On startup, the tool initializes all JS subsystems in order:
1. `JSLex_Init()`
2. `JSParse_Init()`
3. `JSComp_Init()`
4. `JSValidate_Init()`
5. `JSRT_Init()`
6. `JSVM_Init()`
7. `JSVM_InstallBuiltins()`

Note: JSBridge is NOT initialized — the MCP tool runs in "headless" mode without a DOM.

### 10.2 Test262 Harness

`Test262Harness.ailang` (source in the AiLangSH root, compiled to `test262_harness.x` and `Test262.x`) is a test runner for ECMAScript conformance validation using the official Test262 test suite.

#### 10.2.1 Architecture

```
Test262 .js file
    │
    ▼
Harness_ReadAll(path)
    │
    ▼
Harness_ExtractFrontmatter(content)
    │  Finds /*--- ... ---*/ YAML block
    │
    ▼
Harness_ParseYAML(frontmatter)
    │  Extracts:
    │    • includes:     [assert.js, sta.js, ...]
    │    • negative:     {phase, type}
    │    • flags:        [async, ...]
    │
    ▼
Harness_PrepareCode()
    │  Prepends include files
    │
    ▼
Harness_ExecuteTest(js_code)
    └── (stub — calls JS engine)
```

#### 10.2.2 Test File Format

Test262 files use a YAML frontmatter block:

```javascript
/*---
includes: [assert.js, sta.js]
flags: [async]
negative:
  phase: runtime
  type: ReferenceError
---*/

// JavaScript test code
assert.sameValue(foo, 42);
```

#### 10.2.3 Parsed Fields

| Field | Source | Purpose |
|-------|--------|---------|
| `includes` | YAML `includes:` | Helper files to prepend (e.g., assert.js) |
| `is_negative` | YAML `negative:` | Whether the test expects an error |
| `neg_phase` | `negative.phase` | When the error should occur (runtime/parse) |
| `neg_type` | `negative.type` | Expected error type (ReferenceError, TypeError, etc.) |
| `is_async` | `flags: [async]` | Whether the test is async |
| `test_code` | After `---*/` | The actual JavaScript test code |

#### 10.2.4 Code Preparation

The harness prepends required include files from `/mnt/c/Users/Sean/Documents/test262/harness/`:

```
[assert.js content] + "\n" + [original test code]
```

The combined string is then handed to the JS engine for execution.

#### 10.2.5 Current Limitations

The `Harness_ExecuteTest` function is currently a stub — it has TODO comments where the actual JS Engine invocation would go. The harness can parse and prepare test files but does not yet execute them through the VM (the engine execution path is through `cc_js_ipc` or `JSEngine` directly).

### 10.3 Test262 Compliance Status

**Current: 12,567 / 23,899 (52.6%)**

The test262 test suite is located at `/mnt/c/Users/Sean/Documents/AiLangSH/test262/` and contains:
- `test/` — 23,899+ individual test files
- `harness/` — Helper files (assert.js, sta.js, etc.)
- `src/` — Test generation infrastructure
- `tools/` — Test runner tools

---

## 11. Roadmap & Future Work

### 11.1 Current Gaps

The engine currently lacks several major language features, broken down by impact on Test262 compliance:

| Category | Failures | % of Total |
|----------|----------|-----------|
| Async/await/Promise | 4,645 | 41.0% |
| Class destructuring params | 3,552 | 31.3% |
| Class private fields (#field) | 3,186 | 28.1% |
| Class fields / computed props | 2,164 | 19.1% |
| Destructuring edge cases | ~800 | 7.1% |
| let/const TDZ | ~200 | 1.8% |
| Float/numeric (IEEE 754) | 189 | 1.7% |
| Template literals | ~37 | 0.3% |

### 11.2 Implementation Phases

#### Phase 1: Quick Wins (~+2,000 passes → 61%)
- **Computed property names in classes** (~500 passes) — Parser already handles `[expr]`, compiler needs to use SET_PROP_COMPUTED
- **Class field declarations** (~800 passes) — Parse `x = 5` in class body, emit initializer in constructor prologue
- **Object.defineProperty / keys / create** (~1,200 passes) — Property descriptor support in JSRuntime
- **Template literal improvements** (~37 passes)

#### Phase 2: Async/Await + Promises (~+4,000 passes → 78%)
- **Promise type** — New JSType, state machine (pending/fulfilled/rejected), .then()/.catch()
- **Microtask queue** — FIFO queue in JSVM, drain after script turns
- **Async/await syntax** — New tokens (KW_ASYNC, KW_AWAIT), new AST types, parser integration
- **Async compilation** — Reuse generator infrastructure for state-machine-based async functions
- **Async VM execution** — AWAIT opcode, promise integration

#### Phase 3: Class Advanced (~+3,000 passes → 90%)
- **Private fields (#field)** — Mangled property names, compile-time access checks
- **Static blocks** — `static { ... }` in class body
- **extends expression improvements** — Computed extends expressions

#### Phase 4: Numeric (~+189 passes → 91%)
- **IEEE 754 double** — Separate FLOAT64 type using SSE2, for Test262 compliance
- **Fixed-point** — Q32.32 for DOM/layout performance (alongside IEEE 754)
- **Auto-selection heuristic** — Layout engine uses fixed-point, general JS uses IEEE 754

#### Phase 5: Remaining (~+2,106 passes → 100%)
- **let/const TDZ** (~200) — CHECK_TDZ opcode
- **Iterator protocol** (~500) — Symbol.iterator, lazy for-of, spread, destructuring
- **Proxy/Reflect** (~1,000) — Advanced metaprogramming
- **Module system** (~365) — import/export syntax, dynamic import()
- **RegExp advanced** (~200) — Named groups, lookbehind, unicode (extends existing Thompson NFA)

### 11.3 Design Constraints & Trade-offs

1. **No GC** — Arena allocation means all memory lives until reset. This is efficient for page-load-and-discard patterns but limits long-running applications. A future WeakRef/FinalizationRegistry implementation may require a simple refcount scheme.

2. **Integer-only math** — Currently all numbers are integers. This simplifies the runtime but limits Test262 conformance. The planned dual-mode (fixed-point for layout, IEEE 754 for JS) adds complexity but passes compliance.

3. **No JIT** — The engine is purely interpreted. The stack-based bytecode design would lend itself to a simple template JIT in the future, but current performance targets page scripting, not computation-heavy workloads.

4. **Blocking VM** — The VM runs synchronously. There is no event loop yielding, no microtask interleaving, and no async suspension. These are planned for Phase 2.

5. **DOM coupling** — The JSBridge is tightly coupled to the specific HTMLDom library. A future abstraction layer could support different DOM implementations.

---

## Appendix A: File Reference

| File | Path | Lines |
|------|------|-------|
| JSLexer | `Librarys/Browser/Library.JSLexer.ailang` | 1,477 |
| JSParser | `Librarys/Browser/Library.JSParser.ailang` | 4,967 |
| JSValidate | `Librarys/Browser/Library.JSValidate.ailang` | 209 |
| JSCompiler | `Librarys/Browser/Library.JSCompiler.ailang` | 3,927 |
| JSRuntime | `Librarys/Browser/Library.JSRuntime.ailang` | 3,370 |
| JSVM | `Librarys/Browser/Library.JSVM.ailang` | 2,297 |
| JSBridge | `Librarys/Browser/Library.JSBridge.ailang` | 2,073 |
| JSEngine | `Librarys/Browser/Library.JSEngine.ailang` | 902 |
| MCP Tool | `Applications/HalCode9000/cc_tools/cc_js_ipc.ailang` | ~260 |
| Test Harness | `Test262Harness.ailang` (AiLangSH root) | ~400 |
| Roadmap | `Librarys/Browser/ROADMAP.md` | ~350 |

## Appendix B: Related Browser Libraries

The JS engine is part of a larger browser stack in `Librarys/Browser/`:

| File | Lines | Purpose |
|------|-------|---------|
| `Library.HTMLTokenizer.ailang` | 67,079 | HTML5 tokenizer |
| `Library.HTMLDom.ailang` | 37,024 | DOM tree construction |
| `Library.HTMLLayout.ailang` | 35,333 | CSS layout engine |
| `Library.CSSParse.ailang` | 32,012 | CSS parser |
| `Library.HTTPClient.ailang` | 19,810 | HTTP/HTTPS client |
| `Library.HTMLRender.ailang` | 7,955 | Rendering to canvas |
| `Library.DNS.ailang` | 20,388 | DNS resolver |
| `Library.URL.ailang` | 14,976 | URL parser |
| `Library.ImageDecode.ailang` | 35,597 | PNG/GIF decoder |
| `Library.JPEGDecode.ailang` | 47,598 | JPEG decoder |

## Appendix C: Opcode Quick Reference

```
00 HALT             Stop execution
01 PUSH_CONST ii    Push constant pool entry
02 PUSH_UNDEF       Push undefined
03 PUSH_NULL        Push null
04 PUSH_TRUE        Push true
05 PUSH_FALSE       Push false
06 POP              Discard top of stack
07 DUP              Duplicate top of stack
10 GET_LOCAL s      Load local slot s
11 SET_LOCAL s      Store to local slot s
12 GET_GLOBAL ii    Load global by const index
13 SET_GLOBAL ii    Store to global by const index
16 GET_PROP ii      Property access by name
17 SET_PROP ii      Property store by name
18 GET_ELEM         Computed property access
19 SET_ELEM         Computed property store
20 ADD              a + b
21 SUB              a - b
22 MUL              a * b
23 DIV              a / b
24 MOD              a % b
25 NEG              -a
26 EXP              a ** b
30 EQ               a == b
31 NEQ              a != b
32 LT               a < b
33 GT               a > b
34 LTE              a <= b
35 GTE              a >= b
36 STRICT_EQ        a === b
37 STRICT_NEQ       a !== b
38 IN               a in b
40 NOT              !a
41 BIT_AND          a & b
42 BIT_OR           a | b
43 BIT_XOR          a ^ b
44 BIT_NOT          ~a
45 SHL              a << b
46 SHR              a >> b
47 TYPEOF           typeof a
48 USHR             a >>> b
49 INSTANCEOF       a instanceof b
50 JMP oo           Unconditional jump
51 JMP_FALSE oo     Jump if false
52 JMP_TRUE oo      Jump if true
53 JMP_NULLISH oo   Jump if null/undefined (keep on stack)
55 CALL a           Call function with a args
56 RETURN           Return from function
57 CLOSURE ii       Create closure
60 NEW_OBJECT       Create empty object
61 NEW_ARRAY        Create empty array
62 CONCAT           String concatenation
63 SET_PROP_COMPUTED    obj[key] = val
64 DEF_GETTER       Define getter
65 DEF_SETTER       Define setter
66 OBJ_KEYS         Object.keys()
67 ARR_APPEND       Array append
68 ARR_EXTEND       Array extend
69 CALL_SPREAD      Call with spread
70 TRY_PUSH         Push exception handler
71 TRY_POP          Pop exception handler
72 THROW            Throw exception
73 YIELD            Yield from generator
74 GEN_CLOSURE      Create generator closure
75 TO_ARRAY         Convert to array
76 DEF_GETTER_COMPUTED  Computed getter
77 DEF_SETTER_COMPUTED  Computed setter
99 NOP              No operation

Legend: s = 1-byte operand, ii = 2-byte big-endian operand, oo = 2-byte signed offset, a = 1-byte arity
```
