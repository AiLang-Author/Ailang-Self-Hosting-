# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Function Dispatch Module for AILANG Compiler
Implements dynamic function dispatch through CallIndirect and AddressOf
"""

import sys
import os
import struct
from ailang_parser.ailang_ast import *

class FunctionDispatch:
    """Dynamic function dispatch operations"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm

    def compile_operation(self, node):
        """Route to specific function dispatch handlers"""
        if hasattr(node, 'function'):
            function = node.function
            handlers = {
                'CallIndirect': self.compile_call_indirect,
                'AddressOf': self.compile_address_of
            }
            
            handler = handlers.get(function)
            if handler:
                return handler(node)
        elif isinstance(node, CallIndirect):
            return self.compile_call_indirect(node)
        elif isinstance(node, AddressOf):
            return self.compile_address_of(node)
        
        return False

    def compile_call_indirect(self, node):
        """CallIndirect(function_pointer, arg1, arg2, ...) - Call function through pointer"""
        try:
            print("DEBUG: Compiling CallIndirect")
            
            if hasattr(node, 'function_address'):
                function_expr = node.function_address
                arguments = node.arguments if hasattr(node, 'arguments') else []
            elif hasattr(node, 'arguments') and len(node.arguments) >= 1:
                # FunctionCall syntax: CallIndirect(func_ptr, arg1, arg2...)
                function_expr = node.arguments[0]
                arguments = node.arguments[1:] if len(node.arguments) > 1 else []
            else:
                raise ValueError("CallIndirect requires at least a function pointer")
            
            # Evaluate function pointer expression FIRST
            self.compiler.compile_expression(function_expr)
            self.asm.emit_push_rax()  # Save function pointer on stack
            
            # Set up arguments in registers (System V ABI)
            # RDI, RSI, RDX, RCX, R8, R9 for first 6 integer args
            arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
            
            # Handle arguments (up to 6 in registers, rest on stack)
            stack_args = 0
            
            # Push stack arguments in reverse order first
            if len(arguments) > 6:
                for i in range(len(arguments) - 1, 5, -1):
                    self.compiler.compile_expression(arguments[i])
                    self.asm.emit_push_rax()
                    stack_args += 1
            
            # Load register arguments
            for i, arg in enumerate(arguments[:6]):
                if i < len(arg_registers):
                    self.compiler.compile_expression(arg)
                    
                    # Move RAX to appropriate register
                    if arg_registers[i] == 'rdi':
                        self.asm.emit_mov_rdi_rax()
                    elif arg_registers[i] == 'rsi':
                        self.asm.emit_mov_rsi_rax()
                    elif arg_registers[i] == 'rdx':
                        self.asm.emit_mov_rdx_rax()
                    elif arg_registers[i] == 'rcx':
                        self.asm.emit_mov_rcx_rax()
                    elif arg_registers[i] == 'r8':
                        self.asm.emit_bytes(0x49, 0x89, 0xC0)  # MOV R8, RAX
                    elif arg_registers[i] == 'r9':
                        self.asm.emit_bytes(0x49, 0x89, 0xC1)  # MOV R9, RAX
            
            # Get function pointer from stack
            # It's at [RSP + stack_args * 8] because we pushed stack args after it
            if stack_args > 0:
                self.asm.emit_bytes(0x48, 0x8B, 0x84, 0x24)  # MOV RAX, [RSP + offset]
                self.asm.emit_bytes(*struct.pack('<i', stack_args * 8))
            else:
                # Function pointer is at top of stack
                self.asm.emit_pop_rax()  # POP RAX - get function pointer
                # DO NOT PUSH IT BACK!

            
            # Call through function pointer
            self.asm.emit_call_register('rax')
            
            # Clean up stack (function pointer + any stack args)
            total_cleanup = 8 + (stack_args * 8)
            if total_cleanup > 0:
                self.asm.emit_bytes(0x48, 0x83, 0xC4)  # ADD RSP, imm8
                self.asm.emit_bytes(total_cleanup & 0xFF)
            
            print("DEBUG: CallIndirect completed")
            return True
            
        except Exception as e:
            print(f"ERROR: CallIndirect compilation failed: {str(e)}")
            raise

    def compile_address_of(self, node):
        """AddressOf(FunctionName) or AddressOf(variable) - Get address of function or variable"""
        try:
            print("DEBUG: Compiling AddressOf")
            
            # Get target
            if hasattr(node, 'target'):
                target = node.target
            elif hasattr(node, 'arguments') and len(node.arguments) >= 1:
                if isinstance(node.arguments[0], Identifier):
                    target = node.arguments[0].name
                else:
                    raise ValueError("AddressOf requires an identifier")
            else:
                raise ValueError("AddressOf requires a target identifier")
            
            print(f"DEBUG: Getting address of '{target}'")
            
            # Check if it's a function first - FIXED LOOKUP
            if hasattr(self.compiler, 'user_functions'):
                # Look in the actual user_functions dictionary
                if target in self.compiler.user_functions.user_functions:
                    # Get function info and label
                    func_info = self.compiler.user_functions.user_functions[target]
                    label = func_info['label']
                    self.asm.emit_load_label_address('rax', label)
                    print(f"DEBUG: Got function address for {target} with label {label}")
                    return True
                
                # Also try with Function. prefix stripped (in case of Function.TestFunc)
                if target.startswith("Function."):
                    clean_target = target[9:]
                    if clean_target in self.compiler.user_functions.user_functions:
                        func_info = self.compiler.user_functions.user_functions[clean_target]
                        label = func_info['label']
                        self.asm.emit_load_label_address('rax', label)
                        print(f"DEBUG: Got function address for {clean_target} with label {label}")
                        return True
            
            # Check if it's a variable
            resolved_name = self.compiler.resolve_acronym_identifier(target)
            if resolved_name in self.compiler.variables:
                # Get variable address
                offset = self.compiler.variables[resolved_name]
                self.asm.emit_lea_rax("RBP", -offset)
                print(f"DEBUG: Got variable address for {resolved_name} at [RBP-{offset}]")
                return True
            
            # Check global/library functions 
            if hasattr(self.compiler, 'library_inliner'):
                if self.compiler.library_inliner.is_library_function(target):
                    # For library functions, we may need to create wrappers
                    # For now, return 0 (null pointer)
                    self.asm.emit_mov_rax_imm64(0)
                    print(f"WARNING: AddressOf for library function {target} not fully implemented")
                    return True
            
            raise ValueError(f"Symbol not found: {target}")
            
        except Exception as e:
            print(f"ERROR: AddressOf compilation failed: {str(e)}")
            raise

# Add AST node classes if not already defined
class CallIndirect:
    def __init__(self, function_address, arguments):
        self.function_address = function_address
        self.arguments = arguments if arguments else []

class AddressOf:
    def __init__(self, target):
        self.target = target