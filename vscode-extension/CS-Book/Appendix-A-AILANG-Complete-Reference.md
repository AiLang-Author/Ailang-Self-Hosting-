# Appendix A: AILANG Complete Reference

This appendix provides a quick alphabetical reference to the core keywords, constructs, and built-in operations in AILang. It is not exhaustive (the full language and libraries are documented in the Programming Manuals), but covers the essentials used throughout this book.

## Keywords and Declaration Forms

- `SubRoutine.Name { ... }` — Defines a subroutine (action, no return value).
- `Function.Name { Input: ... Output: ... Body: { ... } }` — Defines a function with explicit contracts.
- `FixedPool.Name { "field": Initialize=... }` — Named compile-time structured shared state (use Direction= attributes on LinkagePool for contracts).
- `LinkagePool.Name { "field": Initialize=..., CanChange=... }` — Record type definition.
- `Pool.Name.Field` — Qualified access to pool fields.
- `Input:`, `Output:` — Parameter sections on Functions. Richer read/write contracts use `Direction=Input|Output|InOut` on LinkagePool fields (enforced when the pool is passed as a Function Input parameter).
- `Body: { ... }` — The executable part of a Function or SubRoutine.
- `ReturnValue(expr)` — Returns a value from a Function.
- `RunTask(Name)` — Executes a SubRoutine.

## Control Flow

- `IfCondition cond ThenBlock: { ... } ElseBlock: { ... }`
- `WhileLoop cond { ... }`
- `Branch expr { Case value: { ... } Default: { ... } }`
- `Fork cond TrueBlock: { ... } FalseBlock: { ... }`
- `ExitLoop` / `BreakLoop`
- `ContinueLoop`
- `TryBlock: { ... } CatchError.Type { ... } FinallyBlock: { ... }`

## Memory and Pointers

- `Allocate(size)` → Address
- `Deallocate(ptr, size)`
- `Dereference(addr)` → value
- `StoreValue(addr, value)`
- `LinkageField(ptr, PoolName, field)` — Safe access to LinkagePool fields.

## Arithmetic and Logic (Named Primary Form)

All have infix equivalents that require explicit parentheses.

- `Add(a, b)`
- `Subtract(a, b)`
- `Multiply(a, b)`
- `Divide(a, b)`
- `Modulo(a, b)`
- `Power(base, exp)`  (infix `^`)
- `EqualTo(a, b)`, `NotEqual(a, b)`
- `GreaterThan`, `LessThan`, `GreaterEqual`, `LessEqual`
- `And`, `Or`, `Not`
- `BitwiseAnd`, `BitwiseOr`, `BitwiseXor`, `LeftShift`, `RightShift`

## Common Built-in Operations

- `PrintMessage(text)`
- `PrintNumber(n)`
- `String.literal "text"`
- `StringLength(str)`
- `StringCompare(a, b)`
- `StringCopy(str)`
- `Array.Create(capacity)`
- `Array.Get(arr, index)`
- `Array.Set(arr, index, value)`
- `Array.Push(arr, value)`
- `Array.Size(arr)`
- `Array.Destroy(arr)`
- `TimeDate.NowMillis()`

## Debug Facilities (development builds)

- `DebugAssert(condition, message)`
- `DebugTrace.Entry(name)`, `DebugTrace.Point(name)`, `DebugTrace.Exit(name)`
- `DebugMemory.Dump(addr, size)`
- `DebugMemory.Pattern(addr, size, pattern)`
- `DebugPerf.Start(label)`, `DebugPerf.End(label)`
- `DebugBreak()`

For the complete and up-to-date reference, including all standard library modules, see the full Programming Manuals directory, especially:

- AILANG Operator's Reference Guide
- Functions & SubRoutines Reference Manual
- Memory Management Reference Manual
- AILANG Debug Programming Manual
- LinkagePool_Pointers Reference Manual

These manuals are the authoritative source and should be consulted when writing production AILang code.