AILANG Debug Module
Overview
AILANG provides built-in debugging as a language primitive. Debug code compiles conditionally based on flags, with zero overhead when disabled.
Basic Usage
Compilation Flags
bashpython3 main.py test.ailang          # No debug output
python3 main.py -D test.ailang       # Debug level 1
python3 main.py -D2 test.ailang      # Debug level 2
python3 main.py -D3 test.ailang      # Debug level 3 (all)
Debug Blocks
ailangDebug("label", level=1) {
    PrintMessage("This only compiles with -D or higher")
    PrintNumber(variable_to_inspect)
}

Debug("detailed trace", level=2) {
    PrintMessage("This needs -D2 or -D3")
}
Debug Assertions
ailangDebugAssert(GreaterThan(x, 0), "x must be positive")
DebugAssert(NotEqual(ptr, Null), "Pointer is null")
Examples
Example 1: Basic Debugging
ailangFunction.Calculate {
    Input: x:, y:
    Body: {
        Debug("input validation", level=1) {
            PrintMessage("Checking inputs:")
            PrintNumber(x)
            PrintNumber(y)
        }
        
        result = Add(x, y)
        
        Debug("result check", level=2) {
            PrintMessage("Computed result:")
            PrintNumber(result)
        }
        
        ReturnValue(result)
    }
}
Example 2: Assertions for Safety
ailangFunction.ProcessArray {
    Input: arr:, size:
    Body: {
        DebugAssert(GreaterThan(size, 0), "Array size must be positive")
        DebugAssert(NotEqual(arr, Null), "Array pointer is null")
        
        // Process array...
        ReturnValue(0)
    }
}
Example 3: Multi-Level Debugging
ailangDebug("basic info", level=1) {
    PrintMessage("Starting process")
}

Debug("verbose", level=2) {
    PrintMessage("Detailed state information")
    PrintNumber(internal_state)
}

Debug("trace", level=3) {
    PrintMessage("Full execution trace")
    // Expensive debug operations here
}
Debug Levels

Level 0 (default): No debug output
Level 1 (-D): Basic debugging, assertions
Level 2 (-D2): Detailed debugging
Level 3 (-D3): Full trace, all debug output

Performance
Debug code is completely removed during compilation when not enabled. There is zero runtime overhead for debug statements in production builds.
bash# Production build (no debug overhead)
python3 main.py production.ailang

# Development build (with debug)
python3 main.py -D3 production.ailang
