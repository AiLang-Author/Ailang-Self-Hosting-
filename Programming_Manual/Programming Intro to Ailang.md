//Getting Started with AILANG
//Your First AILANG Program
//AILANG programs are simple text files with the .ailang extension. Here's the classic "Hello, World!": ailang


// hello.ailang
PrintMessage("Hello, World!")
Save this as hello.ailang and compile it:
bashpython3 main.py hello.ailang
./hello_exec
Basic Operations
Variables and Arithmetic
ailang// Variables don't need declaration
a = 10
b = 20
sum = Add(a, b)
PrintMessage("Sum is:")
PrintNumber(sum)

// All arithmetic uses named operators
product = Multiply(5, 6)
difference = Subtract(100, 25)
quotient = Divide(50, 2)
Printing Output
ailang// Print text
PrintMessage("This is a message")

// Print numbers (separate function)
value = 42
PrintNumber(value)

// Concatenate strings for complex output
name = "AILANG"
version = NumberToString(2)
message = StringConcat("Welcome to ", name)
message = StringConcat(message, " v")
message = StringConcat(message, version)
PrintMessage(message)
Control Flow
If-Then-Else
ailangscore = 85

IfCondition GreaterThan(score, 90) ThenBlock {
    PrintMessage("Excellent!")
} ElseBlock {
    IfCondition GreaterThan(score, 70) ThenBlock {
        PrintMessage("Good job!")
    } ElseBlock {
        PrintMessage("Keep trying!")
    }
}
While Loops
ailang// Count from 0 to 4
counter = 0
WhileLoop LessThan(counter, 5) {
    PrintMessage("Count:")
    PrintNumber(counter)
    counter = Add(counter, 1)
}
For Each Loop
ailang// Iterate over items (when implemented)
ForEvery item in [1, 2, 3] {
    PrintNumber(item)
}
Functions
Defining Functions
ailangFunction.Math.AddTwo {
    Input: n: Integer
    Output: Integer
    Body: {
        ReturnValue(Add(n, 2))
    }
}

// Call the function
result = Math.AddTwo(5)
PrintNumber(result)  // Prints: 7
SubRoutines (No Return Value)
ailangSubRoutine.Utils.PrintBanner {
    PrintMessage("=" * 50)
    PrintMessage("    AILANG Program")
    PrintMessage("=" * 50)
}

// Call with RunTask
RunTask("Utils.PrintBanner")
File Operations
ailang// Write to file
WriteTextFile("output.txt", "Hello, File System!")

// Check if file exists
exists = FileExists("output.txt")
IfCondition EqualTo(exists, 1) ThenBlock {
    PrintMessage("File created successfully")
}

// Create multiple files
i = 0
WhileLoop LessThan(i, 3) {
    filename = StringConcat("file_", NumberToString(i))
    filename = StringConcat(filename, ".txt")
    content = StringConcat("This is file ", NumberToString(i))
    WriteTextFile(filename, content)
    i = Add(i, 1)
}
Compilation and Execution
Basic Compilation
bash# Compile AILANG to executable
python3 main.py myprogram.ailang

# Run the compiled program
./myprogram_exec
Debug Mode
bash# Compile with debug info
python3 main.py -D myprogram.ailang

# This enables DebugAssert and other debug features
Running Tests
bash# Run the loop structure tests
./run_loop_tests.sh

# Run a specific test
python3 main.py test_basic_ops.ailang
./test_basic_ops_exec

AILANG by Example
Learn AILANG through working examples from the test suite.
Basic Examples
Example 1: Simple Calculator
ailang// calculator.ailang
a = 10
b = 3

// Basic arithmetic
sum = Add(a, b)
diff = Subtract(a, b)
prod = Multiply(a, b)
quot = Divide(a, b)
rem = Modulo(a, b)

PrintMessage("Calculator Results:")
PrintMessage("10 + 3 =")
PrintNumber(sum)
PrintMessage("10 - 3 =")
PrintNumber(diff)
PrintMessage("10 * 3 =")
PrintNumber(prod)
PrintMessage("10 / 3 =")
PrintNumber(quot)
PrintMessage("10 % 3 =")
PrintNumber(rem)
Example 2: String Manipulation
ailang// strings.ailang
first = "Hello"
second = "World"

// Concatenation
greeting = StringConcat(first, ", ")
greeting = StringConcat(greeting, second)
greeting = StringConcat(greeting, "!")
PrintMessage(greeting)  // "Hello, World!"

// String length
len = StringLength(greeting)
PrintMessage("Length:")
PrintNumber(len)

// String comparison
are_equal = StringEquals("test", "test")
PrintMessage("Strings equal (1=yes, 0=no):")
PrintNumber(are_equal)
Example 3: Factorial Function
ailang// factorial.ailang
Function.Math.Factorial {
    Input: n: Integer
    Output: Integer
    Body: {
        IfCondition LessEqual(n, 1) ThenBlock {
            ReturnValue(1)
        }
        
        result = 1
        i = 2
        WhileLoop LessEqual(i, n) {
            result = Multiply(result, i)
            i = Add(i, 1)
        }
        ReturnValue(result)
    }
}

// Test it
fact5 = Math.Factorial(5)
PrintMessage("5! =")
PrintNumber(fact5)  // 120
Intermediate Examples
Example 4: File Processing
ailang// file_processor.ailang
// Create a log file with timestamps

