# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Library Inliner for AILANG Compiler
from ailang_ast import Number, String, Identifier
General-purpose library function inlining system.
Libraries provide high-level abstractions built on primitives.
"""

import sys
import os
import struct
from ailang_parser.ailang_ast import *

class LibraryInliner:
    """General-purpose library function inliner"""

    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm

    def compile_runtask(self, node):
        """Inline RunTask by dispatching to library handlers"""
        task_name = node.task_name
        parts = task_name.split('.')
        
        if len(parts) < 2:
            raise ValueError(f"Invalid task name format: {task_name}")

        library = parts[0]
        function = parts[1]
        
        # Dispatch to library-specific handlers
        handlers = {
            'KeyValue': self.inline_keyvalue_function,
            'Redis': self.inline_redis_function,
            'Collection': self.inline_collection_function,
            'Convert': self.inline_convert_function,
            'Memory': self.inline_memory_function,
            'Math': self.inline_math_function,
        }
        
        handler = handlers.get(library)
        if handler:
            return handler(function, node.arguments)
        else:
            print(f"WARNING: Unknown library: {library}")
            self.asm.emit_mov_rax_imm64(0)
            return False

    def inline_keyvalue_function(self, function, arguments):
        """Key-value store operations - general purpose"""
        if function == "Create":
            # Create a hash table for key-value storage
            size = 64  # Default size
            if arguments:
                size_arg = dict(arguments).get('size')
                if size_arg and isinstance(size_arg, Number):
                    size = int(size_arg.value)
            
            # Use HashCreate primitive
            from ailang_parser.ailang_ast import FunctionCall, Number
            node = FunctionCall('HashCreate', [Number(str(size))])
            self.compiler.compile_function_call(node)
            
        elif function == "Set":
            # Store key-value pair
            arg_dict = dict(arguments)
            store = arg_dict.get('store')
            key = arg_dict.get('key')
            value = arg_dict.get('value')
            
            if not all([store, key, value]):
                raise ValueError("KeyValue.Set requires store, key, value")
            
            # Use HashSet primitive
            node = FunctionCall('HashSet', [store, key, value])
            self.compiler.compile_function_call(node)
            
        elif function == "Get":
            # Retrieve value by key
            arg_dict = dict(arguments)
            store = arg_dict.get('store')
            key = arg_dict.get('key')
            
            if not all([store, key]):
                raise ValueError("KeyValue.Get requires store, key")
            
            # Use HashGet primitive
            node = FunctionCall('HashGet', [store, key])
            self.compiler.compile_function_call(node)
            
        elif function == "Delete":
            # Remove key-value pair
            arg_dict = dict(arguments)
            store = arg_dict.get('store')
            key = arg_dict.get('key')
            
            if not all([store, key]):
                raise ValueError("KeyValue.Delete requires store, key")
            
            # Use HashDelete primitive (when implemented)
            node = FunctionCall('HashDelete', [store, key])
            self.compiler.compile_function_call(node)
            
        elif function == "Exists":
            # Check if key exists
            arg_dict = dict(arguments)
            store = arg_dict.get('store')
            key = arg_dict.get('key')
            
            if not all([store, key]):
                raise ValueError("KeyValue.Exists requires store, key")
            
            # Use HashExists primitive
            node = FunctionCall('HashExists', [store, key])
            self.compiler.compile_function_call(node)
            
        else:
            raise ValueError(f"Unknown KeyValue function: {function}")


    def inline_redis_function(self, function, arguments):
        """Redis operations - built on hash table primitives"""
        if function == "Init":
            # Initialize Redis store
            size = 256  # Default size
            if arguments:
                size_arg = dict(arguments).get('size')
                if size_arg and hasattr(size_arg, 'value'):
                    size = int(size_arg.value)
            
            # Create hash table for storage
            node = FunctionCall('HashCreate', [Number(str(size))])
            self.compiler.compile_function_call(node)
            
        elif function == "Set":
            # Redis SET command
            arg_dict = dict(arguments)
            store = arg_dict.get('store')
            key = arg_dict.get('key')
            value = arg_dict.get('value')
            
            if not all([store, key, value]):
                raise ValueError("Redis.Set requires store, key, value")
            
            # Use HashSet primitive
            node = FunctionCall('HashSet', [store, key, value])
            self.compiler.compile_function_call(node)
            
            # Return would be +OK in RESP, but for now return success (1)
            self.asm.emit_mov_rax_imm64(1)
            
        elif function == "Get":
            # Redis GET command
            arg_dict = dict(arguments)
            store = arg_dict.get('store')
            key = arg_dict.get('key')
            
            if not all([store, key]):
                raise ValueError("Redis.Get requires store, key")
            
            # Use HashGet primitive
            node = FunctionCall('HashGet', [store, key])
            self.compiler.compile_function_call(node)
            # Result is already in RAX
            
        elif function == "Exists":
            # Check if key exists
            arg_dict = dict(arguments)
            store = arg_dict.get('store')
            key = arg_dict.get('key')
            
            if not all([store, key]):
                raise ValueError("Redis.Exists requires store, key")
            
            # Get value and check if non-zero
            node = FunctionCall('HashGet', [store, key])
            self.compiler.compile_function_call(node)
            
            # Set result to 1 if non-zero, 0 if zero
            self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
            self.asm.emit_bytes(0x0F, 0x95, 0xC0)  # SETNE AL
            self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)  # MOVZX RAX, AL
            
        elif function == "Delete":
            # Delete key (set to 0 for now)
            arg_dict = dict(arguments)
            store = arg_dict.get('store')
            key = arg_dict.get('key')
            
            if not all([store, key]):
                raise ValueError("Redis.Delete requires store, key")
            
            # Set value to 0 to indicate deletion
            node = FunctionCall('HashSet', [store, key, Number('0')])
            self.compiler.compile_function_call(node)
            
        else:
            raise ValueError(f"Unknown Redis function: {function}")
            
    def inline_collection_function(self, function, arguments):
        """Collection operations - lists, sets, etc."""
        if function == "CreateList":
            # Allocate dynamic array structure
            # Structure: [capacity:8][size:8][elements...]
            capacity = 16  # Default
            if arguments:
                cap_arg = dict(arguments).get('capacity')
                if cap_arg and isinstance(cap_arg, Number):
                    capacity = int(cap_arg.value)
            
            size = 16 + (capacity * 8)  # Header + elements
            self.asm.emit_mov_rax_imm64(9)  # mmap
            self.asm.emit_mov_rdi_imm64(0)
            self.asm.emit_mov_rsi_imm64(size)
            self.asm.emit_mov_rdx_imm64(3)
            self.asm.emit_mov_r10_imm64(0x22)
            self.asm.emit_mov_r8_imm64(0xFFFFFFFFFFFFFFFF)  # R8 = -1 (fd)
            self.asm.emit_mov_r9_imm64(0)
            self.asm.emit_syscall()
            
            # Initialize header
            self.asm.emit_mov_rbx_rax()
            self.asm.emit_mov_rax_imm64(capacity)
            self.asm.emit_bytes(0x48, 0x89, 0x03)  # [list] = capacity
            self.asm.emit_mov_rax_imm64(0)
            self.asm.emit_bytes(0x48, 0x89, 0x43, 0x08)  # [list+8] = size
            self.asm.emit_mov_rax_rbx()
            
        elif function == "Append":
            # Add element to list
            arg_dict = dict(arguments)
            list_ptr = arg_dict.get('list')
            value = arg_dict.get('value')
            
            if not all([list_ptr, value]):
                raise ValueError("Collection.Append requires list, value")
            
            # Get list pointer
            self.compiler.compile_expression(list_ptr)
            self.asm.emit_mov_rbx_rax()
            
            # Get current size
            self.asm.emit_bytes(0x48, 0x8B, 0x43, 0x08)  # MOV RAX, [RBX+8]
            self.asm.emit_mov_rcx_rax()  # Size in RCX
            
            # Check capacity
            self.asm.emit_bytes(0x48, 0x3B, 0x03)  # CMP RAX, [RBX]
            resize_needed = self.asm.create_label()
            no_resize = self.asm.create_label()
            self.asm.emit_jump_to_label(resize_needed, "JGE")
            
            self.asm.mark_label(no_resize)
            # Calculate element address
            self.asm.emit_bytes(0x48, 0xC1, 0xE0, 0x03)  # SHL RAX, 3 (size * 8)
            self.asm.emit_bytes(0x48, 0x8D, 0x74, 0x03, 0x10)  # LEA RSI, [RBX+RAX+16]
            
            # Store value
            self.compiler.compile_expression(value)
            self.asm.emit_bytes(0x48, 0x89, 0x06)  # MOV [RSI], RAX
            
            # Increment size
            self.asm.emit_bytes(0x48, 0xFF, 0x43, 0x08)  # INC [RBX+8]
            
            self.asm.emit_mov_rax_imm64(1)  # Success
            done = self.asm.create_label()
            self.asm.emit_jump_to_label(done, "JMP")
            
            self.asm.mark_label(resize_needed)
            # Would resize array here
            print("DEBUG: List resize needed (stub)")
            
            self.asm.mark_label(done)
            
        elif function == "Get":
            # Get element at index
            arg_dict = dict(arguments)
            list_ptr = arg_dict.get('list')
            index = arg_dict.get('index')
            
            if not all([list_ptr, index]):
                raise ValueError("Collection.Get requires list, index")
            
            self.compiler.compile_expression(list_ptr)
            self.asm.emit_mov_rbx_rax()
            
            self.compiler.compile_expression(index)
            # Bounds check would go here
            self.asm.emit_bytes(0x48, 0xC1, 0xE0, 0x03)  # SHL RAX, 3
            self.asm.emit_bytes(0x48, 0x8B, 0x44, 0x03, 0x10)  # MOV RAX, [RBX+RAX+16]
            
        else:
            raise ValueError(f"Unknown Collection function: {function}")

    def inline_convert_function(self, function, arguments):
        """Type conversion operations"""
        if function == "ToString":
            # Convert value to string
            arg_dict = dict(arguments)
            value = arg_dict.get('value')
            
            if not value:
                raise ValueError("Convert.ToString requires value")
            
            # Use NumberToString primitive
            node = FunctionCall('NumberToString', [value])
            self.compiler.compile_function_call(node)
            
        elif function == "ToNumber":
            # Convert string to number
            arg_dict = dict(arguments)
            string = arg_dict.get('string')
            
            if not string:
                raise ValueError("Convert.ToNumber requires string")
            
            # Use StringToNumber primitive
            node = FunctionCall('StringToNumber', [string])
            self.compiler.compile_function_call(node)
            
        else:
            raise ValueError(f"Unknown Convert function: {function}")

    def inline_memory_function(self, function, arguments):
        """Memory management operations"""
        if function == "Allocate":
            # Allocate memory block
            arg_dict = dict(arguments)
            size = arg_dict.get('size')
            
            if not size:
                raise ValueError("Memory.Allocate requires size")
            
            # Use Allocate primitive
            node = FunctionCall('Allocate', [size])
            self.compiler.compile_function_call(node)
            
        elif function == "Copy":
            # Copy memory block
            arg_dict = dict(arguments)
            dest = arg_dict.get('dest')
            src = arg_dict.get('src')
            size = arg_dict.get('size')
            
            if not all([dest, src, size]):
                raise ValueError("Memory.Copy requires dest, src, size")
            
            # Use MemoryCopy primitive
            node = FunctionCall('MemoryCopy', [dest, src, size])
            self.compiler.compile_function_call(node)
            
        elif function == "Set":
            # Set memory block to value
            arg_dict = dict(arguments)
            addr = arg_dict.get('address')
            value = arg_dict.get('value')
            size = arg_dict.get('size')
            
            if not all([addr, value, size]):
                raise ValueError("Memory.Set requires address, value, size")
            
            # Use MemorySet primitive
            node = FunctionCall('MemorySet', [addr, value, size])
            self.compiler.compile_function_call(node)
            
        else:
            raise ValueError(f"Unknown Memory function: {function}")

    def inline_math_function(self, function, arguments):
        """Mathematical operations beyond basic arithmetic"""
        if function == "Min":
            # Find minimum of two values
            arg_dict = dict(arguments)
            a = arg_dict.get('a')
            b = arg_dict.get('b')
            
            if not all([a, b]):
                raise ValueError("Math.Min requires a, b")
            
            self.compiler.compile_expression(a)
            self.asm.emit_push_rax()
            self.compiler.compile_expression(b)
            self.asm.emit_pop_rbx()
            
            # CMP RBX, RAX; CMOVL RAX, RBX
            self.asm.emit_bytes(0x48, 0x39, 0xC3)  # CMP RBX, RAX
            self.asm.emit_bytes(0x48, 0x0F, 0x4C, 0xC3)  # CMOVL RAX, RBX
            
        elif function == "Max":
            # Find maximum of two values
            arg_dict = dict(arguments)
            a = arg_dict.get('a')
            b = arg_dict.get('b')
            
            if not all([a, b]):
                raise ValueError("Math.Max requires a, b")
            
            self.compiler.compile_expression(a)
            self.asm.emit_push_rax()
            self.compiler.compile_expression(b)
            self.asm.emit_pop_rbx()
            
            # CMP RBX, RAX; CMOVG RAX, RBX
            self.asm.emit_bytes(0x48, 0x39, 0xC3)  # CMP RBX, RAX
            self.asm.emit_bytes(0x48, 0x0F, 0x4F, 0xC3)  # CMOVG RAX, RBX
            
        elif function == "Abs":
            # Absolute value
            arg_dict = dict(arguments)
            value = arg_dict.get('value')
            
            if not value:
                raise ValueError("Math.Abs requires value")
            
            self.compiler.compile_expression(value)
            # If negative, negate
            self.asm.emit_bytes(0x48, 0x89, 0xC3)  # MOV RBX, RAX
            self.asm.emit_bytes(0x48, 0xC1, 0xFB, 0x3F)  # SAR RBX, 63
            self.asm.emit_bytes(0x48, 0x31, 0xD8)  # XOR RAX, RBX
            self.asm.emit_bytes(0x48, 0x29, 0xD8)  # SUB RAX, RBX
            
        else:
            raise ValueError(f"Unknown Math function: {function}")
        
        
    def inline_lifetime_checker_function(self, function, arguments):
        """Lifetime checker operations"""
        if function == "Init":
            # Inline as HashCreate
            node = FunctionCall('HashCreate', [Number('256')])
            self.compiler.compile_function_call(node)
            # ... additional initialization
            
        elif function == "EnterScope":
            # Inline the scope entry logic
            # This would expand to the function body
            pass