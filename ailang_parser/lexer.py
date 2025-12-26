# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# lexer.py - Main lexer interface
from .lexer_modules import TokenType, Token, LexerError, Lexer

# Re-export all necessary components for backward compatibility
__all__ = [
    'TokenType',
    'Token', 
    'LexerError',
    'Lexer'
]