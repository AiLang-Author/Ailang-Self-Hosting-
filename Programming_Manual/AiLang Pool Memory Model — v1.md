# AiLang Pool Memory Model — v1.0

## 0. Scope
This document specifies AiLang’s **Pool Memory Model**: allocation, ownership, lifetimes, concurrency, and safety guarantees. Pools are a **language primitive** and replace raw `malloc`/`free` and global heap models.

---


WARNING !!!!! READ THE FOLLOWING WARNING !!!!!

AILANG Memory Model Documentation
markdown### Memory Isolation by Design

AILANG implements deliberate memory isolation between execution contexts:

1. **Main Context Pool**: Variables declared in FixedPool are accessible to Main/SubRoutines
2. **Function Context Pool**: Functions get their own isolated pool table
3. **No Shared Memory By Default**: This prevents:
   - Buffer overflows corrupting unrelated data
   - Use-after-free bugs crossing context boundaries  
   - Race conditions in concurrent code
   - Stack corruption from function calls

### Data Sharing Patterns

#### ✓ Correct: Parameter Passing
```ailang
Function.ProcessData {
    Input: data_ptr: Integer
    Body: {
        // Use passed pointer explicitly
    }
}
✓ Correct: Message Passing
ailangSendMessage.Channel { data }
ReceiveMessage.Channel { ProcessData(data) }
✗ Incorrect: Assuming Shared Pool Access
ailang// This won't work - functions can't see Main's pool
Function.BadAccess {
    value = MainPool.shared_var  // Returns 0!
}
Rationale
This design eliminates entire categories of bugs:

No accidental data sharing
Clear ownership semantics
Predictable memory lifecycle
Safe concurrent execution potential


This is similar to Rust's ownership model or Erlang's process isolation - modern language design that learned from C's mistakes. The fact that you have to explicitly pass data between contexts makes the data flow clear and auditable.

The Redis server now works perfectly because we're following the proper pattern - Main owns the store, and passes it explicitly to functions that need it. No hidden shared state, no mysterious corruption.




## 1. Philosophy
- **Explicit, not implicit**: All memory lives in named pools.  
- **Deterministic**: Pools control lifetime, allocation policy, and capacity.  
- **Safe**: Ownership transfer is tracked; no dangling pointers.  
- **Performant**: Pools support fixed-size, dynamic, and zero-copy usage with no GC overhead.  
- **Composable**: Pools integrate with loops/actors, making memory part of concurrency, not a separate subsystem.

---

## 2. Pool Types

| Pool Type          | Description                                                                |
|--------------------|----------------------------------------------------------------------------|
| **FixedPool**      | Pre-allocated, constant capacity. Fastest, predictable footprint.          |
| **DynamicPool**    | Grows on demand up to a maximum. Allocations may trigger expansion.        |
| **SharedPool**     | Multiple actors share access with atomic counters for safe concurrency.    |
| **StackPool**      | LIFO allocation/free pattern. Ideal for recursive or temporary workloads.  |
| **RegionPool**     | Allocations freed en masse when region is reset; no per-object free.       |

---

## 3. Pool Declaration

```ailang
FixedPool.Messages {
  "buffer": ElementType-Byte, MaximumLength-1024,
  "slots": ElementType-Address, MaximumLength-32,
  "policy": Initialize-"zero"
}
Each field declares element type, capacity, and optional init policy.

Pools may be nested or global.

Default init policy is undefined; explicit policies include "zero", "pattern", "lazy".

4. Allocation & Free
ailang
Copy code
msg = PoolAlloc(Messages.slots)
PoolFree(Messages.slots, msg)
PoolAlloc(pool) returns an owned object (pointer, slice, or struct).

PoolFree(pool, obj) returns memory to the pool.

Ownership rules apply: after free, the variable is invalid.

5. Ownership Semantics
Exactly one owner per object at a time.

Ownership may transfer via:

LoopSend (move semantics).

PoolBorrow (read-only access, cannot escape scope).

Use-after-free and double-free are compile-time errors if detectable, runtime asserts if dynamic.

6. Safety Policies
Bounds Checking: Pool arrays are bounds-checked at runtime unless compiled with -Ounsafe.

Init Policy: Initialize-"zero" ensures deterministic start state.

Debug Integration: DebugMemory.Watch(pool) can detect leaks, buffer overruns, and invalid frees.

7. Concurrency Integration
Pools are actor-aware:

FixedPool may be local to a loop/actor.

SharedPool uses atomic ops to allow concurrent alloc/free.

Pool operations are cooperative; contention does not block OS threads.

8. Example: Actor Mailbox with Pool
ailang
Copy code
FixedPool.Mailbox {
  "msgs": ElementType-Text, MaximumLength-128,
  "policy": Initialize-"zero"
}

LoopActor.Logger {
  LoopReceive m {
    case "log": 
      slot = PoolAlloc(Mailbox.msgs)
      StoreString(slot, m)
      PrintMessage("Logged:"); PrintMessage(m)
      PoolFree(Mailbox.msgs, slot)
  }
}
9. Example: Buffer Reuse with Zero-Copy
ailang
Copy code
FixedPool.Network {
  "frames": ElementType-Byte, MaximumLength-8192,
  "policy": Initialize-"pattern", Pattern-0xAA
}

LoopActor.Net {
  LoopReceive packet {
    case data: 
      buf = PoolAlloc(Network.frames)
      MemoryCopy(buf, data, Length(data))
      LoopSend(Consumer, buf)   # Ownership transfers here
  }
}
10. Error Handling
Exhaustion:

PoolAlloc on a full pool → returns null/invalid sentinel.

With policy:"block", sender yields until free space is available.

Misuse:

Freeing non-owned memory → runtime assertion.

Borrow escape → compile-time error.

11. Performance Guidance
Prefer FixedPool for hot paths; avoids fragmentation.

Use RegionPool for batch workloads (parse trees, temp structures).

Shared pools should be sized to minimize contention.

Align pool element sizes to cache lines for better throughput.

12. Conformance Checklist
 Allocation/deallocation is O(1).

 Bounds are enforced.

 Ownership transfer invalidates sender’s reference.

 Pools integrate with DebugMemory facilities.

 Exhaustion is deterministic (no hidden GC).

13. Future Extensions
Pool Profiles: Predefined configs for common use (e.g. network buffers).

NUMA Pools: Node-aware allocation for multi-socket systems.

Persistent Pools: Backed by memory-mapped files.
