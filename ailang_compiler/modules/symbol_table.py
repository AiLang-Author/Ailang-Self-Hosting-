# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/symbol_table.py
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, List

class SymbolType(Enum):
    VARIABLE = "variable"
    FUNCTION = "function"
    POOL = "pool"
    PARAMETER = "parameter"
    LABEL = "label"
    CONSTANT = "constant"

@dataclass
class Symbol:
    name: str
    type: SymbolType
    scope: str  # 'global', 'function:name', 'subroutine:name'
    offset: Optional[int] = None  # Stack offset or pool index
    size: int = 8  # Default 8 bytes
    metadata: dict = None  # Additional info

class SymbolTable:
    def __init__(self):
        self.scopes = {'global': {}}
        self.current_scope = 'global'
        self.scope_stack = ['global']
        self.next_offset = 8  # Start after RBP
        self.pool_index_counter = 0
        self.POOL_MARKER = 0x80000000
        
    def enter_scope(self, name: str, scope_type: str = "function"):
        """Enter a new scope"""
        scope_name = f"{scope_type}:{name}"
        self.scopes[scope_name] = {}
        self.scope_stack.append(scope_name)
        self.current_scope = scope_name
        self.next_offset = 8 # Reset stack offset for new function scope
        
    def exit_scope(self):
        """Exit current scope"""
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1]
            
    def register(self, name: str, symbol_type: SymbolType, size: int = 8, is_pool_var: bool = False) -> Symbol:
        """Register a new symbol"""
        actual_offset = None # Use a distinct name to avoid confusion
        if is_pool_var:
            actual_offset = self.POOL_MARKER | self.pool_index_counter
            self.pool_index_counter += 1
        elif symbol_type == SymbolType.VARIABLE:
            actual_offset = self.next_offset # Assign the current next_offset to the symbol
            self.next_offset += size

        symbol = Symbol(
            name=name,
            type=symbol_type,
            scope=self.current_scope,
            offset=actual_offset, # Use the actual_offset calculated for *this* symbol
            size=size
        )
        
        self.scopes[self.current_scope][name] = symbol
        return symbol
        
    def lookup(self, name: str) -> Optional[Symbol]:
        """Lookup symbol in scope chain"""
        # Check current scope first
        if name in self.scopes[self.current_scope]:
            return self.scopes[self.current_scope][name]
            
        # Check parent scopes
        for scope in reversed(self.scope_stack[:-1]):
            if name in self.scopes[scope]:
                return self.scopes[scope][name]
                
        return None
        
    def get_stack_size(self) -> int:
        """Get total stack size needed"""
        total = 0
        for scope in self.scopes.values():
            for symbol in scope.values():
                if symbol.type == SymbolType.VARIABLE and symbol.offset:
                    total = max(total, symbol.offset + symbol.size)
        return total

    def get_scope_stack_size(self, scope_name: str) -> int:
        """Get stack size needed for a specific scope (e.g., a function)."""
        total = 0
        if scope_name in self.scopes:
            for symbol in self.scopes[scope_name].values():
                if symbol.type == SymbolType.VARIABLE and symbol.offset and not (symbol.offset & self.POOL_MARKER):
                    total = max(total, symbol.offset + symbol.size)
        return total