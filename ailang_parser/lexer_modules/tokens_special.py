# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# tokens_special.py - Special Token Types
from enum import Enum, auto

class DelimiterTokens(Enum):
    # Delimiters
    DOT = auto()
    LBRACE = auto()
    RBRACE = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()
    DASH = auto()
    EQUALS = auto()
    ARROW = auto()

class LiteralTokens(Enum):
    # Literals
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()

class CommentTokens(Enum):
    # Comments
    COMMENT = auto()
    DOC_COMMENT = auto()
    COM_COMMENT = auto()
    TAG_COMMENT = auto()

class SpecialTokens(Enum):
    # Special
    EOF = auto()
    NEWLINE = auto()
    # Error token
    ERROR = auto()