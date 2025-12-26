# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

#parser_class.py
"""Main Parser class with core functionality"""

from typing import List, Optional, Tuple, Dict
from ..lexer import TokenType, Token
from ..ailang_ast import *
from .parse_error import ParseError
from .parse_declarations import ParserDeclarationsMixin
from .parse_statements import ParserStatementsMixin
from .parse_expressions import ParserExpressionsMixin
from .parse_low_level import ParserLowLevelMixin
from .parse_debug import ParserDebugMixin
from .parse_utilities import ParserUtilitiesMixin

class Parser(
    ParserDeclarationsMixin,
    ParserStatementsMixin,
    ParserExpressionsMixin,
    ParserLowLevelMixin,
    ParserDebugMixin,
    ParserUtilitiesMixin
):
    def __init__(self, tokens: List[Token], strict_math: bool = True):
        self.tokens = tokens
        self.position = 0
        self.current_token = self.tokens[0] if tokens else None
        self.previous_token = None
        self.strict_math = strict_math
        self.context_stack: List[str] = []

    def push_context(self, context: str):
        self.context_stack.append(context)

    def pop_context(self):
        if self.context_stack:
            self.context_stack.pop()

    def get_context(self) -> str:
        return " > ".join(self.context_stack) if self.context_stack else "top level"

    def error(self, message: str):
        context = self.get_context()
        raise ParseError(f"In {context}: {message}", self.current_token)

    def advance(self):
        if self.position < len(self.tokens) - 1:
            self.position += 1
            self.previous_token = self.current_token
            self.current_token = self.tokens[self.position]

    def peek(self, offset: int = 1) -> Optional[Token]:
        pos = self.position + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return None

    def match(self, *token_types: TokenType) -> bool:
        return self.current_token and self.current_token.type in token_types

    def check(self, token_type: TokenType) -> bool:
        """Check if current token matches type without consuming it"""
        return self.current_token and self.current_token.type == token_type

    def match_sequence(self, *token_types: TokenType) -> bool:
        for i, token_type in enumerate(token_types):
            token = self.peek(i) if i > 0 else self.current_token
            if not token or token.type != token_type:
                return False
        return True

    def consume(self, token_type: TokenType, message: str = "") -> Token:
        if not self.current_token:
            self.error(f"Expected {token_type.name} but reached end of file. {message}")
        if self.current_token.type != token_type:
            self.error(f"Expected {token_type.name}, got {self.current_token.type.name}. {message}")
        token = self.current_token
        self.advance()
        return token

    def skip_newlines(self):
        while self.match(TokenType.NEWLINE):
            self.advance()

    def parse(self) -> Program:
        self.push_context("program")
        declarations = []
        self.skip_newlines()
        while not self.match(TokenType.EOF):
            self.skip_newlines()
            if self.match(TokenType.EOF):
                break
            if self.match(TokenType.COMMENT, TokenType.DOC_COMMENT, TokenType.COM_COMMENT, TokenType.TAG_COMMENT):
                self.advance()
                continue
            decl = self.parse_declaration()
            if decl:
                declarations.append(decl)
            self.skip_newlines()
        self.pop_context()
        return Program(declarations=declarations, line=1, column=1)