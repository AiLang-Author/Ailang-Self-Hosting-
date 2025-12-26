# LinkagePool Reference Manual

## Overview

**LinkagePool** is a powerful feature in AI Lang that enables structured data sharing between functions and across program boundaries. It provides type-safe, field-based access to allocated memory blocks with automatic null-checking and support for both integer and string data types.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Declaration Syntax](#declaration-syntax)
3. [Allocation and Deallocation](#allocation-and-deallocation)
4. [Field Access](#field-access)
5. [Function Parameters](#function-parameters)
6. [Field Types and Attributes](#field-types-and-attributes)
7. [Memory Model](#memory-model)
8. [Best Practices](#best-practices)
9. [Complete Examples](#complete-examples)
10. [Troubleshooting](#troubleshooting)

---

## Core Concepts

### What is a LinkagePool?

A **LinkagePool** is a structured memory block that acts as a typed parameter block for inter-function communication. Think of it as a struct or record type that can be:

- Dynamically allocated at runtime
- Passed between functions with type safety
- Accessed via named fields with automatic bounds checking
- Used for both input and output parameters

### Key Features

- **Type Safety**: Compiler tracks LinkagePool types through variables and parameters
- **Field Access**: Natural dot notation (e.g., `ptr.field1`)
- **Direction Control**: Mark fields as Input, Output, or InOut
- **String Support**: Fields can store integers or string pointers
- **Automatic Null Checking**: Runtime protection against null pointer dereference
- **Unlimited Parameters**: Stack-based storage allows unlimited LinkagePool parameters

---

## Declaration Syntax

### Basic Declaration

```ailang
LinkagePool.TypeName {
    "field1": Initialize=0
    "field2": Initialize=0
    "field3": Initialize=0
}
```

### Field Names
- Must be enclosed in double quotes
- Can use any valid identifier characters
- Case-sensitive

### Multiple Pools

```ailang
// Small pool
LinkagePool.TinyPool {
    "x": Initialize=0
}

// Large pool with many fields
LinkagePool.CustomerData {
    "id": Initialize=0
    "age": Initialize=0
    "balance": Initialize=0
    "status": Initialize=0
}

// Chain node for linked structures
LinkagePool.ChainNode {
    "id": Initialize=0
    "value": Initialize=0
    "next": Initialize=0
    "prev": Initialize=0
}
```

---

## Allocation and Deallocation

### AllocateLinkage

Allocates a new LinkagePool instance and returns a pointer.

**Syntax:**
```ailang
variable = AllocateLinkage(LinkagePool.TypeName)
```

**Example:**
```ailang
// Allocate a customer record
customer = AllocateLinkage(LinkagePool.CustomerData)

// Allocate multiple pools
node1 = AllocateLinkage(LinkagePool.ChainNode)
node2 = AllocateLinkage(LinkagePool.ChainNode)
node3 = AllocateLinkage(LinkagePool.ChainNode)
```

**Returns:**
- A pointer to the allocated memory block (stored in the variable)
- All fields are initialized according to their `Initialize` attribute
- The compiler tracks the type association automatically

### FreeLinkage (Future)

```ailang
FreeLinkage(pointer_variable)
```

**Note:** Currently a no-op as LinkagePools use static allocation. Full dynamic deallocation will be added in future versions.

---

## Field Access

### Reading Fields

Use dot notation to read field values:

```ailang
LinkagePool.TestPool {
    "field1": Initialize=0
    "field2": Initialize=0
    "field3": Initialize=0
}

ptr = AllocateLinkage(LinkagePool.TestPool)

// Read fields
value1 = ptr.field1
value2 = ptr.field2
value3 = ptr.field3

PrintMessage("Field1: ")
PrintNumber(ptr.field1)
PrintMessage("\n")
```

### Writing Fields

Assign values directly to fields:

```ailang
// Write to fields
ptr.field1 = 100
ptr.field2 = 200
ptr.field3 = 300

// Can use expressions
ptr.field1 = Add(ptr.field2, ptr.field3)
ptr.field2 = Multiply(ptr.field1, 2)
```

### Null Safety

All field accesses include automatic null pointer checking:

```ailang
ptr = AllocateLinkage(LinkagePool.TestPool)
// ptr is valid

value = ptr.field1  // ✓ Safe - automatic null check
```

If the pointer is null, the access will safely return 0 or handle the error appropriately.

---

## Function Parameters

### Declaring LinkagePool Parameters

Functions can accept LinkagePool types as parameters:

```ailang
Function.ProcessCustomer {
    Input: customer: LinkagePool.CustomerData
    
    Body: {
        // Access fields naturally
        customer_id = customer.id
        customer_age = customer.age
        
        PrintMessage("Processing customer ")
        PrintNumber(customer.id)
        PrintMessage("\n")
        
        // Modify output fields
        customer.status = 1
        
        ReturnValue(0)
    }
}

// Call with a LinkagePool
cust = AllocateLinkage(LinkagePool.CustomerData)
cust.id = 12345
cust.age = 30

ProcessCustomer(cust)
```

### Multiple LinkagePool Parameters

Functions support unlimited LinkagePool parameters:

```ailang
Function.TransferData {
    Input: source: LinkagePool.CustomerData
    Input: dest: LinkagePool.CustomerData
    
    Body: {
        // Copy data from source to dest
        dest.id = source.id
        dest.age = source.age
        dest.balance = source.balance
        
        ReturnValue(1)
    }
}
```

### Parameter Type Tracking

The compiler automatically:
1. Tracks which parameters are LinkagePool types
2. Stores LinkagePool parameters on the stack
3. Resolves field access through the correct pool definition
4. Validates field names at compile time

---

## Field Types and Attributes

### Integer Fields (Default)

```ailang
LinkagePool.Numbers {
    "count": Initialize=0
    "total": Initialize=100
    "max_value": Initialize=9999
}
```

Integer fields store 64-bit signed integers.

### String Fields

String fields are automatically detected when initialized with a string value:

```ailang
LinkagePool.Person {
    "id": Initialize=0           // Integer
    "name": Initialize=""         // String
    "email": Initialize=""        // String
    "age": Initialize=0           // Integer
}
```

**String Initialization:**
- `Initialize=""` creates an empty string
- `Initialize="default"` creates a string with default content
- String fields store pointers to null-terminated strings
- Strings are allocated in the data section

### Direction Attributes

Control how fields can be accessed:

```ailang
LinkagePool.IOExample {
    "input1": Initialize=0, Direction=Input     // Read-only
    "output1": Initialize=0, Direction=Output   // Write-only
    "inout1": Initialize=0, Direction=InOut     // Read-write (default)
}
```

**Direction Types:**
- `Input`: Read-only (0x10000000 flag)
- `Output`: Write-only (0x20000000 flag)
- `InOut`: Read-write (0x30000000 flag, default)

**Note:** Direction enforcement is planned for future versions. Currently documented for forward compatibility.

---

## Memory Model

### Field Layout

Fields are laid out sequentially in memory:

```
Offset  | Field      | Size
--------|------------|------
0       | field1     | 8 bytes
8       | field2     | 8 bytes
16      | field3     | 8 bytes
24      | field4     | 8 bytes
...
```

Each field occupies 8 bytes regardless of type:
- **Integers**: Stored directly as 64-bit values
- **Strings**: Stored as 64-bit pointers to data section

### Pool Size Calculation

```
Pool Size = Number of Fields × 8 bytes
```

Example:
```ailang
LinkagePool.Large {
    "f1": Initialize=0
    "f2": Initialize=0
    "f3": Initialize=0
    ...
    "f30": Initialize=0
}
// Size: 30 × 8 = 240 bytes
```

### Pointer Storage

When a LinkagePool is allocated:
1. Memory block is allocated from the static pool
2. All fields are initialized
3. Pointer to block is returned in RAX
4. Pointer is stored in the target variable

Variables holding LinkagePool pointers:
```ailang
ptr1 = AllocateLinkage(LinkagePool.TestPool)  // ptr1 holds address
ptr2 = ptr1                                    // ptr2 copies address
// Both ptr1 and ptr2 point to the same block
```

---

## Best Practices

### 1. Naming Conventions

```ailang
// Good: Descriptive pool names
LinkagePool.CustomerRecord { ... }
LinkagePool.DatabaseConnection { ... }
LinkagePool.ConfigSettings { ... }

// Good: Clear field names
"customer_id": Initialize=0
"first_name": Initialize=""
"is_active": Initialize=0
```

### 2. Field Organization

Group related fields:

```ailang
LinkagePool.PersonRecord {
    // Identity fields
    "id": Initialize=0
    "ssn": Initialize=0
    
    // Name fields
    "first_name": Initialize=""
    "last_name": Initialize=""
    "middle_initial": Initialize=""
    
    // Contact fields
    "email": Initialize=""
    "phone": Initialize=""
    
    // Demographics
    "age": Initialize=0
    "birth_year": Initialize=0
}
```

### 3. Type Safety

Always check pointer validity:

```ailang
ptr = AllocateLinkage(LinkagePool.TestPool)

// The compiler adds null checks, but you can be explicit:
IfCondition NotEqual(ptr, 0) ThenBlock: {
    // Safe to use
    value = ptr.field1
}
```

### 4. Parameter Passing

Use LinkagePools for complex data:

```ailang
// Instead of many parameters:
Function.BadExample {
    Input: id: Number
    Input: name: String
    Input: age: Number
    Input: balance: Number
    Input: status: Number
    // ... many more
}

// Better: Use a LinkagePool
Function.GoodExample {
    Input: person: LinkagePool.PersonRecord
    
    Body: {
        // Access all fields naturally
        process_id = person.id
        process_age = person.age
        // ...
    }
}
```

### 5. Chaining and Lists

Build linked structures:

```ailang
LinkagePool.ListNode {
    "value": Initialize=0
    "next": Initialize=0
}

// Build a linked list
node1 = AllocateLinkage(LinkagePool.ListNode)
node2 = AllocateLinkage(LinkagePool.ListNode)
node3 = AllocateLinkage(LinkagePool.ListNode)

node1.value = 100
node2.value = 200
node3.value = 300

node1.next = node2
node2.next = node3
node3.next = 0  // NULL terminator

// Traverse the list
current = node1
WhileLoop NotEqual(current, 0) {
    PrintNumber(current.value)
    PrintMessage("\n")
    current = current.next
}
```

---

## Complete Examples

### Example 1: Basic Usage

```ailang
LinkagePool.Point {
    "x": Initialize=0
    "y": Initialize=0
}

PrintMessage("Creating a point\n")
point = AllocateLinkage(LinkagePool.Point)

point.x = 10
point.y = 20

PrintMessage("Point coordinates: (")
PrintNumber(point.x)
PrintMessage(", ")
PrintNumber(point.y)
PrintMessage(")\n")
```

### Example 2: Function Parameters

```ailang
LinkagePool.Rectangle {
    "x": Initialize=0
    "y": Initialize=0
    "width": Initialize=0
    "height": Initialize=0
}

Function.CalculateArea {
    Input: rect: LinkagePool.Rectangle
    Output: Number
    
    Body: {
        area = Multiply(rect.width, rect.height)
        ReturnValue(area)
    }
}

Function.Main {
    rect = AllocateLinkage(LinkagePool.Rectangle)
    rect.x = 5
    rect.y = 5
    rect.width = 100
    rect.height = 50
    
    area = CalculateArea(rect)
    
    PrintMessage("Rectangle area: ")
    PrintNumber(area)
    PrintMessage("\n")
}
```

### Example 3: Data Processing Pipeline

```ailang
LinkagePool.DataRecord {
    "id": Initialize=0
    "value": Initialize=0
    "processed": Initialize=0
    "result": Initialize=0
}

Function.ValidateRecord {
    Input: record: LinkagePool.DataRecord
    Output: Number
    Body: {
        // Validation logic
        IfCondition And(GreaterThan(record.id, 0), LessThan(record.value, 1000)) ThenBlock: {
            ReturnValue(1)  // Valid
        }
        ReturnValue(0)  // Invalid
    }
}

Function.ProcessRecord {
    Input: record: LinkagePool.DataRecord
    Body: {
        // Processing logic
        record.result = Multiply(record.value, 2)
        record.processed = 1
        ReturnValue(0)
    }
}

Function.Main {
    // Create and process records
    rec1 = AllocateLinkage(LinkagePool.DataRecord)
    rec1.id = 1001
    rec1.value = 500
    
    valid = ValidateRecord(rec1)
    IfCondition EqualTo(valid, 1) ThenBlock: {
        ProcessRecord(rec1)
        PrintMessage("Processed record ")
        PrintNumber(rec1.id)
        PrintMessage(", result: ")
        PrintNumber(rec1.result)
        PrintMessage("\n")
    }
}
```

### Example 4: Complex Structure with Strings

```ailang
LinkagePool.Employee {
    "emp_id": Initialize=0
    "name": Initialize=""
    "department": Initialize=""
    "salary": Initialize=0
    "years_service": Initialize=0
}

Function.DisplayEmployee {
    Input: emp: LinkagePool.Employee
    
    Body: {
        PrintMessage("Employee ID: ")
        PrintNumber(emp.emp_id)
        PrintMessage("\n")
        
        PrintMessage("Name: ")
        PrintString(emp.name)
        PrintMessage("\n")
        
        PrintMessage("Department: ")
        PrintString(emp.department)
        PrintMessage("\n")
        
        PrintMessage("Salary: $")
        PrintNumber(emp.salary)
        PrintMessage("\n")
        
        ReturnValue(0)
    }
}
```

### Example 5: Tree Structure

```ailang
LinkagePool.TreeNode {
    "value": Initialize=0
    "left": Initialize=0
    "right": Initialize=0
    "parent": Initialize=0
}

Function.CreateTree {
    Output: LinkagePool.TreeNode
    
    Body: {
        root = AllocateLinkage(LinkagePool.TreeNode)
        root.value = 50
        
        left_child = AllocateLinkage(LinkagePool.TreeNode)
        left_child.value = 25
        left_child.parent = root
        root.left = left_child
        
        right_child = AllocateLinkage(LinkagePool.TreeNode)
        right_child.value = 75
        right_child.parent = root
        root.right = right_child
        
        ReturnValue(root)
    }
}

Function.TraverseInOrder {
    Input: node: LinkagePool.TreeNode
    
    Body: {
        IfCondition NotEqual(node, 0) ThenBlock: {
            // Left
            IfCondition NotEqual(node.left, 0) ThenBlock: {
                TraverseInOrder(node.left)
            }
            
            // Current
            PrintNumber(node.value)
            PrintMessage(" ")
            
            // Right
            IfCondition NotEqual(node.right, 0) ThenBlock: {
                TraverseInOrder(node.right)
            }
        }
        ReturnValue(0)
    }
}
```

---

## Troubleshooting

### Common Errors

#### Error: "Not a LinkagePool type"

**Problem:** Variable is not recognized as a LinkagePool pointer.

```ailang
// Wrong:
x = 123
value = x.field1  // ERROR: x is not a LinkagePool

// Correct:
ptr = AllocateLinkage(LinkagePool.TestPool)
value = ptr.field1  // ✓ Works
```

#### Error: "Field 'xyz' not in pool"

**Problem:** Attempting to access a field that doesn't exist.

```ailang
LinkagePool.TestPool {
    "field1": Initialize=0
    "field2": Initialize=0
}

ptr = AllocateLinkage(LinkagePool.TestPool)
value = ptr.field3  // ERROR: field3 doesn't exist

// Check your field names match the declaration
```

#### Error: "Cannot find variable"

**Problem:** Variable hasn't been allocated or is out of scope.

```ailang
// Wrong:
value = ptr.field1  // ERROR: ptr not declared

// Correct:
ptr = AllocateLinkage(LinkagePool.TestPool)
value = ptr.field1  // ✓ Works
```

### Debugging Tips

#### 1. Enable Debug Output

The compiler outputs detailed type tracking information:

```
DEBUG: AllocateLinkage for LinkagePool.TestPool
DEBUG: Setting pending_type on compiler
DEBUG: Verified pending_type set: LinkagePool.TestPool
DEBUG: Stored pointer type for variable 'ptr'
```

#### 2. Verify Pool Definitions

Check that your pool is properly defined before use:

```ailang
// Define BEFORE use
LinkagePool.TestPool {
    "field1": Initialize=0
}

// Then allocate
ptr = AllocateLinkage(LinkagePool.TestPool)
```

#### 3. Test Field Access Separately

Test reads and writes independently:

```ailang
// Test write
ptr.field1 = 100
PrintMessage("Wrote 100\n")

// Test read
value = ptr.field1
PrintMessage("Read: ")
PrintNumber(value)
PrintMessage("\n")
```

#### 4. Check Parameter Types

Verify function parameter types match:

```ailang
Function.Test {
    Input: param: LinkagePool.TestPool  // Must match pool name exactly
    Body: {
        value = param.field1
        ReturnValue(value)
    }
}
```

---

## Technical Details

### Compiler Implementation

The LinkagePool system is implemented across several compiler modules:

- **linkage_pool.py**: Core LinkagePool manager
  - Pool definitions and field tracking
  - Type tracking and validation
  - Allocation and initialization
  - Field access code generation

- **expression_compiler.py**: Expression handling
  - Field read access (ptr.field)
  - Member access resolution
  - Type propagation

- **memory_manager.py**: Assignment handling
  - Field write access (ptr.field = value)
  - Pointer type tracking
  - AllocateLinkage result handling

- **ast_pools.py**: AST node definitions
  - LinkagePool declaration nodes
  - Field access nodes

### Assembly Code Generation

Field reads generate efficient assembly:
```asm
; Load pointer from variable
MOV RAX, [RBP-offset]

; Null check
TEST RAX, RAX
JZ error_label

; Load field value
MOV RAX, [RAX+field_offset]
```

Field writes:
```asm
; Save value
PUSH RAX

; Load pointer
MOV RAX, [RBP-offset]

; Null check
TEST RAX, RAX
JZ error_label

; Store to field
POP RBX
MOV [RAX+field_offset], RBX
```

---

## Future Enhancements

Planned improvements to the LinkagePool system:

1. **Dynamic Deallocation**: Full FreeLinkage implementation
2. **Direction Enforcement**: Runtime checks for Input/Output access
3. **Nested Pools**: LinkagePools containing other LinkagePools
4. **Array Fields**: Support for array members within pools
5. **Serialization**: Built-in save/load to disk
6. **Network Sharing**: Inter-process LinkagePool sharing
7. **Garbage Collection**: Automatic memory management option

---

## Summary

LinkagePool provides a powerful, type-safe mechanism for structured data sharing in AI Lang. Key takeaways:

- ✓ Declare pools with field definitions
- ✓ Allocate with `AllocateLinkage()`
- ✓ Access fields with natural dot notation
- ✓ Pass as function parameters with full type safety
- ✓ Support for both integers and strings
- ✓ Automatic null checking and bounds validation

For more examples, see the test files:
- `test_linkage_phase1.ailang` - Type tracking
- `test_linkage_phase2.ailang` - Field reads
- `test_linkage_phase3.ailang` - Field writes
- `VICIOUS_LINKAGEPOOL.ailang` - Stress testing

---

**Copyright © 2025 Sean Collins, 2 Paws Machine and Engineering**  
**AI Lang Compiler - LinkagePool Feature Manual**