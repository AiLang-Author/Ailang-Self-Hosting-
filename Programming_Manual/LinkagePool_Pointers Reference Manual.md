# LinkagePool Reference Manual v3.0

## Overview

**LinkagePool** is a compiler primitive providing structured, typed memory blocks with named field access. It enables type-safe data sharing between functions with compile-time validation and efficient Arena-backed allocation.

**Core Philosophy:** Explicit types everywhere. The compiler never guesses—if you want type tracking through pointer fields, you declare it with `PointerTo=`.

### v3.0 Features

- **`@` operator** for field access (`ptr@field`)
- **`PointerTo=`** for type-tracked pointer fields
- **`Type=`** for embedded/nested pools
- **`Direction=`** for access control (Input/Output/InOut)
- **Full type propagation** through pointer chains
- **Arena-backed allocation** with real deallocation

---

## Quick Start

```ailang
LibraryImport.Arena

LinkagePool.Point {
    "x": Initialize=0
    "y": Initialize=100
}

SubRoutine.Main {
    Arena_Init()
    
    pt = AllocateLinkage(LinkagePool.Point)
    PrintNumber(pt@x)    // 0
    PrintNumber(pt@y)    // 100
    
    pt@x = 50
    PrintNumber(pt@x)    // 50
    
    FreeLinkage(pt, LinkagePool.Point)
    Exit(0)
}

RunTask(Main)
```

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Declaration Syntax](#declaration-syntax)
3. [Field Attributes](#field-attributes)
4. [The @ Operator](#the--operator)
5. [Allocation and Deallocation](#allocation-and-deallocation)
6. [Type Propagation with PointerTo](#type-propagation-with-pointerto)
7. [Nested Pools with Type](#nested-pools-with-type)
8. [Direction Enforcement](#direction-enforcement)
9. [Function Parameters](#function-parameters)
10. [Introspection Primitives](#introspection-primitives)
11. [Pool Operations](#pool-operations)
12. [Memory Model](#memory-model)
13. [Complete Examples](#complete-examples)
14. [Error Messages](#error-messages)
15. [Migration from v2.0](#migration-from-v20)

---

## Core Concepts

### What is a LinkagePool?

A **LinkagePool** is a compile-time defined memory layout with:

- **Named fields** — Access via `ptr@fieldname` using the `@` operator
- **Type tracking** — Compiler validates field access at compile time
- **Pointer type propagation** — `PointerTo=` enables chained access through pointer fields
- **Direction semantics** — Fields marked Input, Output, or InOut for parameter access control
- **Arena allocation** — Fast slab-based allocation with real deallocation
- **Null safety** — Automatic null pointer checks on access

### LinkagePool vs Other Constructs

| Construct | Purpose | Field Access | Methods | Instances |
|-----------|---------|--------------|---------|-----------|
| **FixedPool** | Global state | Named via `.` | No | Exactly 1 |
| **LinkagePool** | Structured data | Named via `@` | No | Many (heap) |
| **OOP Object** | Behavior + data | Dynamic | Yes | Many |
| **HashMap** | Dynamic keys | Dynamic | No | Many |

### Why @ Instead of Dot?

The dot operator (`.`) is overloaded in AILang:
- `FixedPool.Name.field` — Global pool access
- `LinkagePool.TypeName` — Type declarations  
- `Library.Module.Function` — Namespacing

Using `@` for pointer field access provides:
- **Unambiguous parsing** — No confusion with other dot uses
- **Grep-friendly** — `grep "@"` finds all pointer dereferences
- **Self-documenting** — `@` visually indicates "at this address"
- **Simple lexer/parser** — Single token, no complex splitting

---

## Declaration Syntax

### Basic Structure

```ailang
LinkagePool.TypeName {
    "field1": Initialize=0
    "field2": Initialize=100
    "field3": Initialize=""
    "field4": Initialize=0, Direction=Input
    "field5": Initialize=0, PointerTo=LinkagePool.Other
    "field6": Type=LinkagePool.Embedded
}
```

### Rules

- Field names must be in double quotes
- Each field is 8 bytes (integer, string pointer, or pool pointer)
- Attributes are comma-separated after the colon
- Pools must be declared before use (forward references not allowed)
- Pool names follow `LinkagePool.Name` convention

---

## Field Attributes

| Attribute | Values | Description |
|-----------|--------|-------------|
| `Initialize` | Integer or `""` | **Required.** Default value. `""` = string field |
| `Direction` | `Input`, `Output`, `InOut` | Access control for parameters (default: `InOut`) |
| `PointerTo` | `LinkagePool.X` | Field holds pointer to another pool (enables type tracking) |
| `Type` | `LinkagePool.X` | Embedded/nested pool (inline, not pointer) |

### Initialize Values

```ailang
LinkagePool.Example {
    "count": Initialize=0           // Integer, default 0
    "max": Initialize=9999          // Integer, default 9999
    "name": Initialize=""           // String, empty default
    "label": Initialize="default"   // String, with initial value
    "flags": Initialize=0xFF        // Integer, hex literal
}
```

### Field Type Detection

The compiler determines field type from the `Initialize` value:
- **Integer** — Any numeric literal (`0`, `100`, `0xFF`)
- **String** — Any string literal (`""`, `"default"`)

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
customer@balance = 500          // Direct assignment
customer@id = 12345             // Write integer
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

### Chained Access (with PointerTo)

When fields are declared with `PointerTo=`, the compiler tracks types through the chain:

```ailang
employee@department@name = "Engineering"
manager = employee@department@head
zip = customer@billing@zip
```

### Null Safety

All field access includes automatic null checks:

```ailang
ptr = 0              // Null pointer
value = ptr@x        // Returns 0, no crash
```

Generated assembly includes null check:
```asm
MOV RAX, [RBP-offset]   ; Load pointer
TEST RAX, RAX           ; Null check
JZ .null_handler        ; Skip if null
MOV RAX, [RAX+field]    ; Load field
```

---

## Allocation and Deallocation

### AllocateLinkage

Allocates a new instance from the Arena and initializes all fields to their `Initialize` values.

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

**⚠️ TYPE IS REQUIRED** — The compiler must know which slab to return memory to.

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

## Type Propagation with PointerTo

`PointerTo=` declares that a field holds a pointer to another LinkagePool. This is the key feature that enables the compiler to track types through pointer chains.

### The Problem Without PointerTo

```ailang
LinkagePool.List {
    "head": Initialize=0    // Just an integer to compiler
}

list = AllocateLinkage(LinkagePool.List)
head = list@head
head@value = 100    // ERROR: "head is not a LinkagePool pointer"
```

Without `PointerTo=`, the compiler sees `head` as just an integer field. It has no way to know it should be treated as a pointer to another pool.

### The Solution With PointerTo

```ailang
LinkagePool.Node {
    "value": Initialize=0
    "next": Initialize=0, PointerTo=LinkagePool.Node
}

LinkagePool.List {
    "head": Initialize=0, PointerTo=LinkagePool.Node
    "tail": Initialize=0, PointerTo=LinkagePool.Node
    "count": Initialize=0
}

list = AllocateLinkage(LinkagePool.List)
node = AllocateLinkage(LinkagePool.Node)
list@head = node

// Compiler knows the types at each step:
head = list@head        // head is LinkagePool.Node
head@value = 100        // Works! Compiler knows head is a Node

next = head@next        // next is LinkagePool.Node  
next@value = 200        // Works! Type propagates through chain
```

### Self-Referential Structures

`PointerTo=` can reference the same pool type, enabling linked structures:

```ailang
LinkagePool.Node {
    "value": Initialize=0
    "next": Initialize=0, PointerTo=LinkagePool.Node   // Points to same type
    "prev": Initialize=0, PointerTo=LinkagePool.Node   // Doubly-linked
}

LinkagePool.TreeNode {
    "value": Initialize=0
    "left": Initialize=0, PointerTo=LinkagePool.TreeNode
    "right": Initialize=0, PointerTo=LinkagePool.TreeNode
    "parent": Initialize=0, PointerTo=LinkagePool.TreeNode
}
```

### Memory Model with PointerTo

`PointerTo` fields store an 8-byte address, not the actual struct:

```
List (24 bytes)                 Node @ 0x7F00           Node @ 0x7F40
┌─────────────────┐             ┌─────────────────┐     ┌─────────────────┐
│ head: 0x7F00 ───┼────────────►│ value: 100      │     │ value: 200      │
├─────────────────┤             │ next: 0x7F40 ───┼────►│ next: 0         │
│ tail: 0x7F40 ───┼─────────────┼─────────────────┼─────┼─────────────────┘
├─────────────────┤             └─────────────────┘     
│ count: 2        │                                     
└─────────────────┘
```

---

## Nested Pools with Type

`Type=` embeds another pool's fields directly inline (not a pointer). The nested pool is allocated as part of the parent.

### Declaration

```ailang
LinkagePool.Address {
    "street": Initialize=""
    "city": Initialize=""
    "zip": Initialize=0
}

LinkagePool.Person {
    "name": Initialize=""
    "home": Type=LinkagePool.Address    // Embedded inline
    "work": Type=LinkagePool.Address    // Another embedded copy
}
```

### Memory Model with Type

```
Person (40 bytes)
┌─────────────────┐
│ name            │  8 bytes
├─────────────────┤
│ home.street     │  8 bytes  ┐
│ home.city       │  8 bytes  ├── Address embedded (24 bytes)
│ home.zip        │  8 bytes  ┘
├─────────────────┤
│ work.street     │  8 bytes  ┐
│ work.city       │  8 bytes  ├── Address embedded (24 bytes)
│ work.zip        │  8 bytes  ┘
└─────────────────┘
```

### Chained @ Access

```ailang
person = AllocateLinkage(LinkagePool.Person)
person@home@city = "Chicago"
person@home@zip = 60601
person@work@city = "Evanston"

PrintString(person@home@city)   // "Chicago"
```

**Single allocation:** One `AllocateLinkage` allocates the entire structure including nested pools.

### PointerTo vs Type Comparison

| Attribute | Storage | Memory | Use Case |
|-----------|---------|--------|----------|
| `PointerTo=` | 8 bytes (address only) | Separate allocation | Linked structures, shared references, optional data |
| `Type=` | Full struct size inline | Single allocation | Composition, always-present data, value semantics |

**Choose `PointerTo=` when:**
- Building linked data structures (lists, trees, graphs)
- Multiple objects might reference the same data
- The referenced data is optional (can be null/0)
- You need to swap or reassign references

**Choose `Type=` when:**
- The nested data is always present
- You want single-allocation simplicity
- The nested data belongs to exactly one parent
- You want value semantics (copy parent = copy nested)

---

## Direction Enforcement

Direction attributes control field access **in function parameters only**. They provide compile-time enforcement of read/write contracts.

### Direction Types

| Direction | In Function | Contract |
|-----------|-------------|----------|
| `Input` | Read-only | Caller provides data, callee reads |
| `Output` | Write-only | Callee provides data, caller reads after |
| `InOut` | Read-write | Both can read and write (default) |

### Declaration

```ailang
LinkagePool.CalculationRequest {
    "operand_a": Initialize=0, Direction=Input     // Caller sets
    "operand_b": Initialize=0, Direction=Input     // Caller sets
    "operation": Initialize=0, Direction=Input     // Caller sets
    "result": Initialize=0, Direction=Output       // Callee sets
    "error": Initialize=0, Direction=Output        // Callee sets
}
```

### Enforcement in Function Parameters

```ailang
Function.Calculate {
    Input: req: LinkagePool.CalculationRequest
    Body: {
        // Reading Input fields - OK
        a = req@operand_a          // ✓ OK
        b = req@operand_b          // ✓ OK
        
        // Writing Input fields - ERROR
        req@operand_a = 99         // ✗ ERROR: Cannot write to Input field
        
        // Writing Output fields - OK
        req@result = Add(a, b)     // ✓ OK
        req@error = 0              // ✓ OK
        
        // Reading Output fields - ERROR  
        x = req@result             // ✗ ERROR: Cannot read from Output field
        
        ReturnValue(1)
    }
}
```

### Local Allocations Have Full Access

Direction is **only enforced on parameters**. When you allocate locally, you own the instance and have full access:

```ailang
Function.LocalExample {
    Body: {
        req = AllocateLinkage(LinkagePool.CalculationRequest)
        
        // We own this instance - full access regardless of Direction
        req@operand_a = 100      // ✓ OK - we're the "caller"
        req@result = 0           // ✓ OK - we own it
        x = req@result           // ✓ OK - we own it
        
        Calculate(req)           // Now req is a parameter to Calculate
        
        // After call, we read the outputs
        result = req@result      // ✓ OK - we're the "caller"
    }
}
```

### Compile Errors

```
ERROR: Cannot write to Input field 'operand_a' in parameter 'req'
       Field 'operand_a' has Direction=Input (read-only)
       at line 15

ERROR: Cannot read from Output field 'result' in parameter 'req'
       Field 'result' has Direction=Output (write-only)
       at line 23
```

---

## Function Parameters

### Declaring LinkagePool Parameters

```ailang
Function.ProcessNode {
    Input: node: LinkagePool.Node
    Body: {
        value = node@value
        node@value = Add(value, 1)
        ReturnValue(value)
    }
}
```

### Multiple Parameters

```ailang
Function.TransferValue {
    Input: src: LinkagePool.Node
    Input: dest: LinkagePool.Node
    Input: amount: Integer
    Body: {
        src@balance = Subtract(src@balance, amount)
        dest@balance = Add(dest@balance, amount)
        ReturnValue(1)
    }
}
```

### Calling Functions with LinkagePool Arguments

```ailang
node = AllocateLinkage(LinkagePool.Node)
node@value = 42

result = ProcessNode(node)

PrintNumber(node@value)    // 43 (function modified it)
```

### Address Type for Generic Pointers

When a function accepts any LinkagePool type, use `Address`:

```ailang
Function.List_Append {
    Input: list: Address      // Could be any pool with head/tail
    Input: value: Integer
    Body: {
        // ...
    }
}
```

---

## Introspection Primitives

Compile-time constants for pool metadata. **Zero runtime cost** — these compile to immediate values.

### PoolSize

Returns total size in bytes.

```ailang
size = PoolSize(LinkagePool.Node)
// Compiles to: MOV RAX, 16  (immediate value)
```

### PoolFieldCount

Returns number of fields.

```ailang
count = PoolFieldCount(LinkagePool.Node)
// Compiles to: MOV RAX, 2  (immediate value)
```

### PoolFieldOffset

Returns byte offset of a specific field.

```ailang
offset = PoolFieldOffset(LinkagePool.Node, "next")
// Compiles to: MOV RAX, 8  (immediate value)
```

### Use Cases

```ailang
// Runtime size checks
IfCondition GreaterThan(PoolSize(LinkagePool.BigStruct), 1024) ThenBlock: {
    PrintMessage("Warning: large allocation\n")
}

// Manual memory operations (advanced)
base = customer
balance_ptr = Add(base, PoolFieldOffset(LinkagePool.Customer, "balance"))
```

---

## Pool Operations

All operations require explicit type specification. **No inference.**

### CopyLinkage

Allocate a new pool and copy all fields (shallow copy).

```ailang
dest = CopyLinkage(src, LinkagePool.CustomerRecord)
```

Creates a new allocation. Pointer fields copy the address, not the pointed-to data.

### CopyLinkageInto

Copy fields into an existing allocation.

```ailang
CopyLinkageInto(dest, src, LinkagePool.CustomerRecord)
```

Does not allocate — `dest` must already be allocated.

### ResetLinkage

Restore all fields to their `Initialize` values.

```ailang
ResetLinkage(ptr, LinkagePool.CustomerRecord)
```

Useful for object pooling / reuse patterns.

### CompareLinkage

Byte-level comparison of two pools.

```ailang
equal = CompareLinkage(a, b, LinkagePool.CustomerRecord)
// Returns 1 if identical, 0 if different
```

Compares raw bytes — pointer fields are compared as addresses, not dereferenced.

---

## Memory Model

### Field Layout

Fields are stored sequentially, 8 bytes each:

```
Offset  | Field      | Size
--------|------------|------
0       | field1     | 8 bytes
8       | field2     | 8 bytes
16      | field3     | 8 bytes
24      | field4     | 8 bytes
...     | ...        | ...
```

### All Fields Are 8 Bytes

Regardless of logical type:
- **Integer** — 64-bit signed, 8 bytes
- **String** — Pointer to string data, 8 bytes
- **PointerTo** — Address of another pool, 8 bytes
- **Type** — Expands to embedded pool's full size

### Pointer Semantics

Assignment copies the pointer, not the data:

```ailang
ptr1 = AllocateLinkage(LinkagePool.Point)
ptr2 = ptr1   // Both point to same memory!

ptr2@x = 100
PrintNumber(ptr1@x)  // Prints 100
```

### Nested Pool Layout (Type=)

```ailang
LinkagePool.Inner {
    "a": Initialize=0
    "b": Initialize=0
}

LinkagePool.Outer {
    "x": Initialize=0
    "inner": Type=LinkagePool.Inner
    "y": Initialize=0
}
```

Layout of `Outer`:
```
Offset 0:   x       (8 bytes)
Offset 8:   inner.a (8 bytes)  ┐ Inner embedded
Offset 16:  inner.b (8 bytes)  ┘
Offset 24:  y       (8 bytes)
Total: 32 bytes
```

---

## Complete Examples

### Example 1: Linked List with Type Tracking

```ailang
LibraryImport.Arena

LinkagePool.Node {
    "value": Initialize=0
    "next": Initialize=0, PointerTo=LinkagePool.Node
}

LinkagePool.List {
    "head": Initialize=0, PointerTo=LinkagePool.Node
    "tail": Initialize=0, PointerTo=LinkagePool.Node
    "count": Initialize=0
}

Function.List_Append {
    Input: list: Address
    Input: value: Integer
    Body: {
        node = AllocateLinkage(LinkagePool.Node)
        node@value = value
        node@next = 0
        
        IfCondition EqualTo(list@head, 0) ThenBlock: {
            list@head = node
            list@tail = node
        } ElseBlock: {
            tail = list@tail
            tail@next = node      // Type tracked! Compiler knows tail is Node
            list@tail = node
        }
        
        list@count = Add(list@count, 1)
        ReturnValue(node)
    }
}

Function.List_Print {
    Input: list: Address
    Body: {
        PrintMessage("[")
        current = list@head       // Compiler knows: current is Node
        first = 1
        
        WhileLoop NotEqual(current, 0) {
            IfCondition EqualTo(first, 0) ThenBlock: {
                PrintMessage(", ")
            }
            PrintNumber(current@value)    // Valid! current is Node
            first = 0
            current = current@next        // Type propagates through chain
        }
        
        PrintMessage("]\n")
        ReturnValue(0)
    }
}
```

### Example 2: Binary Tree

```ailang
LinkagePool.TreeNode {
    "value": Initialize=0
    "left": Initialize=0, PointerTo=LinkagePool.TreeNode
    "right": Initialize=0, PointerTo=LinkagePool.TreeNode
}

Function.Tree_Insert {
    Input: root: Address
    Input: value: Integer
    Output: Address
    Body: {
        IfCondition EqualTo(root, 0) ThenBlock: {
            node = AllocateLinkage(LinkagePool.TreeNode)
            node@value = value
            node@left = 0
            node@right = 0
            ReturnValue(node)
        }
        
        IfCondition LessThan(value, root@value) ThenBlock: {
            root@left = Tree_Insert(root@left, value)
        } ElseBlock: {
            root@right = Tree_Insert(root@right, value)
        }
        
        ReturnValue(root)
    }
}

Function.Tree_InOrder {
    Input: node: Address
    Body: {
        IfCondition EqualTo(node, 0) ThenBlock: {
            ReturnValue(0)
        }
        
        Tree_InOrder(node@left)
        PrintNumber(node@value)
        PrintMessage(" ")
        Tree_InOrder(node@right)
        ReturnValue(0)
    }
}
```

### Example 3: Request/Response with Direction

```ailang
LinkagePool.CalcRequest {
    "a": Initialize=0, Direction=Input
    "b": Initialize=0, Direction=Input
    "op": Initialize=0, Direction=Input
    "result": Initialize=0, Direction=Output
    "error": Initialize=0, Direction=Output
}

Function.Calculate {
    Input: req: LinkagePool.CalcRequest
    Body: {
        a = req@a
        b = req@b
        op = req@op
        
        IfCondition EqualTo(op, 1) ThenBlock: {
            req@result = Add(a, b)
            req@error = 0
        }
        IfCondition EqualTo(op, 2) ThenBlock: {
            req@result = Subtract(a, b)
            req@error = 0
        }
        IfCondition EqualTo(op, 3) ThenBlock: {
            IfCondition EqualTo(b, 0) ThenBlock: {
                req@error = 1    // Division by zero
            } ElseBlock: {
                req@result = Divide(a, b)
                req@error = 0
            }
        }
        
        ReturnValue(req@error)
    }
}

SubRoutine.Main {
    Arena_Init()
    
    req = AllocateLinkage(LinkagePool.CalcRequest)
    req@a = 100
    req@b = 42
    req@op = 1
    
    Calculate(req)
    
    PrintMessage("Result: ")
    PrintNumber(req@result)    // 142
    PrintMessage("\n")
    
    FreeLinkage(req, LinkagePool.CalcRequest)
    Exit(0)
}
```

### Example 4: Nested Pools (Embedded)

```ailang
LinkagePool.Name {
    "first": Initialize=""
    "last": Initialize=""
}

LinkagePool.Address {
    "street": Initialize=""
    "city": Initialize=""
    "zip": Initialize=0
}

LinkagePool.Employee {
    "id": Initialize=0
    "name": Type=LinkagePool.Name        // Embedded
    "home": Type=LinkagePool.Address     // Embedded
    "salary": Initialize=0
}

SubRoutine.Main {
    Arena_Init()
    
    emp = AllocateLinkage(LinkagePool.Employee)
    emp@id = 1001
    emp@name@first = "John"
    emp@name@last = "Smith"
    emp@home@city = "Chicago"
    emp@home@zip = 60601
    emp@salary = 75000
    
    PrintMessage("Employee: ")
    PrintString(emp@name@first)
    PrintMessage(" ")
    PrintString(emp@name@last)
    PrintMessage(" from ")
    PrintString(emp@home@city)
    PrintMessage("\n")
    
    FreeLinkage(emp, LinkagePool.Employee)
    Exit(0)
}
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

ERROR: Cannot read from Output field 'result' in parameter 'req'
       Field 'result' has Direction=Output (write-only)
       at line 23
```

### Allocation Errors

```
ERROR: FreeLinkage requires pool type
       Usage: FreeLinkage(ptr, LinkagePool.TypeName)
       at line 42
```

---

## Migration from v2.0

### Breaking Change: @ Replaces Dot

**v2.0 (old):**
```ailang
ptr.field_name
ptr.nested.field
```

**v3.0 (new):**
```ailang
ptr@field_name
ptr@nested@field
```

### New Feature: PointerTo

v3.0 introduces `PointerTo=` for type-tracked pointer fields. Without it, the compiler treats pointer fields as plain integers.

**v2.0 style (still works but no type tracking):**
```ailang
LinkagePool.List {
    "head": Initialize=0    // Compiler sees as integer
}
```

**v3.0 style (with type tracking):**
```ailang
LinkagePool.List {
    "head": Initialize=0, PointerTo=LinkagePool.Node
}
```

### Why the @ Change?

The dot operator was ambiguous:
- `FixedPool.Name.field` — Global pool
- `ptr.field` — Pointer dereference (v2.0)
- `Library.Module` — Import path

The `@` operator is unambiguous and dedicated to pointer field access.

---

## Quick Reference

### Declaration

```ailang
LinkagePool.TypeName {
    "field": Initialize=0
    "field": Initialize=""
    "field": Initialize=0, Direction=Input
    "field": Initialize=0, Direction=Output
    "field": Initialize=0, PointerTo=LinkagePool.Other
    "field": Type=LinkagePool.Embedded
}
```

### Allocation

```ailang
ptr = AllocateLinkage(LinkagePool.Type)
FreeLinkage(ptr, LinkagePool.Type)
```

### Field Access

```ailang
value = ptr@field              // Read
ptr@field = value              // Write
value = ptr@nested@field       // Chained read (PointerTo or Type)
ptr@nested@field = value       // Chained write
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

---

**LinkagePool Reference Manual v3.0**  
**AILang Self-Hosting Compiler**  
**Copyright © 2025 Sean Collins, 2 Paws Machine and Engineering**