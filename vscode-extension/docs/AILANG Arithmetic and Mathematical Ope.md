# AILANG Arithmetic and Mathematical Operations Manual 

## Table of Contents
1. [Overview](#overview)
2. [Basic Arithmetic Operations](#basic-arithmetic-operations)
3. [Infix Notation System](#infix-notation-system)
4. [Unary Operations](#unary-operations)
5. [Comparison Operations](#comparison-operations)
6. [Bitwise Operations](#bitwise-operations)
7. [Logical Operations](#logical-operations)
8. [Advanced Mathematical Functions](#advanced-mathematical-functions)
9. [Mixed Notation Programming](#mixed-notation-programming)
10. [Common Patterns and Examples](#common-patterns-and-examples)

## Overview

AILANG provides a comprehensive mathematical computation system that supports both traditional function-call syntax and modern infix notation. The language seamlessly integrates symbolic operators with named functions, enabling flexible and readable mathematical expressions.

### Supported Number Types
- **Signed Integers**: 64-bit signed integers (-2^63 to 2^63-1)
- **Automatic Promotion**: Operations automatically handle large numbers
- **Zero Handling**: Proper zero semantics for all operations

### Dual Syntax Support
AILANG uniquely supports both syntaxes simultaneously:
```ailang
// Function call syntax
result = Add(a, b)

// Infix symbol syntax  
result = (a + b)

// Mixed usage
result = Add((a * b), Divide(c, d))
```

## Basic Arithmetic Operations

### Addition

**Function Syntax:**
```ailang
result = Add(operand1, operand2)
```

**Infix Syntax:**
```ailang
result = (operand1 + operand2)
```

**Examples:**
```ailang
// Basic addition
sum = Add(10, 5)          // Returns 15
sum = (10 + 5)            // Returns 15

// Variable addition
a = 100
b = 25
total = Add(a, b)         // Returns 125
total = (a + b)           // Returns 125

// Negative numbers
result = Add(-10, 5)      // Returns -5
result = (-10 + 5)        // Returns -5

// Chain operations
result = Add(Add(1, 2), 3)  // Returns 6
result = ((1 + 2) + 3)      // Returns 6
```

### Subtraction

**Function Syntax:**
```ailang
result = Subtract(minuend, subtrahend)
```

**Infix Syntax:**
```ailang
result = (minuend - subtrahend)
```

**Examples:**
```ailang
// Basic subtraction
diff = Subtract(20, 8)    // Returns 12
diff = (20 - 8)           // Returns 12

// Negative results
result = Subtract(5, 10)  // Returns -5
result = (5 - 10)         // Returns -5

// Double negatives
result = Subtract(-5, -10) // Returns 5
result = (-5 - (-10))     // Returns 5
```

### Multiplication

**Function Syntax:**
```ailang
result = Multiply(factor1, factor2)
```

**Infix Syntax:**
```ailang
result = (factor1 * factor2)
```

**Examples:**
```ailang
// Basic multiplication
product = Multiply(7, 6)   // Returns 42
product = (7 * 6)          // Returns 42

// Sign handling
result = Multiply(-3, 4)   // Returns -12
result = (-3 * 4)          // Returns -12

result = Multiply(-3, -4)  // Returns 12
result = (-3 * -4)         // Returns 12

// Large numbers
big = Multiply(1000000, 1000)  // Returns 1000000000
big = (1000000 * 1000)         // Returns 1000000000
```

### Division

**Function Syntax:**
```ailang
result = Divide(dividend, divisor)
```

**Infix Syntax:**
```ailang
result = (dividend / divisor)
```

**Examples:**
```ailang
// Integer division (truncated toward zero)
quotient = Divide(20, 3)   // Returns 6
quotient = (20 / 3)        // Returns 6

// Exact division
result = Divide(100, 4)    // Returns 25
result = (100 / 4)         // Returns 25

// Negative division
result = Divide(-20, 4)    // Returns -5
result = (-20 / 4)         // Returns -5

result = Divide(20, -4)    // Returns -5
result = (20 / -4)         // Returns -5

result = Divide(-20, -4)   // Returns 5
result = (-20 / -4)        // Returns 5
```

**Important Notes:**
- Division by zero results in undefined behavior
- Integer division truncates toward zero
- Sign handling follows standard mathematical rules

### Modulo (Remainder)

**Function Syntax:**
```ailang
result = Modulo(dividend, divisor)
```

**Infix Syntax:**
```ailang
result = (dividend % divisor)
```

**Examples:**
```ailang
// Basic modulo
remainder = Modulo(17, 5)  // Returns 2
remainder = (17 % 5)       // Returns 2

// Zero remainder
result = Modulo(20, 4)     // Returns 0
result = (20 % 4)          // Returns 0

// Negative operands (truncated division)
result = Modulo(-17, 5)    // Returns -2
result = (-17 % 5)         // Returns -2

result = Modulo(17, -5)    // Returns 2
result = (17 % -5)         // Returns 2
```

### Power/Exponentiation

**Function Syntax:**
```ailang
result = Power(base, exponent)
```

**Infix Syntax:**
```ailang
result = (base ^ exponent)
```

**Examples:**
```ailang
// Basic powers
squared = Power(5, 2)      // Returns 25
squared = (5 ^ 2)          // Returns 25

cubed = Power(3, 3)        // Returns 27
cubed = (3 ^ 3)            // Returns 27

// Powers of 2
power2 = Power(2, 8)       // Returns 256
power2 = (2 ^ 8)           // Returns 256

// Power of 1 and 0
identity = Power(42, 1)    // Returns 42
one = Power(42, 0)         // Returns 1
```

## Infix Notation System

AILANG's infix notation requires parentheses for proper precedence and parsing:

### Basic Infix Rules

1. **Parentheses Required**: All infix operations must be enclosed in parentheses
2. **Left-to-Right Evaluation**: Operations evaluate left-to-right within parentheses
3. **Nested Operations**: Parentheses can be nested to any depth
4. **Mixed Syntax**: Infix and function calls can be combined

**Examples:**
```ailang
// Valid infix expressions
result = (a + b)
result = ((a + b) * c)
result = (((a + b) * c) - d)

// Invalid - missing parentheses
// result = a + b           // SYNTAX ERROR
// result = a + b * c       // SYNTAX ERROR
```

### Operator Precedence Through Parentheses

Since AILANG requires explicit parentheses, precedence is controlled by nesting:

```ailang
// Mathematical precedence through explicit grouping
result = ((a * b) + c)     // Multiply first, then add
result = (a * (b + c))     // Add first, then multiply

// Complex expressions
result = (((a + b) * (c - d)) / (e + f))

// Equivalent function call version
result = Divide(Multiply(Add(a, b), Subtract(c, d)), Add(e, f))
```

### Available Infix Operators

**Arithmetic:**
- `+` (addition)
- `-` (subtraction)
- `*` (multiplication)
- `/` (division)
- `%` (modulo)
- `^` (power - **NOT XOR**)

**Comparison:**
- `<` (less than)
- `>` (greater than)
- `<=` (less than or equal)
- `>=` (greater than or equal)
- `==` (equal to)
- `!=` (not equal)

**Logical:**
- `&&` (logical AND)
- `||` (logical OR)
- `!` (logical NOT - unary, prefix only)

**Bitwise:**
- `&` (bitwise AND)
- `|` (bitwise OR)
- `~` (bitwise NOT - unary, prefix only)
- `<<` (left shift)
- `>>` (right shift)

**⚠️ IMPORTANT: No Infix XOR Operator**

BitwiseXor does **NOT** have an infix operator symbol. The `^` symbol is reserved for Power operations.

```ailang
// CORRECT - Use function for XOR
result = BitwiseXor(a, b)

// WRONG - This is POWER, not XOR!
result = (a ^ b)  // This computes a to the power of b
```

## Unary Operations

### Unary Negation (Prefix Minus)

**Prefix Syntax:**
```ailang
result = -value
```

This is syntactic sugar that the compiler transforms to `Subtract(0, value)`.

**Examples:**
```ailang
x = 5
neg_x = -x           // Returns -5 (same as Subtract(0, x))

// In expressions
result = (-5 + 3)    // Returns -2
result = (10 * -2)   // Returns -20

// Double negation
y = -10
pos_y = -(-y)        // Returns 10
```

### Unary NOT (Prefix Bang)

**Prefix Syntax:**
```ailang
result = !value
```

**Parenthesized Syntax:**
```ailang
result = (!value)
```

**Examples:**
```ailang
flag = 1
inverted = !flag     // Returns 0

// In expressions
result = (!false_condition && true_condition)

// Function equivalent
result = Not(flag)
```

### Bitwise NOT (Prefix Tilde)

**Prefix Syntax:**
```ailang
result = ~value
```

**Examples:**
```ailang
bits = 0xFF
complement = ~bits   // Returns bitwise complement

// Function equivalent
result = BitwiseNot(value)
```

## Comparison Operations

### Relational Comparisons

**Function Syntax:**
```ailang
result = LessThan(a, b)        // Returns 1 if a < b, 0 otherwise
result = LessEqual(a, b)       // Returns 1 if a <= b, 0 otherwise
result = GreaterThan(a, b)     // Returns 1 if a > b, 0 otherwise
result = GreaterEqual(a, b)    // Returns 1 if a >= b, 0 otherwise
result = EqualTo(a, b)         // Returns 1 if a == b, 0 otherwise
result = NotEqual(a, b)        // Returns 1 if a != b, 0 otherwise
```

**Infix Syntax:**
```ailang
result = (a < b)
result = (a <= b)
result = (a > b)
result = (a >= b)
result = (a == b)
result = (a != b)
```

**Examples:**
```ailang
// Basic comparisons
age = 25
is_adult = GreaterEqual(age, 18)  // Returns 1
is_adult = (age >= 18)            // Returns 1

// Chained comparisons
x = 10
y = 20
z = 30
result = And(LessThan(x, y), LessThan(y, z))  // Returns 1
result = ((x < y) && (y < z))                 // Returns 1

// Equality testing
value = 42
is_answer = EqualTo(value, 42)    // Returns 1
is_answer = (value == 42)         // Returns 1
```

## Bitwise Operations

### Basic Bitwise Operations

**Function Syntax:**
```ailang
result = BitwiseAnd(a, b)      // Bitwise AND
result = BitwiseOr(a, b)       // Bitwise OR
result = BitwiseXor(a, b)      // Bitwise XOR (exclusive OR) - NO INFIX OPERATOR
result = BitwiseNot(a)         // Bitwise NOT (complement)
result = LeftShift(a, bits)    // Left shift
result = RightShift(a, bits)   // Right shift
```

**Infix Syntax:**
```ailang
result = (a & b)               // Bitwise AND
result = (a | b)               // Bitwise OR
result = (a << bits)           // Left shift
result = (a >> bits)           // Right shift
result = (~a)                  // Bitwise NOT
// NO INFIX FOR XOR - use BitwiseXor(a, b)
```

**⚠️ CRITICAL: The `^` symbol is Power, NOT XOR!**

```ailang
// CORRECT XOR usage
toggled = BitwiseXor(value, mask)

// WRONG - This does POWER not XOR!
toggled = (value ^ mask)  // This computes value to the power of mask!
```

**Examples:**
```ailang
// Basic bitwise operations
mask = 15                      // Binary: 1111
value = 255                    // Binary: 11111111

// AND operation - clear upper bits
result = BitwiseAnd(value, mask)  // Returns 15
result = (value & mask)           // Returns 15

// OR operation - set bits
flags = 0
flag1 = 1
flag2 = 4
combined = BitwiseOr(BitwiseOr(flags, flag1), flag2)  // Returns 5
combined = ((flags | flag1) | flag2)                  // Returns 5

// XOR operation - toggle bits (FUNCTION ONLY)
original = 170                 // Binary: 10101010
toggle_mask = 15              // Binary: 00001111
toggled = BitwiseXor(original, toggle_mask)  // Returns 165
// NOTE: MUST use function - no infix operator

// NOT operation - complement
value = 0
all_bits = BitwiseNot(value)  // Returns -1 (all bits set)
all_bits = (~value)           // Returns -1 (all bits set)
```

### Bit Shifting Operations

**Examples:**
```ailang
// Left shift - multiply by powers of 2
value = 5                     // Binary: 101
shifted = LeftShift(value, 2) // Returns 20 (Binary: 10100)
shifted = (value << 2)        // Returns 20

// Right shift - divide by powers of 2
value = 20                    // Binary: 10100
shifted = RightShift(value, 2) // Returns 5 (Binary: 101)
shifted = (value >> 2)         // Returns 5

// Generate powers of 2
power2_8 = LeftShift(1, 8)    // Returns 256
power2_8 = (1 << 8)           // Returns 256

power2_16 = LeftShift(1, 16)  // Returns 65536
power2_16 = (1 << 16)         // Returns 65536
```

### Common Bit Manipulation Patterns

**Set a Bit:**
```ailang
// Set bit n in value
bit_pos = 5
value = 0
set_bit = BitwiseOr(value, LeftShift(1, bit_pos))
set_bit = (value | (1 << bit_pos))
```

**Clear a Bit:**
```ailang
// Clear bit n in value
bit_pos = 3
value = 255
mask = BitwiseNot(LeftShift(1, bit_pos))
clear_bit = BitwiseAnd(value, mask)
clear_bit = (value & (~(1 << bit_pos)))
```

**Toggle a Bit:**
```ailang
// Toggle bit n in value (MUST use function)
bit_pos = 4
value = 170
toggle_bit = BitwiseXor(value, LeftShift(1, bit_pos))
// CANNOT use infix - BitwiseXor has no operator symbol
```

**Check if Bit is Set:**
```ailang
// Check if bit n is set
bit_pos = 3
value = 42
is_set = NotEqual(BitwiseAnd(value, LeftShift(1, bit_pos)), 0)
is_set = ((value & (1 << bit_pos)) != 0)
```

**Check if Power of 2:**
```ailang
// Check if number is power of 2: n & (n-1) == 0
test_val = 16
is_pow2 = EqualTo(BitwiseAnd(test_val, Subtract(test_val, 1)), 0)
is_pow2 = ((test_val & (test_val - 1)) == 0)
```

## Logical Operations

### Boolean Logic Functions

**Function Syntax:**
```ailang
result = And(a, b)             // Logical AND
result = Or(a, b)              // Logical OR  
result = Not(a)                // Logical NOT
```

**Infix Syntax:**
```ailang
result = (a && b)              // Logical AND
result = (a || b)              // Logical OR
result = (!a)                  // Logical NOT
result = !a                    // Logical NOT (prefix form)
```

**Examples:**
```ailang
// Basic logical operations
flag1 = 1
flag2 = 0

// AND - both must be true
both_true = And(flag1, flag2)   // Returns 0
both_true = (flag1 && flag2)    // Returns 0

// OR - either can be true
either_true = Or(flag1, flag2)  // Returns 1
either_true = (flag1 || flag2)  // Returns 1

// NOT - invert boolean
not_flag = Not(flag1)           // Returns 0
not_flag = (!flag1)             // Returns 0
not_flag = !flag1               // Returns 0 (prefix form)

// Complex boolean expressions
x = 5
y = 10
z = 5
result = And(EqualTo(x, z), GreaterThan(y, x))  // Returns 1
result = ((x == z) && (y > x))                   // Returns 1
```

### Short-Circuit Evaluation

AILANG logical operators support short-circuit evaluation in infix form:

```ailang
// Short-circuit AND - if first is false, second not evaluated
result = (false_condition && expensive_operation())

// Short-circuit OR - if first is true, second not evaluated  
result = (true_condition || expensive_operation())
```

## Advanced Mathematical Functions

AILANG provides several advanced mathematical functions as **compiler-level primitives** for optimal performance. These are implemented directly in the compiler's `math_ops.py` module.

### Integer Square Root

**Function Syntax (Compiler Primitive):**
```ailang
result = ISqrt(value)  // Newton's method, implemented in assembly
```

**Examples:**
```ailang
sqrt_25 = ISqrt(25)    // Returns 5
sqrt_100 = ISqrt(100)  // Returns 10  
sqrt_50 = ISqrt(50)    // Returns 7 (floor of 7.071...)
```

**Implementation:** Uses Newton's method directly compiled to x86-64 assembly for maximum performance.

**Note:** A slower library version `Math.ISqrt()` exists in `Library.FixedPointTrig` but the compiler primitive is recommended.

### Absolute Value

**Function Syntax (Compiler Primitive):**
```ailang
result = Abs(value)
```

**Examples:**
```ailang
pos = Abs(42)      // Returns 42
pos = Abs(-42)     // Returns 42
zero = Abs(0)      // Returns 0
```

**Implementation:** Uses branchless conditional move (CMOV) for optimal performance.

### Minimum and Maximum

**Function Syntax (Compiler Primitives):**
```ailang
result = Min(a, b)     // Returns smaller value
result = Max(a, b)     // Returns larger value
```

**Examples:**
```ailang
smaller = Min(10, 5)   // Returns 5
larger = Max(10, 5)    // Returns 10

// Can be nested (with caution)
smallest = Min(Min(a, b), c)
largest = Max(Max(a, b), c)
```

**Implementation:** Uses x86-64 CMOV instructions for branchless execution.

**Note:** Library versions `Math.Min()` and `Math.Max()` exist in `Library.FixedPointTrig` but are slower.

### Power (Alternative to Infix)

**Function Syntax (Compiler Primitive):**
```ailang
result = Pow(base, exponent)  // Alias for Power()
```

**Examples:**
```ailang
squared = Pow(5, 2)      // Returns 25
cubed = Pow(3, 3)        // Returns 27
```

**Note:** `Pow()` is an alias for the `Power()` function, which is also available via infix as `(base ^ exponent)`. All three forms compile to the same efficient assembly code.

## Mixed Notation Programming

### Combining Syntaxes

AILANG allows seamless mixing of function calls and infix notation:

```ailang
// Mix infix with function calls
result = Add((a * b), Divide(c, d))

// Use infix inside function calls
result = Add((x + y), (z - w))

// Complex mixed expressions
result = Multiply(((a + b) * c), Power(d, 2))
result = (((a + b) * c) * (d ^ 2))

// XOR must always use function
result = BitwiseXor((a & mask), (b | flags))
```

### Style Guidelines

**Recommendation 1: Use infix for simple operations**
```ailang
// Preferred for readability
total = (price + tax)
area = (length * width)
is_valid = (age >= 18)
```

**Recommendation 2: Use functions for operations without infix**
```ailang
// XOR has no infix operator - must use function
toggled = BitwiseXor(value, mask)

// Clearer for complex operations
distance = SquareRoot(Add(Power(x2 - x1, 2), Power(y2 - y1, 2)))
```

## Common Patterns and Examples

### Mathematical Algorithms

**Quadratic Formula Components:**
```ailang
// For ax² + bx + c = 0
// Calculate discriminant: b² - 4ac
a_coef = 1
b_coef = 5  
c_coef = 6
discriminant = ((b_coef ^ 2) - ((4 * a_coef) * c_coef))
```

**Distance Formula:**
```ailang
// Distance between two points
x1 = 0
y1 = 0
x2 = 3
y2 = 4
distance_squared = (((x2 - x1) ^ 2) + ((y2 - y1) ^ 2))  // Returns 25
```

### Bit Manipulation Algorithms

**XOR Swap (MUST use function):**
```ailang
// XOR swap - requires BitwiseXor function
a = 5
b = 10
a = BitwiseXor(a, b)
b = BitwiseXor(a, b)
a = BitwiseXor(a, b)
// a is now 10, b is now 5
```

### Number Theory Functions

**Greatest Common Divisor (Euclidean Algorithm):**
```ailang
gcd_a = 48
gcd_b = 18
WhileLoop NotEqual(gcd_b, 0) {
    temp = gcd_b
    gcd_b = Modulo(gcd_a, gcd_b)
    gcd_a = temp
}
// gcd_a now contains GCD(48, 18) = 6
```

## Error Conditions and Edge Cases

### Division Errors
- **Division by Zero**: Undefined behavior, program may crash
- **Integer Overflow**: Large results may wrap around

### Bitwise Operation Considerations
- **Right Shift of Negative Numbers**: Implementation uses logical shift (fills with zeros)
- **Shift Amounts**: Shifting by more than 63 bits has undefined behavior

### Common Pitfalls

**⚠️ CRITICAL: `^` is Power, NOT XOR!**

```ailang
// WRONG - This does exponentiation!
result = (value ^ 3)  // Computes value³, not value XOR 3

// CORRECT - Power operation
result = (value ^ 3)  // value cubed
result = Power(value, 3)  // Same thing

// CORRECT - XOR operation
result = BitwiseXor(value, 3)  // value XOR 3
```

### Best Practices
1. **Always validate divisors** before division operations
2. **Use parentheses** to make operator precedence explicit
3. **Remember: No infix XOR** - always use `BitwiseXor()` function
4. **Test edge cases** like zero, negative numbers, and large values
5. **Use appropriate data types** for expected value ranges
6. **Consider overflow** in multiplication and power operations

## Quick Reference: Operator Summary

### Infix Operators Available
- Arithmetic: `+` `-` `*` `/` `%` `^` (power)
- Comparison: `<` `>` `<=` `>=` `==` `!=`
- Logical: `&&` `||` `!` (prefix)
- Bitwise: `&` `|` `~` (prefix) `<<` `>>`

### Function-Only Operations (No Infix)
- `BitwiseXor(a, b)` - **No `^` operator, that's Power!**
- `Absolute(value)`
- `Min(a, b)` / `Max(a, b)`
- Advanced math functions (Floor, Ceil, Round, etc.)

This manual provides comprehensive coverage of AILANG's mathematical capabilities as actually implemented in the compiler, enabling developers to write efficient, readable, and mathematically sound programs using both traditional function syntax and modern infix notation.