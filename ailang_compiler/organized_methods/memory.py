"""
Additional methods for memory.py
Memory operations - loads, stores, addressing
"""

class MemoryAdditional:
    """Memory operations - loads, stores, addressing"""

    def emit_cmp_byte_ptr(self):
        """CMP BYTE PTR [RBX + RCX], 0"""
        self.emit_bytes(0x80, 0x3C, 0x0B, 0x00)

    def emit_rep_movsb(self):
        """REP MOVSB"""
        self.emit_bytes(0xF3, 0xA4)

    def emit_rep_stosb(self):
        """REP STOSB"""
        self.emit_bytes(0xF3, 0xAA)

    def emit_rep_stosq(self):
        """REP STOSQ (fast zero-fill)"""
        self.emit_bytes(0xF3, 0x48, 0xAB)
