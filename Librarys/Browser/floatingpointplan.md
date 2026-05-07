# HalCode Hardware Definition — Progressive Fixed-Point for JavaScript Numbers

## Philosophy

> "Even on 32-bit they could have used 4 32-bit integers and split the results."
> — Sean Collins

IEEE 754 floating point is not the only way to represent fractional numbers. It is a
particular engineering tradeoff (dynamic range at the expense of precision and
complexity) that was made in the 1980s. In a modern VM that already uses tagged
16-byte value types, we can do better with **progressive fixed-point**.

The insight: **most numbers in JavaScript are small**. DOM pixel values, CSS
percentages, opacity (0-1), layout coordinates, array indices, loop counters —
these all live in the ±0-10000 range with 2-4 decimal places of precision.
Fixed-point handles this range with zero rounding error and single-cycle integer
arithmetic. IEEE 754 would use 3-5 cycles per operation *and* introduce
representational errors (0.1 + 0.2 ≠ 0.3).

***

## Current State

### JSValue Layout (16 bytes)

```
Offset 0 (8 bytes): JSType tag  (0=UNDEFINED, 1=NULL, 2=BOOLEAN, 3=NUMBER, ...)
Offset 8 (8 bytes): Payload      (for NUMBER: raw 64-bit signed integer)
```

### What Exists Today

| Layer | File | State |
|-------|------|-------|
| JSLexer | `Library.JSLexer.ailang` | Tokenizes NUMBER. Decimal point + fractional digits are **consumed but truncated**. `StringToInt` only. |
| JSParser | `Library.JSParser.ailang` | `JSParse__ParseInt(ptr, len)` converts token text → integer via `StringToInt`. Stores in `ASTType.NUMBER_LIT → N_VALUE`. |
| JSCompiler | `Library.JSCompiler.ailang` | `JSComp__AddNumber(n)` stores integer in constant pool (type=1). Emits `PUSH_CONST <idx>`. |
| JSVM | `Library.JSVM.ailang` | `PUSH_CONST` loads constant → `JSVM__StackPush`. Arithmetic opcodes (ADD/SUB/MUL/DIV) call JSRT functions. |
| JSRuntime | `Library.JSRuntime.ailang` | `JSRT_CreateNumber(n)` stores int64 payload with JSType.NUMBER tag. `JSRT_Add/Sub/Mul/Div` all use integer arithmetic (Add/Subtract/Multiply/Divide). |

**There is no fractional number support at all.** `3.14` is lexed, parsed, and
stored as `3`. The decimal part is silently discarded.

***

## Proposed Architecture: Progressive Fixed-Point

### Three Formats in One 64-Bit Payload

```
┌─────────────────────────────────────────────────────────────┐
│  Q8.8    │  8-bit integer  │  8-bit fraction │  16 bits    │
│          │  range: ±127    │  prec: 1/256    │  small nums │
├─────────────────────────────────────────────────────────────┤
│  Q16.16  │  16-bit integer │ 16-bit fraction │  32 bits    │
│          │  range: ±32767  │  prec: 1/65536  │  medium     │
├─────────────────────────────────────────────────────────────┤
│  Q32.32  │  32-bit integer │ 32-bit fraction │  64 bits    │
│          │  range: ±2.1B   │  prec: ~1/4.3B  │  full       │
└─────────────────────────────────────────────────────────────┘
```

All three fit in a single 64-bit integer. The format is selected at **value creation
time** based on the number's magnitude.

### Format Encoding

We add three new JSType constants. The existing JSType.NUMBER (=3) is deprecated
for new values but still recognized for backward compat.

```ailang
FixedPool.JSType {
    "UNDEFINED":   Initialize=0
    "NULL":        Initialize=1
    "BOOLEAN":     Initialize=2
    "NUMBER":      Initialize=3   // DEPRECATED — raw int64, kept for compat
    "STRING":      Initialize=4
    "OBJECT":      Initialize=5
    "FUNCTION":    Initialize=6
    "ARRAY":       Initialize=7
    "FIXED_8_8":   Initialize=8   // Q8.8 in lower 16 bits of payload
    "FIXED_16_16": Initialize=9   // Q16.16 in lower 32 bits of payload
    "FIXED_32_32": Initialize=10  // Q32.32 in full 64-bit payload
}
```

