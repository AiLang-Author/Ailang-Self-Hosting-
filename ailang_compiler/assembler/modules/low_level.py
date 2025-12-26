# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/low_level.py
"""Low-level operations - pointers, atomic operations, dereferencing"""

import struct

class LowLevelOperations:
    """Pointer and atomic operations"""
    
    # === POINTER DEREFERENCING ===
    
    def emit_dereference_byte(self):
        """Dereference RAX as byte pointer - MOVZX RAX, BYTE PTR [RAX]"""
        self.emit_bytes(0x48, 0x0F, 0xB6, 0x00)
        print("DEBUG: MOVZX RAX, BYTE PTR [RAX]")
    
    def emit_dereference_word(self):
        """Dereference RAX as word pointer - MOVZX RAX, WORD PTR [RAX]"""
        self.emit_bytes(0x48, 0x0F, 0xB7, 0x00)
        print("DEBUG: MOVZX RAX, WORD PTR [RAX]")
    
    def emit_dereference_dword(self):
        """Dereference RAX as dword pointer - MOV EAX, DWORD PTR [RAX]"""
        self.emit_bytes(0x8B, 0x00)
        print("DEBUG: MOV EAX, DWORD PTR [RAX]")
    
    def emit_dereference_qword(self):
        """Dereference RAX as qword pointer - MOV RAX, QWORD PTR [RAX]"""
        self.emit_bytes(0x48, 0x8B, 0x00)
        print("DEBUG: MOV RAX, QWORD PTR [RAX]")
    
    # === POINTER STORES ===
    
    def emit_store_to_pointer_byte(self, value_reg: str = "RBX"):
        """Store byte from value_reg to address in RAX"""
        reg_codes = {'RAX': 0x00, 'RBX': 0x03, 'RCX': 0x01, 'RDX': 0x02}
        if value_reg not in reg_codes:
            raise ValueError(f"Invalid register: {value_reg}")
        
        reg_code = reg_codes[value_reg]
        self.emit_bytes(0x88, 0x00 | (reg_code << 3))  # MOV [RAX], value_reg_byte
        print(f"DEBUG: MOV [RAX], {value_reg.lower()}")
    
    def emit_store_to_pointer_qword(self, value_reg: str = "RBX"):
        """Store qword from value_reg to address in RAX"""
        reg_codes = {'RAX': 0x00, 'RBX': 0x03, 'RCX': 0x01, 'RDX': 0x02}
        if value_reg not in reg_codes:
            raise ValueError(f"Invalid register: {value_reg}")
        
        reg_code = reg_codes[value_reg]
        self.emit_bytes(0x48, 0x89, 0x00 | (reg_code << 3))  # MOV [RAX], value_reg
        print(f"DEBUG: MOV [RAX], {value_reg}")
    
    # === ATOMIC OPERATIONS ===
    
    def emit_atomic_compare_exchange(self, memory_address: int):
        """LOCK CMPXCHG [address], RBX - Atomic compare and exchange"""
        # Load address into RDX
        self.emit_push_rax()
        self.emit_mov_rax_imm64(memory_address)
        self.emit_mov_rdx_rax()
        self.emit_pop_rax()
        
        # LOCK CMPXCHG [RDX], RBX
        self.emit_bytes(0xF0, 0x48, 0x0F, 0xB1, 0x1A)
        print(f"DEBUG: LOCK CMPXCHG [{hex(memory_address)}], RBX")
    
    def emit_atomic_add(self, memory_address: int, value: int):
        """LOCK ADD [address], value - Atomic addition"""
        # Load address into RDX
        self.emit_push_rax()
        self.emit_mov_rax_imm64(memory_address)
        self.emit_mov_rdx_rax()
        self.emit_pop_rax()
        
        if -128 <= value <= 127:
            # LOCK ADD QWORD PTR [RDX], imm8
            self.emit_bytes(0xF0, 0x48, 0x83, 0x02, value & 0xFF)
        else:
            # LOCK ADD QWORD PTR [RDX], imm32
            self.emit_bytes(0xF0, 0x48, 0x81, 0x02)
            self.emit_bytes(*struct.pack('<i', value))
        
        print(f"DEBUG: LOCK ADD [{hex(memory_address)}], {value}")
    
    # === MEMORY BARRIERS ===
    
    def emit_memory_fence(self):
        """MFENCE - Memory fence for ordering"""
        self.emit_bytes(0x0F, 0xAE, 0xF0)
        print("DEBUG: MFENCE")
    
    def emit_store_fence(self):
        """SFENCE - Store fence"""
        self.emit_bytes(0x0F, 0xAE, 0xF8)
        print("DEBUG: SFENCE")
    
    def emit_load_fence(self):
        """LFENCE - Load fence"""
        self.emit_bytes(0x0F, 0xAE, 0xE8)
        print("DEBUG: LFENCE")