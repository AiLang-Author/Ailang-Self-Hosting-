# AIMacro Language Specification (Project Contract)

This document defines what AIMacro **is**, what the transpiler **must** emit, and
what the runtime **must** provide. It is the contract for closing the 95th-percentile
Python feature gap and building the VM.

**Syntax rule:** Python-like grammar with **`end`** closing blocks (not indentation-only).

---

## 1. Lexical

| Element | Status | Notes |
|---------|--------|-------|
| `#` comments | Required | Line comments |
| Integers | Required | Decimal literals |
| Strings | Required | `"..."` with escapes via codegen |
| Identifiers | Required | `[a-zA-Z_][a-zA-Z0-9_]*` |
| Keywords | Required | See `FixedPool.Token` in `AIMacroCore` |
| Indentation | Ignored for blocks | `end` is authoritative |

### Keywords (parser tokens)

`def`, `end`, `if`, `elif`, `else`, `while`, `for`, `in`, `return`, `pass`,
`break`, `continue`, `try`, `except`, `finally`, `raise`, `import`, `from`,
`class`, `True`, `False`, `None`, `and`, `or`, `not`, `is`

---

## 2. Statements

| Construct | Transpile target | Priority |
|-----------|------------------|----------|
| `def f(a, b): … end` | `Function.f` | P0 |
| `if` / `elif` / `else` | `IfCondition` / `ElseBlock` chains | P0 |
| `while` | `WhileLoop` | P0 |
| `for x in range(n)` | index loop + `AIMacro.Range` | P0 |
| `for x in iterable` | iterator protocol (limited) | P1 |
| `return expr` | `ReturnValue` | P0 |
| `break` / `continue` | `BreakLoop` / `ContinueLoop` | P0 |
| `pass` | empty block / no-op | P0 |
| `x = expr` | assign | P0 |
| `x += expr` (aug assign) | read-modify-write | P0 |
| `try` / `except` / `finally` | exception scaffolding | P1 |
| `raise` | runtime error path | P2 |
| `import m` / `from m import x` | `LibraryImport` emission | P1 |
| `class C: … end` | OOP codegen (`CodeGenOOP`) | P1 |
| `with expr:` | desugar to try/finally | P2 |

---

## 3. Expressions

| Construct | Priority | Notes |
|-----------|----------|-------|
| Binary ops `+ - * / % **` | P0 | `**` → `Math.Power`; `/` integer div per AIMacro |
| Floor div `//` | P0 | `Math.FloorDiv` |
| Comparisons `== != < <= > >=` | P0 | String `==` uses `StringCompare` |
| Boolean `and or not` | P0 | `not` precedence documented in feature_probe |
| Unary `-` | P0 | |
| Function calls | P0 | |
| Method calls `obj.m()` | P1 | String/list/dict dispatch tables in CodeGen4 |
| Subscript `a[i]` | P0 | list + dict |
| Slice `a[i:j]` | P1 | `ListSlice`, `StringSlice` |
| List literal `[1, 2]` | P0 | |
| Dict literal `{k: v}` | P1 | |
| Attribute `obj.attr` | P1 | OOP |
| Ternary | P2 | if not present, defer |

### Not in 95th-percentile scope (explicitly deferred)

- `lambda`, `yield`, `async`/`await`
- Decorators `@`
- List/dict/set comprehensions (P1 stretch — high value)
- f-strings `f"..."` (P1 stretch)
- `match` / `case`
- `*args` / `**kwargs` in user defs (packed call infra exists for codegen)

---

## 4. Builtin functions (codegen mapping)

### P0 — must work in all regression tests

| Python | AILang emission |
|--------|-----------------|
| `print(...)` | `AIMacro.Print` / `SmartPrint` |
| `len(x)` | `SmartLen` / `Hash.Size` / `DictGen_SmartLen` |
| `str(x)` | `AIMacro.Str` |
| `int(x)` | `AIMacro.Int` |
| `bool(x)` | `AIMacro.Bool` |
| `range(n)` / `range(a,b)` | `AIMacro.Range` |
| `input(prompt)` | `AIMacro.Input` |

### P1 — 95th-percentile closure

| Python | AILang emission |
|--------|-----------------|
| `abs min max sum` | `AIMacro.*` |
| `enumerate zip sorted reversed` | `AIMacro.*` |
| `any all round` | `AIMacro.*` |
| `ord chr` | `AIMacro.*` |
| `isinstance type` | `Types.*` / `OOPGen_IsInstance` |
| `open(path)` | `AIMacro.Open` |
| `list dict` | constructors |

