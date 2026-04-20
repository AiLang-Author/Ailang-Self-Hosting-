# AiLang Stdlib Index — LLM Quick Reference

One-page index of what's available to an LLM writing AiLang code in this
repo. Catalog, not tutorial. File paths are absolute under
`/mnt/c/Users/Sean/Documents/AILangSH/`.

---

## 1. Compiler built-in intrinsics

Called without any `LibraryImport` — the compiler's FPU / codegen
dispatcher recognises these by name and emits SSE / scalar x86-64 for
them directly.

**Source:** `Librarys/Compiler/Compile/FPU/X86/`

### Memory ops (SSE-accelerated)

| Intrinsic         | Args                  | Notes                                    |
|-------------------|-----------------------|------------------------------------------|
| `MemoryCopy`      | dest, src, count      | memcpy; old name `MemCopy` is **gone**.  |
| `MemorySet`       | dest, byte, count     | memset; old name `MemSet` is **gone**.   |
| `MemCompare`      | a, b, count           | returns 0 = equal.                       |
| `MemChr`          | buf, byte, count      | returns offset or -1.                    |

If the compiler says `Unknown function: MemCopy` / `MemSet`, swap for
the `Memory*` form above.

### Float / SIMD (`Library.FPUCompileX86SSE.ailang`)

| Group             | Names                                                          |
|-------------------|----------------------------------------------------------------|
| Arithmetic        | `Float_Add`, `Float_Sub`, `Float_Mul`, `Float_Div`, `Float_Min`, `Float_Max`, `Float_Sqrt` |
| Conversion        | `Float_FromInt`, `Float_ToInt`, `Float_Round`                   |
| Comparison (→0/1) | `Float_Eq`, `Float_Ne`, `Float_Lt`, `Float_Gt`, `Float_Le`, `Float_Ge` |
| Vec2              | `Vec2_Add`, `Vec2_Sub`, `Vec2_Mul`, `Vec2_Dot`                  |
| Integer           | `ISqrt`, `SquareRoot`, `Abs`, `Min`, `Max`                      |

### Core arithmetic / bitwise primitives

| Primitive                 | Purpose                        |
|---------------------------|--------------------------------|
| `Add`, `Subtract`, `Multiply`, `Divide`, `Modulo` | 64-bit integer math |
| `BitwiseAnd`, `BitwiseOr`, `BitwiseXor` | bitwise ops          |
| `EqualTo`, `NotEqual`, `LessThan`, `GreaterThan`, `LessEqual`, `GreaterEqual` | comparison → 0/1 |
| `And`, `Or`               | short-circuit logical          |
| `GetByte`, `SetByte`      | load/store 8-bit               |
| `Dereference`, `StoreValue` | load/store 64-bit            |
| `Allocate`, `Deallocate`  | **requires `LibraryImport.Arena`** |
| `StringLength`, `StringCompare`, `StringConcat` | null-terminated strings |
| `SystemCall(nr, …)`       | raw Linux syscall              |
| `RunTask(SubRoutineName)` | entry point at bottom of file  |

---

## 2. Runtime libraries (`LibraryImport.<Name>`)

Each lives at `Librarys/Library.<Name>.ailang`.

### Arena — slab allocator (`LibraryImport.Arena`)

Mandatory if you call `Allocate` or `Deallocate`.

| Function           | Signature                                  |
|--------------------|--------------------------------------------|
| `Arena_Init`       | () → Integer                               |
| `Arena_Alloc`      | (size: Integer) → Address                  |
| `Arena_Free`       | (ptr: Address, size: Integer)              |
| `Arena_Reset`      | ()                                         |
| `Arena_Report`     | ()                                         |

In practice you just call `Allocate(size)` / `Deallocate(ptr, size)` —
Arena routes them.

### StringUtils (`LibraryImport.StringUtils`)

