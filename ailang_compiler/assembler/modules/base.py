# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/base.py
"""Base functionality and initialization for X64 assembler"""

import struct
from typing import Dict, List

class AssemblerBase:
    """Base assembler functionality - initialization and core utilities"""
    
    def __init__(self, elf_generator=None):
        self.code = bytearray()
        self.data = []
        self.data_offset = 0
        self.strings = {}
        self.elf = elf_generator
        
        # Jump and relocation management (initialized by main class)
        self.jump_manager = None
        self.relocation_manager = None
        
        # Dynamic addressing support
        self.relocations = []
        self.data_base_address = None
        self.code_base_address = None
        
        # Labels and jumps
        self.labels = {}
        self.pending_jumps = []
        self.pending_calls = []
        self._label_counter = 0
    
    def emit_bytes(self, *bytes_to_emit):
        """Emit bytes to the code buffer"""
        for byte in bytes_to_emit:
            if isinstance(byte, (list, bytearray)):
                self.code.extend(byte)
            else:
                self.code.append(byte)
        
        # Debug output
        if bytes_to_emit:
            hex_str = [f'0x{b:x}' if isinstance(b, int) else str(b) 
                      for b in bytes_to_emit]
            print(f"DEBUG: Emitted bytes: {hex_str}")
    
    def get_position(self):
        """Get current position in code buffer"""
        return len(self.code)
    
    def set_base_addresses(self, code_addr, data_addr):
        """Set base addresses - called by ELF generator after layout calculation"""
        self.code_base_address = code_addr
        self.data_base_address = data_addr
        print(f"Dynamic addresses set - Code: 0x{code_addr:08x}, Data: 0x{data_addr:08x}")
    
    def add_data_relocation(self, code_offset, data_offset):
        """Mark a location that needs data address relocation"""
        self.relocations.append({
            'type': 'data',
            'code_offset': code_offset,
            'data_offset': data_offset
        })
    
    def apply_relocations(self):
        """Apply all address relocations after layout is known"""
        if self.data_base_address is None:
            raise ValueError("Cannot apply relocations - addresses not set!")
        
        for reloc in self.relocations:
            if reloc['type'] == 'data':
                # Calculate actual address
                actual_addr = self.data_base_address + reloc['data_offset']
                
                # Patch it in the code (assuming MOV instruction with 64-bit immediate)
                offset = reloc['code_offset']
                addr_bytes = struct.pack('<Q', actual_addr)
                
                # Patch the code
                for i in range(8):
                    self.code[offset + i] = addr_bytes[i]
        
        print(f"Applied {len(self.relocations)} relocations")
        self.relocations = []  # Clear after applying
    
    def emit_nop(self):
        """NOP instruction"""
        self.emit_bytes(0x90)
    
    def emit_ret(self):
        """RET instruction"""
        self.emit_bytes(0xC3)