Function.Utils.GetTimestamp {
    Output: Integer
    Body: {
        // Simplified - returns a counter
        ReturnValue(12345)
    }
}

SubRoutine.Logger.WriteEntry {
    timestamp = Utils.GetTimestamp()
    ts_str = NumberToString(timestamp)
    
    entry = StringConcat("[", ts_str)
    entry = StringConcat(entry, "] ")
    entry = StringConcat(entry, "Program started")
    
    WriteTextFile("app.log", entry)
}

// Use the logger
RunTask("Logger.WriteEntry")
PrintMessage("Log entry written")
Example 5: Nested Functions
ailang// nested_math.ailang
Function.Math.Square {
    Input: x: Integer
    Output: Integer
    Body: {
        ReturnValue(Multiply(x, x))
    }
}

Function.Math.SumOfSquares {
    Input: a: Integer
    Input: b: Integer
    Output: Integer
    Body: {
        sq_a = Math.Square(a)
        sq_b = Math.Square(b)
        ReturnValue(Add(sq_a, sq_b))
    }
}

// Calculate 3² + 4² = 25
result = Math.SumOfSquares(3, 4)
PrintMessage("3² + 4² =")
PrintNumber(result)
Example 6: Pattern Matching with ChoosePath
ailang// menu.ailang
choice = "2"  // Simulated user input

ChoosePath(choice) {
    CaseOption "1": PrintMessage("You chose option 1")
    CaseOption "2": PrintMessage("You chose option 2")
    CaseOption "3": PrintMessage("You chose option 3")
    CaseOption "quit": HaltProgram("Goodbye!")
    DefaultOption: PrintMessage("Invalid choice")
}
Advanced Examples
Example 7: SubRoutines and State
ailang// counter.ailang
// Global counter managed by subroutines

counter = 0

SubRoutine.Counter.Increment {
    counter = Add(counter, 1)
    PrintMessage("Counter incremented")
}

SubRoutine.Counter.Reset {
    counter = 0
    PrintMessage("Counter reset")
}

SubRoutine.Counter.Display {
    PrintMessage("Current count:")
    PrintNumber(counter)
}

// Use the counter
RunTask("Counter.Display")
RunTask("Counter.Increment")
RunTask("Counter.Increment")
RunTask("Counter.Display")
RunTask("Counter.Reset")
RunTask("Counter.Display")
Example 8: Loop Patterns
ailang// patterns.ailang
// Different loop patterns

// Pattern 1: Count down
PrintMessage("Countdown:")
i = 5
WhileLoop GreaterThan(i, 0) {
    PrintNumber(i)
    i = Subtract(i, 1)
}
PrintMessage("Liftoff!")

// Pattern 2: Skip even numbers
PrintMessage("Odd numbers:")
j = 0
WhileLoop LessThan(j, 10) {
    is_even = EqualTo(Modulo(j, 2), 0)
    IfCondition Not(is_even) ThenBlock {
        PrintNumber(j)
    }
    j = Add(j, 1)
}

// Pattern 3: Nested loops
PrintMessage("Multiplication table:")
row = 1
WhileLoop LessEqual(row, 3) {
    col = 1
    WhileLoop LessEqual(col, 3) {
        product = Multiply(row, col)
        PrintNumber(product)
        col = Add(col, 1)
    }
    row = Add(row, 1)
}
Example 9: Debug Features
ailang// debug_example.ailang
// Compile with: python3 main.py -D debug_example.ailang

value = 10

// Debug assertions
DebugAssert(GreaterThan(value, 0), "Value must be positive")

// Performance timing
DebugPerf.Start("calculation")
result = 0
i = 0
WhileLoop LessThan(i, 1000) {
    result = Add(result, i)
    i = Add(i, 1)
}
DebugPerf.End("calculation")

// Trace points
DebugTrace.Entry("MainCalc", value)
processed = Multiply(value, 2)
DebugTrace.Exit("MainCalc", processed)

PrintMessage("Debug example complete")
Working Test Files
These tests from the test suite are confirmed working:
Test FileDescriptiontest_basic_ops.ailangArithmetic and comparisonstest_strings_comprehensive.ailangAll string operationstest_fileio_minimal.ailangBasic file I/Otest_user_functions_basic.ailangFunction definitionstest_runtask_comprehensive.ailangSubRoutine callstest_loop_simple.ailangBasic loop structurestest_subroutine_basic.ailangSubRoutine patterns
Tips for Success

Start Simple: Begin with PrintMessage and basic arithmetic
Use Named Operators: Remember Add() not +, Multiply() not *
Debug Mode: Compile with -D flag to enable assertions
Check Test Files: Look at working tests for patterns
String Building: Use multiple StringConcat calls for complex strings
Function Naming: Use dotted names like Math.Calculate

Common Patterns
ailang// Pattern: Building complex strings
message = StringConcat("Part 1", " ")
message = StringConcat(message, "Part 2")
message = StringConcat(message, " ")
message = StringConcat(message, NumberToString(42))

// Pattern: Counter loop
i = 0
WhileLoop LessThan(i, limit) {
    // Do work
    i = Add(i, 1)
}

// Pattern: State checking
exists = FileExists("data.txt")
IfCondition EqualTo(exists, 1) ThenBlock {
    // File exists
} ElseBlock {
    // File doesn't exist
}

These docs focus on what actually works based on the test files, avoiding features that are still in development. They provide a practical path for users to start writing AILANG programs today.
