#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Memory Management Module for AILANG Compiler
Handles stack allocation, variable management, and pool operations
"""

import struct
import traceback
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ailang_parser')))
from ailang_ast import *
from ailang_parser.ailang_ast import *

class MemoryManager: 
    """Handles memory-related operations"""    
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        self.pool_metadata = {}
        self.dynamic_pool_metadata = {}
        self.allocation_headers = {}
        # Add these new lines:
        self.pool_variables = {}  
        self.pool_index_counter = 0
        self.POOL_MARKER = 0x80000000
        self.pool_table_allocated = False
        
        
    def discover_pool_variables(self, node):
        """A pre-pass to find all pool variables and mark them before compilation."""
        print("DEBUG: ===== DISCOVER_POOL_VARIABLES called =====")
        
        if not hasattr(node, 'declarations'):
            print("DEBUG: Node has NO declarations attribute!")
            return
        
        print(f"DEBUG: Node has {len(node.declarations)} declarations")
        
        # First pass: List ALL declarations
        for i, decl in enumerate(node.declarations):
            decl_type = type(decl).__name__
            name = getattr(decl, 'name', '<no name>')
            print(f"DEBUG: Declaration [{i}]: Type={decl_type}, Name={name}")

        # Second pass: Process ONLY FixedPool declarations (not DynamicPool!)
        for decl in node.declarations:
            if isinstance(decl, Pool) and decl.pool_type == "FixedPool":
                pool_name = f"{decl.pool_type}.{decl.name}"
                print(f"DEBUG: Pre-scanning FixedPool {pool_name} for variables.")
                for item in decl.body:
                    if hasattr(item, 'key'):
                        var_name = f"{pool_name}.{item.key}"
                        if var_name not in self.compiler.variables:
                            pool_index = self.pool_index_counter
                            self.pool_index_counter += 1
                            pool_marker = self.POOL_MARKER | pool_index
                            self.pool_variables[var_name] = pool_index
                            self.compiler.variables[var_name] = pool_marker
                            print(f"DEBUG: Discovered FixedPool var '{var_name}' at pool index {pool_index}")
        
        total = self.pool_index_counter
        print(f"DEBUG: ===== DISCOVER_POOL_VARIABLES done - found {total} FixedPool vars =====")
    
    
    
    def compile_program(self, node):
        """Compile Program with stack management and pool table setup"""
        try:
            print("DEBUG: Starting program compilation")
            self.discover_pool_variables(node)
            self.allocate_pool_table()  # Allocate pool table after discovery
            #  Discover actors to determine table size ---
            self.compiler.scheduler.discover_actors(node)
            self.calculate_stack_size(node)
            
            # Pre-allocate system variables for actor system
            if 'system_acb_table' not in self.compiler.variables:
                self.compiler.stack_size += 8
                offset = self.compiler.stack_size
                self.compiler.variables['system_acb_table'] = offset
                print(f"DEBUG: Allocated system_acb_table at stack offset {offset}")
            
            if 'system_current_actor' not in self.compiler.variables:
                self.compiler.stack_size += 8
                offset = self.compiler.stack_size
                self.compiler.variables['system_current_actor'] = offset
                print(f"DEBUG: Allocated system_current_actor at stack offset {offset}")
            
            print_buffer_size = 64
            temp_space = 128
            red_zone = 128
            allocate_space = self.scan_allocate_sizes(node)
            # --- FIX: Use discovered actor count for table size ---
            acb_table_size = self.compiler.scheduler.max_actors * self.compiler.scheduler.acb_size
            
            print(f"DEBUG: Total Allocate space needed: {allocate_space}")
            total_space = self.compiler.stack_size + print_buffer_size + temp_space + red_zone + allocate_space + acb_table_size
            print(f"DEBUG: Stack calculation - {len(self.compiler.variables)} vars = {self.compiler.stack_size} bytes, ACB table = {acb_table_size} bytes, total allocated: {total_space}")
            
            self.compiler.codegen.emit_stack_frame_prologue(total_space)
            
            # Zero-initialize only stack variables (not pool markers)
            for var_name, offset in self.compiler.variables.items():
                if not (offset & 0x80000000):  # Only stack variables
                    self.asm.emit_mov_rax_imm64(0)
                    self.asm.emit_bytes(0x48, 0x89, 0x85)
                    self.asm.emit_bytes(*struct.pack('<i', -offset))
                    print(f"DEBUG: Zero-initialized {var_name} at [rbp - {offset}]")
            
            # Initialize ACB table pointer
            acb_table_offset = total_space - acb_table_size
            self.asm.emit_bytes(0x48, 0x8D, 0x85)  # LEA RAX, [RBP - offset]
            self.asm.emit_bytes(*struct.pack('<i', -acb_table_offset))
            
            offset = self.compiler.variables['system_acb_table']
            self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP - offset], RAX
            self.asm.emit_bytes(*struct.pack('<i', -offset))
            print(f"DEBUG: Initialized ACB table pointer at [RBP - {acb_table_offset}]")
            
            # Initialize current actor to 0
            self.asm.emit_mov_rax_imm64(0)
            offset = self.compiler.variables['system_current_actor']
            self.asm.emit_bytes(0x48, 0x89, 0x85)
            self.asm.emit_bytes(*struct.pack('<i', -offset))
            print(f"DEBUG: Initialized current_actor to 0")
            
            # Save callee-saved registers (NOT R15!)
            self.asm.emit_push_rbx()
            self.compiler.track_push("Program save RBX")
            self.asm.emit_push_r12()
            self.compiler.track_push("Program save R12")
            self.asm.emit_push_r13()
            self.compiler.track_push("Program save R13")
            self.asm.emit_push_r14()
            self.compiler.track_push("Program save R14")
            
            # NOW compile all declarations (including pools)
            # Pool initialization code will now have R15 set correctly
            for decl in node.declarations:
                self.compiler.compile_node(decl)
            
            # Restore callee-saved registers (NOT R15!)
            self.compiler.track_pop("Program restore R14")
            self.asm.emit_pop_r14()
            self.compiler.track_pop("Program restore R13")
            self.asm.emit_pop_r13()
            self.compiler.track_pop("Program restore R12")
            self.asm.emit_pop_r12()
            self.compiler.track_pop("Program restore RBX")
            self.asm.emit_pop_rbx()
            self.compiler.codegen.emit_stack_frame_epilogue()
            
            self.asm.emit_mov_rax_imm64(60)
            self.asm.emit_mov_rdi_imm64(0)
            self.asm.emit_syscall()
            
            print("DEBUG: Program compilation completed")
        except Exception as e:
            print(f"ERROR: Program compilation failed: {str(e)}")
            self.compiler.codegen.emit_stack_frame_epilogue()
            raise
        
    def calculate_stack_size(self, node, depth=0):
        """Calculate stack size for variables"""
        if depth > 100:
            print(f"WARNING: Deep recursion detected at depth {depth}")
            return
            
        self.compiler.max_depth = max(self.compiler.max_depth, depth)
        
        node_type = type(node).__name__
        
        if hasattr(node, 'declarations'):  # Program node
            for decl in node.declarations:
                self.calculate_stack_size(decl, depth + 1)
        
        # ==================== ADD THIS SECTION ====================
        elif node_type == 'Function':
            # Traverse function parameters
            if hasattr(node, 'parameters') and node.parameters:
                for param in node.parameters:
                    # Parameters need stack space too
                    if hasattr(param, 'name'):
                        param_name = param.name
                        if param_name not in self.compiler.variables:
                            self.compiler.stack_size += 8  # Parameters are typically 8 bytes
                            self.compiler.variables[param_name] = self.compiler.stack_size
                            print(f"DEBUG: Allocated parameter {param_name} at stack offset {self.compiler.stack_size}")
            
            # Traverse function body
            if hasattr(node, 'body') and node.body:
                for stmt in node.body:
                    self.calculate_stack_size(stmt, depth + 1)
            print(f"DEBUG: Scanned Function {node.name if hasattr(node, 'name') else 'unnamed'}")
        
        elif node_type == 'SubRoutine':
            # SubRoutines don't have parameters but still have bodies
            if hasattr(node, 'body') and node.body:
                for stmt in node.body:
                    self.calculate_stack_size(stmt, depth + 1)
            print(f"DEBUG: Scanned SubRoutine {node.name if hasattr(node, 'name') else 'unnamed'}")
        # ==================== END ADDITION ====================
            
        elif node_type == 'Assignment' or (hasattr(node, 'target') and hasattr(node, 'value')):
            target_name = node.target
            
            # Check if this is a DynamicPool member (PoolName.member format)
            is_dynamic_pool_member = False
            if '.' in target_name:
                parts = target_name.split('.')
                if len(parts) == 2:
                    pool_name = f"DynamicPool.{parts[0]}"
                    if pool_name in self.dynamic_pool_metadata:
                        member_name = parts[1]
                        if member_name in self.dynamic_pool_metadata[pool_name]['members']:
                            is_dynamic_pool_member = True
                            print(f"DEBUG: Skipping allocation for {target_name} (DynamicPool member)")
            
            # Check if FixedPool variable
            resolved_name = None
            if target_name in self.compiler.variables:
                resolved_name = target_name
            elif not is_dynamic_pool_member:
                # Try FixedPool prefix
                prefixed = f"FixedPool.{target_name}"
                if prefixed in self.compiler.variables:
                    resolved_name = prefixed
            
            # Only allocate if NOT a pool variable
            if resolved_name is None and not is_dynamic_pool_member:
                self.compiler.stack_size += 16
                self.compiler.variables[node.target] = self.compiler.stack_size
                print(f"DEBUG: Allocated {node.target} at stack offset {self.compiler.stack_size}")
            elif resolved_name:
                print(f"DEBUG: Skipping allocation for {target_name} (already exists as {resolved_name})")
            
            if hasattr(node.value, '__class__'):
                self.calculate_stack_size(node.value, depth + 1)
        
        elif node_type == 'While':
            for stmt in node.body:
                self.calculate_stack_size(stmt, depth + 1)
        
        elif node_type == 'Loop':
            for stmt in node.body:
                self.calculate_stack_size(stmt, depth + 1)
        
        elif node_type == 'If':
            for stmt in node.then_body:
                self.calculate_stack_size(stmt, depth + 1)
            if node.else_body:
                for stmt in node.else_body:
                    self.calculate_stack_size(stmt, depth + 1)
        
        elif node_type == 'FunctionCall':
            # Pre-allocate space for performance timers
            if node.function == 'DebugPerf.Start':
                if node.arguments and hasattr(node.arguments[0], 'value'):
                    label = node.arguments[0].value
                    var_name = f"__perf_start_{label}"
                    if var_name not in self.compiler.variables:
                        # A timestamp is 8 bytes (qword)
                        self.compiler.stack_size += 8
                        self.compiler.variables[var_name] = self.compiler.stack_size
                        print(f"DEBUG: Pre-allocated perf timer '{var_name}' at stack offset {self.compiler.stack_size}")

            if hasattr(node, 'arguments'):
                for arg in node.arguments:
                    self.calculate_stack_size(arg, depth + 1)
        
        elif node_type == 'Pool':
            if node.pool_type == 'DynamicPool':
                pool_var_name = f"{node.pool_type}.{node.name}"
                if pool_var_name not in self.compiler.variables:
                    self.compiler.stack_size += 8  # Just space for a pointer
                    self.compiler.variables[pool_var_name] = self.compiler.stack_size
                    print(f"DEBUG: Allocated stack pointer for DynamicPool '{pool_var_name}' at offset {self.compiler.stack_size}")
            else:  # For FixedPool, recurse into items
                for item in node.body:
                    self.calculate_stack_size(item, depth + 1)
        
        elif hasattr(node, 'body') and isinstance(node.body, list):
            # Generic handler for any other node with a body
            for stmt in node.body:
                self.calculate_stack_size(stmt, depth + 1)
        
        elif hasattr(node, 'message'):
            self.calculate_stack_size(node.message, depth + 1)

    
    def scan_for_locals(self, node, known_vars):
        """Recursively scans a node (like a function body) to find all local variable assignments."""
        local_vars = set()

        if isinstance(node, list):
            for item in node:
                local_vars.update(self.scan_for_locals(item, known_vars))
            return local_vars

        if not hasattr(node, '__dict__'):
            return local_vars

        # If it's an assignment, check the target
        if type(node).__name__ == 'Assignment':
            target_name = self.compiler.resolve_acronym_identifier(node.target)
            if target_name not in known_vars:
                local_vars.add(target_name)

        # Recurse into children
        for attr_name in dir(node):
            if not attr_name.startswith('_'):
                attr = getattr(node, attr_name)
                if isinstance(attr, (ASTNode, list)):
                    local_vars.update(self.scan_for_locals(attr, known_vars | local_vars))
        return local_vars

    def scan_allocate_sizes(self, node, depth=0):
        """Scan AST for Allocate calls and sum their sizes"""
        total_alloc = 0
        
        if hasattr(node, '__dict__'):
            # Check if this is an Allocate call
            if hasattr(node, 'function') and node.function == 'Allocate':
                if hasattr(node, 'arguments') and len(node.arguments) > 0:
                    arg = node.arguments[0]
                    if hasattr(arg, 'value'):
                        try:
                            size = int(arg.value)
                            total_alloc += size
                            print(f"DEBUG: Found Allocate({size}) at depth {depth}")
                        except:
                            # If it's not a constant, reserve 1KB as safety
                            total_alloc += 1024
                            print(f"DEBUG: Found dynamic Allocate, reserving 1024")
            
            # Recursively scan all attributes
            for attr_name in dir(node):
                if not attr_name.startswith('_'):
                    attr = getattr(node, attr_name)
                    if isinstance(attr, list):
                        for item in attr:
                            total_alloc += self.scan_allocate_sizes(item, depth + 1)
                    elif hasattr(attr, '__dict__'):
                        total_alloc += self.scan_allocate_sizes(attr, depth + 1)
        
        return total_alloc

    # memory_manager.py - Update assignment for pools

    def compile_assignment(self, node):
        """Compile variable assignment with pool-aware addressing"""
        try:
            print(f"DEBUG: Assignment to {node.target}, value: {node.value}, type: {type(node.value)}")
            
            # CRITICAL: Check for AllocateLinkage FIRST, before generic FunctionCall
            if isinstance(node.value, FunctionCall) and node.value.function == 'AllocateLinkage':
                # Compile the allocation, which returns pointer in RAX
                self.compiler.linkage_pool_mgr.compile_allocate_linkage(node.value)
                
                # CHECK FOR PENDING TYPE (set by compile_allocate_linkage)
                print(f"DEBUG: Checking for pending_type after AllocateLinkage...")
                if hasattr(self.compiler, 'pending_type'):
                    print(f"DEBUG: pending_type exists: {self.compiler.pending_type}")
                    if self.compiler.pending_type:
                        if not hasattr(self.compiler, 'pointer_types'):
                            self.compiler.pointer_types = {}
                        self.compiler.pointer_types[node.target] = self.compiler.pending_type
                        print(f"DEBUG: Tracked pointer type: {node.target} -> {self.compiler.pending_type}")
                        
                        # Also store in var_types for backward compatibility
                        if not hasattr(self.compiler, 'var_types'):
                            self.compiler.var_types = {}
                        self.compiler.var_types[node.target] = self.compiler.pending_type
                        self.compiler.pending_type = None  # Clear it
                else:
                    print(f"DEBUG: No pending_type found after AllocateLinkage")
                # The pointer is now in RAX, continue to store it below
                
            # Now check other value types
            elif isinstance(node.value, (Number, String, Identifier, FunctionCall)):
                self.compiler.compile_expression(node.value)
            elif type(node.value).__name__ == 'RunTask':
                self.compiler.compile_node(node.value)
            elif isinstance(node.value, Boolean):
                print(f"DEBUG: Compiling boolean literal: {node.value.value}")
                value_to_emit = 1 if node.value.value else 0
                self.asm.emit_mov_rax_imm64(value_to_emit)
            else:
                value_type = type(node.value).__name__
                print(f"DEBUG: Attempting to compile {value_type} as expression")
                self.compiler.compile_expression(node.value)
            
            # Check if this is a field assignment on a LinkagePool pointer
            if '.' in node.target:
                base_name, field_name = node.target.split('.', 1)
                
                # Check if base is a tracked LinkagePool pointer
                if hasattr(self.compiler, 'pointer_types') and base_name in self.compiler.pointer_types:
                    pool_type = self.compiler.pointer_types[base_name]
                    print(f"DEBUG: LinkagePool field assignment {base_name}.{field_name} = value, type={pool_type}")
                    
                    # Value is already in RAX from compile_expression above
                    # Save it temporarily
                    self.asm.emit_push_rax()  # Save value
                    
                    # Load the pointer into RBX
                    if base_name in self.compiler.variables:
                        offset = self.compiler.variables[base_name]
                        self.asm.emit_bytes(0x48, 0x8B, 0x9D)  # MOV RBX, [RBP-offset]
                        self.asm.emit_bytes(*struct.pack('<i', -offset))
                        print(f"DEBUG: Loaded pointer from [RBP-{offset}] into RBX")
                        
                        # Get field offset
                        if hasattr(self.compiler, 'linkage_pool_mgr'):
                            if pool_type in self.compiler.linkage_pool_mgr.linkage_pools:
                                if field_name in self.compiler.linkage_pool_mgr.linkage_pools[pool_type]:
                                    field_offset, _ = self.compiler.linkage_pool_mgr.linkage_pools[pool_type][field_name]
                                    
                                    # Restore value to RAX
                                    self.asm.emit_pop_rax()
                                    
                                    # Store to [RBX + field_offset]
                                    if field_offset == 0:
                                        self.asm.emit_bytes(0x48, 0x89, 0x03)  # MOV [RBX], RAX
                                    elif field_offset < 128:
                                        self.asm.emit_bytes(0x48, 0x89, 0x43, field_offset)  # MOV [RBX+offset], RAX
                                    else:
                                        self.asm.emit_bytes(0x48, 0x89, 0x83)  # MOV [RBX+offset32], RAX
                                        self.asm.emit_bytes(*struct.pack('<i', field_offset))
                                    
                                    print(f"DEBUG: Stored to field {field_name} at [pointer+{field_offset}]")
                                    return  # CRITICAL: Return here to skip all other processing

            # Now handle the assignment with value in RAX
            # First, try the new acronym system.
            resolved_target = self.compiler.resolve_acronym(node.target)
            # If no match, fall back to the original system for backward compatibility.
            if resolved_target == node.target:
                resolved_target = self.compiler.resolve_acronym_identifier(node.target)
            
            print(f"DEBUG: Assignment to {node.target} (resolved: {resolved_target})")
            
            # Check for DynamicPool access - both full and short forms
            if '.' in resolved_target:
                parts = resolved_target.split('.')
                
                # Check for 3-part form: DynamicPool.TestDynamic.value1
                if len(parts) == 3 and parts[0] == 'DynamicPool':
                    pool_name = f"{parts[0]}.{parts[1]}"
                    member_key = parts[2]
                    
                    if pool_name in self.dynamic_pool_metadata and member_key in self.dynamic_pool_metadata[pool_name]['members']:
                        print(f"DEBUG: Storing to dynamic pool var {resolved_target} (3-part)")
                        self.asm.emit_push_rax()
                        pool_stack_offset = self.compiler.variables[pool_name]
                        member_offset = self.dynamic_pool_metadata[pool_name]['members'][member_key]
                        self.emit_dynamic_pool_store(pool_stack_offset, member_offset)
                        return
                
                # Check for 2-part form: TestDynamic.value1
                elif len(parts) == 2:
                    pool_name = f"DynamicPool.{parts[0]}"
                    member_key = parts[1]
                    
                    if pool_name in self.dynamic_pool_metadata and member_key in self.dynamic_pool_metadata[pool_name]['members']:
                        print(f"DEBUG: Storing to dynamic pool var {resolved_target} (2-part)")
                        self.asm.emit_push_rax()
                        pool_stack_offset = self.compiler.variables[pool_name]
                        member_offset = self.dynamic_pool_metadata[pool_name]['members'][member_key]
                        self.emit_dynamic_pool_store(pool_stack_offset, member_offset)
                        return
            
            # Try to find with pool prefixes if needed
            if resolved_target not in self.compiler.variables and '.' in node.target:
                pool_types = ['FixedPool', 'DynamicPool', 'TemporalPool', 
                            'NeuralPool', 'KernelPool', 'ActorPool', 
                            'SecurityPool', 'ConstrainedPool', 'FilePool']
                for pool_type in pool_types:
                    prefixed_name = f"{pool_type}.{resolved_target}"
                    if prefixed_name in self.compiler.variables:
                        resolved_target = prefixed_name
                        break
            
            # Handle regular variables and FixedPool variables
            if resolved_target not in self.compiler.variables:
                # Check if it's a DynamicPool member that needs special handling
                parts = resolved_target.split('.')
                if len(parts) == 2:
                    pool_name = f"DynamicPool.{parts[0]}"
                    member_name = parts[1]
                    
                    if pool_name in self.dynamic_pool_metadata:
                        if member_name in self.dynamic_pool_metadata[pool_name]['members']:
                            print(f"DEBUG: {resolved_target} is a DynamicPool member, using pool storage")
                            self.asm.emit_push_rax()
                            pool_stack_offset = self.compiler.variables[pool_name]
                            member_offset = self.dynamic_pool_metadata[pool_name]['members'][member_name]
                            self.emit_dynamic_pool_store(pool_stack_offset, member_offset)
                            print(f"DEBUG: Assignment to DynamicPool member {resolved_target} completed")
                            return
                
                # Not a DynamicPool member - allocate normally
                print(f"DEBUG: Stack trace for allocation of {resolved_target}:")
                traceback.print_stack(limit=5)

                self.compiler.stack_size += 16
                offset = self.compiler.stack_size
                self.compiler.variables[resolved_target] = offset
                print(f"DEBUG: Allocated {resolved_target} at stack offset {offset}")
            
            value = self.compiler.variables[resolved_target]
        
            # Check if pool variable (high bit set)
            if value & 0x80000000:  # Pool variable
                pool_index = value & 0x7FFFFFFF
                print(f"DEBUG: Storing to pool var {resolved_target} at pool[{pool_index}]")
                self.asm.emit_bytes(0x49, 0x89, 0x87)  # MOV [R15 + disp32], RAX
                self.asm.emit_bytes(*struct.pack('<i', pool_index * 8))
            else:
                # Stack variable
                offset = value
                self.asm.emit_bytes(0x48, 0x89, 0x85)
                self.asm.emit_bytes(*struct.pack('<i', -offset))
            
            print(f"DEBUG: Assignment to {node.target} completed")
            
        except Exception as e:
            print(f"ERROR: Assignment compilation failed: {str(e)}")
            raise
        
    def compile_resource_item(self, item, pool):
        """Compile a resource item"""
        try:
            pool_name = f"{pool.pool_type}.{pool.name}"
            var_name = f"{pool_name}.{item.key}"
            
            print(f"DEBUG: Compiling resource item {var_name}")
            
            if item.value is not None:
                if var_name not in self.compiler.variables:
                    self.compiler.stack_size += 16
                    self.compiler.variables[var_name] = self.compiler.stack_size
                    print(f"DEBUG: Allocated pool variable {var_name} at stack offset {self.compiler.stack_size}")
                
                if hasattr(item.value, 'value'):
                    item_type = type(item.value).__name__
                    if item_type == 'String':
                        # ✅ Use relocation system instead of hardcoded 0x402000
                        string_offset = self.asm.add_string(item.value.value)
                        self.asm.emit_load_data_address('rax', string_offset)
                        
                        offset = self.compiler.variables[var_name]
                        if offset <= 127:
                            self.asm.emit_bytes(0x48, 0x89, 0x45, 256 - offset)
                        else:
                            self.asm.emit_bytes(0x48, 0x89, 0x85)
                            self.asm.emit_bytes(*struct.pack('<i', -offset))
                        
                        print(f"DEBUG: Initialized {var_name} with relocated string")
                    else:
                        value = int(item.value.value)
                        print(f"DEBUG: Initializing {var_name} = {value} (number)")
                        
                        self.asm.emit_mov_rax_imm64(value)
                        offset = self.compiler.variables[var_name]
                        if offset <= 127:
                            self.asm.emit_bytes(0x48, 0x89, 0x45, 256 - offset)
                        else:
                            self.asm.emit_bytes(0x48, 0x89, 0x85)
                            self.asm.emit_bytes(*struct.pack('<i', -offset))
            
        except Exception as e:
            print(f"ERROR: Resource item compilation failed: {str(e)}")
            raise
    
    def compile_pool(self, node, pre_pass_only=False):
        """Compile Pool declaration with indirect addressing through pool table"""
        if node.pool_type == 'DynamicPool':
            return self.compile_dynamic_pool(node, pre_pass_only)  # Pass pre_pass_only!
        else: # Handles FixedPool and other future static pools
            try:
                pool_name = f"{node.pool_type}.{node.name}"
                
                # --- Discovery Phase (runs in both modes) ---
                for item in node.body:
                    if hasattr(item, 'key'):
                        var_name = f"{pool_name}.{item.key}"
                        if var_name not in self.compiler.variables:
                            pool_index = self.pool_index_counter
                            self.pool_index_counter += 1
                            pool_marker = self.POOL_MARKER | pool_index
                            self.pool_variables[var_name] = pool_index
                            self.compiler.variables[var_name] = pool_marker
                            print(f"DEBUG: Discovered pool var '{var_name}' at pool index {pool_index}")
                
                if pre_pass_only:
                    return True # Discovery is complete for pre-pass

                # --- Code Generation Phase (normal pass only) ---
                print(f"DEBUG: Compiling static pool {pool_name} with global pool table")
                for item in node.body:
                    if hasattr(item, 'key'):
                        var_name = f"{pool_name}.{item.key}"
                        pool_index = self.pool_variables[var_name]
                        print(f"DEBUG: Compiling initialization for {var_name} at pool[{pool_index}]")

                        if item.value is not None:
                            if hasattr(item.value, 'value'):
                                if type(item.value).__name__ == 'String':
                                    string_offset = self.asm.add_string(item.value.value)
                                    
                                    # ✅ Use relocation system for string addresses
                                    self.asm.emit_load_data_address('rax', string_offset)
                                    self.asm.emit_bytes(0x49, 0x89, 0x87)  # MOV [R15 + disp32], RAX
                                    self.asm.emit_bytes(*struct.pack('<i', pool_index * 8))
                                    
                                    print(f"DEBUG: Initialized {var_name} with relocated string at offset {string_offset}")
                                else:
                                    # Integer initialization (unchanged)
                                    init_value = int(item.value.value)
                                    self.asm.emit_mov_rax_imm64(init_value)
                                    self.asm.emit_bytes(0x49, 0x89, 0x87)  # MOV [R15 + disp32], RAX
                                    self.asm.emit_bytes(*struct.pack('<i', pool_index * 8))
                                    print(f"DEBUG: Initialized {var_name} = {init_value}")
                
                print(f"DEBUG: Pool {pool_name} completed")
                return True
            except Exception as e:
                print(f"ERROR: Pool compilation failed: {str(e)}")
                raise

    def compile_dynamic_pool(self, node, pre_pass_only=False):
        """Compile a DynamicPool declaration by allocating it on the heap."""
        try:
            pool_name = f"{node.pool_type}.{node.name}"
            print(f"DEBUG: Compiling DYNAMIC pool {pool_name}")

            if pool_name not in self.dynamic_pool_metadata:
                self.dynamic_pool_metadata[pool_name] = {'members': {}}
            
            member_offsets = {}
            current_offset = 16  # Header: 8 bytes capacity, 8 bytes size
            for item in node.body:
                if hasattr(item, 'key'):
                    member_offsets[item.key] = current_offset
                    current_offset += 8
            self.dynamic_pool_metadata[pool_name]['members'] = member_offsets
            
            # Register the pool in compiler variables if not already present
            if pool_name not in self.compiler.variables:
                self.compiler.stack_size += 16
                self.compiler.variables[pool_name] = self.compiler.stack_size
                print(f"DEBUG: Registered dynamic pool {pool_name} at offset {self.compiler.variables[pool_name]}")

            # CRITICAL: Check if this is just the discovery/pre-pass phase
            if pre_pass_only:
                print(f"DEBUG: Pre-pass only for {pool_name}, skipping code generation")
                return True  # Don't generate runtime code during pre-pass
            
            # === CODE GENERATION PHASE - Only runs during actual compilation ===
            print(f"DEBUG: Generating runtime code for {pool_name}")
            
            num_items = len(node.body)
            initial_capacity = num_items * 2 if num_items > 0 else 16
            mmap_size = 16 + (initial_capacity * 8)

            # Generate mmap syscall to allocate heap memory for the pool
            self.asm.emit_mov_rax_imm64(9)          # sys_mmap
            self.asm.emit_mov_rdi_imm64(0)          # addr = NULL
            self.asm.emit_mov_rsi_imm64(mmap_size)  # size
            self.asm.emit_mov_rdx_imm64(3)          # PROT_READ | PROT_WRITE
            self.asm.emit_mov_r10_imm64(0x22)       # MAP_PRIVATE | MAP_ANONYMOUS
            self.asm.emit_mov_r8_imm64(-1)          # fd = -1
            self.asm.emit_mov_r9_imm64(0)           # offset = 0
            self.asm.emit_syscall()

            # Store the allocated pointer on the stack
            stack_offset = self.compiler.variables[pool_name]
            self.asm.emit_bytes(0x48, 0x89, 0x85, *struct.pack('<i', -stack_offset))
            print(f"DEBUG: Stored DynamicPool pointer for {pool_name} at [RBP - {stack_offset}]")

            # Initialize the pool header with capacity and size
            self.asm.emit_push_rax()                           # Save pool pointer
            self.asm.emit_mov_rbx_imm64(initial_capacity)      # Load capacity
            self.asm.emit_bytes(0x48, 0x89, 0x18)             # MOV [RAX], RBX (store capacity)
            self.asm.emit_mov_rbx_imm64(num_items)            # Load current size
            self.asm.emit_bytes(0x48, 0x89, 0x58, 0x08)       # MOV [RAX+8], RBX (store size)
            self.asm.emit_pop_rax()                           # Restore pool pointer
            
            # Initialize member values from Initialize= declarations
            for item in node.body:
                if hasattr(item, 'key') and item.value is not None:
                    member_offset = member_offsets[item.key]
                    
                    if hasattr(item.value, 'value'):
                        init_value = int(item.value.value)
                        
                        # Load pool base address from stack
                        self.asm.emit_bytes(0x48, 0x8B, 0x85, *struct.pack('<i', -stack_offset))  # MOV RAX, [RBP-offset]
                        
                        # Add member offset to get target address
                        if member_offset > 0:
                            self.asm.emit_bytes(0x48, 0x05, *struct.pack('<I', member_offset))  # ADD RAX, member_offset
                        
                        # Store the initialization value
                        self.asm.emit_mov_rbx_imm64(init_value)
                        self.asm.emit_bytes(0x48, 0x89, 0x18)  # MOV [RAX], RBX
                        
                        print(f"DEBUG: Initialized {pool_name}.{item.key} = {init_value} at offset {member_offset}")
            
            print(f"DEBUG: DynamicPool {pool_name} initialization complete")
            return True
            
        except Exception as e:
            print(f"ERROR: DynamicPool compilation failed: {str(e)}")
            raise
            
        
    def allocate_pool_table(self):
        """Allocate memory for the pool table at program start - dynamically sized"""
        
        if self.pool_table_allocated:
            print("DEBUG: Pool table already allocated, skipping")
            return
        
        num_pools = self.pool_index_counter
        
        # Calculate required size: 8 bytes per pool variable
        required_size = num_pools * 8
        
        # Round up to nearest page (4KB) for mmap efficiency
        page_size = 4096
        pool_table_size = ((required_size + page_size - 1) // page_size) * page_size
        
        # Enforce minimum of 4KB (1 page)
        if pool_table_size < 16384:
            pool_table_size = 16384
        
        # Cap at reasonable maximum (1MB = 131,072 pool variables)
        max_size = 1024 * 1024
        if pool_table_size > max_size:
            print(f"ERROR: Pool table size {pool_table_size} exceeds maximum {max_size}")
            print(f"       You have {num_pools} pool variables, max is {max_size // 8}")
            raise ValueError(f"Too many pool variables: {num_pools} (max {max_size // 8})")
        
        print(f"DEBUG: ===== POOL TABLE ALLOCATION =====")
        print(f"DEBUG: Pool variables discovered: {num_pools}")
        print(f"DEBUG: Required size: {required_size} bytes ({required_size / 1024:.2f} KB)")
        print(f"DEBUG: Allocated size (page-aligned): {pool_table_size} bytes ({pool_table_size / 1024:.2f} KB)")
        print(f"DEBUG: Maximum pool variables: {pool_table_size // 8}")
        print(f"DEBUG: =====================================")
        
        # Allocate via mmap
        self.asm.emit_mov_rax_imm64(9)          # sys_mmap
        self.asm.emit_mov_rdi_imm64(0)          # addr = NULL (let kernel choose)
        self.asm.emit_mov_rsi_imm64(pool_table_size)  # DYNAMIC SIZE!
        self.asm.emit_mov_rdx_imm64(3)          # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)       # MAP_PRIVATE | MAP_ANONYMOUS
        self.asm.emit_mov_r8_imm64(-1)          # fd = -1
        self.asm.emit_mov_r9_imm64(0)           # offset = 0
        self.asm.emit_syscall()
        
        # Check for mmap failure
        self.asm.emit_cmp_rax_imm64(-1)
        error_label = self.asm.create_label()
        success_label = self.asm.create_label()
        self.asm.emit_jump_to_label(error_label, "JE")
        
        # Store pool base in R15
        self.asm.emit_bytes(0x49, 0x89, 0xC7)  # MOV R15, RAX
        
        # Zero-initialize the pool table
        self.asm.emit_mov_rdi_rax()             # RDI = pool table address
        self.asm.emit_mov_rcx_imm64(pool_table_size // 8)  # Number of qwords
        self.asm.emit_mov_rax_imm64(0)          # Zero value
        self.asm.emit_bytes(0xF3, 0x48, 0xAB)   # REP STOSQ (fast zero-fill)
        
        self.asm.emit_jump_to_label(success_label, "JMP")
        
        # Error handling
        self.asm.mark_label(error_label)
        # Print error message and exit
        error_msg = f"FATAL: Failed to allocate pool table ({pool_table_size} bytes)\n"
        error_offset = self.asm.add_string(error_msg)
        self.asm.emit_load_data_address('rsi', error_offset)
        self.asm.emit_mov_rax_imm64(1)          # sys_write
        self.asm.emit_mov_rdi_imm64(2)          # stderr
        self.asm.emit_mov_rdx_imm64(len(error_msg))
        self.asm.emit_syscall()
        
        self.asm.emit_mov_rax_imm64(60)         # sys_exit
        self.asm.emit_mov_rdi_imm64(1)          # exit code 1
        self.asm.emit_syscall()
        
        self.asm.mark_label(success_label)
        self.pool_table_allocated = True
        print(f"DEBUG: Pool table allocated successfully in R15 ({pool_table_size} bytes)")
        
    def emit_dynamic_pool_store(self, pool_stack_offset, member_offset):
        """Helper to emit code for storing a value in a dynamic pool member."""
        # Assumes value to store is on the stack
        # Load pool base pointer from stack into RCX
        self.asm.emit_bytes(0x48, 0x8B, 0x8D, *struct.pack('<i', -pool_stack_offset)) # MOV RCX, [RBP - offset]
        # Add member offset to base pointer
        self.asm.emit_bytes(0x48, 0x81, 0xC1, *struct.pack('<i', member_offset)) # ADD RCX, member_offset
        # Pop value from stack into RAX and store it
        self.asm.emit_pop_rax()
        self.asm.emit_bytes(0x48, 0x89, 0x01) # MOV [RCX], RAX

    def compile_pool_access(self, var_name):
        """Generate code to access a pool variable by absolute address"""
        if var_name in self.pool_variables:
            addr = self.pool_variables[var_name]
            # MOV RAX, [absolute_address]
            self.asm.emit_bytes(0x48, 0xA1)  # MOV RAX, moffs64
            self.asm.emit_bytes(*struct.pack('<Q', addr))
            print(f"DEBUG: Loaded {var_name} from absolute address 0x{addr:x}")
            return True
        return False
    
    def compile_pool_write(self, var_name, value_in_rax=True):
        """Generate code to write to a pool variable by absolute address"""
        if var_name in self.pool_variables:
            addr = self.pool_variables[var_name]
            # MOV [absolute_address], RAX
            self.asm.emit_bytes(0x48, 0xA3)  # MOV moffs64, RAX
            self.asm.emit_bytes(*struct.pack('<Q', addr))
            print(f"DEBUG: Stored to {var_name} at absolute address 0x{addr:x}")
            return True
        return False       
    
    def emit_strdup(self):
        """
        Duplicate a string to prevent double-free issues.
        Input: RAX = source string pointer
        Output: RAX = new duplicated string pointer
        
        This is called when copying strings between pool variables to ensure
        each pool owns its own copy of the string data.
        """
        
        # Step 1: Calculate source string length
        self.asm.emit_push_rax()  # Save source pointer
        self.asm.emit_mov_rdi_rax()  # RDI = source for strlen
        self.asm.emit_xor_rcx_rcx()  # RCX = 0 (length counter)
        
        # strlen loop
        strlen_loop = self.asm.create_label()
        strlen_done = self.asm.create_label()
        self.asm.mark_label(strlen_loop)
        self.asm.emit_bytes(0x80, 0x3C, 0x0F, 0x00)  # CMP BYTE [RDI+RCX], 0
        self.asm.emit_jump_to_label(strlen_done, "JE")
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
        self.asm.emit_jump_to_label(strlen_loop, "JMP")
        self.asm.mark_label(strlen_done)
        
        # RCX now has length, add 1 for null terminator
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
        
        # Step 2: Allocate new memory via mmap
        self.asm.emit_push_rcx()  # Save length+1
        self.asm.emit_mov_rax_imm64(9)  # sys_mmap
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL (let kernel choose)
        self.asm.emit_mov_rsi_rcx()  # length = RCX
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ|WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE|ANON
        self.asm.emit_mov_r8_imm64(0xFFFFFFFFFFFFFFFF)  # fd = -1
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()
        
        # RAX now has new buffer address
        # Stack: [source][length]
        
        # Step 3: Copy string using REP MOVSB for efficiency
        self.asm.emit_mov_rdi_rax()  # RDI = destination
        self.asm.emit_bytes(0x48, 0x8B, 0x74, 0x24, 0x08)  # MOV RSI, [RSP+8] (source)
        self.asm.emit_pop_rcx()  # RCX = length
        self.asm.emit_bytes(0xF3, 0xA4)  # REP MOVSB
        
        # Step 4: Clean up stack and return duplicated string
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x08)  # ADD RSP, 8 (pop source)
        
        print("DEBUG: String duplication completed")
        # RAX now contains the duplicated string pointer
    
    
    def compile_pool_allocation(self, node):
        """Pre-allocate pool variables"""
        try:
            if hasattr(node, 'pool_type') and hasattr(node, 'name'):
                pool_name = f"{node.pool_type}.{node.name}"
                print(f"DEBUG: Pre-allocating pool {pool_name}")
                
                for item in node.body:
                    if hasattr(item, 'key'):
                        var_name = f"{pool_name}.{item.key}"
                        if var_name not in self.compiler.variables:
                            self.compiler.stack_size += 16
                            self.compiler.variables[var_name] = self.compiler.stack_size
                            print(f"DEBUG: Pre-allocated pool variable {var_name} at offset {self.compiler.stack_size}")
            
        except Exception as e:
            print(f"ERROR: Pool allocation failed: {str(e)}")
            raise
    
    def compile_acronym_definitions(self, node):
        """Compile acronym definitions"""
        try:
            print(f"DEBUG: Processing {len(node.mappings)} acronym definitions")  # ← CHANGE THIS
            
            for acronym, full_name in node.mappings.items():  # ← CHANGE THIS
                if acronym in self.compiler.acronym_table:
                    print(f"WARNING: Redefining acronym {acronym}")
                
                self.compiler.acronym_table[acronym] = full_name
                print(f"DEBUG: Mapped {acronym} -> {full_name}")
                
            print(f"DEBUG: Acronym table now contains: {self.compiler.acronym_table}")
            
        except Exception as e:
            print(f"ERROR: Failed to compile acronym definitions: {str(e)}")
            raise
        
    def resolve_acronym_identifier(self, identifier_name):
        """Resolve acronym.variable syntax"""
        try:
            parts = identifier_name.split('.')
            
            if len(parts) == 2:
                acronym, variable = parts
                
                if acronym in self.compiler.acronym_table:
                    full_namespace = self.compiler.acronym_table[acronym]
                    
                    candidates = [
                        f"{full_namespace}.{variable}",
                        f"FixedPool.{full_namespace}.{variable}",
                        f"DynamicPool.{full_namespace}.{variable}",
                        f"TemporalPool.{full_namespace}.{variable}",
                        f"NeuralPool.{full_namespace}.{variable}",
                        f"KernelPool.{full_namespace}.{variable}",
                        f"ActorPool.{full_namespace}.{variable}",
                        f"SecurityPool.{full_namespace}.{variable}",
                        f"ConstrainedPool.{full_namespace}.{variable}"
                    ]
                    
                    for candidate in candidates:
                        if candidate in self.compiler.variables:
                            print(f"DEBUG: Resolved {identifier_name} -> {candidate}")
                            return candidate
                    
                    basic_resolution = f"{full_namespace}.{variable}"
                    print(f"DEBUG: Basic resolution {identifier_name} -> {basic_resolution}")
                    return basic_resolution
            
            return identifier_name
            
        except Exception as e:
            print(f"ERROR: Failed to resolve acronym {identifier_name}: {str(e)}")
            return identifier_name
    
    # All the pool operation methods remain the same
    def compile_pool_resize(self, node):
        """Compile PoolResize(pool_name, new_size) - resize a memory pool"""
        try:
            print("DEBUG: Compiling PoolResize")
            
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_push_rax()
            
            if type(node.arguments[0]).__name__ == 'Identifier':
                pool_name = node.arguments[0].name
                resolved_pool = self.resolve_acronym_identifier(pool_name)
                print(f"DEBUG: Resizing pool {resolved_pool}")
            
            self.asm.emit_pop_rsi()
            self.asm.emit_mov_rax_imm64(9)
            self.asm.emit_mov_rdi_imm64(0)
            self.asm.emit_mov_rdx_imm64(3)
            self.asm.emit_mov_r10_imm64(0x22)
            self.asm.emit_mov_r8_imm64(0xFFFFFFFFFFFFFFFF)
            self.asm.emit_mov_r9_imm64(0)
            self.asm.emit_syscall()
            
            error_label = self.asm.create_label()
            success_label = self.asm.create_label()
            
            self.asm.emit_bytes(0x48, 0x83, 0xF8, 0x00)
            self.asm.emit_jump_to_label(error_label, "JL")
            self.asm.emit_jump_to_label(success_label, "JMP")
            
            self.asm.mark_label(error_label)
            self.asm.emit_mov_rax_imm64(0)
            
            self.asm.mark_label(success_label)
            print("DEBUG: PoolResize completed")
            return True
            
        except Exception as e:
            print(f"ERROR: PoolResize compilation failed: {str(e)}")
            raise

    def compile_pool_move(self, node):
        """Compile PoolMove(data, from_pool, to_pool) - uses size from header"""
        try:
            print("DEBUG: Compiling PoolMove with dynamic size")
            
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_push_rax()
            
            self.asm.emit_bytes(0x48, 0x8B, 0x48, 0xF8)
            self.asm.emit_push_rcx()
            
            self.asm.emit_bytes(0x48, 0x83, 0xC1, 0x08)
            self.asm.emit_mov_rsi_rcx()
            
            self.asm.emit_mov_rax_imm64(9)
            self.asm.emit_mov_rdi_imm64(0)
            self.asm.emit_mov_rdx_imm64(3)
            self.asm.emit_mov_r10_imm64(0x22)
            self.asm.emit_mov_r8_imm64(0xFFFFFFFFFFFFFFFF)
            self.asm.emit_mov_r9_imm64(0)
            self.asm.emit_syscall()
            
            error_label = self.asm.create_label()
            success_label = self.asm.create_label()
            
            self.asm.emit_bytes(0x48, 0x85, 0xC0)
            self.asm.emit_jump_to_label(error_label, "JZ")
            
            self.asm.emit_mov_rdi_rax()
            
            self.asm.emit_pop_rcx()
            self.asm.emit_push_rcx()
            self.asm.emit_bytes(0x48, 0x89, 0x08)
            
            self.asm.emit_bytes(0x48, 0x83, 0xC7, 0x08)
            self.asm.emit_push_rdi()
            
            self.asm.emit_mov_rsi_from_stack_offset(16)
            
            self.asm.emit_pop_rax()
            self.asm.emit_pop_rcx()
            self.asm.emit_push_rax()
            
            self.asm.emit_bytes(0xF3, 0xA4)
            
            self.asm.emit_pop_rax()
            self.asm.emit_add_rsp_imm8(8)
            self.asm.emit_jump_to_label(success_label, "JMP")
            
            self.asm.mark_label(error_label)
            self.asm.emit_mov_rax_imm64(0)
            self.asm.emit_add_rsp_imm8(16)
            
            self.asm.mark_label(success_label)
            print("DEBUG: PoolMove with dynamic size completed")
            return True
            
        except Exception as e:
            print(f"ERROR: PoolMove compilation failed: {str(e)}")
            raise
    
    def compile_pool_compact(self, node):
        """Compile PoolCompact(pool_name) - defragment a memory pool"""
        try:
            print("DEBUG: Compiling PoolCompact")
            
            self.asm.emit_mov_rcx_imm64(0)
            self.asm.emit_mov_rdx_imm64(0)
            
            scan_loop = self.asm.create_label()
            scan_end = self.asm.create_label()
            
            self.asm.mark_label(scan_loop)
            
            self.asm.emit_bytes(0x48, 0x81, 0xF9)
            self.asm.emit_bytes(0x00, 0x10, 0x00, 0x00)
            self.asm.emit_jump_to_label(scan_end, "JGE")
            
            self.asm.emit_bytes(0x48, 0x83, 0xC1, 0x10)
            self.asm.emit_jump_to_label(scan_loop, "JMP")
            
            self.asm.mark_label(scan_end)
            
            self.asm.emit_mov_rax_rcx()
            
            print("DEBUG: PoolCompact completed")
            return True
            
        except Exception as e:
            print(f"ERROR: PoolCompact compilation failed: {str(e)}")
            raise

       
    # In memory_manager.py
    def compile_pool_allocate(self, node):
        """Compile PoolAllocate(pool_name, size)"""
        try:
            print("DEBUG: Compiling PoolAllocate")
            pool_name = node.arguments[0].value if isinstance(node.arguments[0], String) else node.arguments[0].name
            size_node = node.arguments[1]
            size = int(size_node.value) if isinstance(size_node, Number) else 8
            if size <= 0:
                size = 8
            size += 8
            
            self.compiler.compile_expression(size_node)
            self.asm.emit_mov_rsi_rax()  # Size in RSI
            
            self.asm.emit_mov_rax_imm64(9)  # mmap syscall
            self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
            self.asm.emit_mov_rdx_imm64(3)  # PROT_READ | PROT_WRITE
            self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS
            self.asm.emit_mov_r8_imm64(0xFFFFFFFFFFFFFFFF)  # fd = -1
            self.asm.emit_mov_r9_imm64(0)  # offset = 0
            self.asm.emit_syscall()
            
            error_label = self.asm.create_label()
            success_label = self.asm.create_label()
            
            self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
            self.asm.emit_jump_to_label(error_label, "JZ")
            
            # Store mmap address immediately
            var_name = node.variable if hasattr(node, 'variable') else pool_name
            resolved_name = self.compiler.resolve_acronym_identifier(var_name)
            if resolved_name not in self.compiler.variables:
                offset = self.compiler.stack_size
                self.compiler.variables[resolved_name] = offset
                self.compiler.stack_size += 8
                print(f"DEBUG: Allocated {resolved_name} at [rbp - {offset}]")
            offset = self.compiler.variables[resolved_name]
            if offset <= 0 or offset > self.compiler.stack_size:
                print(f"ERROR: Invalid stack offset {offset} for {resolved_name}")
                raise ValueError(f"Invalid stack offset {offset} for {resolved_name}")
            self.asm.emit_bytes(0x48, 0x89, 0x85)
            self.asm.emit_bytes(*struct.pack('<i', -offset))
            self.asm.emit_push_rax()
            self.asm.emit_print_number()  # Log mmap address
            self.asm.emit_pop_rax()
            print(f"DEBUG: Stored mmap address in {resolved_name} at [rbp - {offset}]")
            
            self.asm.emit_mov_rbx_rax()  # Save address in RBX
            self.asm.emit_mov_rax_rsi()  # Restore size in RAX
            self.asm.emit_bytes(0x48, 0x89, 0x03)  # Store size at [RBX]
            self.asm.emit_lea_rax_rbx(8)  # RAX = RBX + 8
            
            self.asm.emit_jump_to_label(success_label, "JMP")
            
            self.asm.mark_label(error_label)
            self.asm.emit_mov_rax_imm64(0)
            print(f"DEBUG: mmap allocation failed for {pool_name}")
            
            self.asm.mark_label(success_label)
            print("DEBUG: PoolAllocate with size header completed")
            return True
        except Exception as e:
            print(f"ERROR: PoolAllocate compilation failed: {str(e)}")
            raise

    def compile_pool_free(self, node):
        """Compile PoolFree(pool_name, address) - return memory to pool"""
        try:
            print("DEBUG: Compiling PoolFree")
            
            self.compiler.compile_expression(node.arguments[1])
            
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: PoolFree completed")
            return True
            
        except Exception as e:
            print(f"ERROR: PoolFree compilation failed: {str(e)}")
            raise 
        
    def compile_pool_get_size(self, node):
        """Get allocated size from pool allocation header"""
        try:
            print("DEBUG: Compiling PoolGetSize")
            
            self.compiler.compile_expression(node.arguments[0])
            
            self.asm.emit_bytes(0x48, 0x8B, 0x40, 0xF8)
            
            print("DEBUG: PoolGetSize completed")
            return True
            
        except Exception as e:
            print(f"ERROR: PoolGetSize compilation failed: {str(e)}")

    def compile_array_create(self, node):
        """Create array with size - allocates (size * 8) + 8 bytes"""
        print("DEBUG: Compiling ArrayCreate")
        
        # Get size argument
        if len(node.arguments) > 0:
            self.compiler.compile_expression(node.arguments[0])
        else:
            self.asm.emit_mov_rax_imm64(10)  # Default size
        
        # Save size for header
        self.asm.emit_push_rax()
        
        # Calculate bytes needed: (size * 8) + 8 for header
        self.asm.emit_bytes(0x48, 0xC1, 0xE0, 0x03)  # SHL RAX, 3 (multiply by 8)
        self.asm.emit_bytes(0x48, 0x83, 0xC0, 0x08)  # ADD RAX, 8

        # Allocate via mmap - CORRECTED
        self.asm.emit_bytes(0x48, 0x89, 0xC6) # MOV RSI, RAX (size for mmap)
        
        self.asm.emit_mov_rax_imm64(9)  # mmap syscall
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ|PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE|MAP_ANONYMOUS
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF) # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()
        
        # Store size in first 8 bytes
        self.asm.emit_mov_rbx_rax()  # Save array pointer
        self.asm.emit_pop_rcx()  # Get size
        self.asm.emit_bytes(0x48, 0x89, 0x0B)  # MOV [RBX], RCX
        
        # Return array pointer
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
        self.compiler.asm.mark_label(done_label)
        
        print("DEBUG: ArrayDestroy completed")
        return True