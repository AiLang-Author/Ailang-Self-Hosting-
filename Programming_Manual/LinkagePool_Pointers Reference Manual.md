# LinkagePool Reference Manual v3.0

## Overview

**LinkagePool** is a compiler primitive providing structured, typed memory blocks with named field access. It enables type-safe data sharing between functions with compile-time validation and efficient Arena-backed allocation.

**Core Philosophy:** Explicit types everywhere. The compiler never guesses - if it can't verify the type from source code, it errors and tells you to fix it.

**v3.0 Change:** Introduces the `@` operator for pointer field access, replacing ambiguous dot notation.

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [The @ Operator](#the--operator)
3. [Declaration Syntax](#declaration-syntax)
4. [Allocation and Deallocation](#allocation-and-deallocation)
5. [Field Access](#field-access)
6. [Direction Enforcement](#direction-enforcement)
7. [Function Parameters](#function-parameters)
8. [Introspection Primitives](#introspection-primitives)
9. [Pool Operations](#pool-operations)
10. [Nested Pools](#nested-pools)
11. [Memory Model](#memory-model)
12. [Complete Examples](#complete-examples)
13. [Error Messages](#error-messages)
14. [Migration from v2.0](#migration-from-v20)

---

## Core Concepts

### What is a LinkagePool?

A **LinkagePool** is a compile-time defined memory layout with:

- **Named fields** - Access via `ptr@fieldname` using the `@` operator
- **Type tracking** - Compiler validates field access at compile time
- **Direction semantics** - Fields marked Input, Output, or InOut
- **Arena allocation** - Fast slab-based allocation with real deallocation
- **Null safety** - Automatic null pointer checks on access

### LinkagePool vs Other Constructs

| Construct | Purpose | Fields | Methods | Instances |
|-----------|---------|--------|---------|-----------|
| **FixedPool** | Global state | Named via `.` | No | Exactly 1 |
| **LinkagePool** | Structured data | Named via `@` | No | Many |
| **OOP Object** | Behavior + data | Dynamic | Yes | Many |
| **HashMap** | Dynamic keys | Dynamic | No | Many |

### Why @ Instead of Dot?

The dot operator (`.`) is overloaded in AILang:
- `FixedPool.Name.field` - Global pool access
- `LinkagePool.TypeName` - Type declarations
- `Library.Module.Function` - Namespacing

Using `@` for pointer field access provides:
- **Unambiguous parsing** - No confusion with other dot uses
- **Grep-friendly** - `grep "@"` finds all pointer dereferences
- **Self-documenting** - `@` visually indicates "at this address"
- **Simple lexer/parser** - Single token, no complex splitting

---

## The @ Operator

The `@` operator is the **pointer field access operator**. It dereferences a LinkagePool pointer and accesses a named field.

### Syntax

```ailang
pointer_variable@field_name
```

### Reading Fields

```ailang
customer = AllocateLinkage(LinkagePool.CustomerRecord)
value = customer@balance        // Read balance field
id = customer@id                // Read id field
```

### Writing Fields

```ailang
customer@balance = 500          // Write to balance
customer@id = 12345             // Write to id
customer@name = "John Doe"      // Write string
```

### In Expressions

```ailang
total = Add(account1@balance, account2@balance)
average = Divide(Add(point@x, point@y), 2)

IfCondition GreaterThan(customer@balance, 0) ThenBlock: {
    PrintMessage("Positive balance\n")
}
```

### Chained Access (Nested Pools)

For nested pools, chain the `@` operator:

```ailang
employee@address@city = "Chicago"
zip = employee@address@zip
```

---

## Declaration Syntax

### Basic Declaration

```ailang
LinkagePool.TypeName {
    "field1": Initialize=0
    "field2": Initialize=0
    "field3": Initialize=""
}
```

### Field Attributes

| Attribute | Values | Description |
|-----------|--------|-------------|
| `Initialize` | Integer or `""` | Default value. `""` = string field |
| `Direction` | `Input`, `Output`, `InOut` | Access control (default: `InOut`) |
| `Type` | `LinkagePool.X` | Nested pool (embedded inline) |

### Complete Example

```ailang
LinkagePool.CustomerRecord {
    // Input fields - read-only in receiving functions
    "id": Initialize=0, Direction=Input
    "name": Initialize="", Direction=Input
    
    // InOut fields - full access (default)
    "balance": Initialize=0
    "credit_limit": Initialize=1000
    
    // Output fields - write-only in receiving functions
    "status_code": Initialize=0, Direction=Output
    "error_msg": Initialize="", Direction=Output
}
```

### Field Types

**Integer Fields** (default):
```ailang
"count": Initialize=0        // 64-bit signed integer
"max_value": Initialize=9999 // With default value
```

**String Fields** (detected by string initializer):
```ailang
"name": Initialize=""        // Empty string pointer
"label": Initialize="default" // String with default
```

---

## Allocation and Deallocation

### AllocateLinkage

Allocates a new instance from the Arena and initializes all fields.

```ailang
ptr = AllocateLinkage(LinkagePool.TypeName)
```

**Behavior:**
1. Selects optimal Arena slab based on pool size
2. Allocates memory block
3. Initializes all fields to their `Initialize` values
4. Returns pointer in RAX
5. Compiler tracks that `ptr` holds a `LinkagePool.TypeName`

**Example:**
```ailang
customer = AllocateLinkage(LinkagePool.CustomerRecord)
customer@id = 12345
customer@name = "John Doe"
customer@balance = 1000
```

### FreeLinkage

Returns memory to the Arena's free list for reuse.

```ailang
FreeLinkage(ptr, LinkagePool.TypeName)
```

**⚠️ TYPE IS REQUIRED** - The compiler must know which slab to return memory to.

**Example:**
```ailang
customer = AllocateLinkage(LinkagePool.CustomerRecord)
// ... use customer ...
FreeLinkage(customer, LinkagePool.CustomerRecord)
```

**Error if type omitted:**
```
ERROR: FreeLinkage requires pool type
       Usage: FreeLinkage(ptr, LinkagePool.TypeName)
       at line 42
```

---

## Field Access

### Reading Fields

```ailang
ptr = AllocateLinkage(LinkagePool.Point)
x_value = ptr@x              // Read field
y_value = ptr@y
total = Add(ptr@x, ptr@y)    // Use in expressions
```

### Writing Fields

```ailang
ptr@x = 100                  // Direct assignment
ptr@y = Add(ptr@x, 50)       // Expression assignment
ptr@name = "Updated"         // String assignment
```

### Null Safety

All field access includes automatic null checks:

```ailang
ptr = AllocateLinkage(LinkagePool.Point)
value = ptr@x   // Safe - null check generated

ptr2 = 0        // Null pointer
value = ptr2@x  // Returns 0, no crash
```

Generated assembly includes:
```asm
MOV RAX, [RBP-offset]   ; Load pointer
TEST RAX, RAX           ; Null check
JZ .null_handler        ; Skip if null
MOV RAX, [RAX+field]    ; Load field
```

---

## Direction Enforcement

Direction attributes are **enforced at compile time** for function parameters.

### Direction Types

| Direction | In Function | Meaning |
|-----------|-------------|---------|
| `Input` | Read-only | Caller provides, callee reads |
| `Output` | Write-only | Callee provides, caller reads |
| `InOut` | Read-write | Both can read and write (default) |

### Enforcement Rules

**Parameters:** Direction is enforced.
```ailang
Function.ProcessRecord {
    Input: rec: LinkagePool.DataRecord
    Body: {
        // Can only READ input fields
        x = rec@input_field          // ✓ OK - reading Input
        rec@input_field = 99         // ✗ ERROR - writing Input
        
        // Can only WRITE output fields
        rec@output_field = 1         // ✓ OK - writing Output
        y = rec@output_field         // ✗ ERROR - reading Output
        
        // Full access to InOut fields
        z = rec@inout_field          // ✓ OK - reading InOut
        rec@inout_field = z          // ✓ OK - writing InOut
    }
}
```

**Local Allocations:** Full access regardless of Direction.
```ailang
Function.LocalExample {
    Body: {
        ptr = AllocateLinkage(LinkagePool.DataRecord)
        ptr@input_field = 100    // ✓ OK - we own this instance
        x = ptr@output_field     // ✓ OK - we own this instance
    }
}
```

### Compile Errors

```
ERROR: Cannot write to Input field 'customer_id' in parameter 'rec'
       Field 'customer_id' has Direction=Input (read-only)
       at line 15

ERROR: Cannot read from Output field 'status_code' in parameter 'rec'  
       Field 'status_code' has Direction=Output (write-only)
       at line 23
```

---

## Function Parameters

### Declaring LinkagePool Parameters

```ailang
Function.ProcessCustomer {
    Input: customer: LinkagePool.CustomerRecord
    
    Body: {
        // Access fields with @
        id = customer@id
        PrintNumber(customer@balance)
        
        // Write to output fields
        customer@status_code = 0
        
        ReturnValue(1)
    }
}
```

### Multiple Parameters

```ailang
Function.TransferFunds {
    Input: source: LinkagePool.Account
    Input: dest: LinkagePool.Account
    Input: amount: Integer
    
    Body: {
        source@balance = Subtract(source@balance, amount)
        dest@balance = Add(dest@balance, amount)
        ReturnValue(1)
    }
}
```

### Calling Functions

```ailang
cust = AllocateLinkage(LinkagePool.CustomerRecord)
cust@id = 12345
cust@balance = 1000

result = ProcessCustomer(cust)

// Read output fields after call
status = cust@status_code
```

---

## Introspection Primitives

Compile-time constants for pool metadata. **Zero runtime cost.**

### PoolSize

Returns total size in bytes.

```ailang
size = PoolSize(LinkagePool.CustomerRecord)
// Compiles to: MOV RAX, 48  (immediate value)
```

### PoolFieldCount

Returns number of fields.

```ailang
count = PoolFieldCount(LinkagePool.CustomerRecord)
// Compiles to: MOV RAX, 6  (immediate value)
```

### PoolFieldOffset

Returns byte offset of a specific field.

```ailang
offset = PoolFieldOffset(LinkagePool.CustomerRecord, "balance")
// Compiles to: MOV RAX, 16  (immediate value)
```

---

## Pool Operations

All operations require explicit type. **No inference.**

### CopyLinkage

Allocate new pool and copy all fields.

```ailang
dest = CopyLinkage(src, LinkagePool.CustomerRecord)
```

### CopyLinkageInto

Copy fields into existing allocation.

```ailang
CopyLinkageInto(dest, src, LinkagePool.CustomerRecord)
```

### ResetLinkage

Restore all fields to their Initialize values.

```ailang
ResetLinkage(ptr, LinkagePool.CustomerRecord)
```

### CompareLinkage

Byte-level comparison of two pools.

```ailang
equal = CompareLinkage(a, b, LinkagePool.CustomerRecord)
// Returns 1 if identical, 0 if different
```

---

## Nested Pools

Embed one pool type inside another.

### Declaration

```ailang
LinkagePool.Address {
    "street": Initialize=""
    "city": Initialize=""
    "zip": Initialize=0
}

LinkagePool.Customer {
    "id": Initialize=0
    "name": Initialize=""
    "billing": Type=LinkagePool.Address
    "shipping": Type=LinkagePool.Address
}
```

### Chained @ Access

```ailang
cust = AllocateLinkage(LinkagePool.Customer)
cust@billing@city = "Chicago"
cust@billing@zip = 60601
cust@shipping@city = "New York"

PrintString(cust@billing@city)   // "Chicago"
```

**Single allocation:** Nested pools are embedded inline.
**Chained @:** Each `@` dereferences one level.

---

## Memory Model

### Field Layout

Fields are sequential, 8 bytes each:

```
Offset  | Field      | Size
--------|------------|------
0       | field1     | 8 bytes
8       | field2     | 8 bytes
16      | field3     | 8 bytes
...
```

### Pointer Semantics

```ailang
ptr1 = AllocateLinkage(LinkagePool.Point)
ptr2 = ptr1   // Both point to same memory

ptr2@x = 100
PrintNumber(ptr1@x)  // Prints 100
```

---

## Complete Examples

### Example 1: Basic Usage

```ailang
LinkagePool.Point {
    "x": Initialize=0
    "y": Initialize=0
}

point = AllocateLinkage(LinkagePool.Point)
point@x = 10
point@y = 20

PrintMessage("Point: (")
PrintNumber(point@x)
PrintMessage(", ")
PrintNumber(point@y)
PrintMessage(")\n")

FreeLinkage(point, LinkagePool.Point)
```

### Example 2: Direction-Controlled API

```ailang
LinkagePool.CalculationRequest {
    "operand_a": Initialize=0, Direction=Input
    "operand_b": Initialize=0, Direction=Input
    "operation": Initialize=0, Direction=Input
    "result": Initialize=0, Direction=Output
    "error": Initialize=0, Direction=Output
}

Function.Calculate {
    Input: req: LinkagePool.CalculationRequest
    Body: {
        a = req@operand_a
        b = req@operand_b
        op = req@operation
        
        IfCondition EqualTo(op, 1) ThenBlock: {
            req@result = Add(a, b)
            req@error = 0
        }
        IfCondition EqualTo(op, 2) ThenBlock: {
            req@result = Subtract(a, b)
            req@error = 0
        }
        
        ReturnValue(1)
    }
}

// Usage
req = AllocateLinkage(LinkagePool.CalculationRequest)
req@operand_a = 100
req@operand_b = 42
req@operation = 1

Calculate(req)

PrintMessage("Result: ")
PrintNumber(req@result)  // 142
```

### Example 3: Linked List

```ailang
LinkagePool.ListNode {
    "value": Initialize=0
    "next": Initialize=0
}

// Build list
node1 = AllocateLinkage(LinkagePool.ListNode)
node2 = AllocateLinkage(LinkagePool.ListNode)
node3 = AllocateLinkage(LinkagePool.ListNode)

node1@value = 100
node1@next = node2

node2@value = 200
node2@next = node3

node3@value = 300
node3@next = 0

// Traverse
current = node1
WhileLoop NotEqual(current, 0) {
    PrintNumber(current@value)
    PrintMessage(" -> ")
    current = current@next
}
PrintMessage("NULL\n")

// Cleanup
FreeLinkage(node1, LinkagePool.ListNode)
FreeLinkage(node2, LinkagePool.ListNode)
FreeLinkage(node3, LinkagePool.ListNode)
```

### Example 4: Nested Pools

```ailang
LinkagePool.Name {
    "first": Initialize=""
    "last": Initialize=""
}

LinkagePool.Employee {
    "id": Initialize=0
    "name": Type=LinkagePool.Name
    "salary": Initialize=0
}

emp = AllocateLinkage(LinkagePool.Employee)
emp@id = 1001
emp@name@first = "John"
emp@name@last = "Smith"
emp@salary = 75000

PrintMessage("Employee: ")
PrintString(emp@name@first)
PrintMessage(" ")
PrintString(emp@name@last)
PrintMessage("\n")
```

---

## Error Messages

### Type Errors

```
ERROR: Variable 'x' is not a LinkagePool pointer
       Cannot use @ operator on non-pointer type
       at line 15

ERROR: Unknown LinkagePool type 'LinkagePool.Foo'
       Defined pools: CustomerRecord, Account, Transaction
       at line 20
```

### Field Errors

```
ERROR: Field 'unknown_field' not in LinkagePool.CustomerRecord
       Available fields: id, name, balance, status_code
       at line 31
```

### Direction Errors

```
ERROR: Cannot write to Input field 'customer_id' in parameter 'rec'
       Field 'customer_id' has Direction=Input (read-only)
       at line 15
```

---

## Migration from v2.0

### Breaking Change: @ Replaces Dot for Field Access

**v2.0:**
```ailang
ptr.field_name
ptr.nested.field
```

**v3.0:**
```ailang
ptr@field_name
ptr@nested@field
```

### Search and Replace

```bash
# Find all old-style access patterns
grep -rn "\.[a-z_]*\s*=" --include="*.ailang" .

# Manual review required - not all dots are field access
```

### Why the Change?

The dot operator was ambiguous:
- `FixedPool.Name.field` - Global pool
- `ptr.field` - Pointer dereference
- `Library.Module` - Import path

The `@` operator is unambiguous and dedicated to pointer field access.

---

## Quick Reference

### Allocation
```ailang
ptr = AllocateLinkage(LinkagePool.Type)
FreeLinkage(ptr, LinkagePool.Type)
```

### Field Access
```ailang
value = ptr@field              // Read
ptr@field = value              // Write
value = ptr@nested@field       // Nested read
ptr@nested@field = value       // Nested write
```

### Introspection
```ailang
size = PoolSize(LinkagePool.Type)
count = PoolFieldCount(LinkagePool.Type)
offset = PoolFieldOffset(LinkagePool.Type, "field")
```

### Operations
```ailang
dest = CopyLinkage(src, LinkagePool.Type)
CopyLinkageInto(dest, src, LinkagePool.Type)
ResetLinkage(ptr, LinkagePool.Type)
equal = CompareLinkage(a, b, LinkagePool.Type)
```

### Declaration
```ailang
LinkagePool.TypeName {
    "field": Initialize=0
    "field": Initialize=""
    "field": Initialize=0, Direction=Input
    "field": Initialize=0, Direction=Output
    "field": Type=LinkagePool.Other
}
```

---

**Copyright © 2025 Sean Collins, 2 Paws Machine and Engineering**
**AILang Compiler - LinkagePool Reference Manual v3.0**