| Function           | Signature                                  |
|--------------------|--------------------------------------------|
| `StrLen`           | (str: Address) → Integer                   |
| `StrToNum`         | (str: Address) → Integer                   |
| `StrFindChar`      | (str, ch) → Integer  (pos or -1)           |
| `StrCompare`       | (s1, s2) → Integer  (0 = equal)            |
| `StrStartsWith`    | (str, prefix) → 0/1                        |
| `StrSubstring`     | (str, start, len) → Address (owned)        |
| `StrSplit`         | (str, delim) → Address (XArray of parts)   |

### XArrays — dynamic array (`LibraryImport.XArrays`)

| Function                 | Signature                          |
|--------------------------|------------------------------------|
| `XArray.XCreate`         | (capacity) → Address               |
| `XArray.XSize`           | (arr) → Integer                    |
| `XArray.XPush`           | (arr, value) → Integer             |
| `XArray.XPop`            | (arr) → Integer                    |
| `XArray.XGet` / `XSet`   | (arr, index[, value])              |

### HashMap — string-keyed map (`LibraryImport.HashMap`)

Best for lookup tables with non-tiny keyspace (use a flat 256-byte
array for byte→byte like tr). Depends on XArrays, StringUtils.

| Function               | Signature                             |
|------------------------|---------------------------------------|
| `HashMap.Create`       | (capacity) → Address                  |
| `HashMap.Set`          | (map, key, value) → Integer           |
| `HashMap.Get`          | (map, key) → Integer                  |
| `HashMap.Delete`       | (map, key) → Integer                  |
| `HashMap.Exists`       | (map, key) → 0/1                      |
| `HashMap.Destroy`      | (map)                                 |

### JSON (`LibraryImport.JSON`, requires XArrays + StringUtils)

`JSON.Tag`, `JSON.TagType`, `JSON.TagValue`, `JSON.AsObject`,
`JSON.AsArray`, `JSON.AsString`, `JSON.AsNumber`, `JSON.AsBool`,
`JSON.ArrayLength`, `JSON.ArrayGet`.

### CSV (`LibraryImport.CSV`, requires XArrays)

`CSV_Parser_Create(data, len)`, `CSV_Parser_Peek(parser)`,
`CSV_LoadFile(filename)`, `CSV_SaveFile(doc, filename)`.

### Socket (`LibraryImport.Socket`) — raw syscall-backed BSD sockets

| Function              | Signature                             |
|-----------------------|---------------------------------------|
| `Socket.CreateAddr`   | (host, port) → Address                |
| `Socket.Create`       | (family, type) → Integer (fd)         |
| `Socket.Connect`      | (sock, addr) → Integer                |
| `Socket.Send`         | (sock, buf, len) → Integer            |
| `Socket.Recv`         | (sock, buf, max) → Integer            |
| `Socket.RecvExact`    | (sock, buf, len) → Integer            |

---

## 3. Linux syscalls used across CoreUtils

`SystemCall(nr, arg1, arg2, …)` — up to 6 args.

| Nr  | Call       | Typical use                      |
|-----|------------|----------------------------------|
| 0   | read       | `SystemCall(0, fd, buf, count)`  |
| 1   | write      | `SystemCall(1, fd, buf, count)`  |
| 2   | open       | `SystemCall(2, path, flags, mode)` |
| 3   | close      | `SystemCall(3, fd)`              |
| 8   | lseek      |                                   |
| 9   | mmap       |                                   |
| 11  | munmap     |                                   |
| 41  | socket     |                                   |
| 42  | connect    |                                   |
| 54  | setsockopt |                                   |
| 60  | exit       | `SystemCall(60, exit_code)`      |
| 257 | openat     | `SystemCall(257, -100, path, 0, 0)` with AT_FDCWD |

---

## 4. Language syntax — learned gotchas

### Must-knows

- **Newlines separate statements.** Semicolons are **not** statement
  separators — putting two statements on one line with `;` triggers
  `PARSE ERROR: Unexpected token in statement`.
- **ASCII only in source.** Unicode glyphs (arrows, em-dashes, smart
  quotes) in **comments or strings** cause parse errors. Stick to ASCII.
- **String literals are limited to ~255 chars.** Split long messages
  into multiple `WriteStderr(...)` / `WriteStdoutStr(...)` calls.
