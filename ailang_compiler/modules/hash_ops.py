# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Hash Table Operations Module for AILANG Compiler - FIXED VERSION
Uses string comparison instead of pointer comparison
"""

import sys
import os
from ailang_parser.ailang_ast import *

class HashOps:
    """Hash table using linear probing with STRING COMPARISON"""

    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm

    def compile_operation(self, node):
        """Route to hash handlers"""
        if hasattr(node, "function"):
            function = node.function
            if function in ['HashCreate', 'HashSet', 'HashGet', 'HashDelete', 'HashExists']:
                handler_name = f'compile_{function.lower().replace("hash", "hash_")}'
                handler = getattr(self, handler_name, None)
                if handler:
                    return handler(node)
        return False

    def emit_string_compare(self):
        """Compare string at R13 with string at [RBX+8]. Sets ZF if equal."""
        
        # Save registers
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()
        self.asm.emit_push_rax()
        self.asm.emit_push_rcx()
        
        # RSI = R13 (search key)
        self.asm.emit_bytes(0x4C, 0x89, 0xEE)      # MOV RSI, R13
        # RDI = [RBX+8] (stored key)
        self.asm.emit_bytes(0x48, 0x8B, 0x7B, 0x08) # MOV RDI, [RBX+8]
        
        # String comparison loop
        compare_loop = self.asm.create_label()
        strings_match = self.asm.create_label()
        strings_differ = self.asm.create_label()
        
        self.asm.mark_label(compare_loop)
        
        # Load and compare bytes
        self.asm.emit_bytes(0x8A, 0x06)            # MOV AL, [RSI]
        self.asm.emit_bytes(0x8A, 0x0F)            # MOV CL, [RDI]
        self.asm.emit_bytes(0x38, 0xC8)            # CMP AL, CL
        self.asm.emit_jump_to_label(strings_differ, "JNE")
        
        # Check for null terminator
        self.asm.emit_bytes(0x84, 0xC0)            # TEST AL, AL
        self.asm.emit_jump_to_label(strings_match, "JZ")
        
        # Move to next character
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)      # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)      # INC RDI
        self.asm.emit_jump_to_label(compare_loop, "JMP")
        
        self.asm.mark_label(strings_match)
        # Set ZF by comparing equal values
        self.asm.emit_bytes(0x48, 0x31, 0xC0)      # XOR RAX, RAX
        self.asm.emit_bytes(0x48, 0x85, 0xC0)      # TEST RAX, RAX (sets ZF)
        end_label = self.asm.create_label()
        self.asm.emit_jump_to_label(end_label, "JMP")
        
        self.asm.mark_label(strings_differ)
        # Clear ZF by setting RAX to 1
        self.asm.emit_bytes(0x48, 0xC7, 0xC0, 0x01, 0x00, 0x00, 0x00)  # MOV RAX, 1
        self.asm.emit_bytes(0x48, 0x85, 0xC0)      # TEST RAX, RAX (clears ZF)
        
        self.asm.mark_label(end_label)
        
        # Restore registers
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rax()
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()

    def compile_hash_create(self, node):
        """Create hash table with linear probing
        Structure: [capacity:8][size:8][entries...]
        Entry: [hash:8][key_addr:8][value:8] = 24 bytes each
        """
        capacity = 16  # Default capacity
        if node.arguments and isinstance(node.arguments[0], Number):
            capacity = int(node.arguments[0].value)
            # Round up to power of 2 for better distribution
            if capacity < 4:
                capacity = 4
            # Make it at least 2x expected size for linear probing
            capacity = capacity * 2

        # Calculate total size: header(16) + entries(capacity * 24)
        total_size = 16 + (capacity * 24)

        # Allocate memory
        self.asm.emit_mov_rax_imm64(9)  # sys_mmap
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
        self.asm.emit_mov_rsi_imm64(total_size)  # size
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ|PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE|MAP_ANONYMOUS
        self.asm.emit_mov_r8_imm64(0xFFFFFFFFFFFFFFFF)  # fd = -1
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()

        # Save table pointer
        self.asm.emit_push_rax()

        # Zero out entire table
        self.asm.emit_mov_rdi_rax()  # RDI = destination
        self.asm.emit_mov_rcx_imm64(total_size)  # RCX = size
        self.asm.emit_bytes(0x31, 0xC0)  # XOR EAX, EAX (zero)
        self.asm.emit_bytes(0xFC)  # CLD
        self.asm.emit_bytes(0xF3, 0xAA)  # REP STOSB

        # Get table pointer back
        self.asm.emit_pop_rax()
        self.asm.emit_mov_rbx_rax()

        # Initialize header
        self.asm.emit_mov_rax_imm64(capacity)
        self.asm.emit_bytes(0x48, 0x89, 0x03)  # MOV [RBX], RAX (capacity)
        
        self.asm.emit_mov_rax_imm64(0)
        self.asm.emit_bytes(0x48, 0x89, 0x43, 0x08)  # MOV [RBX+8], RAX (size=0)

        # Return table pointer
        self.asm.emit_mov_rax_rbx()
        return True

    def compile_hash_set(self, node):
        """HashSet with STRING COMPARISON for key matching"""
        if len(node.arguments) < 3:
            raise ValueError("HashSet requires 3 arguments")

        # Save all registers we'll use
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()
        self.asm.emit_push_r12()  # PUSH R12 (tracked)
        self.asm.emit_push_r13()  # PUSH R13 (tracked)

        # Get value first
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX (value)

        # Get key
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX (key addr)

        # Get table
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()  # RDI = table

        # === HASH THE KEY ===
        self.asm.emit_bytes(0x4C, 0x89, 0xEB)  # MOV RBX, R13 (key string)
        self.asm.emit_mov_rax_imm64(5381)  # Initial hash
        
        hash_loop = self.asm.create_label()
        hash_done = self.asm.create_label()
        
        self.asm.mark_label(hash_loop)
        self.asm.emit_bytes(0x0F, 0xB6, 0x13)  # MOVZX EDX, BYTE [RBX]
        self.asm.emit_bytes(0x84, 0xD2)  # TEST DL, DL
        self.asm.emit_jump_to_label(hash_done, "JZ")
        
        # hash = hash * 33 + char
        self.asm.emit_bytes(0x48, 0x6B, 0xC0, 0x21)  # IMUL RAX, RAX, 33
        self.asm.emit_bytes(0x48, 0x01, 0xD0)  # ADD RAX, RDX
        self.asm.emit_bytes(0x48, 0xFF, 0xC3)  # INC RBX
        self.asm.emit_jump_to_label(hash_loop, "JMP")
        
        self.asm.mark_label(hash_done)
        
        # Save hash value
        self.asm.emit_push_rax()  # Save hash
        
        # === FIND SLOT USING LINEAR PROBING ===
        # index = hash % capacity
        self.asm.emit_bytes(0x48, 0x8B, 0x0F)  # MOV RCX, [RDI] (capacity)
        self.asm.emit_bytes(0x48, 0x31, 0xD2)  # XOR RDX, RDX
        self.asm.emit_bytes(0x48, 0xF7, 0xF1)  # DIV RCX
        # RDX now has index
        
        # Calculate entry address: table + 16 + (index * 24)
        self.asm.emit_bytes(0x48, 0x6B, 0xD2, 0x18)  # IMUL RDX, RDX, 24
        self.asm.emit_bytes(0x48, 0x8D, 0x5C, 0x17, 0x10)  # LEA RBX, [RDI+RDX+16]
        
        # RBX = current slot address
        # Look for empty slot or matching key
        probe_loop = self.asm.create_label()
        found_slot = self.asm.create_label()
        
        self.asm.mark_label(probe_loop)
        
        # Check if slot is empty (hash == 0)
        self.asm.emit_bytes(0x48, 0x8B, 0x03)  # MOV RAX, [RBX] (slot hash)
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_jump_to_label(found_slot, "JZ")  # Empty slot found
        
        # Check if hash matches (potential key match)
        self.asm.emit_pop_rax()  # Get our hash back
        self.asm.emit_push_rax()  # Keep it on stack
        self.asm.emit_bytes(0x48, 0x39, 0x03)  # CMP [RBX], RAX
        
        check_key = self.asm.create_label()
        next_slot = self.asm.create_label()
        
        self.asm.emit_jump_to_label(check_key, "JE")  # Hash matches, check key
        self.asm.emit_jump_to_label(next_slot, "JMP")  # Try next slot
        
        self.asm.mark_label(check_key)
        # STRING COMPARISON instead of pointer comparison
        self.emit_string_compare()  # Compare R13 with [RBX+8]
        self.asm.emit_jump_to_label(found_slot, "JE")  # Strings match, update
        
        self.asm.mark_label(next_slot)
        # Move to next slot (linear probing)
        self.asm.emit_bytes(0x48, 0x83, 0xC3, 0x18)  # ADD RBX, 24 (next entry)
        
        # Wrap around if needed
        # Calculate max address: table + 16 + (capacity * 24)
        self.asm.emit_bytes(0x48, 0x8B, 0x07)  # MOV RAX, [RDI] (capacity)
        self.asm.emit_bytes(0x48, 0x6B, 0xC0, 0x18)  # IMUL RAX, RAX, 24
        self.asm.emit_bytes(0x48, 0x8D, 0x44, 0x07, 0x10)  # LEA RAX, [RDI+RAX+16]
        
        self.asm.emit_bytes(0x48, 0x39, 0xC3)  # CMP RBX, RAX
        wrap_around = self.asm.create_label()
        self.asm.emit_jump_to_label(probe_loop, "JL")  # If RBX < RAX, continue
        
        # Wrap to beginning
        self.asm.emit_bytes(0x48, 0x8D, 0x5F, 0x10)  # LEA RBX, [RDI+16] (first slot)
        self.asm.emit_jump_to_label(probe_loop, "JMP")
        
        # === FOUND SLOT - STORE DATA ===
        self.asm.mark_label(found_slot)
        
        # Check if it's a new entry (hash == 0)
        self.asm.emit_bytes(0x48, 0x8B, 0x03)  # MOV RAX, [RBX]
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        
        not_new = self.asm.create_label()
        self.asm.emit_jump_to_label(not_new, "JNZ")
        
        # New entry - increment size
        self.asm.emit_bytes(0x48, 0xFF, 0x47, 0x08)  # INC [RDI+8]
        
        self.asm.mark_label(not_new)
        
        # Store the entry
        self.asm.emit_pop_rax()  # Get hash
        self.asm.emit_bytes(0x48, 0x89, 0x03)  # MOV [RBX], RAX (hash)
        self.asm.emit_bytes(0x4C, 0x89, 0x6B, 0x08)  # MOV [RBX+8], R13 (key)
        self.asm.emit_bytes(0x4C, 0x89, 0x63, 0x10)  # MOV [RBX+16], R12 (value)
        
        # Return success
        self.asm.emit_mov_rax_imm64(1)
        
        # Restore registers
        self.asm.emit_pop_r13()  # POP R13 (tracked)
        self.asm.emit_pop_r12()  # POP R12 (tracked)
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()
        return True

    def compile_hash_get(self, node):
        """HashGet with STRING COMPARISON for key matching"""
        if len(node.arguments) < 2:
            raise ValueError("HashGet requires 2 arguments")

        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()
        self.asm.emit_push_r13()  # PUSH R13 (tracked)

        # Get key
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX (key)

        # Get table
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()  # RDI = table

        # === HASH THE KEY ===
        self.asm.emit_bytes(0x4C, 0x89, 0xEB)  # MOV RBX, R13
        self.asm.emit_mov_rax_imm64(5381)
        
        hash_loop = self.asm.create_label()
        hash_done = self.asm.create_label()
        
        self.asm.mark_label(hash_loop)
        self.asm.emit_bytes(0x0F, 0xB6, 0x13)  # MOVZX EDX, BYTE [RBX]
        self.asm.emit_bytes(0x84, 0xD2)  # TEST DL, DL
        self.asm.emit_jump_to_label(hash_done, "JZ")
        
        self.asm.emit_bytes(0x48, 0x6B, 0xC0, 0x21)  # IMUL RAX, RAX, 33
        self.asm.emit_bytes(0x48, 0x01, 0xD0)  # ADD RAX, RDX
        self.asm.emit_bytes(0x48, 0xFF, 0xC3)  # INC RBX
        self.asm.emit_jump_to_label(hash_loop, "JMP")
        
        self.asm.mark_label(hash_done)
        
        # Save hash
        self.asm.emit_push_rax()
        
        # === FIND ENTRY ===
        # index = hash % capacity
        self.asm.emit_bytes(0x48, 0x8B, 0x0F)  # MOV RCX, [RDI] (capacity)
        self.asm.emit_bytes(0x48, 0x31, 0xD2)  # XOR RDX, RDX
        self.asm.emit_bytes(0x48, 0xF7, 0xF1)  # DIV RCX
        
        # Calculate entry address
        self.asm.emit_bytes(0x48, 0x6B, 0xD2, 0x18)  # IMUL RDX, RDX, 24
        self.asm.emit_bytes(0x48, 0x8D, 0x5C, 0x17, 0x10)  # LEA RBX, [RDI+RDX+16]
        
        # Probe for entry
        probe_loop = self.asm.create_label()
        found_entry = self.asm.create_label()
        not_found = self.asm.create_label()
        
        # Set probe limit (capacity)
        self.asm.emit_bytes(0x48, 0x8B, 0x0F)  # MOV RCX, [RDI] (capacity)
        
        self.asm.mark_label(probe_loop)
        
        # Check if slot is empty
        self.asm.emit_bytes(0x48, 0x8B, 0x03)  # MOV RAX, [RBX] (hash)
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_jump_to_label(not_found, "JZ")  # Empty = not found
        
        # Check hash
        self.asm.emit_pop_rax()  # Get our hash
        self.asm.emit_push_rax()  # Keep on stack
        self.asm.emit_bytes(0x48, 0x39, 0x03)  # CMP [RBX], RAX
        
        check_key = self.asm.create_label()
        next_slot = self.asm.create_label()
        
        self.asm.emit_jump_to_label(check_key, "JE")
        self.asm.emit_jump_to_label(next_slot, "JMP")
        
        self.asm.mark_label(check_key)
        # STRING COMPARISON instead of pointer comparison
        self.emit_string_compare()  # Compare R13 with [RBX+8]
        self.asm.emit_jump_to_label(found_entry, "JE")
        
        self.asm.mark_label(next_slot)
        # Next slot
        self.asm.emit_bytes(0x48, 0x83, 0xC3, 0x18)  # ADD RBX, 24
        
        # Wrap if needed
        self.asm.emit_bytes(0x48, 0x8B, 0x07)  # MOV RAX, [RDI] (capacity)
        self.asm.emit_bytes(0x48, 0x6B, 0xC0, 0x18)  # IMUL RAX, RAX, 24
        self.asm.emit_bytes(0x48, 0x8D, 0x44, 0x07, 0x10)  # LEA RAX, [RDI+RAX+16]
        
        self.asm.emit_bytes(0x48, 0x39, 0xC3)  # CMP RBX, RAX
        self.asm.emit_jump_to_label(probe_loop, "JL")
        
        # Wrap to beginning
        self.asm.emit_bytes(0x48, 0x8D, 0x5F, 0x10)  # LEA RBX, [RDI+16]
        
        # Decrement counter and continue
        self.asm.emit_bytes(0x48, 0xFF, 0xC9)  # DEC RCX
        self.asm.emit_jump_to_label(probe_loop, "JNZ")
        self.asm.emit_jump_to_label(not_found, "JMP")  # Probed all slots
        
        # === FOUND ===
        self.asm.mark_label(found_entry)
        self.asm.emit_pop_rax()  # Clean stack
        self.asm.emit_bytes(0x48, 0x8B, 0x43, 0x10)  # MOV RAX, [RBX+16] (value)
        
        done = self.asm.create_label()
        self.asm.emit_jump_to_label(done, "JMP")
        
        # === NOT FOUND ===
        self.asm.mark_label(not_found)
        self.asm.emit_pop_rax()  # Clean stack
        self.asm.emit_mov_rax_imm64(0)  # Return 0
        
        self.asm.mark_label(done)
        
        # Restore registers
        self.asm.emit_pop_r13()  # POP R13 (tracked)
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()
        return True

    def compile_hash_exists(self, node):
        """Check if key exists - just call get and check if non-zero"""
        if len(node.arguments) < 2:
            raise ValueError("HashExists requires 2 arguments")
        
        # Just compile as HashGet
        self.compile_hash_get(node)
        
        # Check if result is non-zero
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_bytes(0x0F, 0x95, 0xC0)  # SETNZ AL
        self.asm.emit_bytes(0x0F, 0xB6, 0xC0)  # MOVZX EAX, AL
        
        return True

    def compile_hash_delete(self, node):
        """Delete not implemented yet - would need tombstone markers"""
        print("WARNING: HashDelete not yet implemented")
        self.asm.emit_mov_rax_imm64(0)
        return True