# AILang Compiler — 09: Function Catalog

This document catalogs every function in the compiler, organized by module. For each function: signature, purpose, and key behaviors.

---

## 1. LEXER FUNCTIONS

### CLexerCore
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Lex_Init` | source:Address, filename:Address | void | Initialize lexer state |
| `Lex_CurrentChar` | — | Integer | Return current byte (0 if EOF) |
| `Lex_PeekChar` | offset:Integer | Integer | Look ahead in source |
| `Lex_Advance` | — | void | Move to next char, track line/col |
| `Lex_SkipWhitespace` | — | void | Skip spaces/tabs/CR |
| `Lex_IsDigit` | c:Integer | Integer | Return 1 if '0'-'9' |
| `Lex_IsIdentifierStart` | c:Integer | Integer | Return 1 if letter or '_' |
| `Lex_IsIdentifierPart` | c:Integer | Integer | Return 1 if letter, digit, or '_' |
| `Lex_AddToken` | type, value, line, col, len | void | Create token entry |
| `Lex_GetToken` | index:Integer | Address | Return token at index |
| `Lex_Error` | msg:Address | void | Set error flag, print message |

### CLexerKeywords
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Lex_CheckKeyword` | str:Address, len:Integer | Integer | Return keyword token type or 0 |

### CLexerMain
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Lex_Tokenize` | — | Integer | Main tokenization loop, returns count |
| `Lex_TokenizeNumber` | line, col | void | Read number, create NUMBER token |
| `Lex_GetTokenCount` | — | Integer | Return token count |
| `Lex_DumpTokens` | — | void | Print all tokens |

### CLexerStrings
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Lex_TokenizeString` | line, col | void | Read string literal, handle escapes |

### CLexerNumbers
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Lex_ReadNumber` | — | Address | Read number, return string value |

### CLexerOperators
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Lex_TokenizeOperator` | line, col | Integer | Match operator, return 1 if handled |

### CLexerIdentifiers
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Lex_TokenizeIdentifier` | line, col | void | Read identifier, check keywords |

---

## 2. PARSER FUNCTIONS

### CParserCore
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Parse_Init` | token_count:Integer | Integer | Initialize parser state |
| `Parse_Advance` | — | void | Move to next token |
| `Parse_Peek` | offset:Integer | Integer | Look ahead/behind |
| `Parse_Match` | type:Integer | Integer | Consume token if type matches |
| `Parse_Expect` | type:Integer | Integer | Require token type, error if not |
| `Parse_SkipNewlines` | — | void | Skip NEWLINE tokens |
| `Parse_HasError` | — | Integer | Return error state |
| `Parse_AtStatementStart` | — | Integer | Check if at statement boundary |

### CParserMain
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Parse_Program` | — | Address | Main entry: parse to AST.PROGRAM |
| `Parse` | token_count:Integer | Address | Init + parse pipeline |
| `Parse_WithOptions` | token_count, show_progress, show_ast | Address | Parse with debug options |
| `Parse_SingleExpression` | token_count:Integer | Address | Parse one expression (REPL) |
| `Parse_SingleStatement` | token_count:Integer | Address | Parse one statement (REPL) |
| `Parse_Synchronize` | — | void | Error recovery: skip to safe point |
| `Parse_Validate` | ast:Address | Integer | Check AST structure |
| `Parse_Cleanup` | free_ast:Integer | void | Free parser resources |
| `Parse_PrintStats` | — | void | Print parser statistics |

### CParserExpressions
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Parse_Expression` | — | Address | Parse expression entry point |
| `Parse_Expression_MinPrec` | min_prec:Integer | Address | Pratt parser core |
| `Parse_Primary` | — | Address | Parse literal/identifier/call |
| `Parse_PrefixOp` | — | Address | Parse unary operator |
| `Parse_InfixOp` | left:Address | Address | Parse binary operator |

### CParserStatements
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Parse_Statement` | — | Address | Dispatch to specific parser |
| `Parse_Block` | — | Address | Parse { statements } |
| `Parse_IfStmt` | — | Address | Parse IfCondition block |
| `Parse_WhileStmt` | — | Address | Parse WhileLoop |
| `Parse_Assignment` | — | Address | Parse target = expr |

### CParserDeclarations
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Parse_Declaration` | — | Address | Top-level declaration dispatch |
| `Parse_Function` | — | Address | Parse Function.Name { ... } |
| `Parse_SubRoutine` | — | Address | Parse SubRoutine.Name { ... } |
| `Parse_Pool` | — | Address | Parse pool definition |
| `Parse_LibraryImport` | — | Address | Parse LibraryImport.path |

