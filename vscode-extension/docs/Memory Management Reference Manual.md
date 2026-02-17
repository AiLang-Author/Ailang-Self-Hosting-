# Memory Management Reference Manual

## Overview

AI Lang provides a sophisticated memory management system designed for high-performance native compilation. The system combines stack allocation, heap management, and specialized pool types to offer both safety and efficiency without garbage collection overhead.

**Key Features:**
- Direct memory control with automatic allocation
- Multiple pool types for different use cases
- Type-safe LinkagePool system for structured data
- Zero-overhead access patterns
- Explicit allocation and deallocation

---

## Table of Contents

1. [Memory Architecture](#memory-architecture)
2. [Pool Types](#pool-types)
3. [Variables and Stack Allocation](#variables-and-stack-allocation)
4. [Heap Allocation](#heap-allocation)
5. [LinkagePool System](#linkagepool-system)
6. [Memory Access Patterns](#memory-access-patterns)
7. [Best Practices](#best-practices)
8. [Performance Considerations](#performance-considerations)
9. [Common Patterns](#common-patterns)
10. [Troubleshooting](#troubleshooting)

---

## Memory Architecture

### Register Usage

AI Lang uses a well-defined register allocation strategy:

```
RAX - Return values, temporary computations
RBX - General purpose, preserved across calls
RCX - Loop counters, temporary values
RDX - Secondary computations
RSI - String operations, source pointers
RDI - String operations, destination pointers
RBP - Stack frame base pointer
RSP - Stack pointer
R8-R9 - Function parameters (7th and 8th)
R10-R11 - Temporary values
R12-R13 - Preserved temporaries
R14 - Reserved for future use
R15 - Pool table base pointer (FixedPool access)
```

**Critical:** R15 is reserved for the pool table. Never modify R15 in user code.

### Memory Regions

```
┌─────────────────────────────────┐ High addresses
│         Stack                    │ ← RSP, RBP
│    (local variables, frames)     │
├─────────────────────────────────┤
│         Heap                     │
│    (DynamicPool, Allocate)       │
├─────────────────────────────────┤
│      Pool Table                  │ ← R15
│    (FixedPool variables)         │
├─────────────────────────────────┤
│      Data Section                │
│  (strings, constants, LinkagePools)│
├─────────────────────────────────┤
│      Code Section                │
│    (compiled machine code)       │
└─────────────────────────────────┘ Low addresses
```

---

## Pool Types

AI Lang provides four specialized pool types for different memory management strategies.

### FixedPool

**Purpose:** Static, globally accessible variables with O(1) access time.

**Characteristics:**
- Allocated once at program startup via mmap
- Stored in R15-relative addressing
- Page-aligned (4KB minimum)
- Zero-initialized automatically
- Maximum 131,072 variables (1MB limit)

**Declaration:**
```ailang
FixedPool.Config {
    "max_connections": Initialize=100
    "timeout": Initialize=30
    "buffer_size": Initialize=4096
    "enabled": Initialize=1
}
```

**Access:**
```ailang
// Reading
current_timeout = Config.timeout

// Writing
Config.timeout = 60

// The compiler generates:
// MOV RAX, [R15 + offset]  // Read
// MOV [R15 + offset], RAX  // Write
```

**Memory Layout:**
```
R15 → [var_0: 8 bytes][var_1: 8 bytes][var_2: 8 bytes]...
```

Each variable occupies exactly 8 bytes, addressed as `[R15 + index * 8]`.

**Use Cases:**
- Configuration values
- Global state
- Counters and statistics
- Flags and settings

### DynamicPool

**Purpose:** Heap-allocated, growable collections with dynamic sizing.

**Characteristics:**
- Allocated via mmap on first use
- Can grow beyond initial capacity
- Stored on heap with pointer on stack
- Includes header (16 bytes: capacity + size)

**Declaration:**
```ailang
DynamicPool.Cache {
    "entries": Initialize=0
    "hits": Initialize=0
    "misses": Initialize=0
}
```

**Memory Layout:**
```
Stack: [pointer to heap] (8 bytes)
           ↓
Heap:  [capacity: 8][size: 8][entries: 8][hits: 8][misses: 8]
       ←─ header ─→  ←───────── data ──────────→
```

**Access Pattern:**
```ailang
Cache.entries = 100
hits = Cache.hits

// The compiler generates:
// 1. Load heap pointer from stack: MOV RAX, [RBP-offset]
// 2. Access member: MOV RBX, [RAX + member_offset]
```

**Use Cases:**
- Growing data structures
- Dynamic collections
- Cache systems
- Temporary working sets

### TemporalPool

**Purpose:** Scoped allocations with automatic lifetime management.

**Characteristics:**
- Lifetime tied to scope (function/block)
- Automatic deallocation on scope exit
- Fast allocation (no fragmentation concerns)
- Ideal for temporary computations

**Declaration:**
```ailang
TemporalPool.Workspace {
    "temp_buffer": Initialize=0
    "scratch_space": Initialize=0
}
```

**Lifetime:**
```ailang
Function.ProcessData {
    Body: {
        // TemporalPool allocated here
        Workspace.temp_buffer = Allocate(1024)
        
        // Use the buffer
        ProcessWithBuffer(Workspace.temp_buffer)
        
        // Automatically freed when function returns
    }
}
```

**Use Cases:**
- Function-local temporary storage
- Intermediate computation buffers
- Short-lived data structures

### LinkagePool

**Purpose:** Structured, type-safe data blocks for inter-function communication.

**Characteristics:**
- Defined structure with named fields
- Type tracking by compiler
- Field-level access with dot notation
- Allocated via AllocateLinkage()
- Supports both integers and strings

**Declaration:**
```ailang
LinkagePool.Person {
    "name": Initialize=""
    "age": Initialize=0
    "id": Initialize=0
    "active": Initialize=1
}
```

**Usage:**
```ailang
// Allocate
person = AllocateLinkage(LinkagePool.Person)

// Access with dot notation
person.name = "Alice"
person.age = 30
person.id = 12345
person.active = 1

// Read fields
current_age = person.age
```

**Memory Layout:**
```
[name_ptr: 8][age: 8][id: 8][active: 8]
```

See the **LinkagePool Reference Manual** for complete details.

---

## Variables and Stack Allocation

### Automatic Stack Variables

Regular variables are allocated on the stack automatically:

```ailang
x = 10        // Stack allocation at [RBP-8]
y = 20        // Stack allocation at [RBP-16]
z = Add(x, y) // Stack allocation at [RBP-24]
```

**Stack Frame:**
```
RBP → [saved RBP]
      [return address]
      [x: 8 bytes]      ← RBP-8
      [y: 8 bytes]      ← RBP-16
      [z: 8 bytes]      ← RBP-24
RSP → [top of stack]
```

### Variable Scope

Variables have lexical scoping:

```ailang
x = 10  // Outer scope

IfCondition True ThenBlock: {
    y = 20  // Inner scope
    z = Add(x, y)  // Can access outer x
}

// y is no longer accessible here
```

---

## Heap Allocation

### Allocate() Function

Allocate memory dynamically on the heap:

```ailang
// Allocate 1024 bytes
buffer = Allocate(1024)

// Use the buffer
StoreValue(buffer, 42)
value = Dereference(buffer)

// Free when done
Deallocate(buffer, 1024)
```

**Compiled to:**
```asm
; Allocate
MOV RAX, 9              ; sys_mmap
MOV RDI, 0              ; addr = NULL
MOV RSI, 1024           ; length
MOV RDX, 3              ; PROT_READ | PROT_WRITE
MOV R10, 0x22           ; MAP_PRIVATE | MAP_ANONYMOUS
MOV R8, -1              ; fd = -1
MOV R9, 0               ; offset = 0
SYSCALL
```

### Memory Operations

**StoreValue** - Write to memory:
```ailang
ptr = Allocate(64)
StoreValue(ptr, 100)           // Store at base
StoreValue(Add(ptr, 8), 200)   // Store at offset 8
```

**Dereference** - Read from memory:
```ailang
value1 = Dereference(ptr)
value2 = Dereference(Add(ptr, 8))
```

**Pointer Arithmetic:**
```ailang
// Calculate offset
offset = Multiply(index, 8)
element_ptr = Add(base_ptr, offset)

// Access element
element = Dereference(element_ptr)
```

---

## LinkagePool System

LinkagePools provide structured, type-safe data blocks. See the **LinkagePool Reference Manual** for comprehensive documentation.

### Quick Reference

```ailang
// Define structure
LinkagePool.Config {
    "host": Initialize=""
    "port": Initialize=8080
    "max_conn": Initialize=100
}

// Allocate instance
config = AllocateLinkage(LinkagePool.Config)

// Access fields
config.host = "localhost"
config.port = 3000
config.max_conn = 50

// Read fields
current_port = config.port
```

### Type Safety

The compiler tracks LinkagePool types:

```ailang
LinkagePool.TypeA { "field1": Initialize=0 }
LinkagePool.TypeB { "field2": Initialize=0 }

a = AllocateLinkage(LinkagePool.TypeA)
b = AllocateLinkage(LinkagePool.TypeB)

a.field1 = 10  // ✓ Valid
a.field2 = 20  // ✗ Compile error: field2 not in TypeA
```

---

## Memory Access Patterns

### Sequential Access

Optimal for cache performance:

```ailang
// Process array sequentially
i = 0
WhileLoop LessThan(i, count) {
    offset = Multiply(i, 8)
    element_ptr = Add(base_ptr, offset)
    value = Dereference(element_ptr)
    
    // Process value
    ProcessElement(value)
    
    i = Add(i, 1)
}
```

### Strided Access

Access with fixed stride:

```ailang
// Every 4th element
i = 0
WhileLoop LessThan(i, count) {
    offset = Multiply(i, 32)  // 4 * 8 bytes
    element_ptr = Add(base_ptr, offset)
    value = Dereference(element_ptr)
    
    i = Add(i, 1)
}
```

### Structure Access

Access fields in a structure:

```ailang
// Manual structure (without LinkagePool)
person_ptr = Allocate(32)

// Store fields
StoreValue(person_ptr, 12345)           // ID at offset 0
StoreValue(Add(person_ptr, 8), 30)      // Age at offset 8
StoreValue(Add(person_ptr, 16), 50000)  // Salary at offset 16

// Read fields
person_id = Dereference(person_ptr)
person_age = Dereference(Add(person_ptr, 8))
person_salary = Dereference(Add(person_ptr, 16))
```

---

## Best Practices

### 1. Choose the Right Pool Type

**Use FixedPool when:**
- Data is global and persistent
- Access patterns are random
- Fast O(1) access is critical
- Memory size is predictable

**Use DynamicPool when:**
- Data size grows dynamically
- Lifetime spans multiple functions
- You need structured collections

**Use TemporalPool when:**
- Data is temporary
- Lifetime is scope-bound
- Frequent allocation/deallocation

**Use LinkagePool when:**
- Structured data with named fields
- Passing complex data between functions
- Type safety is important

### 2. Memory Hygiene

Always deallocate heap memory:

```ailang
// Good
buffer = Allocate(1024)
ProcessData(buffer)
Deallocate(buffer, 1024)

// Bad - memory leak
buffer = Allocate(1024)
ProcessData(buffer)
// Missing Deallocate!
```

### 3. Align Allocations

For optimal cache performance, align large allocations:

```ailang
// Align to 64 bytes (cache line)
requested_size = 1000
aligned_size = Add(requested_size, 63)
aligned_size = Divide(aligned_size, 64)
aligned_size = Multiply(aligned_size, 64)

buffer = Allocate(aligned_size)
```

### 4. Minimize Pointer Chasing

Group related data together:

```ailang
// Bad - three separate allocations
name = AllocateString("Alice")
age = 30
id = 12345

// Good - single LinkagePool
person = AllocateLinkage(LinkagePool.Person)
person.name = "Alice"
person.age = 30
person.id = 12345
```

### 5. Use FixedPool for Counters

FixedPools are ideal for statistics:

```ailang
FixedPool.Stats {
    "requests": Initialize=0
    "errors": Initialize=0
    "total_time": Initialize=0
}

// Fast increment
Stats.requests = Add(Stats.requests, 1)
```

---

## Performance Considerations

### FixedPool Performance

**Fastest access pattern in AI Lang:**
- Single instruction: `MOV RAX, [R15 + offset]`
- No pointer chasing
- No cache misses (after warmup)
- Ideal for hot paths

### DynamicPool Performance

**Two-step access:**
1. Load pointer from stack: `MOV RAX, [RBP-offset]`
2. Access member: `MOV RBX, [RAX + member_offset]`

**Cost:** One extra memory access, potential cache miss

### Heap Allocation Cost

**Allocate() overhead:**
- System call (mmap): ~100-500 CPU cycles
- Amortize by allocating larger blocks
- Reuse buffers when possible

**Deallocate() overhead:**
- System call (munmap): ~100-500 CPU cycles
- Consider keeping pools for frequent allocations

### Cache Optimization

**Cache line size:** 64 bytes

```ailang
// Bad - false sharing
FixedPool.Counters {
    "thread1_count": Initialize=0  // offset 0
    "thread2_count": Initialize=0  // offset 8
    // Both in same cache line - contention!
}

// Good - pad to separate cache lines
FixedPool.Counters {
    "thread1_count": Initialize=0     // offset 0
    "pad1": Initialize=0               // offset 8
    "pad2": Initialize=0               // offset 16
    // ... 7 more padding entries
    "thread2_count": Initialize=0     // offset 64
    // Different cache lines - no contention
}
```

---

## Common Patterns

### Buffer Management

```ailang
FixedPool.Buffers {
    "read_buffer": Initialize=0
    "write_buffer": Initialize=0
    "buffer_size": Initialize=4096
}

SubRoutine.InitializeBuffers {
    Buffers.read_buffer = Allocate(Buffers.buffer_size)
    Buffers.write_buffer = Allocate(Buffers.buffer_size)
}

SubRoutine.CleanupBuffers {
    Deallocate(Buffers.read_buffer, Buffers.buffer_size)
    Deallocate(Buffers.write_buffer, Buffers.buffer_size)
}
```

### Ring Buffer

```ailang
FixedPool.RingBuffer {
    "buffer": Initialize=0
    "head": Initialize=0
    "tail": Initialize=0
    "size": Initialize=256
    "count": Initialize=0
}

SubRoutine.RingBufferPush {
    // Input: value (global)
    
    IfCondition LessThan(RingBuffer.count, RingBuffer.size) ThenBlock: {
        // Calculate offset
        offset = Multiply(RingBuffer.tail, 8)
        write_ptr = Add(RingBuffer.buffer, offset)
        
        // Store value
        StoreValue(write_ptr, value)
        
        // Update tail
        RingBuffer.tail = Modulo(Add(RingBuffer.tail, 1), RingBuffer.size)
        RingBuffer.count = Add(RingBuffer.count, 1)
    }
}
```

### Memory Pool

```ailang
FixedPool.MemoryPool {
    "pool_base": Initialize=0
    "pool_size": Initialize=1048576  // 1MB
    "next_free": Initialize=0
}

SubRoutine.PoolAllocate {
    // Input: size (global)
    // Output: allocated (global)
    
    allocated = 0
    
    IfCondition LessEqual(Add(MemoryPool.next_free, size), MemoryPool.pool_size) ThenBlock: {
        allocated = Add(MemoryPool.pool_base, MemoryPool.next_free)
        MemoryPool.next_free = Add(MemoryPool.next_free, size)
    }
}
```

---

## Troubleshooting

### Common Issues

#### Memory Leaks

**Symptom:** Program memory usage grows over time

**Cause:** Missing Deallocate() calls

**Solution:**
```ailang
// Use Try-Finally to ensure cleanup
TryBlock: {
    buffer = Allocate(1024)
    ProcessData(buffer)
} FinallyBlock: {
    Deallocate(buffer, 1024)
}
```

#### Segmentation Faults

**Symptom:** Program crashes with SIGSEGV

**Causes:**
1. Accessing freed memory
2. Null pointer dereference
3. Out of bounds access

**Solutions:**
```ailang
// Check pointer validity
IfCondition NotEqual(ptr, 0) ThenBlock: {
    value = Dereference(ptr)
}

// Bounds checking
IfCondition LessThan(index, array_size) ThenBlock: {
    offset = Multiply(index, 8)
    element = Dereference(Add(array_ptr, offset))
}
```

#### Pool Table Overflow

**Symptom:** Compiler error: "Too many pool variables"

**Cause:** More than 131,072 FixedPool variables

**Solution:** Use DynamicPool or LinkagePool for large collections

#### Double Free

**Symptom:** Corruption or crash on Deallocate()

**Cause:** Calling Deallocate() twice on same pointer

**Solution:**
```ailang
// Set to zero after freeing
Deallocate(buffer, size)
buffer = 0

// Check before freeing
IfCondition NotEqual(buffer, 0) ThenBlock: {
    Deallocate(buffer, size)
    buffer = 0
}
```

---

## Summary

AI Lang's memory management system provides:

✓ **Direct Control** - Explicit allocation and deallocation  
✓ **Type Safety** - LinkagePool system with field tracking  
✓ **High Performance** - Zero-overhead abstractions  
✓ **Flexibility** - Multiple pool types for different needs  
✓ **Simplicity** - Clear, readable syntax  

### Memory Type Decision Matrix

| Requirement | Pool Type |
|-------------|-----------|
| Global state | FixedPool |
| Growing collections | DynamicPool |
| Temporary data | TemporalPool |
| Structured data | LinkagePool |
| Raw buffers | Allocate() |

### Key Takeaways

1. Use FixedPool for performance-critical global state
2. Use DynamicPool for growable collections
3. Use TemporalPool for scoped temporary data
4. Use LinkagePool for structured inter-function communication
5. Always pair Allocate() with Deallocate()
6. Check pointers before dereferencing
7. Align large allocations to cache lines

---

**Copyright © 2025 Sean Collins, 2 Paws Machine and Engineering**  
**AI Lang Compiler - Memory Management Reference Manual**