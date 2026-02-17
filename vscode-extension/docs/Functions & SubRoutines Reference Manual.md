# Functions & SubRoutines Reference Manual

## Overview

AI Lang provides two distinct callable code constructs: **Functions** and **SubRoutines**. While they may appear similar, they serve different purposes and have different characteristics. Understanding when to use each is crucial for writing efficient, maintainable AI Lang code.

**Key Distinction:**
- **Functions** return values and can accept parameters with type declarations
- **SubRoutines** perform actions without formal parameter passing, optimized for side effects

---

## Table of Contents

1. [Functions](#functions)
2. [SubRoutines](#subroutines)
3. [Key Differences](#key-differences)
4. [Parameter Passing](#parameter-passing)
5. [Return Values](#return-values)
6. [Calling Conventions](#calling-conventions)
7. [Use Cases](#use-cases)
8. [Best Practices](#best-practices)
9. [Advanced Patterns](#advanced-patterns)
10. [Performance Considerations](#performance-considerations)

---

## Functions

### Definition

Functions are callable units that accept typed parameters and return a value. They follow a structured declaration with explicit input/output specifications.

### Syntax

```ailang
Function.FunctionName {
    Input: param1: Type, param2: Type
    Output: ReturnType
    Body: {
        // Function body
        ReturnValue(result)
    }
}
```

### Basic Example

```ailang
Function.Add {
    Input: a: Integer, b: Integer
    Output: Integer
    Body: {
        result = Add(a, b)
        ReturnValue(result)
    }
}

// Call the function
sum = Add(5, 10)
PrintNumber(sum)  // 15
```

### Multiple Parameters

```ailang
Function.CalculateVolume {
    Input: length: Integer, width: Integer, height: Integer
    Output: Integer
    Body: {
        area = Multiply(length, width)
        volume = Multiply(area, height)
        ReturnValue(volume)
    }
}

vol = CalculateVolume(10, 5, 3)
```

### No Parameters

```ailang
Function.GetPi {
    Output: Integer
    Body: {
        // Return fixed-point representation of Pi
        ReturnValue(31416)
    }
}

pi = GetPi()
```

### LinkagePool Parameters

Functions can accept LinkagePool types as parameters:

```ailang
LinkagePool.Person {
    "name": Initialize=""
    "age": Initialize=0
    "id": Initialize=0
}

Function.GetPersonAge {
    Input: person: LinkagePool.Person
    Output: Integer
    Body: {
        ReturnValue(person.age)
    }
}

// Usage
person = AllocateLinkage(LinkagePool.Person)
person.age = 30

age = GetPersonAge(person)
```

### Complex Return Types

```ailang
Function.CreatePerson {
    Input: name: String, age: Integer
    Output: LinkagePool.Person
    Body: {
        person = AllocateLinkage(LinkagePool.Person)
        person.name = name
        person.age = age
        person.id = GenerateId()
        
        ReturnValue(person)
    }
}
```

---

## SubRoutines

### Definition

SubRoutines are callable units that execute a sequence of statements but don't formally pass parameters or return values. They communicate via global variables or FixedPool state.

### Syntax

```ailang
SubRoutine.RoutineName {
    // Statements
}
```

### Basic Example

```ailang
SubRoutine.PrintGreeting {
    PrintMessage("Hello, World!\n")
}

// Call the subroutine
RunTask(PrintGreeting)
```

### Working with Global State

```ailang
// Global variable for communication
counter = 0

SubRoutine.IncrementCounter {
    counter = Add(counter, 1)
}

SubRoutine.PrintCounter {
    PrintMessage("Counter: ")
    PrintNumber(counter)
    PrintMessage("\n")
}

// Usage
RunTask(IncrementCounter)
RunTask(IncrementCounter)
RunTask(PrintCounter)  // Counter: 2
```

### Using FixedPool for State

```ailang
FixedPool.Stats {
    "total": Initialize=0
    "count": Initialize=0
}

SubRoutine.AddToStats {
    // Assumes 'value' is set globally before calling
    Stats.total = Add(Stats.total, value)
    Stats.count = Add(Stats.count, 1)
}

SubRoutine.PrintAverage {
    IfCondition GreaterThan(Stats.count, 0) ThenBlock: {
        avg = Divide(Stats.total, Stats.count)
        PrintMessage("Average: ")
        PrintNumber(avg)
        PrintMessage("\n")
    }
}

// Usage
value = 10
RunTask(AddToStats)
value = 20
RunTask(AddToStats)
RunTask(PrintAverage)  // Average: 15
```

### Return from SubRoutine

SubRoutines can exit early with ReturnValue:

```ailang
SubRoutine.ProcessData {
    IfCondition EqualTo(data_valid, 0) ThenBlock: {
        PrintMessage("Invalid data\n")
        ReturnValue(0)  // Exit early
    }
    
    // Continue processing
    ProcessValidData()
}
```

---

## Key Differences

### Comparison Table

| Feature | Function | SubRoutine |
|---------|----------|------------|
| Parameters | Explicit, typed | Implicit (global variables) |
| Return Value | Required | Optional (via ReturnValue) |
| Calling | `result = FunctionName(args)` | `RunTask(RoutineName)` |
| State | Parameters + locals | Global + FixedPool |
| Type Safety | Strong (parameter types) | Weak (global state) |
| Performance | Function call overhead | Minimal overhead |
| Use Case | Computation, transformation | Side effects, orchestration |

### When to Use Functions

✓ **Use Functions when:**
- You need to return a value
- You want type-safe parameter passing
- The operation is a pure computation
- You want to enforce input/output contracts
- The code will be reused with different inputs

Example:
```ailang
Function.Factorial {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessEqual(n, 1) ThenBlock: {
            ReturnValue(1)
        }
        
        prev = Factorial(Subtract(n, 1))
        result = Multiply(n, prev)
        ReturnValue(result)
    }
}
```

### When to Use SubRoutines

✓ **Use SubRoutines when:**
- You're performing side effects (I/O, state changes)
- You're orchestrating multiple operations
- You don't need to return a value
- You're working with shared global state
- Performance is critical (minimal overhead)

Example:
```ailang
SubRoutine.InitializeSystem {
    PrintMessage("Initializing...\n")
    Config.status = STATUS_INITIALIZING
    RunTask(LoadConfiguration)
    RunTask(ConnectDatabase)
    Config.status = STATUS_READY
    PrintMessage("System ready\n")
}
```

---

## Parameter Passing

### Function Parameters

Functions use System V AMD64 calling convention for parameters:

**Register allocation:**
```
1st parameter: RDI
2nd parameter: RSI
3rd parameter: RDX
4th parameter: RCX
5th parameter: R8
6th parameter: R9
7th+ parameters: Stack
```

Example with multiple parameters:
```ailang
Function.ProcessRecord {
    Input: id: Integer, value: Integer, flags: Integer, 
           timestamp: Integer, source: Integer, dest: Integer
    Output: Integer
    Body: {
        // All 6 parameters passed in registers
        result = Compute(id, value, flags, timestamp, source, dest)
        ReturnValue(result)
    }
}
```

### SubRoutine Communication

SubRoutines use global variables or FixedPool for data:

```ailang
// Communication variables
input_value = 0
output_result = 0

SubRoutine.DoubleValue {
    output_result = Multiply(input_value, 2)
}

// Usage
input_value = 10
RunTask(DoubleValue)
PrintNumber(output_result)  // 20
```

### Best Practice: Named Communication

```ailang
FixedPool.ProcessorState {
    "input_data": Initialize=0
    "output_data": Initialize=0
    "status": Initialize=0
    "error_code": Initialize=0
}

SubRoutine.ProcessData {
    // Read from input
    data = ProcessorState.input_data
    
    // Validate
    IfCondition EqualTo(data, 0) ThenBlock: {
        ProcessorState.status = STATUS_ERROR
        ProcessorState.error_code = ERR_INVALID_INPUT
        ReturnValue(0)
    }
    
    // Process
    result = TransformData(data)
    
    // Write to output
    ProcessorState.output_data = result
    ProcessorState.status = STATUS_SUCCESS
}
```

---

## Return Values

### Function Returns

Functions **must** return a value:

```ailang
Function.IsEven {
    Input: n: Integer
    Output: Integer
    Body: {
        remainder = Modulo(n, 2)
        IfCondition EqualTo(remainder, 0) ThenBlock: {
            ReturnValue(1)  // True
        } ElseBlock: {
            ReturnValue(0)  // False
        }
        // Compiler ensures all paths return
    }
}
```

### Multiple Return Points

```ailang
Function.SafeDivide {
    Input: a: Integer, b: Integer
    Output: Integer
    Body: {
        // Early return on error
        IfCondition EqualTo(b, 0) ThenBlock: {
            ReturnValue(0)
        }
        
        // Normal computation
        result = Divide(a, b)
        ReturnValue(result)
    }
}
```

### SubRoutine Returns (Optional)

SubRoutines can exit early but don't return values to the caller:

```ailang
SubRoutine.ValidateAndProcess {
    IfCondition LessThan(input_value, 0) ThenBlock: {
        PrintMessage("Invalid input\n")
        error_flag = 1
        ReturnValue(0)  // Exit early
    }
    
    // Continue processing
    ProcessValidInput()
}
```

---

## Calling Conventions

### Calling Functions

Direct call with arguments:

```ailang
result = FunctionName(arg1, arg2, arg3)
```

**Stack before call:**
```
[local variables]
[saved registers]
RSP →
```

**Stack during call:**
```
[local variables]
[saved registers]
[return address]    ← pushed by CALL
RBP → [saved RBP]   ← function prologue
[function locals]
RSP →
```

### Calling SubRoutines

Use RunTask:

```ailang
RunTask(RoutineName)
```

**Compiled to:**
```asm
; Save callee-saved registers
PUSH RBX
PUSH R12
PUSH R13
PUSH R14

; Call subroutine
CALL RoutineName

; Restore registers
POP R14
POP R13
POP R12
POP RBX
```

### Nested Calls

Functions can call other functions:

```ailang
Function.Hypotenuse {
    Input: a: Integer, b: Integer
    Output: Integer
    Body: {
        a_sq = Square(a)
        b_sq = Square(b)
        sum = Add(a_sq, b_sq)
        result = Sqrt(sum)
        ReturnValue(result)
    }
}

Function.Square {
    Input: x: Integer
    Output: Integer
    Body: {
        ReturnValue(Multiply(x, x))
    }
}
```

SubRoutines can call other SubRoutines:

```ailang
SubRoutine.Initialize {
    RunTask(LoadConfig)
    RunTask(ConnectDB)
    RunTask(StartServer)
}

SubRoutine.LoadConfig {
    // Load configuration
}

SubRoutine.ConnectDB {
    // Connect to database
}

SubRoutine.StartServer {
    // Start server
}
```

---

## Use Cases

### Functions: Computations

```ailang
Function.Fibonacci {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessThan(n, 2) ThenBlock: {
            ReturnValue(n)
        }
        
        n1 = Fibonacci(Subtract(n, 1))
        n2 = Fibonacci(Subtract(n, 2))
        ReturnValue(Add(n1, n2))
    }
}
```

### Functions: Data Transformation

```ailang
Function.NormalizeScore {
    Input: score: Integer, max_score: Integer
    Output: Integer
    Body: {
        // Scale to 0-100
        normalized = Divide(Multiply(score, 100), max_score)
        ReturnValue(normalized)
    }
}
```

### SubRoutines: I/O Operations

```ailang
FixedPool.IOState {
    "filename": Initialize=0
    "data": Initialize=0
    "bytes_read": Initialize=0
}

SubRoutine.ReadFile {
    // IOState.filename must be set before calling
    file = FileOpen(IOState.filename)
    IOState.data = FileRead(file)
    IOState.bytes_read = FileSize(file)
    FileClose(file)
}
```

### SubRoutines: State Management

```ailang
FixedPool.SessionState {
    "user_id": Initialize=0
    "logged_in": Initialize=0
    "session_time": Initialize=0
}

SubRoutine.LoginUser {
    // Assumes user_id is set
    SessionState.logged_in = 1
    SessionState.session_time = GetCurrentTime()
    PrintMessage("User logged in\n")
}

SubRoutine.LogoutUser {
    SessionState.logged_in = 0
    SessionState.session_time = 0
    PrintMessage("User logged out\n")
}
```

---

## Best Practices

### 1. Function Naming

Use verb-noun patterns for functions that return values:

```ailang
Function.CalculateTotal { ... }
Function.GetUserName { ... }
Function.FindMaxValue { ... }
Function.ConvertToString { ... }
```

### 2. SubRoutine Naming

Use imperative verbs for SubRoutines that perform actions:

```ailang
SubRoutine.Initialize { ... }
SubRoutine.ProcessData { ... }
SubRoutine.UpdateDisplay { ... }
SubRoutine.CleanupResources { ... }
```

### 3. Single Responsibility

Each function/subroutine should have one clear purpose:

```ailang
// Good - single purpose
Function.IsValidEmail {
    Input: email: String
    Output: Integer
    Body: {
        has_at = StringContains(email, "@")
        has_dot = StringContains(email, ".")
        ReturnValue(And(has_at, has_dot))
    }
}

// Bad - multiple purposes
Function.ValidateAndSendEmail {
    Input: email: String
    Output: Integer
    Body: {
        // Validation AND sending in one function
        // Should be split
    }
}
```

### 4. Parameter Count

Keep parameter counts reasonable:

```ailang
// Good - 3 parameters
Function.CreateDate {
    Input: year: Integer, month: Integer, day: Integer
    Output: Integer
    Body: { ... }
}

// Better - use LinkagePool for many parameters
LinkagePool.DateComponents {
    "year": Initialize=0
    "month": Initialize=0
    "day": Initialize=0
    "hour": Initialize=0
    "minute": Initialize=0
    "second": Initialize=0
}

Function.CreateDateTime {
    Input: components: LinkagePool.DateComponents
    Output: Integer
    Body: { ... }
}
```

### 5. Error Handling

Return error codes or use FixedPool flags:

```ailang
// Function with error return
Function.SafeOperation {
    Input: value: Integer
    Output: Integer
    Body: {
        IfCondition LessThan(value, 0) ThenBlock: {
            ReturnValue(-1)  // Error code
        }
        
        result = ProcessValue(value)
        ReturnValue(result)
    }
}

// SubRoutine with error flag
FixedPool.ErrorState {
    "has_error": Initialize=0
    "error_code": Initialize=0
}

SubRoutine.RiskyOperation {
    TryBlock: {
        PerformOperation()
    } CatchError: {
        ErrorState.has_error = 1
        ErrorState.error_code = ERR_OPERATION_FAILED
    }
}
```

---

## Advanced Patterns

### Higher-Order Functions (Simulation)

While AI Lang doesn't have first-class functions, you can simulate patterns:

```ailang
FixedPool.Operation {
    "type": Initialize=0  // 1=add, 2=multiply, 3=divide
    "operand": Initialize=0
}

Function.ApplyOperation {
    Input: value: Integer
    Output: Integer
    Body: {
        Branch Operation.type {
            Case 1: {
                ReturnValue(Add(value, Operation.operand))
            }
            Case 2: {
                ReturnValue(Multiply(value, Operation.operand))
            }
            Case 3: {
                ReturnValue(Divide(value, Operation.operand))
            }
        }
        ReturnValue(value)
    }
}
```

### State Machine Pattern

```ailang
FixedPool.Machine {
    "state": Initialize=0
}

SubRoutine.ProcessEvent {
    // Assumes event_type is set globally
    
    Branch Machine.state {
        Case STATE_IDLE: {
            RunTask(HandleIdleEvent)
        }
        Case STATE_PROCESSING: {
            RunTask(HandleProcessingEvent)
        }
        Case STATE_ERROR: {
            RunTask(HandleErrorEvent)
        }
    }
}
```

### Recursive Functions

```ailang
Function.GCD {
    Input: a: Integer, b: Integer
    Output: Integer
    Body: {
        IfCondition EqualTo(b, 0) ThenBlock: {
            ReturnValue(a)
        }
        
        remainder = Modulo(a, b)
        result = GCD(b, remainder)
        ReturnValue(result)
    }
}
```

### Builder Pattern

```ailang
FixedPool.BuilderState {
    "width": Initialize=0
    "height": Initialize=0
    "depth": Initialize=0
}

SubRoutine.SetWidth {
    // Assumes width_value is set
    BuilderState.width = width_value
}

SubRoutine.SetHeight {
    BuilderState.height = height_value
}

SubRoutine.SetDepth {
    BuilderState.depth = depth_value
}

Function.Build {
    Output: Integer
    Body: {
        volume = Multiply(BuilderState.width, BuilderState.height)
        volume = Multiply(volume, BuilderState.depth)
        ReturnValue(volume)
    }
}
```

---

## Performance Considerations

### Function Call Overhead

Each function call involves:
1. Save return address (CALL)
2. Push RBP (prologue)
3. Set up stack frame
4. Execute body
5. Restore stack (epilogue)
6. Return (RET)

**Cost:** ~10-20 CPU cycles minimum

### SubRoutine Call Overhead

SubRoutines are lighter:
1. Save callee-saved registers
2. Execute body
3. Restore registers
4. Return

**Cost:** ~5-10 CPU cycles minimum

### Inlining Considerations

For hot paths, consider inlining:

```ailang
// Instead of calling a function repeatedly
WhileLoop LessThan(i, 1000000) {
    result = SimpleAdd(i, 1)  // Million function calls
    i = result
}

// Inline the operation
WhileLoop LessThan(i, 1000000) {
    i = Add(i, 1)  // Direct operation
}
```

### Tail Call Optimization

AI Lang doesn't automatically optimize tail calls, so deep recursion uses stack:

```ailang
// This will use O(n) stack space
Function.SumToN {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessEqual(n, 0) ThenBlock: {
            ReturnValue(0)
        }
        
        prev = SumToN(Subtract(n, 1))
        ReturnValue(Add(n, prev))
    }
}

// Use iteration for better performance
Function.SumToN_Iterative {
    Input: n: Integer
    Output: Integer
    Body: {
        sum = 0
        i = 1
        WhileLoop LessEqual(i, n) {
            sum = Add(sum, i)
            i = Add(i, 1)
        }
        ReturnValue(sum)
    }
}
```

---

## Summary

### Functions

**Purpose:** Return values from computations  
**Strengths:** Type safety, clear contracts, composability  
**Weaknesses:** Call overhead, parameter passing complexity  
**Use for:** Calculations, transformations, queries  

### SubRoutines

**Purpose:** Perform side effects and orchestration  
**Strengths:** Low overhead, simple state management  
**Weaknesses:** Global state dependency, no type safety  
**Use for:** I/O, state changes, system operations  

### Decision Guide

```
Need to return a value? → Function
Performing side effects? → SubRoutine
Type safety important? → Function
Performance critical? → SubRoutine
Many parameters? → Function with LinkagePool
Simple state changes? → SubRoutine with FixedPool
```

---

**Copyright © 2025 Sean Collins, 2 Paws Machine and Engineering**  
**AI Lang Compiler - Functions & SubRoutines Reference Manual**