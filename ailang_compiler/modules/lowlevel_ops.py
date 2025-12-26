#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Low-Level Operations Module for AILANG Compiler
Handles systems programming operations: pointers, hardware access, atomic operations
FIXED: compile_operation now handles both AST nodes and FunctionCall nodes
"""

import sys
import os
import struct
from ailang_parser.ailang_ast import *

class LowLevelOps:
    """Handles low-level systems programming operations"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
    
    def compile_operation(self, node):
        """Compile low-level operations - handles both AST nodes and FunctionCalls"""
        try:
            # Handle direct AST nodes (AddressOf, Dereference, SizeOf)
            if hasattr(node, '__class__'):
                node_type = node.__class__.__name__
                if node_type == 'AddressOf':
                    return self.compile_address_of_ast(node)
                elif node_type == 'Dereference':
                    return self.compile_dereference_ast(node)
                elif node_type == 'SizeOf':
                    return self.compile_sizeof_ast(node)
                elif node_type == 'InterruptControl':
                    return self.compile_interrupt_control(node)
                elif node_type == 'InlineAssembly':
                    return self.compile_inline_assembly(node)
                elif node_type == 'SystemCall':
                    return self.compile_system_call(node)
            
            # Handle FunctionCall nodes
            if hasattr(node, 'function'):
                if node.function == 'Dereference':
                    return self.compile_dereference(node)
                elif node.function == 'AddressOf':
                    return self.compile_address_of(node)
                elif node.function == 'SizeOf':
                    return self.compile_sizeof(node)
                elif node.function == 'Allocate':
                    return self.compile_allocate(node)
                elif node.function in ['Deallocate', 'Free']:  # Handle both names
                    return self.compile_deallocate(node)
                elif node.function == 'MemoryCopy':
                    return self.compile_memory_copy(node)
                elif node.function == 'MemorySet':
                    return self.compile_memory_set(node)
                elif node.function == 'MemoryCompare':
                    return self.compile_memory_compare(node)
                elif node.function == 'StoreValue':
                    return self.compile_storevalue(node)
                elif node.function == 'SetByte':  
                    return self.compile_setbyte(node)
                elif node.function == 'GetByte':  
                    return self.compile_getbyte(node)
                elif node.function in ['PortRead', 'PortWrite']:
                    return self.compile_port_operation(node)
                elif node.function in ['AtomicRead', 'AtomicWrite', 'AtomicAdd', 'AtomicCompareSwap']:
                    return self.compile_atomic_operation(node)
                elif node.function in ['MMIORead', 'MMIOWrite']:
                    return self.compile_mmio_operation(node)
                elif node.function == 'HardwareRegister':
                    return self.compile_hardware_register(node)
                # If none match, return False so dispatch continues
            
            return False  # Not a low-level operation
                
        except Exception as e:
            print(f"ERROR: Low-level operation compilation failed: {str(e)}")
            raise
        
    # Add this method to the LowLevelOps class in lowlevel_ops.py:

    def compile_setbyte(self, node):
        """SetByte(address, offset, value) - Write a byte to memory"""
        try:
            print("DEBUG: Compiling SetByte operation")
            
            if len(node.arguments) != 3:
                raise ValueError("SetByte requires 3 arguments (address, offset, value)")
            
            # Evaluate address -> push on stack
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_push_rax()
            
            # Evaluate offset -> push on stack  
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_push_rax()
            
            # Evaluate value -> stays in RAX
            self.compiler.compile_expression(node.arguments[2])
            
            # Pop offset into RCX
            self.asm.emit_pop_rcx()
            
            # Pop address into RDX
            self.asm.emit_pop_rdx()
            
            # Add offset to address: RDX = address + offset
            self.asm.emit_bytes(0x48, 0x01, 0xCA)  # ADD RDX, RCX
            
            # Store byte value (AL) at [RDX]
            self.asm.emit_bytes(0x88, 0x02)  # MOV [RDX], AL
            
            # Return the value that was written (still in RAX)
            print("DEBUG: SetByte completed")
            return True
            
        except Exception as e:
            print(f"ERROR: SetByte compilation failed: {str(e)}")
            raise  
        
        
    def compile_getbyte(self, node):
        """GetByte(address, offset) - Read a byte from memory"""
        try:
            print("DEBUG: Compiling GetByte operation")
            
            if len(node.arguments) != 2:
                raise ValueError("GetByte requires 2 arguments (address, offset)")
            
            # Evaluate the address into RAX
            self.compiler.compile_expression(node.arguments[0])
            
            # Save address to RDX
            self.asm.emit_push_rax()  # Save address
            
            # Evaluate the offset into RAX
            self.compiler.compile_expression(node.arguments[1])
            
            # RAX = offset, [RSP] = address
            # Move offset to RCX
            self.asm.emit_mov_rcx_rax()  # RCX = offset
            
            # Restore address to RDX
            self.asm.emit_pop_rdx()  # RDX = address
            
            # Add offset to address: RDX = RDX + RCX
            self.asm.emit_bytes(0x48, 0x01, 0xCA)  # ADD RDX, RCX
            
            # Load byte from [RDX] into RAX (zero-extended)
            self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0x02)  # MOVZX RAX, BYTE [RDX]
            
            print("DEBUG: GetByte completed")
            return True
            
        except Exception as e:
            print(f"ERROR: GetByte compilation failed: {str(e)}")
            raise 
        
    
    def compile_dereference(self, node):
       
        try:
            print("DEBUG: Compiling Dereference")
            if len(node.arguments) < 1:
                raise ValueError("Dereference requires at least 1 argument (address)")
            
            # Compile pointer expression to get address in RAX
            self.compiler.compile_expression(node.arguments[0])
            
            # Get size hint from second argument if present
            size_hint = "qword"  # DEFAULT TO QWORD (not byte!)
            if len(node.arguments) > 1:
                if hasattr(node.arguments[1], 'value'):
                    size_hint = str(node.arguments[1].value).lower().strip('"').strip("'")
            
            # Perform dereference based on size
            if size_hint == "byte":
                # CRITICAL FIX: Was using 0x48, 0x8B, 0x00 (MOV RAX, QWORD [RAX])
                # Now using MOVZX RAX, BYTE [RAX] - proper zero-extend
                self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0x00)  
                print("DEBUG: MOVZX RAX, BYTE [RAX]")
            elif size_hint == "word":
                self.asm.emit_bytes(0x48, 0x0F, 0xB7, 0x00)  # MOVZX RAX, WORD [RAX]
                print("DEBUG: MOVZX RAX, WORD [RAX]")
            elif size_hint == "dword":
                self.asm.emit_bytes(0x8B, 0x00)  # MOV EAX, DWORD [RAX]
                print("DEBUG: MOV EAX, DWORD [RAX]")
            else:  # qword
                self.asm.emit_bytes(0x48, 0x8B, 0x00)  # MOV RAX, QWORD [RAX]
                print("DEBUG: MOV RAX, QWORD [RAX]")
            
            print(f"DEBUG: Dereferenced as {size_hint}")
            return True
            
        except Exception as e:
            print(f"ERROR: Dereference compilation failed: {str(e)}")
            raise
    
    def compile_address_of(self, node):
        """AddressOf(variable) - Get address of variable"""
        if len(node.arguments) < 1:
            raise ValueError("AddressOf requires variable argument")
        
        print("DEBUG: Compiling AddressOf")
        
        if isinstance(node.arguments[0], Identifier):
            var_name = node.arguments[0].name
            resolved_name = self.compiler.resolve_acronym_identifier(var_name)
            
            if resolved_name in self.compiler.variables:
                offset = self.compiler.variables[resolved_name]
                self.asm.emit_lea_rax("RBP", -offset)
                print(f"DEBUG: Got address of {resolved_name} at [RBP - {offset}]")
            else:
                raise ValueError(f"Undefined variable: {var_name}")
        else:
            raise ValueError("AddressOf requires identifier")
        
        return True
    
    def compile_sizeof(self, node):
        """SizeOf(type) - Get size of type"""
        if len(node.arguments) < 1:
            raise ValueError("SizeOf requires type argument")
        
        print("DEBUG: Compiling SizeOf")
        
        type_sizes = {
            'Integer': 8, 'QWord': 8, 'Int64': 8,
            'DWord': 4, 'Int32': 4,
            'Word': 2, 'Int16': 2,
            'Byte': 1, 'Int8': 1,
            'Address': 8, 'Pointer': 8,
            'FloatingPoint': 8,
            'Text': 8,  # Pointer
            'Boolean': 1,
        }
        
        size = 8  # Default
        if isinstance(node.arguments[0], Identifier):
            type_name = node.arguments[0].name
            size = type_sizes.get(type_name, 8)
        
        self.asm.emit_mov_rax_imm64(size)
        print(f"DEBUG: SizeOf = {size}")
        return True
    
    def compile_allocate(self, node):
        """Allocate(size) - Allocate memory using mmap"""
        if len(node.arguments) < 1:
            raise ValueError("Allocate requires size argument")
        
        print("DEBUG: Compiling Allocate")
        
        # Compile size expression
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rsi_rax()  # Size in RSI
        
        # mmap syscall
        self.asm.emit_mov_rax_imm64(9)  # sys_mmap
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()
        
        print("DEBUG: Allocate completed")
        return True
    
    
    def compile_deallocate(self, node):
        """
        Deallocate(address, size) - Free memory using munmap
        
        CRITICAL FIX: Validates size before calling munmap to prevent EINVAL errors.
        When size is 0, munmap would fail with EINVAL, so we skip the syscall.
        """
        if len(node.arguments) < 2:
            raise ValueError("Deallocate requires address and size")
        
        print("DEBUG: Compiling Deallocate with size validation")
        
        # Step 1: Evaluate and save address on stack
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()  # Save address for later
        
        # Step 2: Evaluate size into RSI
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()  # Size in RSI (2nd arg for munmap)
        
        # Step 3: Check if size is 0 (would cause munmap to fail with EINVAL)
        self.asm.emit_test_rsi_rsi()  # Sets ZF if RSI == 0
        
        # Step 4: Create labels for conditional flow
        skip_munmap_label = self.asm.create_label()
        do_munmap_label = self.asm.create_label()
        done_label = self.asm.create_label()
        
        # Step 5: Jump to skip if size is 0 (ZF=1)
        self.asm.emit_jump_to_label(skip_munmap_label, "JZ")
        
        # Step 6: Size is valid (non-zero), perform munmap
        self.asm.mark_label(do_munmap_label)
        self.asm.emit_pop_rax()       # Restore address from stack
        self.asm.emit_mov_rdi_rax()   # Address in RDI (1st arg for munmap)
        # RSI already contains size (2nd arg)
        self.asm.emit_mov_rax_imm64(11)  # sys_munmap = 11
        self.asm.emit_syscall()       # munmap(address, size)
        
        # Jump over the skip path
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        # Step 7: Skip munmap path (size was 0)
        self.asm.mark_label(skip_munmap_label)
        self.asm.emit_pop_rax()       # Clean up stack (discard saved address)
        self.asm.emit_xor_eax_eax()   # Return 0 (success, even though we didn't free)
        
        # Step 8: Done
        self.asm.mark_label(done_label)
        print("DEBUG: Deallocate completed with size validation")
        return True

    def compile_memory_copy(self, node):
        """MemoryCopy(dest, src, size) - Copy memory block"""
        if len(node.arguments) < 3:
            raise ValueError("MemoryCopy requires 3 arguments")
        
        print("DEBUG: Compiling MemoryCopy")
        
        # Get destination
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()
        
        # Get source
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_push_rax()
        
        # Get size
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_mov_rcx_rax()  # Size in RCX
        
        # Get source and dest from stack
        self.asm.emit_pop_rsi()  # Source in RSI
        self.asm.emit_pop_rdi()  # Dest in RDI
        
        # Use REP MOVSB for byte-by-byte copy
        self.asm.emit_bytes(0xF3, 0xA4)  # REP MOVSB
        
        print("DEBUG: MemoryCopy completed")
        return True
    
    def compile_memory_set(self, node):
        """MemorySet(dest, value, size) - Set memory to value"""
        if len(node.arguments) < 3:
            raise ValueError("MemorySet requires 3 arguments")
        
        print("DEBUG: Compiling MemorySet")
        
        # Get destination
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()
        
        # Get value
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_push_rax()
        
        # Get size
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_mov_rcx_rax()  # Size in RCX
        
        # Get value and dest from stack
        self.asm.emit_pop_rax()  # Value in AL
        self.asm.emit_pop_rdi()  # Dest in RDI
        
        # Use REP STOSB to set memory
        self.asm.emit_bytes(0xF3, 0xAA)  # REP STOSB
        
        print("DEBUG: MemorySet completed")
        return True
    
    def compile_memory_compare(self, node):
        """MemoryCompare(addr1, addr2, size) - Compare memory blocks"""
        if len(node.arguments) < 3:
            raise ValueError("MemoryCompare requires 3 arguments")
        
        print("DEBUG: Compiling MemoryCompare")
        
        # Get first address
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # Get second address
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()
        
        # Get size
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_mov_rcx_rax()
        
        # Create labels
        cmp_loop = self.asm.create_label()
        cmp_not_equal = self.asm.create_label()
        cmp_end = self.asm.create_label()
        
        # Check if size is zero
        self.asm.emit_bytes(0x48, 0x85, 0xC9)  # TEST RCX, RCX
        self.asm.emit_jump_to_label(cmp_end, "JE")
        
        # Compare loop
        self.asm.mark_label(cmp_loop)
        self.asm.emit_bytes(0x8A, 0x07)  # MOV AL, [RDI]
        self.asm.emit_bytes(0x8A, 0x1E)  # MOV BL, [RSI]
        self.asm.emit_bytes(0x38, 0xD8)  # CMP AL, BL
        self.asm.emit_jump_to_label(cmp_not_equal, "JNE")
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC9)  # DEC RCX
        self.asm.emit_jump_to_label(cmp_loop, "JNE")
        
        # Equal - return 0
        self.asm.mark_label(cmp_end)
        self.asm.emit_mov_rax_imm64(0)
        done = self.asm.create_label()
        self.asm.emit_jump_to_label(done, "JMP")
        
        # Not equal - return 1
        self.asm.mark_label(cmp_not_equal)
        self.asm.emit_mov_rax_imm64(1)
        
        self.asm.mark_label(done)
        print("DEBUG: MemoryCompare completed")
        return True
    
    
    def compile_get_byte(self, node):
        """
        GetByte(string_addr, index) - Get byte at index in string
        Properly returns zero-extended byte value
        """
        if len(node.arguments) < 2:
            raise ValueError("GetByte requires 2 arguments: address and index")
        
        print("DEBUG: Compiling GetByte")
        
        # Get string address
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()  # Save string address
        
        # Get index
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_pop_rbx()  # Restore string address to RBX
        
        # Calculate address: RBX + RAX
        self.asm.emit_bytes(0x48, 0x01, 0xD8)  # ADD RAX, RBX
        
        # Read byte with zero-extension
        self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0x00)  # MOVZX RAX, BYTE [RAX]
        
        print("DEBUG: GetByte completed")
        return True

    def compile_storevalue(self, node):
        """Compile StoreValue(address, value) - store value at address"""
        print("DEBUG: Compiling StoreValue")
        if len(node.arguments) < 2:
            raise ValueError("StoreValue requires address and value")
        
        # Check if value is a small constant (byte-sized)
        is_byte_value = False
        if isinstance(node.arguments[1], Number):
            val = int(node.arguments[1].value)
            if 0 <= val <= 255:
                is_byte_value = True
                print(f"DEBUG: Detected byte value: {val}")
        
        # Compile address
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()  # Save address
        
        # Compile value
        self.compiler.compile_expression(node.arguments[1])
        # Use R11 instead of RBX (R11 is caller-saved, safe to use)
        self.asm.emit_mov_r11_rax()  # Value in R11
        
        # Restore address
        self.asm.emit_pop_rax()  # Address in RAX
        
        # Store based on value size
        if is_byte_value:
            # MOV [RAX], R11B - store low byte of R11 to address in RAX
            self.asm.emit_bytes(0x44, 0x88, 0x18)  
            print("DEBUG: MOV [RAX], R11B (stored as byte)")
        else:
            # MOV [RAX], R11 - store full qword
            self.asm.emit_bytes(0x4C, 0x89, 0x18)  
            print("DEBUG: MOV [RAX], R11 (stored as qword)")
        
        return True
        
       
    
    def compile_atomic_operation(self, node):
        """Compile atomic operations"""
        try:
            print(f"DEBUG: Compiling {node.function} operation")
            
            if node.function == 'AtomicRead':
                if len(node.arguments) < 1:
                    raise ValueError("AtomicRead requires 1 argument (address)")
                
                # Compile address expression
                self.compiler.compile_expression(node.arguments[0])
                
                # Atomic read is just a regular MOV in x86-64 for aligned data
                self.asm.emit_dereference_qword()
                
            elif node.function == 'AtomicWrite':
                if len(node.arguments) < 2:
                    raise ValueError("AtomicWrite requires 2 arguments (address, value)")
                
                # Compile value expression
                self.compiler.compile_expression(node.arguments[1])
                self.asm.emit_push_rax()  # Save value
                
                # Compile address expression
                self.compiler.compile_expression(node.arguments[0])
                self.asm.emit_mov_rbx_rax()  # Address to RBX
                
                # Get value
                self.asm.emit_pop_rax()   # Value to RAX
                
                # Atomic write (XCHG is implicitly locked)
                self.asm.emit_bytes(0x48, 0x87, 0x03)  # XCHG [RBX], RAX
                
            elif node.function == 'AtomicAdd':
                if len(node.arguments) < 2:
                    raise ValueError("AtomicAdd requires 2 arguments (address, value)")
                
                # Get address
                address = 0x1000  # Default address
                if hasattr(node.arguments[0], 'value'):
                    address = int(node.arguments[0].value)
                
                # Get value
                value = 1  # Default increment
                if len(node.arguments) > 1 and hasattr(node.arguments[1], 'value'):
                    value = int(node.arguments[1].value)
                
                # Atomic add
                self.asm.emit_atomic_add(address, value)
                
            elif node.function == 'AtomicCompareSwap':
                if len(node.arguments) < 3:
                    raise ValueError("AtomicCompareSwap requires 3 arguments (address, expected, new)")
                
                # This is complex - simplified implementation
                # In real code, this would use LOCK CMPXCHG
                
                # Load expected value into RAX
                self.compiler.compile_expression(node.arguments[1])
                
                # Load new value into RBX
                self.asm.emit_push_rax()
                self.compiler.compile_expression(node.arguments[2])
                self.asm.emit_mov_rbx_rax()
                self.asm.emit_pop_rax()
                
                # Get address
                address = 0x1000  # Default
                if hasattr(node.arguments[0], 'value'):
                    address = int(node.arguments[0].value)
                
                # Atomic compare and exchange
                self.asm.emit_atomic_compare_exchange(address)
            
            print(f"DEBUG: {node.function} operation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: {node.function} compilation failed: {str(e)}")
            raise
    
    def compile_mmio_operation(self, node):
        """Compile memory-mapped I/O operations"""
        try:
            print(f"DEBUG: Compiling {node.function} operation")
            
            if node.function == 'MMIORead':
                if len(node.arguments) < 1:
                    raise ValueError("MMIORead requires 1 argument (address)")
                
                # Compile address expression
                self.compiler.compile_expression(node.arguments[0])
                
                # Size hint
                size = "qword"
                if len(node.arguments) > 1 and hasattr(node.arguments[1], 'value'):
                    size = str(node.arguments[1].value).lower()
                
                # MMIO read (volatile memory access)
                if size == "byte":
                    self.asm.emit_dereference_byte()
                elif size == "word":
                    self.asm.emit_dereference_word()
                elif size == "dword":
                    self.asm.emit_dereference_dword()
                else:
                    self.asm.emit_dereference_qword()
                
                # Memory barrier to ensure ordering
                self.asm.emit_memory_fence()
                
            elif node.function == 'MMIOWrite':
                if len(node.arguments) < 2:
                    raise ValueError("MMIOWrite requires 2 arguments (address, value)")
                
                # Compile value expression
                self.compiler.compile_expression(node.arguments[1])
                self.asm.emit_push_rax()  # Save value
                
                # Compile address expression
                self.compiler.compile_expression(node.arguments[0])
                self.asm.emit_mov_rbx_rax()  # Address to RBX
                
                # Get value
                self.asm.emit_pop_rax()   # Value to RAX
                
                # Size hint
                size = "qword"
                if len(node.arguments) > 2 and hasattr(node.arguments[2], 'value'):
                    size = str(node.arguments[2].value).lower()
                
                # Memory barrier before write
                self.asm.emit_memory_fence()
                
                # MMIO write
                if size == "byte":
                    self.asm.emit_store_to_pointer_byte("RAX")
                elif size == "qword":
                    self.asm.emit_store_to_pointer_qword("RAX")
                # Add other sizes as needed
                
                # Memory barrier after write
                self.asm.emit_memory_fence()
            
            print(f"DEBUG: {node.function} operation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: {node.function} compilation failed: {str(e)}")
            raise
    
    def compile_hardware_register(self, node):
        """Compile hardware register access"""
        try:
            print(f"DEBUG: Compiling HardwareRegister operation")
            
            if len(node.arguments) < 2:
                raise ValueError("HardwareRegister requires 2 arguments (register, operation)")
            
            # Get register name
            register = "CR0"  # Default
            if hasattr(node.arguments[0], 'value'):
                register = str(node.arguments[0].value)
            elif hasattr(node.arguments[0], 'name'):
                register = node.arguments[0].name
            
            # Get operation
            operation = "read"  # Default
            if hasattr(node.arguments[1], 'value'):
                operation = str(node.arguments[1].value).lower()
            elif hasattr(node.arguments[1], 'name'):
                operation = node.arguments[1].name.lower()
            
            # Handle control registers
            if register.upper().startswith('CR'):
                cr_num = int(register[2:]) if len(register) > 2 else 0
                
                if operation == "read":
                    self.asm.emit_read_cr(cr_num)
                elif operation == "write":
                    # Value should be in RAX
                    if len(node.arguments) > 2:
                        self.compiler.compile_expression(node.arguments[2])
                    self.asm.emit_write_cr(cr_num)
                else:
                    raise ValueError(f"Invalid operation for control register: {operation}")
            
            # Handle MSRs
            elif register.upper() == "MSR":
                if operation == "read":
                    # MSR number should be in ECX
                    if len(node.arguments) > 2:
                        self.compiler.compile_expression(node.arguments[2])
                        self.asm.emit_bytes(0x89, 0xC1)  # MOV ECX, EAX
                    self.asm.emit_read_msr()
                elif operation == "write":
                    # MSR number in ECX, value in EDX:EAX
                    if len(node.arguments) > 2:
                        self.compiler.compile_expression(node.arguments[2])  # MSR number
                        self.asm.emit_bytes(0x89, 0xC1)  # MOV ECX, EAX
                    if len(node.arguments) > 3:
                        self.compiler.compile_expression(node.arguments[3])  # Value
                        # Split 64-bit value into EDX:EAX
                        self.asm.emit_bytes(0x48, 0x89, 0xC2)  # MOV RDX, RAX
                        self.asm.emit_bytes(0x48, 0xC1, 0xEA, 0x20)  # SHR RDX, 32
                    self.asm.emit_write_msr()
            
            else:
                print(f"WARNING: Unsupported register type: {register}")
                # Just return 0 for unsupported registers
                self.asm.emit_mov_rax_imm64(0)
            
            print(f"DEBUG: HardwareRegister operation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: HardwareRegister compilation failed: {str(e)}")
            raise
    
    def compile_interrupt_control(self, node):
        """Compile interrupt control statements"""
        try:
            if isinstance(node, InterruptControl):
                if node.operation == "enable":
                    self.asm.emit_sti()
                    print("DEBUG: Enabled interrupts")
                elif node.operation == "disable":
                    self.asm.emit_cli()
                    print("DEBUG: Disabled interrupts")
                elif node.operation == "trigger":
                    if node.interrupt_number:
                        # Compile interrupt number
                        self.compiler.compile_expression(node.interrupt_number)
                        # For simplicity, just use INT 0x80 (common Linux syscall)
                        self.asm.emit_int(0x80)
                    else:
                        self.asm.emit_int(0x80)  # Default
                    print("DEBUG: Triggered software interrupt")
                
                return True
            return False
            
        except Exception as e:
            print(f"ERROR: Interrupt control compilation failed: {str(e)}")
            raise
    
    def compile_address_of_ast(self, node):
        """Compile AddressOf AST node directly"""
        try:
            print(f"DEBUG: Compiling AddressOf AST node")
            
            if not hasattr(node, 'variable'):
                raise ValueError("AddressOf node missing variable attribute")
            
            # Get variable name
            if hasattr(node.variable, 'name'):
                var_name = node.variable.name
                
                # FIRST: Check if it's a function
                if hasattr(self.compiler, 'user_functions'):
                    # Look in the actual user_functions dictionary
                    if var_name in self.compiler.user_functions.user_functions:
                        # Get function info and label
                        func_info = self.compiler.user_functions.user_functions[var_name]
                        label = func_info['label']
                        self.asm.emit_load_label_address('rax', label)
                        print(f"DEBUG: Got function address for {var_name} with label {label}")
                        return True
                    
                    # Also try with Function. prefix stripped (in case of Function.TestFunc)
                    if var_name.startswith("Function."):
                        clean_target = var_name[9:]
                        if clean_target in self.compiler.user_functions.user_functions:
                            func_info = self.compiler.user_functions.user_functions[clean_target]
                            label = func_info['label']
                            self.asm.emit_load_label_address('rax', label)
                            print(f"DEBUG: Got function address for {clean_target} with label {label}")
                            return True
                
                # SECOND: Check if it's a variable (your existing code)
                resolved_name = self.compiler.resolve_acronym_identifier(var_name)
                
                if resolved_name in self.compiler.variables:
                    # Get stack offset for variable
                    offset = self.compiler.variables[resolved_name]
                    
                    # Emit LEA RAX, [RBP - offset] directly with correct bytes
                    # LEA RAX, [RBP + disp8] = 48 8D 45 disp8
                    if -128 <= -offset <= 127:
                        self.asm.emit_bytes(0x48, 0x8D, 0x45)
                        # Two's complement for negative offset
                        if offset > 0:
                            self.asm.emit_bytes((256 - offset) & 0xFF)
                        else:
                            self.asm.emit_bytes((-offset) & 0xFF)
                    else:
                        # Use 32-bit displacement for larger offsets
                        self.asm.emit_bytes(0x48, 0x8D, 0x85)
                        self.asm.emit_bytes(*struct.pack('<i', -offset))
                    
                    print(f"DEBUG: Got address of variable {resolved_name} at [RBP - {offset}]")
                else:
                    raise ValueError(f"Undefined variable: {var_name} (resolved: {resolved_name})")
            else:
                raise ValueError("AddressOf requires an identifier argument")
            
            print("DEBUG: AddressOf AST compilation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: AddressOf AST compilation failed: {str(e)}")
            raise
    
    def compile_dereference_ast(self, node):
        """Compile Dereference AST node directly"""
        try:
            print(f"DEBUG: Compiling Dereference AST node")
            
            if not hasattr(node, 'pointer'):
                raise ValueError("Dereference node missing pointer attribute")
            
            # Compile pointer expression to get address in RAX
            self.compiler.compile_expression(node.pointer)
            
            # Get size hint - default to qword for backward compatibility
            size_hint = getattr(node, 'size_hint', 'qword') # Default to qword for integers/pointers
            if size_hint is None or size_hint == '':
                size_hint = 'qword' # Default to qword
            
            # Normalize size hint
            size_hint = str(size_hint).lower().strip('"').strip("'")
            
            # Perform dereference based on size
            if size_hint == "byte":
                # MOVZX RAX, BYTE [RAX] - proper zero-extend
                self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0x00)  # MOVZX RAX, BYTE [RAX]
            elif size_hint == "word":
                self.asm.emit_dereference_word()
            elif size_hint == "dword":
                self.asm.emit_dereference_dword()
            elif size_hint == "qword":
                self.asm.emit_dereference_qword()
            else:
                # Default to qword for unknown hints
                self.asm.emit_dereference_qword()
                print(f"DEBUG: Unknown size hint '{size_hint}', defaulting to qword")
            
            print(f"DEBUG: Dereferenced as {size_hint}")
            return True
            
        except Exception as e:
            print(f"ERROR: Dereference AST compilation failed: {str(e)}")
            raise
                
        
    
    def compile_sizeof_ast(self, node):
        """Compile SizeOf AST node directly"""
        try:
            print(f"DEBUG: Compiling SizeOf AST node")
            
            if not hasattr(node, 'target'):
                raise ValueError("SizeOf node missing target attribute")
            
            # Simple type size mapping
            type_sizes = {
                'Integer': 8, 'Int64': 8, 'QWord': 8,
                'Int32': 4, 'DWord': 4,
                'Int16': 2, 'Word': 2,
                'Int8': 1, 'Byte': 1,
                'UInt64': 8, 'UInt32': 4, 'UInt16': 2, 'UInt8': 1,
                'FloatingPoint': 8,
                'Text': 8,  # Pointer to string
                'Boolean': 1,
                'Address': 8,  # 64-bit pointer
                'Pointer': 8   # 64-bit pointer
            }
            
            size = 8  # Default size
            
            if hasattr(node.target, 'name'):
                type_name = node.target.name
                size = type_sizes.get(type_name, 8)
                print(f"DEBUG: Size of type {type_name} is {size} bytes")
            elif hasattr(node.target, 'type_name'):
                type_name = node.target.type_name
                size = type_sizes.get(type_name, 8)
                print(f"DEBUG: Size of type {type_name} is {size} bytes")
            else:
                # For variables, assume 8 bytes (qword)
                size = 8
                print(f"DEBUG: Default size assumption: {size} bytes")
            
            # Load size into RAX
            self.asm.emit_mov_rax_imm64(size)
            
            print("DEBUG: SizeOf AST compilation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: SizeOf AST compilation failed: {str(e)}")
            raise
    
    def compile_inline_assembly(self, node):
        """Compile inline assembly blocks"""
        try:
            if isinstance(node, InlineAssembly):
                print(f"DEBUG: Compiling inline assembly: {node.assembly_code}")
                
                # Emit the assembly code
                self.asm.emit_inline_assembly(node.assembly_code)
                
                print("DEBUG: Inline assembly compilation completed")
                return True
            return False
            
        except Exception as e:
            print(f"ERROR: Inline assembly compilation failed: {str(e)}")
            raise
    
    def compile_system_call(self, node):
        """Compile system call statements"""
        try:
            if isinstance(node, SystemCall):
                print(f"DEBUG: Compiling system call")
                
                # Compile call number into RAX
                self.compiler.compile_expression(node.call_number)
                
                # Handle arguments (limited to first few for simplicity)
                if len(node.arguments) > 0:
                    # First argument goes to RDI
                    self.asm.emit_push_rax()  # Save syscall number
                    self.compiler.compile_expression(node.arguments[0])
                    self.asm.emit_mov_rdi_rax()
                    self.asm.emit_pop_rax()   # Restore syscall number
                
                if len(node.arguments) > 1:
                    # Second argument goes to RSI
                    self.asm.emit_push_rax()
                    self.asm.emit_push_rdi()
                    self.compiler.compile_expression(node.arguments[1])
                    self.asm.emit_mov_rsi_rax()
                    self.asm.emit_pop_rdi()
                    self.asm.emit_pop_rax()
                
                if len(node.arguments) > 2:
                    # Third argument goes to RDX
                    self.asm.emit_push_rax()
                    self.asm.emit_push_rdi()
                    self.asm.emit_push_rsi()
                    self.compiler.compile_expression(node.arguments[2])
                    self.asm.emit_mov_rdx_rax()
                    self.asm.emit_pop_rsi()
                    self.asm.emit_pop_rdi()
                    self.asm.emit_pop_rax()
                
                # Make the system call
                self.asm.emit_syscall()
                
                print("DEBUG: System call compilation completed")
                return True
            return False
            
        except Exception as e:
            print(f"ERROR: System call compilation failed: {str(e)}")
            raise