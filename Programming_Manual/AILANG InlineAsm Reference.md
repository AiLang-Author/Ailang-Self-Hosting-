# AILang InlineAsm Reference

InlineAsm embeds raw x86-64 machine instructions directly into compiled output.
Two forms: **hex bytes** (legacy) and **mnemonic** (new, requires `ailang-IASM.x`).

---

## Syntax

```
// Statement form — emits bytes, no return value captured
InlineAsm["NOP"]
InlineAsm["90"]

// Expression form — emits bytes, captures RAX after execution
result = InlineAsm["POPCNT rax, rax"]
result = InlineAsm["48 ff c0"]
```

The first non-whitespace character determines the path:
- **Letter (A-Z / a-z)** → mnemonic path (`X86Enc_Assemble`)
- **Anything else** → raw hex path

---

## Mnemonic Syntax

```
InlineAsm["MNEMONIC [op1 [, op2 [, op3]]]"]
```

- Mnemonic is case-insensitive (`mov`, `MOV`, `Mov` all work)
- Register names are case-insensitive (`rax`, `RAX`)
- Operands separated by commas
- Immediate values are decimal integers

```ailang
InlineAsm["NOP"]
InlineAsm["PUSH rax"]
InlineAsm["POP  rax"]
InlineAsm["MOV  rax, 42"]
InlineAsm["IMUL rax, rax, 33"]
InlineAsm["POPCNT rax, rax"]
InlineAsm["BSF  rax, rax"]
InlineAsm["XOR  rax, rax"]
InlineAsm["NEG  rax"]
InlineAsm["NOT  rax"]
```

---

## Hex Byte Syntax

Space-separated byte pairs in hex. Case-insensitive hex digits.

```ailang
InlineAsm["90"]                          // NOP
InlineAsm["48 ff c0"]                    // INC RAX
InlineAsm["48 ff c8"]                    // DEC RAX
InlineAsm["48 69 c0 21 00 00 00"]        // IMUL RAX, RAX, 33
```

---

## Capturing Results

InlineAsm executes inline — it does **not** automatically update local variables.
To capture the result of a transformation, use expression form **after** the setup:

```ailang
// CORRECT — capture after the instruction that produces the value
InlineAsm["MOV rax, 181"]
result = InlineAsm["POPCNT rax, rax"]   // result = 5
ReturnValue(result)

// WRONG — result captures the MOV value, not the POPCNT value
result = InlineAsm["MOV rax, 181"]      // result = 181
InlineAsm["POPCNT rax, rax"]            // RAX = 5, but result is stale
ReturnValue(result)                     // returns 181
```

---

## Immediate Widening

The encoder automatically widens small immediates if the narrow form has no
opcode entry (e.g. x86-64 has no `MOV r64, imm8` — it promotes to `imm32`):

```
imm8  -> imm32 -> imm64  (tried in order until a match is found)
imm16 -> imm32 -> imm64
```

This is transparent — `MOV rax, 5` works even though 5 fits in a byte.

---

## Register Names

| 64-bit | 32-bit | Notes              |
|--------|--------|--------------------|
| rax    | eax    | return value / acc |
| rbx    | ebx    |                    |
| rcx    | ecx    | loop counter       |
| rdx    | edx    |                    |
| rsi    | esi    |                    |
| rdi    | edi    | first arg          |
| rsp    | esp    | stack pointer      |
| rbp    | ebp    | frame pointer      |
| r8–r15 |        | extended regs      |

XMM/YMM/ZMM registers supported for SSE/AVX/AVX-512 instructions.

---

## Notes

- InlineAsm does not participate in AILang's register allocator — it is the
  programmer's responsibility not to clobber registers the compiler is using.
- PUSH/POP pairs are safe for temporary register use.
- The full x86-64 ISA (10,363 forms) is available including SSE, AVX, AVX-512.
- Source: `Librarys/Compiler/CodeEmit/X86/Library.CEmitX86Enc.ailang` (generated).
