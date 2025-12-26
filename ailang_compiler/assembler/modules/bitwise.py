# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/bitwise.py
"""Bitwise operations - XOR, AND, OR, NOT, shifts - COMPLETE VERSION"""

class BitwiseOperations:
    """Bitwise instruction generation - all operations"""
    
    # =========================================================================
    # XOR OPERATIONS
    # =========================================================================
    
    def emit_xor_eax_eax(self):
        """XOR EAX, EAX - zeros RAX (upper 32 bits cleared automatically)"""
        self.emit_bytes(0x31, 0xC0)
        print("DEBUG: XOR EAX, EAX")
    
    def emit_xor_edi_edi(self):
        """XOR EDI, EDI - zeros RDI"""
        self.emit_bytes(0x31, 0xFF)
        print("DEBUG: XOR EDI, EDI")
    
    def emit_xor_esi_esi(self):
        """XOR ESI, ESI - zeros RSI"""
        self.emit_bytes(0x31, 0xF6)
        print("DEBUG: XOR ESI, ESI")
    
    def emit_xor_edx_edx(self):
        """XOR EDX, EDX - zeros RDX"""
        self.emit_bytes(0x31, 0xD2)
        print("DEBUG: XOR EDX, EDX")
    
    def emit_xor_rax_rax(self):
        """XOR RAX, RAX - 64-bit version"""
        self.emit_bytes(0x48, 0x31, 0xC0)
        print("DEBUG: XOR RAX, RAX")
    
    def emit_xor_rbx_rbx(self):
        """XOR RBX, RBX - zero RBX"""
        self.emit_bytes(0x48, 0x31, 0xDB)
        print("DEBUG: XOR RBX, RBX")
    
    def emit_xor_rcx_rcx(self):
        """XOR RCX, RCX - zero RCX"""
        self.emit_bytes(0x48, 0x31, 0xC9)
        print("DEBUG: XOR RCX, RCX")
    
    def emit_xor_rdx_rdx(self):
        """XOR RDX, RDX - zero RDX"""
        self.emit_bytes(0x48, 0x31, 0xD2)
        print("DEBUG: XOR RDX, RDX")
    
    def emit_xor_rsi_rsi(self):
        """XOR RSI, RSI - zero RSI"""
        self.emit_bytes(0x48, 0x31, 0xF6)
        print("DEBUG: XOR RSI, RSI")
    
    def emit_xor_rdi_rdi(self):
        """XOR RDI, RDI - zero RDI"""
        self.emit_bytes(0x48, 0x31, 0xFF)
        print("DEBUG: XOR RDI, RDI")
    
    def emit_xor_r8_r8(self):
        """XOR R8, R8 - zero R8"""
        self.emit_bytes(0x4D, 0x31, 0xC0)
        print("DEBUG: XOR R8, R8")
    
    def emit_xor_r9_r9(self):
        """XOR R9, R9 - zero R9"""
        self.emit_bytes(0x4D, 0x31, 0xC9)
        print("DEBUG: XOR R9, R9")
    
    def emit_xor_r10_r10(self):
        """XOR R10, R10 - zero R10"""
        self.emit_bytes(0x4D, 0x31, 0xD2)
        print("DEBUG: XOR R10, R10")
    
    def emit_xor_rax_rbx(self):
        """XOR RAX, RBX"""
        self.emit_bytes(0x48, 0x31, 0xD8)
        print("DEBUG: XOR RAX, RBX")
    
    # =========================================================================
    # AND OPERATIONS
    # =========================================================================
    
    def emit_and_rax_rbx(self):
        """AND RAX, RBX"""
        self.emit_bytes(0x48, 0x21, 0xD8)
        print("DEBUG: AND RAX, RBX")
    
    def emit_and_rax_imm8(self, value):
        """AND RAX, imm8"""
        self.emit_bytes(0x48, 0x83, 0xE0, value & 0xFF)
        print(f"DEBUG: AND RAX, {value}")
    
    def emit_and_rax_imm32(self, value):
        """AND RAX, imm32"""
        self.emit_bytes(0x48, 0x25)
        self.emit_bytes(*list(value.to_bytes(4, 'little', signed=True)))
        print(f"DEBUG: AND RAX, {value}")
    
    def emit_and_al_imm8(self, value):
        """AND AL, imm8"""
        self.emit_bytes(0x24, value & 0xFF)
        print(f"DEBUG: AND AL, {value}")
    
    # =========================================================================
    # OR OPERATIONS
    # =========================================================================
    
    def emit_or_rax_rbx(self):
        """OR RAX, RBX"""
        self.emit_bytes(0x48, 0x09, 0xD8)
        print("DEBUG: OR RAX, RBX")
    
    def emit_or_rax_imm8(self, value):
        """OR RAX, imm8"""
        self.emit_bytes(0x48, 0x83, 0xC8, value & 0xFF)
        print(f"DEBUG: OR RAX, {value}")
    
    def emit_or_rax_imm32(self, value):
        """OR RAX, imm32"""
        self.emit_bytes(0x48, 0x0D)
        self.emit_bytes(*list(value.to_bytes(4, 'little', signed=True)))
        print(f"DEBUG: OR RAX, {value}")
    
    # =========================================================================
    # NOT OPERATIONS
    # =========================================================================
    
    def emit_not_rax(self):
        """NOT RAX - bitwise complement"""
        self.emit_bytes(0x48, 0xF7, 0xD0)
        print("DEBUG: NOT RAX")
    
    def emit_not_rbx(self):
        """NOT RBX - bitwise complement"""
        self.emit_bytes(0x48, 0xF7, 0xD3)
        print("DEBUG: NOT RBX")
    
    def emit_not_rcx(self):
        """NOT RCX - bitwise complement"""
        self.emit_bytes(0x48, 0xF7, 0xD1)
        print("DEBUG: NOT RCX")
    
    def emit_not_rdx(self):
        """NOT RDX - bitwise complement"""
        self.emit_bytes(0x48, 0xF7, 0xD2)
        print("DEBUG: NOT RDX")
    
    # =========================================================================
    # SHIFT LEFT OPERATIONS
    # =========================================================================
    
    def emit_shl_rax_cl(self):
        """SHL RAX, CL - shift left by CL"""
        self.emit_bytes(0x48, 0xD3, 0xE0)
        print("DEBUG: SHL RAX, CL")
    
    def emit_shl_rax_imm8(self, count):
        """SHL RAX, imm8 - shift left by immediate"""
        if count == 1:
            self.emit_bytes(0x48, 0xD1, 0xE0)
        else:
            self.emit_bytes(0x48, 0xC1, 0xE0, count & 0xFF)
        print(f"DEBUG: SHL RAX, {count}")
    
    def emit_shl_rbx_cl(self):
        """SHL RBX, CL"""
        self.emit_bytes(0x48, 0xD3, 0xE3)
        print("DEBUG: SHL RBX, CL")
    
    # =========================================================================
    # SHIFT RIGHT ARITHMETIC (SAR)
    # =========================================================================
    
    def emit_sar_rax_cl(self):
        """SAR RAX, CL - arithmetic right shift by CL"""
        self.emit_bytes(0x48, 0xD3, 0xF8)
        print("DEBUG: SAR RAX, CL")
    
    def emit_sar_rax_imm8(self, count):
        """SAR RAX, imm8 - arithmetic right shift by immediate"""
        if count == 1:
            self.emit_bytes(0x48, 0xD1, 0xF8)
        else:
            self.emit_bytes(0x48, 0xC1, 0xF8, count & 0xFF)
        print(f"DEBUG: SAR RAX, {count}")
    
    def emit_sar_rbx_cl(self):
        """SAR RBX, CL"""
        self.emit_bytes(0x48, 0xD3, 0xFB)
        print("DEBUG: SAR RBX, CL")
    
    # =========================================================================
    # SHIFT RIGHT LOGICAL (SHR)
    # =========================================================================
    
    def emit_shr_rax_cl(self):
        """SHR RAX, CL - logical right shift by CL"""
        self.emit_bytes(0x48, 0xD3, 0xE8)
        print("DEBUG: SHR RAX, CL")
    
    def emit_shr_rax_imm8(self, count):
        """SHR RAX, imm8 - logical right shift by immediate"""
        if count == 1:
            self.emit_bytes(0x48, 0xD1, 0xE8)
        else:
            self.emit_bytes(0x48, 0xC1, 0xE8, count & 0xFF)
        print(f"DEBUG: SHR RAX, {count}")
    
    def emit_shr_rbx_cl(self):
        """SHR RBX, CL"""
        self.emit_bytes(0x48, 0xD3, 0xEB)
        print("DEBUG: SHR RBX, CL")
    
    def emit_shr_rbx_imm8(self, count):
        """SHR RBX, imm8"""
        if count == 1:
            self.emit_bytes(0x48, 0xD1, 0xEB)
        else:
            self.emit_bytes(0x48, 0xC1, 0xEB, count & 0xFF)
        print(f"DEBUG: SHR RBX, {count}")
    
    # =========================================================================
    # ROTATE LEFT (ROL)
    # =========================================================================
    
    def emit_rol_rax_cl(self):
        """ROL RAX, CL - rotate left by CL"""
        self.emit_bytes(0x48, 0xD3, 0xC0)
        print("DEBUG: ROL RAX, CL")
    
    def emit_rol_rax_imm8(self, count):
        """ROL RAX, imm8"""
        if count == 1:
            self.emit_bytes(0x48, 0xD1, 0xC0)
        else:
            self.emit_bytes(0x48, 0xC1, 0xC0, count & 0xFF)
        print(f"DEBUG: ROL RAX, {count}")
    
    # =========================================================================
    # ROTATE RIGHT (ROR)
    # =========================================================================
    
    def emit_ror_rax_cl(self):
        """ROR RAX, CL - rotate right by CL"""
        self.emit_bytes(0x48, 0xD3, 0xC8)
        print("DEBUG: ROR RAX, CL")
    
    def emit_ror_rax_imm8(self, count):
        """ROR RAX, imm8"""
        if count == 1:
            self.emit_bytes(0x48, 0xD1, 0xC8)
        else:
            self.emit_bytes(0x48, 0xC1, 0xC8, count & 0xFF)
        print(f"DEBUG: ROR RAX, {count}")
    
    # =========================================================================
    # BIT TEST OPERATIONS
    # =========================================================================
    
    def emit_test_rax_rax(self):
        """TEST RAX, RAX - test if zero"""
        self.emit_bytes(0x48, 0x85, 0xC0)
        print("DEBUG: TEST RAX, RAX")
    
    def emit_test_rbx_rbx(self):
        """TEST RBX, RBX"""
        self.emit_bytes(0x48, 0x85, 0xDB)
        print("DEBUG: TEST RBX, RBX")
    
    def emit_test_rcx_rcx(self):
        """TEST RCX, RCX"""
        self.emit_bytes(0x48, 0x85, 0xC9)
        print("DEBUG: TEST RCX, RCX")
    
    def emit_test_rdx_rdx(self):
        """TEST RDX, RDX"""
        self.emit_bytes(0x48, 0x85, 0xD2)
        print("DEBUG: TEST RDX, RDX")
    
    def emit_test_rax_rbx(self):
        """TEST RAX, RBX"""
        self.emit_bytes(0x48, 0x85, 0xD8)
        print("DEBUG: TEST RAX, RBX")
    
    def emit_test_al_imm8(self, value):
        """TEST AL, imm8"""
        self.emit_bytes(0xA8, value & 0xFF)
        print(f"DEBUG: TEST AL, {value}")
    
    def emit_test_rax_imm32(self, value):
        """TEST RAX, imm32"""
        self.emit_bytes(0x48, 0xA9)
        self.emit_bytes(*list(value.to_bytes(4, 'little', signed=True)))
        print(f"DEBUG: TEST RAX, {value}")
    
    # =========================================================================
    # BIT SCAN OPERATIONS
    # =========================================================================
    
    def emit_bsr_rax_rax(self):
        """BSR RAX, RAX - bit scan reverse (find highest set bit)"""
        self.emit_bytes(0x48, 0x0F, 0xBD, 0xC0)
        print("DEBUG: BSR RAX, RAX")
    
    def emit_bsf_rax_rax(self):
        """BSF RAX, RAX - bit scan forward (find lowest set bit)"""
        self.emit_bytes(0x48, 0x0F, 0xBC, 0xC0)
        print("DEBUG: BSF RAX, RAX")
    
    # =========================================================================
    # ADVANCED BIT OPERATIONS (BMI1/BMI2)
    # =========================================================================
    
    def emit_popcnt_rax_rax(self):
        """POPCNT RAX, RAX - count set bits (requires SSE4.2)"""
        self.emit_bytes(0xF3, 0x48, 0x0F, 0xB8, 0xC0)
        print("DEBUG: POPCNT RAX, RAX")
    
    def emit_lzcnt_rax_rax(self):
        """LZCNT RAX, RAX - count leading zeros (requires BMI1)"""
        self.emit_bytes(0xF3, 0x48, 0x0F, 0xBD, 0xC0)
        print("DEBUG: LZCNT RAX, RAX")
    
    def emit_tzcnt_rax_rax(self):
        """TZCNT RAX, RAX - count trailing zeros (requires BMI1)"""
        self.emit_bytes(0xF3, 0x48, 0x0F, 0xBC, 0xC0)
        print("DEBUG: TZCNT RAX, RAX")
    
    def emit_bswap_rax(self):
        """BSWAP RAX - byte swap"""
        self.emit_bytes(0x48, 0x0F, 0xC8)
        print("DEBUG: BSWAP RAX")
    
    def emit_bswap_rbx(self):
        """BSWAP RBX - byte swap"""
        self.emit_bytes(0x48, 0x0F, 0xCB)
        print("DEBUG: BSWAP RBX")

    def emit_test_register(self, reg1: str, reg2: str):
        """TEST reg1, reg2 - Generic 64-bit register test"""
        reg_map = {
            'rax': 0, 'rcx': 1, 'rdx': 2, 'rbx': 3,
            'rsp': 4, 'rbp': 5, 'rsi': 6, 'rdi': 7
        }
        r1 = reg_map.get(reg1.lower())
        r2 = reg_map.get(reg2.lower())

        if r1 is None or r2 is None:
            raise ValueError(f"Invalid register for TEST: {reg1} or {reg2}")

        # REX.W prefix (0x48) + TEST opcode (0x85) + ModR/M byte
        modrm = 0xC0 | (r2 << 3) | r1
        self.emit_bytes(0x48, 0x85, modrm)
        print(f"DEBUG: TEST {reg1}, {reg2}")