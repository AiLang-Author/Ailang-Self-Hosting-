"""
Additional methods for bitwise.py
Bitwise operations - AND, OR, XOR, shifts, rotates
"""

class BitwiseAdditional:
    """Bitwise operations - AND, OR, XOR, shifts, rotates"""

    def emit_and_rax_imm(self):
        """AND RAX, -8"""
        self.emit_bytes(0x48, 0x83, 0xE0, 0xF8)

    def emit_and_rax_r12(self):
        """AND RAX, R12"""
        self.emit_bytes(0x4C, 0x21, 0xE0)

    def emit_and_rax_r13(self):
        """AND RAX, R13"""
        self.emit_bytes(0x4C, 0x21, 0xE8)

    def emit_and_rsi_imm(self):
        """AND RSI, ~7"""
        self.emit_bytes(0x48, 0x83, 0xE6, 0xF8)

    def emit_and_rsp_imm(self):
        """AND RSP, -16"""
        self.emit_bytes(0x48, 0x83, 0xE4, 0xF0)

    def emit_not_r12(self):
        """NOT R12"""
        self.emit_bytes(0x49, 0xF7, 0xD4)

    def emit_not_r13(self):
        """NOT R13"""
        self.emit_bytes(0x49, 0xF7, 0xD5)

    def emit_or_rax_rdx(self):
        """OR RAX, RDX"""
        self.emit_bytes(0x48, 0x09, 0xD0)

    def emit_sar_r12_1(self):
        """SAR R12, 1 (divide by 2)"""
        self.emit_bytes(0x49, 0xD1, 0xFC)

    def emit_sar_rbx_1(self):
        """SAR RBX, 1"""
        self.emit_bytes(0x48, 0xD1, 0xFB)

    def emit_sar_rbx_63(self):
        """SAR RBX, 63"""
        self.emit_bytes(0x48, 0xC1, 0xFB, 0x3F)

    def emit_shl_rax_3(self):
        """SHL RAX, 3"""
        self.emit_bytes(0x48, 0xC1, 0xE0, 0x03)

    def emit_shl_rcx_3(self):
        """SHL RCX, 3"""
        self.emit_bytes(0x48, 0xC1, 0xE1, 0x03)

    def emit_shl_rdx_32(self):
        """SHL RDX, 32"""
        self.emit_bytes(0x48, 0xC1, 0xE2, 0x20)

    def emit_shr_rax_3(self):
        """SHR RAX, 3"""
        self.emit_bytes(0x48, 0xC1, 0xE8, 0x03)

    def emit_shr_rbx_1(self):
        """SHR RBX, 1"""
        self.emit_bytes(0x48, 0xD1, 0xEB)

    def emit_shr_rbx_shift(self):
        """SHR RBX, shift"""
        self.emit_bytes(0x48, 0xC1, 0xEB)

    def emit_shr_rdx_32(self):
        """SHR RDX, 32"""
        self.emit_bytes(0x48, 0xC1, 0xEA, 0x20)
