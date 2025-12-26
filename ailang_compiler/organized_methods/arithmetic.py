"""
Additional methods for arithmetic.py
Arithmetic operations - ADD, SUB, MUL, DIV, INC, DEC
"""

class ArithmeticAdditional:
    """Arithmetic operations - ADD, SUB, MUL, DIV, INC, DEC"""

    def emit_dec_r12(self):
        """DEC R12"""
        self.emit_bytes(0x49, 0xFF, 0xCC)

    def emit_dec_r13(self):
        """DEC R13"""
        self.emit_bytes(0x49, 0xFF, 0xCD)

    def emit_div_rcx(self):
        """DIV RCX"""
        self.emit_bytes(0x48, 0xF7, 0xF1)

    def emit_imul_r12(self):
        """IMUL R12"""
        self.emit_bytes(0x49, 0xF7, 0xEC)

    def emit_imul_rax_r12(self):
        """IMUL RAX, R12"""
        self.emit_bytes(0x49, 0x0F, 0xAF, 0xC4)

    def emit_imul_rax_rax_imm(self):
        """IMUL RAX, RAX, 24"""
        self.emit_bytes(0x48, 0x6B, 0xC0, 0x18)

    def emit_imul_rax_rax_imm(self):
        """IMUL RAX, RAX, 33"""
        self.emit_bytes(0x48, 0x6B, 0xC0, 0x21)

    def emit_imul_rax_rbx_imm(self):
        """IMUL RAX, RBX (result * 10)"""
        self.emit_bytes(0x48, 0x0F, 0xAF, 0xC3)

    def emit_imul_rax_rcx(self):
        """IMUL RAX, RCX"""
        self.emit_bytes(0x48, 0x0F, 0xAF, 0xC1)

    def emit_imul_rdx_rdx_imm(self):
        """IMUL RDX, RDX, 24"""
        self.emit_bytes(0x48, 0x6B, 0xD2, 0x18)

    def emit_inc_r8(self):
        """INC R8"""
        self.emit_bytes(0x49, 0xFF, 0xC0)

    def emit_inc_r9(self):
        """INC R9"""
        self.emit_bytes(0x49, 0xFF, 0xC1)

    def emit_neg_rax(self):
        """NEG RAX"""
        self.emit_bytes(0x48, 0xF7, 0xD8)

    def emit_sub_al_32(self):
        """SUB AL, 32"""
        self.emit_bytes(0x2C, 0x20)

    def emit_sub_rax_imm32(self):
        """SUB RAX, imm32"""
        self.emit_bytes(0x48, 0x2D)

    def emit_sub_rax_r12(self):
        """SUB RAX, R12"""
        self.emit_bytes(0x4C, 0x29, 0xE0)

    def emit_sub_rax_r13(self):
        """SUB RAX, R13 (end - start)"""
        self.emit_bytes(0x4C, 0x29, 0xE8)

    def emit_sub_rcx_r15(self):
        """SUB RCX, R15"""
        self.emit_bytes(0x4C, 0x29, 0xF9)

    def emit_sub_rcx_rax(self):
        """SUB RCX, RAX (bytes used)"""
        self.emit_bytes(0x48, 0x29, 0xC1)

    def emit_sub_rcx_rsi(self):
        """SUB RCX, RSI"""
        self.emit_bytes(0x48, 0x29, 0xF1)

    def emit_sub_rdx_0x30(self):
        """SUB RDX, '0'"""
        self.emit_bytes(0x48, 0x83, 0xEA, 0x30)

    def emit_sub_rdx_rax(self):
        """SUB RDX, RAX"""
        self.emit_bytes(0x48, 0x29, 0xC2)

    def emit_sub_rdx_rcx(self):
        """SUB RDX, RCX"""
        self.emit_bytes(0x48, 0x29, 0xCA)
