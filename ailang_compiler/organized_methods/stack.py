"""
Additional methods for stack.py
Stack operations
"""

class StackAdditional:
    """Stack operations"""

    def emit_popfq(self):
        """POPFQ"""
        self.emit_bytes(0x9D)

    def emit_pushfq(self):
        """PUSHFQ"""
        self.emit_bytes(0x9C)
