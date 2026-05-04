# JIT VM Design — Bytecode-to-Native with Mailbox Allocator

## Overview

Replace the interpreter dispatch loop (`JSVM_Step` → `Branch op`) with native
x86-64 code generated at runtime. The interpreter remains as fallback for cold
paths and complex opcodes. Hot basic blocks are compiled to native and patched
into the dispatch.

**Architecture**: Method JIT (compile entire function at once on first call).
No tracing, no profiling counters. Eager compilation keeps it simple and
deterministic.

---

## Memory Model: Mailbox Head-Tail Bump Allocator

### Concept (from PacketRing / 68HC mailbox pattern)

Two buffers (A and B) with head/tail pointers. Code is bump-allocated forward
from head. When head reaches tail (buffer full), flip to the other buffer.
The cold buffer is eligible for cleanup (functions that haven't been called
since last flip get their entries removed).

```
Buffer A:                            Buffer B:
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│ [func1] [func2] [func3] HEAD→  │  │ (cold — being reclaimed)        │
└─────────────────────────────────┘  └─────────────────────────────────┘
         ↑ active writes                      ↑ GC sweep
```

### Layout

```ailang
FixedPool.JITMem {
    "buf_a":       Initialize=0    // mmap'd buffer A base address
    "buf_b":       Initialize=0    // mmap'd buffer B base address
    "buf_size":    Initialize=0    // size per buffer (default: 2MB)
    "active":      Initialize=0    // 0=A, 1=B — which buffer is currently live
    "head":        Initialize=0    // write cursor in active buffer
    "tail":        Initialize=0    // end of active buffer (buf + buf_size)
    "entry_count": Initialize=0    // number of JIT'd function entries
    "flip_count":  Initialize=0    // total buffer flips (for stats)
}
```

### Operations

```
JIT_Init():
    buf_a = mmap(NULL, 2MB, PROT_READ|PROT_WRITE|PROT_EXEC, MAP_ANON|MAP_PRIVATE)
    buf_b = mmap(NULL, 2MB, PROT_READ|PROT_WRITE|PROT_EXEC, MAP_ANON|MAP_PRIVATE)
    active = 0
    head = buf_a
    tail = buf_a + 2MB

JIT_Alloc(size):
    if head + size > tail:
        JIT_Flip()   // switch to other buffer
    addr = head
    head += size
    // Align to 16 bytes (code alignment for CPU fetch)
    head = (head + 15) & ~15
    return addr

JIT_Flip():
    // Switch active buffer
    active = 1 - active
    if active == 0:
        head = buf_a
        tail = buf_a + buf_size
    else:
        head = buf_b
        tail = buf_b + buf_size
    // Reset the new active buffer (invalidate old entries)
    JIT_InvalidateBuffer(head, buf_size)
    flip_count++
```

### Auto-Grow

If both buffers are nearly full (>90% used before flip), double buf_size:
```
JIT_Grow():
    new_size = buf_size * 2
    mremap(buf_a, buf_size, new_size, MREMAP_MAYMOVE)
    mremap(buf_b, buf_size, new_size, MREMAP_MAYMOVE)
    buf_size = new_size
    // Update tail pointer
```

### Auto-Reduce

If after 10 flips, peak usage stays below 25% of buf_size, halve it:
```
JIT_MaybeShrink():
    if flip_count % 10 == 0 AND peak_usage < buf_size / 4:
        // munmap + re-mmap at half size
```

---

## JIT Entry Table

Maps bytecode function index → native code address.

```ailang
FixedPool.JITConst {
    "MAX_ENTRIES":   Initialize=1024
    "ENTRY_SIZE":    Initialize=24    // [func_idx(8), native_addr(8), code_size(8)]
}

FixedPool.JITState {
    "entries":       Initialize=0    // Arena-allocated table (1024 × 24 bytes)
    "count":         Initialize=0    // Current number of compiled functions
    "enabled":       Initialize=0    // 1=JIT active, 0=interpreter only
}
```

### Lookup (O(1))

Function indices from the compiler are sequential. Use direct-index table:
```
native_addr = Dereference(Add(JITState.entries, Multiply(func_idx, 24)) + 8)
if native_addr != 0:
    // Jump to native code
else:
    // Fall through to interpreter
```

---

## Compilation Pipeline

### Input

A compiled JS function's bytecode: `code_ptr`, `code_len`, `local_count`,
`const_pool`, `const_count`.

### Output

Native x86-64 machine code that:
1. Reads from the VM value stack (`JSVMState.stack`, `JSVMState.sp`)
2. Reads/writes locals from the frame
3. Calls JSRT_* functions for complex operations
4. Returns to the interpreter for uncompilable opcodes

### Compilation Strategy: Whole-Function

