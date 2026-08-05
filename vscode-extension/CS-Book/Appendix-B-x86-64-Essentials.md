# Appendix B: x86-64 Essentials

This appendix gives a minimal, practical introduction to the parts of x86-64 assembly and architecture that you need to read compiler output and understand what AILang programs actually do at the machine level. It is not a full assembly tutorial.

## Registers (General Purpose)

Modern x86-64 has 16 general-purpose 64-bit registers:

- `RAX` — Accumulator, often used for return values and arithmetic.
- `RBX` — Base register, sometimes used for addressing.
- `RCX` — Counter, used in loops and certain instructions.
- `RDX` — Data register, often pairs with RAX.
- `RSI` — Source Index, used in string/memory operations.
- `RDI` — Destination Index, used in string/memory operations.
- `RBP` — Base Pointer (frame pointer). Points to the current stack frame.
- `RSP` — Stack Pointer. Points to the top of the current stack.
- `R8`–`R15` — Additional general-purpose registers (introduced in x86-64).

Lower 32/16/8-bit portions can be accessed (e.g., `EAX`, `AX`, `AL`).

## Important Instructions

- `MOV dest, src` — Copy data (register ← register, memory ← register, etc.).
- `ADD dest, src` — dest = dest + src
- `SUB dest, src` — dest = dest - src
- `IMUL dest, src` — Signed multiply
- `IDIV src` — Signed divide (uses RDX:RAX pair)
- `CMP a, b` — Compare (sets flags, like SUB but discards result)
- `TEST a, b` — Bitwise AND that only sets flags
- `JMP label` — Unconditional jump
- `JE / JNE / JG / JGE / JL / JLE` — Conditional jumps based on flags from CMP/TEST
- `CALL label` — Call subroutine (pushes return address)
- `RET` — Return from subroutine (pops return address)
- `PUSH src` / `POP dest` — Stack operations
- `SYSCALL` — Make a system call (Linux x86-64 ABI)
- `INT3` — Software breakpoint (used by debuggers)

## Calling Convention (System V AMD64 ABI — Linux/macOS)

- First 6 integer/pointer arguments: RDI, RSI, RDX, RCX, R8, R9
- Return value: RAX (and RDX for 128-bit results)
- Caller-saved: RAX, RCX, RDX, RSI, RDI, R8–R11
- Callee-saved: RBX, RBP, R12–R15
- Stack must be 16-byte aligned before a CALL

## Stack Frame Basics

Typical function prologue:
```asm
push rbp
mov  rbp, rsp
sub  rsp, N     ; allocate space for locals
```

Epilogue:
```asm
mov rsp, rbp
pop rbp
ret
```

Local variables are usually at negative offsets from RBP (e.g., `[rbp-8]`).

## Reading Compiler Output

When you see AILang compiler output (with `-d` or verbose flags), look for:
- MOVs that implement assignment and parameter passing
- CMP + conditional JMP for IfCondition / WhileLoop conditions
- CALL / RET for function calls
- LEA for address calculations (common for array indexing and pointer arithmetic)

The AILang compiler is deliberately verbose in its unoptimized output so you can see the direct mapping from source constructs to these instructions. The optimizer then removes obvious redundancy (e.g., unnecessary push/pop pairs for simple arithmetic).

For a deeper reference, consult the Intel or AMD x86-64 Architecture manuals (Software Developer’s Manuals). For day-to-day reading of compiler output, the above is usually sufficient.