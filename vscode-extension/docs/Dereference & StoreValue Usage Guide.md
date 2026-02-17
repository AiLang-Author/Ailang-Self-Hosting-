# Dereference & StoreValue Usage Guide

## Quick Reference for Fixed Functions

### Dereference() - Reading Memory

#### Syntax
```ailang
value = Dereference(address, size_hint)
```

#### Parameters
- `address`: Memory address to read from
- `size_hint`: (Optional) Size of data to read
  - `"byte"` - Read 1 byte (0-255)
  - `"word"` - Read 2 bytes (0-65535)
  - `"dword"` - Read 4 bytes
  - `"qword"` - Read 8 bytes (default if omitted)

#### Examples

```ailang
// Example 1: Reading a single byte
buffer = Allocate(100)
StoreValue(buffer, 65)  // Store 'A'

// CORRECT: Read as byte
char = Dereference(buffer, "byte")
// Result: char = 65

// WRONG: Read without size hint (reads 8 bytes)
char = Dereference(buffer)
// Result: char = might be huge number!


// Example 2: Reading ASCII characters from a string
text_buffer = Allocate(20)

// Store "HELLO"
StoreValue(text_buffer, 72)       // 'H'
StoreValue(Add(text_buffer, 1), 69)  // 'E'
StoreValue(Add(text_buffer, 2), 76)  // 'L'
StoreValue(Add(text_buffer, 3), 76)  // 'L'
StoreValue(Add(text_buffer, 4), 79)  // 'O'

// Read back individual characters
h = Dereference(text_buffer, "byte")           // 72
e = Dereference(Add(text_buffer, 1), "byte")   // 69
l1 = Dereference(Add(text_buffer, 2), "byte")  // 76


// Example 3: Reading different data types
data = Allocate(100)

// Store a large number (8 bytes)
StoreValue(data, 1234567890)

// Read it back as qword (default)
number = Dereference(data)  // or Dereference(data, "qword")
// Result: number = 1234567890


// Example 4: Using GetByte (convenience function)
message = "Hello World"

// Get individual bytes
h = GetByte(message, 0)  // 72 ('H')
e = GetByte(message, 1)  // 101 ('e')
space = GetByte(message, 5)  // 32 (' ')
```

### StoreValue() - Writing Memory

#### Syntax
```ailang
StoreValue(address, value)
```

#### Parameters
- `address`: Memory address to write to
- `value`: Value to write (automatic size detection)

#### Behavior
- If `value` is 0-255: Stores as **1 byte**
- If `value` is > 255: Stores as **8 bytes** (qword)

#### Examples

```ailang
// Example 1: Storing bytes (characters)
buffer = Allocate(100)

// These store as single bytes (0-255)
StoreValue(buffer, 65)              // 'A' - 1 byte
StoreValue(Add(buffer, 1), 66)      // 'B' - 1 byte
StoreValue(Add(buffer, 2), 67)      // 'C' - 1 byte
StoreValue(Add(buffer, 3), 0)       // null terminator - 1 byte


// Example 2: Storing large numbers
buffer = Allocate(100)

// This stores as 8 bytes
StoreValue(buffer, 1234567890)

// Read it back
value = Dereference(buffer, "qword")  // 1234567890


// Example 3: Building a string manually
buffer = Allocate(20)
offset = 0

// Store "HELLO"
StoreValue(Add(buffer, offset), 72)   // 'H'
offset = Add(offset, 1)
StoreValue(Add(buffer, offset), 69)   // 'E'
offset = Add(offset, 1)
StoreValue(Add(buffer, offset), 76)   // 'L'
offset = Add(offset, 1)
StoreValue(Add(buffer, offset), 76)   // 'L'
offset = Add(offset, 1)
StoreValue(Add(buffer, offset), 79)   // 'O'
offset = Add(offset, 1)
StoreValue(Add(buffer, offset), 0)    // null terminator

// Now buffer contains the string "HELLO"
PrintString(buffer)  // Prints: HELLO
```

## Common Patterns

### Pattern 1: Character-by-Character String Processing

```ailang
SubRoutine ProcessString {
    // Input: text (global string)
    // Output: result (processed data)
    
    i = 0
    length = StringLength(text)
    
    WhileLoop LessThan(i, length) {
        // Get character at position i
        char = StringCharAt(text, i)
        
        // Process the character
        IfCondition EqualTo(char, 65) ThenBlock: {  // 'A'
            PrintMessage("Found an A!\n")
        }
        
        i = Add(i, 1)
    }
}
```

### Pattern 2: Manual Buffer Manipulation

