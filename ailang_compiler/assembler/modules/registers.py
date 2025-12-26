# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/registers.py
"""Register-to-register move operations and immediate loads"""

import struct

class RegisterOperations:
    """Register movement and immediate loading operations"""
    
    # === IMMEDIATE LOADS TO REGISTERS ===
    
    
    def emit_mov_rax_imm64(self, value: int):
        """MOV RAX, imm64 - ENHANCED FOR LARGE NUMBERS"""
        self.emit_bytes(0x48, 0xB8)
        
        # ENHANCED ARITHMETIC: Handle large numbers
        if value > 18446744073709551615:  # 2^64 - 1
            truncated_value = value % (2**64)
            print(f"DEBUG: LARGE NUMBER TRUNCATED: {value} -> {truncated_value}")
            self.emit_bytes(*struct.pack('<Q', truncated_value))
        elif value < 0 and value < -9223372036854775808:  # 2^63
            truncated_value = value % (2**64)
            print(f"DEBUG: LARGE NEGATIVE TRUNCATED: {value} -> {truncated_value}")
            self.emit_bytes(*struct.pack('<Q', truncated_value))
        else:
            try:
                self.emit_bytes(*struct.pack('<Q', value))
            except struct.error as e:
                print(f"DEBUG: Struct pack failed for {value}, using modulo fallback")
                safe_value = value % (2**64)
                self.emit_bytes(*struct.pack('<Q', safe_value))
        
        print(f"DEBUG: MOV RAX, {value}")
    
    def emit_mov_rbx_imm64(self, value: int):
        """MOV RBX, imm64"""
        self.emit_bytes(0x48, 0xBB)
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_bytes(*struct.pack('<Q', value))
        print(f"DEBUG: MOV RBX, {value}")
    
    def emit_mov_rcx_imm64(self, value: int):
        """MOV RCX, imm64"""
        self.emit_bytes(0x48, 0xB9)
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_bytes(*struct.pack('<Q', value))
        print(f"DEBUG: MOV RCX, {value}")
    
    def emit_mov_rdx_imm64(self, value: int):
        """MOV RDX, imm64"""
        self.emit_bytes(0x48, 0xBA)
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_bytes(*struct.pack('<Q', value))
        print(f"DEBUG: MOV RDX, {value}")
    
    def emit_mov_rsi_imm64(self, value: int):
        """MOV RSI, imm64"""
        self.emit_bytes(0x48, 0xBE)
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_bytes(*struct.pack('<Q', value))
        print(f"DEBUG: MOV RSI, {value}")
    
    def emit_mov_rdi_imm64(self, value: int):
        """MOV RDI, imm64"""
        self.emit_bytes(0x48, 0xBF)
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_bytes(*struct.pack('<Q', value))
        print(f"DEBUG: MOV RDI, {value}")
    
    def emit_mov_r8_imm64(self, value: int):
        """MOV R8, imm64"""
        self.emit_bytes(0x49, 0xB8)
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_bytes(*struct.pack('<Q', value))
        print(f"DEBUG: MOV R8, {value}")
    
    def emit_mov_r9_imm64(self, value: int):
        """MOV R9, imm64"""
        self.emit_bytes(0x49, 0xB9)
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_bytes(*struct.pack('<Q', value))
        print(f"DEBUG: MOV R9, {value}")
    
    def emit_mov_r10_imm64(self, value: int):
        """MOV R10, imm64"""
        self.emit_bytes(0x49, 0xBA)
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_bytes(*struct.pack('<Q', value))
        print(f"DEBUG: MOV R10, {value}")
    
    def emit_mov_r11_imm64(self, value: int):
        """MOV R11, imm64"""
        self.emit_bytes(0x49, 0xBB)
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_bytes(*struct.pack('<Q', value))
        print(f"DEBUG: MOV R11, {value}")
    # === REGISTER-TO-REGISTER MOVES ===
    
    
    
    
    def emit_mov_rax_rbx(self):
        """MOV RAX, RBX"""
        self.emit_bytes(0x48, 0x89, 0xD8)
    
    def emit_mov_rbx_rax(self):
        """MOV RBX, RAX"""
        self.emit_bytes(0x48, 0x89, 0xC3)
        print("DEBUG: MOV RBX, RAX")
    
    def emit_mov_rcx_rax(self):
        """MOV RCX, RAX"""
        self.emit_bytes(0x48, 0x89, 0xC1)
        print("DEBUG: MOV RCX, RAX")
    
    def emit_mov_rdx_rax(self):
        """MOV RDX, RAX"""
        self.emit_bytes(0x48, 0x89, 0xC2)
    
    def emit_mov_rdi_rax(self):
        """MOV RDI, RAX"""
        self.emit_bytes(0x48, 0x89, 0xC7)
        print("DEBUG: MOV RDI, RAX")
    
    def emit_mov_rsi_rax(self):
        """MOV RSI, RAX"""
        self.emit_bytes(0x48, 0x89, 0xC6)
        print("DEBUG: MOV RSI, RAX")
    
    def emit_mov_rax_rdi(self):
        """MOV RAX, RDI"""
        self.emit_bytes(0x48, 0x89, 0xF8)
        print("DEBUG: MOV RAX, RDI")
    
    def emit_mov_rax_rsi(self):
        """MOV RAX, RSI"""
        self.emit_bytes(0x48, 0x89, 0xF0)
        print("DEBUG: Emitted MOV RAX, RSI")
    
    def emit_mov_rax_rcx(self):
        """MOV RAX, RCX"""
        self.emit_bytes(0x48, 0x89, 0xC8)
        print("DEBUG: MOV RAX, RCX")
    
    def emit_mov_rax_rsp(self):
        """MOV RAX, RSP"""
        self.emit_bytes(0x48, 0x89, 0xE0)
        print("DEBUG: MOV RAX, RSP")
    
    def emit_mov_rdi_rbx(self):
        """MOV RDI, RBX"""
        self.emit_bytes(0x48, 0x89, 0xDF)
        print("DEBUG: MOV RDI, RBX")
    
    def emit_mov_rdi_from_rbx(self):
        """MOV RDI, RBX (alias)"""
        self.emit_mov_rdi_rbx()
    
    def emit_mov_rdi_rsp(self):
        """MOV RDI, RSP"""
        self.emit_bytes(0x48, 0x89, 0xE7)
        print("DEBUG: MOV RDI, RSP")
    
    def emit_mov_rdi_rsi(self):
        """MOV RDI, RSI"""
        self.emit_bytes(0x48, 0x89, 0xF7)
    
    def emit_mov_rsi_rbx(self):
        """MOV RSI, RBX"""
        self.emit_bytes(0x48, 0x89, 0xDE)
        print("DEBUG: MOV RSI, RBX")
    
    def emit_mov_rsi_from_rbx(self):
        """MOV RSI, RBX (alias)"""
        self.emit_mov_rsi_rbx()
    
    def emit_mov_rsi_rcx(self):
        """MOV RSI, RCX"""
        self.emit_bytes(0x48, 0x89, 0xCE)
        print("DEBUG: MOV RSI, RCX")
    
    def emit_mov_rsi_rdi(self):
        """MOV RSI, RDI"""
        self.emit_bytes(0x48, 0x89, 0xFE)
        print("DEBUG: MOV RSI, RDI")
    
    def emit_mov_rsi_rsp(self):
        """MOV RSI, RSP"""
        self.emit_bytes(0x48, 0x89, 0xE6)
        print("DEBUG: MOV RSI, RSP")
    
    def emit_mov_rdx_rbx(self):
        """MOV RDX, RBX"""
        self.emit_bytes(0x48, 0x89, 0xDA)
        print("DEBUG: Emitted MOV RDX, RBX")
    
    def emit_mov_rdx_r10(self):
        """MOV RDX, R10"""
        self.emit_bytes(0x4C, 0x89, 0xD2)
        print("DEBUG: MOV RDX, R10")
    
    def emit_mov_rbx_rsi(self):
        """MOV RBX, RSI"""
        self.emit_bytes(0x48, 0x89, 0xF3)
        print("DEBUG: Emitted MOV RBX, RSI")
    
    def emit_mov_rbp_rsp(self):
        """MOV RBP, RSP - Set up stack frame"""
        self.emit_bytes(0x48, 0x89, 0xE5)
        print("DEBUG: MOV RBP, RSP")
    
    def emit_mov_rsp_rbp(self):
        """MOV RSP, RBP - Restore stack pointer"""
        self.emit_bytes(0x48, 0x89, 0xEC)
        print("DEBUG: MOV RSP, RBP")
    
    def emit_mov_rsp_rax(self):
        """MOV RSP, RAX"""
        self.emit_bytes(0x48, 0x89, 0xC4)
        print("DEBUG: MOV RSP, RAX")
    
    # === Extended register moves (R8-R15) ===
    
    def emit_mov_r8_rdi(self):
        """MOV R8, RDI"""
        self.emit_bytes(0x49, 0x89, 0xF8)
        print("DEBUG: MOV R8, RDI")
    
    def emit_mov_r8_rax(self):
        """MOV R8, RAX"""
        self.emit_bytes(0x49, 0x89, 0xC0)
        print("DEBUG: MOV R8, RAX")
    
    def emit_mov_r9_rsi(self):
        """MOV R9, RSI"""
        self.emit_bytes(0x49, 0x89, 0xF1)
        print("DEBUG: MOV R9, RSI")
    
    def emit_mov_r9_rax(self):
        """MOV R9, RAX"""
        self.emit_bytes(0x49, 0x89, 0xC1)
        print("DEBUG: MOV R9, RAX")
    
    def emit_mov_r10_rax(self):
        """MOV R10, RAX"""
        self.emit_bytes(0x49, 0x89, 0xC2)
        print("DEBUG: MOV R10, RAX")
    
    def emit_mov_r11_rax(self):
        """MOV R11, RAX"""
        self.emit_bytes(0x49, 0x89, 0xC3)
        print("DEBUG: MOV R11, RAX")
    
    
    def emit_mov_rax_r8(self):
        """MOV RAX, R8"""
        self.emit_bytes(0x4C, 0x89, 0xC0)
        print("DEBUG: MOV RAX, R8")
    
    def emit_mov_rax_r9(self):
        """MOV RAX, R9"""
        self.emit_bytes(0x4C, 0x89, 0xC8)
        print("DEBUG: MOV RAX, R9")
    
    def emit_mov_rax_r10(self):
        """MOV RAX, R10"""
        self.emit_bytes(0x4C, 0x89, 0xD0)
        print("DEBUG: MOV RAX, R10")
    
    def emit_mov_rdi_r8(self):
        """MOV RDI, R8"""
        self.emit_bytes(0x4C, 0x89, 0xC7)
        print("DEBUG: MOV RDI, R8")
    
    def emit_mov_rsi_r9(self):
        """MOV RSI, R9"""
        self.emit_bytes(0x4C, 0x89, 0xCE)
        print("DEBUG: MOV RSI, R9")
    
    # === TEST OPERATIONS ===
    
    def emit_test_rax_rax(self):
        """TEST RAX, RAX - Set flags based on RAX"""
        self.emit_bytes(0x48, 0x85, 0xC0)
        print("DEBUG: TEST RAX, RAX")
    
    def emit_test_rcx_rcx(self):
        """TEST RCX, RCX"""
        self.emit_bytes(0x48, 0x85, 0xC9)
    
    def emit_test_rdi_rdi(self):
        """TEST RDI, RDI - Set flags based on RDI"""
        self.emit_bytes(0x48, 0x85, 0xFF)
        print("DEBUG: TEST RDI, RDI")
    
    def emit_test_rsi_rsi(self):
        """TEST RSI, RSI - Set flags based on RSI"""
        self.emit_bytes(0x48, 0x85, 0xF6)
        print("DEBUG: TEST RSI, RSI")
    
    def emit_test_r10_r10(self):
        """TEST R10, R10 - Set flags based on R10"""
        self.emit_bytes(0x4D, 0x85, 0xD2)
        print("DEBUG: TEST R10, R10")
    
    def emit_test_rax_imm8(self, value: int):
        """Test the least significant byte of RAX with an 8-bit immediate"""
        if not 0 <= value <= 0xFF:
            raise ValueError(f"Immediate value {value} out of 8-bit range (0-255)")
        self.emit_bytes(0xA8)  # TEST AL, imm8
        self.emit_bytes(*struct.pack('<B', value))
        print(f"DEBUG: Emitted TEST AL, {value:#x}")
        
        
    def emit_mov_rcx_rbx(self):
        """MOV RCX, RBX - Move RBX to RCX"""
        self.emit_bytes(0x48, 0x89, 0xD9)
        print("DEBUG: MOV RCX, RBX")

    # Also add the reverse operation for completeness:
    def emit_mov_rbx_rcx(self):
        """MOV RBX, RCX - Move RCX to RBX"""
        self.emit_bytes(0x48, 0x89, 0xCB)
        print("DEBUG: MOV RBX, RCX")    
    
    # === COMPARE OPERATIONS ===
    
    def emit_cmp_rax_imm8(self, value):
        """CMP RAX, imm8"""
        self.emit_bytes(0x48, 0x83, 0xF8, value & 0xFF)
        print(f"DEBUG: CMP RAX, {value}")
    
    def emit_cmp_rax_imm32(self, value: int):
        """CMP RAX, imm32 - Compare RAX with 32-bit immediate"""
        self.emit_bytes(0x48, 0x3D)  # CMP RAX, imm32
        self.emit_bytes(*struct.pack('<i', value))
        print(f"DEBUG: CMP RAX, {value}")
    
    def emit_cmp_rax_imm64(self, value: int):
        """Compare RAX with a 64-bit immediate using a register intermediate"""
        value = value & 0xFFFFFFFFFFFFFFFF
        self.emit_mov_rbx_imm64(value)
        self.emit_bytes(0x48, 0x39, 0xD8)  # CMP RAX, RBX
        print(f"DEBUG: Emitted CMP RAX, {value:#x}")
    
    # === INCREMENT/DECREMENT ===
    
    def emit_inc_rdi(self):
        """INC RDI - Increment RDI by 1"""
        self.emit_bytes(0x48, 0xFF, 0xC7)
        print("DEBUG: INC RDI")
    
    def emit_dec_rdi(self):
        """DEC RDI - Decrement RDI"""
        self.emit_bytes(0x48, 0xFF, 0xCF)
        
        
    def emit_inc_rax(self):
        """INC RAX - Increment RAX by 1"""
        self.emit_bytes(0x48, 0xFF, 0xC0)
        print("DEBUG: INC RAX")

    def emit_dec_rax(self):
        """DEC RAX - Decrement RAX by 1"""
        self.emit_bytes(0x48, 0xFF, 0xC8)
        print("DEBUG: DEC RAX")

    def emit_inc_rbx(self):
        """INC RBX - Increment RBX by 1"""
        self.emit_bytes(0x48, 0xFF, 0xC3)
        print("DEBUG: INC RBX")

    def emit_dec_rbx(self):
        """DEC RBX - Decrement RBX by 1"""
        self.emit_bytes(0x48, 0xFF, 0xCB)
        print("DEBUG: DEC RBX")

    def emit_inc_rcx(self):
        """INC RCX - Increment RCX by 1"""
        self.emit_bytes(0x48, 0xFF, 0xC1)
        print("DEBUG: INC RCX")

    def emit_dec_rcx(self):
        """DEC RCX - Decrement RCX by 1"""
        self.emit_bytes(0x48, 0xFF, 0xC9)
        print("DEBUG: DEC RCX")

    def emit_inc_rdx(self):
        """INC RDX - Increment RDX by 1"""
        self.emit_bytes(0x48, 0xFF, 0xC2)
        print("DEBUG: INC RDX")

    def emit_dec_rdx(self):
        """DEC RDX - Decrement RDX by 1"""
        self.emit_bytes(0x48, 0xFF, 0xCA)
        print("DEBUG: DEC RDX")

    def emit_inc_rsi(self):
        """INC RSI - Increment RSI by 1"""
        self.emit_bytes(0x48, 0xFF, 0xC6)
        print("DEBUG: INC RSI")

    def emit_dec_rsi(self):
        """DEC RSI - Decrement RSI by 1"""
        self.emit_bytes(0x48, 0xFF, 0xCE)
        print("DEBUG: DEC RSI")
        
    # Add these methods to the X64Assembler class in assembler.py

    def emit_test_r64_r64(self, reg1, reg2):
        """TEST reg1, reg2"""
        reg_map = {'rax': 0, 'rcx': 1, 'rdx': 2, 'rbx': 3, 'rsi': 6, 'rdi': 7}
        r1 = reg_map[reg1]
        r2 = reg_map[reg2]
        self.emit_bytes([0x48, 0x85, 0xC0 | (r2 << 3) | r1])

    def emit_js(self, label):
        """Jump if sign (JS) - for negative values"""
        offset_placeholder = len(self.code) + 2
        self.emit_bytes([0x78, 0x00])  # JS rel8 placeholder
        self.add_jump_fixup(label, offset_placeholder - 1, 1)  # 1-byte offset

    # === XOR OPERATIONS ===
    def emit_xor_rdx_rdx(self):
        """XOR RDX, RDX - Zero RDX"""
        self.emit_bytes(0x48, 0x31, 0xD2)
        print("DEBUG: XOR RDX, RDX")

    def emit_xor_rsi_rsi(self):
        """XOR RSI, RSI - Zero RSI"""
        self.emit_bytes(0x48, 0x31, 0xF6)
        print("DEBUG: XOR RSI, RSI")

    # === REGISTER TO RSP ===
    def emit_mov_rsi_rsp(self):
        """MOV RSI, RSP"""
        self.emit_bytes(0x48, 0x89, 0xE6)
        print("DEBUG: MOV RSI, RSP")

    def emit_mov_rdi_rsp(self):
        """MOV RDI, RSP"""
        self.emit_bytes(0x48, 0x89, 0xE7)
        print("DEBUG: MOV RDI, RSP")

    # === MEMORY OPERATIONS ===
    def emit_mov_rdi_deref_rax(self):
        """MOV RDI, [RAX]"""
        self.emit_bytes(0x48, 0x8B, 0x38)
        print("DEBUG: MOV RDI, [RAX]")

    def emit_mov_rdi_deref_rax_offset(self, offset):
        """MOV RDI, [RAX + offset]"""
        if offset == 0:
            self.emit_mov_rdi_deref_rax()
        elif offset <= 127:
            self.emit_bytes(0x48, 0x8B, 0x78, offset & 0xFF)
        else:
            self.emit_bytes(0x48, 0x8B, 0xB8)
            self.emit_bytes(*struct.pack('<i', offset))
        print(f"DEBUG: MOV RDI, [RAX + {offset}]")

    def emit_mov_qword_ptr_rsp_rax(self):
        """MOV [RSP], RAX"""
        self.emit_bytes(0x48, 0x89, 0x04, 0x24)
        print("DEBUG: MOV [RSP], RAX")

    def emit_mov_qword_ptr_rsp_offset_imm64(self, offset, value):
        """MOV QWORD [RSP + offset], imm64"""
        self.emit_push_rax()
        self.emit_mov_rax_imm64(value)
        if offset == 0:
            self.emit_bytes(0x48, 0x89, 0x44, 0x24, 0x08)
        else:
            self.emit_bytes(0x48, 0x89, 0x44, 0x24, (offset + 8) & 0xFF)
        self.emit_pop_rax()

    # === XOR OPERATIONS ===
    def emit_xor_rdx_rdx(self):
        """XOR RDX, RDX - Zero RDX"""
        self.emit_bytes(0x48, 0x31, 0xD2)
        print("DEBUG: XOR RDX, RDX")

    def emit_xor_rsi_rsi(self):
        """XOR RSI, RSI - Zero RSI"""
        self.emit_bytes(0x48, 0x31, 0xF6)
        print("DEBUG: XOR RSI, RSI")

    # === REGISTER TO RSP ===
    def emit_mov_rsi_rsp(self):
        """MOV RSI, RSP"""
        self.emit_bytes(0x48, 0x89, 0xE6)
        print("DEBUG: MOV RSI, RSP")

    # === MEMORY OPERATIONS ===
    def emit_mov_rdi_deref_rax(self):
        """MOV RDI, [RAX]"""
        self.emit_bytes(0x48, 0x8B, 0x38)
        print("DEBUG: MOV RDI, [RAX]")

    def emit_mov_rdi_deref_rax_offset(self, offset):
        """MOV RDI, [RAX + offset]"""
        if offset == 0:
            self.emit_mov_rdi_deref_rax()
        elif offset <= 127:
            self.emit_bytes(0x48, 0x8B, 0x78, offset & 0xFF)
        else:
            self.emit_bytes(0x48, 0x8B, 0xB8)
            self.emit_bytes(*struct.pack('<i', offset))
        print(f"DEBUG: MOV RDI, [RAX + {offset}]")

    def emit_mov_qword_ptr_rsp_rax(self):
        """MOV [RSP], RAX"""
        self.emit_bytes(0x48, 0x89, 0x04, 0x24)
        print("DEBUG: MOV [RSP], RAX")

    def emit_mov_qword_ptr_rsp_offset_imm64(self, offset, value):
        """MOV QWORD [RSP + offset], imm64"""
        self.emit_push_rax()
        self.emit_mov_rax_imm64(value)
        if offset == 0:
            self.emit_bytes(0x48, 0x89, 0x44, 0x24, 0x08)
        else:
            self.emit_bytes(0x48, 0x89, 0x44, 0x24, (offset + 8) & 0xFF)
        self.emit_pop_rax()

    def emit_xchg_ah_al(self):
        """XCHG AH, AL - Swap high and low bytes of AX (for network byte order)"""
        self.emit_bytes(0x86, 0xC4)
        print("DEBUG: XCHG AH, AL")

    def emit_bswap_eax(self):
        """BSWAP EAX - Reverse all 4 bytes in EAX (for network byte order)"""
        self.emit_bytes(0x0F, 0xC8)
        print("DEBUG: BSWAP EAX")

    def emit_mov_r10_rsp(self):
        """MOV R10, RSP"""
        self.emit_bytes(0x4C, 0x89, 0xE2)
        print("DEBUG: MOV R10, RSP")