**Why separate types instead of a tag within the payload?**

1. The existing dispatch pattern (`JSRT_GetType → deref offset 0`) is already
   optimized for type-tag switching. Adding internal format tags would require
   a second decode step.

2. FIXED_32_32 uses all 64 bits of the payload. There are no spare bits for a
   format tag without stealing from the integer or fraction range.

3. The type tag is checked on almost every operation anyway. Adding 3 more
   cases to the Branch dispatch costs exactly 3 more integer comparisons.

### Value Creation Rules

When creating a number from a parsed literal (e.g., `3.14`, `100.5`, `0.001`):

1. Count integer digits needed (signed): `ceil(log2(abs(int_part) + 1)) + 1` for sign
2. Count fraction precision needed: `ceil(log2(10^frac_digits))`
3. Choose the smallest format that accommodates both:

```
Required integer bits ≤ 7  AND required fraction bits ≤ 8  → FIXED_8_8
Required integer bits ≤ 15 AND required fraction bits ≤ 16 → FIXED_16_16
Otherwise → FIXED_32_32
```

**Example:**
- `3.14` → integer part 3 needs 3 bits, fraction 0.14 needs ~8 bits → FIXED_8_8
- `100.5` → integer 100 needs 8 bits, fraction needs 1 bit → FIXED_16_16
- `0.001` → integer needs 1 bit, fraction 0.001 needs ~10 bits → FIXED_16_16
- `99999.123456` → integer needs 18 bits → FIXED_32_32

### Arithmetic Rules

#### Same-format operations

Addition, subtraction, multiplication, and division on two values of the same
format produce a result in that format. **Overflow detection** promotes the
result to the next wider format.

```ailang
// Q8.8 + Q8.8 → Q8.8 (check overflow)
// If overflow: retry as Q16.16

// Q16.16 + Q16.16 → Q16.16 (check overflow)
// If overflow: retry as Q32.32
```

For Q8.8:
- Integer overflow if |result| ≥ 128
- Fraction stays within 8 bits for add/sub
- Mul: (a * b) >> 8 → 16-bit intermediate, check if result fits in Q8.8
- Div: (a << 8) / b → quotient in Q8.8

#### Mixed-format operations

When formats differ, the narrower is promoted to the wider:

```
FIXED_8_8  + FIXED_16_16
  → widen Q8.8 to Q16.16 (left-shift fraction by 8)
  → Q16.16 + Q16.16
  → Q16.16 result
```

Promotion is just a left shift. No mantissa alignment, no exponent biasing, no
hidden bit. Just `value << 8` or `value << 16`.

#### Overflow Detection

For Q8.8 addition:
```ailang
sum = a + b
// Check if |sum| exceeds Q8.8 integer range (±127)
// Q8.8 min: -32768 (-128 << 8), Q8.8 max: 32512 (127 << 8 | 0xFF)
If sum > 32512 OR sum < -32768:
    // Promote both to Q16.16 and retry
```

For multiplication, the overflow check happens on the 16-bit (for Q8.8×Q8.8)
or 32-bit (for Q16.16×Q16.16) intermediate before shifting down.

***

## Layer-by-Layer Changes

### 1. JSLexer — `Library.JSLexer.ailang`

**Current:** `JSLex__ScanNumber` already consumes the decimal point and
fractional digits. They are stored in the token string but truncated to
integer at parse time.

**Change:** No change to the lexer. The token already contains the full
text representation (e.g., `"3.14"`, `"100.5"`). The parsing happens in
the parser.

### 2. JSParser — `Library.JSParser.ailang`

**Current:** `JSParse__ParseInt(ptr, len)` calls `StringToInt` and stores
the integer result in `N_VALUE`.

**Change:** Replace `JSParse__ParseInt` with `JSParse__ParseFixed` that:

1. Scans the string for a decimal point
2. If no decimal point: parse as integer, store as FIXED_32_32 with
   fraction=0 (or use smallest format that fits)
3. If decimal point present:
   a. Parse integer part (left of `.`)
   b. Parse fractional part (right of `.`), pad/truncate to format precision
   c. Select format based on required integer bits + fraction bits
   d. Pack: `(int_part << frac_bits) | frac_scaled`

**New function:**