- **Imports are top-level statements**, not decorators. Put
  `LibraryImport.<Name>` above every `FixedPool` / `Function` block.
- If you use `Allocate` / `Deallocate` anywhere, **you must add
  `LibraryImport.Arena`** or the binary silently fails at runtime
  (misbehaves rather than crashes cleanly).

### Canonical syntax shapes

Variable: assign freely (`x = 0`), no type keyword.

Pool (shared state, like global struct):
```
FixedPool.MyState {
    "slot_a": Initialize=0
    "slot_b": Initialize=42
}
// access:  MyState.slot_a = 5
```

Function:
```
Function.Foo {
    Input: x: Integer
    Input: buf: Address
    Output: Integer
    Body: {
        ...
        ReturnValue(result)
    }
}
```

Entry point:
```
SubRoutine.Main {
    ...
    SystemCall(60, 0)
}
RunTask(Main)
```

Conditional / loop:
```
IfCondition EqualTo(x, 0) ThenBlock: {
    ...
} ElseBlock: {
    ...
}

WhileLoop LessThan(i, n) {
    ...
    IfCondition cond ThenBlock: { BreakLoop }
    ContinueLoop
}

WhileLoop 1 {           // infinite loop pattern
    ...
    BreakLoop
}
```

---

## 5. CoreUtil idioms worth copying

### Buffered stdout (cut.ailang pattern)

See `AiLang_CoreUtils/dist/cut_util/cut.ailang` lines ~95-130:

```
FixedPool.OutputBuffer { "buffer": Initialize=0, "position": Initialize=0 }

Function.InitOutputBuffer { Body: {
    OutputBuffer.buffer = Allocate(CONST.BUF_SIZE)
    OutputBuffer.position = 0
} }

Function.FlushOutputBuffer { Body: {
    IfCondition GreaterThan(OutputBuffer.position, 0) ThenBlock: {
        SystemCall(1, 1, OutputBuffer.buffer, OutputBuffer.position)
        OutputBuffer.position = 0
    }
} }
```

### Stderr helper

```
Function.WriteStderr {
    Input: str: Address
    Body: {
        len = StringLength(str)
        SystemCall(1, 2, str, len)     // fd 2 = stderr
    }
}
```

### Stdout NUL-terminated string helper

```
Function.WriteStdoutStr {
    Input: str: Address
    Body: {
        len = StringLength(str)
        SystemCall(1, 1, str, len)
    }
}
```

### Arg parsing from `/proc/self/cmdline`

Canonical implementation: `AiLang_CoreUtils/dist/head_util/head.ailang`
Main (lines ~330-440). Pattern:

1. `openat(AT_FDCWD=-100, "/proc/self/cmdline", 0, 0)` via
   `SystemCall(257, -100, "/proc/self/cmdline", 0, 0)`.
2. Read 4096 bytes into an `Allocate`d buffer.
3. Walk the NUL-separated args byte-by-byte, skipping argv[0] first.
4. Flags detected by `GetByte(buf, p) == 45` (`-`) + second byte.
5. Either copy the arg into a fresh `Allocate` or keep a pointer
   `Add(buf, start)` into the cmdline buffer.

The tr / cut rewrites use a helper `NextArg(buf, limit)` that returns
a pointer to the next NUL-terminated arg without copying — preferred
when you're going to pass the pointer straight into table builders.

---

## 6. Known-current vs known-stale

- Current coreutil compiler:  `AILangSH/ailang6.x`
- Reference good-source coreutils (ported to `ailang6.x`):
  - `AiLang_CoreUtils/dist/head_util/head.ailang`
  - `AiLang_CoreUtils/dist/cut_util/cut.ailang`
  - `AiLang_CoreUtils/dist/tr_util/tr.ailang`
- Everything else in `AiLang_CoreUtils/dist/*/*.ailang` predates the
  `MemCopy → MemoryCopy` rename and the Arena restructure. Assume each
  needs at minimum:
  1. `LibraryImport.Arena` at the top.
  2. `MemCopy` → `MemoryCopy`, `MemSet` → `MemorySet` (where used).
  3. ASCII-only source.
  4. No `;` statement separators.
