# AILang Compiler — 01: Frontend Layer (Lexer → Parser → AST)

## Overview

The frontend transforms raw source text into an AST (Abstract Syntax Tree). Three stages:

```
Source.ailang  →  [Lexer]  →  Token Stream  →  [Parser]  →  AST  →  [Semantic]
  (string)         (8 modules)   (XArray)        (5 modules)   (tree)   (check)
```

---

## 1. LEXER (8 files, ~100KB total)

### 1.1 Architecture

The lexer is a **single-pass character scanner** that produces a flat array of tokens.

**State** (FixedPool.Lex):
```
source: Address       — source text buffer
filename: Address     — source file name
pos: Integer          — current byte position
line, col: Integer    — current line/column
length: Integer       — total source length
tokens: XArray        — token array
token_count: Integer  — number of tokens
error: Integer        — error flag
```

**Token structure** (32 bytes per token):
```
[0]  type: Integer    — token type (Token.* constants)
[8]  value: Address   — string value (for identifiers, numbers, strings)
[16] line: Integer    — source line number
[24] col: Integer     — source column
```

### 1.2 Token Types (CLexerTypes)

Major token categories:
```
NEWLINE, EOF                    — structural
IDENTIFIER, NUMBER, STRING      — literals
FUNCTION, SUBROUTINE, FIXEDPOOL, DYNAMICPOOL, TEMPORALPOOL, NEURALPOOL, KERNELPOOL... — declarations
IF, WHILE, FOR, FORK, BRANCH, CASE, DEFAULT, RETURN, EXITLOOP, CONTINUELOOP, TRY, CATCH, FINALLY — control flow
LIBRARYIMPORT, ACRONYMDEFS, EXPORT — module system
LBRACE, RBRACE, LPAREN, RPAREN, LBRACKET, RBRACKET — delimiters
COMMA, DOT, COLON, SEMICOLON, AT — punctuation
PLUS, MINUS, STAR, SLASH, PERCENT, EQ, NEQ, LT, GT, LTE, GTE, AND, OR, NOT, XOR — operators
ASSIGN, ARROW — assignment and mapping
```

### 1.3 Lexer Module Details

#### CLexerCore — Character-level operations
```
Lex_Init(source, filename) → void
    Initialize lexer state, set source buffer and filename

Lex_CurrentChar() → Integer
    Return byte at current position (0 if EOF)

Lex_PeekChar(offset) → Integer
    Return byte at pos+offset without advancing

Lex_Advance() → void
    Move to next character, track line/column

Lex_SkipWhitespace() → void
    Skip spaces, tabs, carriage returns (not newlines)

Lex_IsDigit(c) → Integer
    Returns 1 if '0'-'9'

Lex_IsIdentifierStart(c) → Integer
    Returns 1 if letter or '_'

Lex_IsIdentifierPart(c) → Integer
    Returns 1 if letter, digit, or '_'

Lex_AddToken(type, value, line, col, len) → void
    Allocate token entry, push to token array

Lex_GetToken(index) → Address
    Return address of token at index

Lex_Error(msg) → void
    Set error flag, print error with line/col
```

#### CLexerKeywords — Keyword recognition
```
Lex_CheckKeyword(str, len) → Integer
    Compare string against keyword table
    Returns token type if keyword, 0 if not

Keyword table includes: Function, SubRoutine, FixedPool, DynamicPool, 
    IfCondition, WhileLoop, ReturnValue, ExitLoop, ContinueLoop,
    LibraryImport, RunTask, PrintMessage, PrintNumber, PrintString,
    ForEvery, Branch, Case, Default, Fork, TryBlock, CatchError,
    FinallyBlock, And, Or, Not, Xor, TrueValue, FalseValue...
```

#### CLexerStrings — String literal tokenizing
```
Lex_TokenizeString(line, col) → void
    Scan characters between "...", handle escape sequences
    Supports: \n \r \t \\ \" \0
    Creates STRING token with unescaped content
```

#### CLexerNumbers — Number literal tokenizing
```
Lex_ReadNumber() → Address
    Read decimal integer (supports negative: -123)
    Returns string representation of the number
    Creates NUMBER token
```

#### CLexerOperators — Operator and delimiter tokenizing
```
Lex_TokenizeOperator(line, col) → Integer
    Match longest operator at current position
    Handles: == != <= >= := & | ^ << >> -> @ # ... etc.
    Returns 1 if matched, 0 if not an operator
```