```ailang
Function.JSParse__ParseFixed {
    Input: ptr: Address
    Input: len: Integer
    Output: Integer   // Returns the fixed-point integer value (raw payload)
    Output: Integer   // Returns the format (JSType.FIXED_8_8, etc.)
    // ... but AILang only supports single return value.
    // Use FixedPool fields instead.
}
```

Alternative: store both format and raw value in dedicated FixedPool fields on
the parser state, then the compiler reads both when creating the constant pool
entry.

**Change to NUMBER_LIT node:** The `N_VALUE` field (64 bits) stores the raw
fixed-point payload. The format is stored in a new node field or inferred
from the constant pool entry type.

Better approach: store the **format** in `N_OP` (currently unused for
NUMBER_LIT nodes). This is cleaner than modifying the node structure.

### 3. JSCompiler — `Library.JSCompiler.ailang`

**Current:** `JSComp__AddNumber(n)` creates a constant pool entry with
type=1 (NUMBER integer) and the raw integer as payload.

**Change:** New function `JSComp__AddFixed(format, raw_value)`:

```ailang
Function.JSComp__AddFixed {
    Input: fmt: Integer     // JSType.FIXED_8_8, FIXED_16_16, or FIXED_32_32
    Input: raw: Integer     // Raw fixed-point payload
    Output: Integer         // Constant pool index
    Body: {
        // Type tag in constant pool entry matches JSType
        // 8 = FIXED_8_8, 9 = FIXED_16_16, 10 = FIXED_32_32
        idx = JSCompState.const_count
        base = Add(JSCompState.const_pool, Multiply(idx, JSCompConst.CONST_SIZE))
        StoreValue(base, save_fmt)
        StoreValue(Add(base, 8), save_raw)
        JSCompState.const_count = Add(idx, 1)
        ReturnValue(idx)
    }
}
```

In `JSComp__CompileExpr` for NUMBER_LIT:
- Read format from `N_OP`
- Read raw value from `N_VALUE`
- Call `JSComp__AddFixed(fmt, raw)` instead of `JSComp__AddNumber(raw)`

### 4. JSVM — `Library.JSVM.ailang`

**Current:** `JSVM__LoadConst` creates a JSValue for each constant pool
entry. Type 1 → `JSRT_CreateNumber(payload)`. Type 2 → `JSRT_CreateString(payload)`.

**Change:** Add cases for types 8, 9, 10:

```ailang
// In JSVM__LoadConst:
IfCondition EqualTo(ctype, 8) ThenBlock: {
    ReturnValue(JSRT_CreateFixed_8_8(cpay))
}
IfCondition EqualTo(ctype, 9) ThenBlock: {
    ReturnValue(JSRT_CreateFixed_16_16(cpay))
}
IfCondition EqualTo(ctype, 10) ThenBlock: {
    ReturnValue(JSRT_CreateFixed_32_32(cpay))
}
```

The bytecode opcodes (ADD, SUB, MUL, DIV, etc.) do NOT change. They still
call `JSRT_Add(av, bv)`, `JSRT_Sub(av, bv)`, etc. The JSRT functions handle
format dispatch internally.

**No new bytecodes needed.** This is the beauty of fixing it at the value
representation layer.

### 5. JSRuntime — `Library.JSRuntime.ailang`

This is where the bulk of the changes go.

#### New Value Creators

```ailang
Function.JSRT_CreateFixed_8_8 {
    Input: raw: Integer      // Already in Q8.8 format
    Output: Address
    Body: {
        val = JSRT__AllocValue()
        StoreValue(val, JSType.FIXED_8_8)
        StoreValue(Add(val, 8), raw)
        ReturnValue(val)
    }
}

Function.JSRT_CreateFixed_16_16 {
    Input: raw: Integer
    Output: Address
    Body: {
        val = JSRT__AllocValue()
        StoreValue(val, JSType.FIXED_16_16)
        StoreValue(Add(val, 8), raw)
        ReturnValue(val)
    }
}

Function.JSRT_CreateFixed_32_32 {
    Input: raw: Integer
    Output: Address
    Body: {
        val = JSRT__AllocValue()
        StoreValue(val, JSType.FIXED_32_32)
        StoreValue(Add(val, 8), raw)
        ReturnValue(val)
    }
}
```

#### Format Promotion Helpers

