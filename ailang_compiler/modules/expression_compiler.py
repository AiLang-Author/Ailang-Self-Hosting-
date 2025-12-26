#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Expression Compiler Module for AILANG Compiler
Handles expression evaluation
"""

import sys
import os
import struct
from ailang_parser.ailang_ast import *
from ailang_parser.ast_modules.ast_expressions import MemberAccess, Identifier
from ailang_parser.ast_modules.ast_memops import MemCompare, MemChr, MemFind, MemCopy


class ExpressionCompiler:
    """Handles expression compilation"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
     
     
    def _resolve_linkage_pool_type(self, base_name):
        """
        Helper to resolve LinkagePool type for a function parameter.
        Looks up the parameter type from the current function's AST node.
        """
        # This is the most reliable way: check the user_functions module directly
        # for the currently compiling function's parameter types.
        if hasattr(self.compiler, 'user_functions'):
            user_funcs = self.compiler.user_functions
            
            # Check if we are inside a function context
            if hasattr(user_funcs, 'current_function') and user_funcs.current_function:
                func_name = user_funcs.current_function
                
                # Get the function's metadata
                if func_name in user_funcs.user_functions:
                    func_info = user_funcs.user_functions[func_name]
                    param_types = func_info.get('param_types', {})
                    
                    # Look up the base name in this function's parameters
                    if base_name in param_types:
                        pool_type = param_types[base_name]
                        print(f"DEBUG: Resolved {base_name} -> {pool_type} from current function '{func_name}'")
                        return pool_type

        return None   
    
    def compile_member_access(self, node):
        """Compile member access like CFG.MAX"""
        # Resolve acronym in base object
        if isinstance(node.object, Identifier):
            base_name = node.object.name
            resolved_base = self.compiler.resolve_acronym(base_name)
            
            # Reconstruct the full name with the resolved base
            if isinstance(node.member, Identifier):
                member_name = node.member.name
                full_name = f"{resolved_base}.{member_name}"
                
                # Create a new Identifier node with the fully resolved name
                # and compile it using the existing identifier logic.
                resolved_identifier = Identifier(
                    name=full_name,
                    line=node.line,
                    column=node.column
                )
                self.compile_expression(resolved_identifier)
                return True
        return False
    

    def resolve_linkage_access(self, node):
        
        """
        Handles member access for LinkagePools with debugging and full implementation
        """
        print(f"\n=== RESOLVE_LINKAGE_ACCESS DEBUG ===")
        
        if not isinstance(node, MemberAccess):
            print(f"DEBUG: Not a MemberAccess node")
            return False

        base_name = node.object.name if hasattr(node.object, 'name') else str(node.object)
        field_name = node.member.name if hasattr(node.member, 'name') else node.member
        
        print(f"DEBUG: Accessing {base_name}.{field_name}")
        
        # Step 1: Determine the Pool Type
        pool_name = None
        
        # Check function parameters first
        if hasattr(self.compiler.user_functions, 'current_function') and self.compiler.user_functions.current_function:
            func_name = self.compiler.user_functions.current_function
            print(f"DEBUG: Current function: {func_name}")
            
            if func_name in self.compiler.user_functions.user_functions:
                func_info = self.compiler.user_functions.user_functions[func_name]
                param_types = func_info.get('param_types', {})
                
                if base_name in param_types:
                    pool_name = param_types[base_name]
                    print(f"DEBUG: Found param '{base_name}' with type '{pool_name}'")
                
                # Also check if it's in params list
                if base_name in func_info.get('params', []):
                    param_idx = func_info['params'].index(base_name)
                    print(f"DEBUG: '{base_name}' is parameter #{param_idx}")
        
        # Check acronym map
        if not pool_name and base_name in self.compiler.acronym_map:
            pool_name = self.compiler.acronym_map[base_name]
            print(f"DEBUG: Resolved acronym '{base_name}' to '{pool_name}'")
        
        # Check var_types
        if not pool_name and hasattr(self.compiler, 'var_types') and base_name in self.compiler.var_types:
            pool_name = self.compiler.var_types[base_name]
            print(f"DEBUG: Found type in var_types: '{pool_name}'")
        
        if not pool_name:
            print(f"DEBUG: Could not determine pool type for '{base_name}'")
            return False
        
        if pool_name not in self.compiler.linkage_pool_mgr.linkage_pools:
            print(f"DEBUG: Pool '{pool_name}' not defined")
            return False
        
        if field_name not in self.compiler.linkage_pool_mgr.linkage_pools[pool_name]:
            print(f"DEBUG: Field '{field_name}' not in pool '{pool_name}'")
            return False
        
        print(f"DEBUG: Valid LinkagePool field access: {pool_name}.{field_name}")
        
        # Step 2: Determine if this is a parameter or local variable
        is_parameter = False
        param_offset = None
        
        # Check if base_name is a function parameter
        if hasattr(self.compiler.user_functions, 'current_function') and self.compiler.user_functions.current_function:
            func_name = self.compiler.user_functions.current_function
            if func_name in self.compiler.user_functions.user_functions:
                func_info = self.compiler.user_functions.user_functions[func_name]
                if base_name in func_info.get('params', []):
                    is_parameter = True
                    # Parameters are at offsets 8, 16, 24, etc.
                    param_idx = func_info['params'].index(base_name)
                    param_offset = 8 * (param_idx + 1)
                    print(f"DEBUG: '{base_name}' is parameter at offset {param_offset}")
        
        # Step 3: Generate the correct code based on parameter vs local variable
        if is_parameter and param_offset:
            print(f"DEBUG: Accessing parameter LinkagePool at [RBP-{param_offset}]")
            
            # Load the LinkagePool pointer from the parameter stack slot
            # MOV RAX, [RBP - param_offset]
            self.asm.emit_bytes(0x48, 0x8B, 0x85)
            self.asm.emit_bytes(*struct.pack('<i', -param_offset))
            print(f"DEBUG: MOV RAX, [RBP-{param_offset}] (load LinkagePool pointer)")
            
            # Now RAX contains the pointer to the LinkagePool
            # Load the field at offset
            field_offset, _ = self.compiler.linkage_pool_mgr.linkage_pools[pool_name][field_name]
            
            if field_offset == 0:
                # MOV RAX, [RAX]
                self.asm.emit_bytes(0x48, 0x8B, 0x00)
                print(f"DEBUG: MOV RAX, [RAX] (load field at offset 0)")
            elif field_offset < 128:
                # MOV RAX, [RAX + offset]
                self.asm.emit_bytes(0x48, 0x8B, 0x40, field_offset)
                print(f"DEBUG: MOV RAX, [RAX+{field_offset}] (load field)")
            else:
                # MOV RAX, [RAX + offset] with 32-bit offset
                self.asm.emit_bytes(0x48, 0x8B, 0x80)
                self.asm.emit_bytes(*struct.pack('<i', field_offset))
                print(f"DEBUG: MOV RAX, [RAX+{field_offset}] (load field with 32-bit offset)")
            
            print(f"DEBUG: Successfully loaded {pool_name}.{field_name}")
            return True
            
        elif base_name in self.compiler.variables:
            # It's a local variable (created with AllocateLinkage)
            var_offset = self.compiler.variables[base_name]
            print(f"DEBUG: Accessing local LinkagePool variable at [RBP-{var_offset}]")
            
            # Load the LinkagePool pointer from local variable
            self.asm.emit_bytes(0x48, 0x8B, 0x85)
            self.asm.emit_bytes(*struct.pack('<i', -var_offset))
            print(f"DEBUG: MOV RAX, [RBP-{var_offset}] (load local LinkagePool pointer)")
            
            # Load the field
            field_offset, _ = self.compiler.linkage_pool_mgr.linkage_pools[pool_name][field_name]
            
            if field_offset == 0:
                self.asm.emit_bytes(0x48, 0x8B, 0x00)
            elif field_offset < 128:
                self.asm.emit_bytes(0x48, 0x8B, 0x40, field_offset)
            else:
                self.asm.emit_bytes(0x48, 0x8B, 0x80)
                self.asm.emit_bytes(*struct.pack('<i', field_offset))
            
            print(f"DEBUG: Loaded field at offset {field_offset}")
            return True
        
        else:
            print(f"ERROR: Cannot find '{base_name}' as parameter or variable")
            return False

    # Add this helper method to the ExpressionCompiler class:
    def compile_linkage_store(self, node):
        """
        Handle storing to LinkagePool fields (for assignments)
        This is called when a LinkagePool field appears on the LEFT side of assignment
        """
        if not isinstance(node, MemberAccess):
            return False
            
        base_name = node.object.name if hasattr(node.object, 'name') else str(node.object)
        field_name = node.member.name if hasattr(node.member, 'name') else node.member
        
        # Determine pool type (same logic as resolve_linkage_access)
        pool_name = None
        if base_name in self.compiler.acronym_map:
            pool_name = self.compiler.acronym_map[base_name]
        elif hasattr(self.compiler, 'var_types') and base_name in self.compiler.var_types:
            pool_name = self.compiler.var_types[base_name]
        elif hasattr(self.compiler.user_functions, 'current_function'):
            func_name = self.compiler.user_functions.current_function
            if func_name in self.compiler.user_functions.user_functions:
                param_types = self.compiler.user_functions.user_functions[func_name].get('param_types', {})
                if base_name in param_types:
                    pool_name = param_types[base_name]
        
        if not pool_name or pool_name not in self.compiler.linkage_pool_mgr.linkage_pools:
            return False
            
        if field_name not in self.compiler.linkage_pool_mgr.linkage_pools[pool_name]:
            return False
        
        # Check if it's a function parameter
        is_function_param = False
        param_stack_offset = None
        
        if hasattr(self.compiler.user_functions, 'current_function'):
            func_name = self.compiler.user_functions.current_function
            if func_name in self.compiler.user_functions.user_functions:
                func_info = self.compiler.user_functions.user_functions[func_name]
                if base_name in func_info['params']:
                    is_function_param = True
                    
                    if hasattr(self.compiler.linkage_pool_mgr, 'param_stack_offsets'):
                        if base_name in self.compiler.linkage_pool_mgr.param_stack_offsets:
                            param_stack_offset = self.compiler.linkage_pool_mgr.param_stack_offsets[base_name]
        
        # Store the field based on where the parameter is
        if is_function_param and param_stack_offset is not None:
            # Use stack-based store
            self.compiler.current_linkage_access_param = base_name
            self.compiler.linkage_pool_mgr.store_linkage_field_to_stack(
                base_name, pool_name, field_name, src_reg='rax'
            )
            if hasattr(self.compiler, 'current_linkage_access_param'):
                del self.compiler.current_linkage_access_param
            return True
            
        elif base_name in self.compiler.variables:
            # Local variable
            offset = self.compiler.variables[base_name]
            
            # Load pointer to R13
            self.asm.emit_push_r13()
            self.asm.emit_bytes(0x4C, 0x8B, 0xAD)
            self.asm.emit_bytes(*struct.pack('<i', -offset))
            
            # Store field using R13 as base
            self.compiler.linkage_pool_mgr.store_linkage_field(
                pool_name, field_name, src_reg='rax', base_reg='r13'
            )
            
            self.asm.emit_pop_r13()
            return True
        
        return False

    def compile_variable(self, var_name):
        """Compile a variable reference, handling LinkagePool parameters."""
        if var_name in self.compiler.variables:
            offset = self.compiler.variables[var_name]
            
            # NEW: Check if this is a LinkagePool parameter
            if hasattr(self.compiler, 'parameter_types'):
                param_type = self.compiler.parameter_types.get(var_name)
                if param_type and param_type.startswith('LinkagePool.'):
                    # This is a pointer stored on stack - load the VALUE
                    print(f"DEBUG: Loading LinkagePool pointer {var_name} from [RBP-{offset}]")
                    self.asm.emit_bytes(0x48, 0x8B, 0x85)  # MOV RAX, [RBP+disp32]
                    self.asm.emit_bytes(*struct.pack('<i', -offset))
                    return
            
            # Regular variable - existing code
            # self.load_local_variable(offset) # Assuming a method like this exists or is part of the logic below
            # For now, replicate the logic for a simple stack variable load
            self.asm.emit_bytes(0x48, 0x8b, 0x85)
            self.asm.emit_bytes(*struct.pack('<i', -offset))

    def compile_expression(self, expr):
        try:
            print(f"DEBUG compile_expression: expr type = {type(expr).__name__}, expr = {expr}")
            if isinstance(expr, Number):
                value_str = str(expr.value)
                if value_str.startswith('0x') or value_str.startswith('0X'):
                    self.asm.emit_mov_rax_imm64(int(value_str, 16))
                elif value_str.startswith('0b') or value_str.startswith('0B'):
                    self.asm.emit_mov_rax_imm64(int(value_str, 2))
                elif '.' in value_str or 'e' in value_str.lower():
                    self.asm.emit_mov_rax_imm64(int(float(value_str)))
                else:
                    self.asm.emit_mov_rax_imm64(int(value_str))
                    
            elif isinstance(expr, Identifier):
                # PRIORITY 1: Check if this is a DynamicPool member FIRST (before acronym resolution and ScopeManager)
                if '.' in expr.name:
                    parts = expr.name.split('.')
                    if len(parts) == 2:
                        pool_name = f"DynamicPool.{parts[0]}"
                        member_name = parts[1]
                        
                        # Check if this is a known DynamicPool member
                        if hasattr(self.compiler, 'memory') and hasattr(self.compiler.memory, 'dynamic_pool_metadata'):
                            if pool_name in self.compiler.memory.dynamic_pool_metadata:
                                if member_name in self.compiler.memory.dynamic_pool_metadata[pool_name]['members']:
                                    # This is a DynamicPool member - load from heap NOW before anything else
                                    print(f"DEBUG: Reading DynamicPool member {expr.name} (early detection)")
                                    
                                    # Get pool pointer from stack
                                    if pool_name in self.compiler.variables:
                                        pool_stack_offset = self.compiler.variables[pool_name]
                                        self.asm.emit_bytes(0x48, 0x8B, 0x85, *struct.pack('<i', -pool_stack_offset))  # MOV RAX, [RBP-offset]
                                        
                                        # Add member offset
                                        member_offset = self.compiler.memory.dynamic_pool_metadata[pool_name]['members'][member_name]
                                        if member_offset > 0:
                                            self.asm.emit_bytes(0x48, 0x05, *struct.pack('<I', member_offset))  # ADD RAX, offset
                                        
                                        # Dereference to get value
                                        self.asm.emit_bytes(0x48, 0x8B, 0x00)  # MOV RAX, [RAX]
                                        
                                        print(f"DEBUG: Loaded {expr.name} from DynamicPool at offset {member_offset}")
                                        return
                
                # PRIORITY 2: Resolve name for acronyms/field access
                if '.' in expr.name:
                    # This looks like field access (e.g., CUST.CustomerID)
                    # Don't expand via acronyms - keep the original name
                    resolved_name = expr.name
                    print(f"DEBUG: Dotted identifier {expr.name}, treating as field access (no acronym expansion)")
                else:
                    # Check if it's a function parameter FIRST
                    resolved_name = expr.name  # Start with original name
                    is_param = False

                    # Check if we're in a function and if this is a parameter
                    if hasattr(self.compiler.user_functions, 'current_function'):
                        func_name = self.compiler.user_functions.current_function
                        if func_name and func_name in self.compiler.user_functions.user_functions:
                            func_info = self.compiler.user_functions.user_functions[func_name]
                            if expr.name in func_info.get('params', []):
                                is_param = True
                                print(f"DEBUG: {expr.name} is a function parameter, skipping acronym resolution")

                    # Only resolve acronyms if it's NOT a parameter
                    if not is_param:
                        resolved_name = self.compiler.resolve_acronym(expr.name)
                        if resolved_name == expr.name:
                            resolved_name = self.compiler.resolve_acronym_identifier(expr.name)
                
                print(f"DEBUG: Final resolved_name: {resolved_name}")
                
                # NEW: Check for LinkagePool field access FIRST (before ScopeManager)
                if '.' in resolved_name:
                    base_name, field_name = resolved_name.split('.', 1)
                    
                    # Check if base is a LinkagePool pointer variable
                    if hasattr(self.compiler, 'pointer_types') and base_name in self.compiler.pointer_types:
                        pool_type = self.compiler.pointer_types[base_name]
                        print(f"DEBUG: LinkagePool field access {base_name}.{field_name}, type={pool_type}")
                        
                        # Load the pointer value into RAX
                        if base_name in self.compiler.variables:
                            offset = self.compiler.variables[base_name]
                            # Load pointer from stack
                            self.asm.emit_bytes(0x48, 0x8B, 0x85)  # MOV RAX, [RBP-offset]
                            self.asm.emit_bytes(*struct.pack('<i', -offset))
                            print(f"DEBUG: Loaded pointer from [RBP-{offset}]")
                            
                            # Get field offset from LinkagePool definition
                            if hasattr(self.compiler, 'linkage_pool_mgr'):
                                if pool_type in self.compiler.linkage_pool_mgr.linkage_pools:
                                    if field_name in self.compiler.linkage_pool_mgr.linkage_pools[pool_type]:
                                        field_offset, direction = self.compiler.linkage_pool_mgr.linkage_pools[pool_type][field_name]
                                        
                                        # Load field value from [RAX + field_offset]
                                        if field_offset == 0:
                                            self.asm.emit_bytes(0x48, 0x8B, 0x00)  # MOV RAX, [RAX]
                                        elif field_offset < 128:
                                            self.asm.emit_bytes(0x48, 0x8B, 0x40, field_offset)  # MOV RAX, [RAX+offset]
                                        else:
                                            self.asm.emit_bytes(0x48, 0x8B, 0x80)  # MOV RAX, [RAX+offset32]
                                            self.asm.emit_bytes(*struct.pack('<i', field_offset))
                                        
                                        print(f"DEBUG: Loaded field {field_name} from [pointer+{field_offset}]")
                                        return  # DONE - don't check ScopeManager

                # PRIORITY 3: Check scope manager for parameters
                if hasattr(self.compiler, 'scope_mgr'):
                    var_type, offset = self.compiler.scope_mgr.resolve(resolved_name)
                    if var_type == 'param':
                        # Load parameter from stack
                        self.asm.emit_bytes(0x48, 0x8b, 0x85)
                        self.asm.emit_bytes(*struct.pack('<i', -offset))
                        return
                    elif var_type == 'global':
                        # Handle global variables from ScopeManager
                        if offset & 0x80000000:
                            pool_index = offset & 0x7FFFFFFF
                            print(f"DEBUG: Loading pool var {resolved_name} from pool[{pool_index}] (via ScopeManager)")
                            # MOV RAX, [R15 + pool_index*8]
                            self.asm.emit_bytes(0x49, 0x8B, 0x87)
                            self.asm.emit_bytes(*struct.pack('<i', pool_index * 8))
                            return
                        else:
                            # Regular stack variable
                            print(f"DEBUG: Loading stack var {resolved_name} from [RBP-{offset}] (via ScopeManager)")
                            self.asm.emit_bytes(0x48, 0x8b, 0x85)
                            self.asm.emit_bytes(*struct.pack('<i', -offset))
                            return
                
                # CHECK: Is this a DynamicPool member? (secondary check after resolution)
                parts = resolved_name.split('.')
                if len(parts) == 2:
                    pool_name = f"DynamicPool.{parts[0]}"
                    member_name = parts[1]
                    
                    # Check if this is a known DynamicPool member
                    if hasattr(self.compiler, 'memory') and hasattr(self.compiler.memory, 'dynamic_pool_metadata'):
                        print(f"DEBUG CHECK: dynamic_pool_metadata keys: {list(self.compiler.memory.dynamic_pool_metadata.keys())}")
                        if pool_name in self.compiler.memory.dynamic_pool_metadata:
                            if member_name in self.compiler.memory.dynamic_pool_metadata[pool_name]['members']:
                                # This is a DynamicPool member - load from heap
                                print(f"DEBUG CHECK: pool_name={pool_name}, member_name={member_name}")
                                print(f"DEBUG: Reading DynamicPool member {resolved_name}")
                                
                                # Get pool pointer from stack
                                if pool_name in self.compiler.variables:
                                    pool_stack_offset = self.compiler.variables[pool_name]
                                    self.asm.emit_bytes(0x48, 0x8B, 0x85, *struct.pack('<i', -pool_stack_offset))  # MOV RAX, [RBP-offset]
                                    
                                    # Add member offset
                                    member_offset = self.compiler.memory.dynamic_pool_metadata[pool_name]['members'][member_name]
                                    if member_offset > 0:
                                        self.asm.emit_bytes(0x48, 0x05, *struct.pack('<I', member_offset))  # ADD RAX, offset
                                    
                                    # Dereference to get value
                                    self.asm.emit_bytes(0x48, 0x8B, 0x00)  # MOV RAX, [RAX]
                                    
                                    print(f"DEBUG: Loaded {resolved_name} from DynamicPool at offset {member_offset}")
                                    return
                
                # Try to find the variable
                if resolved_name not in self.compiler.variables:
                    # Try with pool type prefixes
                    pool_types = ['FixedPool', 'DynamicPool', 'TemporalPool', 
                                'NeuralPool', 'KernelPool', 'ActorPool', 
                                'SecurityPool', 'ConstrainedPool', 'FilePool']
                    
                    for pool_type in pool_types:
                        prefixed_name = f"{pool_type}.{resolved_name}"
                        if prefixed_name in self.compiler.variables:
                            resolved_name = prefixed_name
                            print(f"DEBUG: Resolved pool variable {expr.name} -> {prefixed_name}")
                            break
                
                if resolved_name in self.compiler.variables:
                    value = self.compiler.variables[resolved_name]
                    
                    # Check if this is a pool variable (high bit set)
                    if value & 0x80000000:  # Pool variable marker
                        pool_index = value & 0x7FFFFFFF  # Get actual index
                        print(f"DEBUG: Loading pool var {resolved_name} from pool[{pool_index}]")
                        # MOV RAX, [R15 + pool_index*8]
                        self.asm.emit_bytes(0x49, 0x8B, 0x87)  # MOV RAX, [R15 + disp32]
                        self.asm.emit_bytes(*struct.pack('<i', pool_index * 8))
                    else:
                        self.compile_variable(resolved_name)
                else:
                    # This should now only be reached for non-LinkagePool dotted names, if any.
                    raise ValueError(f"Unhandled identifier: {resolved_name}")
                    
            elif isinstance(expr, String):
                string_offset = self.asm.add_string(expr.value)
                self.asm.emit_load_data_address('rax', string_offset)
                print(f"DEBUG: Loaded string literal at data offset {string_offset}")
            elif isinstance(expr, MemberAccess): # Re-route to the new handler
                if not self.resolve_linkage_access(expr):
                    # Fallback to original member access if it's not a linkage pool
                    self.compile_member_access(expr)
            elif isinstance(expr, FunctionCall):
                self.compiler.compile_function_call(expr)
            elif isinstance(expr, Dereference):
                print("DEBUG: Compiling low-level operation: Dereference")
                self.compiler.lowlevel.compile_operation(expr)
            elif type(expr).__name__ == 'AddressOf':
                print("DEBUG: Compiling low-level operation: AddressOf")
                self.compiler.lowlevel.compile_operation(expr)
            elif type(expr).__name__ == 'SizeOf':
                print("DEBUG: Compiling low-level operation: SizeOf")
                self.compiler.lowlevel.compile_operation(expr)
            # === Memory Comparison Operations ===
            elif isinstance(expr, MemCompare):
                # self.compiler.emit_comment("MemCompare operation")
                return self.compiler.memcompare_ops.compile_memcompare([expr.addr1, expr.addr2, expr.length])
                
            elif isinstance(expr, MemChr):
                # self.compiler.emit_comment("MemChr operation")
                return self.compiler.memcompare_ops.compile_memchr([expr.addr, expr.byte_value, expr.length])
                
            elif isinstance(expr, MemFind):
                # self.compiler.emit_comment("MemFind operation")
                return self.compiler.memcompare_ops.compile_memfind([expr.haystack, expr.haystack_len, expr.needle, expr.needle_len])
            elif isinstance(expr, MemCopy):
                print("DEBUG: Compiling MemCopy expression")
                self.compiler._compile_function_call_dispatch(expr)
                return True
            else:
                raise ValueError(f"Unsupported expression type: {type(expr)}")
        except Exception as e:
            print(f"ERROR: Expression compilation failed: {str(e)}")
            raise
        
    

    