# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/cache.py
"""Cache and TLB operations"""

class CacheOperations:
    """Cache and TLB management operations"""
    
    def emit_invlpg(self, address: int):
        """INVLPG [address] - Invalidate page in TLB"""
        # Load address into RAX, then invalidate
        self.emit_mov_rax_imm64(address)
        self.emit_bytes(0x0F, 0x01, 0x38)  # INVLPG [RAX]
        print(f"DEBUG: INVLPG [{hex(address)}]")
    
    def emit_wbinvd(self):
        """WBINVD - Write back and invalidate cache"""
        self.emit_bytes(0x0F, 0x09)
        print("DEBUG: WBINVD")
    
    def emit_invd(self):
        """INVD - Invalidate cache without writeback"""
        self.emit_bytes(0x0F, 0x08)
        print("DEBUG: INVD")