---

## 3. AST FUNCTIONS

### CASTCore
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `AST_MakeNode` | type:Integer | Address | Allocate 64-byte node |
| `AST_MakeProgram` | — | Address | Create PROGRAM node |
| `AST_GetType` | node:Address | Integer | Get node type |
| `AST_GetData1` | node:Address | Address | Get primary data (name) |
| `AST_GetData2` | node:Address | Address | Get secondary data |
| `AST_GetData3` | node:Address | Integer | Get tertiary data |
| `AST_GetData4` | node:Address | Integer | Get quaternary data |
| `AST_SetData1-4` | node, value | void | Set data fields |
| `AST_GetChild` | node, index | Address | Get child by index |
| `AST_GetChildCount` | node:Address | Integer | Count children |
| `AST_AddChild` | node, child | void | Append child |
| `AST_SetChild` | node, index, child | void | Replace child |

### CASTNodes
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `AST_MakeFunction` | name:Address | Address | Create FUNCTION node |
| `AST_MakeSubroutine` | name:Address | Address | Create SUBROUTINE node |
| `AST_MakeIdentifier` | name:Address | Address | Create IDENTIFIER node |
| `AST_MakeNumber` | value:Address | Address | Create NUMBER node |
| `AST_MakeString` | value:Address | Address | Create STRING node |
| `AST_MakeCall` | name:Address | Address | Create CALL node |
| `AST_MakeAssignment` | target:Address | Address | Create ASSIGNMENT node |
| `AST_MakeReturn` | expr:Address | Address | Create RETURN node |

### CASTDebug
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `AST_Dump` | node:Address | void | Recursive tree print |
| `AST_DumpNode` | node, indent | void | Single node print |

---

## 4. COMPILE LAYER FUNCTIONS

### CCompileMain (Central Dispatcher)
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Compile_Init` | — | Integer | Initialize compile state |
| `Compile_Free` | — | void | Deallocate resources |
| `Compile_Program` | ast:Address | Integer | **MAIN ENTRY**: compile entire AST |
| `Compile_Node` | node:Address | Integer | Type dispatch on AST node |
| `Compile_FunctionCall` | node:Address | Integer | Name dispatch through modules |
| `Compile_Expression` | node:Address | Integer | Evaluate expr → RAX |
| `Compile_NewLabel` | — | Integer | Create new label |
| `Compile_PushLoop` | break, continue | void | Push loop context |
| `Compile_PopLoop` | — | void | Pop loop context |
| `Compile_Error` | msg:Address | void | Set error flag |
| `Compile_RegisterLocal` | name, offset | void | Register local var |
| `Compile_AddVariable` | name, type, size, flags | Integer | Add variable entry |

### CCompileScope
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Scope_Init` | — | Integer | Initialize scope system |
| `Scope_Free` | — | Integer | Free scope resources |
| `Scope_SaveAndClear` | func_name:Address | Integer | Save scope, clear locals |
| `Scope_Restore` | — | Integer | Restore previous scope |
| `Scope_AddParameter` | name:Address, offset:Integer | Integer | Register function param |
| `Scope_Resolve` | name:Address | Integer | Resolve variable → offset |
| `Scope_InFunction` | — | Integer | Return 1 if inside function |
| `Scope_GetCurrentFunc` | — | Address | Current function name |
| `Scope_ClearFunctionParams` | func_name:Address | Integer | Invalidate params |
| `Scope_SetVarPoolType` | name, type | void | Store var→pool mapping |
| `Scope_GetVarPoolType` | name:Address | Address | Look up pool type |
| `Scope_IsParameter` | name:Address | Integer | Check if param |

