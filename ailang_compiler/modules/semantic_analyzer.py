# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

    # ailang_compiler/semantic_analyzer.py
from typing import List, Set
from ailang_parser.ailang_ast import *
from .symbol_table import SymbolTable, SymbolType
from ..ast_visitor import ASTVisitor

class SemanticAnalyzer(ASTVisitor):
    def __init__(self, compiler_context, symbol_table: SymbolTable):
        self.compiler = compiler_context
        self.symbols = symbol_table
        self.errors = []
        self.warnings = []
        
    def analyze(self, ast: Program) -> bool:
        """Single complete pass over entire AST"""
        print("Phase 1: Semantic Analysis Starting")
        
        # Visit everything ONCE
        self.visit(ast)
        
        if self.errors:
            for error in self.errors:
                print(f"ERROR: {error}")
            return False
            
        print(f"Semantic Analysis Complete: {len(self.symbols.scopes)} scopes, "
              f"{sum(len(s) for s in self.symbols.scopes.values())} symbols")
        return True
        
    def handle_Program(self, node: Program):
        """Visit program root"""
        # Process declarations in order
        for decl in node.declarations or []:
            self.visit(decl)
            
    def handle_Function(self, node):
        """Visit function definition"""
        # Register function
        symbol = self.symbols.register(node.name, SymbolType.FUNCTION)

        # Collect parameter names and store them in metadata
        param_names = []
        if hasattr(node, 'parameters'):
            for param in node.parameters:
                param_names.append(param.name)
        
        symbol.metadata = {'label': self.compiler.asm.create_label(), 'params': param_names}
        
        # Enter function scope
        self.symbols.enter_scope(node.name, "function")
        
        # Explicitly visit parameters to register them
        if hasattr(node, 'parameters'):
            for param in node.parameters:
                self.visit(param)
        
        # Explicitly visit the body to register local variables
        if hasattr(node, 'body'):
            for stmt in node.body:
                self.visit(stmt)
                
        # Exit scope
        self.symbols.exit_scope()
        
    def handle_SubRoutine(self, node):
        """Visit subroutine"""
        symbol = self.symbols.register(node.name, SymbolType.FUNCTION)
        symbol.metadata = {'label': self.compiler.asm.create_label(), 'params': []} # Subroutines have no params
        # Explicitly visit the body to find assignments
        if hasattr(node, 'body'):
            for stmt in node.body:
                self.visit(stmt)
        
    def handle_Assignment(self, node):
        """Visit assignment - register variable if new"""
        # Check if variable exists
        if not self.symbols.lookup(node.target):
            # Register new variable in the current scope
            self.symbols.register(node.target, SymbolType.VARIABLE)
            
        # Visit value expression
        self.visit(node.value)
        
    def handle_Identifier(self, node):
        """Check identifier exists"""
        if not self.symbols.lookup(node.name):
            # This check is too aggressive for the semantic pass, as built-ins aren't in the table yet.
            # Type checking will be a separate, later pass. For now, we just register symbols.
            pass
            
    def handle_FunctionCall(self, node):
        """Visit function call"""
        # Check function exists
        if not self.symbols.lookup(node.function):
            # Might be built-in, check later
            pass
            
        # Let generic visit handle arguments
        self.handle_generic(node)
                
    def handle_Parameter(self, node):
        """Handle function parameter declaration."""
        # The visitor pattern will find this node.
        # We register it as a PARAMETER type symbol.
        self.symbols.register(node.name, SymbolType.PARAMETER)

    def handle_Pool(self, node):
        """Visit pool declaration"""
        if node.pool_type == 'DynamicPool':
            pool_name = f"{node.pool_type}.{node.name}"
            # Register the main pool symbol, which will be a pointer on the stack
            pool_symbol = self.symbols.register(pool_name, SymbolType.VARIABLE)
            
            # Calculate member offsets and store them as metadata
            member_offsets = {}
            current_offset = 16  # Header: 8 bytes capacity, 8 bytes size
            for item in node.body:
                if hasattr(item, 'key'):
                    member_offsets[item.key] = current_offset
                    current_offset += 8
            pool_symbol.metadata = {'pool_type': 'Dynamic', 'members': member_offsets}
            print(f"DEBUG: Registered DynamicPool '{pool_name}' with members: {member_offsets}")
        else: # FixedPool
            pool_name = f"{node.pool_type}.{node.name}"
            self.symbols.register(pool_name, SymbolType.POOL)
            # Register pool variables for FixedPool
            for item in node.body:
                if hasattr(item, 'key'):
                    var_name = f"{pool_name}.{item.key}"
                    self.symbols.register(var_name, SymbolType.VARIABLE, is_pool_var=True)