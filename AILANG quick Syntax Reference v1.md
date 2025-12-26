# AILANG Complete Syntax Reference v1.0

## Comments
```ailang
// Single line comment
/* Multi-line comment */
```

## Types
| Type | Description | Example |
|------|-------------|---------|
| `Integer` | 64-bit signed | `42`, `-100` |
| `Text` | UTF-8 string | `"Hello"` |
| `Boolean` | True/False | `True`, `False` |
| `Address` | Memory pointer | `Allocate(1024)` |
| `Null` | Null value | `Null` |

## Variables & Assignment
```ailang
x = 42
name = "Hello"
ptr = Allocate(100)
```

---

## Functions

### Function Declaration
```ailang
Function.FunctionName {
    Input: param1: Type, param2: Type
    Output: ReturnType
    Body: {
        // statements
        ReturnValue(result)
    }
}
```

### Function Call
```ailang
result = FunctionName(arg1, arg2)
```

### No Parameters
```ailang
Function.GetValue {
    Output: Integer
    Body: {
        ReturnValue(42)
    }
}
```

---

## SubRoutines

### Declaration (no parameters, no return)
```ailang
SubRoutine.DoSomething {
    PrintMessage("Hello\n")
}
```

### Call
```ailang
RunTask(DoSomething)
```

---

## Control Flow

### IfCondition
```ailang
IfCondition condition ThenBlock: {
    // true path
} ElseBlock: {
    // false path
}
```

### WhileLoop
```ailang
WhileLoop condition {
    // loop body
}
```

### ForEvery
```ailang
ForEvery item in collection {
    // process item
}
```

### Fork (mandatory both paths)
```ailang
Fork condition TrueBlock: {
    // true path
} FalseBlock: {
    // false path
}
```

### Branch (switch/case)
```ailang
Branch expression {
    Case value1: {
        // statements
    }
    Case value2: {
        // statements
    }
    Default: {
        // default statements
    }
}
```

### TryBlock/CatchError
```ailang
TryBlock: {
    // risky code
} CatchError: {
    // error handling
} FinallyBlock: {
    // cleanup (always runs)
}
```

---

## Operators

### Arithmetic
| Function | Symbol | Example |
|----------|--------|---------|
| `Add(a, b)` | `+` | `(a + b)` |
| `Subtract(a, b)` | `-` | `(a - b)` |
| `Multiply(a, b)` | `*` | `(a * b)` |
| `Divide(a, b)` | `/` | `(a / b)` |
| `Modulo(a, b)` | `%` | `(a % b)` |
| `Power(a, b)` | `^` | `(a ^ b)` |

### Comparison
| Function | Symbol | Example |
|----------|--------|---------|
| `EqualTo(a, b)` | `==` | `(a == b)` |
| `NotEqual(a, b)` | `!=` | `(a != b)` |
| `LessThan(a, b)` | `<` | `(a < b)` |
| `GreaterThan(a, b)` | `>` | `(a > b)` |
| `LessEqual(a, b)` | `<=` | `(a <= b)` |
| `GreaterEqual(a, b)` | `>=` | `(a >= b)` |

### Logical
| Function | Symbol | Example |
|----------|--------|---------|
| `And(a, b)` | `&&` | `(a && b)` |
| `Or(a, b)` | `\|\|` | `(a \|\| b)` |
| `Not(a)` | `!` | `!a` or `(!a)` |

### Bitwise
| Function | Symbol | Notes |
|----------|--------|-------|
| `BitwiseAnd(a, b)` | `&` | `(a & b)` |
| `BitwiseOr(a, b)` | `\|` | `(a \| b)` |
| `BitwiseXor(a, b)` | — | **NO symbol** (use function) |
| `BitwiseNot(a)` | `~` | `~a` |
| `LeftShift(a, n)` | `<<` | `(a << n)` |
| `RightShift(a, n)` | `>>` | `(a >> n)` |

**⚠️ CRITICAL:** `^` is **POWER**, not XOR! Use `BitwiseXor()` for XOR.

### Infix Rules
- All infix operations **require parentheses**: `(a + b)`
- Nested: `((a + b) * c)`
- Invalid: `a + b` (no parentheses)

---

## Memory Operations