#### CLexerIdentifiers — Identifier tokenizing
```
Lex_TokenizeIdentifier(line, col) → void
    Read [a-zA-Z_][a-zA-Z0-9_]* 
    Check if it's a keyword (CLexerKeywords)
    Create IDENTIFIER token or keyword token
```

#### CLexerMain — Main tokenization loop
```
Lex_Tokenize() → Integer
    Main loop: while not EOF:
        Skip whitespace
        Check for: EOF, newline, comment (//), string ("),
                   number (digit or -digit), identifier, operator
        Error on unknown character
    Returns token count

Lex_DumpTokens() → void
    Print all tokens for debugging
```

### 1.4 Lexer Flow

```
Lex_Init(source, filename)
    │
    ▼
Lex_Tokenize()
    │
    ├─ while not EOF:
    │   ├─ Lex_SkipWhitespace()
    │   ├─ c = Lex_CurrentChar()
    │   ├─ c==0?       → EOF token, done
    │   ├─ c=='\n'?    → NEWLINE token
    │   ├─ c=='/'?     → skip comment
    │   ├─ c=='"'?     → Lex_TokenizeString()
    │   ├─ isDigit(c)? → Lex_ReadNumber()
    │   ├─ c=='-' && isDigit(next)? → Lex_ReadNumber() (negative)
    │   ├─ isIdent(c)? → Lex_TokenizeIdentifier()
    │   ├─ isOp(c)?    → Lex_TokenizeOperator()
    │   └─ else        → Lex_Error("Unknown character")
    │
    ▼
Lex.token_count tokens ready for parser
```

---

## 2. PARSER (5 files, ~150KB total)

### 2.1 Architecture

The parser uses a **recursive descent** approach with **Pratt parsing** for expressions. It consumes tokens via a global position counter and produces AST nodes.

**State** (FixedPool.PParser):
```
p_tokens: Address         — reference to lexer token array
p_token_count: Integer    — total tokens
p_pos: Integer            — current token position
p_current_type: Integer   — type of current token
p_current_value: Address  — value of current token
p_context_depth: Integer  — brace/block nesting depth
p_error: Integer          — error flag
p_error_line, p_error_col, p_error_msg
p_ast_root: Address       — root AST node
```

### 2.2 Parser Module Details

#### CParserCore — Core parsing infrastructure
```
Parse_Init(token_count) → Integer
    Initialize parser, set up token stream reference

Parse_Advance() → void
    Move to next token, update p_current_type/value

Parse_Peek(offset) → Integer
    Look ahead/behind by offset tokens

Parse_Match(type) → Integer
    If current token matches type, advance and return 1

Parse_Expect(type) → Integer
    Require current token to match type, error if not

Parse_SkipNewlines() → void
    Skip NEWLINE tokens (whitespace between statements)

Parse_HasError() → Integer
    Return p_error flag

Parse_AtStatementStart() → Integer
    Check if we're at a known statement-start token
```

#### CParserExpressions — Expression parsing (Pratt parser)
```
Parse_Expression() → Address
    Entry point: parse expression starting at current position

Parse_Expression_MinPrec(min_prec) → Address
    Pratt parser core: parse prefix, then infix operators with precedence

Parse_Primary() → Address
    Parse: number, string, identifier, function call, parenthesized expr,
           array literal [a,b], lambda, member access (a.b), index access (a[i]),
           pointer field access (a@field)

Parse_PrefixOp() → Address
    Handle: - (negate), ! (not), ~ (bitnot)

Parse_InfixOp(left) → Address  
    Handle: + - * / % == != < > <= >= && || & | ^ << >>
    Each operator has precedence and associativity
```

**Precedence table (typical):**
```
1:  || (lowest)
2:  &&
3:  == != < > <= >=
4:  + -
5:  * / %
6:  << >>
7:  & | ^
8:  unary - ! ~ (highest)
```