```ailang
// Promote Q8.8 → Q16.16: raw << 8
Function.JSRT__Promote_8_8_to_16_16 {
    Input: raw8: Integer
    Output: Integer
    Body: {
        ReturnValue(ShiftLeft(raw8, 8))
    }
}

// Promote Q16.16 → Q32.32: raw << 16
Function.JSRT__Promote_16_16_to_32_32 {
    Input: raw16: Integer
    Output: Integer
    Body: {
        ReturnValue(ShiftLeft(raw16, 16))
    }
}

// Promote Q8.8 → Q32.32: raw << 24
Function.JSRT__Promote_8_8_to_32_32 {
    Input: raw8: Integer
    Output: Integer
    Body: {
        ReturnValue(ShiftLeft(raw8, 24))
    }
}
```

#### Arithmetic with Progressive Widening

```ailang
// JSRT_Add — rewritten with fixed-point awareness
Function.JSRT_Add {
    Input: a: Address
    Input: b: Address
    Output: Address
    Body: {
        save_a = a
        save_b = b
        IfCondition EqualTo(save_a, 0) ThenBlock: { save_a = JSRTState.undef_val }
        IfCondition EqualTo(save_b, 0) ThenBlock: { save_b = JSRTState.undef_val }
        a_type = Dereference(save_a)
        b_type = Dereference(save_b)

        // String concatenation (unchanged)
        is_str = 0
        IfCondition EqualTo(a_type, JSType.STRING) ThenBlock: { is_str = 1 }
        IfCondition EqualTo(b_type, JSType.STRING) ThenBlock: { is_str = 1 }
        IfCondition EqualTo(is_str, 1) ThenBlock: {
            // ... existing string concat path ...
        }

        // Normalize both to numbers
        a_raw = JSRT__GetAsRaw(a_type, Dereference(Add(save_a, 8)))
        b_raw = JSRT__GetAsRaw(b_type, Dereference(Add(save_b, 8)))
        a_fmt = JSRT__GetFormat(a_type)
        b_fmt = JSRT__GetFormat(b_type)

        // Widen to common format
        // ... format negotiation logic ...
        // ... add in common format ...
        // ... check overflow, promote if needed ...
    }
}
```

The implementation details for the arithmetic dispatch are significant. Here's
the core approach:

**Format negotiation** finds the wider of the two formats. The narrower is
promoted (left-shifted), then integer addition is performed in the wider format.

**Overflow check** verifies that the result fits in the wider format. If not,
both are promoted again and the operation is retried.

#### ToNumber Coercion

`JSRT_ToNumber` currently returns a raw integer. With fixed-point, it needs to
return a fixed-point value. Options:
1. Return as FIXED_32_32 (widest, always fits)
2. Return format-preserving if already fixed
3. Add a new `JSRT_ToFixed` that returns both format and raw value

#### String Conversion

`JSRT__IntToStr` → needs a fixed-point-aware `JSRT__FixedToStr` that:
1. Extracts the integer part: `raw >> frac_bits`
2. Extracts the fraction part: `raw & frac_mask`
3. Converts fraction to decimal digits by repeated multiply-by-10 and divide

#### Comparison

Strict equality already compares payloads with `Equal`. This works for
fixed-point provided both values are the same format. For cross-format
comparison, promote to common format first.

***

## Interop with Existing Code

### DOM/Layout Engine

The layout engine (`Library.HTMLLayout.ailang`) uses integer pixel values.
Currently these come from JSRT_ToNumber coercion of JS values. With fixed-point,
CSS values like `width: 100.5` can be represented precisely.

The bridge (`Library.JSBridge.ailang`) converts JS values to layout coordinates
via `JSRT_ToNumber`. This should be updated to `JSRT_ToFixed` and then round
or truncate to integer pixels as needed.

### Math Builtins

`Math.floor`, `Math.ceil`, `Math.round` become trivial:
- `floor`: `raw & ~frac_mask`
- `ceil`: `(raw + frac_mask) & ~frac_mask`
- `round`: `(raw + (frac_mask >> 1)) & ~frac_mask`

These are single-cycle bitwise operations. Compare to IEEE 754 where `floor`
requires checking the exponent, extracting the mantissa, shifting by a
variable amount, and reassembling — ~20-30 cycles.

### parseInt / parseFloat

