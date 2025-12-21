# AILANG String Operations and Text Processing Manual

## Table of Contents
1. [Overview](#overview)
2. [Basic String Operations](#basic-string-operations)
3. [String Analysis Functions](#string-analysis-functions)
4. [String Manipulation Functions](#string-manipulation-functions)
5. [String Conversion Operations](#string-conversion-operations)
6. [Advanced Text Processing](#advanced-text-processing)
7. [Performance Optimization](#performance-optimization)
8. [Real-World Examples](#real-world-examples)
9. [Best Practices](#best-practices)

---

## Overview

AILANG provides a comprehensive string processing system designed for systems programming, text manipulation, and data processing tasks. All strings are null-terminated byte sequences with full UTF-8 compatibility and efficient memory management.

### String Representation
- **Null-Terminated**: All strings end with a null byte (`0x00`)
- **UTF-8 Compatible**: Support for Unicode characters via UTF-8 encoding
- **Memory Managed**: Automatic allocation and cleanup for string operations
- **Pointer-Based**: Strings are memory addresses pointing to character data

### Core Design Principles
- **Performance**: Optimized x86-64 assembly implementations
- **Safety**: Memory-safe string handling with bounds checking
- **Flexibility**: Both high-level functions and low-level buffer access
- **Interoperability**: Easy conversion between strings, numbers, and raw data

---

## Basic String Operations

### String Creation

**String Literals:**
```ailang
// Basic string literals
greeting = "Hello, World!"
empty_string = ""
multichar = "ABC123!@#"

// Strings with special characters
newline_string = "Line 1\nLine 2"
tab_string = "Column 1\tColumn 2"
quote_string = "She said \"Hello\""
```

**Character to String Conversion:**
```ailang
result = StringFromChar(ascii_code)
```

**Examples:**
```ailang
// Convert ASCII codes to strings
letter_a = StringFromChar(65)        // Returns "A"
letter_z = StringFromChar(90)        // Returns "Z"
space = StringFromChar(32)           // Returns " "
newline = StringFromChar(10)         // Returns "\n"
exclaim = StringFromChar(33)         // Returns "!"
```

### String Length

**Function Syntax:**
```ailang
length = StringLength(string)
```

**Examples:**
```ailang
// Basic length operations
hello_len = StringLength("Hello")         // Returns 5
empty_len = StringLength("")              // Returns 0
long_len = StringLength("Very long string with many characters")

// Variable string length
message = "Testing"
msg_len = StringLength(message)           // Returns 7

// Length in loops and conditions
text = "Process this text"
IfCondition GreaterThan(StringLength(text), 10) ThenBlock: {
    PrintMessage("Long text detected")
}
```

### String Concatenation

**Basic Concatenation:**
```ailang
result = StringConcat(string1, string2)
```

**Examples:**
```ailang
// Basic concatenation
greeting = StringConcat("Hello", "World")     // Returns "HelloWorld"
spaced = StringConcat("Hello ", "World")      // Returns "Hello World"

// Multiple concatenations
full_name = StringConcat(first_name, StringConcat(" ", last_name))

// Building strings incrementally
message = "Status: "
message = StringConcat(message, "Processing")
message = StringConcat(message, "...")         // "Status: Processing..."

// Empty string concatenation
result1 = StringConcat("", "Test")            // Returns "Test"
result2 = StringConcat("Test", "")            // Returns "Test"
```

**High-Performance Pool Concatenation:**
```ailang
// For high-frequency operations, uses a memory pool
result = StringConcatPooled(string1, string2)
```

**Note:** `StringConcatPooled` uses a pre-allocated memory pool for faster concatenation in loops or repeated operations. Falls back to returning the first string if the pool is full.

### String Comparison

**Equality Testing:**
```ailang
result = StringEquals(string1, string2)       // Returns 1 if equal, 0 if not
```

**Examples:**
```ailang
// Basic equality (case-sensitive)
is_same = StringEquals("Hello", "Hello")      // Returns 1
is_diff = StringEquals("Hello", "hello")      // Returns 0

// Variable comparison
username = "admin"
is_admin = StringEquals(username, "admin")    // Returns 1

// Comparison in conditions
password = GetPassword()
IfCondition StringEquals(password, "secret123") ThenBlock: {
    PrintMessage("Access granted")
} ElseBlock: {
    PrintMessage("Access denied")
}

// Empty string comparison
is_empty = StringEquals(input, "")            // Check if string is empty
```

**Lexicographical Comparison:**
```ailang
result = StringCompare(string1, string2)      // Returns 0 if equal, non-zero if different
```

---

## String Analysis Functions

### Character Access

**Character at Position:**
```ailang
char_code = StringCharAt(string, index)
```

**Examples:**
```ailang
// Access individual characters (returns ASCII code)
text = "Hello"
first_char = StringCharAt(text, 0)            // Returns 72 ('H')
last_char = StringCharAt(text, 4)             // Returns 111 ('o')

// Character analysis in loops
message = "Test123"
i = 0
digit_count = 0
WhileLoop LessThan(i, StringLength(message)) {
    char_code = StringCharAt(message, i)
    // Check if digit (ASCII 48-57 = '0'-'9')
    IfCondition And(GreaterEqual(char_code, 48), LessEqual(char_code, 57)) ThenBlock: {
        digit_count = Add(digit_count, 1)
    }
    i = Add(i, 1)
}
```

### String Search Functions

**Find Substring Position:**
```ailang
position = StringIndexOf(haystack, needle)
position = StringIndexOf(haystack, needle, start_position)
```

**Examples:**
```ailang
// Find substring position (returns -1 if not found)
text = "Hello World Programming"
world_pos = StringIndexOf(text, "World")      // Returns 6
missing_pos = StringIndexOf(text, "Missing")  // Returns -1

// Search from specific position
text = "apple, banana, apple, cherry"
first_apple = StringIndexOf(text, "apple")    // Returns 0
second_apple = StringIndexOf(text, "apple", 7) // Returns 15

// Search-based logic
email = "user@domain.com"
at_pos = StringIndexOf(email, "@")
IfCondition GreaterThan(at_pos, 0) ThenBlock: {
    domain_start = Add(at_pos, 1)
    domain = StringSubstring(email, domain_start, StringLength(email))
    PrintMessage("Domain: ")
    PrintString(domain)
}
```

**Contains Check:**
```ailang
has_substring = StringContains(haystack, needle)
```

**Examples:**
```ailang
// Check for keywords (returns 1 if found, 0 if not)
message = "Error: File not found"
is_error = StringContains(message, "Error")   // Returns 1
is_warning = StringContains(message, "Warning") // Returns 0

// Content filtering
text = "This contains profanity"
needs_filter = StringContains(text, "profanity")

// URL validation
url = "https://example.com"
is_https = StringContains(url, "https://")    // Returns 1
```

---

## String Manipulation Functions

### Substring Extraction

**Extract by Start and End Position:**
```ailang
result = StringSubstring(string, start_index, end_index)
result = StringExtract(string, start_index, end_index)  // Alias
```

**Important:** `StringSubstring` uses **end position**, not length. The substring is from `start_index` to `end_index` (exclusive of end).

**Examples:**
```ailang
// Basic substring extraction
text = "Programming Language"
first_word = StringSubstring(text, 0, 11)     // Returns "Programming"
second_word = StringSubstring(text, 12, 20)   // Returns "Language"

// Extract file extension
filename = "document.pdf"
dot_pos = StringIndexOf(filename, ".")
extension = StringSubstring(filename, Add(dot_pos, 1), StringLength(filename))
// Returns "pdf"

// Extract middle portion
full_text = "The quick brown fox"
middle = StringSubstring(full_text, 4, 9)     // Returns "quick"
```

**Extract Until Delimiter:**
```ailang
result = StringExtractUntil(buffer, start_offset, delimiter)
```

**Examples:**
```ailang
// Parse line-by-line
text_buffer = "First line\nSecond line\nThird line"
first_line = StringExtractUntil(text_buffer, 0, "\n")  // Returns "First line"

// Parse CSV fields  
csv_line = "name,age,city"
field1 = StringExtractUntil(csv_line, 0, ",")  // Returns "name"

// Protocol parsing
http_header = "GET /index.html HTTP/1.1\r\n"
method = StringExtractUntil(http_header, 0, " ")  // Returns "GET"

// Returns empty string (NULL) if delimiter not found
```

### Case Conversion

**Upper and Lower Case:**
```ailang
result = StringToUpper(string)
result = StringToLower(string)
```

**Examples:**
```ailang
// Case normalization
username = "JohnDoe"
normalized = StringToLower(username)          // Returns "johndoe"

// Case-insensitive comparison helper
Function.CaseInsensitiveEquals {
    Input: str1: Address
    Input: str2: Address
    Output: Integer
    Body: {
        upper1 = StringToUpper(str1)
        upper2 = StringToUpper(str2)
        result = StringEquals(upper1, upper2)
        ReturnValue(result)
    }
}

// Text formatting
title = "programming guide"
formatted_title = StringToUpper(title)        // Returns "PROGRAMMING GUIDE"

// Command processing
user_command = "quit"
command_upper = StringToUpper(user_command)   // Returns "QUIT"
```

### String Trimming

**Remove Leading and Trailing Whitespace:**
```ailang
result = StringTrim(string)
```

**Examples:**
```ailang
// Clean user input
user_input = "  Hello World  "
cleaned = StringTrim(user_input)              // Returns "Hello World"

// Process configuration values
config_value = "\tSomeValue\n"
clean_value = StringTrim(config_value)        // Returns "SomeValue"

// Data cleanup
data_field = "   123.45   "
clean_number = StringTrim(data_field)         // Returns "123.45"

// Tab and space removal
messy = "  \t  Text  \t  "
neat = StringTrim(messy)                      // Returns "Text"
```

### String Replacement

**Replace First Occurrence:**
```ailang
result = StringReplace(string, old_substring, new_substring)
```

**Note:** Currently replaces only the **first occurrence** of the substring.

**Examples:**
```ailang
// Simple replacement
text = "Hello World"
modified = StringReplace(text, "World", "AILANG")  // Returns "Hello AILANG"

// Path normalization
windows_path = "C:\\Users\\Name"
unix_path = StringReplace(windows_path, "\\", "/")  // Returns "C:/Users/Name"

// Template processing (single replacement)
template = "Welcome {USER} to the system"
personalized = StringReplace(template, "{USER}", "Alice")
// Returns "Welcome Alice to the system"

// Data sanitization
unsafe_data = "<script>alert('xss')</script>"
safe_data = StringReplace(unsafe_data, "<", "&lt;")
// Returns "&lt;script>alert('xss')</script>"
```

### String Splitting

**Split by Delimiter:**
```ailang
array = StringSplit(string, delimiter)
```

**Returns:** An array/list where each element is a substring between delimiters.

**Examples:**
```ailang
// Parse comma-separated values
csv_row = "apple,banana,cherry"
fruits = StringSplit(csv_row, ",")
// fruits contains: ["apple", "banana", "cherry"]

first_fruit = ArrayGet(fruits, 0)  // "apple"
second_fruit = ArrayGet(fruits, 1) // "banana"

// Parse command line arguments
command_line = "program --input file.txt --output result.txt"
args = StringSplit(command_line, " ")
// args contains: ["program", "--input", "file.txt", "--output", "result.txt"]

// Split file path
file_path = "/usr/local/bin/program"
path_parts = StringSplit(file_path, "/")
// path_parts contains: ["", "usr", "local", "bin", "program"]

// Parse key-value pairs
config_line = "setting=value"
pair = StringSplit(config_line, "=")
key = ArrayGet(pair, 0)     // "setting"
value = ArrayGet(pair, 1)   // "value"

// Empty string handling
empty_split = StringSplit("", ",")
// Returns array with one empty string: [""]
```

---

## String Conversion Operations

### Number to String Conversion

**Function Syntax:**
```ailang
string_result = NumberToString(number)
```

**Examples:**
```ailang
// Basic number conversion
age_str = NumberToString(25)                  // Returns "25"
negative_str = NumberToString(-42)            // Returns "-42"
zero_str = NumberToString(0)                  // Returns "0"

// Large number conversion
big_number = 1000000
big_str = NumberToString(big_number)          // Returns "1000000"

// Dynamic string building
counter = 1
message = StringConcat("Item ", NumberToString(counter))  // "Item 1"

// Formatting output function
Function.FormatNumber {
    Input: num: Integer
    Input: label: Address
    Output: Address
    Body: {
        num_str = NumberToString(num)
        result = StringConcat(label, ": ")
        result = StringConcat(result, num_str)
        ReturnValue(result)
    }
}

price_text = FormatNumber(299, "Price")       // Returns "Price: 299"

// Building complex messages
error_code = 404
status = StringConcat("Error ", NumberToString(error_code))
// Returns "Error 404"
```

### String to Number Conversion

**Function Syntax:**
```ailang
number_result = StringToNumber(string)
```

**Examples:**
```ailang
// Basic string to number
age = StringToNumber("25")                    // Returns 25
negative = StringToNumber("-42")              // Returns -42
zero = StringToNumber("0")                    // Returns 0

// Parse user input
PrintMessage("Enter age: ")
user_input = ReadInput()
user_input = StringTrim(user_input)           // Clean whitespace
age = StringToNumber(user_input)

// Configuration parsing
config_value = "1024"
buffer_size = StringToNumber(config_value)

// Arithmetic on string numbers
str1 = "100"
str2 = "50"
num1 = StringToNumber(str1)
num2 = StringToNumber(str2)
sum = Add(num1, num2)
sum_str = NumberToString(sum)                 // "150"

// Parse integers from text
price_text = "The cost is 299 dollars"
// Would need manual extraction first
start = StringIndexOf(price_text, "299")
price_str = StringSubstring(price_text, start, Add(start, 3))
price = StringToNumber(price_str)             // Returns 299
```

**Important Notes:**
- Invalid characters are ignored or cause conversion to stop
- Non-numeric strings may return 0
- Handles negative numbers with leading `-`
- No decimal point support (integers only)

---

## Advanced Text Processing

### Line-by-Line Processing

**Text File Processing Pattern:**
```ailang
Function.ProcessTextFile {
    Input: content: Address
    Output: Integer
    Body: {
        offset = 0
        line_count = 0
        content_length = StringLength(content)
        
        WhileLoop LessThan(offset, content_length) {
            // Extract line until newline
            line = StringExtractUntil(content, offset, "\n")
            line_length = StringLength(line)
            
            // Process non-empty lines
            IfCondition GreaterThan(line_length, 0) ThenBlock: {
                line = StringTrim(line)
                ProcessLine(line)
                line_count = Add(line_count, 1)
            }
            
            // Move to next line (+1 for newline character)
            offset = Add(offset, Add(line_length, 1))
        }
        
        ReturnValue(line_count)
    }
}
```

### CSV Parsing

**CSV Row Parser:**
```ailang
Function.ParseCSVRow {
    Input: row: Address
    Output: Address
    Body: {
        fields = StringSplit(row, ",")
        field_count = XArray.XSize(fields)
        
        // Trim each field
        i = 0
        WhileLoop LessThan(i, field_count) {
            field = XArray.XGet(fields, i)
            trimmed = StringTrim(field)
            XArray.XSet(fields, i, trimmed)
            i = Add(i, 1)
        }
        
        ReturnValue(fields)
    }
}

// Usage:
csv_line = "John Doe, 30, New York"
fields = ParseCSVRow(csv_line)
name = XArray.XGet(fields, 0)   // "John Doe"
age_str = XArray.XGet(fields, 1) // "30"
city = XArray.XGet(fields, 2)   // "New York"
```

### Configuration File Parser

**INI-Style Config Parser:**
```ailang
Function.ParseConfig {
    Input: config_text: Address
    Output: Address
    Body: {
        config = XSHash.XCreate()
        lines = StringSplit(config_text, "\n")
        line_count = XArray.XSize(lines)
        
        i = 0
        WhileLoop LessThan(i, line_count) {
            line = XArray.XGet(lines, i)
            line = StringTrim(line)
            
            // Skip empty lines and comments
            line_len = StringLength(line)
            IfCondition GreaterThan(line_len, 0) ThenBlock: {
                first_char = StringCharAt(line, 0)
                
                // Skip comments (# = 35)
                IfCondition NotEqual(first_char, 35) ThenBlock: {
                    // Parse key=value
                    equals_pos = StringIndexOf(line, "=")
                    IfCondition GreaterThan(equals_pos, 0) ThenBlock: {
                        key = StringSubstring(line, 0, equals_pos)
                        key = StringTrim(key)
                        
                        value_start = Add(equals_pos, 1)
                        value = StringSubstring(line, value_start, line_len)
                        value = StringTrim(value)
                        
                        XSHash.XInsert(config, key, value)
                    }
                }
            }
            
            i = Add(i, 1)
        }
        
        ReturnValue(config)
    }
}

// Usage:
config_text = "host=localhost\nport=8080\n# Comment line\ndebug=true"
settings = ParseConfig(config_text)
host = XSHash.XLookup(settings, "host")     // "localhost"
port_str = XSHash.XLookup(settings, "port") // "8080"
port = StringToNumber(port_str)             // 8080
```

### URL Parsing

**Simple URL Parser:**
```ailang
Function.ParseURL {
    Input: url: Address
    Output: Address  // Returns hash table with components
    Body: {
        result = XSHash.XCreate()
        
        // Extract protocol
        protocol_end = StringIndexOf(url, "://")
        IfCondition GreaterThan(protocol_end, 0) ThenBlock: {
            protocol = StringSubstring(url, 0, protocol_end)
            XSHash.XInsert(result, "protocol", protocol)
            
            // Start of host
            host_start = Add(protocol_end, 3)
        } ElseBlock: {
            host_start = 0
        }
        
        // Extract host and path
        slash_pos = StringIndexOf(url, "/", host_start)
        url_len = StringLength(url)
        
        IfCondition GreaterThan(slash_pos, 0) ThenBlock: {
            host = StringSubstring(url, host_start, slash_pos)
            XSHash.XInsert(result, "host", host)
            
            path = StringSubstring(url, slash_pos, url_len)
            XSHash.XInsert(result, "path", path)
        } ElseBlock: {
            host = StringSubstring(url, host_start, url_len)
            XSHash.XInsert(result, "host", host)
            XSHash.XInsert(result, "path", "/")
        }
        
        ReturnValue(result)
    }
}

// Usage:
url = "https://example.com/api/users"
parsed = ParseURL(url)
protocol = XSHash.XLookup(parsed, "protocol")  // "https"
host = XSHash.XLookup(parsed, "host")          // "example.com"
path = XSHash.XLookup(parsed, "path")          // "/api/users"
```

---

## Performance Optimization

### Use StringConcatPooled for Loops

When concatenating strings repeatedly in loops, use `StringConcatPooled` for better performance:

**Inefficient:**
```ailang
result = ""
i = 0
WhileLoop LessThan(i, 1000) {
    result = StringConcat(result, "X")  // Allocates every time
    i = Add(i, 1)
}
```

**Efficient:**
```ailang
result = ""
i = 0
WhileLoop LessThan(i, 1000) {
    result = StringConcatPooled(result, "X")  // Uses memory pool
    i = Add(i, 1)
}
```

### Minimize Temporary Strings

**Less Efficient:**
```ailang
temp1 = StringConcat("Hello", " ")
temp2 = StringConcat(temp1, "World")
temp3 = StringConcat(temp2, "!")
result = temp3
```

**More Efficient:**
```ailang
result = StringConcat(StringConcat(StringConcat("Hello", " "), "World"), "!")
```

**Most Efficient (Using StringBuilder Pattern):**
```ailang
Function.BuildString {
    Input: parts: Address  // Array of strings
    Output: Address
    Body: {
        // Calculate total length
        total_len = 0
        part_count = XArray.XSize(parts)
        i = 0
        
        WhileLoop LessThan(i, part_count) {
            part = XArray.XGet(parts, i)
            part_len = StringLength(part)
            total_len = Add(total_len, part_len)
            i = Add(i, 1)
        }
        
        // Allocate once
        buffer = Allocate(Add(total_len, 1))
        offset = 0
        i = 0
        
        // Copy all parts
        WhileLoop LessThan(i, part_count) {
            part = XArray.XGet(parts, i)
            part_len = StringLength(part)
            
            // Manual copy
            j = 0
            WhileLoop LessThan(j, part_len) {
                char = StringCharAt(part, j)
                StoreValue(Add(buffer, Add(offset, j)), char)
                j = Add(j, 1)
            }
            
            offset = Add(offset, part_len)
            i = Add(i, 1)
        }
        
        // Null terminate
        StoreValue(Add(buffer, offset), 0)
        
        ReturnValue(buffer)
    }
}
```

### Cache String Lengths

**Inefficient:**
```ailang
i = 0
WhileLoop LessThan(i, StringLength(text)) {
    // StringLength called every iteration!
    char = StringCharAt(text, i)
    ProcessChar(char)
    i = Add(i, 1)
}
```

**Efficient:**
```ailang
text_len = StringLength(text)  // Cache length
i = 0
WhileLoop LessThan(i, text_len) {
    char = StringCharAt(text, i)
    ProcessChar(char)
    i = Add(i, 1)
}
```

---

## Real-World Examples

### Log File Analyzer

```ailang
Function.AnalyzeLogFile {
    Input: log_content: Address
    Output: Address
    Body: {
        stats = XSHash.XCreate()
        XSHash.XInsert(stats, "errors", NumberToString(0))
        XSHash.XInsert(stats, "warnings", NumberToString(0))
        XSHash.XInsert(stats, "info", NumberToString(0))
        
        lines = StringSplit(log_content, "\n")
        line_count = XArray.XSize(lines)
        
        i = 0
        WhileLoop LessThan(i, line_count) {
            line = XArray.XGet(lines, i)
            line_upper = StringToUpper(line)
            
            // Count log levels
            IfCondition StringContains(line_upper, "ERROR") ThenBlock: {
                current = XSHash.XLookup(stats, "errors")
                count = StringToNumber(current)
                count = Add(count, 1)
                XSHash.XInsert(stats, "errors", NumberToString(count))
            }
            
            IfCondition StringContains(line_upper, "WARNING") ThenBlock: {
                current = XSHash.XLookup(stats, "warnings")
                count = StringToNumber(current)
                count = Add(count, 1)
                XSHash.XInsert(stats, "warnings", NumberToString(count))
            }
            
            IfCondition StringContains(line_upper, "INFO") ThenBlock: {
                current = XSHash.XLookup(stats, "info")
                count = StringToNumber(current)
                count = Add(count, 1)
                XSHash.XInsert(stats, "info", NumberToString(count))
            }
            
            i = Add(i, 1)
        }
        
        ReturnValue(stats)
    }
}

// Usage:
log_data = "INFO: Starting application\nERROR: Connection failed\nWARNING: Retry attempt 1\nERROR: Max retries exceeded"
stats = AnalyzeLogFile(log_data)

errors = StringToNumber(XSHash.XLookup(stats, "errors"))     // 2
warnings = StringToNumber(XSHash.XLookup(stats, "warnings")) // 1
info = StringToNumber(XSHash.XLookup(stats, "info"))         // 1
```

### Simple Template Engine

```ailang
Function.RenderTemplate {
    Input: template: Address
    Input: variables: Address  // Hash table
    Output: Address
    Body: {
        result = template
        
        // Get all variable keys
        keys = XSHash.XGetKeys(variables)
        key_count = XArray.XSize(keys)
        
        i = 0
        WhileLoop LessThan(i, key_count) {
            key = XArray.XGet(keys, i)
            value = XSHash.XLookup(variables, key)
            
            // Create placeholder: {{KEY}}
            placeholder = StringConcat("{{", key)
            placeholder = StringConcat(placeholder, "}}")
            
            // Replace (note: replaces first occurrence only)
            result = StringReplace(result, placeholder, value)
            
            i = Add(i, 1)
        }
        
        ReturnValue(result)
    }
}

// Usage:
template_text = "Hello {{NAME}}, welcome to {{SYSTEM}}!"

vars = XSHash.XCreate()
XSHash.XInsert(vars, "NAME", "Alice")
XSHash.XInsert(vars, "SYSTEM", "AILANG")

rendered = RenderTemplate(template_text, vars)
// Returns: "Hello Alice, welcome to AILANG!"
```

### Email Address Validator

```ailang
Function.IsValidEmail {
    Input: email: Address
    Output: Integer
    Body: {
        // Must contain @
        at_pos = StringIndexOf(email, "@")
        IfCondition LessEqual(at_pos, 0) ThenBlock: {
            ReturnValue(0)  // Invalid: no @ or @ at start
        }
        
        email_len = StringLength(email)
        
        // Must contain . after @
        dot_pos = StringIndexOf(email, ".", at_pos)
        IfCondition LessEqual(dot_pos, 0) ThenBlock: {
            ReturnValue(0)  // Invalid: no . after @
        }
        
        // . must not be immediately after @
        IfCondition EqualTo(dot_pos, Add(at_pos, 1)) ThenBlock: {
            ReturnValue(0)  // Invalid: @. pattern
        }
        
        // Must have at least one char after final .
        IfCondition GreaterEqual(dot_pos, Subtract(email_len, 1)) ThenBlock: {
            ReturnValue(0)  // Invalid: . at end
        }
        
        ReturnValue(1)  // Valid
    }
}

// Usage:
valid1 = IsValidEmail("user@example.com")     // Returns 1
valid2 = IsValidEmail("invalid.email")        // Returns 0
valid3 = IsValidEmail("@example.com")         // Returns 0
valid4 = IsValidEmail("user@example")         // Returns 0
```

---

## Best Practices

### Memory Management

1. **Always null-terminate manually created strings**
   ```ailang
   buffer = Allocate(10)
   StoreValue(Add(buffer, 0), 72)  // 'H'
   StoreValue(Add(buffer, 1), 105) // 'i'
   StoreValue(Add(buffer, 2), 0)   // NULL terminator
   ```

2. **Validate string lengths before operations**
   ```ailang
   IfCondition GreaterThan(StringLength(input), max_size) ThenBlock: {
       PrintMessage("Input too long!")
       ReturnValue(0)
   }
   ```

3. **Clean up allocated strings** (if using manual memory management)

### Performance Guidelines

1. **Use `StringConcatPooled` for loops** - significantly faster for repeated concatenations
2. **Cache `StringLength` results** - don't recalculate in loops
3. **Prefer `StringCharAt` over repeated `StringSubstring`** for character iteration
4. **Use `StringContains` before `StringIndexOf`** if you only need existence check

### Code Organization

1. **Create reusable string utility functions**
   ```ailang
   Function.IsWhitespace {
       Input: char_code: Integer
       Output: Integer
       Body: {
           // Space=32, Tab=9, Newline=10, CR=13
           is_space = EqualTo(char_code, 32)
           is_tab = EqualTo(char_code, 9)
           is_newline = EqualTo(char_code, 10)
           is_cr = EqualTo(char_code, 13)
           
           result = Or(Or(is_space, is_tab), Or(is_newline, is_cr))
           ReturnValue(result)
       }
   }
   ```

2. **Group related string operations into modules**
3. **Use descriptive variable names**
   ```ailang
   // Good
   user_email = "user@example.com"
   domain_start = StringIndexOf(user_email, "@")
   
   // Avoid
   s = "user@example.com"
   p = StringIndexOf(s, "@")
   ```

4. **Document string format expectations**
   ```ailang
   // Expects: "YYYY-MM-DD" format
   Function.ParseDate {
       Input: date_string: Address
       ...
   }
   ```

### Error Handling

1. **Check for NULL/empty strings**
   ```ailang
   IfCondition EqualTo(StringLength(input), 0) ThenBlock: {
       PrintMessage("Error: Empty input")
       ReturnValue(0)
   }
   ```

2. **Validate search results**
   ```ailang
   pos = StringIndexOf(text, needle)
   IfCondition EqualTo(pos, -1) ThenBlock: {
       PrintMessage("Substring not found")
       ReturnValue(0)
   }
   ```

3. **Handle edge cases** (empty strings, single characters, etc.)

---

## Function Reference Summary

| Function | Arguments | Returns | Description |
|----------|-----------|---------|-------------|
| `StringFromChar` | `(ascii_code)` | String | Convert ASCII code to 1-char string |
| `StringLength` | `(string)` | Integer | Get length of string |
| `StringConcat` | `(str1, str2)` | String | Concatenate two strings |
| `StringConcatPooled` | `(str1, str2)` | String | Pool-based concatenation (faster) |
| `StringEquals` | `(str1, str2)` | Integer | Returns 1 if equal, 0 if not |
| `StringCompare` | `(str1, str2)` | Integer | Returns 0 if equal, non-zero if different |
| `StringCharAt` | `(string, index)` | Integer | Get ASCII code at position |
| `StringIndexOf` | `(haystack, needle[, start])` | Integer | Find position (-1 if not found) |
| `StringContains` | `(haystack, needle)` | Integer | Returns 1 if contains, 0 if not |
| `StringSubstring` | `(string, start, end)` | String | Extract substring (start to end) |
| `StringExtract` | `(string, start, end)` | String | Alias for StringSubstring |
| `StringExtractUntil` | `(buffer, offset, delim)` | String | Extract until delimiter |
| `StringToUpper` | `(string)` | String | Convert to uppercase |
| `StringToLower` | `(string)` | String | Convert to lowercase |
| `StringTrim` | `(string)` | String | Remove leading/trailing whitespace |
| `StringReplace` | `(str, old, new)` | String | Replace first occurrence |
| `StringSplit` | `(string, delimiter)` | Array | Split into array of strings |
| `StringToNumber` | `(string)` | Integer | Parse string to integer |
| `NumberToString` | `(number)` | String | Convert integer to string |
| `ReadInput` | `()` | String | Read line from stdin |
| `PrintString` | `(string)` | void | Print string to stdout |

---

## ASCII Reference

Common ASCII codes for string processing:

- **Digits:** `'0'=48` to `'9'=57`
- **Uppercase:** `'A'=65` to `'Z'=90`
- **Lowercase:** `'a'=97` to `'z'=122`
- **Whitespace:** Space=32, Tab=9, Newline=10, CR=13
- **Punctuation:** `'!'=33`, `'.'=46`, `','=44`, `':'=58`, `';'=59`
- **Operators:** `'+'=43`, `'-'=45`, `'*'=42`, `'/'=47`, `'='=61`
- **Brackets:** `'('=40`, `')'=41`, `'['=91`, `']'=93`, `'{'=123`, `'}'=125`

---

This manual covers all currently implemented string operations in AILANG. For the latest updates and additional examples, see the official AILANG documentation and repository.