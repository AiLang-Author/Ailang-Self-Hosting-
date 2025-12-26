AILANG Debug Programming Manual
Table of Contents

Overview
Debug Levels
Debug Assertions
Debug Blocks
Performance Profiling
Command-Line Options
Examples and Patterns
Performance Considerations
Troubleshooting

Overview
AILANG provides a comprehensive debugging system that enables developers to add diagnostic code that can be conditionally compiled and executed based on debug levels. The debug system is designed for zero-overhead production builds while providing rich debugging capabilities during development.
Core Debug Features

Debug Assertions: DebugAssert for runtime validation
Debug Blocks: Debug() blocks with level-based execution
Performance Profiling: DebugPerf for timing measurements
Conditional Compilation: Debug code compiles to NOPs at level 0
Multi-level Control: Fine-grained control via -D flags

Debug Philosophy

Zero overhead when disabled (production builds)
Progressive detail levels for different debugging needs
Integration with existing code without modification
Runtime control of debug output

Debug Levels
AILANG uses a hierarchical debug level system (0-4) where higher levels include all features of lower levels:
Level 0: Production (Default)

All debug code disabled
Debug statements compile to NOPs
Zero runtime overhead
Use for production releases

Level 1: Basic Validation

Assertions enabled (DebugAssert)
Critical error checking
Minimal performance impact
Use for testing and QA

Level 2: Tracing

All Level 1 features
Debug blocks up to level 2 execute
Function entry/exit traces
Variable inspection points
Use for development debugging

Level 3: Detailed Analysis

All Level 2 features
Debug blocks up to level 3 execute
Memory inspection
Watchpoint simulation
Concurrency checks
Use for complex debugging

Level 4: Interactive Debugging

All Level 3 features
All debug blocks execute
Breakpoint simulation
Interactive inspection
Core dump control
Use for deep debugging sessions

Debug Assertions
Runtime validation that halts execution on failure:
ailangDebugAssert(condition, message)
Parameters:

condition: Boolean expression to validate
message: String displayed if assertion fails

Behavior:

Evaluates condition at runtime (when debug level ≥ 1)
Continues execution if condition is true
Prints message and exits if condition is false
Compiles to NOP at debug level 0

Examples:
ailang// Basic assertions
DebugAssert(GreaterThan(x, 0), "x must be positive")
DebugAssert(NotEqual(ptr, 0), "Null pointer detected")

// Complex conditions
result = CalculateValue()
DebugAssert(And(GreaterEqual(result, 0), LessEqual(result, 100)), "Result out of range")

// Loop invariants
i = 0
WhileLoop LessThan(i, count) {
    DebugAssert(LessThan(i, array_size), "Array index out of bounds")
    // Process array[i]
    i = Add(i, 1)
}
Debug Blocks
Conditional code execution based on debug level:
ailangDebug(label, level=N) {
    // Debug code here
}
Parameters:

label: String identifier for the debug block
level: Minimum debug level for execution (1-4)

Behavior:

Block executes only if current debug level ≥ specified level
Label helps identify debug output
Can contain any valid AILANG code
Compiles to NOP if level requirement not met

Examples:
ailang// Basic debug block
Debug("initialization", level=1) {
    PrintMessage("System initializing...")
}

// Variable inspection
Debug("variables", level=2) {
    PrintMessage("Current values:")
    PrintMessage("  x =")
    PrintNumber(x)
    PrintMessage("  status =")
    PrintNumber(status)
}

// Detailed analysis
Debug("memory_check", level=3) {
    PrintMessage("Memory analysis:")
    // Simulate memory dump
    PrintMessage("  Stack usage: 1024 bytes")
    PrintMessage("  Heap usage: 4096 bytes")
}

// Nested debug blocks
Debug("outer", level=2) {
    PrintMessage("Outer block")
    
    Debug("inner", level=3) {
        PrintMessage("Inner block (only at level 3+)")
    }
}
Performance Profiling
Measure execution time of code sections:
ailangDebugPerf.Start(label)
// Code to profile
DebugPerf.End(label)
DebugPerf.Mark(label)
Operations:

Start: Begin timing a section
End: Stop timing and record duration
Mark: Record a timestamp marker

Behavior:

Only active when -P flag is set
Uses RDTSC instruction for cycle-accurate timing
Minimal overhead when enabled
Compiles to NOP when disabled

Examples:
ailang// Time a computation
DebugPerf.Start("calculation")

result = 0
i = 0
WhileLoop LessThan(i, 1000) {
    result = Add(result, Multiply(i, i))
    i = Add(i, 1)
}

DebugPerf.End("calculation")

// Time multiple sections
DebugPerf.Start("phase1")
ProcessPhaseOne()
DebugPerf.End("phase1")

DebugPerf.Start("phase2")
ProcessPhaseTwo()
DebugPerf.End("phase2")

// Mark important points
DebugPerf.Mark("checkpoint_reached")
Command-Line Options
Debug Level Control
bash# No debug (production)
python3 main.py program.ailang

# Level 1: Assertions only
python3 main.py program.ailang -D1

# Level 2: + Debug blocks and traces
python3 main.py program.ailang -D2

# Level 3: + Detailed analysis
python3 main.py program.ailang -D3

# Level 4: Full debugging
python3 main.py program.ailang -D4
Performance Profiling
bash# Enable profiling
python3 main.py program.ailang -P

# Combine with debug level
python3 main.py program.ailang -D2 -P