- `parseInt`: Extract integer part: `raw >> frac_bits`
- `parseFloat`: Return the fixed-point value as-is (it already IS a float-like
  representation)

***

## Performance Analysis

### Integer Operations Are Fast

| Operation | x86-64 Latency | Notes |
|-----------|----------------|-------|
| ADD/SUB (int) | 1 cycle | Single uop |
| MUL (64-bit) | 3-4 cycles | IMUL reg,reg |
| DIV (64-bit) | 20-80 cycles | IDIV (avoid when possible) |
| SHL/SHR (fixed) | 1 cycle | Shift by immediate |
| SHL/SHR (variable) | 1-2 cycles | SHL reg,cl |
| CMP + Jcc | 1 cycle | Fused compare-and-branch |

| Operation | SSE2 Latency | Notes |
|-----------|-------------|-------|
| ADDSD | 3-4 cycles | Scalar double add |
| MULSD | 4-5 cycles | Scalar double multiply |
| DIVSD | 13-32 cycles | Scalar double divide |
| CVTTSD2SI | 3-6 cycles | Double to integer |
| CVTSI2SD | 4-5 cycles | Integer to double |

**Fixed-point addition = 1 cycle. SSE2 double addition = 3-4 cycles.**

For the common case (small DOM values in Q8.8 or Q16.16), we're getting
3-4× speedup on arithmetic operations.

### No Shift Penalty for Same-Format Operations

Two Q8.8 values added together: just `ADD rax, rbx`. No shift, no alignment,
no normalization. This is the "avoid dumb shift like floats" that Sean
mentioned.

The only time shifts occur is during format promotion (cross-format operations
or overflow), and those are fixed-amount shifts (<< 8, << 16), not variable
barrel shifts like IEEE 754 mantissa alignment.

### Memory Density

A Q8.8 value still uses 16 bytes (the JSValue struct). But the payload is
only 16 meaningful bits. In the future, a packed value array could store
multiple Q8.8 values per cache line — but that's a separate optimization.

***

## Implementation Phases

### Phase 1: JSRuntime Core

1. Add `JSType.FIXED_8_8`, `FIXED_16_16`, `FIXED_32_32` to FixedPool
2. Add `JSRT_CreateFixed_8_8/16_16/32_32`
3. Rewrite `JSRT_Add` with format-aware dispatch
4. Rewrite `JSRT_Sub`, `JSRT_Mul`, `JSRT_Div`, `JSRT_Neg`
5. Add format promotion helpers
6. Add overflow detection
7. Rewrite `JSRT__IntToStr` → `JSRT__FixedToStr`
8. Update `JSRT_ToNumber` to handle fixed types
9. Update comparison operators for cross-format equality

### Phase 2: Parser + Compiler

1. Add `JSParse__ParseFixed(ptr, len)` — parse decimal string to fixed-point
2. Store format in `N_OP` field of NUMBER_LIT AST nodes
3. Add `JSComp__AddFixed(fmt, raw)` to compiler
4. Update `JSComp__CompileExpr` NUMBER_LIT case
5. Update `JSVM__LoadConst` for types 8, 9, 10

### Phase 3: JSVM + Integration

1. No bytecode changes needed (arithmetic opcodes unchanged)
2. Test with integer values first (backward compat via JSType.NUMBER=3)
3. Test with decimal literals
4. Update JSBridge for fixed-point → pixel conversion
5. Test DOM layout with fractional values

### Phase 4: Optimization

1. Add inline fast paths for common format pairs (Q8.8+Q8.8, Q16.16+Q16.16)
2. Consider packed value arrays for homogeneous fixed-point data
3. Profile vs. IEEE 754 for the Test262 numeric tests

***

## Comparison: Fixed-Point vs IEEE 754

| Property | Fixed-Point (proposed) | IEEE 754 Double |
|----------|----------------------|-----------------|
| Addition latency | 1 cycle | 3-4 cycles |
| Multiplication latency | 3-4 cycles (int) | 4-5 cycles (SSE) |
| Division latency | 20-80 cycles (int) | 13-32 cycles (SSE) |
| 0.1 + 0.2 | Exactly 0.3 | 0.30000000000000004 |
| Range (widest) | ±2.1 billion | ±1.8×10^308 |
| Precision (small nums) | 1/256 or 1/65536 | ~15 decimal digits |
| Rounding | Truncation (deterministic) | Round-to-nearest-even |
| NaN handling | None needed | Extra checks everywhere |
| Infinity | None needed | Extra checks everywhere |
| Subnormals | Never | Yes (slow path) |
| Format detection | 1 integer compare | Check exponent field |
| Shift amount | Constant (0, 8, 16) | Variable (0-52) |