```ailang
SubRoutine BuildCustomString {
    buffer = Allocate(100)
    pos = 0
    
    // Write "TEST: "
    StoreValue(Add(buffer, pos), 84)  // 'T'
    pos = Add(pos, 1)
    StoreValue(Add(buffer, pos), 69)  // 'E'
    pos = Add(pos, 1)
    StoreValue(Add(buffer, pos), 83)  // 'S'
    pos = Add(pos, 1)
    StoreValue(Add(buffer, pos), 84)  // 'T'
    pos = Add(pos, 1)
    StoreValue(Add(buffer, pos), 58)  // ':'
    pos = Add(pos, 1)
    StoreValue(Add(buffer, pos), 32)  // ' '
    pos = Add(pos, 1)
    StoreValue(Add(buffer, pos), 0)   // null
    
    PrintString(buffer)
    Deallocate(buffer, 100)
}
```

### Pattern 3: Reading Binary Data

```ailang
SubRoutine ReadBinaryData {
    data = Allocate(100)
    
    // Suppose data is filled with binary values
    
    // Read first byte
    byte1 = Dereference(data, "byte")
    
    // Read first word (2 bytes)
    word1 = Dereference(data, "word")
    
    // Read first dword (4 bytes)
    dword1 = Dereference(data, "dword")
    
    // Read first qword (8 bytes)
    qword1 = Dereference(data, "qword")
    
    Deallocate(data, 100)
}
```

### Pattern 4: Memory Copy with Byte Operations

```ailang
SubRoutine CopyBytes {
    // Manual byte-by-byte copy
    source = Allocate(100)
    dest = Allocate(100)
    
    // Fill source
    StoreValue(source, 72)  // 'H'
    StoreValue(Add(source, 1), 73)  // 'I'
    StoreValue(Add(source, 2), 0)
    
    // Copy byte by byte
    i = 0
    WhileLoop LessThan(i, 3) {
        byte_val = Dereference(Add(source, i), "byte")
        StoreValue(Add(dest, i), byte_val)
        i = Add(i, 1)
    }
    
    // Or use built-in MemoryCopy
    MemoryCopy(dest, source, 3)
    
    Deallocate(source, 100)
    Deallocate(dest, 100)
}
```

## ASCII Character Reference

Common ASCII values for quick reference:

| Character | Value | Character | Value |
|-----------|-------|-----------|-------|
| `\0` (null) | 0 | `'0'` | 48 |
| Space | 32 | `'9'` | 57 |
| `'!'` | 33 | `'A'` | 65 |
| `'"'` | 34 | `'Z'` | 90 |
| `'#'` | 35 | `'a'` | 97 |
| `'@'` | 64 | `'z'` | 122 |

## Common Mistakes to Avoid

### ❌ Mistake 1: Forgetting size hint for byte operations
```ailang
// WRONG - reads 8 bytes, might get huge number
byte = Dereference(buffer)

// CORRECT - reads 1 byte
byte = Dereference(buffer, "byte")
```

### ❌ Mistake 2: Using wrong size for character data
```ailang
// WRONG - stores as 8-byte value
StoreValue(buffer, 1000)  // Too large for byte

// CORRECT - use values 0-255 for single bytes
StoreValue(buffer, 65)  // 'A'
```

### ❌ Mistake 3: Not null-terminating strings
```ailang
// WRONG - no null terminator
buffer = Allocate(10)
StoreValue(buffer, 72)      // 'H'
StoreValue(Add(buffer, 1), 73)  // 'I'
PrintString(buffer)  // May print garbage!

// CORRECT - always null-terminate
buffer = Allocate(10)
StoreValue(buffer, 72)      // 'H'
StoreValue(Add(buffer, 1), 73)  // 'I'
StoreValue(Add(buffer, 2), 0)   // null terminator
PrintString(buffer)  // Prints: HI
```

### ❌ Mistake 4: Reading past buffer end
```ailang
// WRONG - reading beyond allocated memory
buffer = Allocate(5)
value = Dereference(Add(buffer, 100), "byte")  // CRASH!

// CORRECT - stay within bounds
buffer = Allocate(100)
value = Dereference(Add(buffer, 50), "byte")  // OK
Deallocate(buffer, 100)
```

## Performance Tips

1. **Use StringCharAt() for string access** - It's optimized and safer
2. **Use MemoryCopy() for bulk copies** - Much faster than byte-by-byte
3. **Use MemorySet() for initialization** - Faster than loops
4. **Cache string length** - Don't call StringLength() repeatedly in loops
5. **Use appropriate data types** - Don't use strings where numbers work

## Testing Your Code

Always test with the provided test harness:

```bash
./ailang_compiler string_operations_test_harness_v2.ailang
./string_operations_test_harness_v2_exec
```

Look for:
- ✅ 100% pass rate
- ✅ All byte operations returning correct values
- ✅ No segmentation faults
- ✅ No memory leaks

---

**Remember:** The bugs are now fixed, but proper usage is still important for reliable code!