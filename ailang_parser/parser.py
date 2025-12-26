# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

#parser.py
"""Main parser module - provides backward compatibility"""

from .parser_modules.parse_error import ParseError
from .parser_modules.parser_class import Parser

__all__ = ['Parser', 'ParseError']