### String methods (via `Gen_MethodCallExpr`)

`strip`, `upper`, `lower`, `find`, `startswith`, `endswith`, `split`, `replace`,
`join` — mapped in codegen; verify per `test_string_methods.aim`.

### List methods

`append`, `pop`, `insert`, `remove`, `extend`, `index`, `count`, `copy`, `clear`

### Dict methods

`keys`, `values`, `items`, `get`, `pop`, `update` — via `AIMacroDict` + codegen

---

## 5. Type system (runtime)

`TypeID` constants in `Library.AIMacro.ailang`:

`INT`, `STR`, `LIST`, `DICT`, `BOOL`, `NONE`

`isinstance(x, int)` → `Types.IsInstance(x, TypeID.INT)` at codegen time when
second arg is a type name identifier.

Type **annotations** in source (`def f(x: int)`) are parsed by
`AIMacroTypeAnnotations` — annotations are informational unless extended later.

---

## 6. OOP specification

| Feature | Test file | Codegen module |
|---------|-----------|----------------|
| `class C: … end` | `test_oop_complete.aim` | `CodeGenOOP` |
| `__init__(self, …)` | same | `OOPGen_*` |
| `self.attr` | same | attribute access |
| method calls | same | `METHOD_CALL` nodes |
| inheritance | `super_test.aim` | `SUPER_CALL` |
| `isinstance(obj, Class)` | `test_isinstance.aim` | `OOPGen_IsInstance` |

---

## 7. Generated AILang file structure

Every transpiled module **must** include at minimum:

```ailang
LibraryImport.AIMacro.AIMacro
LibraryImport.AIMacro.AIMacroString
LibraryImport.AIMacro.AIMacroTypes
// + AIMacroDict if dicts used
// + Hash if dicts used

Function.<user_fn> { … }

SubRoutine.Main {
    // call main() if present, or script body
}
```

Codegen **must**:

1. Emit valid AILang that compiles under `ailang.x` without manual edits
2. Preserve Python semantics for integer division and string concat as documented
3. Track string/dict/list variable types for correct `len` and method dispatch
4. Support >6 parameter calls via packed array convention

---

## 8. VM specification (Phase 3 — draft)

### Value model (`AIMValue`)

| Tag | Payload |
|-----|---------|
| INT | integer |
| STR | pointer + length |
| LIST | `Array` handle |
| DICT | `Hash` handle |
| BOOL | 0/1 |
| NONE | sentinel |
| OBJECT | OOP instance ptr |
| FUNC | bytecode closure |

### Opcode categories (target ~40–50, mirror JSVM)

- Stack: `PUSH`, `POP`, `DUP`
- Locals/globals: `LOAD_LOCAL`, `STORE_LOCAL`, `LOAD_GLOBAL`, `STORE_GLOBAL`
- Arithmetic: `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `POW`
- Compare: `EQ`, `NE`, `LT`, `LE`, `GT`, `GE`
- Control: `JMP`, `JMP_IF`, `JMP_IFNOT`, `CALL`, `RET`
- Builtin: `CALL_BUILTIN` (index into builtin table)
- Container: `INDEX_GET`, `INDEX_SET`, `ATTR_GET`, `ATTR_SET`

### VM invariants

- Max stack depth: 16384 (match JSVM)
- Max call frames: 1024
- Step limit configurable (infinite loop guard)
- Errors set `AIMVMState.error` and halt

---

## 9. Acceptance criteria (definition of done)

### Phase 1 — Transpiler hardening

- [ ] All P0 tests in `TEST_MATRIX.md` transpile without error
- [ ] ≥90% of P0 tests compile with `ailang.x`
- [ ] ≥80% of P0 tests produce expected stdout when run
- [ ] Feature scorecard maintained in `STATUS.md`

### Phase 2 — 95th-percentile closure

- [ ] `open` / file read/write working in ≥3 test scripts
- [ ] `import` emits valid `LibraryImport` for ≥3 stdlib shims
- [ ] Dict + OOP comprehensive tests pass end-to-end
- [ ] `try/except` catches runtime errors in VM or transpiled code
- [ ] List comprehension or f-string (at least one) implemented

### Phase 3 — VM runtime

- [ ] `AIMacroCompiler` emits bytecode for P0 subset
- [ ] `AIMacroVM` runs `test_minimal.aim` equivalent without AOT
- [ ] `aimacro_console` can switch `--vm` / `--aot` modes
- [ ] VM passes same P0 matrix as AOT mode