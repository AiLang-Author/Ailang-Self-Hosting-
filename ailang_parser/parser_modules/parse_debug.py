# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

#parse_debug.py
"""Parser methods for debug-related operations"""

from ..lexer import TokenType
from ..ailang_ast import *

class ParserDebugMixin:
    """Mixin for debug-related parsing methods"""
    
    def parse_debug_block(self):
        """Parse Debug("label", level=N) { ... }"""
        self.advance()  # consume 'Debug'
        
        # Default values
        label = "debug"
        level = 1
        
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            
            # Get label if it's a string
            if self.match(TokenType.STRING):
                label = self.current_token.value
                self.advance()
                
                # Check for level parameter
                if self.match(TokenType.COMMA):
                    self.advance()
                    # Skip 'level' identifier if present
                    if self.current_token and self.current_token.value == 'level':
                        self.advance()
                        if self.match(TokenType.EQUALS):
                            self.advance()
                    if self.match(TokenType.NUMBER):
                        level = int(self.current_token.value)
                        self.advance()
            
            self.consume(TokenType.RPAREN)
        
        # Parse the block
        body = []
        if self.match(TokenType.LBRACE):
            self.consume(TokenType.LBRACE)
            self.skip_newlines()
            
            while not self.match(TokenType.RBRACE) and self.current_token:
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
                self.skip_newlines()
            
            self.consume(TokenType.RBRACE)
        
        return DebugBlock(label=label, level=level, body=body,
                         line=self.current_token.line if self.current_token else 0,
                         column=self.current_token.column if self.current_token else 0)
    
    def parse_debug_assert(self):
        """Parse DebugAssert(condition, "message")"""
        self.advance()  # consume 'DebugAssert'
        
        self.consume(TokenType.LPAREN)
        
        # Parse condition
        condition = self.parse_expression()
        
        # Get message
        message = "Assertion failed"
        if self.match(TokenType.COMMA):
            self.advance()
            if self.match(TokenType.STRING):
                message = self.current_token.value
                self.advance()
        
        self.consume(TokenType.RPAREN)
        
        return DebugAssert(condition=condition, message=message,
                          line=self.current_token.line if self.current_token else 0,
                          column=self.current_token.column if self.current_token else 0)
        
    def parse_debug_perf(self):
        """Parse DebugPerf.Start/End/Mark operations"""
        self.consume(TokenType.DEBUGPERF)  # Consume 'DebugPerf' token (not IDENTIFIER)
        self.consume(TokenType.DOT)
        
        operation = self.consume(TokenType.IDENTIFIER).value  # Start, End, Mark, etc.
        
        # Parse the label in parentheses
        label_node = None
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            if self.match(TokenType.STRING):
                label_token = self.consume(TokenType.STRING)
                from ..ailang_ast import String
                label_node = String(value=label_token.value, line=label_token.line, column=label_token.column)
            self.consume(TokenType.RPAREN)
        
        # Handle block syntax for Start (optional)
        body = []
        if operation == "Start" and self.match(TokenType.LBRACE):
            self.consume(TokenType.LBRACE)
            self.skip_newlines()
            while not self.match(TokenType.RBRACE):
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
                self.skip_newlines()
            self.consume(TokenType.RBRACE)
        
        # Create a FunctionCall node that debug_ops can handle
        
        return FunctionCall(
            function=f"DebugPerf.{operation}",
            arguments=[label_node] if label_node else [],
            line=self.current_token.line if self.current_token else 0,
            column=self.current_token.column if self.current_token else 0
        )

    # In parse_debug.py - extend existing ParserDebugMixin

def parse_debug_statement(self):
    """Parse all debug statements - unified syntax"""
    if not self.match(TokenType.DEBUG):
        return None
        
    self.advance()  # consume 'debug'
    
    # Check for debug subcommands
    if self.current_token and self.current_token.type == TokenType.IDENTIFIER:
        cmd = self.current_token.value
        
        # New enhanced debug commands
        if cmd == 'stacktrace':
            return self.parse_debug_stacktrace()
        elif cmd == 'memory':
            return self.parse_debug_memory()
        elif cmd == 'watch':
            return self.parse_debug_watch()
        elif cmd == 'locals':
            return self.parse_debug_locals()
        elif cmd == 'registers':
            return self.parse_debug_registers()
        elif cmd == 'interactive':
            return self.parse_debug_interactive()
        elif cmd == 'breakpoint':
            return self.parse_debug_breakpoint()
        elif cmd == 'profile':
            return self.parse_debug_profile()
        elif cmd == 'leak':
            return self.parse_debug_leak_check()
        elif cmd == 'core':
            return self.parse_debug_core()
        elif cmd == 'assert':
            return self.parse_debug_assert()  # Existing
        elif cmd == 'trace':
            return self.parse_debug_trace()   # Existing
        else:
            # Fall back to existing debug block parsing
            return self.parse_debug_block()