#### CParserStatements — Statement parsing
```
Parse_Statement() → Address
    Dispatch based on current token:
    - IfCondition → Parse_IfStmt()
    - WhileLoop → Parse_WhileStmt()
    - ForEvery → Parse_ForEveryStmt()
    - ReturnValue/Return → Parse_ReturnStmt()
    - ExitLoop/BreakLoop → Parse_BreakStmt()
    - ContinueLoop → Parse_ContinueStmt()
    - Branch/Switch → Parse_SwitchStmt()
    - Fork → Parse_ForkStmt()
    - TryBlock → Parse_TryStmt()
    - { → Parse_Block()
    - identifier → Parse_Assignment() or Parse_FunctionCall()

Parse_Block() → Address
    Parse { statement* } block, return AST.BLOCK node

Parse_IfStmt() → Address
    IfCondition expr ThenBlock: { ... } [ElseBlock: { ... }]
    Returns AST.IF node

Parse_WhileStmt() → Address
    WhileLoop condition { ... }
    Returns AST.WHILE node

Parse_Assignment() → Address
    target = expression
    target@field = expression  (pointer field write)
    Returns AST.ASSIGNMENT node
```

#### CParserDeclarations — Top-level declarations
```
Parse_Declaration() → Address
    Dispatch based on current token:
    - LibraryImport → parse import
    - Function → parse function definition
    - SubRoutine → parse subroutine
    - FixedPool/DynamicPool/etc → parse pool definition
    - LoopMain/LoopActor → parse loop definition
    - identifier followed by { → pool member init
    - RunTask(identifier) → task invocation

Parse_Function() → Address
    Function.Name { Input: ... Output: ... Body: { ... } }
    Returns AST.FUNCTION node

Parse_SubRoutine() → Address
    SubRoutine.Name { ... }
    Returns AST.SUBROUTINE node

Parse_Pool() → Address
    FixedPool.Name { "field": Initialize=... }
    DynamicPool.Name { "field": Initialize=... }
    Returns AST.POOL_* node

Parse_LibraryImport() → Address
    LibraryImport.path.to.module
    Returns AST.LIBRARY_IMPORT node
```

#### CParserMain — Entry point
```
Parse_Program() → Address
    Main loop: while not EOF:
        Parse_SkipNewlines()
        decl = Parse_Declaration()
        if decl: AST_AddChild(program, decl)
    Returns AST.PROGRAM node

Parse(token_count) → Address
    Parse_Init() → Parse_Program() → return AST

Parse_Validate(ast) → Integer
    Check AST: counts functions, subroutines, pools, imports
    Prints validation summary
```

### 2.3 Parser Flow

```
Parse_Init(token_count)
    │
    ▼
Parse_Program()
    │
    ├─ while not EOF:
    │   ├─ skip newlines
    │   ├─ Parse_Declaration()
    │   │   ├─ Function → Parse_Function()
    │   │   ├─ SubRoutine → Parse_SubRoutine()
    │   │   ├─ FixedPool/DynamicPool/etc → Parse_Pool()
    │   │   ├─ LibraryImport → Parse_LibraryImport()
    │   │   ├─ RunTask → parse task call
    │   │   └─ default → Parse_Statement() (might be pool member init)
    │   └─ add child to program node
    │
    ▼
AST.PROGRAM node with declaration children
```

---

## 3. AST (5 files, ~75KB total)

### 3.1 Architecture

AST nodes are flat 64-byte records stored in a global array. The tree is built by linking nodes via child indices.

**Node structure** (64 bytes):
```
[0]  type: Integer        — AST node type (AST.* constants)
[8]  data1: Address       — primary data (string/identifier)
[16] data2: Address       — secondary data (field name, etc.)
[24] data3: Integer       — tertiary data (numeric)
[32] data4: Integer       — quaternary data
[40] children: XArray     — child node addresses
[48] line, col: Integer   — source location
```

### 3.2 AST Node Types (200+ constants)

**Structure nodes:**
```
PROGRAM (1), LIBRARY_IMPORT (2), ACRONYM_DEFS (3), MODULE (4), EXPORT (5)
```

**Function-related:**
```
FUNCTION (100), SUBROUTINE (101), PARAMETER (102), OUTPUT_DECL (103),
BODY (104), LAMBDA (105), COMBINATOR (106-110), EXTERN_KFUNC (111)
```

**Pool types:**
```
POOL (200), POOL_FIXED (201), POOL_DYNAMIC (202), POOL_TEMPORAL (203),
POOL_NEURAL (204), POOL_KERNEL (205), POOL_ACTOR (206), POOL_SECURITY (207),
POOL_CONSTRAINED (208), POOL_FILE (209), POOL_LINKAGE (210)
POOL_MEMBER/POOL_ITEM (211), SUBPOOL (212), POOL_ATTR (213)
POOL_INITIALIZE (220) through POOL_DIRECTION (228)
```

