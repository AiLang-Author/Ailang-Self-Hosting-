# AILANG Debug System Manual
## Version 2.0 - Self-Hosting Compiler

---

## Table of Contents

1. [Overview](#overview)
2. [Debug Levels](#debug-levels)
3. [Compilation Flags](#compilation-flags)
4. [Debug Blocks](#debug-blocks)
5. [Debug Assertions](#debug-assertions)
6. [Debug Tracing](#debug-tracing)
7. [Debug Breakpoints](#debug-breakpoints)
8. [Performance Profiling](#performance-profiling)
9. [Memory Debugging](#memory-debugging)
10. [Debug Inspection](#debug-inspection)
11. [Patterns and Examples](#patterns-and-examples)
12. [Performance Considerations](#performance-considerations)
13. [Compiler Implementation](#compiler-implementation)

---

## Overview

AILANG provides a comprehensive built-in debug system as a language primitive. Unlike external debuggers, AILANG's debug features are part of the language itself, enabling:

- **Zero-overhead production builds** - Debug code compiles to NOPs when disabled
- **Conditional compilation** - Debug blocks only compile when the required level is met
- **Progressive detail levels** - Fine-grained control from basic assertions to full tracing
- **Native integration** - Debug primitives understand AILANG's memory model and constructs

### Design Philosophy

1. **Zero Cost Abstraction** - Disabled debug code has no runtime overhead
2. **Hierarchical Levels** - Higher levels include all lower-level features
3. **Source Integration** - Debug logic lives in your source code, not external tools
4. **Self-Documenting** - Debug blocks serve as inline documentation of expectations

---

## Debug Levels

AILANG uses a hierarchical debug level system (0-4). Higher levels include all features of lower levels.

| Level | Name | Features | Use Case |
|-------|------|----------|----------|
| 0 | Production | All debug code stripped | Release builds |
| 1 | Basic | `DebugAssert` only | Testing, QA |
| 2 | Trace | + `Debug` blocks (level 1-2) | Development |
| 3 | Detailed | + Memory inspection, level 3 blocks | Complex debugging |
| 4 | Full | + Breakpoints, all blocks | Deep investigation |

### Level Details

**Level 0 (Production)**
- All debug statements compile to single-byte NOPs
- Zero runtime overhead
- Binary size minimally affected
- Use for all production releases

**Level 1 (Basic)**
- `DebugAssert` statements are active
- Assertions halt program on failure with message
- Minimal performance impact (~1-2%)
- Use for testing and quality assurance

**Level 2 (Trace)**
- Debug blocks with `level=1` and `level=2` execute
- Function entry/exit tracing available
- Variable inspection points active
- Use during active development

**Level 3 (Detailed)**
- All Level 2 features plus level 3 blocks
- Memory debugging features active
- Detailed state inspection available
- Use for investigating complex bugs

**Level 4 (Full)**
- All debug features active
- `DebugBreak` emits INT3 instructions
- Interactive debugging support
- Use for deep debugging sessions

---

## Compilation Flags

### Command Line

```bash
# Production build (level 0, default)
./compiler.x program.ailang

# Basic debugging (level 1)
./compiler.x -D program.ailang
./compiler.x -D1 program.ailang

# Trace debugging (level 2)
./compiler.x -D2 program.ailang

# Detailed debugging (level 3)
./compiler.x -D3 program.ailang

# Full debugging (level 4)
./compiler.x -D4 program.ailang

# Enable performance profiling
./compiler.x -P program.ailang

# Combine flags
./compiler.x -D2 -P program.ailang
```

### Console Commands

```
ailang> debug 0        # Set to production
ailang> debug 1        # Set to basic
ailang> debug 2        # Set to trace
ailang> debug 3        # Set to detailed
ailang> debug 4        # Set to full
ailang> perf on        # Enable profiling
ailang> perf off       # Disable profiling
```

---

## Debug Blocks

Conditional code blocks that only compile when the debug level meets the requirement.

### Syntax

```ailang
Debug("label", level=N) {
    // Code here only compiles if debug level >= N
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| label | String | Yes | Identifier for the debug block |
| level | Integer | No | Minimum debug level (default: 1) |

### Behavior

- Block compiles only if current debug level ≥ specified level
- Below required level: entire block becomes a single NOP
- Label helps identify debug output and aids in filtering
- Can contain any valid AILANG statements

### Examples

```ailang
// Basic debug output (level 1+)
Debug("startup", level=1) {
    PrintMessage("Application starting...\n")
}

// Variable inspection (level 2+)
Debug("state check", level=2) {
    PrintMessage("Current counter: ")
    PrintNumber(counter)
    PrintMessage("\n")
}

// Detailed memory state (level 3+)
Debug("memory analysis", level=3) {
    PrintMessage("Buffer address: ")
    PrintNumber(buffer_ptr)
    PrintMessage(" Size: ")
    PrintNumber(buffer_size)
    PrintMessage("\n")
}

// Interactive checkpoint (level 4 only)
Debug("checkpoint", level=4) {
    PrintMessage("=== CHECKPOINT: About to process data ===\n")
    DebugBreak("pre-process")
}
```

### Nested Blocks

Debug blocks can be nested. Inner blocks only execute if both their level AND the outer block's level are met.

```ailang
Debug("outer", level=2) {
    PrintMessage("Outer block executing\n")
    
    Debug("inner", level=3) {
        // Only executes at level 3+
        PrintMessage("Inner block (detailed)\n")
    }
}
```

---

## Debug Assertions

Runtime validation that halts execution on failure.

### Syntax

```ailang
DebugAssert(condition, "message")
DebugAssert(condition)  // Message optional
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| condition | Expression | Yes | Boolean expression to validate |
| message | String | No | Message displayed on failure |

### Behavior

- Active at debug level 1 and above
- Evaluates condition at runtime
- If true (non-zero): continues execution
- If false (zero): prints message and exits with code 1
- At level 0: compiles to NOP

### Examples

```ailang
// Basic null check
DebugAssert(NotEqual(ptr, 0), "Null pointer")

// Range validation
DebugAssert(And(GreaterEqual(index, 0), LessThan(index, array_size)), 
            "Index out of bounds")

// Postcondition check
result = Calculate(x, y)
DebugAssert(GreaterEqual(result, 0), "Calculation returned negative")

// Without message
DebugAssert(GreaterThan(count, 0))
```

### Failure Output

When an assertion fails:

```
ASSERTION FAILED: Index out of bounds
```

Program exits with code 1.

---

## Debug Tracing

Track function execution flow and variable values.

### Syntax

```ailang
DebugTrace.Entry("function_name", param1, param2, ...)
DebugTrace.Exit("function_name", return_value)
DebugTrace.Point("label", value)
```

### Behavior

- Active at debug level 2 and above
- `Entry`: Log function entry with parameters
- `Exit`: Log function exit with return value
- `Point`: Log arbitrary checkpoint with value

### Examples

```ailang
Function.ProcessOrder {
    Input: order_id: Integer
    Input: quantity: Integer
    Output: Integer
    Body: {
        DebugTrace.Entry("ProcessOrder", order_id, quantity)
        
        total = Multiply(quantity, GetPrice(order_id))
        
        DebugTrace.Point("calculated_total", total)
        
        IfCondition LessThan(total, 0) ThenBlock: {
            DebugTrace.Exit("ProcessOrder", -1)
            ReturnValue(-1)
        }
        
        DebugTrace.Exit("ProcessOrder", total)
        ReturnValue(total)
    }
}
```

### Output Format

```
[TRACE] ENTRY ProcessOrder(42, 5)
[TRACE] POINT calculated_total = 250
[TRACE] EXIT ProcessOrder -> 250
```

---

## Debug Breakpoints

Insert software breakpoints for debugger interaction.

### Syntax

```ailang
DebugBreak("label")
```

### Behavior

- Active at debug level 4 only
- Emits x86 INT3 instruction (0xCC)
- Triggers debugger breakpoint trap
- Without debugger: causes SIGTRAP (program terminates)
- Below level 4: compiles to NOP

### Examples

```ailang
Function.CriticalOperation {
    Body: {
        // Break before dangerous operation
        DebugBreak("pre-critical")
        
        PerformCriticalWork()
        
        // Break after to inspect results
        DebugBreak("post-critical")
    }
}
```

### Usage with GDB

```bash
# Compile with full debug
./compiler.x -D4 program.ailang -o program.x

# Run under GDB
gdb ./program.x
(gdb) run
# Program stops at DebugBreak points
(gdb) info registers
(gdb) continue
```

---

## Performance Profiling

Measure execution time of code sections using CPU cycle counter.

### Syntax

```ailang
DebugPerf.Start("label")
// ... code to profile ...
DebugPerf.End("label")

DebugPerf.Mark("checkpoint")
```

### Behavior

- Requires `-P` flag to enable
- Uses RDTSC/RDTSCP instructions for cycle-accurate timing
- `Start`: Records start timestamp
- `End`: Records end timestamp, calculates duration
- `Mark`: Records single timestamp marker
- Without `-P`: compiles to NOPs

### Examples

```ailang
Function.OptimizedSort {
    Input: arr: Address
    Input: size: Integer
    Body: {
        DebugPerf.Start("total_sort")
        
        DebugPerf.Start("partition")
        pivot = Partition(arr, size)
        DebugPerf.End("partition")
        
        DebugPerf.Start("recursion")
        QuickSort(arr, pivot)
        QuickSort(Add(arr, Multiply(pivot, 8)), Subtract(size, pivot))
        DebugPerf.End("recursion")
        
        DebugPerf.End("total_sort")
    }
}
```

### Output

```
[PERF] partition: 12,456 cycles
[PERF] recursion: 89,234 cycles
[PERF] total_sort: 102,891 cycles
```

---

## Memory Debugging

Inspect and validate memory state.

### Syntax

```ailang
DebugMemory.Dump(address, size, "label")
DebugMemory.Watch(address, "label")
DebugMemory.Pattern(address, size, pattern)
DebugMemory.Leak.Start()
DebugMemory.Leak.Check()
```

### Behavior

- Active at debug level 3 and above
- `Dump`: Hex dump memory region
- `Watch`: Monitor address for changes (future)
- `Pattern`: Fill memory with pattern (e.g., 0xDEADBEEF)
- `Leak.Start/Check`: Track allocations for leak detection

### Examples

```ailang
Function.ProcessBuffer {
    Input: data: Address
    Input: size: Integer
    Body: {
        DebugMemory.Leak.Start()
        
        buffer = Allocate(1024)
        
        Debug("buffer state", level=3) {
            DebugMemory.Dump(buffer, 64, "allocated buffer")
            DebugMemory.Pattern(buffer, 1024, 0xDEADBEEF)
        }
        
        ProcessData(buffer, data, size)
        
        Deallocate(buffer, 1024)
        
        DebugMemory.Leak.Check()  // Warns if leaks detected
    }
}
```

---

## Debug Inspection

Examine runtime state.

### Syntax

```ailang
DebugInspect.Variables()
DebugInspect.Stack()
DebugInspect.Pools()
```

### Behavior

- Active at debug level 3 and above
- `Variables`: Dump all variables in current scope
- `Stack`: Show current stack frame
- `Pools`: Display FixedPool and DynamicPool states

### Examples

```ailang
Function.ComplexCalculation {
    Input: x: Integer
    Input: y: Integer
    Body: {
        temp1 = Add(x, y)
        temp2 = Multiply(x, y)
        
        Debug("inspect", level=3) {
            DebugInspect.Variables()
            // Output: x=5, y=3, temp1=8, temp2=15
        }
        
        result = Divide(temp2, temp1)
        ReturnValue(result)
    }
}
```

---

## Patterns and Examples

### Pattern 1: Progressive Debug Detail

```ailang
Function.ProcessData {
    Input: data: Address
    Input: size: Integer
    Output: Integer
    Body: {
        // Always validate (level 1+)
        DebugAssert(NotEqual(data, 0), "Null data pointer")
        DebugAssert(GreaterThan(size, 0), "Invalid size")
        
        // Basic trace (level 2+)
        Debug("trace", level=2) {
            PrintMessage("[ProcessData] Starting, size=")
            PrintNumber(size)
            PrintMessage("\n")
        }
        
        // Detailed state (level 3+)
        Debug("state", level=3) {
            DebugMemory.Dump(data, 32, "input data")
        }
        
        result = DoProcessing(data, size)
        
        // Validate result
        DebugAssert(GreaterEqual(result, 0), "Processing failed")
        
        Debug("trace", level=2) {
            PrintMessage("[ProcessData] Complete, result=")
            PrintNumber(result)
            PrintMessage("\n")
        }
        
        ReturnValue(result)
    }
}
```

### Pattern 2: Performance Analysis

```ailang
Function.RenderFrame {
    Body: {
        DebugPerf.Start("frame")
        
        DebugPerf.Start("physics")
        UpdatePhysics()
        DebugPerf.End("physics")
        
        DebugPerf.Start("ai")
        UpdateAI()
        DebugPerf.End("ai")
        
        DebugPerf.Start("render")
        DrawScene()
        DebugPerf.End("render")
        
        DebugPerf.End("frame")
    }
}
```

### Pattern 3: Memory Safety

```ailang
Function.SafeArrayAccess {
    Input: arr: Address
    Input: index: Integer
    Input: arr_size: Integer
    Output: Integer
    Body: {
        DebugAssert(NotEqual(arr, 0), "Null array")
        DebugAssert(GreaterEqual(index, 0), "Negative index")
        DebugAssert(LessThan(index, arr_size), "Index out of bounds")
        
        value = ArrayGet(arr, index)
        ReturnValue(value)
    }
}
```

### Pattern 4: Error Investigation

```ailang
Function.DiagnoseIssue {
    Input: input: Address
    Body: {
        Debug("entry", level=2) {
            PrintMessage("=== DiagnoseIssue Entry ===\n")
        }
        
        // Checkpoint 1
        step1 = ProcessStep1(input)
        Debug("checkpoint1", level=3) {
            PrintMessage("After Step1: ")
            PrintNumber(step1)
            PrintMessage("\n")
        }
        DebugAssert(NotEqual(step1, -1), "Step1 failed")
        
        // Checkpoint 2
        step2 = ProcessStep2(step1)
        Debug("checkpoint2", level=3) {
            PrintMessage("After Step2: ")
            PrintNumber(step2)
            PrintMessage("\n")
        }
        
        // Full debug for problem area
        Debug("problem_area", level=4) {
            PrintMessage("=== ENTERING PROBLEM AREA ===\n")
            DebugInspect.Variables()
            DebugBreak("investigate")
        }
        
        FinalStep(step2)
    }
}
```

---

## Performance Considerations

### Overhead by Level

| Level | Overhead | Impact |
|-------|----------|--------|
| 0 | None | Zero - NOPs optimized away |
| 1 | Minimal | ~1-2% (assertion checks only) |
| 2 | Low | ~5-10% (traces add I/O) |
| 3 | Moderate | ~15-25% (memory inspection) |
| 4 | High | Variable (breakpoints halt execution) |

### Best Practices

1. **Use appropriate levels** - Don't put level 1 checks in hot loops
2. **Level 4 sparingly** - Breakpoints in loops will halt repeatedly
3. **Profile without debug** - Use `-P` alone for accurate perf data
4. **Production = Level 0** - Always ship with debug disabled
5. **Assertions are cheap** - Use liberally at level 1

### Memory Impact

- Level 0: No additional memory
- Level 1-2: Minimal (string literals for messages)
- Level 3+: Additional buffers for memory tracking
- With `-P`: Perf slot storage (~32 bytes per marker)

---

## Compiler Implementation

### File Structure

```
Librarys/Compiler/Debug/
├── Library.CDebugTypes.ailang      # State and constants
├── Library.CCompileDebug.ailang    # Compile DEBUG_* nodes
└── X86/
    └── Library.CEmitDebugX86.ailang # INT3, RDTSC, NOP
```

### AST Node Types

| Node Type | Value | Description |
|-----------|-------|-------------|
| DEBUG_BLOCK | 900 | Debug block with body |
| DEBUG_ASSERT | 901 | Assertion statement |
| DEBUG_TRACE | 902 | Trace point |
| DEBUG_BREAK | 903 | Breakpoint |

### Token Types

| Token | Value | Keyword |
|-------|-------|---------|
| DEBUG | 21 | Debug |
| DEBUGASSERT | 22 | DebugAssert |
| DEBUGTRACE | 23 | DebugTrace |
| DEBUGBREAK | 24 | DebugBreak |
| DEBUGMEMORY | 25 | DebugMemory |
| DEBUGPERF | 26 | DebugPerf |
| DEBUGINSPECT | 27 | DebugInspect |
| DEBUGCONTROL | 28 | DebugControl |

### Code Generation

**Debug Block (level met):**
```
; Compile body normally
<body instructions>
```

**Debug Block (level not met):**
```
90                  ; NOP
```

**DebugAssert:**
```
<compile condition> ; Result in RAX
48 85 C0           ; TEST RAX, RAX
75 XX              ; JNE pass_label
; Print failure message
; MOV RDI, 1
; MOV RAX, 60 (exit)
; SYSCALL
pass_label:
```

**DebugBreak:**
```
CC                  ; INT3
```

**DebugPerf.Start:**
```
0F 31              ; RDTSC (EDX:EAX = timestamp)
; Store to perf slot
```

---

## Quick Reference

### Debug Statements

| Statement | Min Level | Description |
|-----------|-----------|-------------|
| `Debug("label", level=N) { }` | N | Conditional block |
| `DebugAssert(cond, "msg")` | 1 | Runtime assertion |
| `DebugTrace.Entry(...)` | 2 | Function entry log |
| `DebugTrace.Exit(...)` | 2 | Function exit log |
| `DebugTrace.Point(...)` | 2 | Checkpoint log |
| `DebugBreak("label")` | 4 | Software breakpoint |
| `DebugPerf.Start("label")` | -P flag | Start timer |
| `DebugPerf.End("label")` | -P flag | End timer |
| `DebugMemory.Dump(...)` | 3 | Hex dump |
| `DebugMemory.Leak.Start()` | 3 | Start leak tracking |
| `DebugMemory.Leak.Check()` | 3 | Check for leaks |
| `DebugInspect.Variables()` | 3 | Dump scope vars |

### Command Line Flags

| Flag | Effect |
|------|--------|
| (none) | Level 0 - production |
| `-D` or `-D1` | Level 1 - assertions |
| `-D2` | Level 2 - tracing |
| `-D3` | Level 3 - detailed |
| `-D4` | Level 4 - full |
| `-P` | Enable profiling |

---

*AILANG Debug System v2.0 - Zero-overhead debugging as a language primitive*