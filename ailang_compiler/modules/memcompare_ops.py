# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/modules/memcompare_ops.py
"""
Memory Comparison Primitives for AILANG
Provides optimized memory operations for pattern matching and string comparison.
MemChr uses SSE2 SIMD instructions for 16-byte parallel processing.
MemCompare uses scalar byte-by-byte (SSE2 optimization more complex for compare).
"""

class MemCompareOps:
    """
    Memory comparison operations that compile to optimized x86-64 assembly.
    - MemCompare: Scalar byte-by-byte comparison (simple and reliable)
    - MemChr: SSE2 SIMD for 16-byte parallel search (up to 16x faster!)
    """
    
    def __init__(self, compiler):
        self.compiler = compiler
        self.asm = compiler.asm  # Reference to X64Assembler
        
    def compile_memcompare(self, args):
        """
        MemCompare(addr1, addr2, length) -> Integer

        Compares two memory regions using an SSE2-optimized loop for performance.
        Returns: 0 if equal, 1 if different

        SSE2 Strategy for memcmp:
        1. Process 16 bytes at a time with MOVDQU (unaligned loads)
        2. Compare with PCMPEQB (all 16 bytes in parallel)
        3. Check if all bytes matched with PMOVMSKB
        4. Early exit on first difference
        5. Scalar fallback for remaining bytes < 16

        CRITICAL: Result left in RAX, returns True (like SystemCall pattern)
        """
        if len(args) != 3:
            raise ValueError("MemCompare requires exactly 3 arguments")
        
        addr1, addr2, length = args
        
        print("DEBUG: Compiling MemCompare with SSE2 optimization")
        
        # Labels for control flow
        sse2_loop = self.asm.create_label()
        check_scalar = self.asm.create_label()
        scalar_loop = self.asm.create_label()
        equal_label = self.asm.create_label()
        not_equal_label = self.asm.create_label()
        done_label = self.asm.create_label()
        
        # Evaluate all arguments and push to stack
        self.compiler.compile_expression(length)
        self.asm.emit_push_rax()
        
        self.compiler.compile_expression(addr2)
        self.asm.emit_push_rax()
        
        self.compiler.compile_expression(addr1)
        self.asm.emit_push_rax()
        
        # Pop into working registers
        self.asm.emit_bytes(0x5E)  # POP RSI (addr1)
        self.asm.emit_bytes(0x5F)  # POP RDI (addr2)
        self.asm.emit_pop_rcx()    # POP RCX (length)
        
        # Check for zero/negative length
        self.asm.emit_test_r64_r64('rcx', 'rcx')
        self.asm.emit_jump_to_label(equal_label, "JLE")
        
        # === SSE2 MAIN LOOP: Process 16 bytes at a time ===
        self.asm.mark_label(sse2_loop)
        
        # Check if we have at least 16 bytes left
        self.asm.emit_bytes(0x48, 0x83, 0xF9, 0x10)  # CMP RCX, 16
        self.asm.emit_jump_to_label(check_scalar, "JB")  # Jump if Below
        
        # Load 16 bytes from addr1: MOVDQU XMM0, [RSI]
        self.asm.emit_bytes(0xF3, 0x0F, 0x6F, 0x06)
        
        # Load 16 bytes from addr2: MOVDQU XMM1, [RDI]
        self.asm.emit_bytes(0xF3, 0x0F, 0x6F, 0x0F)
        
        # Compare all 16 bytes: PCMPEQB XMM0, XMM1
        # Result: 0xFF where equal, 0x00 where different
        self.asm.emit_bytes(0x66, 0x0F, 0x74, 0xC1)
        
        # Extract comparison mask: PMOVMSKB EAX, XMM0
        # If all bytes equal, EAX = 0xFFFF (all bits set)
        # If any byte differs, at least one bit will be 0
        self.asm.emit_bytes(0x66, 0x0F, 0xD7, 0xC0)
        
        # Check if all 16 bytes matched: CMP EAX, 0xFFFF
        self.asm.emit_bytes(0x3D, 0xFF, 0xFF, 0x00, 0x00)  # CMP EAX, 0xFFFF
        self.asm.emit_jump_to_label(not_equal_label, "JNE")  # Jump if Not Equal
        
        # All 16 bytes matched, advance to next chunk
        self.asm.emit_bytes(0x48, 0x83, 0xC6, 0x10)  # ADD RSI, 16
        self.asm.emit_bytes(0x48, 0x83, 0xC7, 0x10)  # ADD RDI, 16
        self.asm.emit_bytes(0x48, 0x83, 0xE9, 0x10)  # SUB RCX, 16
        self.asm.emit_jump_to_label(sse2_loop, "JMP")
        
        # === SCALAR LOOP: Handle remaining bytes (< 16) ===
        self.asm.mark_label(check_scalar)
        self.asm.emit_test_r64_r64('rcx', 'rcx')
        self.asm.emit_jump_to_label(equal_label, "JZ")
        
        print("DEBUG: Emitting scalar fallback for MemCompare")
        
        self.asm.mark_label(scalar_loop)
        
        # Load byte from [RSI]: MOVZX EAX, BYTE [RSI]
        self.asm.emit_bytes(0x0F, 0xB6, 0x06)
        
        # Load byte from [RDI]: MOVZX EDX, BYTE [RDI]
        self.asm.emit_bytes(0x0F, 0xB6, 0x17)
        
        # Compare: CMP AL, DL
        self.asm.emit_bytes(0x38, 0xD0)
        
        # Jump if NOT equal
        self.asm.emit_jump_to_label(not_equal_label, "JNE")
        
        # Equal so far, advance pointers
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_bytes(0x48, 0xFF, 0xC9)  # DEC RCX
        self.asm.emit_jump_to_label(scalar_loop, "JNZ")
        
        # === ALL BYTES MATCHED ===
        self.asm.mark_label(equal_label)
        self.asm.emit_bytes(0x48, 0x31, 0xC0)  # XOR RAX, RAX (result = 0)
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        # === BYTES DIFFER ===
        self.asm.mark_label(not_equal_label)
        self.asm.emit_bytes(0x48, 0xC7, 0xC0, 0x01, 0x00, 0x00, 0x00)  # MOV RAX, 1
        
        # === DONE ===
        self.asm.mark_label(done_label)
        print("DEBUG: MemCompare SSE2 compiled, result in RAX")
        return True  # Signal to compiler that result is in RAX
                
    def compile_memchr(self, args):
        """
        MemChr(addr, byte_value, length) -> Integer
        
        SSE2-optimized byte search. Returns position or -1.
        """
        if len(args) != 3:
            raise ValueError("MemChr requires exactly 3 arguments: (addr, byte, length)")
        
        addr, byte_val, length = args
        
        print("DEBUG: Compiling MemChr with SSE2 SIMD optimization")
        
        # Generate unique labels
        not_found_label = self.asm.create_label()
        done_label = self.asm.create_label()
        sse2_loop = self.asm.create_label()
        found_sse2 = self.asm.create_label()
        check_scalar = self.asm.create_label()
        scalar_loop = self.asm.create_label()
        found_scalar = self.asm.create_label()
        
        # Push args to stack
        self.compiler.compile_expression(length)
        self.asm.emit_push_rax()
        
        self.compiler.compile_expression(byte_val)
        self.asm.emit_push_rax()
        
        self.compiler.compile_expression(addr)
        self.asm.emit_push_rax()
        
        # Pop into registers
        self.asm.emit_bytes(0x5F)  # POP RDI (address)
        self.asm.emit_pop_rax()     # POP RAX (byte value)
        self.asm.emit_pop_rcx()     # POP RCX (length)
        
        # Check for zero/negative length
        self.asm.emit_test_r64_r64('rcx', 'rcx')
        self.asm.emit_jump_to_label(not_found_label, "JLE")
        
        # Save original address in R8
        self.asm.emit_bytes(0x49, 0x89, 0xF8)  # MOV R8, RDI
        
        # CRITICAL FIX: Save search byte in R9 before we clobber AL
        self.asm.emit_bytes(0x41, 0x89, 0xC1)  # MOV R9D, EAX (save byte in R9)
        
        # Broadcast byte to XMM0
        self.asm.emit_bytes(0x66, 0x0F, 0x6E, 0xC0)  # MOVD XMM0, EAX
        self.asm.emit_bytes(0x66, 0x0F, 0x60, 0xC0)  # PUNPCKLBW XMM0, XMM0
        self.asm.emit_bytes(0xF2, 0x0F, 0x70, 0xC0, 0x00)  # PSHUFLW XMM0, XMM0, 0
        self.asm.emit_bytes(0x66, 0x0F, 0x70, 0xC0, 0x00)  # PSHUFD XMM0, XMM0, 0
        
        # SSE2 loop
        self.asm.mark_label(sse2_loop)
        self.asm.emit_bytes(0x48, 0x83, 0xF9, 0x10)  # CMP RCX, 16
        self.asm.emit_jump_to_label(check_scalar, "JB")
        
        self.asm.emit_bytes(0xF3, 0x0F, 0x6F, 0x0F)  # MOVDQU XMM1, [RDI]
        self.asm.emit_bytes(0x66, 0x0F, 0x74, 0xC8)  # PCMPEQB XMM1, XMM0
        self.asm.emit_bytes(0x66, 0x0F, 0xD7, 0xC1)  # PMOVMSKB EAX, XMM1 (clobbers AL!)
        
        self.asm.emit_bytes(0x85, 0xC0)  # TEST EAX, EAX
        self.asm.emit_jump_to_label(found_sse2, "JNZ")
        
        self.asm.emit_bytes(0x48, 0x83, 0xC7, 0x10)  # ADD RDI, 16
        self.asm.emit_bytes(0x48, 0x83, 0xE9, 0x10)  # SUB RCX, 16
        self.asm.emit_jump_to_label(sse2_loop, "JMP")
        
        # Found in SSE2
        self.asm.mark_label(found_sse2)
        self.asm.emit_bytes(0x0F, 0xBC, 0xD0)  # BSF EDX, EAX
        self.asm.emit_bytes(0x48, 0x89, 0xF8)  # MOV RAX, RDI
        self.asm.emit_bytes(0x4C, 0x29, 0xC0)  # SUB RAX, R8
        self.asm.emit_bytes(0x48, 0x01, 0xD0)  # ADD RAX, RDX
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        # Scalar fallback - RESTORE search byte from R9!
        self.asm.mark_label(check_scalar)
        self.asm.emit_bytes(0x44, 0x89, 0xC8)  # MOV EAX, R9D (restore search byte)
        self.asm.emit_test_r64_r64('rcx', 'rcx')
        self.asm.emit_jump_to_label(not_found_label, "JZ")
        
        self.asm.mark_label(scalar_loop)
        self.asm.emit_bytes(0x0F, 0xB6, 0x17)  # MOVZX EDX, BYTE [RDI]
        self.asm.emit_bytes(0x38, 0xC2)  # CMP DL, AL (now AL has the right value!)
        self.asm.emit_jump_to_label(found_scalar, "JE")
        
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_bytes(0x48, 0xFF, 0xC9)  # DEC RCX
        self.asm.emit_jump_to_label(scalar_loop, "JNZ")
        
        # Not found
        self.asm.mark_label(not_found_label)
        self.asm.emit_mov_rax_imm64(0xFFFFFFFFFFFFFFFF)
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        # Found in scalar
        self.asm.mark_label(found_scalar)
        self.asm.emit_bytes(0x48, 0x89, 0xF8)  # MOV RAX, RDI
        self.asm.emit_bytes(0x4C, 0x29, 0xC0)  # SUB RAX, R8
        
        # Done
        self.asm.mark_label(done_label)
        print("DEBUG: MemChr compiled, result in RAX")
        return True
    
    def compile_memcopy(self, args):
        """
        MemCopy(dest, src, length) -> Integer (returns length copied)
        
        Fast bulk memory copy using SSE2 for 16-byte chunks.
        Assumes non-overlapping regions (like standard memcpy).
        
        Strategy:
        1. Copy 16 bytes at a time with MOVDQU (unaligned loads/stores)
        2. Fall back to byte-by-byte for remaining bytes < 16
        3. Return total bytes copied
        
        This is CRITICAL for grep performance - eliminates byte-by-byte loops!
        
        Performance: 4-10x faster than manual loops for buffers > 64 bytes
        
        CRITICAL: Result left in RAX, returns True
        """
        if len(args) != 3:
            raise ValueError("MemCopy requires exactly 3 arguments")
        
        dest, src, length = args
        
        print("DEBUG: Compiling MemCopy with SSE2")
        
        # Labels
        sse2_loop = self.asm.create_label()
        check_scalar = self.asm.create_label()
        scalar_loop = self.asm.create_label()
        done_label = self.asm.create_label()
        
        # Evaluate all arguments and push to stack
        self.compiler.compile_expression(length)
        self.asm.emit_push_rax()
        
        self.compiler.compile_expression(src)
        self.asm.emit_push_rax()
        
        self.compiler.compile_expression(dest)
        self.asm.emit_push_rax()
        
        # Pop into working registers
        self.asm.emit_bytes(0x5F)  # POP RDI (dest)
        self.asm.emit_bytes(0x5E)  # POP RSI (src)
        self.asm.emit_pop_rcx()    # POP RCX (length)
        
        # Save original length in R8 for return value
        self.asm.emit_bytes(0x49, 0x89, 0xC8)  # MOV R8, RCX
        
        # Check for zero length
        self.asm.emit_test_r64_r64('rcx', 'rcx')
        self.asm.emit_jump_to_label(done_label, "JZ")
        
        # === SSE2 MAIN LOOP: Copy 16 bytes at a time ===
        self.asm.mark_label(sse2_loop)
        
        # Check if we have at least 16 bytes left
        self.asm.emit_bytes(0x48, 0x83, 0xF9, 0x10)  # CMP RCX, 16
        self.asm.emit_jump_to_label(check_scalar, "JB")
        
        # Load 16 bytes: MOVDQU XMM0, [RSI]
        self.asm.emit_bytes(0xF3, 0x0F, 0x6F, 0x06)
        
        # Store 16 bytes: MOVDQU [RDI], XMM0
        self.asm.emit_bytes(0xF3, 0x0F, 0x7F, 0x07)
        
        # Advance pointers and decrement counter
        self.asm.emit_bytes(0x48, 0x83, 0xC6, 0x10)  # ADD RSI, 16
        self.asm.emit_bytes(0x48, 0x83, 0xC7, 0x10)  # ADD RDI, 16
        self.asm.emit_bytes(0x48, 0x83, 0xE9, 0x10)  # SUB RCX, 16
        self.asm.emit_jump_to_label(sse2_loop, "JMP")
        
        # === SCALAR LOOP: Copy remaining bytes (< 16) ===
        self.asm.mark_label(check_scalar)
        self.asm.emit_test_r64_r64('rcx', 'rcx')
        self.asm.emit_jump_to_label(done_label, "JZ")
        
        print("DEBUG: Emitting scalar fallback for MemCopy")
        
        self.asm.mark_label(scalar_loop)
        
        # Load byte: MOVZX EAX, BYTE [RSI]
        self.asm.emit_bytes(0x0F, 0xB6, 0x06)
        
        # Store byte: MOV BYTE [RDI], AL
        self.asm.emit_bytes(0x88, 0x07)
        
        # Advance pointers
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_bytes(0x48, 0xFF, 0xC9)  # DEC RCX
        self.asm.emit_jump_to_label(scalar_loop, "JNZ")
        
        # === DONE ===
        self.asm.mark_label(done_label)
        # Return original length
        self.asm.emit_bytes(0x4C, 0x89, 0xC0)  # MOV RAX, R8
        
        print("DEBUG: MemCopy SSE2 compiled, result in RAX")
        return True
        
    def compile_memfind(self, args):
        """
        MemFind(haystack, haystack_len, needle, needle_len) -> Integer
        
        Not yet implemented - use MemCompare in a loop instead.
        
        Future: Could use SSE2 for the first byte + MemCompare for rest.
        This is how real-world strstr() implementations work.
        """
        raise NotImplementedError(
            "MemFind not yet implemented. "
            "Use MemCompare in a loop for pattern matching."
        )