## Mathematical Operators & PEMDAS Support

AILANG implements **standard mathematical notation** with proper PEMDAS/BODMAS precedence - exactly as taught in mathematics, not the confusing conventions found in many programming languages.

### Supported Operators

#### Arithmetic Operators
- `+` Addition
- `-` Subtraction  
- `*` Multiplication
- `/` Division
- `%` Modulo (remainder)
- `^` **Exponentiation** (power) - Yes, the actual math symbol!

#### Comparison Operators
- `>` Greater than
- `<` Less than
- `>=` Greater than or equal
- `<=` Less than or equal
- `==` Equal to
- `!=` Not equal to

#### Bitwise Operators
- `&` Bitwise AND
- `|` Bitwise OR
- `<<` Left shift
- `>>` Right shift
- `~` Bitwise NOT
- `BitwiseXor()` XOR (function form - no symbol conflict)

#### Logical Operators
- `&&` Logical AND
- `||` Logical OR
- `!` Logical NOT

### Precedence (HARD PEMDAS)

Operations are evaluated in standard mathematical order:

1. **P**arentheses `()`MANDATORY
2. **E**xponents `^` 
3. **M**ultiplication `*` and **D**ivision `/` (left-to-right)
4. **A**ddition `+` and **S**ubtraction `-` (left-to-right)

### Examples
```ailang
// Standard math notation works as expected
energy = (mass * (c^2))                    // E=mc²
force = ((G * (m1 * m2)) / r^2)            // Newton's law of gravitation
quadratic = (-b + sqrt((b^2) - (4*a*c))) / (2*a)  // Quadratic formula

// No surprises for scientists and engineers
result = ((2^3) + (4 * 5))                   // = 8 + 20 = 28 (not 160!)
voltage = (current * resistance)         // Ohm's law

HARD PEMDAS RULES PREVENT BUGS AND ERRORS !!!!