### Compile Modules — All TryCompile Pattern
| Module | TryCompile Function | Operations |
|--------|-------------------|------------|
| CCompileArith | `CompileArith_TryCompile` | Add, Subtract, Multiply, Divide, Modulo, Negate, Increment, Decrement |
| CCompileCompare | `CompileCompare_TryCompile` | EqualTo, NotEqual, LessThan, GreaterThan, LessEqual, GreaterEqual |
| CCompileIO | `CompileIO_TryCompile` | PrintMessage, PrintNumber, PrintString, PrintChar, ReadLine, ReadChar |
| CCompileStmt | `CompileStmt_TryCompile` | If, While, Assign, Return, Block, Break, Continue, Switch, Fork, Try |
| CCompileExpr | `CompileExpr_TryCompile` | LoadVariable, StoreVariable, MemberAccess, IndexAccess |
| CCompileFunc | `CompileFunc_TryCompile` | Function definition, function call |
| CCompilePool | `CompilePool_TryCompile` | FixedPool, DynamicPool definitions |
| CCompileLogic | `CompileLogic_TryCompile` | And, Or, Not |
| CCompileBitwise | `CompileBitwise_TryCompile` | BitwiseAnd, BitwiseOr, BitwiseXor, BitwiseNot, LShift, RShift |
| CCompileString | `CompileString_TryCompile` | StringCompare, StringLength, StringCopy, SetByte, GetByte |
| CCompileMem | `CompileMem_TryCompile` | Allocate, Deallocate, StoreValue, Dereference |
| CCompileArray | `CompileArray_TryCompile` | XCreate, XPush, XPop, XGet, XSet, XSize, XDestroy |
| CCompileFile | `CompileFile_TryCompile` | FileOpen, FileRead, FileWrite, FileClose, FileSeek, FileGetSize, FileExists, ReadTextFile, WriteTextFile |
| CCompileAtomic | `CompileAtomic_TryCompile` | AtomicAdd, AtomicSub, AtomicXchg |
| CCompileSystem | `CompileSystem_TryCompile` | Syscall, inline asm |

---

## 5. EMIT LAYER FUNCTIONS

### CEmitCore — Buffer Management
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Emit_Init` | — | void | Allocate code/data buffers |
| `Emit_Free` | — | void | Deallocate all buffers |
| `Emit_Byte` | b:Integer | void | Write 1 byte to code |
| `Emit_Word` | w:Integer | void | Write 2 bytes (LE) |
| `Emit_DWord` | d:Integer | void | Write 4 bytes (LE) |
| `Emit_QWord` | q:Integer | void | Write 8 bytes (LE) |
| `Emit_Bytes` | ptr, count | void | Copy bytes to code |
| `Emit_GetPosition` | — | Integer | Current code position |
| `Emit_PatchByte` | pos, value | void | Overwrite 1 byte |
| `Emit_PatchDWord` | pos, value | void | Overwrite 4 bytes |
| `Emit_PatchQWord` | pos, value | void | Overwrite 8 bytes |
| `Emit_DataByte` | b:Integer | void | Write byte to data section |

### CEmitCore — Label Management
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Emit_CreateLabel` | — | Integer | Allocate label, return ID |
| `Emit_CreateNamedLabel` | name:Address | Integer | Create named label |
| `Emit_MarkLabel` | label_id | void | Mark label at current pos |
| `Emit_GetLabelAddress` | label_id | Integer | Get resolved address |
| `Emit_IsLabelResolved` | label_id | Integer | Check resolution |
| `Emit_FindLabel` | name:Address | Integer | Find by name |
| `Emit_DefineLabel` | label_id | void | Alias for MarkLabel |

### CEmitCore — Fixup Management
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Emit_AddFixup` | label_id, type | void | Record forward reference |
| `Emit_AddFixupAt` | pos, label_id, type | void | Record at specific position |
| `Emit_ResolveFixups` | — | void | Patch all forward references |

### CEmitCore — Data Relocation
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Emit_InitDataRelocs` | — | void | Create reloc array |
| `Emit_AddDataReloc` | code_pos, data_off | void | Record data reference |
| `Emit_SetBaseAddresses` | code_addr, data_addr | void | Set computed base addresses |
| `Emit_ApplyDataRelocations` | — | void | Patch data addresses in code |
| `Emit_FreeDataRelocs` | — | void | Free reloc entries |

### CEmitCore — Data Section
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Emit_AddString` | str:Address | Integer | Add null-terminated string |
| `Emit_AddData` | ptr, size | Integer | Add raw bytes |

### CEmitCore — Symbols & Stats
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Emit_AddSymbol` | name, type | Integer | Register symbol |
| `Emit_PrintStats` | — | void | Print emission stats |
| `Emit_DumpCode` | max_bytes | void | Hex dump code buffer |