**Statement nodes:**
```
ASSIGNMENT (300), BLOCK (301), IF (302), WHILE (303), RETURN (304),
EXIT_LOOP (305), CONTINUE_LOOP (306), TRY/CATCH/FINALLY (307-309),
THROW (310), FOR_EVERY (311), SWITCH (312), CASE (313), DEFAULT (314),
LOOP_MAIN/SHADOW/START/ACTOR (315-318), WITH_CONTEXT (319),
DEFER (320), FORK (321), BRANCH (322), UNTIL (323), EVERY_INTERVAL (324)
```

**Expression nodes:**
```
CALL (400), IDENTIFIER (401), NUMBER (402), STRING (403), BOOLEAN (404),
NULL (405), ARRAY_LITERAL (406), MAP_LITERAL (407), TUPLE_LITERAL (408),
RECORD_LITERAL (409), BINARY_OP (410), UNARY_OP (411), MEMBER_ACCESS (412),
INDEX_ACCESS (413), CONDITIONAL (414), LAMBDA_EXPR (415)
```

**Operator nodes (500-608):** Arithmetic, comparison, logic, bitwise, memory, I/O, string, array, socket, hash, system, loop messaging, security

**Debug nodes:**
```
DEBUG_BLOCK (900) through DEBUG_CONTROL (907)
```

**Type nodes:**
```
TYPE_INTEGER (950) through TYPE_POINTER (974)
POINTER_FIELD_ACCESS (975), POINTER_FIELD_ASSIGN (976)
```

### 3.3 AST Module Details

#### CASTCore — Node creation and manipulation
```
AST_MakeNode(type) → Address
    Allocate 64-byte node, initialize children XArray, track in ASTState.all_nodes

AST_MakeProgram() → Address
    Create AST.PROGRAM node

AST_GetType(node) → Integer
AST_GetData1(node) → Address       — primary data (usually name)
AST_GetData2(node) → Address       — secondary data
AST_GetData3(node) → Integer
AST_GetData4(node) → Integer

AST_SetData1-4(node, value) → void
AST_GetChild(node, index) → Address
AST_GetChildCount(node) → Integer
AST_AddChild(node, child) → void
AST_SetChild(node, index, child) → void
```

#### CASTNodes — Typed node constructors
```
AST_MakeFunction(name) → Address
    Creates FUNCTION node with name in data1

AST_MakeSubroutine(name) → Address
    Creates SUBROUTINE node with name in data1

AST_MakeIdentifier(name) → Address
    Creates IDENTIFIER node

AST_MakeNumber(value_str) → Address
    Creates NUMBER node

AST_MakeString(value_str) → Address
    Creates STRING node

AST_MakeCall(name) → Address
    Creates CALL node (function call)

AST_MakeAssignment(target) → Address
    Creates ASSIGNMENT node

AST_MakeReturn(expr) → Address
    Creates RETURN node with expression child
```

#### CASTDebug — AST printing
```
AST_Dump(node) → void
    Recursively print AST tree with indentation

AST_DumpNode(node, indent) → void
    Print single node info: type, data1-4, child count
```

#### CSemanticCore — Semantic analysis
```
Semantic_Check(ast) → Integer
    Walk entire AST, perform checks:
    - Undefined variable references
    - Type mismatches in expressions
    - Function call arity checking
    - Pool field existence verification
```

---

## 4. Frontend Data Flow

```
Source text (string in memory)
    │
    ▼ Lex_Init(source, filename)
    │
    ▼ Lex_Tokenize()
    │   • Character-by-character scanning
    │   • Specialized handlers for strings, numbers, operators
    │   • Keyword table lookup for identifiers
    │   • Produces: XArray of 32-byte token structs
    │
    ▼ Parse_Init(token_count)
    │
    ▼ Parse_Program()
    │   • Token-by-token consumption
    │   • Recursive descent: declaration → statement → expression
    │   • Pratt parser for expression precedence
    │   • Produces: tree of 64-byte AST nodes
    │
    ▼ Parse_Validate(ast)
    │   • Count functions, subroutines, pools, imports
    │   • Verify PROGRAM root type
    │   • Report statistics
    │
    ▼ Semantic_Check(ast) [optional]
    │   • Undefined variable detection
    │   • Type checking
    │
    ▼ AST root (Address) → ready for compilation
```

---

*Document 01 of 10 — Frontend Layer*
