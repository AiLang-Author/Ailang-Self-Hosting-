"""
Additional methods for comparisons.py
Comparison and condition code operations
"""

class ComparisonsAdditional:
    """Comparison and condition code operations"""

    def emit_sete_al(self):
        """SETE AL"""
        self.emit_bytes(0x0F, 0x94, 0xC0)

    def emit_setg_al(self):
        """SETG AL"""
        self.emit_bytes(0x0F, 0x9F, 0xC0)

    def emit_setge_al(self):
        """SETGE AL"""
        self.emit_bytes(0x0F, 0x9D, 0xC0)

    def emit_setl_al(self):
        """SETL AL"""
        self.emit_bytes(0x0F, 0x9C, 0xC0)

    def emit_setle_al(self):
        """SETLE AL"""
        self.emit_bytes(0x0F, 0x9E, 0xC0)

    def emit_setne_al(self):
        """SETNE AL"""
        self.emit_bytes(0x0F, 0x95, 0xC0)
