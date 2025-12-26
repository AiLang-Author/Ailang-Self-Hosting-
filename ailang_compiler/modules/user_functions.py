#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
User-Defined Functions Module for AILANG Compiler
Implements support for Function.Category.Name definitions
"""

import struct
from ailang_parser.ailang_ast import *

class UserFunctions:
    """Handles user-defined function compilation and calls"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        
        # Track user-defined functions
        # Key: "Category.Name", Value: {'label': label, 'params': [...], 'node': ast_node}
        self.user_functions = {}
        
        # Track current function context for returns
        self.current_function = None

    def is_function_registered(self, func_name: str) -> bool:
        """Checks if a function name has been registered."""
        # This is the method that ailang_compiler.py expects to exist.
        return func_name in self.user_functions
        
    def register_function(self, node):
        """Register a user-defined function during first pass"""
        try:
            # Extract function name from node
            func_name = node.name

            # CRITICAL FIX: Strip "Function." prefix if present
            if func_name.startswith("Function."):
                func_name = func_name[9:]  # Remove "Function." prefix

            # Generate unique label for this function
            label = self.asm.create_label()

            # NEW: Extract parameter names AND types from input_params list of tuples
            params = []
            param_types = {}  # Map param_name -> type
            
            for param in node.input_params:
                param_name = param[0]
                param_type = param[1] if len(param) > 1 else None
                params.append(param_name)
                
                if param_type:
                    # Convert TypeExpression to string
                    if hasattr(param_type, 'base_type'):
                        param_type_str = param_type.base_type
                    else:
                        param_type_str = str(param_type)
                    param_types[param_name] = param_type_str
        
            # Store function info
            self.user_functions[func_name] = {
                'label': label,
                'params': params,
                'param_types': param_types,  # NEW: Store parameter types
                'node': node,
                'compiled': False
            }

            print(f"DEBUG: Registered user function: {func_name} with params {params} at label {label}")
            if param_types:
                print(f"DEBUG: Parameter types: {param_types}")
            
            return label

        except Exception as e:
            print(f"ERROR: Failed to register function: {str(e)}")
            raise
    
    def compile_function_definition(self, node):
        """Compile a function definition"""
        try:
            func_name = node.name
            
            # CRITICAL FIX: Strip "Function." prefix if present
            if func_name.startswith("Function."):
                func_name = func_name[9:]
            
            if func_name not in self.user_functions:
                # Register it first (will also strip prefix)
                self.register_function(node)
            
            func_info = self.user_functions[func_name]
            
            # Skip if already compiled
            if func_info['compiled']:
                return
            
            print(f"DEBUG: Compiling function {func_name}")
            
            # Save current function context
            old_function = self.current_function
            self.current_function = func_name
            
            # CRITICAL FIX: Save global variable scope
            saved_variables = self.compiler.variables.copy()
            saved_stack_size = self.compiler.stack_size
            
            # Create fresh local scope but PRESERVE POOL VARIABLES
            self.compiler.variables = {}
            self.compiler.stack_size = 0
            
            # Copy pool variables (high bit set) to local scope
            # Pool variables are global and should be accessible everywhere
            for var_name, var_value in saved_variables.items():
                if var_value & 0x80000000:  # Pool variable marker
                    self.compiler.variables[var_name] = var_value
                    print(f"DEBUG: Preserved pool variable {var_name} in local scope")
            
            # Push function scope for parameter tracking
            if hasattr(self.compiler, 'scope_mgr'):
                self.compiler.scope_mgr.push_function(func_name)
            
            # CRITICAL FIX: Jump over function definition during normal execution
            skip_label = self.asm.create_label()
            self.asm.emit_jump_to_label(skip_label, "JMP")
            
            # Mark function entry point
            label = func_info['label']
            self.asm.mark_label(label)
            
            # Function prologue
            self.asm.emit_push_rbp()
            self.asm.emit_mov_rbp_rsp()

            # --- FIX: Save all callee-saved registers ---
            self.asm.emit_push_rbx()
            self.asm.emit_push_r12()
            self.asm.emit_push_r13()
            self.asm.emit_push_r14()
            
            # --- CRITICAL FIX: Handle LinkagePool parameters FIRST ---
            # This must happen before parameter registers (RDI, RSI) are used for anything else.
            # This moves the incoming linkage block pointers into their dedicated base registers (R14, R15).
            handled_params = []
            if hasattr(self.compiler, 'linkage_pool_mgr'):
                handled_params = self.compiler.linkage_pool_mgr.compile_function_with_linkage(node)
                if handled_params is None:
                    handled_params = []
                print(f"DEBUG: LinkagePool handled parameters at indices: {handled_params}")

            
            # --- FIX: Dynamically calculate local variable space ---
            # Pre-scan function body to calculate space needed for locals.
            known_vars = set(self.compiler.variables.keys()) # Params + pool vars
            local_vars_needed = self.compiler.memory.scan_for_locals(node.body, known_vars)
            callee_saved_regs_space = 32 # 4 registers * 8 bytes (RBX, R12, R13, R14)
            
            param_count = len(func_info['params'])
            local_space = len(local_vars_needed) * 16 # 16 bytes per local for safety
            print(f"DEBUG: Function '{func_name}' requires space for {param_count} params and {len(local_vars_needed)} locals ({local_space} bytes).")
            if param_count > 0 or local_space > 0:
                # Allocate space for parameters, locals, AND the 4 callee-saved registers
                stack_space = ((param_count * 8 + local_space + callee_saved_regs_space + 15) // 16) * 16
                
                
                # FIX: Use proper instruction encoding for stack allocation
                if stack_space < 128:
                    # Small immediate: SUB RSP, imm8
                    self.asm.emit_bytes(0x48, 0x83, 0xEC, stack_space)
                else:
                    # Large immediate: SUB RSP, imm32
                    self.asm.emit_bytes(0x48, 0x81, 0xEC)
                    self.asm.emit_bytes(*struct.pack('<I', stack_space))
                
                print(f"DEBUG: Allocated {stack_space} bytes for function locals")
            
            # Register parameters in LOCAL scope
            for i, param_name in enumerate(func_info['params']):
                # NEW: Check parameter type FIRST
                param_type = func_info.get('param_types', {}).get(param_name)
                if param_type and param_type.startswith('LinkagePool.'):
                    print(f"DEBUG: Skipping LinkagePool param {param_name} - handled by LinkagePool module")
                    # Track this globally for field access
                    if not hasattr(self.compiler, 'pointer_types'):
                        self.compiler.pointer_types = {}
                    self.compiler.pointer_types[param_name] = param_type
                    print(f"DEBUG: Tracked parameter type: {param_name} -> {param_type}")
                    continue  # LinkagePool module handles this completely

                if i in handled_params:
                    continue  # This should never happen now

                # NEW: Get parameter type from func_info
                param_type = func_info.get('param_types', {}).get(param_name)
                if param_type and hasattr(self.compiler, 'parameter_types'):
                    # Store in global parameter_types for field access resolution
                    self.compiler.parameter_types[param_name] = param_type
                    print(f"DEBUG: Stored parameter type: {param_name} -> {param_type}")
                
                self.compiler.stack_size += 8
                offset = self.compiler.stack_size
                self.compiler.variables[param_name] = offset
                print(f"DEBUG: Param {param_name} at local offset {offset}")
                
                # Register parameter in scope manager - THIS IS THE KEY FIX
                if hasattr(self.compiler, 'scope_mgr'):
                    self.compiler.scope_mgr.add_parameter(param_name, offset)
                    print(f"DEBUG: Registered param {param_name} with scope manager at offset {offset}")
                
                # Move from register to stack
                if i == 0:
                    self.asm.emit_mov_rax_rdi()
                elif i == 1:
                    self.asm.emit_mov_rax_rsi()
                elif i == 2:
                    self.asm.emit_bytes(0x48, 0x89, 0xD0)  # MOV RAX, RDX
                elif i == 3:
                    self.asm.emit_mov_rax_rcx()
                elif i == 4:
                    self.asm.emit_bytes(0x4C, 0x89, 0xC0)  # MOV RAX, R8
                elif i == 5:
                    self.asm.emit_bytes(0x4C, 0x89, 0xC8)  # MOV RAX, R9
                
                # Store to LOCAL stack frame (use 32-bit offset to avoid wraparound)
                self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP+disp32], RAX
                self.asm.emit_bytes(*struct.pack('<i', -offset))
                print(f"DEBUG: Param {param_name} stored at [RBP-{offset}]")
            
            # Compile function body with local scope
            if hasattr(node, 'body'):
                for stmt in node.body:
                    self.compiler.compile_node(stmt)
            
            # Default return value if no explicit return
            if not self._has_return_statement(node):
                self.compile_return(None)
            
            # Mark as compiled
            func_info['compiled'] = True
            
            # CRITICAL FIX: Mark the skip label to continue normal execution
            self.asm.mark_label(skip_label)
            
            # Pop function scope
            if hasattr(self.compiler, 'scope_mgr'):
                self.compiler.scope_mgr.pop()
            
            # Restore function context
            self.current_function = old_function
            
            # CRITICAL FIX: Restore global variable scope
            self.compiler.variables = saved_variables
            self.compiler.stack_size = saved_stack_size

            # CRITICAL FIX: Clear linkage param types after function is compiled
            if hasattr(self.compiler, 'linkage_param_types'):
                self.compiler.linkage_param_types.clear()
                print("DEBUG: Cleared linkage_param_types on function exit")
            
            print(f"DEBUG: Function {func_name} compiled successfully")
            
        except Exception as e:
            print(f"ERROR: Failed to compile function {func_name}: {str(e)}")
            raise
            
    def _count_local_variables(self, body):
        """Count local variables that will be created in function body"""
        # Simple heuristic - count assignments
        count = 0
        for stmt in body:
            if hasattr(stmt, 'target'):  # Assignment
                count += 1
        return count + 10  # Add some extra space for temporaries
    
    def compile_function_call(self, node):
        """Compile a call to a user-defined function"""
        try:
            func_name = node.function
            
            if func_name not in self.user_functions:
                return False
            
            func_info = self.user_functions[func_name]
            print(f"DEBUG: Compiling call to user function: {func_name}")
            
            # --- NEW: Check for LinkagePool arguments BEFORE push/pop ---
            linkage_args = []  # List of (arg_index, arg_node, param_name, param_type)
            
            if hasattr(node, 'arguments') and node.arguments:
                for i, arg in enumerate(node.arguments[:6]):  # Only first 6 args use registers
                    if i < len(func_info['params']):
                        param_name = func_info['params'][i]
                        param_type = func_info.get('param_types', {}).get(param_name)
                        
                        # Check if this parameter expects a LinkagePool
                        if param_type and param_type.startswith('LinkagePool.'):
                            # Check if the argument is a LinkagePool variable or parameter
                            arg_is_linkage = False
                            arg_var_name = None
                            
                            # Check if arg is a simple identifier
                            if hasattr(arg, 'name'):
                                arg_var_name = arg.name
                                
                                # Is it a LinkagePool parameter of the calling function?
                                if hasattr(self.compiler, 'parameter_types'):
                                    arg_type = self.compiler.parameter_types.get(arg_var_name)
                                    if arg_type and arg_type.startswith('LinkagePool.'):
                                        arg_is_linkage = True
                                        print(f"DEBUG: Arg {i} '{arg_var_name}' is a LinkagePool parameter")
                                
                                # Is it a local LinkagePool variable?
                                if not arg_is_linkage and hasattr(self.compiler, 'pointer_types'):
                                    if arg_var_name in self.compiler.pointer_types:
                                        arg_is_linkage = True
                                        print(f"DEBUG: Arg {i} '{arg_var_name}' is a local LinkagePool variable")
                            
                            if arg_is_linkage and arg_var_name:
                                linkage_args.append((i, arg, param_name, param_type, arg_var_name))
            
            # --- Handle LinkagePool arguments specially ---
            if linkage_args:
                print(f"DEBUG: Found {len(linkage_args)} LinkagePool arguments")
                
                # System V AMD64 ABI: First 6 args go in RDI, RSI, RDX, RCX, R8, R9
                arg_regs = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
                
                # Process arguments in order
                for i in range(len(node.arguments[:6])):
                    arg = node.arguments[i]
                    
                    # Check if this is a LinkagePool argument
                    is_linkage = any(la[0] == i for la in linkage_args)
                    
                    if is_linkage:
                        # Find the linkage arg info
                        la_info = next(la for la in linkage_args if la[0] == i)
                        arg_var_name = la_info[4]
                        
                        print(f"DEBUG: Loading LinkagePool '{arg_var_name}' into {arg_regs[i].upper()}")
                        
                        # Load the LinkagePool pointer from stack into RAX
                        if arg_var_name in self.compiler.variables:
                            offset = self.compiler.variables[arg_var_name]
                            # MOV RAX, [RBP - offset]
                            self.asm.emit_bytes(0x48, 0x8B, 0x85)
                            self.asm.emit_bytes(*struct.pack('<i', -offset))
                            print(f"DEBUG: Loaded pointer from [RBP-{offset}]")
                        else:
                            print(f"ERROR: LinkagePool variable '{arg_var_name}' not found!")
                            self.asm.emit_mov_rax_imm64(0)
                        
                        # Move RAX into the appropriate parameter register
                        if arg_regs[i] == 'rdi':
                            self.asm.emit_bytes(0x48, 0x89, 0xC7)  # MOV RDI, RAX
                        elif arg_regs[i] == 'rsi':
                            self.asm.emit_bytes(0x48, 0x89, 0xC6)  # MOV RSI, RAX
                        elif arg_regs[i] == 'rdx':
                            self.asm.emit_bytes(0x48, 0x89, 0xC2)  # MOV RDX, RAX
                        elif arg_regs[i] == 'rcx':
                            self.asm.emit_bytes(0x48, 0x89, 0xC1)  # MOV RCX, RAX
                        elif arg_regs[i] == 'r8':
                            self.asm.emit_bytes(0x49, 0x89, 0xC0)  # MOV R8, RAX
                        elif arg_regs[i] == 'r9':
                            self.asm.emit_bytes(0x49, 0x89, 0xC1)  # MOV R9, RAX
                        
                        print(f"DEBUG: Moved pointer into {arg_regs[i].upper()}")
                        
                    else:
                        # Regular argument - evaluate and put in register
                        self.compiler.compile_expression(arg)
                        
                        # Move RAX into the appropriate parameter register
                        if arg_regs[i] == 'rdi':
                            self.asm.emit_bytes(0x48, 0x89, 0xC7)  # MOV RDI, RAX
                        elif arg_regs[i] == 'rsi':
                            self.asm.emit_bytes(0x48, 0x89, 0xC6)  # MOV RSI, RAX
                        elif arg_regs[i] == 'rdx':
                            self.asm.emit_bytes(0x48, 0x89, 0xC2)  # MOV RDX, RAX
                        elif arg_regs[i] == 'rcx':
                            self.asm.emit_bytes(0x48, 0x89, 0xC1)  # MOV RCX, RAX
                        elif arg_regs[i] == 'r8':
                            self.asm.emit_bytes(0x49, 0x89, 0xC0)  # MOV R8, RAX
                        elif arg_regs[i] == 'r9':
                            self.asm.emit_bytes(0x49, 0x89, 0xC1)  # MOV R9, RAX
            
            else:
                # --- ORIGINAL LOGIC: No LinkagePool args, use push/pop ---
                # 1. Evaluate all arguments and push their results onto the stack in reverse order.
                if hasattr(node, 'arguments') and node.arguments:
                    num_args = len(node.arguments[:6])
                    for i in range(num_args - 1, -1, -1):
                        arg = node.arguments[i]
                        self.compiler.compile_expression(arg)
                        self.asm.emit_push_rax()
                
                # 2. Pop the results from the stack into the correct parameter registers.
                if hasattr(node, 'arguments') and node.arguments:
                    num_args = len(node.arguments[:6])
                    arg_regs = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
                    pop_methods = {
                        'rdi': self.asm.emit_pop_rdi, 'rsi': self.asm.emit_pop_rsi,
                        'rdx': self.asm.emit_pop_rdx, 'rcx': self.asm.emit_pop_rcx,
                        'r8': self.asm.emit_pop_r8,   'r9': self.asm.emit_pop_r9
                    }
                    
                    for i in range(num_args):
                        if i < len(arg_regs):
                            pop_methods[arg_regs[i]]()
            
            # Align stack before CALL (must be 16-byte aligned)
            self.asm.emit_bytes(0x48, 0x83, 0xE4, 0xF0)  # AND RSP, -16
            
            # Emit CALL instruction
            label = func_info['label']
            current_pos = len(self.asm.code)
            self.asm.emit_bytes(0xE8)  # CALL opcode
            
            if label in self.asm.labels:
                target_pos = self.asm.labels[label]
                offset = target_pos - (current_pos + 5)
                self.asm.emit_bytes(*struct.pack('<i', offset))
                print(f"DEBUG: CALL offset: {offset} ({hex(offset)})")
            else:
                # Forward reference
                self.asm.emit_bytes(0x00, 0x00, 0x00, 0x00)
                if not hasattr(self.compiler, 'user_function_fixups'):
                    self.compiler.user_function_fixups = []
                self.compiler.user_function_fixups.append((func_name, current_pos))
                print(f"DEBUG: Forward reference added")
            
            # Result is in RAX
            print(f"DEBUG: User function {func_name} called")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to call function {func_name}: {str(e)}")
            raise
        
    def compile_return(self, value_node):
        """Compile ReturnValue statement"""
        try:
            print(f"DEBUG: Compiling ReturnValue")
            
            # Compile return value to RAX if provided
            if value_node:
                self.compiler.compile_expression(value_node)
            else:
                # Default return 0
                self.asm.emit_mov_rax_imm64(0)

            # Check if we're in a SubRoutine context
            if hasattr(self.compiler, 'compiling_subroutine') and self.compiler.compiling_subroutine:
                print("DEBUG: ReturnValue in SubRoutine - jumping to return label")
                # Jump to the subroutine's return label
                if hasattr(self.compiler, 'subroutine_return_label'):
                    self.asm.emit_jump_to_label(self.compiler.subroutine_return_label, "JMP")
                return
            
            # In a user Function context - do full epilogue
            if hasattr(self, 'current_function') and self.current_function:
                print("DEBUG: ReturnValue in Function - full epilogue")
                # Restore callee-saved registers
                self.asm.emit_pop_r14()
                self.asm.emit_pop_r13()
                self.asm.emit_pop_r12()
                self.asm.emit_pop_rbx()
                
                # Function epilogue
                self.asm.emit_mov_rsp_rbp()
                self.asm.emit_pop_rbp()
                self.asm.emit_ret()
            else:
                # Not in any special context
                print("DEBUG: ReturnValue in unknown context - value in RAX only")
            
            print(f"DEBUG: ReturnValue compiled")
            
        except Exception as e:
            print(f"ERROR: Failed to compile return: {str(e)}")
            raise
    
    def _has_return_statement(self, node):
        """Check if function has explicit return statement"""
        if hasattr(node, 'body'):
            for stmt in node.body:
                if hasattr(stmt, 'type') and stmt.type == 'ReturnValue':
                    return True
                # Could be FunctionCall to ReturnValue
                if isinstance(stmt, FunctionCall) and stmt.function == 'ReturnValue':
                    return True
        return False
    
    def process_all_functions(self, ast):
        """First pass: find and register all function definitions"""
        try:
            self._find_functions_in_node(ast)
            print(f"DEBUG: Found {len(self.user_functions)} user-defined functions")
        except Exception as e:
            print(f"ERROR: Failed to process functions: {str(e)}")
            raise
    
    def _find_functions_in_node(self, node):
        """Recursively find function definitions"""
        from ailang_parser.ailang_ast import Function
        
        # Check if it's a Function node by class
        if isinstance(node, Function):
            self.register_function(node)
        
        # Check for nested structures
        if hasattr(node, 'body'):
            if isinstance(node.body, list):
                for item in node.body:
                    self._find_functions_in_node(item)
        
        if hasattr(node, 'declarations'):
            for decl in node.declarations:
                self._find_functions_in_node(decl)