---

## 6. EMIT TAGS FUNCTIONS

| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `EmitTag_Init` | — | void | Initialize tag system |
| `EmitTag_Free` | — | void | Free tag memory |
| `EmitTag_Add` | pos, len, class, operand | void | Register tagged instruction |
| `EmitTag_MarkLabel` | code_pos | void | Zero-length LABEL tag |
| `EmitTag_CanFuseStoreLoad` | entry, next | Integer | Safety predicate |
| `EmitTag_Optimize` | — | void | Run peephole pass |
| `EmitTag_NopBytes` | pos, len | void | Write NOPs (0x90) |
| `EmitTag_Dump` | — | void | Print all tags |

---

## 7. ELF OUTPUT FUNCTIONS

### CELFBuilder
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `ELF_Init` | — | void | Allocate output buffer |
| `ELF_Free` | — | void | Deallocate buffer |
| `ELF_WriteByte` | b:Integer | void | Write byte to ELF buffer |
| `ELF_WriteWord` | w:Integer | void | Write 16-bit LE |
| `ELF_WriteDWord` | d:Integer | void | Write 32-bit LE |
| `ELF_WriteQWord` | q:Integer | void | Write 64-bit LE |
| `ELF_WriteBytes` | ptr, count | void | Copy bytes |
| `ELF_WriteZeros` | count:Integer | void | Write zeros |
| `ELF_Align` | align:Integer | void | Pad to alignment |
| `ELF_WriteHeader` | entry, phoff, ... | void | Write 64-byte ELF header |
| `ELF_WriteProgramHeader` | type, flags, offset, ... | void | Write 56-byte PHDR |
| `ELF_Build` | code, code_size, data, data_size | Integer | Build complete ELF |
| `ELF_BuildFromEmit` | — | Integer | Build from Emit buffers |
| `ELF_GetBuffer` | — | Address | Return ELF buffer |
| `ELF_GetSize` | — | Integer | Return ELF size |
| `ELF_WriteFile` | filename:Address | Integer | Write ELF to disk |
| `ELF_AddString` | str:Address | Integer | Add to string table |

### COutput
| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Output_WriteExecutable` | filename:Address | Integer | Write ELF to file |
| `Output_WriteBinary` | filename, code, size | Integer | Write raw binary |
| `Output_WriteData` | filename, data, size | Integer | Write data file |
| `Output_BuildAndWrite` | filename:Address | Integer | Full build pipeline |
| `Output_DumpCode` | max_bytes:Integer | void | Print code hex dump |
| `Output_PrintStats` | — | void | Print compile stats |

---

## 8. IMPORT RESOLVER FUNCTIONS

| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `Import_Init` | — | Address | Allocate state struct |
| `Import_ResolveAll` | ast:Address | Integer | Full resolution pipeline |
| `Import_CopyStr` | str:Address | Address | Duplicate string |
| `Import_StrEqual` | a, b:Address | Integer | String equality check |
| `Import_HashString` | str:Address | Integer | DJB2 hash |
| `Import_GenPrefix` | state:Address | Address | Generate "NSxx_" prefix |
| `Import_RecordSymbol` | state, symbol, mod | void | Track symbol in module |
| `Import_DetectConflicts` | state:Address | void | Find name conflicts |
| `Import_AssignPrefixes` | state:Address | void | Assign NS prefixes |
| `Import_BuildRewriteMap` | state:Address | Address | Build prefixed name map |
| `Import_GetPrefixedFor` | map, symbol, mod | Address | Look up prefixed name |
| `Import_GetSymbolType` | source, start, len | Integer | Detect declaration type |
| `Import_BuildPrefixed` | prefix, symbol | Address | Concatenate prefix_symbol |

---

## 9. OPTIMIZER FUNCTIONS

| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `CompileOptimizer_ConstantFold` | node:Address | Integer | Fold constant expressions |
| `CompileOptimizer_DeadStore` | block:Address | Integer | Eliminate dead stores |
| `CompileOptimizer_JumpThread` | code:Address | Integer | Thread jump chains |
| `OptimizeHoist_FindInvariants` | loop:Address | Integer | Find loop invariants |
| `OptimizeHoist_HoistExpr` | expr, loop | Integer | Move expr before loop |

---

*Document 09 of 10 — Function Catalog*

*Total functions documented: ~250+*
*Compiler version: May 2025*
