# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

#parse_expressions.py
"""Parser methods for handling expressions"""

from typing import List, Tuple
from ..lexer import TokenType
from ..ast_modules.ast_expressions import MemberAccess  
from ..ailang_ast import *  

class ParserExpressionsMixin:
    """Mixin for expression parsing methods"""
    
    def parse_expression(self) -> ASTNode:
        """Main entry point - now uses postfix parsing"""
        self.skip_newlines()
        return self.parse_postfix_expression()
    
    def parse_strict_expression(self) -> ASTNode:
        self.skip_newlines()
        if self.match(TokenType.LPAREN):
            return self.parse_parenthesized_expression()
        if self.match(TokenType.ADD, TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.SUBTRACT,
                TokenType.POWER, TokenType.MODULO, TokenType.SQUAREROOT, TokenType.ABSOLUTEVALUE,
   
                TokenType.ISQRT, TokenType.ABS, TokenType.MIN, TokenType.MAX, TokenType.POW,
    
                TokenType.GREATERTHAN, TokenType.LESSTHAN,
                TokenType.GREATERTHAN, TokenType.LESSTHAN,
                TokenType.EQUALTO, TokenType.NOTEQUAL, TokenType.GREATEREQUAL, TokenType.LESSEQUAL,
                TokenType.AND, TokenType.OR, TokenType.NOT,
                # ADD BITWISE OPERATIONS (with correct names):
                TokenType.BITWISEAND, TokenType.BITWISEOR, TokenType.BITWISEXOR,
                TokenType.BITWISENOT, TokenType.LEFTSHIFT, TokenType.RIGHTSHIFT,
                # String and I/O functions
                TokenType.READINPUT, TokenType.READINPUTNUMBER, TokenType.GETUSERCHOICE,
                TokenType.STRINGEQUALS, TokenType.STRINGCONTAINS, TokenType.STRINGSTARTSWITH,
                TokenType.STRINGENDSWITH, TokenType.STRINGCONCAT, TokenType.STRINGSUBSTRING,
                TokenType.STRINGLENGTH, TokenType.STRINGTONUMBER, TokenType.NUMBERTOSTRING,
                TokenType.STRINGTOUPPER, TokenType.STRINGTOLOWER, TokenType.CHARTOSTRING, TokenType.STRINGINDEXOF,
                TokenType.STRINGSPLIT,
                TokenType.STRINGTRIM, TokenType.STRINGREPLACE, TokenType.STRINGTOSTRING,
                TokenType.STRINGEXTRACT, TokenType.STRINGCHARAT, TokenType.STRINGEXTRACTUNTIL,
                TokenType.WRITETEXTFILE, TokenType.READTEXTFILE, TokenType.FILEEXISTS, TokenType.READBINARYFILE, TokenType.WRITEBINARYFILE):
            return self.parse_math_function()
   
        # === NEW: Low-Level Function Parsing ===
        elif self.match(TokenType.DEREFERENCE, TokenType.ADDRESSOF, TokenType.SIZEOF,
                    TokenType.ALLOCATE, TokenType.DEALLOCATE,
                    TokenType.PORTREAD, TokenType.PORTWRITE, TokenType.HARDWAREREGISTER,
                    TokenType.ATOMICREAD, TokenType.ATOMICWRITE, TokenType.MMIOREAD, TokenType.MMIOWRITE, TokenType.STOREVALUE,
                    # ADD ATOMIC OPERATIONS HERE
                    TokenType.ATOMICADD, TokenType.ATOMICSUBTRACT, TokenType.ATOMICCOMPARESWAP, TokenType.ATOMICEXCHANGE):
            return self.parse_lowlevel_function()
        elif self.match(TokenType.MEMORYCOMPARE, TokenType.MEMCHR, TokenType.MEMFIND, TokenType.MEMORYCOPY):
            return self.parse_memop_function()
        # === NEW: Virtual Memory Expression Parsing ===
        elif self.match(TokenType.PAGETABLE, TokenType.VIRTUALMEMORY, TokenType.CACHE, 
                    TokenType.TLB, TokenType.MEMORYBARRIER):
            return self.parse_vm_operation()
        # === NEW: Pool Memory Operations Parsing ===
        elif self.match(TokenType.POOLRESIZE, TokenType.POOLMOVE, TokenType.POOLCOMPACT,
                    TokenType.POOLALLOCATE, TokenType.POOLFREE):
            return self.parse_pool_operation()
        return self.parse_primary()

    def parse_parenthesized_expression(self) -> ASTNode:
        start_token = self.consume(TokenType.LPAREN)
        self.skip_newlines()
        
        # Parse the inner expression recursively
        expr = self.parse_expression()
        self.skip_newlines()
        
        # Check for infix notation (e.g., "(2 Multiply 3)" or "(2 * 3)")
        if isinstance(expr, (Number, Identifier, FunctionCall)):
            self.skip_newlines()
            
            # First check for NAMED operators (existing code)
            if self.match(TokenType.ADD, TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.SUBTRACT, 
                        TokenType.POWER, TokenType.MODULO,
                        TokenType.GREATERTHAN, TokenType.LESSTHAN,
                        TokenType.EQUALTO, TokenType.NOTEQUAL, TokenType.GREATEREQUAL, 
                        TokenType.LESSEQUAL, TokenType.AND, TokenType.OR, TokenType.NOT):
                op_token = self.current_token
                op_name = op_token.value
                
                # Special handling for unary NOT
                if op_token.type == TokenType.NOT:
                    self.advance()
                    self.skip_newlines()
                    operand = self.parse_expression()
                    self.skip_newlines()
                    self.consume(TokenType.RPAREN)
                    return FunctionCall(function='Not', arguments=[operand],
                                    line=start_token.line, column=start_token.column)
                
                # Binary operators
                self.advance()
                self.skip_newlines()
                second_operand = self.parse_expression()
                self.skip_newlines()
                self.consume(TokenType.RPAREN)
                return FunctionCall(function=op_name, arguments=[expr, second_operand],
                                line=start_token.line, column=start_token.column)
            
            #  Check for SYMBOL operators (only valid in parentheses!)
            elif self.match(TokenType.PLUS_SIGN, TokenType.STAR_SIGN, TokenType.SLASH_SIGN,
                TokenType.DASH, TokenType.PERCENT_SIGN, TokenType.CARET_SIGN,
                TokenType.GREATER_SIGN, TokenType.LESS_SIGN, TokenType.BANG_SIGN,
                TokenType.AMPERSAND_SIGN, TokenType.PIPE_SIGN,
                TokenType.EQUALTO, TokenType.NOTEQUAL,  
                TokenType.GREATEREQUAL, TokenType.LESSEQUAL,  
                TokenType.AND_AND, TokenType.PIPE_PIPE,
                TokenType.LESS_LESS, TokenType.GREATER_GREATER):
                
                symbol_token = self.current_token
                
                # Map symbols to operator function names
                symbol_map = {
                TokenType.PLUS_SIGN: 'Add',
                TokenType.DASH: 'Subtract',
                TokenType.STAR_SIGN: 'Multiply',
                TokenType.SLASH_SIGN: 'Divide',
                TokenType.PERCENT_SIGN: 'Modulo',
                TokenType.CARET_SIGN: 'Power',
                TokenType.GREATER_SIGN: 'GreaterThan',
                TokenType.LESS_SIGN: 'LessThan',
                TokenType.EQUALTO: 'EqualTo',           # Changed from EQUAL_EQUAL
                TokenType.NOTEQUAL: 'NotEqual',         # Changed from BANG_EQUAL
                TokenType.GREATEREQUAL: 'GreaterEqual', # Changed from GREATER_EQUAL_SIGN
                TokenType.LESSEQUAL: 'LessEqual',       # Changed from LESS_EQUAL_SIGN
                TokenType.BANG_SIGN: 'Not',
                TokenType.AMPERSAND_SIGN: 'BitwiseAnd',
                TokenType.PIPE_SIGN: 'BitwiseOr',
                TokenType.AND_AND: 'And',
                TokenType.PIPE_PIPE: 'Or',
                TokenType.LESS_LESS: 'LeftShift',
                TokenType.GREATER_GREATER: 'RightShift',
            }
                
                op_name = symbol_map.get(symbol_token.type)
                if not op_name:
                    self.error(f"Unknown operator symbol: {symbol_token.value}")
                
                # Handle unary ! (Not)
                if symbol_token.type == TokenType.BANG_SIGN:
                    self.advance()
                    self.skip_newlines()
                    operand = self.parse_expression()
                    self.skip_newlines()
                    self.consume(TokenType.RPAREN)
                    return FunctionCall(function='Not', arguments=[operand],
                                    line=start_token.line, column=start_token.column)
                
                # Binary operators
                self.advance()
                self.skip_newlines()
                second_operand = self.parse_expression()
                self.skip_newlines()
                self.consume(TokenType.RPAREN)
                return FunctionCall(function=op_name, arguments=[expr, second_operand],
                                line=start_token.line, column=start_token.column)
        
        self.skip_newlines()
        self.consume(TokenType.RPAREN)
        return expr
    
    
    def parse_math_function(self) -> ASTNode:
        op_token = self.current_token
        op_name = op_token.value
        self.advance()
        self.consume(TokenType.LPAREN)
        self.skip_newlines()
        args = []
        while not self.match(TokenType.RPAREN):
            args.append(self.parse_expression())
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
            elif not self.match(TokenType.RPAREN):
                self.skip_newlines()
        self.consume(TokenType.RPAREN)
        return FunctionCall(function=op_name, arguments=args,
                           line=op_token.line, column=op_token.column)

    def parse_memop_function(self) -> ASTNode:
        """Parse memory operation functions"""
        from ailang_parser.ast_modules.ast_memops import MemCompare, MemChr, MemFind, MemCopy
        
        op_token = self.current_token
        op_type = op_token.type
        self.advance()
        
        self.consume(TokenType.LPAREN)
        
        if op_type == TokenType.MEMORYCOMPARE:
            addr1 = self.parse_expression()
            self.consume(TokenType.COMMA)
            addr2 = self.parse_expression()
            self.consume(TokenType.COMMA)
            length = self.parse_expression()
            self.consume(TokenType.RPAREN)
            
            return MemCompare(
                addr1=addr1,
                addr2=addr2,
                length=length,
                line=op_token.line,
                column=op_token.column
            )
        
        elif op_type == TokenType.MEMCHR:
            addr = self.parse_expression()
            self.consume(TokenType.COMMA)
            byte_val = self.parse_expression()
            self.consume(TokenType.COMMA)
            length = self.parse_expression()
            self.consume(TokenType.RPAREN)
            
            return MemChr(
                addr=addr,
                byte_value=byte_val,
                length=length,
                line=op_token.line,
                column=op_token.column
            )
        
        elif op_type == TokenType.MEMORYCOPY:
            # MemCopy(dest, src, length)
            dest = self.parse_expression()
            self.consume(TokenType.COMMA)
            src = self.parse_expression()
            self.consume(TokenType.COMMA)
            length = self.parse_expression()
            self.consume(TokenType.RPAREN)
            
            return MemCopy(
                dest=dest,
                src=src,
                length=length,
                line=op_token.line,
                column=op_token.column
            )
        elif op_type == TokenType.MEMFIND:
            haystack = self.parse_expression()
            self.consume(TokenType.COMMA)
            h_len = self.parse_expression()
            self.consume(TokenType.COMMA)
            needle = self.parse_expression()
            self.consume(TokenType.COMMA)
            n_len = self.parse_expression()
            self.consume(TokenType.RPAREN)
            
            return MemFind(
                haystack=haystack,
                haystack_len=h_len,
                needle=needle,
                needle_len=n_len,
                line=op_token.line,
                column=op_token.column
            )

    def parse_primary(self) -> ASTNode:
        self.skip_newlines()
        
        # Handle prefix - operator (unary minus)
        if self.match(TokenType.DASH):
            token = self.current_token
            self.advance()
            # Recursively parse the expression to be negated.
            # Using parse_primary() gives it high precedence.
            operand = self.parse_primary()
            
            # Syntactic sugar: -x becomes Subtract(0, x)
            zero_node = Number(value="0", line=token.line, column=token.column)
            return FunctionCall(function='Subtract', arguments=[zero_node, operand],
                                line=token.line, column=token.column)

        # Handle prefix ! operator (unary NOT)
        if self.match(TokenType.BANG_SIGN):
            token = self.current_token
            self.advance()
            operand = self.parse_primary()  # Recursively parse what comes after !
            return FunctionCall(function='Not', arguments=[operand],
                            line=token.line if token else 0, 
                            column=token.column if token else 0)
            
        if self.match(TokenType.TILDE_SIGN):
            token = self.current_token
            self.advance()
            operand = self.parse_primary()
            return FunctionCall(function='BitwiseNot', arguments=[operand],
                            line=token.line if token else 0, 
                            column=token.column if token else 0)

        # Allow SystemCall to be used as a value-producing expression
        if self.match(TokenType.SYSCALL):
            return self.parse_system_call()
        
        if self.match(TokenType.NUMBER):
            token = self.current_token
            self.advance()
            return Number(value=token.value, line=token.line, column=token.column)
        
        elif self.match(TokenType.STRING):
            token = self.current_token
            self.advance()
            return String(value=token.value, line=token.line, column=token.column)
        
        elif self.match(TokenType.TRUE):
            token = self.current_token
            self.advance()
            return Boolean(value=True, line=token.line, column=token.column)
        
        elif self.match(TokenType.FALSE):
            token = self.current_token
            self.advance()
            return Boolean(value=False, line=token.line, column=token.column)
        
        elif self.match(TokenType.NULL):
            token = self.current_token
            self.advance()
            return Number(value=0, line=token.line, column=token.column)
        
        elif self.match(TokenType.LAMBDA):
            return self.parse_lambda()
        
        elif self.match(TokenType.APPLY):
            return self.parse_apply()
        
        elif self.match(TokenType.RUNTASK):
            return self.parse_runtask()
        
        elif self.match(TokenType.RUNMACRO):
            return self.parse_runmacro()
        
        elif self.match(TokenType.IDENTIFIER, TokenType.FIXEDPOOL, TokenType.DYNAMICPOOL,
                TokenType.TEMPORALPOOL, TokenType.NEURALPOOL, TokenType.KERNELPOOL,
                TokenType.ACTORPOOL, TokenType.SECURITYPOOL, TokenType.CONSTRAINEDPOOL,
                TokenType.FILEPOOL, TokenType.LINKAGEPOOL):
            # MODIFIED to handle tilde suffix directly
            identifier_token = self.current_token
            identifier_name = identifier_token.value
            self.advance()

            # Check for ~ suffix (force acronym expansion)
            if self.match(TokenType.TILDE_SIGN) or (self.current_token and self.current_token.value == '~'):
                self.advance()  # Consume the ~

                # Force expand through acronym map
                acronym_map = None
                if hasattr(self, 'compiler') and hasattr(self.compiler, 'acronym_map'):
                    acronym_map = self.compiler.acronym_map
                elif hasattr(self, 'acronym_map'):
                    acronym_map = self.acronym_map
                
                if acronym_map and identifier_name in acronym_map:
                    expanded = acronym_map[identifier_name]
                    print(f"DEBUG: Force expanded {identifier_name}~ to {expanded}")
                    identifier_name = expanded
            
            # Create the identifier node with possibly expanded name
            return Identifier(
                name=identifier_name,
                line=identifier_token.line,
                column=identifier_token.column
            )
            return self.parse_identifier()
        
        elif self.match(TokenType.LPAREN):
            return self.parse_parenthesized_expression()
        
        elif self.match(TokenType.LBRACKET):
            return self.parse_array_literal()
        
        elif self.match(TokenType.LBRACE):
        # Map literals not implemented yet
            return None
        
        elif self.match(TokenType.PI):
            token = self.current_token
            self.advance()
            return Number(value=3.14159265358979323846, line=token.line, column=token.column)
        
        elif self.match(TokenType.E):
            token = self.current_token
            self.advance()
            return Number(value=2.71828182845904523536, line=token.line, column=token.column)
        
        elif self.match(TokenType.PHI):
            token = self.current_token
            self.advance()
            return Number(value=1.61803398874989484820, line=token.line, column=token.column)
        
        elif self.match(TokenType.BYTES, TokenType.KILOBYTES, TokenType.MEGABYTES,
                    TokenType.GIGABYTES, TokenType.SECONDS, TokenType.MILLISECONDS,
                    TokenType.MICROSECONDS, TokenType.PERCENT):
            return self.parse_unit()
        
        elif self.match(TokenType.BYTE, TokenType.WORD, TokenType.DWORD, TokenType.QWORD):
            return self.parse_memory_size_cast()
        
        # Hash operations
        elif self.match(TokenType.HASHCREATE):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "HashCreate", args)
        
        elif self.match(TokenType.HASHFUNCTION):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "HashFunction", args)
        
        elif self.match(TokenType.HASHSET):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "HashSet", args)
        
        elif self.match(TokenType.HASHGET):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "HashGet", args)
        
        # Socket operations
        elif self.match(TokenType.SOCKETCREATE):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "SocketCreate", args)
        
        elif self.match(TokenType.SOCKETBIND):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "SocketBind", args)
        
        elif self.match(TokenType.SOCKETLISTEN):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "SocketListen", args)
        
        elif self.match(TokenType.SOCKETACCEPT):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "SocketAccept", args)
        
        elif self.match(TokenType.SOCKETREAD):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "SocketRead", args)
        
        elif self.match(TokenType.SOCKETWRITE):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "SocketWrite", args)
        
        elif self.match(TokenType.SOCKETCLOSE):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "SocketClose", args)
        
        elif self.match(TokenType.SOCKETCONNECT):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "SocketConnect", args)
        
        elif self.match(TokenType.SOCKETSETOPTION):
            line = self.current_token.line
            column = self.current_token.column
            self.advance()
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "Expected ')'")
            return FunctionCall(line, column, "SocketSetOption", args)
        
        else:
            self.error(f"Unexpected token in expression: {self.current_token.value if self.current_token else 'EOF'}")

    def parse_apply(self) -> Apply:
        start_token = self.consume(TokenType.APPLY)
        self.consume(TokenType.LPAREN)
        self.skip_newlines()
        function = self.parse_expression()
        arguments = []
        while self.match(TokenType.COMMA):
            self.consume(TokenType.COMMA)
            self.skip_newlines()
            arguments.append(self.parse_expression())
        self.skip_newlines()
        self.consume(TokenType.RPAREN)
        return Apply(function=function, arguments=arguments,
                    line=start_token.line, column=start_token.column)

    def parse_runmacro(self) -> RunMacro:
        start_token = self.consume(TokenType.RUNMACRO)
        self.consume(TokenType.DOT)
        macro_path = self.parse_dotted_name()
        self.consume(TokenType.LPAREN)
        self.skip_newlines()
        arguments = []
        while not self.match(TokenType.RPAREN):
            arguments.append(self.parse_expression())
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
            elif not self.match(TokenType.RPAREN):
                self.skip_newlines()
        self.consume(TokenType.RPAREN)
        return RunMacro(macro_path=macro_path, arguments=arguments,
                        line=start_token.line, column=start_token.column)

    def parse_identifier(self) -> ASTNode:
        """Parse an identifier, handling ~ suffix for forced expansion"""
        identifier_token = self.consume(TokenType.IDENTIFIER)
        identifier_name = identifier_token.value

        # Check if next character is ~
        if self.current_token and self.current_token.value == '~':
            self.advance()  # Consume ~

            # Try to expand through acronym map
            acronym_map = None
            if hasattr(self, 'compiler') and hasattr(self.compiler, 'acronym_map'):
                acronym_map = self.compiler.acronym_map # Access acronym_map from compiler
            elif hasattr(self, 'acronym_map'):
                acronym_map = self.acronym_map

            if acronym_map and identifier_name in acronym_map:
                expanded = acronym_map[identifier_name]
                print(f"DEBUG: Force expanded {identifier_name}~ to {expanded}")
                identifier_name = expanded

        return Identifier(
            name=identifier_name,
            line=identifier_token.line,
            column=identifier_token.column
        )
    def parse_array_literal(self):
        """Parse array literal [...]"""
        start_token = self.consume(TokenType.LBRACKET)
        elements = []
        self.skip_newlines()
        while not self.match(TokenType.RBRACKET):
            elements.append(self.parse_expression())
            self.skip_newlines()
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
            elif not self.match(TokenType.RBRACKET):
                self.error("Expected ',' or ']' in array literal")
        self.consume(TokenType.RBRACKET)
        return Array(elements=elements, line=start_token.line, column=start_token.column)

    def parse_unit(self):
        """Parse units like Bytes, Seconds, etc."""
        token = self.current_token
        unit_type = token.value
        self.advance()
        
        # Some units may be followed by a value
        value = None
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            value = self.parse_expression()
            self.consume(TokenType.RPAREN)
        
        return FunctionCall(
            function=unit_type,
            arguments=[value] if value else [],
            line=token.line,
            column=token.column
        )

    def parse_memory_size_cast(self):
        """Parse memory size cast operations"""
        token = self.current_token
        cast_type = token.value
        self.advance()
        
        # Memory casts expect a value
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            value = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return FunctionCall(
                function=f"Cast{cast_type}",
                arguments=[value],
                line=token.line,
                column=token.column
            )
        else:
            self.error(f"Expected '(' after {cast_type}")

    def parse_record_type(self):
        """Parse Record type definitions"""
        start_token = self.consume(TokenType.RECORD)
        self.consume(TokenType.DOT)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LBRACE)
        
        fields = {}
        self.skip_newlines()
        while not self.match(TokenType.RBRACE):
            field_name = self.consume(TokenType.IDENTIFIER).value
            self.consume(TokenType.COLON)
            field_type = self.parse_type()
            fields[field_name] = field_type
            
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
            else:
                self.skip_newlines()
        
        self.consume(TokenType.RBRACE)
        return RecordType(
            name=name,
            fields=fields,
            line=start_token.line,
            column=start_token.column
        )
        
        
    def parse_postfix_expression(self) -> ASTNode:
        """
        Handles member access and function calls properly
        """
        # Start with primary expression (use existing method)
        # If parse_strict_expression exists, use it; otherwise use parse_primary
        if hasattr(self, 'parse_strict_expression'):
            expr = self.parse_strict_expression()
        else:
            expr = self.parse_primary()
        
        # Handle postfix operators
        while True:
            if self.match(TokenType.DOT):
                # Member access
                self.consume(TokenType.DOT)
                
                if not self.match(TokenType.IDENTIFIER):
                    self.error(f"Expected identifier after '.' at line {self.current_token.line}")
                
                member_token = self.consume(TokenType.IDENTIFIER)
                member_ident = Identifier(
                    name=member_token.value,
                    line=member_token.line,
                    column=member_token.column
                )
                
                # Create MemberAccess node
                expr = MemberAccess(
                    obj=expr,
                    member=member_ident,
                    line=expr.line,
                    column=expr.column
                )
                
            elif self.match(TokenType.LPAREN):
                # Function call
                lparen_token = self.current_token
                self.consume(TokenType.LPAREN)
                
                arguments = []
                if not self.check(TokenType.RPAREN):
                    arguments.append(self.parse_expression())
                    
                    while self.match(TokenType.COMMA):
                        self.consume(TokenType.COMMA)
                        self.skip_newlines()
                        arguments.append(self.parse_expression())
                
                self.consume(TokenType.RPAREN)
                
                # FIX: Convert MemberAccess to dotted string for AllocateLinkage
                if isinstance(expr, Identifier) and expr.name == "AllocateLinkage":
                    fixed_args = []
                    for arg in arguments:
                        if isinstance(arg, MemberAccess):
                            # Convert LinkagePool.TestPool to "LinkagePool.TestPool"
                            dotted_name = f"{arg.obj.name}.{arg.member.name}"
                            fixed_args.append(Identifier(name=dotted_name, line=arg.line, column=arg.column))
                        else:
                            fixed_args.append(arg)
                    arguments = fixed_args

                # Handle special case for Negate
                if isinstance(expr, Identifier) and expr.name == "Negate":
                    if len(arguments) != 1:
                        self.error(f"Negate function expects 1 argument, but got {len(arguments)}")
                    
                    zero_node = Number(value=0, line=lparen_token.line, column=lparen_token.column)
                    
                    return FunctionCall(
                        function="Subtract",  # Keep as string for compatibility
                        arguments=[zero_node, arguments[0]],
                        line=lparen_token.line,
                        column=lparen_token.column
                    )
                
                # For compatibility, convert simple identifiers back to strings
                if isinstance(expr, Identifier):
                    function_ref = expr.name
                else:
                    function_ref = expr  # Keep as AST node for member access
                
                expr = FunctionCall(
                    function=function_ref,
                    arguments=arguments,
                    line=lparen_token.line,
                    column=lparen_token.column
                )
                
            else:
                # No more postfix operators
                break
        
        return expr
    
    # ============= NEW METHOD - ADD THIS =============
    def parse_function_call_with_base(self, function_expr: ASTNode) -> FunctionCall:
        """
        NEW METHOD - Parses function call arguments for a given function expression.
        This is different from your existing function call parsing.
        """
        # Save position for error reporting
        lparen_token = self.current_token
        self.consume(TokenType.LPAREN)
        
        # Parse arguments
        arguments = []
        if not self.check(TokenType.RPAREN):
            arguments.append(self.parse_expression())
            
            while self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
                arguments.append(self.parse_expression())
        
        self.consume(TokenType.RPAREN)
        
        return FunctionCall(
            function=function_expr,  # Now an AST node, not a string
            arguments=arguments,
            line=lparen_token.line,
            column=lparen_token.column
        )