# Profile production build
python3 main.py program.ailang -D0 -P
Examples and Patterns
Pattern 1: Progressive Debug Detail
ailangSubRoutine.ProcessData {
    // Always validate inputs (level 1+)
    DebugAssert(GreaterThan(data_size, 0), "Invalid data size")
    
    // Basic trace (level 2+)
    Debug("trace", level=2) {
        PrintMessage("ProcessData: Starting")
    }
    
    // Detailed state (level 3+)
    Debug("state", level=3) {
        PrintMessage("Input parameters:")
        PrintMessage("  data_size =")
        PrintNumber(data_size)
    }
    
    // Process data
    result = PerformCalculation(data_size)
    
    // Validate result
    DebugAssert(GreaterEqual(result, 0), "Calculation failed")
    
    Debug("trace", level=2) {
        PrintMessage("ProcessData: Complete")
    }
}
Pattern 2: Performance Analysis
ailangSubRoutine.OptimizedAlgorithm {
    DebugPerf.Start("total")
    
    // Phase 1: Initialization
    DebugPerf.Start("init")
    InitializeStructures()
    DebugPerf.End("init")
    
    // Phase 2: Main computation
    DebugPerf.Start("compute")
    
    i = 0
    WhileLoop LessThan(i, iterations) {
        // Mark every 100 iterations
        IfCondition EqualTo(Modulo(i, 100), 0) ThenBlock {
            DebugPerf.Mark("iteration_100")
        }
        
        ProcessIteration(i)
        i = Add(i, 1)
    }
    
    DebugPerf.End("compute")
    
    // Phase 3: Cleanup
    DebugPerf.Start("cleanup")
    CleanupStructures()
    DebugPerf.End("cleanup")
    
    DebugPerf.End("total")
}
Pattern 3: Error Investigation
ailangSubRoutine.ComplexOperation {
    Debug("entry", level=2) {
        PrintMessage("ComplexOperation: Entry")
    }
    
    // Checkpoint 1
    step1_result = StepOne()
    Debug("checkpoint1", level=3) {
        PrintMessage("After StepOne:")
        PrintNumber(step1_result)
    }
    DebugAssert(GreaterThan(step1_result, 0), "StepOne failed")
    
    // Checkpoint 2
    step2_result = StepTwo(step1_result)
    Debug("checkpoint2", level=3) {
        PrintMessage("After StepTwo:")
        PrintNumber(step2_result)
    }
    
    // Detailed debugging for problem area
    Debug("problem_area", level=4) {
        PrintMessage("Entering problem area")
        PrintMessage("All variables:")
        PrintNumber(step1_result)
        PrintNumber(step2_result)
        // Add breakpoint simulation
        PrintMessage("BREAKPOINT: Check state")
    }
    
    final_result = StepThree(step2_result)
    
    Debug("exit", level=2) {
        PrintMessage("ComplexOperation: Exit")
    }
}
Pattern 4: Memory Debugging
ailangSubRoutine.MemoryIntensive {
    // Track allocations
    Debug("memory_start", level=3) {
        PrintMessage("Memory tracking started")
    }
    
    // Allocation
    buffer_size = 1024
    DebugAssert(LessEqual(buffer_size, 65536), "Buffer too large")
    
    Debug("allocation", level=3) {
        PrintMessage("Allocating buffer:")
        PrintNumber(buffer_size)
    }
    
    // Use buffer
    ProcessBuffer(buffer_size)
    
    // Cleanup verification
    Debug("memory_end", level=3) {
        PrintMessage("Memory cleanup complete")
    }
}
Performance Considerations
Debug Level Impact
LevelOverheadUse Case0NoneProduction releases1MinimalTesting and QA2LowDevelopment3ModerateDebugging4HighDeep investigation
Optimization Tips

Use Appropriate Levels: Choose the minimum level needed
Avoid Level 4 in Loops: High-level debug blocks in tight loops impact performance
Profile Sparingly: DebugPerf has measurable overhead
Conditional Debug: Use runtime conditions to limit debug output
Production Builds: Always compile with -D0 for release

Memory Usage
Debug blocks may increase stack usage when enabled:

Level 1: Negligible impact
Level 2-3: Small stack overhead for trace data
Level 4: Larger overhead for state preservation

Troubleshooting
Common Issues
Assertion Always Fails
ailang// Wrong: Assignment instead of comparison
DebugAssert(x = 10, "x should be 10")

// Correct: Use comparison
DebugAssert(EqualTo(x, 10), "x should be 10")
Debug Block Not Executing
ailang// Check compilation flags
// This only runs at level 3+
Debug("test", level=3) {
    PrintMessage("This needs -D3 or higher")
}
Performance Data Not Collected
ailang// Requires -P flag
DebugPerf.Start("test")
// Only works with: python3 main.py file.ailang -P
Debug Strategy

Start with Level 1: Verify assertions pass
Add Level 2 Traces: Track execution flow
Use Level 3 for State: Inspect variables at key points
Level 4 for Deep Dive: When other levels insufficient
Profile After Fixing: Optimize only after correctness

Integration with Development
bash# Development workflow
make debug   # Compile with -D2
make test    # Run with -D1
make profile # Run with -P
make release # Compile with -D0
Compiler Implementation Notes
The AILANG debug system uses conditional compilation:

Level Check: Debug level compared at compile time
NOP Generation: Disabled debug code becomes no-ops
Runtime Library: Debug support functions linked when needed
Symbol Preservation: Debug symbols retained based on level

Debug Code Generation
pythondef compile_debug_block(self, node):
    if node.level > self.debug_level:
        # Emit NOP
        self.asm.emit_nop()
    else:
        # Compile block contents
        for stmt in node.body:
            self.compile_statement(stmt)
Performance Profiling Implementation
The profiler uses x86-64 RDTSC instruction:

Reads processor timestamp counter
64-bit cycle count since reset
Overhead: ~20-30 cycles per measurement
Resolution: Single CPU cycle

This manual provides comprehensive coverage of AILANG's debug capabilities, enabling developers to effectively diagnose and optimize their programs while maintaining zero-overhead production builds.