On `CALL` opcode:
1. Check JIT entry table for the callee function index
2. If native_addr != 0 → jump to it
3. If native_addr == 0 → compile the function, store entry, then jump

### Register Allocation (minimal)

We don't do full register allocation. The VM is stack-based.
Use a fixed register convention:

```
RAX  — scratch / return value / TOS cache
RBX  — VM stack pointer (JSVMState.sp * 8 + JSVMState.stack)
RCX  — scratch / argument passing
RDX  — scratch / upper 128-bit multiply
RSI  — bytecode PC (for fallback)
RDI  — const_pool base pointer
RBP  — frame pointer (locals base)
R12  — JSVMState.stack base (callee-saved)
R13  — JSVMState.sp (callee-saved)
R14  — reserved
R15  — reserved
```

### Opcode Translation (Tier 1 — Simple Opcodes)

These compile 1:1 to short native sequences:

| Bytecode | Native x86-64 | Cycles |
|----------|--------------|--------|
| PUSH_CONST idx | `mov rax, [rdi + idx*16 + 8]; mov [r12 + r13*8], rax; inc r13` | 3 |
| PUSH_UNDEF | `mov qword [r12 + r13*8], 0; inc r13` | 2 |
| PUSH_TRUE | `mov qword [r12 + r13*8], 1; inc r13` | 2 |
| POP | `dec r13` | 1 |
| DUP | `mov rax, [r12 + (r13-1)*8]; mov [r12 + r13*8], rax; inc r13` | 3 |
| GET_LOCAL n | `mov rax, [rbp + n*8]; mov [r12 + r13*8], rax; inc r13` | 3 |
| SET_LOCAL n | `dec r13; mov rax, [r12 + r13*8]; mov [rbp + n*8], rax` | 3 |
| ADD | `dec r13; mov rax,[r12+r13*8]; dec r13; call JSRT_Add; mov [r12+r13*8],rax; inc r13` | ~10 |
| JMP offset | `jmp rel32` | 1 |
| JMP_FALSE off | `dec r13; mov rax,[r12+r13*8]; test rax,rax; jz rel32` | 3 |
| RETURN | `dec r13; mov rax,[r12+r13*8]; ret` | 2 |
| HALT | `ret` | 1 |

### Opcode Translation (Tier 2 — Calls to Runtime)

Complex opcodes that call JSRT_* functions. JIT emits a `call` instruction:

```asm
; ADD opcode (calls JSRT_Add)
    dec   r13                    ; pop b
    mov   rsi, [r12 + r13*8]    ; rsi = b (JSValue*)
    dec   r13                    ; pop a
    mov   rdi, [r12 + r13*8]    ; rdi = a (JSValue*)
    call  JSRT_Add              ; rax = result JSValue*
    mov   [r12 + r13*8], rax    ; push result
    inc   r13
```

This is the same work the interpreter does, minus the dispatch overhead
(Branch lookup, ReadByte, bounds checks). Eliminating dispatch = ~5-10 cycles
per opcode saved.

### Opcode Translation (Tier 3 — Deferred to Interpreter)

These are too complex or rare to JIT. Emit a "bail to interpreter" stub:

- TRY_PUSH / TRY_POP / THROW
- YIELD / GEN_CLOSURE
- CLOSURE (captures)
- GET_PROP / SET_PROP (polymorphic IC needed for real speedup)

Bail stub:
```asm
; Save JIT state back to JSVMState
    mov   [JSVMState.sp], r13
    mov   [JSVMState.pc], <bytecode_offset>
    ret   ; return to JSVM_Run which resumes interpreter
```

---

## Integration with JSVM_Run

### Modified Run Loop

```ailang
Function.JSVM_Run {
    Output: Address
    Body: {
        JSVMTmp.done = 0
        WhileLoop EqualTo(JSVMTmp.done, 0) {
            // Check if current PC is at a JIT'd function entry
            IfCondition And(EqualTo(JITState.enabled, 1), EqualTo(JSVMState.pc, 0)) ThenBlock: {
                // Function entry — check JIT table
                native = JIT_Lookup(JSVMState.current_func)
                IfCondition NotEqual(native, 0) ThenBlock: {
                    // Jump to native code
                    JIT_Execute(native)
                    // When native returns, check if we need to continue
                    // ...
                }
            }
            // Fallback: interpreter step
            rc = JSVM_Step()
            IfCondition Or(EqualTo(JSVMState.halted, 1), EqualTo(JSVMState.error, 1)) ThenBlock: {
                JSVMTmp.done = 1
            }
        }
        // ...
    }
}
```

### JIT_Execute — Trampoline

The trampoline sets up registers and calls the native code:

