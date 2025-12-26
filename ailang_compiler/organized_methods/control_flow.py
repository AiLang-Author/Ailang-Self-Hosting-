"""
Additional methods for control_flow.py
Control flow - jumps, conditional moves, loops
"""

class ControlFlowAdditional:
    """Control flow - jumps, conditional moves, loops"""

    def emit_jl_rel8(self):
        """JL loop_start"""
        self.emit_bytes(0x7C, 0xFF)

    def emit_jle_rel8(self):
        """JLE loop_end"""
        self.emit_bytes(0x7E)

    def emit_jle_rel8(self):
        """JLE +4 (skip to return 0)"""
        self.emit_bytes(0x7E, 0x04)

    def emit_jmp_rel8(self):
        """JMP loop_start"""
        self.emit_bytes(0xEB, 0xFF)

    def emit_jnz_rel8(self):
        """JNZ +5"""
        self.emit_bytes(0x75, 0x05)

    def emit_jz_rel8(self):
        """JZ skip_mult"""
        self.emit_bytes(0x74)