The tradeoff is clear: fixed-point gives up dynamic range (you can't represent
1e308) in exchange for simplicity, speed, and exactness. For a browser JS engine
dealing with DOM values, CSS, and UI math, the dynamic range of double is
wasteful and the precision issues are harmful.

For scientific computing (which won't run in this browser), IEEE 754's range
matters. For the web platform, it doesn't.

***

## Open Questions

1. **What about `Infinity` and `NaN`?** These are IEEE 754 concepts that don't
   exist in fixed-point. Division by zero returns 0 (current behavior) or
   could return a sentinel value. `Infinity` in JS typically comes from
   `1/0` — we can keep the current behavior (return 0) and add explicit
   `Number.POSITIVE_INFINITY` as a special constant if needed.

2. **What about very large integers?** `Number.MAX_SAFE_INTEGER` is 2^53-1.
   Our Q32.32 max is ~2.1B. For larger integers, we'd need Q48.16 or a
   separate bigint type. This is future work.

3. **What about `Math.random()`?** Returns a value in [0, 1). In Q32.32, this
   is a random integer in [0, 2^32-1] stored as FIXED_32_32. Very natural.

4. **Should `JSType.NUMBER` (=3) be kept?** Yes, for backward compatibility
   with existing compiled bytecode and the constant pool. New code will emit
   FIXED_8_8/16_16/32_32. `JSRT_ToNumber` and arithmetic functions should
   handle type=3 by treating it as FIXED_32_32 with fraction=0 (or by
   wrapping it).

5. **Format selection heuristic:** Should we always choose the smallest format
   that fits, or should we prefer Q16.16 as the default and only use Q8.8 for
   values that are provably small? Q16.16 has better precision and still uses
   only 32 bits.

***

## Code Generator Primitives Needed

For the AILang → x86-64 code generator, the fixed-point arithmetic primitives
are:

| Primitive | x86-64 | Description |
|-----------|--------|-------------|
| `FixedAdd(a, b, fmt)` | ADD reg, reg | Integer add (format-agnostic) |
| `FixedSub(a, b, fmt)` | SUB reg, reg | Integer sub |
| `FixedMul(a, b, fmt)` | IMUL + SAR | Multiply then arithmetic shift right |
| `FixedDiv(a, b, fmt)` | SHL + IDIV | Shift left then integer divide |
| `FixedPromote(val, from, to)` | SHL imm | Left shift by fixed amount |
| `FixedTruncate(val, from, to)` | SAR imm | Right shift by fixed amount |
| `FixedExtractInt(val, fmt)` | SAR imm | Shift right to get integer part |
| `FixedExtractFrac(val, fmt)` | AND mask | Mask to get fraction part |
| `FixedFromInt(n, fmt)` | SHL imm | Left shift integer to fixed-point |

These are all single x86-64 instructions or short sequences. No SSE registers
needed. No XMM save/restore on function calls. No FPU control word manipulation.

The code generator already has `Emit_AddRegReg`, `Emit_SubRaxImm8`, etc. in
`CEmitCoreArch.ailang`. Fixed-point arithmetic reuses these integer primitives
directly.

***

## References

- `Librarys/Browser/Library.JSRuntime.ailang` — Current value system
- `Librarys/Browser/Library.JSVM.ailang` — Bytecode interpreter
- `Librarys/Browser/Library.JSCompiler.ailang` — AST → bytecode
- `Librarys/Browser/Library.JSParser.ailang` — Token stream → AST
- `Librarys/Browser/Library.JSLexer.ailang` — Source → tokens
- `Librarys/Compiler/CodeEmit/X86/Library.CEmitX86Arith.ailang` — x86 arithmetic emission
- `Librarys/Compiler/CodeEmit/Library.CEmitCoreArch.ailang` — ISA dispatch
- `Librarys/Compiler/Compile/FPU/` — Existing FPU module (SSE2 floats for AILang itself)