```asm
JIT_Execute:
    ; Save callee-saved registers
    push  rbx
    push  r12
    push  r13
    push  rbp

    ; Load VM state into registers
    mov   r12, [JSVMState.stack]      ; stack base
    mov   r13, [JSVMState.sp]         ; stack pointer
    mov   rbp, <locals_base>          ; frame locals
    mov   rdi, [JSVMState.const_pool] ; const pool

    ; Call native function code
    call  rax                          ; rax = native_addr

    ; Save VM state back
    mov   [JSVMState.sp], r13

    ; Restore callee-saved
    pop   rbp
    pop   r13
    pop   r12
    pop   rbx
    ret
```

---

## Ping-Pong GC (Mailbox Cleanup)

### When Buffer Flips

On `JIT_Flip()`, the OLD buffer becomes cold. Before zeroing it:

1. Walk the JIT entry table
2. For each entry whose `native_addr` points into the cold buffer:
   - Check a "last_called" counter (incremented on each native call)
   - If called since last flip: **recompile** into the new active buffer
   - If NOT called since last flip: **evict** (set native_addr = 0, falls back to interpreter)

This gives us automatic cleanup of dead code with zero pauses:
- Hot functions migrate forward (always live)
- Cold functions get evicted (free memory)
- No stop-the-world, no mark phase, no write barriers

### Memory Pressure Behavior

```
Normal:     2MB active, 2MB cold, ~4MB total JIT pressure
Busy:       grow to 4MB+4MB, 8MB+8MB, etc.
Quiet:      shrink back after 10 low-usage flips
Worst case: 16MB total (8M×2) — acceptable for a browser tab
```

---

## Implementation Phases

### Phase 1: Infrastructure
- [ ] `JIT_Init()` — mmap two executable buffers
- [ ] `JIT_Alloc(size)` — bump allocator with flip
- [ ] `JIT_Flip()` — buffer switch
- [ ] JIT entry table allocation

### Phase 2: Trivial Compilation
- [ ] Compile arithmetic-only functions (PUSH_CONST, ADD, SUB, MUL, GET_LOCAL, SET_LOCAL, RETURN)
- [ ] Trampoline (JIT_Execute)
- [ ] Verify correctness: `fib(20)` produces same result via JIT and interpreter

### Phase 3: Control Flow
- [ ] JMP, JMP_FALSE, JMP_TRUE → native jumps (rel32)
- [ ] Forward jump patching (backpatch like compiler's JSComp__PatchJump)
- [ ] Loop headers (backward jumps)

### Phase 4: Full Opcode Coverage
- [ ] CALL → recursive JIT (compile callee if needed, then `call` native)
- [ ] GET_PROP/SET_PROP → call JSRT functions
- [ ] Exception handling → bail to interpreter
- [ ] Generators → bail to interpreter

### Phase 5: Optimizations
- [ ] Inline JSRT_Add/Sub/Mul for NUMBER types (type check + integer op, skip JSValue allocation)
- [ ] Constant folding in JIT (PUSH_CONST + PUSH_CONST + ADD → PUSH_CONST result)
- [ ] Loop-invariant code motion (hoist GET_LOCAL outside loops)

---

## File Layout

```
Librarys/Browser/
    Library.JSJIT.ailang        — JIT compiler (bytecode → native x86-64)
    Library.JSJITMem.ailang     — Mailbox allocator (mmap, flip, grow/shrink)
    Library.JSJITTrampoline.ailang — Register setup, call convention, bail stubs
```

Or consolidated into a single `Library.JSJIT.ailang` if total LOC < 1000.

---

## Syscall Reference

```ailang
// mmap(addr, len, prot, flags, fd, offset)
// PROT_READ=1, PROT_WRITE=2, PROT_EXEC=4 → 7 (RWX)
// MAP_PRIVATE=2, MAP_ANONYMOUS=32 → 34
buf = SystemCall(9, 0, size, 7, 34, -1, 0)

// mremap(old_addr, old_size, new_size, flags)
// MREMAP_MAYMOVE=1
buf = SystemCall(25, old_addr, old_size, new_size, 1)

// munmap(addr, size)
SystemCall(11, addr, size)
```

---

## Expected Performance Gain

The interpreter currently spends ~5-10 cycles per opcode on dispatch overhead:
- ReadByte (memory load)
- Branch (compare + conditional jump — potentially mispredicted)
- Step counter increment + bounds check
- Function call overhead (JSVM_Step is a full function)

JIT eliminates ALL of this. Pure arithmetic sequences (loops, math) go from
~15 cycles/op (dispatch + work) to ~5 cycles/op (just work).

**Expected speedup: 2-3× on compute-heavy code.** Combined with fixed-point
arithmetic (already 100× faster than V8), this would put us at 200-300× for
integer workloads.

For comparison: V8's TurboFan JIT produces ~2-3 cycles/op for optimized code.
Our simple method JIT won't match that, but we start from a much lower baseline
(no GC, no object boxing, no type guards) so the absolute performance stays
competitive.
