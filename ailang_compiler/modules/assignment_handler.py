#!/usr/bin/env python3
"""
Assignment Handler Module for AILANG Compiler
Handles compilation of variable assignment statements.
"""

import struct
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ailang_parser')))
from ailang_ast import *
from .symbol_table import SymbolType

class AssignmentHandler:
    """Handles compilation of assignment statements."""

    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm

    def compile_assignment(self, node):
        """Compile variable assignment with pool-aware addressing"""
        try:
            print(f"DEBUG TRACE: Enter compile_assignment for {node.target}")
            print(f"DEBUG: Assignment to {node.target}, value: {node.value}, type: {type(node.value)}")

            target_name = node.target  # Get target name early

            # Check if value is another typed pointer (for propagation) BEFORE compiling
            if isinstance(node.value, Identifier):
                source_name = node.value.name
                if hasattr(self.compiler, 'pointer_types') and source_name in self.compiler.pointer_types:
                    source_type = self.compiler.pointer_types[source_name]
                    if not hasattr(self.compiler, 'pointer_types'):
                        self.compiler.pointer_types = {}
                    self.compiler.pointer_types[target_name] = source_type
                    print(f"DEBUG: Propagated type {source_type} from {source_name} to {target_name}")

            # Compile the value expression first (we need it in RAX for any assignment)
            if isinstance(node.value, (Number, String, Identifier, FunctionCall)):
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

            # Now handle the assignment with value in RAX
            # Use the symbol table for lookup
            print(f"DEBUG: About to lookup symbol, checking pending_type first...")
            if hasattr(self.compiler, 'pending_type'):
                print(f"DEBUG: pending_type = {self.compiler.pending_type}")
                if self.compiler.pending_type:
                    if not hasattr(self.compiler, 'pointer_types'):
                        self.compiler.pointer_types = {}
                    self.compiler.pointer_types[target_name] = self.compiler.pending_type
                    print(f"DEBUG: Tracked pointer type: {target_name} -> {self.compiler.pending_type}")
                    self.compiler.pending_type = None
            
            symbol = self.compiler.symbol_table.lookup(node.target)
            if not symbol:
                raise ValueError(f"Undeclared variable '{node.target}' encountered during assignment. Semantic analysis failed.")
            
            # Check for DynamicPool member assignment
            if symbol.type == SymbolType.VARIABLE and '.' in symbol.name:
                parts = symbol.name.split('.')
                if len(parts) == 3 and parts[0] == 'DynamicPool':
                    pool_name = f"{parts[0]}.{parts[1]}"
                    member_key = parts[2]
                    pool_symbol = self.compiler.symbol_table.lookup(pool_name)
                    if pool_symbol and pool_symbol.metadata and pool_symbol.metadata.get('pool_type') == 'Dynamic':
                        print(f"DEBUG: Storing to dynamic pool var {symbol.name}")
                        self.asm.emit_push_rax() # Save value
                        member_offset = pool_symbol.metadata['members'][member_key]
                        # This needs to call the helper in PoolManager
                        self.compiler.pool_manager.emit_dynamic_pool_store(pool_symbol.offset, member_offset)
                        print(f"DEBUG: Assignment to DynamicPool member {symbol.name} completed")
                        print(f"DEBUG TRACE: Exiting compile_assignment at point 1 (DynamicPool member)")
                        return
            
            # Check if it's a pool variable (FixedPool)
            if symbol.offset & self.compiler.symbol_table.POOL_MARKER:
                pool_index = symbol.offset & ~self.compiler.symbol_table.POOL_MARKER
                print(f"DEBUG: Storing to pool var {symbol.name} at pool[{pool_index}]")
                self.asm.emit_bytes(0x49, 0x89, 0x87)  # MOV [R15 + disp32], RAX
                self.asm.emit_bytes(*struct.pack('<i', pool_index * 8))
            else:
                # Regular stack variable storage
                offset = symbol.offset
                print(f"DEBUG: Storing to stack var {symbol.name} at [RBP-{offset}]")
                
                # MOV [RBP - offset], RAX
                if offset <= 127:
                    # Small offset: use 8-bit displacement
                    self.asm.emit_bytes(0x48, 0x89, 0x45, (256 - offset) & 0xFF)  # MOV [RBP-offset], RAX
                else:
                    # Large offset: use 32-bit displacement
                    self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP-offset], RAX
                    self.asm.emit_bytes(*struct.pack('<i', -offset))
                
                print(f"DEBUG: Stored value to {symbol.name} at [RBP-{offset}]")
            
            print(f"DEBUG TRACE: Exiting compile_assignment at point 2 (end of try block)")
            print(f"DEBUG: Assignment to {node.target} completed")
            
        except Exception as e:
            print(f"DEBUG TRACE: Exiting compile_assignment at point 3 (exception)")
            print(f"ERROR: Assignment compilation failed: {str(e)}")
            raise