#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Relocation Manager for AILANG Compiler
Handles all address fixups for true position independence.
"""
import struct
from dataclasses import dataclass
from typing import List

@dataclass
class Relocation:
    code_offset: int
    data_offset: int

class RelocationManager:
    """Manages all data relocations."""
    def __init__(self):
        self.relocations: List[Relocation] = []

    def add_data_relocation(self, code_offset: int, data_offset: int):
        """Adds a record of a data address that needs patching."""
        self.relocations.append(Relocation(code_offset, data_offset))

   # In relocation_manager.py
def apply_all_relocations(self, code: bytearray, data_base_addr: int):
    """Apply all relocations to the code section"""
    print(f"Applying {len(self.relocations)} relocations...")
    for reloc in self.relocations:
        # Skip relocations for mmap addresses (dynamic, not data section)
        if reloc.data_offset < 0 or reloc.data_offset >= 0x10000:
            print(f"DEBUG: Skipping relocation for non-data address at code offset {reloc.code_offset} (data offset {reloc.data_offset})")
            continue
        final_address = data_base_addr + reloc.data_offset
        if final_address < data_base_addr or final_address > data_base_addr + 0x10000:
            print(f"ERROR: Invalid relocation address {hex(final_address)} at code offset {reloc.code_offset} (data offset {reloc.data_offset})")
            continue
        if reloc.code_offset + 8 > len(code):
            print(f"ERROR: Code offset {reloc.code_offset} out of bounds for code size {len(code)}")
            continue
        address_bytes = struct.pack('<Q', final_address)
        code[reloc.code_offset : reloc.code_offset + 8] = address_bytes
        print(f"DEBUG: Patched code offset {reloc.code_offset} with address {hex(final_address)} (data offset {reloc.data_offset})")