# Fixed-Point Division via Reciprocal Multiply — 68HC Scaling Trick

## Core Insight

Division is expensive (IDIV: 20-80 cycles). Multiplication is cheap (IMUL: 3-4 cycles).
Scale by the midpoint so division becomes multiplication by the reciprocal.

```
a / b  →  a * (SCALE / b) >> SHIFT
```

On x86-64, `IMUL r64, r64` produces a 128-bit result in RDX:RAX.
The upper bits ARE the fixed-point division result. No real IDIV in the hot path.

---

## Math

### Q32.32 Format

Real value of `a_raw` in Q32.32: `A = a_raw / 2^32`

Division: `A / B = (a_raw / 2^32) / (b_raw / 2^32) = a_raw / b_raw`

But we need the result in Q32.32: `result_raw = (a_raw * 2^32) / b_raw`

### Reciprocal Transform

Precompute: `recip = 2^64 / b_raw`

Then: `result_raw = (a_raw * recip) >> 32`

Proof: `(a_raw * 2^64 / b_raw) >> 32 = (a_raw * 2^32) / b_raw` ✓

### x86-64 Implementation

```asm
; Input: RAX = a_raw (Q32.32), RBX = b_raw (Q32.32)
; Step 1: Compute reciprocal (amortizable — do once per divisor)
    xor   rdx, rdx
    mov   rax, 1          ; RDX:RAX = 2^64
    mov   rdx, 1          ; Actually: RDX=1, RAX=0 → 2^64 as 128-bit
    xor   rax, rax
    div   rbx             ; RAX = 2^64 / b_raw = reciprocal
    mov   rcx, rax        ; RCX = reciprocal (save for reuse)

; Step 2: Multiply a_raw * reciprocal (128-bit result in RDX:RAX)
    mov   rax, [a_raw]
    imul  rcx             ; RDX:RAX = a_raw * reciprocal (signed: use IMUL r64)
    ; Actually for signed: imul is one-operand form → RDX:RAX = RAX * r/m64

; Step 3: Extract Q32.32 result — bits [95:32] of 128-bit product
    shrd  rax, rdx, 32   ; RAX = (RDX[31:0] << 32) | (RAX >> 32)
    ; RAX now contains the Q32.32 division result
```

**Cost: 3 cycles (IMUL) + 1 cycle (SHRD) = 4 cycles per division.**

The initial IDIV (for reciprocal) costs 20-80 cycles but is computed ONCE.

---

## Per-Format Details

### Q8.8 Division

```
recip = 2^16 / b_raw        ; fits in 16 bits
result = (a_raw * recip) >> 8
```

x86-64: Single 32-bit IMUL, shift right 8. Fits entirely in GPR.
```asm
    movzx eax, [a_raw]     ; 16-bit Q8.8 value
    imul  eax, ecx         ; 32-bit result (no overflow possible for Q8.8 × Q8.8)
    sar   eax, 8           ; arithmetic shift right → Q8.8 result
```
Cost: 3 cycles. No 128-bit math needed.

### Q16.16 Division

```
recip = 2^32 / b_raw        ; fits in 32 bits
result = (a_raw * recip) >> 16
```

x86-64: 64-bit IMUL, shift right 16.
```asm
    movsxd rax, [a_raw]    ; 32-bit Q16.16 sign-extended to 64
    imul   rax, rcx        ; 64-bit result (rcx = reciprocal)
    sar    rax, 16          ; arithmetic shift right → Q16.16 result
```
Cost: 3-4 cycles. Still no 128-bit math.

### Q32.32 Division

```
recip = 2^64 / b_raw        ; fits in 64 bits
result = bits[95:32] of (a_raw * recip)  ; 128-bit intermediate
```

x86-64: One-operand IMUL (128-bit), SHRD to extract.
```asm
    mov   rax, [a_raw]
    imul  rcx              ; RDX:RAX = signed 128-bit product
    shrd  rax, rdx, 32    ; extract bits [95:32]
```
Cost: 4-5 cycles.

---

## Reciprocal Caching Strategy

### Constant Divisors (compile-time)

For `x / 10`, `x / 255`, `x / 360`, etc. — the reciprocal is a constant:

```
recip_10     = 2^64 / (10 << 32) = 0x1999999999999999   ; for Q32.32 "10.0"
recip_255    = 2^64 / (255 << 32)
recip_360    = 2^64 / (360 << 32)
```

Emitted directly as `MOV RCX, imm64` — zero runtime cost for the reciprocal.

### Loop-Invariant Divisors

```javascript
for (var i = 0; i < n; i++) {
    result[i] = data[i] / scale;
}
```

Compiler hoists `recip = 2^64 / scale_raw` outside the loop.
Inner loop: `IMUL + SHRD` per iteration (4 cycles) vs `IDIV` (20-80 cycles).

### Dynamic Divisors (one-shot)

For `a / b` where `b` changes every time:
- Fall back to the standard approach: `(a << 32) / b` using real IDIV
- But even here, we can use the MUL trick with a Newton-Raphson reciprocal approximation (2 iterations = 4 MULs ≈ 16 cycles, still better than IDIV)

### Newton-Raphson Reciprocal (optional, 16 cycles)

For when you need a fast one-shot reciprocal without IDIV:

