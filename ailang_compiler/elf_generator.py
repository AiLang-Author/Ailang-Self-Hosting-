#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
ELF Executable Generator - FULLY DYNAMIC
Production-ready with no hardcoded addresses
"""

import struct

class ELFGenerator:
    """Generate 64-bit ELF executables with fully dynamic layout"""
    
    def __init__(self):
        self.load_addr = 0x400000  # Standard Linux load address
        self.page_size = 0x1000     # 4KB pages
        
        # These will be calculated dynamically
        self.code_addr = None
        self.data_addr = None
        self.code_file_offset = None
        self.data_file_offset = None
        
    def calculate_layout(self, code_size, data_size):
        """Calculate memory layout dynamically based on actual sizes"""
        
        # Reserve first page for headers
        header_size = self.page_size
        
        # Code starts at second page
        self.code_file_offset = header_size
        self.code_addr = self.load_addr + self.code_file_offset
        
        # Calculate where code section ends
        code_end = self.code_file_offset + code_size
        
        # Data starts at next page boundary after code
        # This ensures proper alignment and separation
        self.data_file_offset = ((code_end + self.page_size - 1) // self.page_size) * self.page_size
        self.data_addr = self.load_addr + self.data_file_offset
        
        print(f"\nDYNAMIC LAYOUT CALCULATED:")
        print(f"  Load base:  0x{self.load_addr:08x}")
        print(f"  Code start: 0x{self.code_addr:08x} (file offset: 0x{self.code_file_offset:04x})")
        print(f"  Code size:  {code_size} bytes")
        print(f"  Data start: 0x{self.data_addr:08x} (file offset: 0x{self.data_file_offset:04x})")
        print(f"  Data size:  {data_size} bytes")
        
        return self.code_addr, self.data_addr
    
    def generate(self, code: bytes, data: bytes, assembler=None) -> bytes:
        """Generate ELF with dynamic layout based on actual sizes"""
        # --- START OF SURGICAL REPLACEMENT ---
        header_size = 0x1000  # 4KB, a standard page size

        # 1. Calculate final virtual addresses for code and data sections.
        code_virtual_addr = self.load_addr + header_size
        code_end_offset = header_size + len(code)
        # Align data section to the next page boundary for security and performance.
        data_file_offset = (code_end_offset + self.page_size - 1) & -self.page_size
        data_virtual_addr = self.load_addr + data_file_offset

        # 2. Inform the assembler of these final addresses.
        if assembler:
            assembler.set_base_addresses(code_virtual_addr, data_virtual_addr)
            # 3. Trigger the assembler to apply all relocations. This patches the placeholder addresses.
            assembler.apply_relocations()
            # Get the final, patched machine code.
            code = bytes(assembler.code)

        print(f"\nDynamic ELF Layout:")
        print(f"  Code: 0x{code_virtual_addr:x} ({len(code)} bytes)")
        print(f"  Data: 0x{data_virtual_addr:x} ({len(data)} bytes)")
        # --- END OF SURGICAL REPLACEMENT ---

        elf_header = bytearray()
        elf_header.extend(b'\x7fELF\x02\x01\x01\x00' + b'\x00'*8)
        elf_header.extend(struct.pack('<HHIQQQIHHHHHH',
            2, 0x3E, 1, code_virtual_addr, 64, 0, 0, 64, 56, 2, 0, 0, 0))

        code_phdr = bytearray()
        code_phdr.extend(struct.pack('<IIQQQQQQ',
            1, 5, header_size, code_virtual_addr, code_virtual_addr,
            len(code), len(code), self.page_size))

        data_phdr = bytearray()
        data_phdr.extend(struct.pack('<IIQQQQQQ',
            1, 6, data_file_offset, data_virtual_addr, data_virtual_addr,
            len(data), len(data), self.page_size))

        executable = bytearray()
        executable.extend(elf_header)
        executable.extend(code_phdr)
        executable.extend(data_phdr)
        executable.extend(b'\x00' * (header_size - len(executable)))
        executable.extend(code)
        executable.extend(b'\x00' * (data_file_offset - len(executable)))
        executable.extend(data)

        return bytes(executable)