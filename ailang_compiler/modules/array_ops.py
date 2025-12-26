#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Array Operations Module for AILANG Compiler
Handles compilation of array creation, access, and manipulation.
"""

import struct
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ailang_parser')))
from ailang_ast import *

class ArrayOps:
    """Handles compilation of array-related operations."""

    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm

    def compile_array_create(self, node):
        """Create array using heap allocator"""
        print("DEBUG: Compiling ArrayCreate with heap")
        
        if not hasattr(self.compiler, 'heap'):
            from .heap_manager import HeapManager 
            self.compiler.heap = HeapManager(self.compiler)
        
        # Get size
        if len(node.arguments) > 0:
            self.compiler.compile_expression(node.arguments[0])
        else:
            self.asm.emit_mov_rax_imm64(10)
        
        # Save the size (number of elements) on the stack before calculating bytes
        self.asm.emit_push_rax()

        # Calculate bytes: (size * 8) + 8
        self.asm.emit_bytes(0x48, 0xC1, 0xE0, 0x03)  # SHL RAX, 3
        self.asm.emit_bytes(0x48, 0x83, 0xC0, 0x08)  # ADD RAX, 8
        
        # Allocate from heap
        self.compiler.heap.compile_alloc()
        
        # RAX now has the new array address. Store the size in its header.
        self.asm.emit_mov_rbx_rax()
        self.asm.emit_pop_rcx() # Pop the original size into RCX
        self.asm.emit_bytes(0x48, 0x89, 0x0B)  # MOV [RBX], RCX (Store size at the start of the array)
        
        self.asm.emit_mov_rax_rbx()
        return True
    
    def compile_array_set(self, node):
        """Set array[index] = value"""
        print("DEBUG: Compiling ArraySet")
        
        if len(node.arguments) < 3:
            raise ValueError("ArraySet needs array, index, value")
        
        # Get array pointer
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()
        
        # Get index
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_push_rax()
        
        # Get value
        self.compiler.compile_expression(node.arguments[2])
        
        # Calculate offset: (index * 8) + 8
        self.asm.emit_mov_rcx_rax()  # Value in RCX
        self.asm.emit_pop_rax()  # Index
        self.asm.emit_bytes(0x48, 0xC1, 0xE0, 0x03)  # SHL RAX, 3
        self.asm.emit_bytes(0x48, 0x83, 0xC0, 0x08)  # ADD RAX, 8
        
        # Add to array base
        self.asm.emit_pop_rbx()  # Array pointer
        self.asm.emit_bytes(0x48, 0x01, 0xD8)  # ADD RAX, RBX
        
        # Store value
        self.asm.emit_bytes(0x48, 0x89, 0x08)  # MOV [RAX], RCX
        return True
    
    def compile_array_get(self, node):
        """Get array[index]"""
        print("DEBUG: Compiling ArrayGet")
        
        if len(node.arguments) < 2:
            raise ValueError("ArrayGet needs array, index")
        
        # Get array pointer
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()
        
        # Get index
        self.compiler.compile_expression(node.arguments[1])
        
        # Calculate offset: (index * 8) + 8
        self.asm.emit_bytes(0x48, 0xC1, 0xE0, 0x03)  # SHL RAX, 3
        self.asm.emit_bytes(0x48, 0x83, 0xC0, 0x08)  # ADD RAX, 8
        
        # Add to array base
        self.asm.emit_pop_rbx()  # Array pointer
        self.asm.emit_bytes(0x48, 0x01, 0xD8)  # ADD RAX, RBX
        
        # Load value
        self.asm.emit_bytes(0x48, 0x8B, 0x00)  # MOV RAX, [RAX]
        return True
    
    def compile_array_length(self, node):
        """Get array length from header"""
        print("DEBUG: Compiling ArrayLength")
        
        if len(node.arguments) < 1:
            raise ValueError("ArrayLength needs array")
        
        # Get array pointer
        self.compiler.compile_expression(node.arguments[0])
        
        # Load size from first 8 bytes
        self.asm.emit_bytes(0x48, 0x8B, 0x00)  # MOV RAX, [RAX]
        return True
    
    def compile_array_destroy(self, node):
        """Compile ArrayDestroy - properly free array memory using munmap"""
        print("DEBUG: Compiling ArrayDestroy")
        
        # Get array pointer argument
        if node.arguments:
            self.compiler.compile_expression(node.arguments[0])
        # Array pointer is now in RAX
        
        # Check for null pointer
        self.compiler.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        null_check = self.compiler.asm.create_label()
        done_label = self.compiler.asm.create_label()
        self.compiler.asm.emit_jump_to_label(null_check, "JZ")  # Jump if null
        
        # Save registers we'll use
        self.compiler.asm.emit_push_rbx()
        self.compiler.asm.emit_push_rcx()
        
        # Array structure (from compile_array_create):
        # [0-7]: capacity
        # [8-15]: length  
        # [16+]: data elements
        
        # Move array pointer to RBX for later use
        self.compiler.asm.emit_bytes(0x48, 0x89, 0xC3)  # MOV RBX, RAX
        
        # Get the capacity (total allocated size)
        self.compiler.asm.emit_bytes(0x48, 0x8B, 0x0B)  # MOV RCX, [RBX] (capacity)
        
        # Calculate total allocation size: 16 (header) + capacity * 8
        self.compiler.asm.emit_bytes(0x48, 0xC1, 0xE1, 0x03)  # SHL RCX, 3 (multiply by 8)
        self.compiler.asm.emit_bytes(0x48, 0x83, 0xC1, 0x10)  # ADD RCX, 16 (header size)
        
        # Prepare for munmap syscall
        # RDI = address (array pointer)
        # RSI = size (total allocation)
        self.compiler.asm.emit_bytes(0x48, 0x89, 0xDF)  # MOV RDI, RBX (address)
        self.compiler.asm.emit_bytes(0x48, 0x89, 0xCE)  # MOV RSI, RCX (size)
        
        # munmap syscall
        self.compiler.asm.emit_mov_rax_imm64(11)  # munmap syscall number
        self.compiler.asm.emit_syscall()
        
        # Check result (0 = success, -1 = error)
        # For now, we'll just return the result
        
        # Restore registers
        self.compiler.asm.emit_pop_rcx()
        self.compiler.asm.emit_pop_rbx()
        
        # Jump to done
        self.compiler.asm.emit_jump_to_label(done_label, "JMP")
        
        # Null pointer case - just return 0
        self.compiler.asm.mark_label(null_check)
        self.compiler.asm.emit_xor_eax_eax()  # Return 0 (zeros full RAX)
        
        # Done
        self.asm.mark_label(done_label)
        
        print("DEBUG: ArrayDestroy completed")
        return True