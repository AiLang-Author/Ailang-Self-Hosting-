AILANG Quick Syntax Reference
Basic Syntax
Comments
ailang// Single line comment
Variables
ailangname = value              // No type declaration needed
x = 42                    // Integer
text = "Hello"           // String  
flag = True              // Boolean (True/False)
Output
ailangPrintMessage("text")      // Print string
PrintNumber(value)        // Print number
Operators (All Named)
Arithmetic
ailangAdd(a, b)                // a + b
Subtract(a, b)           // a - b
Multiply(a, b)           // a * b
Divide(a, b)             // a / b
Modulo(a, b)             // a % b
Power(a, b)              // a ^ b
Comparison
ailangEqualTo(a, b)            // a == b (returns 1 or 0)
NotEqual(a, b)           // a != b
GreaterThan(a, b)        // a > b
LessThan(a, b)           // a < b
GreaterEqual(a, b)       // a >= b
LessEqual(a, b)          // a <= b
Logical
ailangAnd(a, b)                // a && b
Or(a, b)                 // a || b
Not(a)                   // !a
Control Flow
If-Then-Else
ailangIfCondition expression ThenBlock {
    // statements
} ElseBlock {
    // statements
}
While Loop
ailangWhileLoop condition {
    // statements
    BreakLoop         // Optional: exit loop
    ContinueLoop      // Optional: skip to next iteration
}
For Each
ailangForEvery item in collection {
    // statements
}
Switch/Case
ailangChoosePath(variable) {
    CaseOption "value1": statement
    CaseOption "value2": statement
    DefaultOption: statement
}
Functions
Define Function
ailangFunction.Module.Name {
    Input: param1: Type
    Input: param2: Type
    Output: ReturnType
    Body: {
        // statements
        ReturnValue(expression)
    }
}
Call Function
ailangresult = Module.Name(arg1, arg2)
Define SubRoutine (No Return)
ailangSubRoutine.Module.Name {
    // statements
}
Call SubRoutine
ailangRunTask("Module.Name")
Strings
Basic Operations
ailangStringLength(str)                    // Get length
StringConcat(str1, str2)             // Join strings
StringEquals(str1, str2)             // Compare (returns 1/0)
StringCompare(str1, str2)            // Compare (returns 0 if equal)
Conversions
ailangNumberToString(num)                  // 42 → "42"
StringToNumber(str)                  // "42" → 42
File I/O
Basic File Operations
ailangWriteTextFile("file.txt", "content") // Write file
exists = FileExists("file.txt")      // Check existence (1/0)
ReadTextFile("file.txt")             // Read file (when implemented)
Memory Pools
Pool Declaration
ailangFixedPool.PoolName {
    "variable": Initialize-value, CanChange-True
    "constant": Initialize-value, CanChange-False
}
Access Pool Variables
ailangvalue = PoolName.variable
PoolName.variable = newValue
Error Handling
Try-Catch
ailangTryBlock: {
    // statements that might fail
}
CatchError.ErrorType {
    // handle error
}
FinallyBlock: {
    // always executes
}
Debug Features (Compile with -D flag)
ailangDebugAssert(condition, "message")    // Runtime assertion
DebugTrace.Entry("label", value)     // Trace entry
DebugTrace.Exit("label", value)      // Trace exit
DebugPerf.Start("label")            // Start timing
DebugPerf.End("label")              // End timing
Program Control
ailangHaltProgram()                        // Exit program
HaltProgram("message")               // Exit with message
Common Patterns
Counter Loop
ailangi = 0
WhileLoop LessThan(i, 10) {
    // Do something with i
    i = Add(i, 1)
}
String Building
ailangmsg = StringConcat("Hello", ", ")
msg = StringConcat(msg, "World")
msg = StringConcat(msg, "!")
Null Check
ailangIfCondition EqualTo(value, Null) ThenBlock {
    // Handle null
}
Boolean Operations
ailangis_valid = And(GreaterThan(x, 0), LessThan(x, 100))
IfCondition is_valid ThenBlock {
    // x is between 0 and 100
}
Type Reference
TypeDescriptionExampleInteger64-bit signed integer42, -100TextUTF-8 string"Hello"BooleanTrue/FalseTrue, FalseNullNull valueNull
Compile & Run
bash# Compile
python3 main.py program.ailang

# Run
./program_exec

# Debug mode
python3 main.py -D program.ailang

Remember: AILANG uses named operators (Add not +), explicit control flow (IfCondition/ThenBlock), and structured syntax (blocks with {}).