```
; Approximate 2^64 / b using Newton-Raphson
; Initial guess: x0 = 2^63 / leading_bits(b)  (BSR + shift, ~3 cycles)
; Iteration: x_{n+1} = x_n * (2 - b * x_n)
; 2 iterations gives ~60 bits of precision (enough for Q32.32)

; x0 ≈ 2^(63 - BSR(b)) << 32
    bsr   rcx, rbx         ; rcx = floor(log2(b))
    mov   rax, 1
    shl   rax, 63
    shr   rax, cl          ; x0 = 2^(63-log2(b))
    shl   rax, 32          ; scale to Q32.32 space

; Iteration 1: x1 = x0 * (2 - b*x0) >> 32
    mov   rdx, rbx
    imul  rdx, rax         ; b * x0 (64-bit)
    shr   rdx, 32
    neg   rdx
    add   rdx, 2           ; 2 - b*x0/2^32
    ... (simplified — actual impl uses SHRD)

; After 2 iterations: rax ≈ 2^64 / b with < 1 ULP error
```

This gives us a **pure-multiply division path** with no IDIV at all:
- BSR (1 cycle) + 4× IMUL (12 cycles) + shifts (3 cycles) = ~16 cycles
- vs IDIV at 20-80 cycles

---

## Integration with JSRuntime

### JSRT_Div Rewrite

```ailang
Function.JSRT_Div {
    Input: a: Address
    Input: b: Address
    Output: Address
    Body: {
        a_type = Dereference(a)
        b_type = Dereference(b)
        a_raw = Dereference(Add(a, 8))
        b_raw = Dereference(Add(b, 8))

        // Zero check (division by zero → return 0 or Infinity sentinel)
        IfCondition EqualTo(b_raw, 0) ThenBlock: {
            ReturnValue(JSRT_CreateFixed_32_32(0))
        }

        // Promote both to common format (Q32.32 for max precision)
        a_q32 = JSRT__ToQ32(a_raw, a_type)
        b_q32 = JSRT__ToQ32(b_raw, b_type)

        // Reciprocal multiply: result = (a_q32 * recip(b_q32)) >> 32
        // Uses compiler intrinsic: FixedDiv_Q32(a, b) → IMUL+SHRD
        result = FixedDiv_Q32(a_q32, b_q32)

        ReturnValue(JSRT_CreateFixed_32_32(result))
    }
}
```

### Compiler Intrinsic: FixedDiv_Q32

New compiler primitive (alongside MemCompare, MemorySet, etc.):

```ailang
// FixedDiv_Q32(a, b) → (a * (2^64/b)) >> 32
// Emits: MOV RAX,1 / XOR RDX,RDX / ... / DIV / IMUL / SHRD
// Or Newton-Raphson path if configured
```

This is a single AILang function call that emits the inline x86-64 sequence.
The compiler recognizes `FixedDiv_Q32` like it recognizes `MemCompare` — as a
hardware-accelerated primitive.

---

## Multiplication (also benefits)

Q32.32 multiplication: `A * B = (a_raw * b_raw) >> 32`

```asm
    mov   rax, [a_raw]
    imul  [b_raw]          ; RDX:RAX = a_raw * b_raw (128-bit signed)
    shrd  rax, rdx, 32    ; extract bits [95:32] = Q32.32 result
```

Same SHRD pattern as division. **3-4 cycles for fixed-point multiply.**

Compare: SSE2 MULSD = 4-5 cycles, AND it needs XMM register save/restore
on function boundaries. Our approach stays entirely in GPR (general purpose
registers) — zero register pressure on the floating-point unit.

---

## Summary of Cycle Costs

| Operation | Fixed-Point (Q32.32) | IEEE 754 (SSE2 double) | Speedup |
|-----------|---------------------|----------------------|---------|
| Add/Sub   | 1 cycle (ADD/SUB)   | 3-4 cycles (ADDSD)   | 3-4×    |
| Multiply  | 4 cycles (IMUL+SHRD)| 4-5 cycles (MULSD)   | ~1×     |
| Div (cached recip) | 4 cycles (IMUL+SHRD) | 13-32 cycles (DIVSD) | 3-8× |
| Div (one-shot) | 16 cycles (Newton) | 13-32 cycles (DIVSD) | 1-2× |
| Div (cold, real) | 20-80 cycles (IDIV) | 13-32 cycles (DIVSD) | 0.4-2× |
| Compare   | 1 cycle (CMP)       | 3 cycles (UCOMISD)   | 3×      |
| Floor     | 1 cycle (AND mask)  | 5+ cycles (ROUNDSD)  | 5×      |
| Ceil      | 2 cycles (ADD+AND)  | 5+ cycles (ROUNDSD)  | 2-3×    |
| Int→Float | 1 cycle (SHL)       | 4-5 cycles (CVTSI2SD)| 4-5×    |
| Float→Int | 1 cycle (SAR)       | 3-6 cycles (CVTTSD2SI)| 3-6×  |

**Average: 2-4× faster than SSE2 doubles across all operations.**
Division with reciprocal caching closes the one gap where IDIV was slower.

---

## Relation to Existing Compiler Primitives

The AILang compiler already has:
- `Multiply(a, b)` → IMUL
- `Divide(a, b)` → IDIV
- `ShiftLeft(a, n)` / `ShiftRight(a, n)` → SHL/SAR

New primitives needed:
- `FixedMul_Q32(a, b)` → IMUL (128-bit) + SHRD 32
- `FixedDiv_Q32(a, b)` → compute reciprocal + IMUL + SHRD 32
- `FixedMul_Q16(a, b)` → IMUL (64-bit) + SAR 16
- `FixedDiv_Q16(a, b)` → reciprocal + IMUL + SAR 16

These go in `Librarys/Compiler/Compile/FPU/X86/` alongside the existing
`Library.FPUCompileX86MemOps.ailang` (which has MemCompare, MemChr, etc.).

File: `Library.FPUCompileX86FixedPoint.ailang`
