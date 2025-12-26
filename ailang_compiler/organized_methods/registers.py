"""
Additional methods for registers.py
Register-to-register moves and register operations
"""

class RegistersAdditional:
    """Register-to-register moves and register operations"""

    def emit_cmp_al_bl(self):
        """CMP AL, BL"""
        self.emit_bytes(0x38, 0xD8)

    def emit_cmp_al_cl(self):
        """CMP AL, CL"""
        self.emit_bytes(0x38, 0xC8)

    def emit_cmp_al_dl(self):
        """CMP AL, DL"""
        self.emit_bytes(0x38, 0xD0)

    def emit_cmp_r14_r13(self):
        """CMP R14, R13 (end >= start)"""
        self.emit_bytes(0x4D, 0x39, 0xEE)

    def emit_cmp_rax_0(self):
        """CMP RAX, 0"""
        self.emit_bytes(0x48, 0x83, 0xF8, 0x00)

    def emit_cmp_rax_0x400000(self):
        """CMP RAX, 0x400000"""
        self.emit_bytes(
            0x48, 0x3D, 0x00, 0x00, 0x40, 0x00
        )

    def emit_cmp_rax_1000000(self):
        """CMP RAX, 1000000"""
        self.emit_bytes(
            0x48, 0x3D, 0x40, 0x42, 0x0F, 0x00
        )

    def emit_cmp_rax_r12(self):
        """CMP RAX, R12"""
        self.emit_bytes(0x4C, 0x39, 0xE0)

    def emit_cmp_rax_r13(self):
        """CMP RAX, R13"""
        self.emit_bytes(0x4C, 0x39, 0xE8)

    def emit_cmp_rbx_rdx(self):
        """CMP RBX, RDX"""
        self.emit_bytes(0x48, 0x39, 0xD3)

    def emit_cmp_rcx_rax(self):
        """CMP RCX, RAX"""
        self.emit_bytes(0x48, 0x39, 0xC1)

    def emit_cmp_rdi_rsi(self):
        """CMP RDI, RSI (if end <= start, we're done)"""
        self.emit_bytes(0x48, 0x39, 0xF7)

    def emit_lea_rbx(self):
        """LEA RBX, [RDI+RDX+16]"""
        self.emit_bytes(
            0x48, 0x8D, 0x5C, 0x17, 0x10
        )

    def emit_lea_rbx(self):
        """LEA RBX, [RDI+16] (first slot)"""
        self.emit_bytes(0x48, 0x8D, 0x5F, 0x10)

    def emit_lea_rcx(self):
        """LEA RCX, [RDX+24]"""
        self.emit_bytes(0x48, 0x8D, 0x4A, 0x18)

    def emit_lea_rcx(self):
        """LEA RCX, [R14+RCX+16]"""
        self.emit_bytes(
            0x49, 0x8D, 0x4C, 0x0E, 0x10
        )

    def emit_lea_rsi(self):
        """LEA RSI, [RBX+RAX+16]"""
        self.emit_bytes(
            0x48, 0x8D, 0x74, 0x03, 0x10
        )

    def emit_mov_al_r9(self):
        """MOV AL, [R9]"""
        self.emit_bytes(0x41, 0x8A, 0x01)

    def emit_mov_al_rbx(self):
        """MOV AL, [RBX]"""
        self.emit_bytes(0x8A, 0x03)

    def emit_mov_al_rcx(self):
        """MOV AL, [RCX]"""
        self.emit_bytes(0x8A, 0x01)

    def emit_mov_al_rdi(self):
        """MOV AL, [RDI]"""
        self.emit_bytes(0x8A, 0x07)

    def emit_mov_al_rsi(self):
        """MOV AL, [RSI]"""
        self.emit_bytes(0x8A, 0x06)

    def emit_mov_bl_r8(self):
        """MOV BL, [R8]"""
        self.emit_bytes(0x41, 0x8A, 0x18)

    def emit_mov_bl_rsi(self):
        """MOV BL, [RSI]"""
        self.emit_bytes(0x8A, 0x1E)

    def emit_mov_cl_rbx(self):
        """MOV CL, [RBX]"""
        self.emit_bytes(0x8A, 0x0B)

    def emit_mov_cl_rdi(self):
        """MOV CL, [RDI]"""
        self.emit_bytes(0x8A, 0x0F)

    def emit_mov_cl_rsi(self):
        """MOV CL, [RSI]"""
        self.emit_bytes(0x8A, 0x0E)

    def emit_mov_dl_rsi(self):
        """MOV DL, [RSI]"""
        self.emit_bytes(0x8A, 0x16)

    def emit_mov_r11_r10(self):
        """MOV [R11], R10"""
        self.emit_bytes(0x4D, 0x89, 0x13)

    def emit_mov_r12_rax(self):
        """MOV R12, RAX"""
        self.emit_bytes(0x49, 0x89, 0xC4)

    def emit_mov_r13_r12(self):
        """MOV R13, R12"""
        self.emit_bytes(0x4D, 0x89, 0xE5)

    def emit_mov_r13_rax(self):
        """MOV R13, RAX"""
        self.emit_bytes(0x49, 0x89, 0xC5)

    def emit_mov_r14_rax(self):
        """MOV [R14], RAX"""
        self.emit_bytes(0x49, 0x89, 0x06)

    def emit_mov_r14_rax(self):
        """MOV R14, RAX (end)"""
        self.emit_bytes(0x49, 0x89, 0xC6)

    def emit_mov_r15_r12(self):
        """MOV R15, R12"""
        self.emit_bytes(0x4D, 0x89, 0xE7)

    def emit_mov_r15_rax(self):
        """MOV R15, RAX"""
        self.emit_bytes(0x49, 0x89, 0xC7)

    def emit_mov_rax_r11(self):
        """MOV RAX, [R11]"""
        self.emit_bytes(0x49, 0x8B, 0x03)

    def emit_mov_rax_r12(self):
        """MOV RAX, R12"""
        self.emit_bytes(0x4C, 0x89, 0xE0)

    def emit_mov_rax_r13(self):
        """MOV RAX, R13"""
        self.emit_bytes(0x4C, 0x89, 0xE8)

    def emit_mov_rax_r14(self):
        """MOV RAX, R14 (end)"""
        self.emit_bytes(0x4C, 0x89, 0xF0)

    def emit_mov_rax_r15(self):
        """MOV RAX, [R15 + disp32]"""
        self.emit_bytes(0x49, 0x8B, 0x87)

    def emit_mov_rax_rax(self):
        """MOV RAX, [RAX]"""
        self.emit_bytes(0x48, 0x8B, 0x00)

    def emit_mov_rax_rbp(self):
        """MOV RAX, [RBP - offset]"""
        self.emit_bytes(0x48, 0x8B, 0x45)

    def emit_mov_rax_rdx(self):
        """MOV RAX, RDX (remainder)"""
        self.emit_bytes(0x48, 0x89, 0xD0)

    def emit_mov_rbx_r12(self):
        """MOV RBX, R12 (exp in RBX)"""
        self.emit_bytes(0x4C, 0x89, 0xE3)

    def emit_mov_rbx_r13(self):
        """MOV RBX, R13 (key string)"""
        self.emit_bytes(0x4C, 0x89, 0xEB)

    def emit_mov_rcx_r12(self):
        """MOV RCX, R12"""
        self.emit_bytes(0x4C, 0x89, 0xE1)

    def emit_mov_rcx_r13(self):
        """MOV RCX, R13"""
        self.emit_bytes(0x4C, 0x89, 0xE9)

    def emit_mov_rcx_r14(self):
        """MOV RCX, R14"""
        self.emit_bytes(0x4C, 0x89, 0xF1)

    def emit_mov_rcx_r15(self):
        """MOV RCX, R15"""
        self.emit_bytes(0x4C, 0x89, 0xF9)

    def emit_mov_rcx_rbp(self):
        """MOV RCX, [RBP - offset]"""
        self.emit_bytes(0x48, 0x8B, 0x8D)

    def emit_mov_rcx_rdi(self):
        """MOV RCX, RDI (end address)"""
        self.emit_bytes(0x48, 0x89, 0xF9)

    def emit_mov_rcx_rdi(self):
        """MOV RCX, [RDI] (capacity)"""
        self.emit_bytes(0x48, 0x8B, 0x0F)

    def emit_mov_rcx_rdx(self):
        """MOV RCX, RDX"""
        self.emit_bytes(0x48, 0x89, 0xD1)

    def emit_mov_rdi_al(self):
        """MOV [RDI], AL"""
        self.emit_bytes(0x88, 0x07)

    def emit_mov_rdi_cl(self):
        """MOV [RDI], CL"""
        self.emit_bytes(0x88, 0x0F)

    def emit_mov_rdi_r12(self):
        """MOV RDI, R12"""
        self.emit_bytes(0x4C, 0x89, 0xE7)

    def emit_mov_rdi_r13(self):
        """MOV RDI, R13"""
        self.emit_bytes(0x4C, 0x89, 0xEF)

    def emit_mov_rdi_r14(self):
        """MOV RDI, R14"""
        self.emit_bytes(0x4C, 0x89, 0xF7)

    def emit_mov_rdi_r15(self):
        """MOV RDI, R15"""
        self.emit_bytes(0x4C, 0x89, 0xFF)

    def emit_mov_rdi_rbp(self):
        """MOV RDI, [RBP + base_offset]"""
        self.emit_bytes(0x48, 0x8B, 0xBD)

    def emit_mov_rdx_al(self):
        """MOV [RDX], AL"""
        self.emit_bytes(0x88, 0x02)

    def emit_mov_rdx_rbp(self):
        """MOV RDX, [RBP + size_offset]"""
        self.emit_bytes(0x48, 0x8B, 0x95)

    def emit_mov_rdx_rcx(self):
        """MOV [RDX], RCX"""
        self.emit_bytes(0x48, 0x89, 0x0A)

    def emit_mov_rdx_rcx(self):
        """MOV RDX, RCX (length)"""
        self.emit_bytes(0x48, 0x89, 0xCA)

    def emit_mov_rsi_r12(self):
        """MOV RSI, R12 (string pointer)"""
        self.emit_bytes(0x4C, 0x89, 0xE6)

    def emit_mov_rsi_r13(self):
        """MOV RSI, R13"""
        self.emit_bytes(0x4C, 0x89, 0xEE)

    def emit_mov_rsi_r14(self):
        """MOV RSI, R14"""
        self.emit_bytes(0x4C, 0x89, 0xF6)

    def emit_mov_rsi_r15(self):
        """MOV RSI, R15"""
        self.emit_bytes(0x4C, 0x89, 0xFE)

    def emit_movzx_eax_al(self):
        """MOVZX EAX, AL"""
        self.emit_bytes(0x0F, 0xB6, 0xC0)

    def emit_movzx_edx_byte_ptr(self):
        """MOVZX EDX, BYTE [RBX]"""
        self.emit_bytes(0x0F, 0xB6, 0x13)

    def emit_movzx_edx_byte_ptr(self):
        """MOVZX EDX, BYTE [RSI]"""
        self.emit_bytes(0x0F, 0xB6, 0x16)

    def emit_movzx_rax_al(self):
        """MOVZX RAX, AL"""
        self.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)

    def emit_movzx_rax_byte_ptr(self):
        """MOVZX RAX, BYTE [RAX]"""
        self.emit_bytes(0x48, 0x0F, 0xB6, 0x00)

    def emit_movzx_rax_byte_ptr(self):
        """MOVZX RAX, BYTE [RDX]"""
        self.emit_bytes(0x48, 0x0F, 0xB6, 0x02)

    def emit_movzx_rax_word(self):
        """MOVZX RAX, WORD [RAX]"""
        self.emit_bytes(0x48, 0x0F, 0xB7, 0x00)

    def emit_test_al_al(self):
        """TEST AL, AL"""
        self.emit_bytes(0x84, 0xC0)

    def emit_test_cl_cl(self):
        """TEST CL, CL"""
        self.emit_bytes(0x84, 0xC9)

    def emit_test_dl_dl(self):
        """TEST DL, DL"""
        self.emit_bytes(0x84, 0xD2)

    def emit_test_r12_r12(self):
        """TEST R12, R12"""
        self.emit_bytes(0x4D, 0x85, 0xE4)

    def emit_test_r13_r13(self):
        """TEST R13, R13"""
        self.emit_bytes(0x4D, 0x85, 0xED)

    def emit_test_rbx_1(self):
        """TEST RBX, 1"""
        self.emit_bytes(
            0x48, 0xF7, 0xC3, 0x01, 0x00, 0x00, 0x00
        )

    def emit_xchg_rbx_rax(self):
        """XCHG [RBX], RAX"""
        self.emit_bytes(0x48, 0x87, 0x03)