| Function | Description |
|----------|-------------|
| `Allocate(size)` | Allocate bytes, returns address |
| `Deallocate(addr, size)` | Free memory |
| `StoreValue(addr, value)` | Write to address |
| `Dereference(addr)` | Read 8 bytes from address |
| `Dereference(addr, "byte")` | Read 1 byte |
| `Dereference(addr, "word")` | Read 2 bytes |
| `Dereference(addr, "dword")` | Read 4 bytes |
| `Dereference(addr, "qword")` | Read 8 bytes |
| `GetByte(addr, index)` | Read byte at offset |
| `SetByte(addr, index, value)` | Write byte at offset |
| `AddressOf(variable)` | Get address of variable |

---

## String Operations

| Function | Description |
|----------|-------------|
| `StringLength(str)` | Get string length |
| `StringConcat(a, b)` | Concatenate strings |
| `StringCompare(a, b)` | Compare (0=equal) |
| `StringCopy(str)` | Duplicate string |
| `StringCharAt(str, index)` | Get char at position |

---

## I/O Operations

| Function | Description |
|----------|-------------|
| `PrintMessage("text")` | Print literal text |
| `PrintNumber(value)` | Print integer |
| `PrintString(addr)` | Print null-terminated string |
| `ReadLine()` | Read line from stdin |

---

## Pool Types

### FixedPool (global static variables)
```ailang
FixedPool.Config {
    "max_size": Initialize=1024, CanChange=True
    "version": Initialize=1, CanChange=False
}

// Access
Config.max_size = 2048
value = Config.version
```

### DynamicPool (growable heap)
```ailang
DynamicPool.Cache {
    "entries": Initialize=0
    "count": Initialize=0
}
```

### LinkagePool (structured data blocks)
```ailang
LinkagePool.Person {
    "name": Initialize=0
    "age": Initialize=0
    "id": Initialize=0
}

// Allocate and use
person = AllocateLinkage(LinkagePool.Person)
person.name = "Alice"
person.age = 30
FreeLinkage(person)
```

---

## Arrays

| Function | Description |
|----------|-------------|
| `ArrayCreate(size)` | Create array |
| `ArrayGet(arr, index)` | Get element |
| `ArraySet(arr, index, value)` | Set element |
| `ArrayLength(arr)` | Get length |

---

## Library Import
```ailang
LibraryImport.Path.To.Module
```

---

## Program Control

| Function | Description |
|----------|-------------|
| `HaltProgram()` | Exit program |
| `HaltProgram("message")` | Exit with message |
| `ReturnValue(value)` | Return from function |
| `BreakLoop` | Exit loop (use flag workaround) |

---

## Debug (compile with -D flag)
```ailang
DebugAssert(condition, "message")
DebugTrace.Entry("label", value)
DebugTrace.Exit("label", value)
DebugPerf.Start("label")
DebugPerf.End("label")
```

---

## Complete Example

```ailang
LibraryImport.Library.XArrays

FixedPool.State {
    "count": Initialize=0, CanChange=True
}

Function.Factorial {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessEqual(n, 1) ThenBlock: {
            ReturnValue(1)
        }
        prev = Factorial(Subtract(n, 1))
        ReturnValue(Multiply(n, prev))
    }
}

SubRoutine.Main {
    PrintMessage("Factorial Calculator\n")
    
    i = 1
    WhileLoop LessEqual(i, 10) {
        result = Factorial(i)
        PrintNumber(i)
        PrintMessage("! = ")
        PrintNumber(result)
        PrintMessage("\n")
        i = Add(i, 1)
    }
    
    State.count = 10
    PrintMessage("Computed ")
    PrintNumber(State.count)
    PrintMessage(" factorials\n")
}
```

---

## Quick Reminders

1. **Parentheses required** for all infix: `(a + b)` not `a + b`
2. **`^` is POWER** not XOR — use `BitwiseXor()`
3. **Null-terminate strings** manually with `SetByte(addr, len, 0)`
4. **Always `Deallocate`** what you `Allocate`
5. **Use `"byte"` hint** when reading single bytes
6. **Function names are PascalCase**: `PrintMessage`, `WhileLoop`
7. **Pool access uses dot notation**: `PoolName.field`

---

SEE PROGRAMMING MANUAL FOLDER FOR MORE 

*AILANG v2.0 — Sean Collins, 2 Paws Machine and Engineering*