# AILANG Array Primitives Manual

**Version:** 1.0  
**Type:** Core Language Primitives  
**Implementation:** Compiler Built-ins (x86-64 Assembly)

---

## Table of Contents

1. [Overview](#overview)
2. [Array Structure](#array-structure)
3. [Core Array Functions](#core-array-functions)
4. [Memory Management](#memory-management)
5. [Usage Patterns](#usage-patterns)
6. [Performance Characteristics](#performance-characteristics)
7. [Common Pitfalls](#common-pitfalls)
8. [Real-World Examples](#real-world-examples)
9. [Comparison with Library Arrays](#comparison-with-library-arrays)

---

## Overview

AILANG provides built-in array primitives implemented directly in the compiler as optimized x86-64 assembly. These are **fixed-size** arrays that must be explicitly managed.

### Key Characteristics

- **Fixed Size**: Arrays do not automatically resize
- **Zero-Indexed**: First element is at index 0
- **Pointer-Based**: Arrays are memory addresses
- **Type Flexible**: Can store integers, pointers, or addresses
- **Manual Management**: Must be explicitly destroyed

### Core Functions

```ailang
ArrayCreate(size)        // Create array
ArraySet(arr, i, val)    // Set element
ArrayGet(arr, i)         // Get element
ArrayLength(arr)         // Get capacity
ArrayDestroy(arr)        // Free memory
```

---

## Array Structure

### Memory Layout

Arrays are allocated with an 8-byte header followed by element storage:

```
Byte Offset | Contents
------------|--------------------
[0-7]       | Capacity (number of elements)
[8-15]      | Element 0
[16-23]     | Element 1
[24-31]     | Element 2
...         | ...
```

**Size Formula:** `8 + (capacity × 8)` bytes

**Example:**
```ailang
arr = ArrayCreate(5)
// Allocates: 8 + (5 × 8) = 48 bytes
// Can store 5 elements (indices 0-4)
```

### Implementation Details

- **Allocation**: Uses `mmap` syscall for memory
- **Alignment**: 8-byte aligned for 64-bit pointers
- **Header**: First 8 bytes store capacity
- **Elements**: Each element is 8 bytes (64-bit integer/pointer)

---

## Core Array Functions

### ArrayCreate

Create a new fixed-size array.

**Signature:**
```ailang
result = ArrayCreate(size)
```

**Parameters:**
- `size` - Number of elements (capacity)

**Returns:** Address of the new array (or 0 on failure)

**Examples:**
```ailang
// Create array with 10 elements
arr = ArrayCreate(10)

// Create small array
small = ArrayCreate(2)

// Create large array
large = ArrayCreate(1000)

// Default size if no argument (implementation-defined, typically 10)
default_arr = ArrayCreate()
```

**Memory Allocated:**
- Header: 8 bytes
- Elements: size × 8 bytes
- Total: `8 + (size × 8)` bytes

**Important Notes:**
- Elements are NOT initialized to zero
- Array capacity is fixed after creation
- Must call `ArrayDestroy()` when done
- Returns 0 if allocation fails

---

### ArraySet

Set an element at a specific index.

**Signature:**
```ailang
ArraySet(array, index, value)
```

**Parameters:**
- `array` - Array address
- `index` - Zero-based position (0 to capacity-1)
- `value` - Integer or address to store

**Returns:** Nothing (void operation)

**Examples:**
```ailang
arr = ArrayCreate(5)

// Set individual elements
ArraySet(arr, 0, 100)
ArraySet(arr, 1, 200)
ArraySet(arr, 2, 300)
ArraySet(arr, 3, 400)
ArraySet(arr, 4, 500)

// Store pointers/addresses
name = "Alice"
ArraySet(arr, 0, name)

hash_table = XSHash.XCreate(16)
ArraySet(arr, 1, hash_table)

// Store results of calculations
result = Add(10, 20)
ArraySet(arr, 2, result)
```

**Important Notes:**
- **NO bounds checking** - setting beyond capacity causes memory corruption
- Does NOT check if array is null
- Overwrites previous value without freeing it
- Indices start at 0

**Unsafe Examples:**
```ailang
arr = ArrayCreate(5)

// BAD: Index 5 is out of bounds (valid: 0-4)
ArraySet(arr, 5, 999)  // Memory corruption!

// BAD: Negative index
ArraySet(arr, -1, 999)  // Memory corruption!

// BAD: Array is null
arr = 0
ArraySet(arr, 0, 100)  // Segmentation fault!
```

---

### ArrayGet

Get an element at a specific index.

**Signature:**
```ailang
value = ArrayGet(array, index)
```

**Parameters:**
- `array` - Array address
- `index` - Zero-based position (0 to capacity-1)

**Returns:** Value stored at that index

**Examples:**
```ailang
arr = ArrayCreate(3)
ArraySet(arr, 0, 10)
ArraySet(arr, 1, 20)
ArraySet(arr, 2, 30)

// Get individual elements
first = ArrayGet(arr, 0)   // Returns 10
second = ArrayGet(arr, 1)  // Returns 20
third = ArrayGet(arr, 2)   // Returns 30

// Use in expressions
sum = Add(ArrayGet(arr, 0), ArrayGet(arr, 1))  // sum = 30

// Get pointer values
names = ArrayCreate(2)
ArraySet(names, 0, "Alice")
ArraySet(names, 1, "Bob")

name1 = ArrayGet(names, 0)
PrintString(name1)  // Prints "Alice"
```

**Important Notes:**
- **NO bounds checking** - accessing beyond capacity reads garbage
- Does NOT check if array is null
- Returns whatever 8 bytes happen to be at that memory location
- Uninitialized elements contain undefined values

**Unsafe Examples:**
```ailang
arr = ArrayCreate(5)

// BAD: Reading uninitialized element
value = ArrayGet(arr, 0)  // Undefined! Not initialized

// BAD: Out of bounds
value = ArrayGet(arr, 10)  // Reading invalid memory!

// BAD: Negative index
value = ArrayGet(arr, -1)  // Reading invalid memory!
```

---

### ArrayLength

Get the capacity (number of elements) of an array.

**Signature:**
```ailang
capacity = ArrayLength(array)
```

**Parameters:**
- `array` - Array address

**Returns:** Capacity stored in array header

**Examples:**
```ailang
arr = ArrayCreate(10)
len = ArrayLength(arr)  // Returns 10

// Use in loops
i = 0
WhileLoop LessThan(i, ArrayLength(arr)) {
    ArraySet(arr, i, Multiply(i, 2))
    i = Add(i, 1)
}

// Cache length for performance
arr_len = ArrayLength(arr)
i = 0
WhileLoop LessThan(i, arr_len) {
    value = ArrayGet(arr, i)
    ProcessValue(value)
    i = Add(i, 1)
}
```

**Important Notes:**
- Returns the **capacity**, not the "used" length
- Arrays don't track how many elements are actually set
- Very fast - just reads header (O(1))
- Does NOT check if array is null

---

### ArrayDestroy

Free the memory used by an array.

**Signature:**
```ailang
ArrayDestroy(array)
```

**Parameters:**
- `array` - Array address to free

**Returns:** Nothing (void operation)

**Examples:**
```ailang
// Basic cleanup
arr = ArrayCreate(10)
// ... use array ...
ArrayDestroy(arr)

// Cleanup in error handling
arr = ArrayCreate(100)
IfCondition EqualTo(arr, 0) ThenBlock: {
    PrintMessage("Failed to create array")
    ReturnValue(0)
}

// ... use array ...

ArrayDestroy(arr)
ReturnValue(1)
```

**Important Notes:**
- Uses `munmap` syscall to free memory
- Does NOT free elements (if they're pointers to allocated memory)
- After destroy, the pointer is invalid (dangling)
- Calling on null pointer is safe (no-op)
- Calling twice on same array causes undefined behavior

**Memory Leak Example:**
```ailang
// BAD: Memory leak - array never destroyed
Function.LeakMemory {
    Body: {
        arr = ArrayCreate(1000)
        // ... use array ...
        // MISSING: ArrayDestroy(arr)
        ReturnValue(1)  // Array is lost!
    }
}
```

**Proper Cleanup:**
```ailang
// GOOD: Always destroy arrays
Function.ProperCleanup {
    Body: {
        arr = ArrayCreate(1000)
        
        // ... use array ...
        
        // Clean up before returning
        ArrayDestroy(arr)
        ReturnValue(1)
    }
}
```

---

## Memory Management

### Allocation Strategy

Arrays use `mmap` directly for allocation:

```ailang
// Pseudo-code of what ArrayCreate does:
size_bytes = 8 + (capacity × 8)
address = mmap(NULL, size_bytes, PROT_READ|PROT_WRITE, 
               MAP_PRIVATE|MAP_ANONYMOUS, -1, 0)
store capacity at address
return address
```

### Deallocation Strategy

```ailang
// Pseudo-code of what ArrayDestroy does:
capacity = read from address
size_bytes = 8 + (capacity × 8)
munmap(address, size_bytes)
```

### Ownership Rules

**Rule 1: Creator Destroys**
```ailang
Function.CreateAndUse {
    Body: {
        arr = ArrayCreate(10)
        
        // Use array...
        
        ArrayDestroy(arr)  // Creator must destroy
    }
}
```

**Rule 2: Caller Owns Return Values**
```ailang
Function.CreateArray {
    Output: Address
    Body: {
        arr = ArrayCreate(10)
        ReturnValue(arr)  // Caller now responsible
    }
}

SubRoutine.Main {
    arr = CreateArray()
    // ... use arr ...
    ArrayDestroy(arr)  // Caller must destroy
}
```

**Rule 3: Don't Destroy Borrowed References**
```ailang
Function.ProcessArray {
    Input: arr: Address
    Body: {
        // Use arr...
        
        // DON'T destroy - we don't own it!
        // ArrayDestroy(arr)  // BAD!
    }
}
```

### Nested Allocations

When array elements are pointers to allocated memory:

```ailang
// Create array of strings
strings = ArrayCreate(3)

// Allocate and store strings
str1 = Allocate(10)
str2 = Allocate(10)
str3 = Allocate(10)

ArraySet(strings, 0, str1)
ArraySet(strings, 1, str2)
ArraySet(strings, 2, str3)

// MUST free in correct order:
// 1. Free elements first
i = 0
WhileLoop LessThan(i, 3) {
    str = ArrayGet(strings, i)
    Deallocate(str, 10)
    i = Add(i, 1)
}

// 2. Then free array
ArrayDestroy(strings)
```

---

## Usage Patterns

### Pattern 1: Simple Data Storage

```ailang
Function.StoreScores {
    Body: {
        scores = ArrayCreate(5)
        
        ArraySet(scores, 0, 95)
        ArraySet(scores, 1, 87)
        ArraySet(scores, 2, 92)
        ArraySet(scores, 3, 78)
        ArraySet(scores, 4, 88)
        
        // Calculate average
        sum = 0
        i = 0
        WhileLoop LessThan(i, 5) {
            sum = Add(sum, ArrayGet(scores, i))
            i = Add(i, 1)
        }
        
        average = Divide(sum, 5)
        PrintMessage("Average: ")
        PrintNumber(average)
        
        ArrayDestroy(scores)
    }
}
```

### Pattern 2: Array of Pointers

```ailang
Function.StoreUserNames {
    Body: {
        users = ArrayCreate(3)
        
        ArraySet(users, 0, "Alice")
        ArraySet(users, 1, "Bob")
        ArraySet(users, 2, "Charlie")
        
        // Print all names
        i = 0
        WhileLoop LessThan(i, 3) {
            name = ArrayGet(users, i)
            PrintString(name)
            i = Add(i, 1)
        }
        
        // No need to free strings (they're literals)
        ArrayDestroy(users)
    }
}
```

### Pattern 3: Array of Structures

```ailang
Function.CreateUserDatabase {
    Output: Address
    Body: {
        users = ArrayCreate(10)
        
        // Each element is a hash table
        i = 0
        WhileLoop LessThan(i, 10) {
            user = XSHash.XCreate(8)
            ArraySet(users, i, user)
            i = Add(i, 1)
        }
        
        ReturnValue(users)
    }
}

Function.DestroyUserDatabase {
    Input: users: Address
    Body: {
        count = ArrayLength(users)
        
        // Free each hash table
        i = 0
        WhileLoop LessThan(i, count) {
            user = ArrayGet(users, i)
            XSHash.XDestroy(user)
            i = Add(i, 1)
        }
        
        // Free array
        ArrayDestroy(users)
    }
}
```

### Pattern 4: Return Multiple Values

```ailang
Function.ParseCSVRow {
    Input: line: Address
    Output: Address
    Body: {
        // Create array to hold fields
        fields = ArrayCreate(10)
        field_count = 0
        
        // Parse line and populate array
        parts = StringSplit(line, ",")
        parts_count = XArray.XSize(parts)
        
        i = 0
        WhileLoop LessThan(i, parts_count) {
            part = XArray.XGet(parts, i)
            ArraySet(fields, field_count, part)
            field_count = Add(field_count, 1)
            i = Add(i, 1)
        }
        
        XArray.XDestroy(parts)
        ReturnValue(fields)
    }
}

// Usage:
fields = ParseCSVRow("Alice,30,Engineer")
name = ArrayGet(fields, 0)
age = ArrayGet(fields, 1)
job = ArrayGet(fields, 2)
ArrayDestroy(fields)
```

### Pattern 5: Fixed-Size Buffer

```ailang
Function.CreateFixedBuffer {
    Input: size: Integer
    Output: Address
    Body: {
        buffer = ArrayCreate(size)
        
        // Initialize all to zero
        i = 0
        WhileLoop LessThan(i, size) {
            ArraySet(buffer, i, 0)
            i = Add(i, 1)
        }
        
        ReturnValue(buffer)
    }
}
```

### Pattern 6: Working with Indices

```ailang
Function.FindInArray {
    Input: arr: Address
    Input: target: Integer
    Output: Integer
    Body: {
        size = ArrayLength(arr)
        
        i = 0
        WhileLoop LessThan(i, size) {
            value = ArrayGet(arr, i)
            
            IfCondition EqualTo(value, target) ThenBlock: {
                ReturnValue(i)  // Return index
            }
            
            i = Add(i, 1)
        }
        
        ReturnValue(-1)  // Not found
    }
}

// Usage:
arr = ArrayCreate(5)
ArraySet(arr, 0, 10)
ArraySet(arr, 1, 20)
ArraySet(arr, 2, 30)
ArraySet(arr, 3, 40)
ArraySet(arr, 4, 50)

index = FindInArray(arr, 30)  // Returns 2
index2 = FindInArray(arr, 99)  // Returns -1
```

---

## Performance Characteristics

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| `ArrayCreate` | O(1) | Single mmap syscall |
| `ArraySet` | O(1) | Direct memory write |
| `ArrayGet` | O(1) | Direct memory read |
| `ArrayLength` | O(1) | Read header |
| `ArrayDestroy` | O(1) | Single munmap syscall |

### Memory Overhead

- **Per Array**: 8 bytes (capacity header)
- **Per Element**: 8 bytes (64-bit value)
- **Total for n elements**: `8 + (n × 8)` bytes

### Performance Tips

1. **Cache length in loops:**
   ```ailang
   // GOOD: Cache length
   len = ArrayLength(arr)
   i = 0
   WhileLoop LessThan(i, len) { ... }
   
   // BAD: Recalculate every iteration
   i = 0
   WhileLoop LessThan(i, ArrayLength(arr)) { ... }
   ```

2. **Pre-size appropriately:**
   ```ailang
   // GOOD: Create exact size needed
   arr = ArrayCreate(100)
   
   // BAD: Over-allocate
   arr = ArrayCreate(10000)  // Wasted memory
   ```

3. **Batch operations when possible:**
   ```ailang
   // GOOD: Process in batches
   i = 0
   WhileLoop LessThan(i, ArrayLength(arr)) {
       val = ArrayGet(arr, i)
       Process(val)
       i = Add(i, 1)
   }
   ```

---

## Common Pitfalls

### Pitfall 1: Forgetting to Destroy

```ailang
// BAD: Memory leak
Function.CreateTemporary {
    Body: {
        temp = ArrayCreate(100)
        // ... use temp ...
        // MISSING: ArrayDestroy(temp)
    }
}

// GOOD: Always destroy
Function.CreateTemporary {
    Body: {
        temp = ArrayCreate(100)
        // ... use temp ...
        ArrayDestroy(temp)
    }
}
```

### Pitfall 2: Out of Bounds Access

```ailang
// BAD: No bounds checking
arr = ArrayCreate(5)
ArraySet(arr, 10, 999)  // Memory corruption!

// GOOD: Validate indices
arr = ArrayCreate(5)
index = 10

IfCondition LessThan(index, ArrayLength(arr)) ThenBlock: {
    ArraySet(arr, index, 999)
} ElseBlock: {
    PrintMessage("Index out of bounds!")
}
```

### Pitfall 3: Using After Destroy

```ailang
// BAD: Use after free
arr = ArrayCreate(10)
ArrayDestroy(arr)
value = ArrayGet(arr, 0)  // Undefined behavior!

// GOOD: Don't use after destroy
arr = ArrayCreate(10)
value = ArrayGet(arr, 0)
ArrayDestroy(arr)
// Don't touch arr after this point
```

### Pitfall 4: Not Freeing Nested Data

```ailang
// BAD: Memory leak of inner data
arr = ArrayCreate(5)
ArraySet(arr, 0, Allocate(100))
ArraySet(arr, 1, Allocate(100))
ArrayDestroy(arr)  // Leaks the allocated blocks!

// GOOD: Free nested data first
arr = ArrayCreate(5)
ArraySet(arr, 0, Allocate(100))
ArraySet(arr, 1, Allocate(100))

// Free contents first
i = 0
WhileLoop LessThan(i, 2) {
    ptr = ArrayGet(arr, i)
    Deallocate(ptr, 100)
    i = Add(i, 1)
}

ArrayDestroy(arr)
```

### Pitfall 5: Uninitialized Elements

```ailang
// BAD: Reading uninitialized memory
arr = ArrayCreate(10)
sum = 0
i = 0
WhileLoop LessThan(i, 10) {
    sum = Add(sum, ArrayGet(arr, i))  // Garbage values!
    i = Add(i, 1)
}

// GOOD: Initialize before reading
arr = ArrayCreate(10)
i = 0
WhileLoop LessThan(i, 10) {
    ArraySet(arr, i, 0)  // Initialize to zero
    i = Add(i, 1)
}

// Now safe to read
sum = 0
i = 0
WhileLoop LessThan(i, 10) {
    sum = Add(sum, ArrayGet(arr, i))
    i = Add(i, 1)
}
```

---

## Real-World Examples

### Example 1: Command Line Arguments

```ailang
Function.ParseArguments {
    Input: argc: Integer
    Input: argv: Address
    Output: Address
    Body: {
        // Create array to hold arguments
        args = ArrayCreate(argc)
        
        i = 0
        WhileLoop LessThan(i, argc) {
            arg_ptr = ArrayGet(argv, i)
            ArraySet(args, i, arg_ptr)
            i = Add(i, 1)
        }
        
        ReturnValue(args)
    }
}
```

### Example 2: Fixed-Size Stack

```ailang
// Stack using array (capacity-limited)
Function.StackCreate {
    Input: capacity: Integer
    Output: Address
    Body: {
        stack = ArrayCreate(Add(capacity, 1))
        // Element 0 stores current size
        ArraySet(stack, 0, 0)
        ReturnValue(stack)
    }
}

Function.StackPush {
    Input: stack: Address
    Input: value: Integer
    Output: Integer
    Body: {
        size = ArrayGet(stack, 0)
        capacity = Subtract(ArrayLength(stack), 1)
        
        IfCondition GreaterEqual(size, capacity) ThenBlock: {
            ReturnValue(0)  // Stack full
        }
        
        // Push value
        new_index = Add(size, 1)
        ArraySet(stack, new_index, value)
        ArraySet(stack, 0, new_index)
        
        ReturnValue(1)  // Success
    }
}

Function.StackPop {
    Input: stack: Address
    Output: Integer
    Body: {
        size = ArrayGet(stack, 0)
        
        IfCondition EqualTo(size, 0) ThenBlock: {
            ReturnValue(-1)  // Stack empty
        }
        
        value = ArrayGet(stack, size)
        ArraySet(stack, 0, Subtract(size, 1))
        
        ReturnValue(value)
    }
}
```

### Example 3: Matrix (2D Array)

```ailang
// Represent matrix as flat array
Function.MatrixCreate {
    Input: rows: Integer
    Input: cols: Integer
    Output: Address
    Body: {
        total = Multiply(rows, cols)
        matrix = ArrayCreate(Add(total, 2))
        
        // Store dimensions
        ArraySet(matrix, 0, rows)
        ArraySet(matrix, 1, cols)
        
        // Initialize to zero
        i = 2
        WhileLoop LessThan(i, Add(total, 2)) {
            ArraySet(matrix, i, 0)
            i = Add(i, 1)
        }
        
        ReturnValue(matrix)
    }
}

Function.MatrixSet {
    Input: matrix: Address
    Input: row: Integer
    Input: col: Integer
    Input: value: Integer
    Body: {
        cols = ArrayGet(matrix, 1)
        index = Add(Multiply(row, cols), col)
        ArraySet(matrix, Add(index, 2), value)
    }
}

Function.MatrixGet {
    Input: matrix: Address
    Input: row: Integer
    Input: col: Integer
    Output: Integer
    Body: {
        cols = ArrayGet(matrix, 1)
        index = Add(Multiply(row, cols), col)
        ReturnValue(ArrayGet(matrix, Add(index, 2)))
    }
}

// Usage:
matrix = MatrixCreate(3, 3)
MatrixSet(matrix, 0, 0, 1)
MatrixSet(matrix, 1, 1, 5)
MatrixSet(matrix, 2, 2, 9)

value = MatrixGet(matrix, 1, 1)  // Returns 5
```

---

## Comparison with Library Arrays

### Built-in Arrays vs XArray

| Feature | Built-in Arrays | Library.XArrays |
|---------|----------------|-----------------|
| **Allocation** | Fixed size | Dynamic (auto-resize) |
| **Performance** | Faster (no overhead) | Slower (extra bookkeeping) |
| **Bounds Check** | None | Optional |
| **Memory** | Minimal overhead | Extra metadata (24 bytes) |
| **API** | 5 simple functions | 15+ functions |
| **Use Case** | Known size, performance-critical | Unknown size, convenience |

### When to Use Built-in Arrays

✅ Size known at creation  
✅ Performance critical path  
✅ Simple fixed-size buffers  
✅ Low-level system programming  
✅ Minimal memory overhead needed

### When to Use XArray

✅ Size unknown or variable  
✅ Frequent push/pop operations  
✅ Need automatic resizing  
✅ Want helper functions (sort, search)  
✅ Convenience over performance

### Example Comparison

**Built-in Array:**
```ailang
arr = ArrayCreate(5)
ArraySet(arr, 0, 10)
ArraySet(arr, 1, 20)
value = ArrayGet(arr, 0)
ArrayDestroy(arr)
```

**XArray:**
```ailang
arr = XArray.XCreate(5)
XArray.XPush(arr, 10)  // Auto-handles index
XArray.XPush(arr, 20)  // Auto-resizes if needed
value = XArray.XGet(arr, 0)
XArray.XDestroy(arr)
```

---

## Best Practices

1. **Always initialize before reading:**
   ```ailang
   arr = ArrayCreate(10)
   i = 0
   WhileLoop LessThan(i, 10) {
       ArraySet(arr, i, 0)
       i = Add(i, 1)
   }
   ```

2. **Validate indices manually:**
   ```ailang
   IfCondition And(GreaterEqual(index, 0), 
                   LessThan(index, ArrayLength(arr))) ThenBlock: {
       value = ArrayGet(arr, index)
   }
   ```

3. **Use clear naming:**
   ```ailang
   // GOOD: Descriptive names
   user_scores = ArrayCreate(10)
   player_names = ArrayCreate(5)
   
   // BAD: Unclear
   arr1 = ArrayCreate(10)
   arr2 = ArrayCreate(5)
   ```

4. **Document capacity:**
   ```ailang
   // Create array for 100 users
   users = ArrayCreate(100)
   ```

5. **Clean up in correct order:**
   ```ailang
   // Free contents first, then container
   FreeContents(arr)
   ArrayDestroy(arr)
   ```

---

## Version History

### Version 1.0 (Current)
- Core array primitives
- Fixed-size allocation
- Direct mmap/munmap implementation
- Zero-copy design

---

## See Also

- **Library.XArrays Manual**: Dynamic arrays with auto-resize
- **AILANG Memory Management Guide**: Allocate/Deallocate patterns
- **AILANG String Operations Manual**: String array patterns
- **Library.HashMap Manual**: Arrays of hash tables

---

## License

Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering  
Licensed under the Sean Collins Software License (SCSL)