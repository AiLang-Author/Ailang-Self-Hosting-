# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

#parse_utilities.py
"""Parser utility methods"""

from typing import List
from ..lexer import TokenType
from ..ailang_ast import *

class ParserUtilitiesMixin:
    """Mixin for utility parsing methods"""
    
    def parse_dotted_name(self) -> str:
        parts = [self.consume(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT) and self.peek() and self.peek().type == TokenType.IDENTIFIER:
            self.consume(TokenType.DOT)
            parts.append(self.consume(TokenType.IDENTIFIER).value)
        return '.'.join(parts)

    def parse_qualified_name(self) -> str:
        """
        Parses a name that can start with a keyword or identifier,
        e.g., FixedPool.Name or MyVar.field
        """
        # DEBUG: Print what we're actually looking at
        print(f"DEBUG parse_qualified_name: current_token.type={self.current_token.type if self.current_token else None}, value={self.current_token.value if self.current_token else None}")
        
        pool_keywords = [
            TokenType.FIXEDPOOL, TokenType.DYNAMICPOOL,
            TokenType.TEMPORALPOOL, TokenType.NEURALPOOL, TokenType.KERNELPOOL,
            TokenType.ACTORPOOL, TokenType.SECURITYPOOL, TokenType.CONSTRAINEDPOOL,
            TokenType.FILEPOOL, TokenType.LINKAGEPOOL
        ]
        
        allowed_first_tokens = [TokenType.IDENTIFIER] + pool_keywords
        
        if not self.match(*allowed_first_tokens):
            self.error("Expected an identifier or pool type to start a qualified name.")
        
        # Check if first token is a pool keyword
        is_pool_type = self.current_token.type in pool_keywords
        
        parts = [self.current_token.value]
        self.advance()
        
        # Only consume dots if this started with a pool keyword
        # Regular identifiers should let parse_postfix_expression handle member access
        if is_pool_type:
            while self.match(TokenType.DOT) and self.peek() and self.peek().type == TokenType.IDENTIFIER:
                self.consume(TokenType.DOT)
                parts.append(self.consume(TokenType.IDENTIFIER).value)
        
        return '.'.join(parts)

    def parse_type(self):
        """Parse type annotations"""
        type_tokens = [
            TokenType.IDENTIFIER, TokenType.INTEGER, TokenType.FLOATINGPOINT,
            TokenType.TEXT, TokenType.BOOLEAN, TokenType.ADDRESS, TokenType.ARRAY,
            TokenType.MAP, TokenType.TUPLE, TokenType.RECORD, TokenType.OPTIONALTYPE,
            TokenType.CONSTRAINEDTYPE, TokenType.ANY, TokenType.VOID,
            # Low-level types
            TokenType.BYTE, TokenType.WORD, TokenType.DWORD, TokenType.QWORD,
            TokenType.UINT8, TokenType.UINT16, TokenType.UINT32, TokenType.UINT64,
            TokenType.INT8, TokenType.INT16, TokenType.INT32, TokenType.INT64,
            TokenType.POINTER, TokenType.LINKAGEPOOL
        ]
        if self.match(*type_tokens):
            token = self.current_token
            type_name = token.value
            self.advance()
            
            # Handle dotted types like LinkagePool.RequestArea
            while self.match(TokenType.DOT):
                self.consume(TokenType.DOT)
                next_token = self.consume(TokenType.IDENTIFIER)
                type_name += '.' + next_token.value
            
            # Return string directly for LinkagePool types
            if type_name.startswith('LinkagePool'):
                return type_name
            
            # Return TypeExpression for other types
            return TypeExpression(base_type=type_name, line=token.line, column=token.column)
        return None

    def parse_string_array(self) -> List[str]:
        """Parse an array of strings"""
        strings = []
        self.consume(TokenType.LBRACKET)
        while not self.match(TokenType.RBRACKET):
            if self.match(TokenType.STRING):
                strings.append(self.consume(TokenType.STRING).value)
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
        self.consume(TokenType.RBRACKET)
        return strings